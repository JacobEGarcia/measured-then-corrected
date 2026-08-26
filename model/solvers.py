"""Newton vs CG vs PGS: which solver, and does the choice actually matter?

JD: "optimize simulation performance" / "debug complex simulation issues."

The stability study found that raising ITERATIONS did nothing for a hard mass
ratio. That leaves the obvious follow-up unanswered: does changing the SOLVER
ALGORITHM do what more iterations of the same algorithm could not?

MuJoCo offers three:
  Newton  -- second order, few iterations, expensive per iteration (default)
  CG      -- conjugate gradient, first order
  PGS     -- projected Gauss-Seidel, the classic game-physics choice

Measured on the same two problems used elsewhere in this repo, so the numbers
are comparable: an easy equal-mass tower, and the 1000:1 stack that defeats
iteration count.
"""
import json, os, time
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
SOLVERS = ("Newton", "CG", "PGS")

TOWER = """
<mujoco>
  <option timestep="{dt}" gravity="0 0 -9.81" solver="{solver}" iterations="{it}"/>
  <worldbody>
    <geom type="plane" size="5 5 0.1"/>
    {bodies}
  </worldbody>
</mujoco>
"""

RATIO = """
<mujoco>
  <option timestep="{dt}" gravity="0 0 -9.81" solver="{solver}" iterations="{it}"/>
  <worldbody>
    <geom type="plane" size="5 5 0.1"/>
    <body name="light" pos="0 0 0.05"><freejoint/>
      <geom type="box" size="0.05 0.05 0.05" mass="1"/></body>
    <body name="heavy" pos="0 0 0.151"><freejoint/>
      <geom type="box" size="0.05 0.05 0.05" mass="{heavy}"/></body>
  </worldbody>
</mujoco>
"""


def tower(solver, it, n=8, dt=0.002):
    bodies = "".join(
        f'<body pos="0 0 {0.05+i*0.101:.4f}"><freejoint/>'
        f'<geom type="box" size="0.05 0.05 0.05" mass="5"/></body>' for i in range(n))
    return mujoco.MjModel.from_xml_string(
        TOWER.format(dt=dt, solver=solver, it=it, bodies=bodies))


def bench(m, sim_time=2.0, reps=3):
    steps = int(sim_time / m.opt.timestep)
    best = float("inf")
    for _ in range(reps):
        d = mujoco.MjData(m)
        t0 = time.perf_counter()
        for _ in range(steps):
            mujoco.mj_step(m, d)
        best = min(best, time.perf_counter() - t0)
    d = mujoco.MjData(m)
    for _ in range(steps):
        mujoco.mj_step(m, d)
    return best, steps, d


def easy_problem():
    rows = []
    for s in SOLVERS:
        m = tower(s, 100)
        wall, steps, d = bench(m)
        z = np.sort(d.qpos[2::7][:8])
        gaps = np.diff(z)
        pen_mm = float(max(0.0, 0.101 - gaps.min()) * 1000)
        rows.append({"solver": s, "steps_per_s": round(steps / wall, 1),
                     "penetration_mm": round(pen_mm, 4),
                     "stable": bool(np.all(np.isfinite(d.qpos)) and z.min() > 0.02)})
    return rows


def hard_problem(heavy=1000.0, dt=0.002):
    """The 1000:1 stack. Iteration count could not fix this; can a different
    algorithm?"""
    rows = []
    for s in SOLVERS:
        for it in (1, 100):
            m = mujoco.MjModel.from_xml_string(
                RATIO.format(dt=dt, solver=s, it=it, heavy=heavy))
            wall, steps, d = bench(m)
            zl, zh = float(d.qpos[2]), float(d.qpos[9])
            fin = bool(np.all(np.isfinite(d.qpos)))
            rows.append({"solver": s, "iterations": it,
                         "steps_per_s": round(steps / wall, 1),
                         "squash_mm": round((0.101 - (zh - zl)) * 1000, 3) if fin else None,
                         "light_sank_mm": round((0.05 - zl) * 1000, 3) if fin else None,
                         "finite": fin})
    return rows


if __name__ == "__main__":
    out = {}
    print("EASY problem -- 8-box equal-mass tower\n")
    print(f"  {'solver':<8} {'steps/s':>10} {'penetration mm':>16} {'stable':>8}")
    out["easy"] = easy_problem()
    for r in out["easy"]:
        print(f"  {r['solver']:<8} {r['steps_per_s']:>10.1f} "
              f"{r['penetration_mm']:>16.4f} {str(r['stable']):>8}")

    print("\nHARD problem -- 1000:1 mass ratio (iteration count cannot fix it)\n")
    print(f"  {'solver':<8} {'iters':>6} {'steps/s':>10} {'squash mm':>11} {'sank mm':>9}")
    out["hard"] = hard_problem()
    for r in out["hard"]:
        sq = f"{r['squash_mm']:.3f}" if r["squash_mm"] is not None else "n/a"
        sk = f"{r['light_sank_mm']:.3f}" if r["light_sank_mm"] is not None else "n/a"
        print(f"  {r['solver']:<8} {r['iterations']:>6} {r['steps_per_s']:>10.1f} "
              f"{sq:>11} {sk:>9}")

    sq = {(r["solver"], r["iterations"]): r["squash_mm"] for r in out["hard"]}
    best = min((v for v in sq.values() if v is not None), default=None)
    worst = max((v for v in sq.values() if v is not None), default=None)
    out["hard_summary"] = {"best_squash_mm": best, "worst_squash_mm": worst,
                           "spread_mm": round(worst - best, 4) if best is not None else None}
    print(f"\n  squash across ALL solver x iteration combinations: "
          f"{best:.3f} to {worst:.3f} mm  (spread {worst-best:.3f} mm)")

    json.dump(out, open(os.path.join(HERE, "solvers.json"), "w"), indent=2)
    print("\nwrote model/solvers.json")


# --------------------------------------------------------------------------
# READING THE HARD-PROBLEM RESULT.
#
# No solver fixes a 1000:1 mass ratio. What changes is WHICH body fails:
#
#   Newton   squash  50.2 mm, light body SANK 49.2 mm
#            -- the light box is driven almost its full half-height into the
#               floor; the stack geometry survives, the floor contact does not
#
#   CG, PGS  squash 101.0 mm, light body sank ~0.1 mm
#            -- the light box holds its ground and the heavy box passes
#               ENTIRELY through it (101 mm of squash on a 101 mm gap means the
#               two centres coincide)
#
# Two different wrong answers, neither better. Combined with the iteration
# sweep in stability_frontier.py, the conclusion is that a bad mass ratio is
# not a solver-tuning problem at all -- not iterations, not algorithm. It has
# to be fixed in the MODEL (rescale masses, or replace the stack with a joint).
# --------------------------------------------------------------------------


def failure_modes(rows=None):
    rows = rows or hard_problem()
    out = {}
    for r in rows:
        if r["squash_mm"] is None:
            continue
        key = f"{r['solver']}@{r['iterations']}"
        # which body gave way: the light one sinking, or full interpenetration
        out[key] = {
            "squash_mm": r["squash_mm"],
            "light_sank_mm": r["light_sank_mm"],
            "mode": ("light body driven into the floor"
                     if r["light_sank_mm"] > 10.0
                     else "heavy body passed through the light one")}
    return out
