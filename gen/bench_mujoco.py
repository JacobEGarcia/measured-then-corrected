"""
MuJoCo half of the MuJoCo-vs-Isaac-Sim benchmark (notebook 5).

Runs on any machine including Apple Silicon -- which is precisely the point of
the comparison: MuJoCo runs anywhere, Isaac Sim needs an NVIDIA RT-core GPU.

The Isaac Sim half (gen/bench_isaac.py) runs on the Lightning box and writes a
JSON with the same schema, so the notebook can join them.

    python3 gen/bench_mujoco.py --out out/bench_mujoco.json
"""
import argparse
import json
import platform
import time

import mujoco
import numpy as np

# A pendulum has a closed-form energy invariant, so we can measure integrator
# accuracy rather than just speed. Speed alone is a bad benchmark: any engine
# can be fast if it is wrong.
PENDULUM = """
<mujoco>
  <option timestep="{dt}" integrator="{integrator}" gravity="0 0 -9.81"/>
  <worldbody>
    <body name="arm" pos="0 0 1">
      <joint name="hinge" type="hinge" axis="0 1 0" damping="0"/>
      <geom name="rod" type="capsule" fromto="0 0 0 0 0 -0.5"
            size="0.02" density="1000"/>
    </body>
  </worldbody>
</mujoco>
"""

FALLING_BOXES = """
<mujoco>
  <option timestep="0.004" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" size="10 10 0.1"/>
    {bodies}
  </worldbody>
</mujoco>
"""


def bench_throughput(n_boxes, steps=2000, seed=0):
    """Contact-rich throughput: n boxes dropped onto a plane."""
    rng = np.random.default_rng(seed)
    bodies = []
    for i in range(n_boxes):
        x, y = rng.uniform(-1.5, 1.5, 2)
        z = 0.3 + 0.35 * (i % 12)
        bodies.append(
            f'<body name="b{i}" pos="{x:.3f} {y:.3f} {z:.3f}">'
            f'<freejoint/><geom type="box" size="0.05 0.05 0.05"/></body>')
    model = mujoco.MjModel.from_xml_string(
        FALLING_BOXES.format(bodies="\n    ".join(bodies)))
    data = mujoco.MjData(model)

    mujoco.mj_step(model, data)          # warm up, exclude JIT/alloc cost
    mujoco.mj_resetData(model, data)

    t0 = time.perf_counter()
    for _ in range(steps):
        mujoco.mj_step(model, data)
    wall = time.perf_counter() - t0

    sim_time = steps * model.opt.timestep
    return {
        "n_boxes": n_boxes,
        "steps": steps,
        "wall_s": round(wall, 4),
        "steps_per_s": round(steps / wall, 1),
        "realtime_factor": round(sim_time / wall, 2),
        "n_contacts_final": int(data.ncon),
    }


def bench_energy(dt, integrator="RK4", seconds=10.0):
    """Integrator accuracy: energy drift of an undamped pendulum.

    An undamped pendulum conserves energy exactly. Any drift is pure
    integrator error, which makes this a clean apples-to-apples accuracy
    metric across engines.
    """
    model = mujoco.MjModel.from_xml_string(
        PENDULUM.format(dt=dt, integrator=integrator))
    data = mujoco.MjData(model)
    data.qpos[0] = np.pi / 3          # 60 deg from rest
    mujoco.mj_forward(model, data)

    def energy():
        mujoco.mj_energyPos(model, data)
        mujoco.mj_energyVel(model, data)
        return float(data.energy[0] + data.energy[1])

    e0 = energy()
    n = int(seconds / dt)
    drift = []
    for i in range(n):
        mujoco.mj_step(model, data)
        if i % max(1, n // 200) == 0:
            drift.append(abs(energy() - e0) / max(abs(e0), 1e-9))

    return {
        "dt": dt,
        "integrator": integrator,
        "seconds": seconds,
        "rel_energy_drift_final": float(drift[-1]),
        "rel_energy_drift_max": float(max(drift)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/bench_mujoco.json")
    ap.add_argument("--steps", type=int, default=2000)
    args = ap.parse_args()

    print("MuJoCo", mujoco.__version__, "on", platform.platform())
    print("\n-- throughput (contact-rich) --")
    tp = []
    for n in (1, 8, 32, 128, 512):
        r = bench_throughput(n, steps=args.steps)
        tp.append(r)
        print(f"  {n:4d} boxes: {r['steps_per_s']:9.1f} steps/s  "
              f"realtime x{r['realtime_factor']:<7.2f} contacts={r['n_contacts_final']}")

    print("\n-- integrator accuracy (energy drift) --")
    acc = []
    for dt in (0.01, 0.005, 0.002, 0.001):
        for integ in ("Euler", "RK4"):
            r = bench_energy(dt, integ)
            acc.append(r)
            print(f"  dt={dt:<6} {integ:<6} rel drift after 10s: "
                  f"{r['rel_energy_drift_final']:.3e}")

    out = {
        "engine": "mujoco",
        "version": mujoco.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "accelerator": "CPU",
        "throughput": tp,
        "accuracy": acc,
    }
    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
