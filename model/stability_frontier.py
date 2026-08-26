"""Where is the fastest STABLE configuration? A dt x solver-iteration sweep.

JD: "optimize simulation performance" / "identify and resolve simulation
performance bottlenecks."

Everyone knows "smaller timestep = more stable = slower". That framing hides
the actual engineering question, which is a Pareto frontier: for a required
accuracy, which (dt, iterations) pair costs the least wall-clock? Halving dt
doubles cost; adding solver iterations costs far less. Whether that trade is
worth taking is a measurement, not a rule of thumb.

Stability here is judged on three separate failure modes, because a sim can be
"not NaN" and still be useless:
  blowup      -- NaN / inf / energy explosion
  sinking     -- objects fall through the floor
  penetration -- objects visibly interpenetrate at rest
"""
import json, os, time
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))

STACK = """
<mujoco>
  <option timestep="{dt}" gravity="0 0 -9.81" iterations="{it}" solver="Newton"/>
  <worldbody>
    <geom name="floor" type="plane" size="5 5 0.1"/>
    {bodies}
  </worldbody>
</mujoco>
"""


def stack(dt, iters, n=6, mass=5.0):
    """A tower: the bottom contact carries n*mass, which is where stiff
    contact problems actually show up."""
    inner = ""
    for i in range(n):
        inner += (f'<body pos="0 0 {0.05 + i*0.101:.4f}"><freejoint/>'
                  f'<geom type="box" size="0.05 0.05 0.05" mass="{mass}"/></body>')
    return mujoco.MjModel.from_xml_string(
        STACK.format(dt=dt, it=iters, bodies=inner))


def evaluate(dt, iters, sim_time=2.0, n=6):
    m = stack(dt, iters, n=n)
    d = mujoco.MjData(m)
    steps = int(sim_time / dt)
    t0 = time.perf_counter()
    for _ in range(steps):
        mujoco.mj_step(m, d)
    wall = time.perf_counter() - t0

    z = d.qpos[2::7][:n]                       # z of each box
    blowup = bool(not np.all(np.isfinite(d.qpos)) or np.abs(d.qpos).max() > 1e3)
    sinking = bool(np.isfinite(z).all() and z.min() < 0.02)
    # at rest the tower should sit at 0.05, 0.151, 0.252 ... ; measure the
    # worst gap-closure between neighbours
    if np.isfinite(z).all():
        gaps = np.diff(np.sort(z))
        penetration_mm = float(max(0.0, 0.101 - gaps.min()) * 1000) if len(gaps) else 0.0
    else:
        penetration_mm = float("inf")

    return {"dt": dt, "iterations": iters,
            "wall_s": round(wall, 4),
            "steps_per_s": round(steps / wall, 1),
            "cost_per_simsec": round(wall / sim_time, 5),
            "blowup": blowup, "sinking": sinking,
            "penetration_mm": round(penetration_mm, 4) if np.isfinite(penetration_mm) else None,
            "stable": bool(not blowup and not sinking and penetration_mm < 5.0)}


if __name__ == "__main__":
    DTS = [0.0005, 0.001, 0.002, 0.004, 0.008, 0.016]
    ITS = [1, 5, 20, 100]
    rows = [evaluate(dt, it) for dt in DTS for it in ITS]

    print(f"  {'dt':>7} {'iters':>6} {'steps/s':>10} {'cost/simsec':>12} "
          f"{'pen mm':>8}  {'verdict':<10}")
    for r in rows:
        v = "BLOWUP" if r["blowup"] else "SINKING" if r["sinking"] else \
            "ok" if r["stable"] else "soft"
        pen = f"{r['penetration_mm']:.3f}" if r["penetration_mm"] is not None else "  n/a"
        print(f"  {r['dt']:>7} {r['iterations']:>6} {r['steps_per_s']:>10.1f} "
              f"{r['cost_per_simsec']:>12.5f} {pen:>8}  {v:<10}")

    stable = [r for r in rows if r["stable"]]
    best = min(stable, key=lambda r: r["cost_per_simsec"]) if stable else None
    out = {"rows": rows, "cheapest_stable": best}

    if best:
        print(f"\n  CHEAPEST STABLE CONFIG: dt={best['dt']} iterations={best['iterations']}")
        print(f"    {best['cost_per_simsec']:.5f} s of wall-clock per simulated second")
        naive = [r for r in stable if r["dt"] == min(r2["dt"] for r2 in stable)]
        if naive:
            n0 = min(naive, key=lambda r: r["cost_per_simsec"])
            print(f"    vs the 'just use a small timestep' choice (dt={n0['dt']}): "
                  f"{n0['cost_per_simsec']/best['cost_per_simsec']:.1f}x cheaper")

    json.dump(out, open(os.path.join(HERE, "stability_frontier.json"), "w"), indent=2)
    print("\nwrote model/stability_frontier.json")


# --------------------------------------------------------------------------
# The first sweep produced no instability at all -- every cell read "ok", so
# there was no frontier to find. A 6-box tower of equal masses is simply not a
# hard contact problem. Two things make it hard, and the sweep needs both:
#
#   larger dt        -- extend past 0.016 until it genuinely breaks
#   MASS RATIO       -- a heavy body resting on a light one is the classic
#                       solver killer: the light body must transmit a force
#                       many times its own weight, and an under-converged
#                       solver lets it squash or sink
#
# The first sweep did confirm something worth keeping, though, and it was not
# what it set out to measure: penetration was IDENTICAL (1.637 mm) for every
# dt from 0.0005 to 0.008, then jumped at dt=0.016. That is the 2*dt clamp
# from the contact study reappearing on its own -- solref's default timeconst
# is 0.02 s, and 2*dt only exceeds it once dt > 0.01.
# --------------------------------------------------------------------------

RATIO_STACK = """
<mujoco>
  <option timestep="{dt}" gravity="0 0 -9.81" iterations="{it}" solver="{solver}"/>
  <worldbody>
    <geom name="floor" type="plane" size="5 5 0.1"/>
    <body name="light" pos="0 0 0.05"><freejoint/>
      <geom type="box" size="0.05 0.05 0.05" mass="{m_light}"/></body>
    <body name="heavy" pos="0 0 0.151"><freejoint/>
      <geom type="box" size="0.05 0.05 0.05" mass="{m_heavy}"/></body>
  </worldbody>
</mujoco>
"""


def evaluate_ratio(dt, iters, ratio, solver="Newton", sim_time=2.0, reps=3):
    """Heavy box on light box. `ratio` is m_heavy / m_light."""
    m = mujoco.MjModel.from_xml_string(RATIO_STACK.format(
        dt=dt, it=iters, solver=solver, m_light=1.0, m_heavy=float(ratio)))
    steps = int(sim_time / dt)
    # time it several times and keep the best -- single runs varied by ~40%
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
    z_light, z_heavy = float(d.qpos[2]), float(d.qpos[9])
    finite = bool(np.all(np.isfinite(d.qpos)))
    blowup = bool(not finite or np.abs(d.qpos).max() > 1e3)
    sinking = bool(finite and z_light < 0.02)
    # ideal rest: light at 0.05, heavy at 0.151
    squash_mm = float((0.101 - (z_heavy - z_light)) * 1000) if finite else None
    return {"dt": dt, "iterations": iters, "mass_ratio": ratio, "solver": solver,
            "steps_per_s": round(steps / best, 1),
            "cost_per_simsec": round(best / sim_time, 5),
            "z_light": round(z_light, 5), "z_heavy": round(z_heavy, 5),
            "squash_mm": round(squash_mm, 3) if squash_mm is not None else None,
            "blowup": blowup, "sinking": sinking,
            "stable": bool(not blowup and not sinking and squash_mm is not None
                           and abs(squash_mm) < 5.0)}


# --------------------------------------------------------------------------
# APPARENT CONTRADICTION with model/contact_tuning.py.
#
# The contact study measured penetration as mass-INDEPENDENT: MuJoCo's solref
# is parameterised in TIME (timeconst, dampratio), and the solver normalises
# by the contact's effective mass, so a heavier box does not sink further.
#
# This sweep shows squash scaling hard with load: 1.2 mm -> 6.0 mm -> 51 mm as
# the mass ratio goes 1 -> 100 -> 10000. Both cannot be unconditionally true.
#
# The reconciliation: mass normalisation uses the effective mass AT THE
# CONTACT. When a box rests directly on the floor, the load IS its own mass,
# the normalisation matches, and penetration is flat. In a stack, the lower
# contact carries the mass of everything above it while its effective mass is
# still that of the light body -- load and normalising mass diverge, and the
# cancellation fails by exactly the mass ratio.
#
# The test below isolates it: same total load, delivered two different ways.
# --------------------------------------------------------------------------

SINGLE = """
<mujoco>
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom type="plane" size="5 5 0.1"/>
    <body pos="0 0 0.05"><freejoint/>
      <geom type="box" size="0.05 0.05 0.05" mass="{m}"/></body>
  </worldbody>
</mujoco>
"""


def penetration_single(mass, sim_time=2.0, dt=0.002):
    """One box of mass `mass` on the floor. Load == own mass."""
    m = mujoco.MjModel.from_xml_string(SINGLE.format(m=mass))
    d = mujoco.MjData(m)
    for _ in range(int(sim_time / dt)):
        mujoco.mj_step(m, d)
    return round((0.05 - float(d.qpos[2])) * 1000, 4)      # mm below rest


def penetration_stacked(total_load, light_mass=1.0, sim_time=2.0, dt=0.002):
    """A 1 kg box carrying `total_load` on top. Same force at the floor
    contact, but the effective mass there is only the light box's."""
    m = mujoco.MjModel.from_xml_string(RATIO_STACK.format(
        dt=dt, it=50, solver="Newton", m_light=light_mass,
        m_heavy=float(total_load - light_mass)))
    d = mujoco.MjData(m)
    for _ in range(int(sim_time / dt)):
        mujoco.mj_step(m, d)
    return round((0.05 - float(d.qpos[2])) * 1000, 4)


def reconcile():
    # start at 2 kg: a 1 kg light box means the heavy body would be
    # massless at a 1 kg total, which MuJoCo rejects outright
    loads = [2.0, 10.0, 100.0, 1000.0]
    out = []
    for L in loads:
        out.append({"total_load_kg": L,
                    "single_box_pen_mm": penetration_single(L),
                    "stacked_on_1kg_pen_mm": penetration_stacked(L)})
    return out
