# Maxing out Isaac Sim on Kaggle

Rendering is dead here; physics is not. This is the plan for everything the
free tier can actually do, and the salvage route for the two notebooks that
were designed around a renderer we do not have.

## What the constraint actually removes

| Needs a renderer | Does not |
|---|---|
| RGB / depth / segmentation images | Rigid-body and contact dynamics |
| Camera-based RL | State-based RL |
| Appearance domain randomization | **Physics** domain randomization |
| Photoreal synthetic datasets | Trajectory / contact / sensor datasets |

The right-hand column is most of what a robotics-simulation engineer actually
does. Losing the renderer is a real loss for perception work and close to
irrelevant for control work.

## Notebook 2 — was: synthetic image data

**Dead on Kaggle.** No renderer, no images. Two options:

- **A.** Keep it Lightning-only, publish when that box exists.
- **B.** Repoint it at *non-visual* synthetic data: contact-event datasets,
  joint-trajectory corpora, sensor streams. Still genuinely useful training
  data, still generated for free, and nobody has published it.

B is the better use of the constraint. A is the better notebook if Lightning
appears.

## Notebook 3 — was: appearance domain randomization

**Salvageable, and arguably improved.** Pivot from randomizing *appearance*
(colors, lighting, camera) to randomizing *physics* (mass, friction, damping,
restitution).

Why this is the stronger experiment:

- Appearance DR answers "does my vision model survive a new camera?"
- **Physics DR answers "does my controller survive a real robot?"** — which is
  the sim2real question that actually kills robotics projects.
- It needs no renderer, so it runs entirely on the free tier.
- The control and treatment arms stay perfectly matched: same task, same
  policy class, same budget, only the dynamics distribution differs.

**Experiment design:**

    Control   : tune a policy under nominal dynamics only
    Treatment : tune the same policy class under randomized dynamics
    Test      : evaluate BOTH across a held-out sweep of mass and friction,
                including values outside the training range

    Metric    : success rate vs dynamics offset

The interesting result is the shape of the curve, not just the mean — the
control arm should be sharp and brittle, the treatment arm flatter and wider.
And if randomization is pushed too far, the treatment arm should get *worse*,
because DR is not monotonic. That non-monotonicity is the finding worth
publishing; almost everyone reports DR as strictly good.

## Notebook 4 — Isaac Lab RL

Viable if `isaaclab` installs (under test). State-based tasks only —
cartpole and ant, not vision-based manipulation. Checkpoint aggressively:
Kaggle sessions cap at 12 hours and the disk is wiped between them.

## Notebook 5 — MuJoCo vs Isaac Sim

Currently missing its Isaac column because that half needs a GPU. The
capability probe measures Isaac Sim throughput on the same axis as
`bench_mujoco.py`, which completes the comparison **on identical hardware** —
a fairer benchmark than the usual cross-machine ones.

## Quota budget

30 GPU hr/week. Each run costs ~10 min of install plus the work. That is
roughly 100 runs a week available; we have used under 2 hours total.

The install is the dominant cost. If run count climbs past ~10, cache the
installed environment as a Kaggle Dataset and attach it instead of
reinstalling. Not worth the complexity before then.

---

# RESULT: the capability map (measured 2026-08-25)

| Capability | Free Kaggle T4 | Evidence |
|---|---|---|
| GPU PhysX pipeline | ✅ | `device: cuda:0` |
| Rigid body + contacts | ✅ | recovered g = 9.8100, error 0.000% |
| Articulated robots | ✅ | Franka Panda 9-DOF, joints actuating |
| Robot asset library | ✅ | 50 vendor folders reachable |
| Contact/IMU/Effort/JointState | ✅ | `isaacsim.sensors.experimental.physics` |
| Physics domain randomization | ✅ | reproduces Coulomb mass-independence |
| Isaac Lab | ✅ | 3.0.0b2.post1, 197 Gym environments |
| **Vectorized RL envs** | ✅ | **212,899 env steps/s at 4096 envs** |
| RTX rendering | ❌ | GPU Foundation never initialises |

## The headline number

Isaac Lab, `Isaac-Cartpole-Direct-v0`, free Kaggle T4:

    envs    env steps/s   policy steps/s   VRAM
      64        3,864.8            60.4    2.33 GB
     256       13,917.0            54.4    3.00 GB
    1024       55,565.9            54.3    3.81 GB
    4096      212,899.1            52.0    4.22 GB

**86% of perfect linear scaling** from 64 to 4096 environments, and
`policy_steps_per_s` is FLAT -- stepping 4096 environments costs the same
wall-clock as stepping 64. That is the entire argument for GPU simulation,
visible in one column.

At 4096 envs only 4.22 GB of the T4's 15 GB is used, so there is substantial
headroom left.

Note this is not comparable to the earlier MJX figure (1.5M steps/s on CPU at
batch 1024): MJX was stepping bare physics, while an Isaac Lab step also
computes observations, rewards, terminations and resets. Different work per
step.

## The nvrtc trap (five attempts)

Isaac Lab environments CONSTRUCT fine but fail on first `step()` with:

    RuntimeError: nvrtc: error: failed to open libnvrtc-builtins.so.13.0

torch 2.11.0+cu130 JIT-compiles a kernel and needs CUDA 13's runtime compiler.
Three separate traps stacked on top of each other:

1. **PyPI's `nvidia-cuda-nvrtc-cu13` is a 0.0 MB stub** (version 0.0.1). It
   installs successfully and provides nothing.
2. The real wheels are on **NVIDIA's index** under `nvidia-cuda-nvrtc`, where
   **13.0.88** matches cu130.
3. Even installed, NVRTC still cannot find them: **it resolves builtins
   relative to whichever `libnvrtc.so` the process loaded**, not via
   `LD_LIBRARY_PATH`. Torch ships its own copy in `torch/lib` and looks there.

Fix: install from NVIDIA's index, then COPY the builtins next to every
`libnvrtc.so` on disk (12 locations in this image).

Two more things learned the hard way:

- `ctypes.CDLL(..., RTLD_GLOBAL)` on NVIDIA libs segfaults Kit at startup
  inside `XOpenDisplay`. Do not preload.
- Setting `LD_LIBRARY_PATH` inside a running process does nothing; the dynamic
  linker reads it at exec. Set it on a subprocess instead.

## Consequence for the notebooks

- **NB1** Isaac Sim physics on Kaggle -- verified, ready.
- **NB2** synthetic images -- still blocked (no renderer). Repoint at
  non-visual data, or wait for Lightning.
- **NB3** domain randomization -- SALVAGED via physics DR, validated.
- **NB4** Isaac Lab RL -- now fully viable with the nvrtc fix.
- **NB5** MuJoCo vs Isaac -- complete; crossover measured at ~100 bodies.
