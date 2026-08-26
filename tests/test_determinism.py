"""Gates for the determinism / chaos-horizon study."""
import math, os, sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
import determinism as det


def test_repeated_runs_are_bit_identical():
    r = det.q1_repeat_runs_bit_identical(trials=3)
    assert r["bit_identical"], (
        f"repeated runs differ by {r['max_abs_diff']:.3e}; MuJoCo single-thread "
        "stepping is supposed to be exactly reproducible")


def test_an_untouched_body_across_the_room_changes_nothing():
    """The regression-test killer: adding scenery must not perturb existing
    objects through constraint/island ordering."""
    r = det.q2_unrelated_body_perturbs_the_scene()
    assert r["unaffected"], (
        f"adding a box 3 m away shifted body 0 by {r['max_abs_diff']:.3e}; "
        "scene content is coupling through solver ordering")


def test_ulp_perturbation_must_not_vanish_into_rounding():
    """Guards the bug this study actually hit: a 1-ULP-at-1.0 nudge added to a
    coordinate of 2.0 rounds away, silently producing two identical runs."""
    q = 2.0
    wrong = np.nextafter(1.0, 2.0) - 1.0
    right = np.nextafter(q, np.inf) - q
    assert q + wrong == q, "the rounding trap no longer reproduces"
    assert q + right != q, "the magnitude-relative nudge must survive"


def test_zero_reference_does_not_fall_into_denormals():
    """Second trap: nextafter(0.0, 1.0) is the smallest denormal (4.94e-324),
    not a usable ULP."""
    assert np.nextafter(0.0, 1.0) < 1e-300, "denormal assumption changed"
    r = det.q3_chaos_contact()
    assert r["perturbation"] > 1e-17, (
        f"contact perturbation is {r['perturbation']:.3e} -- back in denormal "
        "territory, where the growth figures are meaningless")


@pytest.mark.parametrize("fn,lo,hi", [
    (det.q3_chaos_smooth, 1.5, 3.0),
    (det.q3_chaos_contact, 0.15, 0.8),
])
def test_lyapunov_exponents_are_positive_and_in_range(fn, lo, hi):
    r = fn()
    lam = r["lyapunov_exponent_per_s"]
    assert lam is not None and lo < lam < hi, (
        f"Lyapunov exponent {lam} /s outside [{lo}, {hi}]")


def test_exponent_is_independent_of_perturbation_size():
    """The claim that makes it a Lyapunov exponent rather than a curve fit:
    poking harder must not change the growth RATE."""
    a = det.q3_chaos_smooth()["lyapunov_exponent_per_s"]
    b = det.q3_chaos_smooth_seeded()["lyapunov_exponent_per_s"]
    rel = abs(a - b) / a
    assert rel < 0.10, (
        f"exponents from a 1-ULP and a 1e-12 seed differ by {rel*100:.1f}%; "
        "they should agree to a few percent")


def test_exponent_predicts_a_different_seeds_horizon():
    """Blind predictive check -- the strongest form of validation available
    here: fit on one run, predict another."""
    a = det.q3_chaos_smooth()
    b = det.q3_chaos_smooth_seeded()
    pred = math.log(1e-3 / 1e-12) / a["lyapunov_exponent_per_s"]
    err = abs(pred - b["t_reach_1mm_s"]) / b["t_reach_1mm_s"]
    assert err < 0.15, (
        f"predicted 1 mm at {pred:.2f} s, measured {b['t_reach_1mm_s']:.2f} s "
        f"({err*100:.1f}% error)")


def test_contact_chaos_is_slower_than_smooth_chaos():
    """Counter-intuitive but measured: friction and inelastic contact dissipate,
    so the tumbling box diverges far more slowly than the frictionless
    pendulum. If this ever inverts, the write-up's explanation is wrong."""
    smooth = det.q3_chaos_smooth()["lyapunov_exponent_per_s"]
    contact = det.q3_chaos_contact()["lyapunov_exponent_per_s"]
    assert contact < smooth, (
        f"contact chaos ({contact}/s) now outpaces smooth chaos ({smooth}/s)")
