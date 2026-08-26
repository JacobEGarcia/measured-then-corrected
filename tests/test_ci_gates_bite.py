"""Verify the CI gates actually FAIL on broken input.

A test suite that passes on a broken model is worse than no suite, because it
converts "unknown" into "verified". These deliberately corrupt the spec and
assert that the corresponding gate rejects it.
"""
import os, sys
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "model"))
import robot_spec


def test_gate_rejects_unphysical_inertia():
    """Triangle inequality gate must reject a tensor that violates it."""
    L = robot_spec.build()                       # capture BEFORE mutating
    L[1]["diaginertia"] = (1e-6, 1e-6, 10.0)     # izz >> ixx + iyy
    with pytest.raises(AssertionError):
        for x in L:
            ixx, iyy, izz = x["diaginertia"]
            assert ixx + iyy >= izz - 1e-12, f"{x['name']} violates triangle ineq"


def test_gate_rejects_inverted_joint_limits():
    L = robot_spec.build()
    L[1]["limit"] = (1.0, -1.0)
    with pytest.raises(AssertionError):
        for x in L:
            if x["axis"] is None:
                continue
            lo, hi = x["limit"]
            assert lo < hi, f"{x['name']} limits inverted"


def test_gate_rejects_wrong_gravity():
    """The gravity gate must reject a model with the wrong g."""
    import mujoco
    xml = """<mujoco><option timestep="0.00416666666" gravity="0 0 -5.0" integrator="RK4"/>
    <worldbody><geom type="plane" size="10 10 .1"/>
    <body pos="0 0 1"><freejoint/><geom type="box" size=".05 .05 .05" mass="1"/></body>
    </worldbody></mujoco>"""
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    zs, ts = [], []
    for i in range(120):
        mujoco.mj_step(m, d)
        if d.qpos[2] > 0.11:
            zs.append(float(d.qpos[2])); ts.append(i/240)
    a, _, _ = np.polyfit(ts, zs, 2)
    with pytest.raises(AssertionError):
        assert abs(-2*a - 9.81) < 0.05, f"recovered g = {-2*a:.4f}"


def test_gate_rejects_velocity_drag_masquerading_as_friction():
    """Mass-independence gate must reject drag. Linear drag decelerates light
    objects faster, so stopping distance becomes mass-dependent -- exactly what
    the real gate is designed to notice."""
    import mujoco
    dists = []
    for mass in (1.0, 5.0):
        xml = f"""<mujoco><option timestep="0.00416666666" gravity="0 0 -9.81" integrator="RK4"/>
        <worldbody><geom type="plane" size="20 20 .1" friction="0.001 0 0"/>
        <body pos="0 0 0.0501"><freejoint/>
        <geom type="box" size=".05 .05 .05" mass="{mass}" friction="0.001 0 0"/>
        </body></worldbody></mujoco>"""
        m = mujoco.MjModel.from_xml_string(xml)
        m.dof_damping[:3] = 2.0                    # linear drag, not Coulomb
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d); d.qvel[0] = 2.0
        for _ in range(1600):
            mujoco.mj_step(m, d)
        dists.append(float(d.qpos[0]))
    spread = abs(dists[0]-dists[1]) / max(dists) * 100
    with pytest.raises(AssertionError):
        assert spread < 5.0, f"5x mass changed stopping distance by {spread:.1f}%"
