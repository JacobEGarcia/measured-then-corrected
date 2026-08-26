"""Minimum grip force for a two-finger pinch grasp, against closed form.

JD: "Background in legged locomotion, MANIPULATION, or multi-body systems."

A parallel-jaw grasp on a smooth block holds when friction at the two contacts
carries the weight:

    2 * mu * F  >=  m * g        ->        F_min = m*g / (2*mu)

mu and m are inputs; F_min is an emergent property of the dynamics. Sweeping
the grip force and finding where the object stops falling recovers F_min
without ever asking the engine for it -- the same closed-loop structure as the
friction-cone and gravity-recovery studies elsewhere in this repo.

PREDICTION, before running: measured F_min lands slightly ABOVE theory.
Coulomb's law is the limit of static friction, so the analytic value is exactly
marginal -- it holds with zero margin, and any numerical softness pushes the
first genuinely-holding force one step past it.
"""
import json, os
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
G = 9.81

GRIPPER = """
<mujoco model="pinch">
  <option timestep="0.0005" gravity="0 0 -9.81" cone="elliptic"
          integrator="implicitfast"/>
  <default>
    <geom friction="{mu} 0.005 0.0001" solref="0.004 1"/>
  </default>
  <worldbody>
    <!-- two fingers on slides, squeezing inward along x -->
    <body name="fL" pos="-0.05 0 0.5">
      <joint name="jL" type="slide" axis="1 0 0" damping="12"/>
      <geom type="box" size="0.01 0.03 0.04" mass="0.2"/>
    </body>
    <body name="fR" pos="0.05 0 0.5">
      <joint name="jR" type="slide" axis="-1 0 0" damping="12"/>
      <geom type="box" size="0.01 0.03 0.04" mass="0.2"/>
    </body>
    <!-- the object, free to fall if the grasp is too weak -->
    <body name="obj" pos="0 0 0.5">
      <freejoint/>
      <geom type="box" size="0.028 0.028 0.028" mass="{m}"/>
    </body>
  </worldbody>
  <actuator>
    <!-- constant inward force on each finger: this IS the grip force -->
    <motor joint="jL" gear="1" ctrllimited="false"/>
    <motor joint="jR" gear="1" ctrllimited="false"/>
  </actuator>
</mujoco>
"""


def holds(force, mu, mass, sim_time=1.5, drop_thresh=0.005):
    """Squeeze with `force` newtons per finger; does the object stay put?"""
    m = mujoco.MjModel.from_xml_string(GRIPPER.format(mu=mu, m=mass))
    d = mujoco.MjData(m)
    d.ctrl[:] = force
    # let the fingers close and the contact settle before judging
    for _ in range(int(0.4 / m.opt.timestep)):
        mujoco.mj_step(m, d)
    z_start = float(d.xpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "obj")][2])
    for _ in range(int(sim_time / m.opt.timestep)):
        mujoco.mj_step(m, d)
    z_end = float(d.xpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "obj")][2])
    drop = z_start - z_end
    return {"force_N": force, "mu": mu, "mass": mass,
            "drop_m": round(drop, 6), "held": bool(drop < drop_thresh)}


def theory(mu, mass):
    return mass * G / (2.0 * mu)


def find_min_force(mu, mass, lo=0.1, hi=200.0, tol=0.02):
    """Bisect for the smallest force that holds. Bisection assumes the
    predicate is monotone; `verify_monotone` below checks that rather than
    trusting it."""
    if not holds(hi, mu, mass)["held"]:
        return None
    for _ in range(40):
        if (hi - lo) / hi < tol:
            break
        mid = 0.5 * (lo + hi)
        if holds(mid, mu, mass)["held"]:
            hi = mid
        else:
            lo = mid
    return hi


def verify_monotone(mu, mass, forces):
    """Bisection is only valid if 'holds' is monotone in force. Squeezing
    harder should never make a grasp WORSE -- but a stiff contact can eject
    the object, so this is worth checking rather than assuming."""
    rows = [holds(f, mu, mass) for f in forces]
    flips = sum(1 for a, b in zip(rows, rows[1:]) if a["held"] and not b["held"])
    return {"rows": rows, "monotone": flips == 0, "held_then_failed": flips}


if __name__ == "__main__":
    out = {"g": G, "cases": []}
    print(f"  {'mu':>5} {'mass':>6} {'theory N':>10} {'measured N':>12} "
          f"{'error %':>9}")
    for mu, mass in ((0.4, 0.5), (0.8, 0.5), (0.4, 1.0), (1.0, 1.0)):
        th = theory(mu, mass)
        meas = find_min_force(mu, mass)
        if meas is None:
            print(f"  {mu:>5} {mass:>6} {th:>10.3f} {'never held':>12}")
            out["cases"].append({"mu": mu, "mass": mass, "theory_N": round(th, 4),
                                 "measured_N": None})
            continue
        err = (meas - th) / th * 100.0
        out["cases"].append({"mu": mu, "mass": mass, "theory_N": round(th, 4),
                             "measured_N": round(meas, 4),
                             "error_pct": round(err, 2)})
        print(f"  {mu:>5} {mass:>6} {th:>10.3f} {meas:>12.3f} {err:>+8.1f}%")

    ok = [c for c in out["cases"] if c["measured_N"] is not None]
    if ok:
        errs = [c["error_pct"] for c in ok]
        out["summary"] = {"mean_error_pct": round(float(np.mean(errs)), 2),
                          "max_abs_error_pct": round(float(np.max(np.abs(errs))), 2),
                          "all_above_theory": all(e > 0 for e in errs)}
        print(f"\n  mean error {out['summary']['mean_error_pct']:+.1f}%, "
              f"max |error| {out['summary']['max_abs_error_pct']:.1f}%")
        print(f"  every measurement above theory: {out['summary']['all_above_theory']}")

    print("\n  monotonicity check (squeezing harder must not make it worse)")
    out["monotone"] = verify_monotone(0.4, 0.5, [2, 5, 10, 20, 40, 80, 160])
    print(f"    monotone: {out['monotone']['monotone']}  "
          f"(held-then-failed transitions: {out['monotone']['held_then_failed']})")

    json.dump(out, open(os.path.join(HERE, "grasp.json"), "w"), indent=2)
    print("\nwrote model/grasp.json")



# --------------------------------------------------------------------------
# PREDICTION CONFIRMED, including its direction.
#
#     mu   mass   theory N   measured N    error
#    0.4    0.5      6.131        6.444    +5.1%
#    0.8    0.5      3.066        3.516   +14.7%
#    0.4    1.0     12.262       12.594    +2.7%
#    1.0    1.0      4.905        5.273    +7.5%
#
# All four land ABOVE the closed form, mean +7.5%. That is the right sign:
# F = m*g/(2*mu) is the MARGINAL holding force, the exact limit of static
# friction, so it holds with zero margin. Any numerical softness -- finite
# contact stiffness, a settling transient, discrete stepping -- pushes the
# first genuinely-holding force a little past it. A measurement BELOW theory
# would have been the alarming result, since nothing in the model should let a
# grasp beat Coulomb.
#
# The spread (2.7% to 14.7%) tracks the absolute force: the weakest grasp
# (3.07 N) has the largest relative error, which is what a roughly constant
# additive offset looks like when expressed as a percentage.
# --------------------------------------------------------------------------


def offset_is_additive_not_multiplicative():
    """Test the explanation above rather than just asserting it. If the excess
    is a roughly constant force offset, absolute error should be far more
    consistent than relative error."""
    rows = []
    for mu, mass in ((0.4, 0.5), (0.8, 0.5), (0.4, 1.0), (1.0, 1.0)):
        th = theory(mu, mass)
        meas = find_min_force(mu, mass)
        if meas is None:
            continue
        rows.append({"mu": mu, "mass": mass, "theory_N": round(th, 4),
                     "measured_N": round(meas, 4),
                     "abs_excess_N": round(meas - th, 4),
                     "rel_excess_pct": round((meas - th) / th * 100, 2)})
    absr = [r["abs_excess_N"] for r in rows]
    relr = [r["rel_excess_pct"] for r in rows]
    cv = lambda v: float(np.std(v) / abs(np.mean(v))) if np.mean(v) else float("inf")
    return {"rows": rows,
            "abs_excess_cv": round(cv(absr), 3),
            "rel_excess_cv": round(cv(relr), 3),
            "additive_is_tighter": bool(cv(absr) < cv(relr))}
