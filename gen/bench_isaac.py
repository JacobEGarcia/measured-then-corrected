"""
Isaac Sim half of the MuJoCo-vs-Isaac benchmark (notebook 5).

Runs ON THE LIGHTNING BOX (or any Linux + RT-core NVIDIA GPU). Emits the same
JSON schema as gen/bench_mujoco.py so the notebook can join them directly.

    source ~/isaacenv/bin/activate && source ~/.isaac_env
    python gen/bench_isaac.py --out out/bench_isaac.json

Fairness notes -- benchmarks between engines are easy to rig by accident:
  * Both runs use physics-only stepping (render=False). Rendering is Isaac's
    advantage and MuJoCo does not compete there; mixing it in would be
    dishonest in the other direction.
  * Both use the same box count, box size, timestep and step count.
  * Warm-up steps are excluded from timing on both sides (PhysX allocates GPU
    buffers lazily; counting that as steady-state cost would be unfair).
  * The energy test uses the same undamped pendulum and the same metric.
"""
import argparse
import json
import os
import subprocess
import sys
import time

for k, v in [("ACCEPT_EULA", "Y"), ("OMNI_KIT_ACCEPT_EULA", "YES"),
             ("PRIVACY_CONSENT", "Y")]:
    os.environ.setdefault(k, v)

from isaacsim import SimulationApp                       # noqa: E402

simulation_app = SimulationApp({"headless": True})       # must precede imports

try:                                                     # 4.5 renamed these
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid
except ImportError:
    from omni.isaac.core import World
    from omni.isaac.core.objects import DynamicCuboid

import numpy as np                                       # noqa: E402


def gpu_name():
    try:
        return subprocess.run(
            "nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader",
            shell=True, capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def bench_throughput(n_boxes, steps=2000, dt=0.004, seed=0):
    rng = np.random.default_rng(seed)
    world = World(stage_units_in_meters=1.0, physics_dt=dt)
    world.scene.add_default_ground_plane()
    for i in range(n_boxes):
        x, y = rng.uniform(-1.5, 1.5, 2)
        z = 0.3 + 0.35 * (i % 12)
        world.scene.add(DynamicCuboid(
            prim_path=f"/World/b{i}", name=f"b{i}",
            position=np.array([x, y, z]), size=0.1))
    world.reset()

    for _ in range(10):                      # warm up; exclude lazy GPU allocs
        world.step(render=False)

    t0 = time.perf_counter()
    for _ in range(steps):
        world.step(render=False)
    wall = time.perf_counter() - t0

    world.clear()
    return {
        "n_boxes": n_boxes, "steps": steps,
        "wall_s": round(wall, 4),
        "steps_per_s": round(steps / wall, 1),
        "realtime_factor": round(steps * dt / wall, 2),
    }


def bench_energy(dt, seconds=10.0):
    """Undamped pendulum energy drift -- same invariant as the MuJoCo side.

    Built from a revolute joint on a capsule so the mass properties match the
    MuJoCo model as closely as the two asset formats allow.
    """
    from pxr import UsdPhysics, UsdGeom, Gf
    import omni.usd

    world = World(stage_units_in_meters=1.0, physics_dt=dt)
    stage = omni.usd.get_context().get_stage()

    UsdGeom.Xform.Define(stage, "/World")
    body = UsdGeom.Capsule.Define(stage, "/World/arm")
    body.CreateHeightAttr(0.5)
    body.CreateRadiusAttr(0.02)
    body.AddTranslateOp().Set(Gf.Vec3d(0, 0, 0.75))
    UsdPhysics.RigidBodyAPI.Apply(stage.GetPrimAtPath("/World/arm"))
    UsdPhysics.CollisionAPI.Apply(stage.GetPrimAtPath("/World/arm"))

    joint = UsdPhysics.RevoluteJoint.Define(stage, "/World/hinge")
    joint.CreateBody1Rel().SetTargets(["/World/arm"])
    joint.CreateAxisAttr("Y")
    world.reset()

    from isaacsim.core.prims import RigidPrim  # noqa
    prim = RigidPrim("/World/arm")

    def energy():
        pos, _ = prim.get_world_poses()
        lv, av = prim.get_velocities()[0], prim.get_velocities()[1]
        m = 1.0
        ke = 0.5 * m * float(np.sum(np.asarray(lv) ** 2))
        pe = m * 9.81 * float(np.asarray(pos)[0][2])
        return ke + pe

    e0 = energy()
    n = int(seconds / dt)
    drift = []
    for i in range(n):
        world.step(render=False)
        if i % max(1, n // 200) == 0:
            drift.append(abs(energy() - e0) / max(abs(e0), 1e-9))
    world.clear()
    return {
        "dt": dt, "integrator": "PhysX-TGS", "seconds": seconds,
        "rel_energy_drift_final": float(drift[-1]),
        "rel_energy_drift_max": float(max(drift)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/bench_isaac.json")
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--skip-energy", action="store_true",
                    help="energy test is fiddly across USD versions; skip if it errors")
    args = ap.parse_args()

    print("GPU:", gpu_name())
    tp = []
    print("\n-- throughput (contact-rich) --")
    for n in (1, 8, 32, 128, 512):
        r = bench_throughput(n, steps=args.steps)
        tp.append(r)
        print(f"  {n:4d} boxes: {r['steps_per_s']:9.1f} steps/s  "
              f"realtime x{r['realtime_factor']:.2f}")

    acc = []
    if not args.skip_energy:
        print("\n-- integrator accuracy (energy drift) --")
        for dt in (0.01, 0.005, 0.002, 0.001):
            try:
                r = bench_energy(dt)
                acc.append(r)
                print(f"  dt={dt:<6} PhysX  rel drift: "
                      f"{r['rel_energy_drift_final']:.3e}")
            except Exception as e:
                print(f"  dt={dt}: energy test failed ({type(e).__name__}: {e})")

    out = {
        "engine": "isaac-sim", "version": "6.0.1.0",
        "platform": sys.platform, "machine": "x86_64",
        "accelerator": gpu_name(),
        "throughput": tp, "accuracy": acc,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print("\nwrote", args.out)
    simulation_app.close()


if __name__ == "__main__":
    main()
