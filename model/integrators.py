"""Integrator accuracy: verify the ORDER, not just the vibe.

JD: "validate simulation fidelity" / "optimize simulation performance."

"RK4 is more accurate than Euler" is not a validation. The rigorous statement
is that a method of order p has global error O(dt^p), so halving dt must cut
the error by 2^p. That is measurable, and it is the standard way to catch a
mis-implemented or silently-degraded integrator: an RK4 that converges at
order 1 is telling you something is wrong that no eyeball test would reveal.

Two independent checks here:
  1. observed order    -- slope of log(error) vs log(dt), against theory
  2. energy drift      -- on a conservative system, total energy is invariant,
                          so any drift is pure integration error

The system is a damping-free, actuator-free double pendulum under gravity:
conservative by construction, and stiff enough to separate the methods.
"""
import json, os, time
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))

PENDULUM = """
<mujoco>
  <option timestep="{dt}" gravity="0 0 -9.81" integrator="{integ}"/>
  <worldbody>
    <body pos="0 0 1">
      <joint name="a" type="hinge" axis="0 1 0"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.02" mass="1"/>
      <body pos="0 0 -0.3">
        <joint name="b" type="hinge" axis="0 1 0"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.02" mass="1"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""

# start at a moderate amplitude: energetic enough to be a real test, mild
# enough that chaos does not swamp the convergence measurement inside T
Q0 = np.array([0.8, 0.4])
T_END = 0.5


def integrate(integ, dt, t_end=T_END, q0=Q0, want_energy=False):
    m = mujoco.MjModel.from_xml_string(PENDULUM.format(dt=dt, integ=integ))
    d = mujoco.MjData(m)
    d.qpos[:2] = q0
    mujoco.mj_forward(m, d)
    n = int(round(t_end / dt))
    energies = []
    t0 = time.perf_counter()
    for _ in range(n):
        mujoco.mj_step(m, d)
        if want_energy:
            mujoco.mj_energyPos(m, d)
            mujoco.mj_energyVel(m, d)
            energies.append(float(d.energy[0] + d.energy[1]))
    wall = time.perf_counter() - t0
    return {"qpos": d.qpos[:2].copy(), "wall": wall, "steps": n,
            "energy": np.array(energies) if want_energy else None}


def reference():
    """RK4 at a timestep far below anything under test."""
    return integrate("RK4", 1e-6)["qpos"]


def order_of_accuracy(integ, dts, ref):
    errs, rows = [], []
    for dt in dts:
        r = integrate(integ, dt)
        e = float(np.linalg.norm(r["qpos"] - ref))
        errs.append(max(e, 1e-16))
        rows.append({"dt": dt, "error": e, "wall_s": round(r["wall"], 5),
                     "steps_per_s": round(r["steps"] / r["wall"], 1)})
    # fit only where the error is above round-off and below saturation
    e = np.array(errs); x = np.log(np.array(dts))
    keep = (e > 1e-13) & (e < 1e-1)
    order = float(np.polyfit(x[keep], np.log(e[keep]), 1)[0]) if keep.sum() >= 3 else None
    return {"integrator": integ, "rows": rows,
            "observed_order": round(order, 3) if order else None,
            "points_used": int(keep.sum())}


def energy_drift(integ, dt=0.001, t_end=5.0):
    """On a conservative system any change in total energy is error."""
    r = integrate(integ, dt, t_end=t_end, want_energy=True)
    E = r["energy"]
    if E is None or len(E) < 10:
        return None
    rel = (E - E[0]) / abs(E[0])
    return {"integrator": integ, "dt": dt,
            "rel_drift_final": float(rel[-1]),
            "rel_drift_max_abs": float(np.abs(rel).max()),
            "drift_per_s": float(rel[-1] / t_end),
            "steps_per_s": round(r["steps"] / r["wall"], 1)}


THEORY = {"Euler": 1, "implicit": 1, "implicitfast": 1, "RK4": 4}

# --------------------------------------------------------------------------
# `implicitfast` reported energy drift IDENTICAL to `Euler` to four significant
# figures (4.661e-04 /s, max 2.437e-03). Two integrators agreeing that exactly
# is not a coincidence -- it means they are doing the same arithmetic.
#
# Hypothesis: `implicitfast` only treats VELOCITY-DEPENDENT forces implicitly
# (joint damping, fluid drag, actuator damping). The test pendulum has none of
# those -- no damping, no actuators, no viscosity -- so there is nothing to
# implicitise and it degenerates to explicit Euler.
#
# If that is right, adding joint damping must separate them.
# --------------------------------------------------------------------------

DAMPED = """
<mujoco>
  <option timestep="{dt}" gravity="0 0 -9.81" integrator="{integ}"/>
  <worldbody>
    <body pos="0 0 1">
      <joint name="a" type="hinge" axis="0 1 0" damping="{damp}"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.02" mass="1"/>
      <body pos="0 0 -0.3">
        <joint name="b" type="hinge" axis="0 1 0" damping="{damp}"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.02" mass="1"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""


def damped_run(integ, damp, dt=0.005, t_end=2.0):
    m = mujoco.MjModel.from_xml_string(DAMPED.format(dt=dt, integ=integ, damp=damp))
    d = mujoco.MjData(m)
    d.qpos[:2] = Q0
    mujoco.mj_forward(m, d)
    for _ in range(int(round(t_end / dt))):
        mujoco.mj_step(m, d)
    return d.qpos[:2].copy()


def implicitfast_vs_euler(damps=(0.0, 0.01, 1.0, 50.0)):
    """The separating experiment. With no damping the two must agree exactly;
    with damping present implicitfast should pull away, and the gap should
    widen as the damping gets stiffer -- that is the whole point of treating
    it implicitly."""
    rows = []
    for dmp in damps:
        e = damped_run("Euler", dmp)
        f = damped_run("implicitfast", dmp)
        diff = float(np.linalg.norm(e - f))
        rows.append({"damping": dmp, "euler_qpos": e.tolist(),
                     "implicitfast_qpos": f.tolist(),
                     "difference": diff,
                     "identical": bool(np.array_equal(e, f))})
    return rows


# --------------------------------------------------------------------------
# HYPOTHESIS REFUTED, and the real answer is more useful.
#
# I predicted joint damping would separate `implicitfast` from `Euler`. It does
# not: they stay BIT-IDENTICAL at damping 0, 0.01, 1 and 50. Two controls ruled
# out the boring explanations -- damping changes the trajectory by 1.58 rad, and
# m.opt.integrator really does read mjINT_IMPLICITFAST.
#
# The reason is that MuJoCo's Euler ALREADY integrates joint damping
# implicitly. Damping was never a discriminating variable.
#
# What actually separates them is velocity-dependent forces Euler does not
# special-case: fluid drag, and -- the one that matters for robots -- VELOCITY
# ACTUATORS, which is what a joint PD controller's derivative term is.
# --------------------------------------------------------------------------

VEL_ACT = """
<mujoco>
  <option timestep="{dt}" gravity="0 0 -9.81" integrator="{integ}"/>
  <worldbody>
    <body pos="0 0 1">
      <joint name="a" type="hinge" axis="0 1 0"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.02" mass="1"/>
      <body pos="0 0 -0.3">
        <joint name="b" type="hinge" axis="0 1 0"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.02" mass="1"/>
      </body>
    </body>
  </worldbody>
  <actuator><velocity joint="a" kv="{kv}"/><velocity joint="b" kv="{kv}"/></actuator>
</mujoco>
"""


def velocity_actuator_run(integ, kv, dt=0.005, t_end=2.0, vel_limit=1e3):
    """
    CHECKING isfinite() IS NOT A STABILITY TEST.

    First version of this function judged stability with np.isfinite, and
    reported Euler as STABLE at kv=500 after it had failed at kv=20, 50 and
    100 -- a non-monotonic result that made no sense.

    MuJoCo detects a diverged step (mjWARN_BADQACC, the "Nan, Inf or huge
    value in QACC" warning) and RESETS the state to zero. Euler at kv=500
    reached |qvel| = 3.45e5 by step 3, got reset, and then sat at exactly
    zero for the remaining 397 steps -- perfectly finite, and perfectly
    meaningless. The isfinite check was measuring MuJoCo's recovery, not the
    integrator's stability.

    Two signals are needed instead: the PEAK velocity ever reached, and the
    reset signature (an exact-zero state that the system never re-excites).
    """
    m = mujoco.MjModel.from_xml_string(VEL_ACT.format(dt=dt, integ=integ, kv=kv))
    d = mujoco.MjData(m)
    d.qpos[:2] = Q0
    mujoco.mj_forward(m, d)
    peak_v = 0.0
    reset_seen = False
    for _ in range(int(round(t_end / dt))):
        mujoco.mj_step(m, d)
        if np.all(np.isfinite(d.qvel)):
            peak_v = max(peak_v, float(np.abs(d.qvel).max()))
        else:
            peak_v = float("inf")
            break
        # exact zeros in BOTH position and velocity is the reset fingerprint;
        # a real pendulum passes through qvel=0 but never with qpos=0 too
        if np.all(d.qpos[:2] == 0.0) and np.all(d.qvel[:2] == 0.0):
            reset_seen = True
            break
    unstable = bool(reset_seen or not np.isfinite(peak_v) or peak_v > vel_limit)
    return {"integrator": integ, "kv": kv, "dt": dt,
            "unstable": unstable,
            "peak_qvel": peak_v if np.isfinite(peak_v) else None,
            "autoreset_detected": reset_seen,
            "qpos": d.qpos[:2].tolist()}


def gain_stability_threshold(kvs=(1, 5, 10, 20, 50, 100, 500),
                             integs=("Euler", "implicitfast", "implicit", "RK4")):
    """At what derivative gain does each integrator give up?

    This is the practical form of the question: a joint PD controller's kv is
    set by the control engineer, not the sim engineer, and 'your gains are too
    high' is the wrong answer when a one-word integrator change fixes it.
    """
    rows = []
    for integ in integs:
        first_bad = None
        for kv in kvs:
            r = velocity_actuator_run(integ, kv)
            rows.append(r)
            if r["unstable"] and first_bad is None:
                first_bad = kv
        rows.append({"integrator": integ, "summary": True,
                     "first_unstable_kv": first_bad,
                     "max_stable_kv": max([k for k in kvs if first_bad is None or k < first_bad],
                                          default=None)})
    return rows


if __name__ == "__main__":
    ref = reference()
    dts = [2e-3, 1e-3, 5e-4, 2.5e-4, 1.25e-4]
    out = {"reference_qpos": ref.tolist(), "t_end": T_END, "order": [], "energy": []}

    print("observed order of accuracy  (global error vs dt, log-log slope)\n")
    print(f"  {'integrator':<14} {'theory':>7} {'observed':>9}   verdict")
    for integ in ("Euler", "implicit", "implicitfast", "RK4"):
        r = order_of_accuracy(integ, dts, ref)
        out["order"].append(r)
        th = THEORY[integ]; ob = r["observed_order"]
        ok = "matches" if ob and abs(ob - th) < 0.5 else "MISMATCH"
        print(f"  {integ:<14} {th:>7} {ob if ob else 'n/a':>9}   {ok}")

    print("\nenergy drift on a conservative system (5 s, dt=1e-3)\n")
    print(f"  {'integrator':<14} {'rel drift/s':>13} {'max |rel|':>12} {'steps/s':>10}")
    for integ in ("Euler", "implicit", "implicitfast", "RK4"):
        r = energy_drift(integ)
        if r:
            out["energy"].append(r)
            print(f"  {integ:<14} {r['drift_per_s']:>13.3e} "
                  f"{r['rel_drift_max_abs']:>12.3e} {r['steps_per_s']:>10.1f}")

    out["implicitfast_vs_euler"] = implicitfast_vs_euler()
    out["gain_stability"] = gain_stability_threshold()
    json.dump(out, open(os.path.join(HERE, "integrators.json"), "w"), indent=2)
    print("\nwrote model/integrators.json")
