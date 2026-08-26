"""Gates for the stability frontier and the mass-normalisation reconciliation."""
import os, sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
import stability_frontier as sf


def test_penetration_is_flat_when_load_equals_own_mass():
    """contact_tuning.py's claim, re-derived independently here."""
    pens = [sf.penetration_single(m) for m in (2.0, 10.0, 100.0, 1000.0)]
    spread = max(pens) - min(pens)
    assert spread < 1e-3, (
        f"single-box penetration varied by {spread:.5f} mm across a 500x load "
        "range; it is supposed to be mass-independent")


def test_penetration_scales_with_load_in_a_stack():
    """The case that breaks the normalisation, and the reason a heavy object
    on a light one is the classic solver killer."""
    light = sf.penetration_stacked(2.0)
    heavy = sf.penetration_stacked(1000.0)
    assert heavy / light > 50, (
        f"stacked penetration only grew {heavy/light:.1f}x for a 500x load; "
        "the mass-ratio failure mode has changed")


def test_the_two_results_are_not_contradictory():
    """Guards the RECONCILIATION itself: same total load, two deliveries,
    opposite behaviour. If these ever agree, the explanation is wrong."""
    rows = sf.reconcile()
    single = {r["total_load_kg"]: r["single_box_pen_mm"] for r in rows}
    stacked = {r["total_load_kg"]: r["stacked_on_1kg_pen_mm"] for r in rows}
    assert single[2.0] == pytest.approx(single[1000.0], abs=1e-3)
    assert stacked[1000.0] > 20 * stacked[2.0]


def test_solver_iterations_do_not_rescue_a_bad_mass_ratio():
    """The counter-intuitive one worth stating out loud: the standard advice
    'raise solver iterations for stiff contacts' buys nothing here, because
    the squash is the soft-contact model behaving as specified, not a
    convergence failure."""
    lo = sf.evaluate_ratio(0.004, 1, 100, reps=1)
    hi = sf.evaluate_ratio(0.004, 50, 100, reps=1)
    assert lo["squash_mm"] == pytest.approx(hi["squash_mm"], abs=1e-3), (
        f"1 iteration gave {lo['squash_mm']} mm, 50 gave {hi['squash_mm']} mm; "
        "iterations now matter, so the write-up needs revising")


def test_mass_ratio_dominates_timestep_as_a_failure_axis():
    """At ratio 1 even a huge timestep survives; at ratio 10000 even a tiny
    one fails. Timestep is the wrong knob to reach for first."""
    easy_big_dt = sf.evaluate_ratio(0.032, 5, 1, reps=1)
    hard_small_dt = sf.evaluate_ratio(0.001, 50, 10000, reps=1)
    assert easy_big_dt["stable"], "ratio 1 at dt=0.032 should still be fine"
    assert not hard_small_dt["stable"], (
        "ratio 10000 at dt=0.001 is now stable; the 'mass ratio dominates dt' "
        "claim no longer holds")
