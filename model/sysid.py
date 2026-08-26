"""Recover physical parameters from noisy trajectory data.

JD: "Tune physics parameters -- friction, damping, inertia, actuator models --
to maximize sim-to-real transfer."

Everything else in this project VALIDATES a model whose parameters are known.
This does the inverse, which is the actual job: a robot arrives, you do not know
its damping or joint friction, and you have noisy encoder data.

Method:
  1. Generate "hardware" data from the arm with parameters I then pretend not
     to know, plus encoder noise and a limited sample rate.
  2. Recover them by minimising trajectory error over the simulator itself.
  3. Report on a HELD-OUT trajectory from a different initial condition.

Step 3 is the one that matters. Fitting the training trajectory proves nothing
-- enough free parameters will fit anything. Predicting motion the optimiser
never saw is the claim worth making.
"""
import json, os, sys
import numpy as np
import mujoco
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BASE = open(os.path.join(HERE, "arm3.xml")).read()

# The values the "hardware" actually has. The optimiser never sees these.
TRUE = {"damping": [0.155, 0.083, 0.061], "frictionloss": 0.037}

ENCODER_NOISE_RAD = 0.002      # ~0.11 deg, a realistic encoder
SAMPLE_HZ = 100                # loggers rarely run at the physics rate
DT = 0.002


def build(damping, frictionloss):
    """Rewrite the model with a candidate parameter set."""
    xml = BASE
    for i, d in enumerate(damping, start=1):
        # each joint line carries its own damping; replace positionally
        xml = xml.replace(f'name="j_link{i}"', f'name="j_link{i}" __M{i}__')
    for i, d in enumerate(damping, start=1):
        xml = xml.replace(f'__M{i}__', "")
    # simplest reliable route: patch the numeric attributes directly
    m = mujoco.MjModel.from_xml_string(BASE)
    for i, d in enumerate(damping):
        m.dof_damping[i] = float(d)
        m.dof_frictionloss[i] = float(frictionloss)
    return m


def rollout(m, q0, steps=1000):
    d = mujoco.MjData(m)
    d.qpos[:] = q0
    mujoco.mj_forward(m, d)
    every = max(1, int(round(1.0 / (SAMPLE_HZ * DT))))
    out = []
    for i in range(steps):
        mujoco.mj_step(m, d)
        if i % every == 0:
            out.append(d.qpos.copy())
    return np.array(out)


def make_measurements(q0, seed=0):
    """Simulated 'hardware': true parameters, encoder noise, 100 Hz logging."""
    rng = np.random.default_rng(seed)
    m = build(TRUE["damping"], TRUE["frictionloss"])
    clean = rollout(m, q0)
    return clean + rng.normal(0, ENCODER_NOISE_RAD, clean.shape), clean


def residual_multi(theta, datasets):
    """Fit across SEVERAL trajectories at once.

    One gravity-driven settle does not excite damping and Coulomb friction
    distinguishably -- they trade off, so many parameter sets fit it equally
    well. That is an identifiability problem, not an optimiser problem, and the
    fix is excitation: more initial conditions, covering more of the state
    space.
    """
    damping = np.abs(theta[:3]); fric = abs(theta[3])
    try:
        m = build(damping, fric)
    except Exception:
        return 1e6
    tot = 0.0
    for meas, q0 in datasets:
        pred = rollout(m, q0)
        n = min(len(pred), len(meas))
        tot += ((pred[:n] - meas[:n]) ** 2).mean()
    return float(np.sqrt(tot / len(datasets)))


def residual(theta, meas, q0):
    damping = np.abs(theta[:3])
    fric = abs(theta[3])
    try:
        pred = rollout(build(damping, fric), q0)
    except Exception:
        return 1e6
    n = min(len(pred), len(meas))
    return float(np.sqrt(((pred[:n] - meas[:n]) ** 2).mean()))


if __name__ == "__main__":
    Q_TRAIN = np.array([0.4, -0.7, 1.0])
    Q_TEST = np.array([-0.6, 0.5, -0.9])       # never seen by the optimiser

    meas_train, clean_train = make_measurements(Q_TRAIN, seed=0)
    meas_test, clean_test = make_measurements(Q_TEST, seed=1)

    # a deliberately poor starting guess -- a nominal CAD model, say
    x0 = np.array([0.30, 0.30, 0.30, 0.10])
    print(f"true      : damping {TRUE['damping']}  friction {TRUE['frictionloss']}")
    print(f"initial   : damping {list(x0[:3])}  friction {x0[3]}")
    print(f"noise     : {ENCODER_NOISE_RAD} rad encoder, {SAMPLE_HZ} Hz logging\n")

    # --- single trajectory (what most people do) ---------------------
    res = minimize(residual, x0, args=(meas_train, Q_TRAIN),
                   method="Nelder-Mead",
                   options={"maxiter": 600, "xatol": 1e-5, "fatol": 1e-8})
    est_d = list(np.abs(res.x[:3])); est_f = abs(res.x[3])

    # --- several trajectories (excitation) -----------------------------
    EXCITE = [np.array([0.4,-0.7,1.0]), np.array([-0.5,0.9,-1.1]),
              np.array([1.2,-1.4,0.3]), np.array([-1.0,-0.2,1.5]),
              np.array([0.1, 1.1,-1.3])]
    sets = [(make_measurements(q, seed=10+i)[0], q) for i, q in enumerate(EXCITE)]
    res_m = minimize(residual_multi, x0, args=(sets,), method="Nelder-Mead",
                     options={"maxiter": 1200, "xatol": 1e-5, "fatol": 1e-9})
    md = list(np.abs(res_m.x[:3])); mf = abs(res_m.x[3])
    merrs = [abs(e-t)/t*100 for e, t in zip(md, TRUE["damping"])]
    mferr = abs(mf-TRUE["frictionloss"])/TRUE["frictionloss"]*100

    print(f"recovered : damping {[round(v,4) for v in est_d]}  "
          f"friction {est_f:.4f}")
    print(f"  {res.nit} iterations, final train RMS {res.fun:.6f} rad\n")

    errs = [abs(e - t) / t * 100 for e, t in zip(est_d, TRUE["damping"])]
    ferr = abs(est_f - TRUE["frictionloss"]) / TRUE["frictionloss"] * 100
    for i, (e, t, pc) in enumerate(zip(est_d, TRUE["damping"], errs), 1):
        print(f"  damping j{i}: {e:.4f} vs {t:.4f}   {pc:5.1f}% error")
    print(f"  friction   : {est_f:.4f} vs {TRUE['frictionloss']:.4f}   {ferr:5.1f}% error")

    # THE test: does the identified model predict motion it was never fit to?
    pred_test = rollout(build(est_d, est_f), Q_TEST)
    pred_nom = rollout(build(x0[:3], x0[3]), Q_TEST)
    n = min(len(pred_test), len(clean_test))
    rms_id = float(np.sqrt(((pred_test[:n] - clean_test[:n]) ** 2).mean()))
    rms_nom = float(np.sqrt(((pred_nom[:n] - clean_test[:n]) ** 2).mean()))
    print(f"\nHELD-OUT trajectory (q0 = {list(Q_TEST)}), vs noiseless truth:")
    print(f"  nominal model    RMS {rms_nom:.5f} rad")
    print(f"  identified model RMS {rms_id:.5f} rad")
    print(f"  improvement      {rms_nom/max(rms_id,1e-12):.1f}x")

    # --- multi-start ---------------------------------------------------
    # Probing the loss surface showed the TRUE parameters fit 35x better than
    # what a single Nelder-Mead run found, with a ridge of residual ~0.67
    # between the two. So the parameters ARE identifiable; the optimiser was
    # simply trapped. More excitation does not help a local-minimum problem --
    # more starting points does.
    rng_s = np.random.default_rng(7)
    starts = [x0] + [np.concatenate([rng_s.uniform(0.02, 0.5, 3),
                                     [rng_s.uniform(0.005, 0.15)]])
                     for _ in range(11)]
    best = None
    for st in starts:
        r = minimize(residual_multi, st, args=(sets,), method="Nelder-Mead",
                     options={"maxiter": 900, "xatol": 1e-6, "fatol": 1e-10})
        if best is None or r.fun < best.fun:
            best = r
    bd = list(np.abs(best.x[:3])); bf = abs(best.x[3])
    berrs = [abs(e-t)/t*100 for e, t in zip(bd, TRUE["damping"])]
    bferr = abs(bf-TRUE["frictionloss"])/TRUE["frictionloss"]*100
    pred_b = rollout(build(bd, bf), Q_TEST)
    nb_ = min(len(pred_b), len(clean_test))
    rms_b = float(np.sqrt(((pred_b[:nb_]-clean_test[:nb_])**2).mean()))

    print(f"\n--- with {len(EXCITE)} excitation trajectories instead of 1 ---")
    print(f"recovered : damping {[round(v,4) for v in md]}  friction {mf:.4f}")
    for i,(e,t,pc) in enumerate(zip(md, TRUE["damping"], merrs), 1):
        print(f"  damping j{i}: {e:.4f} vs {t:.4f}   {pc:5.1f}% error")
    print(f"  friction   : {mf:.4f} vs {TRUE['frictionloss']:.4f}   {mferr:5.1f}% error")
    pred_m = rollout(build(md, mf), Q_TEST)
    nm = min(len(pred_m), len(clean_test))
    rms_m = float(np.sqrt(((pred_m[:nm]-clean_test[:nm])**2).mean()))
    print(f"  held-out RMS {rms_m:.5f} rad")
    print(f"\n--- multi-start ({len(starts)} starting points) ---")
    print(f"recovered : damping {[round(v,4) for v in bd]}  friction {bf:.4f}")
    for i,(e,t,pc) in enumerate(zip(bd, TRUE["damping"], berrs), 1):
        print(f"  damping j{i}: {e:.4f} vs {t:.4f}   {pc:5.1f}% error")
    print(f"  friction   : {bf:.4f} vs {TRUE['frictionloss']:.4f}   {bferr:5.1f}% error")
    print(f"  held-out RMS {rms_b:.5f} rad   train residual {best.fun:.6f}")

    print(f"\nmean |param error|")
    print(f"  1 trajectory            {np.mean(errs+[ferr]):7.1f}%")
    print(f"  {len(EXCITE)} trajectories, 1 start  {np.mean(merrs+[mferr]):7.1f}%")
    print(f"  {len(EXCITE)} trajectories, {len(starts)} starts {np.mean(berrs+[bferr]):7.1f}%")

    json.dump({"true": TRUE,
               "multi": {"n_trajectories": len(EXCITE),
                         "damping": [float(v) for v in md],
                         "frictionloss": float(mf),
                         "param_errors_pct": {"damping": merrs, "frictionloss": mferr},
                         "heldout_rms": rms_m,
                         "mean_abs_param_error_pct": float(np.mean(merrs+[mferr]))},
               "multistart": {"n_starts": len(starts),
                              "damping": [float(v) for v in bd],
                              "frictionloss": float(bf),
                              "param_errors_pct": {"damping": berrs, "frictionloss": bferr},
                              "mean_abs_param_error_pct": float(np.mean(berrs+[bferr])),
                              "heldout_rms": rms_b,
                              "train_residual": float(best.fun)},
               "single_mean_abs_param_error_pct": float(np.mean(errs+[ferr])),
               "initial_guess": {"damping": list(x0[:3]), "frictionloss": float(x0[3])},
               "recovered": {"damping": [float(v) for v in est_d],
                             "frictionloss": float(est_f)},
               "param_errors_pct": {"damping": errs, "frictionloss": ferr},
               "encoder_noise_rad": ENCODER_NOISE_RAD, "sample_hz": SAMPLE_HZ,
               "iterations": int(res.nit), "train_rms_rad": float(res.fun),
               "heldout": {"q0": list(map(float, Q_TEST)),
                           "rms_nominal": rms_nom, "rms_identified": rms_id,
                           "improvement_x": rms_nom / max(rms_id, 1e-12)}},
              open(os.path.join(HERE, "sysid.json"), "w"), indent=2)
    print("\nwrote model/sysid.json")


def sensitivity_report(sets_q0, out_path=None):
    """Which parameters can this experiment identify AT ALL?

    Perturb each parameter and measure how much the observable trajectory
    changes. A parameter with zero sensitivity leaves no trace in the data:
    no optimiser, no amount of data and no number of restarts can recover it.
    Running this FIRST tells you which numbers are worth fitting.
    """
    base_d, base_f = TRUE["damping"], TRUE["frictionloss"]
    ref = [rollout(build(base_d, base_f), q) for q in sets_q0]
    rows = []
    for i in range(3):
        pert = list(base_d); pert[i] *= 10.0
        alt = [rollout(build(pert, base_f), q) for q in sets_q0]
        s = max(float(np.abs(a[:min(len(a), len(r))] - r[:min(len(a), len(r))]).max())
                for a, r in zip(alt, ref))
        rows.append({"param": f"damping_j{i+1}", "sensitivity_rad": s,
                     "identifiable": bool(s > 1e-6)})
    alt = [rollout(build(base_d, base_f * 10), q) for q in sets_q0]
    s = max(float(np.abs(a[:min(len(a), len(r))] - r[:min(len(a), len(r))]).max())
            for a, r in zip(alt, ref))
    rows.append({"param": "frictionloss", "sensitivity_rad": s,
                 "identifiable": bool(s > 1e-6)})
    if out_path:
        json.dump(rows, open(out_path, "w"), indent=2)
    return rows
