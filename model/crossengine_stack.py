"""Does PhysX share MuJoCo's mass-ratio failure, and do its iterations help?

JD: "Experience with physics engines (PhysX, MuJoCo, Bullet, or similar)" /
"identify and resolve simulation performance bottlenecks."

Measured in MuJoCo (model/stability_frontier.py, model/solvers.py):
  - mass ratio dominates timestep as a failure axis
  - raising solver iterations from 1 to 50 changes the squash by less than
    1e-3 mm, and changing the ALGORITHM (Newton/CG/PGS) only changes which
    body fails. In MuJoCo the squash is the soft-contact model behaving as
    specified, not a convergence failure, so no amount of solving fixes it.

PREDICTIONS recorded in the Kaggle probe BEFORE the run:
  A. PhysX will also degrade with mass ratio -- every penetration-based solver
     does; the light body must transmit many times its own weight.
  B. PhysX solver iterations WILL help, unlike MuJoCo's, because TGS is an
     iterative substepping solver that re-linearises and corrects penetration
     each iteration. That is genuinely different work.

Both confirmed. B was confirmed in DIRECTION but wrong in SHAPE: I expected a
convergence curve and got a step function.

Isaac Sim 6.0.1 / PhysX on a Kaggle T4. A 1 kg cube with a heavier cube resting
on it; "squash" is how far the ideal 100 mm centre-to-centre gap closes, so
100 mm means the two centres coincide -- the heavy body has passed entirely
through the light one.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
FULL_PASSTHROUGH_MM = 100.0
RESOLVED_MM = 10.0

MASS_RATIO = {1: 0.4479, 10: 2.7221, 100: 100.0023, 1000: 99.9992, 10000: 99.9990}

POSITION_ITERS = {1: 99.9990, 32: 99.9991, 64: 100.0001, 96: 2.0421,
                  128: 0.5548, 160: 1.1049, 192: 0.8365, 224: 0.1899, 255: 0.4387}

VELOCITY_ITERS = {1: 100.0016, 32: 109.8345, 128: 100.0006, 255: 99.9999}

CLIFF_VS_RATIO = {
    100:   {64: 0.3359, 128: 0.0834, 255: -0.0304},
    1000:  {64: 100.0001, 128: 1.7998, 255: 0.2030},
    10000: {64: 99.9999, 128: 100.0000, 255: 100.0000},
}

TIMESTEP_HZ = {480: 100.0000, 120: 99.9994, 60: 99.9992, 30: 99.9957}

# MuJoCo, same question, from stability_frontier.py
MUJOCO_ITERATIONS_AT_RATIO_100 = {1: 5.954, 5: 5.954, 50: 5.954}


def mass_ratio_cliff():
    """PhysX degrades far more abruptly than MuJoCo. MuJoCo went 1.2 -> 5.95
    -> 51 mm over ratios 1/100/10000, a gradual slide. PhysX is fine at 10 and
    completely gone at 100."""
    ordered = sorted(MASS_RATIO)
    first_bad = next((r for r in ordered
                      if MASS_RATIO[r] > FULL_PASSTHROUGH_MM * 0.5), None)
    last_ok = max((r for r in ordered
                   if MASS_RATIO[r] < RESOLVED_MM), default=None)
    return {"last_working_ratio": last_ok, "first_failing_ratio": first_bad,
            "squash_at_last_ok_mm": MASS_RATIO[last_ok],
            "squash_at_first_bad_mm": MASS_RATIO[first_bad],
            "jump_factor": round(MASS_RATIO[first_bad] / MASS_RATIO[last_ok], 1)}


def iteration_threshold(table=None):
    """Where the step is. Not a convergence curve -- 1, 32 and 64 are
    indistinguishable failures and 96 is a working stack."""
    table = table or POSITION_ITERS
    ordered = sorted(table)
    below = [i for i in ordered if table[i] > FULL_PASSTHROUGH_MM * 0.5]
    above = [i for i in ordered if table[i] < RESOLVED_MM]
    return {"highest_failing": max(below) if below else None,
            "lowest_working": min(above) if above else None,
            "squash_below_mm": table[max(below)] if below else None,
            "squash_above_mm": table[min(above)] if above else None}


def velocity_iterations_do_not_substitute():
    """The control that identifies the mechanism. If the cliff were about
    total solver effort, velocity iterations would help too. They do not --
    which points specifically at position-level depenetration work."""
    v = list(VELOCITY_ITERS.values())
    return {"range_mm": [min(v), max(v)],
            "any_resolved": any(x < RESOLVED_MM for x in v),
            "spread_mm": round(max(v) - min(v), 4)}


def threshold_scales_with_ratio():
    """The requirement is not a constant. Ratio 100 is solved by 64
    iterations, ratio 1000 needs 128, and ratio 10000 is not solved by 255 --
    PhysX's maximum. So iterations buy headroom, not immunity."""
    out = {}
    for ratio, row in CLIFF_VS_RATIO.items():
        working = [i for i in sorted(row) if row[i] < RESOLVED_MM]
        out[ratio] = {"min_iters_that_work": min(working) if working else None,
                      "solvable_at_all": bool(working)}
    return out


def timestep_is_not_the_axis():
    v = list(TIMESTEP_HZ.values())
    return {"spread_mm": round(max(v) - min(v), 4),
            "all_fail": all(x > FULL_PASSTHROUGH_MM * 0.5 for x in v)}


if __name__ == "__main__":
    c = mass_ratio_cliff()
    print("A. MASS RATIO -- PhysX falls off a cliff where MuJoCo slid\n")
    for r in sorted(MASS_RATIO):
        print(f"    ratio {r:>6} -> {MASS_RATIO[r]:>9.4f} mm")
    print(f"\n    fine at {c['last_working_ratio']} ({c['squash_at_last_ok_mm']} mm), "
          f"gone at {c['first_failing_ratio']} ({c['squash_at_first_bad_mm']} mm) "
          f"-- a {c['jump_factor']}x jump in one step")
    print("    MuJoCo, same ratios, slid gradually: 1.2 -> 5.95 -> 51 mm")

    t = iteration_threshold()
    print("\nB. POSITION ITERATIONS -- a step function, not a convergence curve\n")
    for i in sorted(POSITION_ITERS):
        mark = "  <- resolved" if POSITION_ITERS[i] < RESOLVED_MM else ""
        print(f"    pos_iters {i:>4} -> {POSITION_ITERS[i]:>9.4f} mm{mark}")
    print(f"\n    fails at {t['highest_failing']}, works at {t['lowest_working']}")
    print("    MuJoCo, same question: 1/5/50 iterations all give 5.954 mm.")
    print("    Identical. In MuJoCo iterations are not the lever at all.")

    v = velocity_iterations_do_not_substitute()
    print("\nB2. VELOCITY ITERATIONS -- the control that names the mechanism\n")
    for i in sorted(VELOCITY_ITERS):
        print(f"    vel_iters {i:>4} -> {VELOCITY_ITERS[i]:>9.4f} mm")
    print(f"\n    none resolve: {not v['any_resolved']}. The cliff is not about "
          "total solver effort;")
    print("    it is specifically POSITION-level depenetration work.")

    print("\nB3. THE THRESHOLD SCALES WITH THE RATIO\n")
    for ratio, r in threshold_scales_with_ratio().items():
        if r["solvable_at_all"]:
            print(f"    ratio {ratio:>6} -> solved from {r['min_iters_that_work']} iterations")
        else:
            print(f"    ratio {ratio:>6} -> NOT solved even at 255 (PhysX's maximum)")
    print("\n    Iterations buy headroom, not immunity.")

    ts = timestep_is_not_the_axis()
    print("\nC. TIMESTEP -- not the axis, in either engine\n")
    for hz in sorted(TIMESTEP_HZ, reverse=True):
        print(f"    {hz:>5} Hz -> {TIMESTEP_HZ[hz]:>9.4f} mm")
    print(f"\n    spread across a 16x timestep range: {ts['spread_mm']} mm. "
          "All fail equally.")

    json.dump({"mass_ratio": MASS_RATIO, "position_iters": POSITION_ITERS,
               "velocity_iters": VELOCITY_ITERS, "cliff_vs_ratio": CLIFF_VS_RATIO,
               "timestep_hz": TIMESTEP_HZ,
               "mass_ratio_cliff": c, "iteration_threshold": t,
               "velocity_control": v,
               "threshold_scales": threshold_scales_with_ratio(),
               "timestep_verdict": ts},
              open(os.path.join(HERE, "crossengine_stack.json"), "w"), indent=2)
    print("\nwrote model/crossengine_stack.json")
