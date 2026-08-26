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
