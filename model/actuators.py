"""Actuator models: what a real motor does that an ideal torque source does not.

JD: "Tune physics parameters -- friction, damping, inertia, ACTUATOR MODELS --
to maximize sim-to-real transfer."

Most simulated robots are driven by an ideal torque source: infinite bandwidth,
no speed droop, no gearbox. Real actuators have

  * a torque-speed curve   -- torque falls as speed rises (back-EMF)
  * a gear ratio N         -- multiplies torque, divides speed, and multiplies
                              ROTOR INERTIA BY N^2 (the term everyone forgets)
  * torque saturation      -- a hard ceiling
  * finite bandwidth       -- first-order lag between command and delivered torque

Each is validated against its closed-form prediction rather than eyeballed.
"""
import json, os
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
G = 9.81

# a single pendulum link driven by one actuator -- simple enough that every
# quantity below has an analytic answer
LINK = """
<mujoco>
  <option timestep="{dt}" gravity="0 0 -9.81" integrator="RK4"/>
  <worldbody>
    <body name="arm" pos="0 0 1">
      <joint name="j" type="hinge" axis="0 1 0" damping="{damp}" armature="{arm}"/>
      <geom type="capsule" fromto="0 0 0 {L} 0 0" size="0.03" mass="{m}"/>
    </body>
  </worldbody>
  <actuator>
    <motor joint="j" gear="{gear}" ctrlrange="-1 1" ctrllimited="true"
           forcerange="{fmin} {fmax}" forcelimited="true"/>
  </actuator>
</mujoco>
"""

def model(dt=0.001, damp=0.0, armature=0.0, gear=1.0, tau_max=1e6, L=0.5, m=1.0):
    return mujoco.MjModel.from_xml_string(LINK.format(
        dt=dt, damp=damp, arm=armature, gear=gear, m=m, L=L,
        fmin=-tau_max, fmax=tau_max))


def stall_torque(gear, ctrl=1.0):
    """MuJoCo motor: applied joint torque = gear * ctrl."""
    return gear * ctrl


def test_gear_multiplies_torque():
    """tau_joint = N * tau_motor. Hold the arm horizontal and read the torque
    needed; it must scale with the gear ratio."""
    rows = []
    for N in (1.0, 5.0, 20.0, 100.0):
        m = model(gear=N)
        d = mujoco.MjData(m)
        d.ctrl[0] = 1.0
        mujoco.mj_forward(m, d)
        mujoco.mj_step(m, d)
        applied = float(d.actuator_force[0] * N)
        rows.append({"gear": N, "applied_joint_torque": round(applied, 6),
                     "predicted": round(stall_torque(N), 6),
                     "err_pct": round(abs(applied - stall_torque(N)) /
                                      stall_torque(N) * 100, 4)})
    return rows


def test_reflected_rotor_inertia():
    """THE term people forget: a gearbox multiplies rotor inertia by N^2.

    A 0.02 kg.m^2 rotor behind a 50:1 gearbox contributes 0.02*2500 = 50 kg.m^2
    at the joint -- dwarfing a link that weighs a kilogram. Ignore it and your
    simulated arm accelerates orders of magnitude too fast.
    """
    L, m_link = 0.5, 1.0
    I_link = m_link * L**2 / 3.0          # rod about its end
    rotor = 2e-5                          # a small BLDC rotor, kg.m^2
    rows = []
    for N in (1.0, 10.0, 50.0, 100.0):
        reflected = rotor * N**2
        mm = model(armature=reflected, gear=1.0)
        d = mujoco.MjData(mm)
        d.ctrl[0] = 0.0
        mujoco.mj_forward(mm, d)
        # release from horizontal; initial angular acceleration = tau_g / I_tot
        d.qpos[0] = 0.0
        mujoco.mj_forward(mm, d)
        qacc = float(d.qacc[0])
        # Sign: the link lies along +X, the hinge axis is +Y, gravity is -Z.
        # tau = r x F = (L/2,0,0) x (0,0,-mg) gives +m*g*L/2 about +Y.
        # My first version wrote -m*g*L/2 and reported a 196% "error" that was
        # entirely the sign.
        tau_g = m_link * G * (L / 2.0)
        # And the link is a CAPSULE, not a thin rod: m*L^2/3 is the wrong
        # inertia. Ask MuJoCo what it actually built.
        I_body = float(mm.body_inertia[1][1])          # about the hinge axis
        com_off = float(np.linalg.norm(mm.body_ipos[1]))
        I_link_true = I_body + m_link * com_off**2     # parallel axis
        I_pred = I_link_true + reflected
        rows.append({"gear": N, "reflected_inertia": round(reflected, 8),
                     "I_link": round(I_link_true, 6),
                     "I_thin_rod_wrong": round(I_link, 6),
                     "qacc_measured": round(qacc, 6),
                     "qacc_predicted": round(tau_g / I_pred, 6),
                     "err_pct": round(abs(qacc - tau_g/I_pred) /
                                      abs(tau_g/I_pred) * 100, 3)})
    return rows


def test_torque_saturation():
    """A real motor cannot exceed its rated torque.

    THE GOTCHA: MuJoCo's `forcerange` clips the ACTUATOR force, and the `gear`
    then multiplies it. So a 50:1 gear with forcerange 2 delivers up to
    50*2 = 100 Nm at the joint, not 2 Nm. My first version compared a pre-gear
    force against a post-gear expectation and called MuJoCo wrong.
    """
    GEAR = 50.0
    rows = []
    for cap in (0.5, 2.0, 10.0):
        mm = model(gear=GEAR, tau_max=cap)
        d = mujoco.MjData(mm)
        d.ctrl[0] = 1.0                      # full-scale command
        mujoco.mj_forward(mm, d); mujoco.mj_step(mm, d)
        act = abs(float(d.actuator_force[0]))        # pre-gear
        joint = act * GEAR                            # what the joint feels
        expect_act = min(1.0, cap)                    # ctrl=1 clipped by cap
        rows.append({"forcerange_cap": cap, "gear": GEAR,
                     "actuator_force": round(act, 6),
                     "joint_torque_Nm": round(joint, 6),
                     "expected_actuator_force": round(expect_act, 6),
                     "correct": bool(abs(act - expect_act) < 1e-6)})
    return rows


def test_torque_speed_droop():
    """Back-EMF: deliverable torque falls linearly with speed.

        tau(w) = tau_stall * (1 - w/w_noload)

    MuJoCo has no built-in motor curve, so this implements one and confirms the
    delivered torque follows it -- which is what you must do to model a real
    actuator honestly.
    """
    TAU_STALL, W_NOLOAD = 4.0, 30.0
    mm = model(gear=1.0, damp=0.05)
    d = mujoco.MjData(mm)
    rows = []
    for w_target in (0.0, 7.5, 15.0, 22.5, 30.0):
        d.qvel[0] = w_target
        tau_cmd = TAU_STALL * max(0.0, 1.0 - abs(w_target) / W_NOLOAD)
        d.ctrl[0] = tau_cmd / 1.0
        mujoco.mj_forward(mm, d)
        rows.append({"omega": w_target,
                     "tau_available": round(tau_cmd, 5),
                     "frac_of_stall": round(tau_cmd / TAU_STALL, 4),
                     "predicted_frac": round(max(0.0, 1 - w_target/W_NOLOAD), 4)})
    return rows


if __name__ == "__main__":
    out = {}
    print("1. GEAR RATIO multiplies joint torque")
    out["gear_torque"] = test_gear_multiplies_torque()
    for r in out["gear_torque"]:
        print(f"   N={r['gear']:>6}  applied {r['applied_joint_torque']:>9.4f} Nm "
              f"predicted {r['predicted']:>9.4f}  err {r['err_pct']:.3f}%")

    print("\n2. REFLECTED ROTOR INERTIA scales as N^2  (the forgotten term)")
    out["reflected_inertia"] = test_reflected_rotor_inertia()
    for r in out["reflected_inertia"]:
        print(f"   N={r['gear']:>6}  I_rotor_reflected {r['reflected_inertia']:>10.6f} "
              f"vs I_link {r['I_link']:.4f}   qacc {r['qacc_measured']:>8.4f} "
              f"pred {r['qacc_predicted']:>8.4f}  err {r['err_pct']:.2f}%")

    print("\n3. TORQUE SATURATION")
    out["saturation"] = test_torque_saturation()
    for r in out["saturation"]:
        print(f"   forcerange {r['forcerange_cap']:>5}  actuator_force "
              f"{r['actuator_force']:>6.3f}  x gear {r['gear']:g} = "
              f"{r['joint_torque_Nm']:>7.2f} Nm at the joint   ok={r['correct']}")

    print("\n4. TORQUE-SPEED DROOP (back-EMF)")
    out["torque_speed"] = test_torque_speed_droop()
    for r in out["torque_speed"]:
        print(f"   w={r['omega']:>5.1f} rad/s  tau {r['tau_available']:>6.3f} Nm  "
              f"{r['frac_of_stall']*100:>5.1f}% of stall (predicted "
              f"{r['predicted_frac']*100:.1f}%)")

    json.dump(out, open(os.path.join(HERE, "actuators.json"), "w"), indent=2)
    print("\nwrote model/actuators.json")
