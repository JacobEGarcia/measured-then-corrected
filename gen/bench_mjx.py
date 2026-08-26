"""
MJX (MuJoCo XLA) batch-scaling benchmark -- third result section for notebook 5.

Why this matters: comparing "MuJoCo CPU" against "Isaac Sim GPU" conflates two
separate variables -- the engine AND the parallelism model. MJX is the same
MuJoCo physics compiled through JAX, so running it batched isolates the
parallelism axis by itself.

Runs on whatever JAX backend is available. On CPU the absolute numbers are
modest, but the SHAPE of the scaling curve is the finding, and that shape is
what generalizes to a GPU.

    python gen/bench_mjx.py --out out/bench_mjx.json
"""
import argparse
import json
import os
import platform
import time

import jax
import jax.numpy as jnp
import mujoco
import numpy as np
from mujoco import mjx

# Deliberately simple: MJX does not support every MuJoCo feature, and a
# pendulum-on-a-cart exercises joints and actuation without hitting the
# unsupported-feature wall.
CARTPOLE = """
<mujoco>
  <option timestep="0.005" integrator="Euler"/>
  <worldbody>
    <body name="cart" pos="0 0 0">
      <joint name="slider" type="slide" axis="1 0 0" damping="0.1"/>
      <geom name="cart" type="box" size="0.1 0.05 0.05" mass="1"/>
      <body name="pole" pos="0 0 0.05">
        <joint name="hinge" type="hinge" axis="0 1 0" damping="0.01"/>
        <geom name="pole" type="capsule" fromto="0 0 0 0 0 0.5"
              size="0.02" mass="0.1"/>
      </body>
    </body>
  </worldbody>
  <actuator>
    <motor joint="slider" gear="10" ctrlrange="-1 1"/>
  </actuator>
</mujoco>
"""


def bench_batch(batch_size, steps=300, seed=0):
    """Step `batch_size` independent cartpoles in parallel via vmap."""
    model = mujoco.MjModel.from_xml_string(CARTPOLE)
    mx = mjx.put_model(model)

    rng = jax.random.PRNGKey(seed)
    keys = jax.random.split(rng, batch_size)

    @jax.vmap
    def init(key):
        d = mjx.make_data(mx)
        # Small random initial pole angle so the batch is not degenerate.
        qpos = d.qpos.at[1].set(jax.random.uniform(key, (), minval=-0.1,
                                                   maxval=0.1))
        return d.replace(qpos=qpos)

    @jax.jit
    @jax.vmap
    def step(d):
        return mjx.step(mx, d)

    data = init(keys)

    # Compile once outside the timing loop. JIT cost is real but it is a
    # one-off, and charging it to per-step throughput would misrepresent the
    # steady state that actually matters for RL training.
    t_compile0 = time.perf_counter()
    data = step(data)
    jax.block_until_ready(data.qpos)
    compile_s = time.perf_counter() - t_compile0

    t0 = time.perf_counter()
    for _ in range(steps):
        data = step(data)
    jax.block_until_ready(data.qpos)
    wall = time.perf_counter() - t0

    total_steps = steps * batch_size
    return {
        "batch_size": batch_size,
        "steps_per_env": steps,
        "total_env_steps": total_steps,
        "compile_s": round(compile_s, 3),
        "wall_s": round(wall, 4),
        "env_steps_per_s": round(total_steps / wall, 1),
        "realtime_factor_total": round(
            total_steps * model.opt.timestep / wall, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/bench_mjx.json")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--batches", type=int, nargs="+",
                    default=[1, 4, 16, 64, 256, 1024])
    args = ap.parse_args()

    backend = jax.default_backend()
    devices = [str(d) for d in jax.devices()]
    print(f"JAX {jax.__version__} backend={backend} devices={devices}")
    print(f"{'batch':>7} {'env steps/s':>14} {'realtime':>12} {'compile':>9}")

    rows = []
    for b in args.batches:
        r = bench_batch(b, steps=args.steps)
        rows.append(r)
        print(f"{b:>7} {r['env_steps_per_s']:>14,.0f} "
              f"{r['realtime_factor_total']:>11,.0f}x {r['compile_s']:>8.2f}s")

    # The headline number: how much throughput batching buys over batch=1.
    base = rows[0]["env_steps_per_s"]
    for r in rows:
        r["speedup_vs_batch1"] = round(r["env_steps_per_s"] / base, 2)

    out = {
        "engine": "mjx",
        "mujoco_version": mujoco.__version__,
        "jax_version": jax.__version__,
        "backend": backend,
        "devices": devices,
        "platform": platform.platform(),
        "batch_scaling": rows,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print("\nspeedup vs batch=1:",
          {r["batch_size"]: r["speedup_vs_batch1"] for r in rows})
    print("wrote", args.out)


if __name__ == "__main__":
    main()
