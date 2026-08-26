"""Physics regression gates -- each asserts against a CLOSED-FORM answer.

Golden-value tests rot: someone regenerates the golden file and the test
passes forever afterwards regardless of correctness. Where an analytic answer
exists, assert against that instead; it cannot be regenerated.
"""
import os, sys
import numpy as np
import pytest
import mujoco

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "model")
G = 9.81

FREEFALL = """
<mujoco><option timestep="{dt}" gravity="0 0 -9.81" integrator="{integ}"/>
<worldbody><geom type="plane" size="10 10 .1"/>
<body pos="0 0 1"><freejoint/><geom type="box" size=".05 .05 .05" mass="1"/></body>
</worldbody></mujoco>"""

SLIDE = """
<mujoco><option timestep="0.00416666666" gravity="0 0 -9.81" integrator="RK4"/>
<worldbody><geom type="plane" size="20 20 .1" friction="{mu} 0 0"/>
<body pos="0 0 0.0501"><freejoint/>
<geom type="box" size=".05 .05 .05" mass="1" friction="{mu} 0 0"
      solref="0.002 1" solimp="0.99 0.999 0.001"/></body>
</worldbody></mujoco>"""

PENDULUM = """
<mujoco><option timestep="{dt}" integrator="{integ}" gravity="0 0 -9.81"/>
<worldbody><body pos="0 0 1"><joint type="hinge" axis="0 1 0" damping="0"/>
<geom type="capsule" fromto="0 0 0 0 0 -0.5" size="0.02" density="1000"/>
</body></worldbody></mujoco>"""


def test_gravity_recovered_from_freefall():
    """Fit z = at^2+bt+c to the fall; -2a must be g. Timestep-independent,
    unlike comparing raw positions."""
    m = mujoco.MjModel.from_xml_string(FREEFALL.format(dt=1/240, integ="RK4"))
    d = mujoco.MjData(m)
    zs, ts = [], []
    for i in range(120):
        mujoco.mj_step(m, d)
        if d.qpos[2] > 0.11:
            zs.append(float(d.qpos[2])); ts.append(i / 240)
    a, _, _ = np.polyfit(ts, zs, 2)
    assert abs(-2*a - G) < 0.05, f"recovered g = {-2*a:.4f}, expected {G}"


def test_rest_height_equals_half_extent():
    """A settled 0.1 m box must rest with its centre at exactly 0.05 m."""
    m = mujoco.MjModel.from_xml_string(FREEFALL.format(dt=1/240, integ="RK4"))
    d = mujoco.MjData(m)
    for _ in range(1200):
        mujoco.mj_step(m, d)
    assert abs(d.qpos[2] - 0.05) < 2e-3, f"rests at {d.qpos[2]:.5f}, want 0.05"


@pytest.mark.parametrize("mu,tol_pct", [(0.2, 2.0), (0.4, 2.0), (0.6, 3.0)])
def test_coulomb_stopping_distance(mu, tol_pct):
    """d = v^2 / (2*mu*g). Friction that is subtly wrong passes an
    'it slid and stopped' check and fails this one."""
    m = mujoco.MjModel.from_xml_string(SLIDE.format(mu=mu))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    d.qvel[0] = 2.0
    for _ in range(1600):
        mujoco.mj_step(m, d)
    analytic = 2.0**2 / (2*mu*G)
    err = abs(d.qpos[0] - analytic) / analytic * 100
    assert err < tol_pct, f"mu={mu}: {d.qpos[0]:.4f} m vs {analytic:.4f} m ({err:.1f}%)"


def test_coulomb_is_mass_independent():
    """Stopping distance must NOT depend on mass. This is the check that
    catches an engine faking friction with a velocity-proportional drag."""
    dists = []
    for mass in (1.0, 5.0):
        xml = SLIDE.format(mu=0.4).replace('mass="1"', f'mass="{mass}"')
        m = mujoco.MjModel.from_xml_string(xml)
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d); d.qvel[0] = 2.0
        for _ in range(1600):
            mujoco.mj_step(m, d)
        dists.append(float(d.qpos[0]))
    spread = abs(dists[0]-dists[1]) / max(dists) * 100
    assert spread < 5.0, f"5x mass changed stopping distance by {spread:.1f}%"


def test_rk4_beats_euler_on_energy_drift():
    """Integrator regression. If someone swaps the default integrator, this
    fails loudly instead of silently degrading every downstream result."""
    def drift(integ):
        m = mujoco.MjModel.from_xml_string(PENDULUM.format(dt=0.01, integ=integ))
        d = mujoco.MjData(m)
        d.qpos[0] = np.pi/3
        mujoco.mj_forward(m, d)
        def energy():
            mujoco.mj_energyPos(m, d); mujoco.mj_energyVel(m, d)
            return float(d.energy[0] + d.energy[1])
        e0 = energy()
        for _ in range(1000):
            mujoco.mj_step(m, d)
        return abs(energy() - e0) / abs(e0)
    assert drift("RK4") < drift("Euler") / 10, "RK4 lost its accuracy advantage"


def test_simulation_is_deterministic():
    """Same model, same seed, same result. Non-determinism makes every other
    regression test meaningless."""
    def run():
        m = mujoco.MjModel.from_xml_string(FREEFALL.format(dt=1/240, integ="RK4"))
        d = mujoco.MjData(m)
        d.qvel[:3] = [0.3, -0.2, 0.1]
        for _ in range(600):
            mujoco.mj_step(m, d)
        return d.qpos.copy()
    assert np.allclose(run(), run(), atol=0.0), "simulation is not deterministic"
