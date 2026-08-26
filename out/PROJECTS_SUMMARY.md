# Four projects against the Robotics Simulation Engineer requirements

Built on Kaggle's free GPU tier. Everything measured, nothing estimated.

---

## A — Author a robot, validate it across three simulators

*JD: "Design and implement high-fidelity robot models (URDF/MJCF) with accurate
kinematics, dynamics, and contact properties"*

3-DOF arm authored from scratch: analytic inertia tensors, joint limits,
damping, joint friction, contact friction. **One parameter source emits MJCF,
URDF and SDF**, so the formats cannot drift.

    151 cross-format comparisons     0 mismatches
    2000-config forward kinematics   3.331e-16 m max error

**The bug worth reporting:** the first run passed all 147 numeric comparisons
with an FK error of 0.23 m. In URDF the link frame sits at the joint, so
`<origin xyz="0 0 0"/>` put every centre of mass on its own joint axis —
correct masses attached to the wrong places.

> Comparing numbers proves the FILES agree.
> Comparing kinematics proves the ROBOTS agree.

Imported into Isaac Sim 6.0: correct DOF, joint names, masses to 7 digits,
damping as authored, no spurious drives, limits enforced in both engines.
A permuted inertia diagonal turned out to be a rotated principal frame
(`principalAxes = 0.5,0.5,0.5,0.5`), not a defect — checking one more attribute
prevented a false bug report.

One divergence (`j_link3`) remains **unexplained and is recorded as such**.

Details: `model/RESULTS.md`

---

## B — Sensor simulation, every reading checked against theory

*JD nice-to-have: "Knowledge of sensor simulation — cameras, LiDAR, IMUs,
force/torque sensors"*

| sensor | result |
|---|---|
| **Effort** | ✅ gravity-loaded Franka: −7.6 Nm shoulder, +16.9 Nm elbow, ~0 on joints that do not fight gravity |
| **Joint state** | ✅ 9 DOF, 0.016 rad commanded↔readback |
| Contact / IMU | class exists; no Kit command in 6.0 authors the schema prim |
| LiDAR / Radar | only **RTX** variants registered — needs the renderer |

Verifying a sensor *exists* is worthless; each of these asserts a closed-form
value (contact force = mg, IMU proper acceleration = g, holding torque = mgL).

**The structural finding:** pure-physics sensing works on free hardware;
anything routed through the render pipeline does not. Effort and joint state are
solver quantities. LiDAR casts rays through an RTX pipeline that never
initialises.

Also documented: `isaacsim.sensors.physx` is **deprecated** and holds only
lidar/proximity stubs. The real classes live in
`isaacsim.sensors.experimental.physics`, and their constructors take a
**positional `path`** — not the `prim_path=` every tutorial shows.

---

## C — CI/CD for simulation testing

*JD nice-to-have: "Experience with CI/CD for simulation testing and automated
validation"*

    17 gates, ~0.6 s, GitHub Actions on push / PR / weekly

Gates assert against **closed-form physics, not golden files** — golden values
rot the moment someone regenerates them; `v²/(2μg)` cannot be regenerated.

Four tests verify **the gates actually bite**, feeding each deliberately broken
input. The sharpest swaps Coulomb friction for linear velocity drag and confirms
the mass-independence gate rejects it — proving that test distinguishes real
friction from something that merely resembles it.

CI regenerates the model from spec rather than testing committed files, and
fails if they differ — enforcing single-source-of-truth mechanically.

Details: `tests/README.md`

---

## D — Reinforcement learning: a diagnosis, not a policy

*JD nice-to-have: "reinforcement learning in simulation"*

Four attempts (CEM, then PPO ×3) all produced policies indistinguishable from
random. Rather than tune a fifth time, I instrumented the environment.

    action_scale = 100      -> an action of 1.0 is 100 N
    logstd = -1             -> exploration noise alone was ±37 N

That was real, and fixing it changed nothing. The deeper finding came from the
observation ranges under a 200 N action differential:

    cart position   range 1.5 - 3.0 m     responds
    cart velocity   range 5.0 - 9.6 m/s   responds
    dim 2           range 0.0             STATIC
    dim 3           range ≤ 0.0008        STATIC

**Half the state vector never changes.** The pole degree of freedom does not
move, so the task carries no learnable signal — every policy is optimal because
every policy is irrelevant.

Honest limit: this shows the pole DOF is static on this build. Whether that is
an environment-configuration issue or a misread observation layout is
unresolved.

---

## What the free tier established overall

Isaac Sim physics (49/50 robot vendors, 65,536 parallel envs at 812k steps/s),
MuJoCo, MJX, Gazebo (via conda), ROS 2 with a working Isaac bridge, and both
T4s at 1.87×. **Rendering is the one thing free hardware genuinely cannot do.**
