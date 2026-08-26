"""MuJoCo side of the cross-engine comparison.

Same experiment will run in Isaac Sim: launch a box at a known speed across a
plane of known friction, measure where it stops. Coulomb gives the answer in
closed form, so BOTH engines can be checked against theory independently
rather than only against each other.

One control matters more than it looks: friction is set identically on the box
AND the ground. MuJoCo combines contact friction with elementwise max, PhysX
averages -- so with different values the comparison would measure the
combination rule instead of the solver.
"""
import json, time
import mujoco
import numpy as np

XML = """
<mujoco>
  <option timestep="{dt}" gravity="0 0 -9.81" integrator="RK4"/>
  <worldbody>
    <geom name="floor" type="plane" size="20 20 .1" friction="{mu} 0 0"/>
    <body name="box" pos="0 0 0.0501">
      <freejoint/>
      <geom name="box" type="box" size=".05 .05 .05" mass="1"
            friction="{mu} 0 0" solref="0.002 1" solimp="0.99 0.999 0.001"/>
    </body>
  </worldbody>
</mujoco>
"""

def run(mu, v0=2.0, dt=1/240, steps=1600):
    m = mujoco.MjModel.from_xml_string(XML.format(mu=mu, dt=dt))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    d.qvel[0] = v0                      # launch along +x
    xs = []
    for _ in range(steps):
        mujoco.mj_step(m, d)
        xs.append(float(d.qpos[0]))
    xs = np.array(xs)
    speed = float(np.linalg.norm(d.qvel[:3]))
    return {"mu": mu, "stop_x": round(float(xs[-1]), 5),
            "final_speed": round(speed, 5),
            "stopped": bool(speed < 0.01),
            "analytic": round(v0**2 / (2*mu*9.81), 5)}

if __name__ == "__main__":
    MUS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]
    t0 = time.time()
    rows = [run(mu) for mu in MUS]
    print(f"{'mu':>5} {'MuJoCo':>10} {'analytic':>10} {'err %':>8} {'stopped':>8}")
    for r in rows:
        e = abs(r["stop_x"] - r["analytic"]) / r["analytic"] * 100
        r["err_pct_vs_analytic"] = round(e, 2)
        print(f"{r['mu']:>5.2f} {r['stop_x']:>10.4f} {r['analytic']:>10.4f} "
              f"{e:>7.1f}% {str(r['stopped']):>8}")
    json.dump({"engine": "mujoco", "version": mujoco.__version__,
               "v0": 2.0, "dt": 1/240, "integrator": "RK4",
               "note": "friction identical on box and floor to neutralise "
                       "differing contact-combination rules",
               "wall_s": round(time.time()-t0, 1), "runs": rows},
              open("out/sim2sim_mujoco.json", "w"), indent=2)
    print("\nwrote out/sim2sim_mujoco.json")
