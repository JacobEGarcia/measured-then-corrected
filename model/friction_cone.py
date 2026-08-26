"""Pyramidal vs elliptic friction cones: the anisotropy you get for free speed.

JD: "Background in legged locomotion, manipulation, or multi-body systems" /
"optimize simulation performance."

Coulomb friction says the tangential force lies inside a CIRCLE of radius
mu*Fn. Solving that exactly is a second-order cone constraint. Most engines
offer an approximation: replace the circle with a POLYGON (a pyramid in 3D),
which turns the problem into linear constraints.

I wrote "cheaper option" here before measuring, and that was wrong -- see the
cost result at the bottom of this file. In MuJoCo the pyramid is SLOWER.

The cost of that approximation is anisotropy. A square inscribed in a circle
has more friction available along its diagonals than along its axes, so a box
pushed at 45 degrees behaves differently from one pushed along an axis -- in a
way that has nothing to do with the physics you specified.

This measures the direction error directly: push a box along many headings and
compare the heading it actually slides along against the heading it was pushed.
"""
import json, os, time
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))

SLIDE = """
<mujoco>
  <option timestep="0.001" gravity="0 0 -9.81" cone="{cone}" integrator="implicitfast"/>
  <worldbody>
    <geom type="plane" size="10 10 0.1" friction="{mu} 0.005 0.0001"/>
    <body name="puck" pos="0 0 0.05">
      <freejoint/>
      <geom type="box" size="0.05 0.05 0.05" mass="1"
            friction="{mu} 0.005 0.0001"/>
    </body>
  </worldbody>
</mujoco>
"""


def slide_heading(cone, heading_deg, mu=0.5, v0=2.0, t_end=1.5):
    """Launch the box across the floor at `heading_deg` and see which way it
    actually goes. With isotropic Coulomb friction the answer must be
    'exactly the way it was launched', for every heading."""
    m = mujoco.MjModel.from_xml_string(SLIDE.format(cone=cone, mu=mu))
    d = mujoco.MjData(m)
    th = np.radians(heading_deg)
    d.qvel[0] = v0 * np.cos(th)
    d.qvel[1] = v0 * np.sin(th)
    mujoco.mj_forward(m, d)
    start = d.qpos[:2].copy()
    n = int(t_end / m.opt.timestep)
    for _ in range(n):
        mujoco.mj_step(m, d)
    disp = d.qpos[:2] - start
    travelled = float(np.linalg.norm(disp))
    actual = float(np.degrees(np.arctan2(disp[1], disp[0])))
    err = (actual - heading_deg + 180.0) % 360.0 - 180.0
    return {"cone": cone, "heading_deg": heading_deg,
            "actual_deg": round(actual, 4),
            "direction_error_deg": round(float(err), 4),
            "distance_m": round(travelled, 5)}


def cone_cost(cone, n_bodies=30, steps=3000, reps=3):
    inner = "".join(
        f'<body pos="{(i%6)*0.13-0.32:.3f} {((i//6)%6)*0.13-0.32:.3f} 0.06">'
        f'<freejoint/><geom type="box" size="0.05 0.05 0.05" mass="1" '
        f'friction="0.5 0.005 0.0001"/></body>' for i in range(n_bodies))
    m = mujoco.MjModel.from_xml_string(f"""<mujoco>
      <option timestep="0.002" gravity="0 0 -9.81" cone="{cone}"/>
      <worldbody><geom type="plane" size="10 10 0.1" friction="0.5 0.005 0.0001"/>
      {inner}</worldbody></mujoco>""")
    best = float("inf")
    for _ in range(reps):
        d = mujoco.MjData(m)
        t0 = time.perf_counter()
        for _ in range(steps):
            mujoco.mj_step(m, d)
        best = min(best, time.perf_counter() - t0)
    return {"cone": cone, "steps_per_s": round(steps / best, 1),
            "us_per_step": round(best / steps * 1e6, 3)}


if __name__ == "__main__":
    headings = list(range(0, 91, 5))
    out = {"headings_deg": headings, "sweeps": {}, "cost": []}

    print("direction error: heading the box SLID vs heading it was PUSHED\n")
    print(f"  {'heading':>8} {'pyramidal':>12} {'elliptic':>12}")
    rows = {}
    for cone in ("pyramidal", "elliptic"):
        rows[cone] = [slide_heading(cone, h) for h in headings]
        out["sweeps"][cone] = rows[cone]
    for i, h in enumerate(headings):
        print(f"  {h:>7}d {rows['pyramidal'][i]['direction_error_deg']:>12.4f} "
              f"{rows['elliptic'][i]['direction_error_deg']:>12.4f}")

    for cone in ("pyramidal", "elliptic"):
        e = np.abs([r["direction_error_deg"] for r in rows[cone]])
        worst = headings[int(e.argmax())]
        out[f"{cone}_summary"] = {"max_abs_error_deg": round(float(e.max()), 4),
                                  "mean_abs_error_deg": round(float(e.mean()), 4),
                                  "worst_heading_deg": worst}
        print(f"\n  {cone:<10} max |error| {e.max():.4f} deg at {worst} deg, "
              f"mean {e.mean():.4f} deg")

    print("\ncost of the exact cone")
    for cone in ("pyramidal", "elliptic"):
        c = cone_cost(cone)
        out["cost"].append(c)
        print(f"  {cone:<10} {c['steps_per_s']:>10.1f} steps/s   "
              f"{c['us_per_step']:>8.3f} us/step")

    json.dump(out, open(os.path.join(HERE, "friction_cone.json"), "w"), indent=2)
    print("\nwrote model/friction_cone.json")



# --------------------------------------------------------------------------
# WRONG PREDICTION, corrected by the measurement in this same file.
#
# I described the pyramidal cone as the cheap approximation you trade accuracy
# for. Measured, MuJoCo gives the opposite:
#
#     pyramidal    637.9 steps/s     max direction error 12.76 deg
#     elliptic   1,641.8 steps/s     max direction error  0.71 deg
#
# The exact cone is 2.6x FASTER and 18x more accurate. There is no trade here
# at all -- pyramidal is dominated.
#
# Partial explanation: for the same 120 contacts, pyramidal builds 480
# constraint rows and elliptic 360 (4 vs 3 rows per contact). That is 1.33x
# the rows, which does NOT by itself account for 2.6x the wall-clock, so
# solver conditioning is doing the rest. I have not isolated that part, and
# say so rather than inventing a mechanism.
#
# The "linear constraints are cheaper" intuition comes from LCP-style solvers.
# MuJoCo's convex solver handles the elliptic cone natively, so the intuition
# does not transfer.
# --------------------------------------------------------------------------


def constraint_rows(cone, n_bodies=30, settle=500):
    """Rows in the constraint Jacobian, which is what the solver actually
    pays for -- ncon alone hides the cone's cost."""
    inner = "".join(
        f'<body pos="{(i%6)*0.13-0.32:.3f} {((i//6)%6)*0.13-0.32:.3f} 0.06">'
        f'<freejoint/><geom type="box" size="0.05 0.05 0.05" mass="1" '
        f'friction="0.5 0.005 0.0001"/></body>' for i in range(n_bodies))
    m = mujoco.MjModel.from_xml_string(f"""<mujoco>
      <option timestep="0.002" gravity="0 0 -9.81" cone="{cone}"/>
      <worldbody><geom type="plane" size="10 10 0.1" friction="0.5 0.005 0.0001"/>
      {inner}</worldbody></mujoco>""")
    d = mujoco.MjData(m)
    for _ in range(settle):
        mujoco.mj_step(m, d)
    return {"cone": cone, "nefc": int(d.nefc), "ncon": int(d.ncon),
            "rows_per_contact": round(d.nefc / max(d.ncon, 1), 3)}
