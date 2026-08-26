"""Gates for the MuJoCo vs PhysX contact comparison.

These lock in measurements taken on a Kaggle T4 running Isaac Sim 6.0.1. The
PhysX numbers are recorded constants, not re-measured here -- there is no GPU
in CI -- so these gates guard the ANALYSIS and the MuJoCo half against drift,
and will need re-running against a new Isaac release.
"""
import os, sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
import crossengine_contact as ce


def test_both_engines_are_mass_independent():
    """The non-obvious agreement: two solvers sharing no code both make
    resting penetration invariant to a 1000x mass change."""
    for eng, a in ce.agreements().items():
        assert a["spread_mm"] < 1e-4, (
            f"{eng} penetration varied by {a['spread_mm']} mm across "
            "0.5-500 kg; the cross-engine agreement no longer holds")


def test_mujoco_is_flat_in_dt_until_the_clamp_engages():
    d = ce.disagreements()
    assert d["mujoco_is_flat_at_fine_dt"], (
        "MuJoCo penetration is no longer identical at 480/240/120 Hz")
    assert d["mujoco_2dt_at_120hz"] < 0.02 < d["mujoco_2dt_at_60hz"], (
        "the 2*dt crossover no longer falls between 120 Hz and 60 Hz")


def test_physx_has_no_clamp_plateau():
    """The predicted difference: with no timeconst there is nothing to clamp,
    so PhysX should vary smoothly across the whole range."""
    d = ce.disagreements()
    assert not d["physx_is_flat_at_fine_dt"], (
        "PhysX now shows a flat region, which would suggest clamping")
    assert d["physx_monotonic_in_dt"], "PhysX penetration is no longer monotonic in dt"


def test_the_engines_disagree_on_stiffness_by_orders_of_magnitude():
    """Practical consequence: contact parameters tuned in one engine do not
    port to the other. Default MuJoCo contact is far softer."""
    gaps = ce.stiffness_gap()
    assert all(g["mujoco_over_physx"] > 50 for g in gaps), (
        f"stiffness ratios have collapsed: {[g['mujoco_over_physx'] for g in gaps]}")
    fine = [g for g in gaps if g["hz"] == 480][0]
    assert fine["mujoco_over_physx"] > 1000, (
        "at a fine timestep MuJoCo used to be >1000x softer than PhysX")


def test_rest_offset_maps_one_to_one_to_standoff():
    """PhysX exposes a LENGTH knob MuJoCo has no equivalent for: ask for a
    5 mm standoff and the body rests 5 mm above geometric contact."""
    for r in ce.rest_offset_is_a_geometric_standoff():
        if r["rest_offset_m"] > 0:
            expected_mm = r["rest_offset_m"] * 1000
            assert r["standoff_mm"] == pytest.approx(expected_mm, rel=0.01), (
                f"rest_offset {r['rest_offset_m']} m gave a "
                f"{r['standoff_mm']} mm standoff, expected ~{expected_mm}")
