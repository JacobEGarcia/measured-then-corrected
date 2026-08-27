"""Gates for the gait-validation study.

These lock in measurements taken in Isaac Sim on a Kaggle T4 (recorded
constants -- no GPU in CI), and guard the ANALYSIS that says the run is not a
valid gait. The point of these gates is that a future run must BEAT them.
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
import gait_validation as gv


def test_foot_detection_found_real_feet_on_two_of_three_robots():
    """The harness half did work: ANYmal and Spot resolve to actual foot
    links across two different vendor naming schemes."""
    assert set(gv.ATTEMPT7["ANYmal"]["feet"].values()) == {
        "LF_FOOT", "LH_FOOT", "RF_FOOT", "RH_FOOT"}
    assert set(gv.ATTEMPT7["Spot"]["feet"].values()) == {
        "fl_foot", "fr_foot", "hl_foot", "hr_foot"}


def test_a1_foot_detection_picked_a_hip():
    """The known miss, kept as a gate so the fix can be demonstrated rather
    than asserted. Lowest-link-per-leg is pose-dependent; chain depth is not."""
    assert gv.ATTEMPT7["A1"]["feet"]["FL"] == "FL_hip", (
        "A1 FL detection changed -- if it now resolves to a foot, this gate "
        "should be updated to assert the fix, not the bug")
    assert gv.ATTEMPT7["A1"]["z_range_m"]["FL"] < 0.01, (
        "the giveaway was a 4 mm z range against 77-100 mm for real feet")


def test_measured_swings_are_too_large_to_be_steps():
    """The measurement that invalidates the measurement."""
    v = gv.swing_verdict()
    assert not v["ANYmal"]["swing_is_plausible"], "ANYmal swing now plausible"
    assert not v["Spot"]["swing_is_plausible"], "Spot swing now plausible"
    assert v["Spot"]["max_swing_m"] > 0.5, (
        "Spot's 0.76 m foot excursion was the clearest evidence of a fall")


def test_duty_cycles_do_not_describe_a_trot():
    """A trot is 50% duty on every leg. ANYmal never lifts a foot; Spot is
    wildly asymmetric."""
    v = gv.swing_verdict()
    assert v["ANYmal"]["mean_duty_error_vs_0p5"] > 0.4, (
        "ANYmal duty was ~0.96 on all four legs -- nothing ever lifting")
    assert v["ANYmal"]["duty_spread"] < 0.01, (
        "all four ANYmal legs agreed with each other while all being wrong, "
        "which is what a body-wide motion looks like")
    assert v["Spot"]["duty_spread"] > 0.2, "Spot's asymmetry was the tell"


def test_a1_is_the_partial_exception_and_should_be_reported_as_such():
    """Honesty gate. A1's swing IS in a plausible range and its duty error is
    the smallest of the three, so it must not be lumped in with the other two
    as an outright failure."""
    v = gv.swing_verdict()
    assert v["A1"]["swing_is_plausible"], "A1's 0.10 m swing was within range"
    assert v["A1"]["mean_duty_error_vs_0p5"] < 0.1, (
        "A1 was closest to a real trot of the three")
    assert v["A1"]["mean_duty_error_vs_0p5"] < v["ANYmal"]["mean_duty_error_vs_0p5"]
    assert v["A1"]["mean_duty_error_vs_0p5"] < v["Spot"]["mean_duty_error_vs_0p5"]


def test_the_pin_never_held_and_that_is_recorded():
    """The test-stand approach was abandoned on evidence, not on a hunch.
    A FixedJoint targeting the reference Xform does not anchor an
    articulation's root link."""
    drift = gv.pin_never_held()
    assert drift["ANYmal"] > 0.1, "ANYmal trunk drift was 0.30 m"
    assert drift["Spot"] > 0.5, "Spot trunk drift was 1.03 m"


def test_the_fall_contaminated_foot_detection():
    """Ranking links by WORLD-frame excursion during a leg sweep fails while
    the body is descending: the fall adds the same offset to every link.
    Four of eight legs resolved to a thigh, shank or upper-leg link. This is
    the evidence that the frame, not the stand, was the problem."""
    bad = gv.fall_contaminated_foot_detection()
    assert len(bad) >= 3, (
        f"only {len(bad)} mis-detected links; the contamination argument for "
        "switching to the trunk frame rests on this being widespread")
    assert "ANYmal.LF" in bad and bad["ANYmal.LF"] == "LF_THIGH"


# ---------------------------------------------------- the trot that worked

import gait_result as gres


def test_spot_reproduces_the_commanded_trot():
    """A trot has one signature: diagonal pairs together, the two pairs half a
    cycle apart. Scored against that directly, not against a duty number whose
    stance threshold I chose."""
    t = gres.trot_error("Spot")
    assert t is not None
    assert t["diag_FL_HR_deg"] < 15, f"FL and HR {t['diag_FL_HR_deg']}° apart"
    assert t["diag_FR_HL_deg"] < 15, f"FR and HL {t['diag_FR_HL_deg']}° apart"
    assert abs(t["between_pairs_deg"] - 180) < 15, (
        f"pairs {t['between_pairs_deg']}° apart, expected 180")
    assert t["worst_deviation_deg"] < 10, (
        f"worst deviation {t['worst_deviation_deg']}° from an ideal trot")


def test_the_other_two_robots_are_diagnosed_not_hidden():
    """One of three is the honest result. Both failures have named causes in
    the recorded data, and this gate makes sure they stay named."""
    w = gres.why_the_others_failed()
    assert "shank or thigh" in w["ANYmal"]["cause"], (
        "ANYmal's cause was mis-resolved foot links")
    assert w["A1"]["max_swing_m"] < 1e-3, (
        f"A1's legs moved {w['A1']['max_swing_m']} m; the 'never moved' "
        "diagnosis no longer holds")


def test_only_one_robot_passes_and_that_is_recorded():
    """Guards against quietly claiming three."""
    passing = [n for n in ("Spot", "ANYmal", "A1")
               if (gres.trot_error(n) or {}).get("worst_deviation_deg", 999) < 15]
    assert passing == ["Spot"], f"passing robots changed: {passing}"
