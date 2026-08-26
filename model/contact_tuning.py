"""Contact parameters: what solref/solimp actually control, measured.

JD: "Solid understanding of rigid-body dynamics, CONTACT MECHANICS, and control
theory" / "Tune physics parameters ... to maximize sim-to-real transfer."

MuJoCo's contacts are soft constraints, not hard stops. `solref=(timeconst,
dampratio)` sets the stiffness and damping of the contact spring; `solimp` sets
how the constraint impedance varies with penetration depth.

Nobody's intuition for these is reliable, so this measures three things that
matter in practice and have checkable answers:

  1. PENETRATION  -- how far a resting box sinks into the floor
  2. RESTITUTION  -- bounce height vs the coefficient you asked for
  3. STABILITY    -- where the timestep/stiffness combination explodes

Getting these wrong is the classic "my policy exploits the simulator" bug: a
gripper that holds objects by sinking into them transfers to nothing.
"""
import json, os
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
G = 9.81

BOX = """
<mujoco>
  <option timestep="{dt}" gravity="0 0 -9.81" integrator="{integ}"/>
  <worldbody>
    <geom name="floor" type="plane" size="10 10 .1" solref="{sr}" solimp="{si}"/>
    <body name="b" pos="0 0 {h}">
      <freejoint/>
      <geom name="g" type="box" size=".05 .05 .05" mass="{m}"
            solref="{sr}" solimp="{si}"/>
    </body>
  </worldbody>
</mujoco>
"""

def run(dt=0.002, solref="0.02 1", solimp="0.9 0.95 0.001",
        h=0.05, mass=1.0, steps=1500, integ="RK4", v0=0.0):
    m = mujoco.MjModel.from_xml_string(
        BOX.format(dt=dt, sr=solref, si=solimp, h=h, m=mass, integ=integ))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    if v0: d.qvel[2] = v0
    zs = []
    for _ in range(steps):
        mujoco.mj_step(m, d)
        zs.append(float(d.qpos[2]))
    return m, d, np.array(zs)


def penetration_vs_solref():
    """A resting box should sit with its centre at exactly half its extent
    (0.05 m). Anything less is penetration -- the contact spring compressing
    under the box's own weight."""
    rows = []
    for tc in (0.001, 0.005, 0.01, 0.02, 0.05):
        _, _, zs = run(solref=f"{tc} 1")
        rest = float(np.median(zs[-200:]))
        rows.append({"solref_timeconst": tc,
                     "rest_z": round(rest, 7),
                     "penetration_mm": round((0.05 - rest) * 1000, 4)})
    return rows


def penetration_vs_mass():
    """MEASURED RESULT, contrary to spring intuition: penetration does NOT
    scale with load.

    I predicted a heavier box would compress the contact further. Across a
    1000x mass range the penetration is identical to four decimals, because
    MuJoCo's solref is parameterised in TIME (timeconst, dampratio), not
    stiffness -- the solver normalises by the effective mass so contact
    response is consistent across scales.

    Practical consequence: you can change a payload's mass without retuning
    contacts, which is not true of a naive stiffness-based contact model."""
    rows = []
    for mass in (0.1, 1.0, 10.0, 100.0):
        _, _, zs = run(mass=mass)
        rest = float(np.median(zs[-200:]))
        rows.append({"mass_kg": mass, "rest_z": round(rest, 7),
                     "penetration_mm": round((0.05 - rest) * 1000, 4)})
    return rows


def restitution_check():
    """solref's damping ratio controls bounce. Drop from 0.5 m and compare the
    rebound height against the requested coefficient of restitution:
        h_bounce / h_drop = e^2
    """
    rows = []
    H = 0.5
    for damp in (1.0, 0.7, 0.4, 0.2):
        _, _, zs = run(solref=f"0.02 {damp}", h=H, steps=3000)
        # first local max after the initial impact
        below = np.where(zs < 0.08)[0]
        if len(below) == 0:
            rows.append({"solref_dampratio": damp, "note": "never contacted"}); continue
        i0 = int(below[0])
        after = zs[i0:]
        peak = float(after.max())
        e_meas = float(np.sqrt(max(peak - 0.05, 0.0) / (H - 0.05)))
        rows.append({"solref_dampratio": damp,
                     "rebound_height_m": round(peak, 5),
                     "restitution_measured": round(e_meas, 4)})
    return rows


def stability_envelope():
    """Where does it blow up? Stiff contacts (small timeconst) need small
    timesteps. This maps the safe operating region instead of discovering it
    mid-training-run."""
    rows = []
    for dt in (0.0005, 0.001, 0.002, 0.005, 0.01):
        for tc in (0.0005, 0.002, 0.01, 0.05):
            try:
                # 1.5 s of SIMULATED time for every dt. Using a fixed step
                # count gave dt=0.0005 only 0.4 s -- the box had barely landed,
                # and its "16 mm penetration" was really an unsettled box.
                steps = int(round(1.5 / dt))
                _, d, zs = run(dt=dt, solref=f"{tc} 1", h=0.3, steps=steps)
                bad = (not np.all(np.isfinite(zs))) or float(np.max(np.abs(zs))) > 5.0
                rest = float(np.median(zs[-int(0.2/dt):]))
                pen = (0.05 - rest) * 1000
            except Exception:
                bad, pen = True, float("nan")
            rows.append({"dt": dt, "solref_timeconst": tc,
                         "stable": bool(not bad),
                         "penetration_mm": None if bad else round(pen, 3),
                         # rule of thumb: the contact timeconst should be
                         # several timesteps long
                         "timeconst_over_dt": round(tc / dt, 2)})
    return rows


if __name__ == "__main__":
    out = {}
    print("1. PENETRATION vs solref timeconst  (resting box, want z = 0.05 exactly)")
    out["penetration_vs_solref"] = penetration_vs_solref()
    for r in out["penetration_vs_solref"]:
        print(f"   timeconst {r['solref_timeconst']:<7} rest_z {r['rest_z']:.6f}  "
              f"penetration {r['penetration_mm']:>8.4f} mm")

    print("\n2. PENETRATION vs LOAD  (same contact, heavier box)")
    out["penetration_vs_mass"] = penetration_vs_mass()
    for r in out["penetration_vs_mass"]:
        print(f"   mass {r['mass_kg']:>6} kg   penetration {r['penetration_mm']:>9.4f} mm")

    print("\n3. RESTITUTION vs solref dampratio  (drop 0.5 m)")
    out["restitution"] = restitution_check()
    for r in out["restitution"]:
        if "note" in r:
            print(f"   dampratio {r['solref_dampratio']:<5} {r['note']}")
        else:
            print(f"   dampratio {r['solref_dampratio']:<5} rebound "
                  f"{r['rebound_height_m']:.4f} m   e = {r['restitution_measured']:.4f}")

    print("\n4. STABILITY ENVELOPE  (stable? / penetration)")
    out["stability"] = stability_envelope()
    print(f"   {'dt':>8} {'timeconst':>10} {'tc/dt':>7} {'stable':>8} {'pen mm':>10}")
    for r in out["stability"]:
        pen = r['penetration_mm']
        pen_s = "        --" if pen is None else f"{pen:>10.3f}"
        print(f"   {r['dt']:>8} {r['solref_timeconst']:>10} "
              f"{r['timeconst_over_dt']:>7} {str(r['stable']):>8} {pen_s}")

    json.dump(out, open(os.path.join(HERE, "contact_tuning.json"), "w"), indent=2)
    print("\nwrote model/contact_tuning.json")
