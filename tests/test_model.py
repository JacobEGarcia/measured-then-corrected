"""Model-integrity gates.

These run in CI on every commit. They exist because the failure they catch is
silent: a model that loads fine, simulates fine, and has wrong dynamics.
"""
import json, os, subprocess, sys
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "model")
sys.path.insert(0, MODEL)


@pytest.fixture(scope="session")
def validation():
    """Regenerate the three formats and validate from scratch, so CI can never
    pass on a stale artifact."""
    subprocess.run([sys.executable, os.path.join(MODEL, "emit.py")],
                   check=True, capture_output=True)
    subprocess.run([sys.executable, os.path.join(MODEL, "validate.py")],
                   check=True, capture_output=True)
    return json.load(open(os.path.join(MODEL, "validation.json")))


def test_formats_agree(validation):
    """MJCF, URDF and SDF must describe identical numbers."""
    cv = validation["cross_validation"]
    assert cv["comparisons"] >= 150, "validation coverage shrank"
    assert cv["mismatches"] == [], f"format drift: {cv['mismatches'][:3]}"


def test_forward_kinematics(validation):
    """Matching XML numbers proves the FILES agree. Only FK proves the ROBOTS
    agree -- this gate caught a frame-convention bug that all 147 numeric
    comparisons passed."""
    fk = validation["forward_kinematics"]
    assert fk["samples"] >= 2000
    assert fk["max_abs_err_m"] < 1e-12, (
        f"FK divergence {fk['max_abs_err_m']:.3e} m -- link frames disagree")


def test_inertia_is_physical():
    """Every inertia must satisfy the triangle inequality. A tensor that
    violates it is unphysical and some solvers will happily integrate it."""
    from robot_spec import build
    for L in build():
        ixx, iyy, izz = L["diaginertia"]
        assert ixx + iyy >= izz - 1e-12, f"{L['name']} violates triangle ineq"
        assert iyy + izz >= ixx - 1e-12, f"{L['name']} violates triangle ineq"
        assert izz + ixx >= iyy - 1e-12, f"{L['name']} violates triangle ineq"
        assert min(ixx, iyy, izz) > 0, f"{L['name']} has non-positive inertia"


def test_mass_positive_and_sane():
    from robot_spec import build
    for L in build():
        assert L["mass"] > 0
        assert L["mass"] < 100, f"{L['name']} mass {L['mass']} looks wrong"


def test_joint_limits_ordered():
    from robot_spec import build
    for L in build():
        if L["axis"] is None:
            continue
        lo, hi = L["limit"]
        assert lo < hi, f"{L['name']} limits inverted"
        assert abs(lo) < 2*np.pi and abs(hi) < 2*np.pi
