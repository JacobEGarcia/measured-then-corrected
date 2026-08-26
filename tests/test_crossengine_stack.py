"""Gates for the PhysX mass-ratio / iteration study.

PhysX numbers are recorded constants from a Kaggle T4 run (no GPU in CI), so
these gates guard the ANALYSIS and the cross-engine contrast. They will need
re-running against a new Isaac release.
"""
import os, sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
import crossengine_stack as cs


def test_physx_falls_off_a_cliff_where_mujoco_slid():
    """Both engines degrade with mass ratio -- but not in the same shape.
    MuJoCo went 1.2 -> 5.95 -> 51 mm over ratios 1/100/10000. PhysX is fine at
    10 and completely gone at 100."""
    c = cs.mass_ratio_cliff()
    assert c["last_working_ratio"] == 10
    assert c["first_failing_ratio"] == 100
    assert c["jump_factor"] > 20, (
        f"the one-step jump is only {c['jump_factor']}x; the 'cliff, not "
        "slide' framing needs revisiting")


def test_position_iterations_are_a_step_function_not_a_curve():
    """The prediction was right in direction and wrong in shape: I expected
    TGS to converge gradually. 1, 32 and 64 are indistinguishable failures;
    96 is a working stack."""
    t = cs.iteration_threshold()
    assert t["highest_failing"] == 64
    assert t["lowest_working"] == 96
    assert t["squash_below_mm"] > 90, "64 iterations should be full pass-through"
    assert t["squash_above_mm"] < 5, "96 iterations should give a real stack"


def test_mujoco_iterations_never_help_at_all():
    """The contrast that makes the PhysX result interesting."""
    v = set(cs.MUJOCO_ITERATIONS_AT_RATIO_100.values())
    assert len(v) == 1, (
        f"MuJoCo squash now varies with iteration count: {v}. That would "
        "contradict stability_frontier.py")


def test_velocity_iterations_do_not_substitute():
    """The control that names the mechanism. If the cliff were about total
    solver effort, velocity iterations would help too."""
    v = cs.velocity_iterations_do_not_substitute()
    assert not v["any_resolved"], (
        "velocity iterations now resolve the stack; the 'position-level "
        "depenetration specifically' conclusion is wrong")


def test_the_iteration_threshold_scales_with_mass_ratio():
    """Iterations buy headroom, not immunity -- the practical statement."""
    s = cs.threshold_scales_with_ratio()
    assert s[100]["min_iters_that_work"] < s[1000]["min_iters_that_work"], (
        "a harder ratio no longer needs more iterations")
    assert not s[10000]["solvable_at_all"], (
        "ratio 10000 is now solvable within PhysX's 255-iteration maximum")


def test_timestep_is_not_the_failure_axis_in_either_engine():
    ts = cs.timestep_is_not_the_axis()
    assert ts["spread_mm"] < 0.1, (
        f"timestep now matters ({ts['spread_mm']} mm across a 16x range)")
    assert ts["all_fail"], "every timestep should fail equally at ratio 1000"
