"""Gates for the integrator study."""
import os, sys, warnings
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
import integrators as ig

warnings.filterwarnings("ignore")
DTS = [2e-3, 1e-3, 5e-4, 2.5e-4, 1.25e-4]


@pytest.fixture(scope="module")
def ref():
    return ig.reference()


@pytest.mark.parametrize("integ,theory", [("Euler", 1), ("implicit", 1),
                                          ("implicitfast", 1), ("RK4", 4)])
def test_observed_order_matches_theory(integ, theory, ref):
    """The real integrator test: a method of order p must show global error
    O(dt^p). An RK4 that converges at order 1 is broken in a way no eyeball
    test would catch."""
    r = ig.order_of_accuracy(integ, DTS, ref)
    ob = r["observed_order"]
    assert ob is not None, f"could not fit an order for {integ}"
    assert abs(ob - theory) < 0.5, (
        f"{integ} converged at order {ob}, theory says {theory}")


def test_rk4_conserves_energy_far_better_than_euler():
    e = ig.energy_drift("Euler")
    r = ig.energy_drift("RK4")
    assert abs(r["drift_per_s"]) < abs(e["drift_per_s"]) / 1e5, (
        f"RK4 drift {r['drift_per_s']:.3e}/s vs Euler {e['drift_per_s']:.3e}/s "
        "-- the gap has collapsed")


def test_explicit_euler_gains_energy_and_implicit_loses_it():
    """Textbook signs, and a cheap check that the integrators are distinct."""
    assert ig.energy_drift("Euler")["drift_per_s"] > 0
    assert ig.energy_drift("implicit")["drift_per_s"] < 0


def test_joint_damping_does_not_separate_implicitfast_from_euler():
    """Guards the REFUTED hypothesis. MuJoCo's Euler already integrates joint
    damping implicitly, so damping is not a discriminating variable. If this
    ever starts differing, the explanation in the module is wrong."""
    rows = ig.implicitfast_vs_euler()
    assert all(r["identical"] for r in rows), (
        "implicitfast now differs from Euler under pure joint damping; the "
        "'Euler already implicitises damping' explanation needs revisiting")


def test_isfinite_is_not_a_stability_test():
    """Guards the bug that produced a non-monotonic stability table: MuJoCo
    resets a diverged state to zero, so the result stays finite forever."""
    r = ig.velocity_actuator_run("Euler", 500)
    assert r["autoreset_detected"], (
        "Euler at kv=500 no longer trips MuJoCo's divergence auto-reset; the "
        "detector's justification no longer applies")
    assert np.all(np.array(r["qpos"]) == 0.0), "reset fingerprint changed"


def test_implicit_integrators_survive_gains_that_kill_explicit_ones():
    """The practical payoff: a joint PD controller's derivative gain is set by
    the control engineer. 'Lower your gains' is the wrong answer when a
    one-word integrator change buys 50x the headroom."""
    for kv in (20, 100, 500):
        assert not ig.velocity_actuator_run("implicitfast", kv)["unstable"], \
            f"implicitfast unstable at kv={kv}"
    assert ig.velocity_actuator_run("Euler", 20)["unstable"], \
        "Euler is no longer unstable at kv=20"


def test_rk4_is_less_stable_than_euler_despite_higher_order():
    """Counter-intuitive and worth gating: order of accuracy says nothing
    about the size of the stability region."""
    assert ig.velocity_actuator_run("RK4", 10)["unstable"], \
        "RK4 now survives kv=10"
    assert not ig.velocity_actuator_run("Euler", 10)["unstable"], \
        "Euler now fails kv=10"


def test_implicit_damping_gain_reduces_peak_velocity_monotonically():
    """Physical sanity: a higher derivative gain must damp harder, not less."""
    peaks = [ig.velocity_actuator_run("implicitfast", kv)["peak_qvel"]
             for kv in (5, 20, 100, 500)]
    assert all(a > b for a, b in zip(peaks, peaks[1:])), (
        f"peak velocity not monotonically decreasing with gain: {peaks}")
