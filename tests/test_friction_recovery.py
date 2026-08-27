"""Gates for recovering mu from the slip angle."""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
import friction_recovery as fr


def test_mu_is_recovered_within_two_percent():
    """mu goes in as a material property; the slip angle comes out of the
    dynamics. tan(theta) = mu closes the loop without asking the engine."""
    for r in fr.recovered():
        assert abs(r["error_pct"]) < 3.0, (
            f"mu {r['mu_input']} recovered as {r['mu_recovered']} "
            f"({r['error_pct']:+.1f}%)")


def test_the_bias_is_positive_and_forced_by_the_grid():
    """Guards the CORRECTION. I predicted a low bias from pre-slip creep. A
    2-degree sweep can only flag the first grid line at or above the true
    threshold, so the bias had to be positive regardless of creep."""
    b = fr.bias_is_forced_by_the_grid()
    assert b["all_errors_positive"], "the bias is no longer positive"
    assert b["all_above_true"], "a detected angle fell below the true one"
    assert b["all_within_one_step"], (
        f"max overshoot {b['max_overshoot_deg']}° exceeds the "
        f"{b['grid_step_deg']}° grid step, so discretisation is no longer a "
        "sufficient explanation")


def test_creep_exists_but_never_trips_the_detector():
    """The mechanism I blamed IS present -- it just never reaches the 20 mm
    detection threshold, which is why it could not cause an early trigger."""
    creep = fr.pre_slip_creep()
    assert any(c["creep_samples_m"] for c in creep), "no creep observed at all"
    for c in creep:
        for _, m in c["creep_samples_m"]:
            assert m < 0.02, f"creep of {m} m would have tripped the detector"
