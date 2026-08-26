"""Determinism: when is a simulation reproducible, and for how long?

JD: "validate simulation fidelity" / "debug complex simulation issues."

"My RL run isn't reproducible" is one of the most common robotics-sim bug
reports, and it is usually not a bug. Three separate questions get conflated:

  1. Is a repeated run BIT-IDENTICAL?          (determinism)
  2. Does an UNRELATED change perturb it?      (coupling / island ordering)
  3. How fast does a tiny perturbation grow?   (chaos horizon)

Only (1) and (2) are engineering choices. (3) is physics, and it bounds how
much reproducibility is even worth chasing.
"""
import json, os
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))

PILE = """
<mujoco>
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom type="plane" size="5 5 0.1"/>
    {bodies}
    {extra}
  </worldbody>
</mujoco>
"""


def pile(n=12, extra=""):
    bodies = "".join(
        f'<body pos="{(i%4)*0.09-0.13:.4f} {((i//4)%4)*0.09-0.13:.4f} {0.06+(i//16)*0.1:.4f}">'
        f'<freejoint/><geom type="box" size="0.04 0.04 0.04" mass="0.3"/></body>'
        for i in range(n))
    return mujoco.MjModel.from_xml_string(PILE.format(bodies=bodies, extra=extra))


def run(m, steps=1500, perturb=0.0):
    d = mujoco.MjData(m)
    if perturb:
        d.qpos[0] += perturb
    mujoco.mj_forward(m, d)
    traj = []
    for _ in range(steps):
        mujoco.mj_step(m, d)
        traj.append(d.qpos[:7].copy())
    return np.array(traj)


def q1_repeat_runs_bit_identical(trials=5):
    m = pile()
    ref = run(m)
    diffs = []
    for _ in range(trials - 1):
        diffs.append(float(np.abs(run(m) - ref).max()))
    return {"trials": trials, "max_abs_diff": max(diffs),
            "bit_identical": max(diffs) == 0.0}


def q1b_fresh_model_object():
    """Does re-PARSING the same XML give the same answer? (It should, but this
    is where lazily-cached broadphase state would show up.)"""
    a = run(pile())
    b = run(pile())
    return {"max_abs_diff": float(np.abs(a - b).max()),
            "bit_identical": bool(np.array_equal(a, b))}


def q2_unrelated_body_perturbs_the_scene():
    """Add a box across the room that never touches anything. Does body 0's
    trajectory change? If yes, contact/constraint ORDERING is coupling
    nominally independent objects -- the classic 'I only added a prop and my
    regression test broke' failure."""
    ref = run(pile())
    far = '<body pos="3.0 3.0 0.06"><freejoint/><geom type="box" size="0.04 0.04 0.04" mass="0.3"/></body>'
    alt = run(pile(extra=far))
    return {"max_abs_diff": float(np.abs(alt - ref).max()),
            "unaffected": bool(np.array_equal(alt, ref))}


def q3_chaos_horizon(perturb=None, steps=1500, dt=0.002):
    """One-ULP nudge to a single coordinate; track the divergence envelope.

    Reports the time at which the trajectories separate by 1 mm and by 1 cm.
    Beyond that horizon, 'reproducible' requires bit-exactness -- matching to
    float tolerance is impossible in principle, not through sloppiness."""
    m = pile()
    if perturb is None:
        perturb = np.spacing(0.0) if False else np.nextafter(0.0, 1.0)
    # a true 1-ULP nudge relative to the coordinate's own magnitude
    base = run(m)[0][0]
    perturb = np.nextafter(abs(base) + 1.0, 2.0) - (abs(base) + 1.0)
    ref = run(m, steps=steps)
    alt = run(m, steps=steps, perturb=perturb)
    sep = np.linalg.norm(alt[:, :3] - ref[:, :3], axis=1)

    def first_cross(thresh):
        idx = np.argmax(sep > thresh)
        return None if sep.max() <= thresh else round(float(idx * dt), 4)

    return {"perturbation_m": float(perturb),
            "t_reach_1um_s": first_cross(1e-6),
            "t_reach_1mm_s": first_cross(1e-3),
            "t_reach_1cm_s": first_cross(1e-2),
            "final_separation_m": float(sep[-1]),
            "growth_factor": float(sep[-1] / perturb) if perturb else None}


# --------------------------------------------------------------------------
# BAD EXPERIMENT DESIGN, then the fix.
#
# q3_chaos_horizon above reported growth_factor == 1.000 and a final
# separation exactly equal to the input perturbation. That is not "MuJoCo is
# so stable there is no chaos" -- it is the wrong scene. A pile of boxes
# dropped on a plane DISSIPATES: friction and inelastic contact drive it to a
# fixed point, so it is contractive, and perturbations shrink or ride along
# unchanged. To measure a chaos horizon you need a system that stays
# sensitive. Two are used below: one smooth, one contact-driven.
# --------------------------------------------------------------------------

DOUBLE_PENDULUM = """
<mujoco>
  <option timestep="0.0005" gravity="0 0 -9.81" integrator="RK4"/>
  <worldbody>
    <body pos="0 0 1">
      <joint name="a" type="hinge" axis="0 1 0"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.02" mass="1"/>
      <body pos="0 0 -0.3">
        <joint name="b" type="hinge" axis="0 1 0"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.02" mass="1"/>
        <site name="tip" pos="0 0 -0.3" size="0.01"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""

INCLINE = """
<mujoco>
  <option timestep="0.001" gravity="0 0 -9.81"/>
  <worldbody>
    <geom type="plane" size="8 8 0.1" euler="0 20 0" friction="0.4 0.005 0.0001"/>
    <body pos="0 0 1.2">
      <freejoint/>
      <geom type="box" size="0.05 0.03 0.02" mass="0.5"
            solref="0.004 0.2" friction="0.4 0.005 0.0001"/>
    </body>
  </worldbody>
</mujoco>
"""


def _diverge(xml, steps, dt, perturb_idx, q0=None, track="site"):
    m = mujoco.MjModel.from_xml_string(xml)

    def go(eps):
        d = mujoco.MjData(m)
        if q0 is not None:
            d.qpos[:len(q0)] = q0
        d.qpos[perturb_idx] += eps
        mujoco.mj_forward(m, d)
        out = []
        sid = 0 if m.nsite else None
        for _ in range(steps):
            mujoco.mj_step(m, d)
            out.append(d.site_xpos[sid].copy() if sid is not None else d.qpos[:3].copy())
        return np.array(out)

    ref = go(0.0)
    # BUG FOUND: `eps = nextafter(1.0,2.0)-1.0` is 1 ULP at magnitude 1.0. The
    # double pendulum starts at qpos[0]=2.0, whose ULP is TWICE that, so
    # `qpos[0] += eps` rounded straight back to 2.0 and the perturbation never
    # happened. The runs were bit-identical and the "growth factor" was the
    # 1e-18 clamp below. A ULP is relative -- size it against the coordinate
    # you are actually perturbing.
    q_ref = float(q0[perturb_idx]) if q0 is not None else 0.0
    # SECOND rounding trap: when the coordinate is 0.0, `nextafter(0.0, 1.0)`
    # is 4.94e-324 -- the smallest DENORMAL, not a meaningful ULP. Denormal
    # arithmetic is not representative and the growth figure it produced
    # (2e305x) was nonsense. Fall back to 1 ULP at unit magnitude instead.
    eps = (np.nextafter(q_ref, np.inf) - q_ref) if q_ref else (np.nextafter(1.0, 2.0) - 1.0)
    if q_ref and (q_ref + eps) == q_ref:
        raise AssertionError("perturbation vanished into rounding")
    alt = go(eps)
    sep = np.linalg.norm(alt - ref, axis=1)
    sep = np.maximum(sep, 1e-18)                # keep the log finite

    def first_cross(t):
        return round(float(np.argmax(sep > t) * dt), 4) if sep.max() > t else None

    # Lyapunov exponent from the exponential-growth stretch, before saturation
    hi = int(np.argmax(sep > 1e-3)) or len(sep)
    lo = max(int(hi * 0.15), 5)
    lam = None
    if hi > lo + 10:
        t = np.arange(lo, hi) * dt
        lam = float(np.polyfit(t, np.log(sep[lo:hi]), 1)[0])

    return {"perturbation": float(eps),
            "t_reach_1um_s": first_cross(1e-6),
            "t_reach_1mm_s": first_cross(1e-3),
            "t_reach_1cm_s": first_cross(1e-2),
            "final_separation_m": float(sep[-1]),
            "growth_factor": float(sep[-1] / eps),
            "lyapunov_exponent_per_s": round(lam, 3) if lam else None,
            "e_folding_time_s": round(1.0 / lam, 4) if lam and lam > 0 else None}


def q3_chaos_smooth():
    """Double pendulum: textbook chaos, NO contact involved. Proves the
    divergence is physics, not a contact-solver artefact."""
    return _diverge(DOUBLE_PENDULUM, steps=20000, dt=0.0005,
                    perturb_idx=0, q0=[2.0, 1.0])


def q3_chaos_smooth_seeded(eps=1e-12):
    """Same pendulum with a finite, deliberately-chosen seed. A true 1-ULP
    nudge needs ~40 e-foldings to reach millimetres, which outruns the
    integrator's own accuracy; 1e-12 rad divergence is measurable inside a few
    seconds and gives a clean exponent to fit."""
    m = mujoco.MjModel.from_xml_string(DOUBLE_PENDULUM)

    def go(e):
        d = mujoco.MjData(m)
        d.qpos[:2] = [2.0, 1.0]
        d.qpos[0] += e
        mujoco.mj_forward(m, d)
        return np.array([(mujoco.mj_step(m, d), d.site_xpos[0].copy())[1]
                         for _ in range(20000)])

    ref, alt = go(0.0), go(eps)
    sep = np.maximum(np.linalg.norm(alt - ref, axis=1), 1e-18)
    dt = 0.0005
    hi = int(np.argmax(sep > 1e-3)) or len(sep)
    lo = max(int(hi * 0.15), 5)
    t = np.arange(lo, hi) * dt
    lam = float(np.polyfit(t, np.log(sep[lo:hi]), 1)[0])
    return {"perturbation": eps,
            "t_reach_1mm_s": round(float(np.argmax(sep > 1e-3) * dt), 4) if sep.max() > 1e-3 else None,
            "t_reach_1cm_s": round(float(np.argmax(sep > 1e-2) * dt), 4) if sep.max() > 1e-2 else None,
            "final_separation_m": float(sep[-1]),
            "growth_factor": float(sep[-1] / eps),
            "lyapunov_exponent_per_s": round(lam, 3),
            "e_folding_time_s": round(1.0 / lam, 4) if lam > 0 else None}


def q3_chaos_contact():
    """A box tumbling down a 20-degree incline: chaos through contact, which
    is the case that actually bites robotics sim."""
    return _diverge(INCLINE, steps=6000, dt=0.001, perturb_idx=0)



def q3_chaos_contact_seeded(eps=1e-12, steps=6000, dt=0.001):
    """The incline with the same finite seed as the pendulum, so the two
    exponents are directly comparable."""
    m = mujoco.MjModel.from_xml_string(INCLINE)

    def go(e):
        d = mujoco.MjData(m)
        d.qpos[0] += e
        mujoco.mj_forward(m, d)
        return np.array([(mujoco.mj_step(m, d), d.qpos[:3].copy())[1]
                         for _ in range(steps)])

    ref, alt = go(0.0), go(eps)
    sep = np.maximum(np.linalg.norm(alt - ref, axis=1), 1e-18)
    hi = int(np.argmax(sep > 1e-3)) or len(sep)
    lo = max(int(hi * 0.15), 5)
    t = np.arange(lo, hi) * dt
    lam = float(np.polyfit(t, np.log(sep[lo:hi]), 1)[0])
    return {"perturbation": eps,
            "t_reach_1mm_s": round(float(np.argmax(sep > 1e-3) * dt), 4) if sep.max() > 1e-3 else None,
            "final_separation_m": float(sep[-1]),
            "growth_factor": float(sep[-1] / eps),
            "lyapunov_exponent_per_s": round(lam, 3),
            "e_folding_time_s": round(1.0 / lam, 4) if lam > 0 else None}


def predict_ulp_horizon(lam, eps, target=1e-3):
    """Cross-check: the exponent measured from ONE seed should predict the
    time-to-target for a DIFFERENT seed. If it does, the exponent is real."""
    import math
    return round(math.log(target / eps) / lam, 3)


if __name__ == "__main__":
    out = {}
    print("Q1  repeated runs, same MjModel object")
    out["repeat_runs"] = r = q1_repeat_runs_bit_identical()
    print(f"    max |diff| over {r['trials']} runs : {r['max_abs_diff']:.3e}"
          f"   bit-identical: {r['bit_identical']}")

    print("\nQ1b re-parsed model, same XML")
    out["fresh_model"] = r = q1b_fresh_model_object()
    print(f"    max |diff| : {r['max_abs_diff']:.3e}   bit-identical: {r['bit_identical']}")

    print("\nQ2  add an untouched box 3 m away")
    out["unrelated_body"] = r = q2_unrelated_body_perturbs_the_scene()
    print(f"    max |diff| on body 0 : {r['max_abs_diff']:.3e}"
          f"   unaffected: {r['unaffected']}")

    print("\nQ3  one-ULP perturbation, divergence horizon")
    out["chaos"] = r = q3_chaos_horizon()
    print(f"    perturbation      : {r['perturbation_m']:.3e} m")
    for k, lbl in (("t_reach_1um_s", "1 um"), ("t_reach_1mm_s", "1 mm"),
                   ("t_reach_1cm_s", "1 cm")):
        v = r[k]
        print(f"    separation hits {lbl:<5}: " + (f"{v} s" if v is not None else "never (in 3 s)"))
    print(f"    final separation  : {r['final_separation_m']:.4e} m")
    if r["growth_factor"]:
        print(f"    growth factor     : {r['growth_factor']:.3e}x")

    out["chaos_bad_design_note"] = (
        "the pile-of-boxes scene is dissipative and settles to a fixed point, "
        "so it cannot show a chaos horizon; growth_factor came out exactly "
        "1.000. Replaced with one smooth and one contact-driven system.")
    out["chaos_smooth_1ulp"] = q3_chaos_smooth()
    out["chaos_smooth_seeded_1e-12"] = q3_chaos_smooth_seeded()
    out["chaos_contact_1ulp"] = q3_chaos_contact()
    out["chaos_contact_seeded_1e-12"] = q3_chaos_contact_seeded()
    lam = out["chaos_smooth_1ulp"]["lyapunov_exponent_per_s"]
    out["predictive_check"] = {
        "predicted_1mm_s": predict_ulp_horizon(lam, 1e-12),
        "measured_1mm_s": out["chaos_smooth_seeded_1e-12"]["t_reach_1mm_s"]}
    json.dump(out, open(os.path.join(HERE, "determinism.json"), "w"), indent=2)
    print("\nwrote model/determinism.json")
