"""Validating a trot on ANYmal, Spot and A1 -- and what the first run proved.

JD: "Background in legged locomotion, manipulation, or multi-body systems."

A trot is defined by its CONTACT SCHEDULE: diagonal pairs (FL+HR, FR+HL) swing
in antiphase at 50% duty. Commanding sinusoids that LOOK like walking proves
nothing; the test is whether measured foot contacts match the gait diagram you
asked for.

Run in Isaac Sim 6.0.1 on a Kaggle T4 across three vendors' quadrupeds, because
a gait harness that only works on one robot has not been validated at all.

RESULT OF THE FIRST CLEAN RUN: the harness worked and the experiment did not.
That distinction is the finding.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- what took eight attempts to get working -----------------------------

HARNESS_LESSONS = {
    "leg_grouping": (
        "Quadruped joint naming is vendor-specific: ANYbotics LF/RF/LH/RH, "
        "Boston Dynamics fl/fr/hl/hr, Unitree FL/FR/RL/RR. A hand-written tag "
        "list failed on all three. Grouping by the prefix before the first "
        "underscore works on all three."),
    "foot_detection": (
        "Four schemes failed before one held. Matching link names against "
        "JOINT names fails because the two schemes differ. Global lowest-N "
        "puts two feet in one quadrant. Lowest-per-quadrant let the ROOT prim "
        "win a quadrant. Adding a Gprim filter then emptied the candidate list "
        "on ANYmal and Spot, whose link nodes are Xforms with Gprim CHILDREN."),
    "foot_is_the_leaf": (
        "Lowest-link-per-leg still mis-picked A1's FL_hip -- at the settled "
        "pose the hip sat lower than the foot in that one chain, with a 4 mm z "
        "range against 77-100 mm for real feet. Height is pose-dependent; "
        "CHAIN DEPTH is not. The foot is the leaf of its own chain."),
    "the_bug_the_error_did_not_name": (
        "An `if` block sat OUTSIDE the stepping loop, so w.step() and the "
        "height recording lived in an `else` that never ran. The sim was never "
        "stepped, foot-height arrays stayed empty, and numpy reported "
        "'zero-size array to reduction operation minimum'. I read that as foot "
        "detection returning nothing and rewrote foot detection twice. The "
        "message was real; the attribution was not."),
    "pin_the_accelerator": (
        "One attempt died inside SimulationApp.__init__ after ~18 minutes of "
        "installing, with a single warning: 'Minimum GPU compute capability "
        "7.0 is required'. It had landed on a Tesla P100 (cc 6.0). "
        "`enable_gpu: true` does not pin the GPU model -- only --accelerator "
        "does."),
}

# ---- attempt 7: the first run that completed end to end ------------------

ATTEMPT7 = {
    "commanded": {"gait": "trot", "frequency_hz": 1.6, "duty": 0.5},
    "ANYmal": {
        "feet": {"LF": "LF_FOOT", "LH": "LH_FOOT", "RF": "RF_FOOT", "RH": "RH_FOOT"},
        "quadrants": {"LF": "FL", "LH": "HL", "RF": "FR", "RH": "HR"},
        "duty_measured": {"LF": 0.961, "LH": 0.961, "RF": 0.967, "RH": 0.967},
        "z_range_m": {"LF": 0.2903, "LH": 0.2888, "RF": 0.2838, "RH": 0.2825}},
    "Spot": {
        "feet": {"FL": "fl_foot", "FR": "fr_foot", "HL": "hl_foot", "HR": "hr_foot"},
        "quadrants": {"FL": "FL", "FR": "FR", "HL": "HL", "HR": "HR"},
        "duty_measured": {"FL": 0.075, "FR": 0.222, "HL": 0.092, "HR": 0.297},
        "z_range_m": {"FL": 0.6965, "FR": 0.7561, "HL": 0.6697, "HR": 0.6170}},
    "A1": {
        "feet": {"FL": "FL_hip", "FR": "FR_calf", "RL": "RL_calf", "RR": "RR_calf"},
        "quadrants": {"FL": "FL", "FR": "FR", "RL": "HL", "RR": "HR"},
        "duty_measured": {"FL": 0.589, "FR": 0.419, "RL": 0.442, "RR": 0.442},
        "z_range_m": {"FL": 0.0041, "FR": 0.0772, "RL": 0.0816, "RR": 0.1008}},
}

# a foot executing a trot step swings a few centimetres
PLAUSIBLE_SWING_M = 0.15


def swing_verdict():
    """The measurement that invalidates the measurement.

    Foot z-ranges of 0.29 m (ANYmal) and up to 0.76 m (Spot) are not feet
    swinging through a step -- they are the whole robot falling over. Open-loop
    joint sinusoids with no balance controller topple a quadruped, so the
    measured contact timing describes the fall, not the commanded trot.

    The duty numbers make the same point: a trot is 50% duty on every leg.
    ANYmal read 0.96 on all four (nothing ever lifts) and Spot read 0.075 to
    0.297, wildly asymmetric. Neither is a gait.
    """
    out = {}
    for robot in ("ANYmal", "Spot", "A1"):
        zr = ATTEMPT7[robot]["z_range_m"]
        duty = ATTEMPT7[robot]["duty_measured"]
        worst = max(zr.values())
        out[robot] = {
            "max_swing_m": worst,
            "swing_is_plausible": bool(worst < PLAUSIBLE_SWING_M),
            "duty_spread": round(max(duty.values()) - min(duty.values()), 4),
            "mean_duty_error_vs_0p5": round(
                sum(abs(d - 0.5) for d in duty.values()) / len(duty), 4)}
    return out


def why_a_test_stand():
    return (
        "Pinning the trunk to the world isolates gait KINEMATICS from balance, "
        "which is how a gait generator is validated on a bench before a "
        "controller exists. Trunk height is set from the measured leg reach so "
        "the feet still make and break contact against the plane. Only then do "
        "duty cycle and diagonal-pair phase mean anything.")


if __name__ == "__main__":
    print("Commanded:", ATTEMPT7["commanded"], "\n")
    print(f"  {'robot':<8} {'max foot swing':>15} {'plausible?':>11} "
          f"{'duty spread':>12} {'mean |duty-0.5|':>16}")
    v = swing_verdict()
    for robot, r in v.items():
        print(f"  {robot:<8} {r['max_swing_m']:>14.4f}m {str(r['swing_is_plausible']):>11} "
              f"{r['duty_spread']:>12.4f} {r['mean_duty_error_vs_0p5']:>16.4f}")

    print("\n  A trot is 50% duty on every leg. ANYmal measured 0.96 on all four")
    print("  (nothing ever lifts); Spot measured 0.075 to 0.297. Foot swings of")
    print("  0.29-0.76 m are robots falling over, not feet stepping.")
    print("\n  The harness worked. The EXPERIMENT did not, and the distinction")
    print("  is the finding: an open-loop joint sinusoid is not a gait.")
    print(f"\n  {why_a_test_stand()}")

    json.dump({"harness_lessons": HARNESS_LESSONS, "attempt7": ATTEMPT7,
               "swing_verdict": v, "why_test_stand": why_a_test_stand()},
              open(os.path.join(HERE, "gait_validation.json"), "w"), indent=2)
    print("\nwrote model/gait_validation.json")
