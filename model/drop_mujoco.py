"""Reference trajectory: release the arm from a fixed pose and let gravity act.

Same initial condition will be replayed in Isaac Sim and Gazebo. Joint damping
and friction are in the model, so the arm settles rather than oscillating
forever -- which makes the final resting pose a second, sharper check than the
trajectory alone.
"""
import json, os, sys
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
Q0 = [0.5, -0.8, 1.2]          # released from here, zero velocity
DT, STEPS = 0.002, 1500        # 3 s

m = mujoco.MjModel.from_xml_path(os.path.join(HERE, "arm3.xml"))
d = mujoco.MjData(m)
d.qpos[:] = Q0
mujoco.mj_forward(m, d)

traj = []
for i in range(STEPS):
    mujoco.mj_step(m, d)
    if i % 15 == 0:                      # 100 Hz sampling
        traj.append({"t": round((i+1)*DT, 5),
                     "q": [round(float(v), 6) for v in d.qpos]})

out = {"engine": "mujoco", "version": mujoco.__version__,
       "q0": Q0, "dt": DT, "steps": STEPS,
       "final_q": [round(float(v), 6) for v in d.qpos],
       "final_qvel_norm": round(float(np.linalg.norm(d.qvel)), 6),
       "trajectory": traj}
json.dump(out, open(os.path.join(HERE, "drop_mujoco.json"), "w"), indent=1)
print(f"MuJoCo {mujoco.__version__}")
print(f"  q0        {Q0}")
print(f"  final q   {out['final_q']}")
print(f"  |qvel|    {out['final_qvel_norm']:.6f}  (settled: {out['final_qvel_norm'] < 1e-3})")
print(f"  samples   {len(traj)}")
