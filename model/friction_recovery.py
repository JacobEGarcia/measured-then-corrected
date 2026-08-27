"""Recovering a friction coefficient PhysX was never asked to report.

JD: "validate simulation fidelity" / "Experience with physics engines".

mu goes in as a material property. The angle at which a block starts to slide
comes out of the dynamics. Coulomb connects them: tan(theta_slip) = mu. Sweep
the incline, find the first angle that slides, and recover mu without ever
reading it back from the engine.

PREDICTION recorded before the run: within a few percent, but BIASED LOW --
the block is sampled at discrete angles and creeps before it visibly slides,
so the first angle flagged as slipping arrives a little early.

That was WRONG IN DIRECTION, and the reason is embarrassing once seen: the
sweep steps in 2-degree increments, so the first angle FLAGGED as slipping is
by construction the first grid point at or above the true threshold. It can
never land below it. The bias had to be positive no matter what creep does.
Pre-slip creep is visible in the data (0.4-0.8 mm of motion one step before
release) but sits far under the 20 mm detection threshold, so it never
triggers anything early.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = json.load(open(os.path.join(HERE, "friction_recovery.json")))
SWEEP = RAW["friction_sweep"]
STEP_DEG = 2.0


def recovered():
    out = []
    for c in SWEEP:
        mu_in = c["mu_input"]
        ang = c["slip_angle_deg"]
        out.append({
            "mu_input": mu_in,
            "slip_angle_deg": ang,
            "true_slip_angle_deg": round(math.degrees(math.atan(mu_in)), 3),
            "mu_recovered": c["mu_recovered"],
            "error_pct": c["error_pct"],
            "overshoot_deg": round(ang - math.degrees(math.atan(mu_in)), 3)})
    return out


def bias_is_forced_by_the_grid():
    """The correction, stated as a check rather than a claim.

    If the positive bias comes from angle discretisation, then every detected
    angle must sit ABOVE the true one, and by less than one grid step. Both
    are testable.
    """
    rows = recovered()
    over = [r["overshoot_deg"] for r in rows]
    return {"all_above_true": all(o > 0 for o in over),
            "all_within_one_step": all(o < STEP_DEG for o in over),
            "max_overshoot_deg": round(max(over), 3),
            "grid_step_deg": STEP_DEG,
            "all_errors_positive": all(r["error_pct"] > 0 for r in rows)}


def pre_slip_creep():
    """Creep exists -- it just never reaches the detection threshold."""
    out = []
    for c in SWEEP:
        moved = [(r["angle_deg"], r["moved_m"]) for r in c["rows"]
                 if "moved_m" in r and 0 < r["moved_m"] < 0.02]
        out.append({"mu_input": c["mu_input"], "creep_samples_m": moved})
    return out


if __name__ == "__main__":
    print("mu goes IN as a material property; the slip angle comes OUT\n")
    print(f"  {'mu in':>7} {'true angle':>11} {'detected':>9} {'mu out':>8} {'error':>8}")
    for r in recovered():
        print(f"  {r['mu_input']:>7} {r['true_slip_angle_deg']:>10.2f}° "
              f"{r['slip_angle_deg']:>8}° {r['mu_recovered']:>8} "
              f"{r['error_pct']:>+7.1f}%")

    b = bias_is_forced_by_the_grid()
    print(f"\n  PREDICTION WAS WRONG IN DIRECTION -- I said biased low.")
    print(f"  every error positive       : {b['all_errors_positive']}")
    print(f"  every angle above the true : {b['all_above_true']}")
    print(f"  every one within one step  : {b['all_within_one_step']}"
          f"  (max {b['max_overshoot_deg']}° on a {b['grid_step_deg']}° grid)")
    print("\n  A 2-degree sweep can only ever flag the first grid point at or")
    print("  ABOVE the threshold, so the bias had to be positive whatever")
    print("  creep does.")

    print("\n  creep does exist, one step before release:")
    for c in pre_slip_creep():
        print(f"    mu {c['mu_input']}: {c['creep_samples_m']}")

    json.dump({"recovered": recovered(), "bias_check": bias_is_forced_by_the_grid(),
               "creep": pre_slip_creep()},
              open(os.path.join(HERE, "friction_recovery_analysis.json"), "w"), indent=2)
    print("\nwrote model/friction_recovery_analysis.json")
