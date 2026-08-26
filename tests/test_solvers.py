"""Gates for the solver comparison."""
import os, sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
import solvers as sv


@pytest.fixture(scope="module")
def easy():
    return {r["solver"]: r for r in sv.easy_problem()}


@pytest.fixture(scope="module")
def hard_rows():
    return sv.hard_problem()


def test_all_three_solvers_agree_on_accuracy(easy):
    """Solver choice does not change the answer on a well-conditioned problem
    -- which is what makes the speed difference free to take."""
    pens = [r["penetration_mm"] for r in easy.values()]
    assert max(pens) - min(pens) < 0.01, (
        f"solvers now disagree on penetration: {pens}")


def test_newton_is_far_faster_than_pgs(easy):
    """PGS is the classic game-physics choice and is dominated here."""
    ratio = easy["Newton"]["steps_per_s"] / easy["PGS"]["steps_per_s"]
    assert ratio > 5, (
        f"Newton is only {ratio:.1f}x faster than PGS; it was 14x")


def test_no_solver_rescues_a_bad_mass_ratio(hard_rows):
    """Together with the iteration sweep: a 1000:1 ratio is not fixable by
    solver tuning, only by changing the model."""
    squashes = [r["squash_mm"] for r in hard_rows if r["squash_mm"] is not None]
    assert min(squashes) > 20.0, (
        f"some solver now keeps squash under 20 mm ({min(squashes)}); the "
        "'not a solver-tuning problem' conclusion needs revisiting")


def test_solvers_fail_in_different_ways(hard_rows):
    """The distinction worth stating: Newton drives the light body into the
    floor, CG and PGS let the heavy body pass through it."""
    modes = sv.failure_modes(hard_rows)
    newton = modes["Newton@100"]["mode"]
    pgs = modes["PGS@100"]["mode"]
    assert newton != pgs, "the two failure modes have converged"
    assert "floor" in newton
    assert "through" in pgs


def test_iterations_still_do_nothing_for_newton(hard_rows):
    """Consistency check against stability_frontier.py, on the same problem."""
    by = {(r["solver"], r["iterations"]): r["squash_mm"] for r in hard_rows}
    assert by[("Newton", 1)] == pytest.approx(by[("Newton", 100)], abs=1e-3), (
        "Newton's squash now depends on iteration count, contradicting the "
        "stability study")
