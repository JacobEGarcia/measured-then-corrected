# Kaggle progression tracker

Profile: https://www.kaggle.com/jacobegarcia  (joined ~2026-08-19)
Last updated: 2026-08-24

## Verified thresholds

| Category | Expert needs | Bronze | Silver | Gold |
|---|---|---|---|---|
| Notebooks | **5 bronze** | 5 upvotes | 20 | 50 |
| Datasets  | **3 bronze** | 5 upvotes | 20 | 50 |
| Discussion| **50 bronze**| **1** net upvote | 5 | 10 |
| Competitions | 2 bronze | top-% placement | - | - |

Rules that shape the schedule:
- Self-votes and **Novice-tier votes do not count**.
- Votes on content **older than 90 days** stop counting. Stagger publishing.
- Silver/gold each count as a bronze for crossing a tier line.
- **Playground / Getting Started / InClass award NO medals.**

## THE finding of 2026-08-24

Everything on the account was **private**. Private content earns zero medals,
so 8 notebooks and 3 datasets built Aug 18-19 were accruing nothing.
7 of 8 notebooks and 3 of 3 datasets were invisible.

Fixed this session. Details below.

## Notebooks

| Notebook | Public | Ran clean | Votes |
|---|---|---|---|
| phyllotaxis-why-137-5-degrees | yes | COMPLETE | 0/5 |
| phyllotaxis-spiral-geometry-in-r | yes | COMPLETE | 0/5 |
| rsna-knee-format-correct-baseline | yes | COMPLETE | 0/5 |
| tabular-toolkit | yes | COMPLETE | 0/5 |
| titanic-using-a-pretrained-kaggle-model | yes (already) | - | 0/5 |
| **s2-in-hand-reorientation-leap-mjx** | **private** | ERROR | - |
| titanic-tutorial | private (deliberate) | - | - |
| notebook9ffc4141b0 | private (scratch) | - | - |
| isaac-sim-on-kaggle-free-t4-robotics-simulation | private (verifying) | running | - |

### s2-in-hand-reorientation-leap-mjx — blocked, needs a decision

Failed on `assert any(d.platform == 'gpu' ...)` because its kernel metadata had
`enable_gpu: false`. The notebook is fine; the environment was wrong.

Reverted to private, because public + errored is the worst possible state.

To fix it we must set `enable_gpu/enable_internet: true` and re-push — but
cell 7 runs `TOTAL_STEPS = 100_000_000` at 2048 envs, which is plausibly a
full 12-hour session, roughly a third of the 30 hr/week GPU quota.
**Not spending that without a decision.** Options: run it for real, or lower
TOTAL_STEPS for a fast verified run and publish that.

Its GitHub dependency is fine — `JacobEGarcia/robotics-rl-portfolio` is public
and contains `s2_inhand/train.py`.

## Datasets

| Dataset | Public | Usability | Votes |
|---|---|---|---|
| phyllotaxis-spiral-geometry-reference | yes | 0.59 | 0/5 |
| palmer-penguins-linked-from-seaborn-data | yes | 0.24 -> pending recompute | 0/5 |
| titanic-baseline-predictions-notebook-output | yes | 0.06 -> pending recompute | 0/5 |
| mujoco-vs-isaac-benchmark | **private** (ready) | - | - |

Metadata repaired this session:
- **Mojibake** in phyllotaxis: 11 corrupted sequences fixed (`Â°`->`°`,
  `â€"`->`—`). The text is mixed-encoding, so a whole-string repair silently
  fails; fixed per damaged run, preserving genuine `φ`/`√`/`π`.
- **Two datasets had no description at all** — now 1,584 and 1,295 chars.

Note: `kaggle datasets metadata --update` omits `isPrivate`, and Kaggle
**defaults it to public**. That is how the three went public. Remember this
before any future metadata update.

## Models (a 5th category)

3 models exist; only `titanic-survival-baselines` is public. The other two
(`mnist-onnx-linked-from-onnxmodels`, `titanic-pipeline-notebook-output`) are
private. Models progression thresholds are not clearly documented, so no
promises — but publishing them is free upside.

## Contributor checklist

- [x] Bio filled in (sim-to-real RL, procedural 3D, game engines)
- [x] Ran a notebook
- [x] Competition submission (Titanic, 0.75119 public)
- [ ] Phone verification — **unverified, and it gates the GPU quota**
- [ ] Made a comment
- [ ] Cast an upvote

## Gotchas learned the hard way this session

1. **`isaacsim` wheels are pinned to exact Python versions.** 4.x needs 3.10,
   5.x needs 3.11, **6.0.x needs 3.12**. Kaggle runs 3.12, so every tutorial
   pinning `==4.5.0` cannot install there. pip's error never mentions Python.
2. **A kernel's title must slugify to its id** or the push 400s. Now enforced
   at build time by `tools/slugcheck.py`.
3. **Kaggle tags are a controlled vocabulary using spaces**, not hyphens.
   `computer vision` works; `computer-vision` and `synthetic-data` are dropped.
4. **`kernels push` always re-runs the notebook.** Pushing to change visibility
   re-executes it, which is how the MJX notebook went public and errored.
5. Dataset titles must be **6-50 characters**.
6. nbformat >= 4.5 wants a per-cell `id`; Kaggle warns without one.
7. **Kaggle's container has no NVIDIA Vulkan ICD file.** Isaac Sim renders
   through Vulkan, so `SimulationApp` dies at startup with
   `VkResult: ERROR_INCOMPATIBLE_DRIVER` / "Vulkan 1.1 is not supported",
   and the kernel is killed outright (`DeadKernelError`) rather than raising.
   The driver is fine and the T4 has RT cores — what is missing is
   `/usr/share/vulkan/icd.d/nvidia_icd.json`, the JSON that registers the
   driver with the Vulkan loader. Under test: writing that file ourselves
   plus `--/rtx/verifyDriverVersion/enabled=false`.
8. `/kaggle/working` had only **20.9 GB** free while `/tmp` had **1,102 GB**.
   The isaacsim wheels are ~20 GB, so installing into the working dir is
   marginal at best. The preflight now warns about this.

## Isaac Sim on Kaggle — verification log

| Attempt | Result |
|---|---|
| 1 | FAIL in 40s — `isaacsim==4.5.0` needs Python 3.10, Kaggle has 3.12 |
| 2 | FAIL in 580s — install OK (9m34s), then Vulkan ICD missing, kernel died |
| 3 | FAIL — Vulkan ICD fix WORKED; next wall: PhysX CUDA context |
| 4 | FAIL — single-GPU pin did not help; NumPy ABI errors surfaced |
| 5 | **All four runs were on a Tesla P100, not a T4** — see below |
| 6 | On a real T4: physics WORKS, RTX rendering does not |
| 7 | FAIL — `ButtonItem` ImportError from Kit's async extension hooks |
| 8 | FAIL — pip ReadTimeoutError pulling ~20 GB (added --timeout/--retries) |
| 9 | FAIL — my own free-fall check was wrong (bounce samples) |
| 10 | **COMPLETE** — subprocess design + gravity-recovery test |

### Final verified result (notebook 1)

    SimulationApp is up
    API layout: isaacsim.* (4.5+)
    scene ready / TRAJECTORY_SAVED
    exit code: -11          <- SIGSEGV in app.close(), AFTER data was saved
    RTX errors: 9           <- renderer never initialises

    rest height       : 0.1000 m   (expected 0.1000 = half extent)
    recovered gravity : 9.8100 m/s^2  (expected 9.8100)  error 0.000%
    PhysX correct: YES

**Isaac Sim physics runs on a free Kaggle T4 and recovers g to 0.000%.
The RTX renderer does not initialise at all.**

Consequences: state-based RL and physics work are viable on Kaggle; synthetic
image data and pixel-based RL are not, and need the Lightning box.

### Design decisions that mattered

- **Run Isaac Sim in a SUBPROCESS, never in the notebook kernel.** Kit's async
  extension hooks fire between cells and pull in a UI chain that is broken
  headless (`ImportError: ButtonItem`); worse, Kit segfaults on shutdown
  (exit -11). In-kernel that is a DeadKernelError and total data loss. In a
  subprocess it is a return code. Write results to disk BEFORE teardown.
- **Test gravity, not position.** Comparing simulated positions to
  `z0 - 0.5*g*t^2` conflates integrator offset with physical error: a 60 Hz
  first-order scheme is legitimately ~35 mm off while being correct. Fit
  `z = at^2+bt+c` and take `-2a` — timestep-independent, and it recovered
  9.8100 exactly.
- **Mask only PRE-IMPACT samples.** The cube bounces; a naive
  `heights > 0.11` mask grabs post-bounce points and compares them against a
  curve that is metres underground. My first check reported a 3243 mm error
  that was entirely my own bug.

This is exactly why nothing gets published before it runs. Attempt 1 would
have shipped a notebook that cannot install; attempt 2 one that kills the
kernel.

### The mistake I nearly published

I was about to publish a teardown concluding "Isaac Sim cannot run on Kaggle,"
with PhysX's failure to create a CUDA context as the hard stop.

Then I read the GPU line in the output: **Tesla P100-PCIE-16GB, compute 6.0.**
Every one of the four attempts had run on a P100 — Pascal, no RT cores, and
genuinely below PhysX's stated 7.0 minimum. The error message was telling the
literal truth and I had misread it as a container limitation.

Root cause: `enable_gpu: true` gets Kaggle's **default** GPU (P100). Selecting
a T4 requires `machine_shape` / `--accelerator` with an exact string:

    NvidiaTeslaT4 | NvidiaTeslaP100 | Tpu1VmV38

Anything else — `T4x2`, `nvidiaTeslaT4` (lowercase n) — is accepted without
complaint and silently falls back to P100. Verified with a probe kernel:
`NvidiaTeslaT4` yields **2x Tesla T4, compute 7.5**.

`tools/kaggle_prep.py` now pins `machine_shape` so this cannot regress.

Lesson: when an error message states a specific numeric requirement, check the
number before concluding the message is wrong.
