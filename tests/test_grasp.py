"""Gates for the pinch-grasp study."""
import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
import grasp as gr


CASES = [(0.4, 0.5), (0.8, 0.5), (1.0, 1.0)]


@pytest.fixture(scope="module")
def measured():
    return {(mu, m): gr.find_min_force(mu, m) for mu, m in CASES}


@pytest.mark.parametrize("mu,mass", CASES)
def test_min_grip_force_matches_closed_form(mu, mass, measured):
    """F_min = m*g / (2*mu). mu and mass go in; the holding threshold is an
    emergent property of the dynamics."""
    th = gr.theory(mu, mass)
    meas = measured[(mu, mass)]
    assert meas is not None, f"never held at mu={mu}, mass={mass}"
    err = abs(meas - th) / th
    assert err < 0.20, (
        f"measured {meas:.3f} N vs theory {th:.3f} N ({err*100:.1f}% off)")


def test_no_grasp_beats_coulomb(measured):
    """The sign matters more than the magnitude. F = m*g/(2*mu) is the
    MARGINAL holding force -- the exact limit of static friction -- so it
    holds with zero margin and every measurement should land above it. A
    measurement BELOW theory would mean the contact model is generating
    friction the material properties do not license."""
    for (mu, mass), meas in measured.items():
        th = gr.theory(mu, mass)
        assert meas >= th, (
            f"mu={mu}, mass={mass}: held at {meas:.3f} N, below the Coulomb "
            f"limit of {th:.3f} N -- the grasp is beating its own friction")


def test_the_excess_is_an_additive_offset(measured):
    """Guards the EXPLANATION, not just the result. If the excess is a roughly
    constant force offset (finite contact stiffness, settling transient), its
    absolute spread should be much tighter than its relative spread."""
    r = gr.offset_is_additive_not_multiplicative()
    assert r["additive_is_tighter"], (
        f"absolute excess CV {r['abs_excess_cv']} is no longer tighter than "
        f"relative CV {r['rel_excess_cv']}; the additive-offset explanation "
        "in the module needs rewriting")
    assert r["abs_excess_cv"] < 0.35, (
        f"absolute excess is no longer consistent (CV {r['abs_excess_cv']})")


def test_squeezing_harder_never_makes_the_grasp_worse():
    """Bisection is only valid if the predicate is monotone. A stiff contact
    CAN eject an object, so this is checked rather than assumed."""
    r = gr.verify_monotone(0.4, 0.5, [2, 5, 10, 20, 40, 80, 160])
    assert r["monotone"], (
        f"{r['held_then_failed']} force step(s) went from holding to failing; "
        "find_min_force's bisection is invalid")


def test_doubling_mass_doubles_the_required_force(measured):
    """A closed-form scaling that must survive independent of the offset."""
    a = measured[(0.4, 0.5)]
    m2 = gr.find_min_force(0.4, 1.0)
    ratio = m2 / a
    assert 1.7 < ratio < 2.3, (
        f"doubling the mass changed the required force by {ratio:.2f}x, "
        "expected ~2x")
