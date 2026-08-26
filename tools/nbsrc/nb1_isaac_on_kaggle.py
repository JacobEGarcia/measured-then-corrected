TITLE = "Isaac Sim on a Free Kaggle T4: Physics Yes, RTX No"
SLUG = "isaac-sim-on-a-free-kaggle-t4-physics-yes-rtx-no"
SUBTITLE = ("It runs — but only half of it, and four traps stand in the way. "
            "Every error below is real captured output from this notebook.")
TAGS = ['robotics', 'gpu', 'beginner']

CELLS = [
("md", """
## The answer, up front

**NVIDIA Isaac Sim's physics engine runs on Kaggle's free T4. Its RTX renderer
does not.**

That split matters more than a yes or no, because it decides which robotics
work you can do here for free:

| Work | On free Kaggle? |
|---|---|
| Physics simulation, state-based RL | ✅ Yes |
| Contact dynamics, robot control | ✅ Yes |
| **Synthetic image data, RTX rendering** | ❌ **No** |
| Camera-based / pixel RL | ❌ No |

Getting there took four attempts and four separate traps. Every error quoted
below is real captured output, not a hypothetical. If you are about to try
this, I hope it saves you the evening it cost me.
"""),

("md", """
## Trap 0 — Kaggle gives you a P100, not a T4

This is the one that wasted the most time, and it is invisible unless you look.

Setting `enable_gpu: true` gets Kaggle's **default** GPU: a **Tesla P100**.
Pascal, compute capability **6.0**, **no RT cores**, and below PhysX's stated
7.0 minimum. Isaac Sim cannot work on it, and the error it produces —

```
[Error] [omni.physx.foundation.plugin] Failed to create Cuda Context Manager.
[Error] [omni.physx.plugin] Unable to create PxCudaContextManager!
[Warning] PhysX warning: Minimum GPU compute capability 7.0 is required
```

— reads like a container problem but is a plain statement of fact about the
hardware.

**Via the API**, request a T4 explicitly. Only three strings are accepted:

```
NvidiaTeslaT4  |  NvidiaTeslaP100  |  Tpu1VmV38
```

```bash
kaggle kernels push -p . --accelerator NvidiaTeslaT4
```

or `"machine_shape": "NvidiaTeslaT4"` in `kernel-metadata.json`.

**Anything else is accepted silently and falls back to P100.** I tried `T4x2`,
lowercase `nvidiaTeslaT4`, and a deliberate `INVALID_PROBE` — all pushed
without complaint, all gave a P100.

**In the UI**, pick *GPU T4 x2* in the Accelerator dropdown.

Check what you actually got before anything else:
"""),

("code", r'''
import os, subprocess, sys

def sh(c):
    r = subprocess.run(c, shell=True, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()

gpu = sh("nvidia-smi --query-gpu=name,compute_cap,memory.total,driver_version "
         "--format=csv,noheader")
print(gpu or "(no GPU — set Accelerator to GPU T4 x2)")

cc = 0.0
for line in gpu.splitlines():
    try:
        cc = max(cc, float(line.split(",")[1]))
    except (IndexError, ValueError):
        pass

print()
if cc >= 7.5:
    print(f"OK — compute {cc} has RT cores and clears PhysX's 7.0 minimum.")
elif cc:
    print(f"STOP — compute {cc} is below 7.0. This is almost certainly a P100.")
    print("Isaac Sim will fail here no matter what else you fix.")
'''),

("md", """
### The RT core table, while we are here

Isaac Sim's renderer needs **RT cores** — dedicated ray-tracing hardware. The
counterintuitive part is which GPUs have them:

| GPU | Compute cap | RT cores? |
|---|---|---|
| **P100** (Kaggle default) | **6.0** | ❌ No |
| **T4** (what you must ask for) | 7.5 | ✅ Yes |
| L4 / L40S | 8.9 | ✅ Yes |
| RTX 3090 / 4090 | 8.6 / 8.9 | ✅ Yes |
| **A100** | **8.0** | ❌ **No** |
| **H100** | **9.0** | ❌ **No** |

The expensive datacenter parts strip RT cores out — their customers train
transformers, they do not render. A $2/hr A100 is **worse for rendering** than
a free T4. For physics-only RL on state vectors, an A100 is perfectly fine.
"""),

("md", """
## Trap 1 — The Python version pin

```
ERROR: Could not find a version that satisfies the requirement isaacsim==4.5.0
       (from versions: 6.0.0.0, 6.0.0.1, 6.0.1.0)
```

**The `isaacsim` wheels are pinned to exact Python versions:**

| Isaac Sim | Requires Python | Kaggle (3.12)? |
|---|---|---|
| 4.0 – 4.5 | **3.10 only** | ❌ |
| 5.0 – 5.1 | **3.11 only** | ❌ |
| **6.0.x** | **3.12** | ✅ |

Nearly every tutorial online pins `==4.5.0` because that was current when it
was written. On Python 3.12 that install cannot succeed, and pip's message
never mentions Python — the `from versions:` list is the real signal.
"""),

("code", r'''
py = sys.version_info
ISAAC_FOR_PY = {(3, 10): "4.5.0", (3, 11): "5.1.0", (3, 12): "6.0.1.0"}
version = ISAAC_FOR_PY.get((py.major, py.minor), "6.0.1.0")
print(f"Python {py.major}.{py.minor} -> isaacsim=={version}")
'''),

("md", """
## Trap 2 — Vulkan has no driver registered

With the right version the install succeeds (~20 GB, about 10 minutes). Then
`SimulationApp` starts and the kernel **dies outright** — no traceback:

```
[Error] [omni.rtx] VkResult: ERROR_INCOMPATIBLE_DRIVER
[Error] [omni.rtx] vkCreateInstance failed. Vulkan 1.1 is not supported
DeadKernelError: Kernel died
```

**The message blames the driver. The driver is fine.** What Kaggle's container
lacks is `/usr/share/vulkan/icd.d/nvidia_icd.json` — the small JSON that tells
the Vulkan loader which library implements the driver. Isaac Sim renders
through Vulkan, so without that registration nothing starts.

Write it yourself. This fix is useful well beyond Isaac Sim — it applies to
any Vulkan workload in a container that ships CUDA but not the graphics ICD.
"""),

("code", r'''
import glob, json

sh("apt-get update -qq && apt-get install -y -qq libvulkan1 vulkan-tools")

cands = (glob.glob("/usr/lib/x86_64-linux-gnu/libGLX_nvidia.so*")
         + glob.glob("/usr/local/nvidia/lib64/libGLX_nvidia.so*"))
print("libGLX_nvidia:", cands or "NONE FOUND")

os.makedirs("/usr/share/vulkan/icd.d", exist_ok=True)
with open("/usr/share/vulkan/icd.d/nvidia_icd.json", "w") as f:
    json.dump({"file_format_version": "1.0.0",
               "ICD": {"library_path": cands[0] if cands else "libGLX_nvidia.so.0",
                       "api_version": "1.3.242"}}, f, indent=2)

info = sh("vulkaninfo --summary")
print("Vulkan device visible:", "deviceName" in info or "GPU id" in info)
'''),

("md", """
## Install, then Trap 3 — the NumPy ABI mismatch

Past Vulkan, Kit boots ~16,000 lines of extensions and then every
`isaacsim.core` import fails:

```
[Error] Failed to import python module isaacsim.core.prims.
        Error: cannot import name '_center' from 'numpy._core.umath'
[Error] Failed to import python module isaacsim.core.api.
        Error: cannot import name 'SingleGeometryPrim'
```

Isaac Sim 6.0.1.0 is built against **NumPy < 2.1**; Kaggle ships **2.3.1**.
`numpy._core.umath._center` is a private symbol that moved between them.

The fix is a downgrade — and it must happen **before** importing `isaacsim`.
"""),

("code", r'''
%%time
# ~20 GB over the wire. The default pip timeout is 15s per read, which is
# not enough for wheels this size -- a plain `pip install` here fails with
# ReadTimeoutError often enough that retries are not optional.
!pip install -q --timeout 120 --retries 5 "isaacsim[all,extscache]=={version}" --extra-index-url https://pypi.nvidia.com
!pip install -q --timeout 120 --retries 5 "numpy<2.1"

import importlib.util
if importlib.util.find_spec("isaacsim") is None:
    raise SystemExit("isaacsim did not install -- re-run this cell. "
                     "Large-wheel downloads time out intermittently.")
print("isaacsim installed")
'''),

("code", r'''
import numpy
print("numpy:", numpy.__version__, "(needs to be < 2.1)")
'''),

("md", """
## It works — physics, at least

Now the part that succeeds. `SimulationApp` must be constructed **before** any
other `isaacsim`/`omni` import; it bootstraps the extension system everything
else depends on.

Expect RTX errors in the output below. **They are not fatal** — physics runs
anyway, which is the whole finding of this notebook.

One hard-won detail: **run Isaac Sim in a subprocess, not in the notebook
kernel.** Kit's async extension hooks fire between cells and drag in a UI
widget chain that is broken headless (`ImportError: cannot import name
'ButtonItem'`), and when Kit fails hard it takes the whole kernel with it —
`DeadKernelError`, no traceback. A subprocess turns a lost session into a
return code.
"""),

("code", r'''
# Isaac Sim runs in a SUBPROCESS, not in this kernel. That is deliberate.
#
# Kit registers async extension-enable hooks at startup. In a notebook those
# fire between cells (or mid-step) and one of them pulls in a UI widget chain
# that is broken headless:
#     ImportError: cannot import name 'ButtonItem' from 'omni.kit.window.property'
# Worse, when Kit fails hard it kills the process outright -- DeadKernelError,
# no traceback, notebook over.
#
# A subprocess isolates all of that: the hooks cannot reach this kernel, a
# crash costs us a return code instead of the session, and the exact same
# script runs identically outside a notebook.

ISAAC_SCRIPT = r"""
import json, os, sys
os.environ["ACCEPT_EULA"] = "Y"
os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"
os.environ["PRIVACY_CONSENT"] = "Y"
sys.argv += ["--/rtx/verifyDriverVersion/enabled=false"]

from isaacsim import SimulationApp
app = SimulationApp({"headless": True, "width": 320, "height": 240})
print("SimulationApp is up", flush=True)

try:
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid
    layout = "isaacsim.* (4.5+)"
except ImportError:
    from omni.isaac.core import World
    from omni.isaac.core.objects import DynamicCuboid
    layout = "omni.isaac.* (<=4.2)"
print("API layout:", layout, flush=True)

import numpy as np
world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()
cube = world.scene.add(DynamicCuboid(
    prim_path="/World/cube", name="cube",
    position=np.array([0.0, 0.0, 1.0]), size=0.2))
world.reset()
print("scene ready", flush=True)

dt, heights = 1.0 / 60.0, []
for _ in range(120):
    world.step(render=False)          # render=False -> physics only
    heights.append(float(cube.get_world_pose()[0][2]))

json.dump({"dt": dt, "heights": heights, "layout": layout},
          open("/kaggle/working/trajectory.json", "w"))
print("TRAJECTORY_SAVED", flush=True)
app.close()
"""

open("run_isaac.py", "w").write(ISAAC_SCRIPT)
r = subprocess.run([sys.executable, "-u", "run_isaac.py"],
                   capture_output=True, text=True)

for line in r.stdout.splitlines():
    if any(k in line for k in ("SimulationApp", "API layout", "scene ready",
                               "TRAJECTORY_SAVED")):
        print(line)

print("\nexit code:", r.returncode)
rtx = [l for l in (r.stdout + r.stderr).splitlines()
       if "omni.rtx" in l or "GPU Foundation" in l]
print("RTX errors:", len(rtx), "(expected — see below)")
'''),

("code", r'''
import json
import numpy as np

traj = json.load(open("/kaggle/working/trajectory.json"))
heights = np.array(traj["heights"])
times = np.arange(len(heights)) * traj["dt"]

# Compare ONLY the pre-impact samples. The cube bounces, so a naive
# "every sample above resting height" mask picks up post-bounce points and
# compares them against a free-fall curve that is metres underground by then.
below = np.flatnonzero(heights <= 0.11)
first_contact = below[0] if below.size else len(heights)
t_f, z_f = times[:first_contact], heights[:first_contact]

z0 = heights[0]

# Recover gravity by fitting z = a*t^2 + b*t + c. This is the right test:
# comparing raw positions against the continuous curve conflates integrator
# offset with physical error -- a 60 Hz first-order scheme is legitimately
# ~35 mm off the analytic parabola without being wrong. The QUADRATIC
# coefficient is unaffected by that offset, so -2a recovers g exactly and the
# test is timestep-independent.
a, b, c = np.polyfit(t_f, z_f, 2)
g_measured = -2 * a
analytic = z0 - 0.5 * 9.81 * t_f ** 2

print(f"start height       : {z0:.4f} m")
print(f"rest height        : {heights[-1]:.4f} m   (expected 0.1000 = half extent)")
print(f"free-fall samples  : {t_f.size}")
print()
print(f"recovered gravity  : {g_measured:.4f} m/s^2   (expected 9.8100)")
print(f"error              : {abs(g_measured-9.81):.4f}  "
      f"({abs(g_measured-9.81)/9.81*100:.3f}%)")
print()
ok = abs(g_measured - 9.81) < 0.2 and abs(heights[-1] - 0.1) < 0.005
print("PhysX correct:", "YES" if ok else "NO — investigate")
'''),

("md", """
### Is the physics actually correct?

Two independent checks, neither of which can be fudged:

1. **The resting height must equal the cube's half-extent** — 0.1 m for a
   0.2 m cube. Contact resolution either gets this exactly right or it does
   not.
2. **Gravity, recovered from the trajectory.** Fit `z = at² + bt + c` to the
   pre-impact samples; `-2a` is the acceleration.

The second is worth explaining, because the obvious test is wrong. Comparing
simulated positions directly against `z₀ - ½gt²` conflates *integrator offset*
with *physical error*: a 60 Hz first-order scheme sits about 35 mm off the
continuous parabola while being perfectly correct. The quadratic coefficient
is immune to that offset, so this test is timestep-independent — and it is the
difference between "looks about right" and a number you can defend.
"""),

("code", r'''
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(times, heights, lw=2.5, label="Isaac Sim (PhysX on T4)")
ax.plot(t_f, analytic, "--", lw=1.8, color="crimson",
        label=r"analytic  $z_0 - \frac{1}{2}gt^2$")
ax.axhline(0.1, color="gray", ls=":", lw=1, label="resting height")
ax.set_xlabel("time (s)"); ax.set_ylabel("cube height (m)")
ax.set_title("Free fall and impact — Isaac Sim on a free Kaggle T4")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout(); plt.show()
'''),

("md", """
### About that exit code

The subprocess returns **-11**, which is `SIGSEGV` — Isaac Sim segfaults on
shutdown inside `app.close()`. Note *where* it happens: `TRAJECTORY_SAVED`
printed first, so the simulation completed and the data is on disk. The crash
is purely in teardown.

This is the subprocess decision paying for itself. Run in the notebook kernel,
that segfault takes the kernel with it — `DeadKernelError`, no traceback, and
every result you had computed is gone. In a subprocess it is a return code you
can ignore.

The general lesson: **write results to disk before shutting down anything that
might not shut down cleanly.**
"""),

("md", """
## What does not work — RTX rendering

The renderer fails, and unlike the earlier traps this one has no fix from
inside a notebook:

```
[Error] [omni.rtx] No device could be created. Some known system issues:
 - Your GPUs do not support RayTracing: DXR or Vulkan ray_tracing...
 - For Ubuntu, it requires server-xorg-core 1.20.7+ and a display
 - For Linux dockers, the setup is not complete. Install the latest
   driver, xServer and NVIDIA container runtime.
[Error] [omni.gpu_foundation_factory.plugin] Failed to create any GPU devices,
        including an attempt with compatibility mode.
[Error] [omni.kit.renderer.plugin] GPU Foundation is not initialized!
```

The T4 *has* RT cores. What is missing is the rest of the stack Kit's RTX
backend expects — an xServer and the NVIDIA container runtime. Kaggle's image
is built for CUDA compute, not graphics.

Interestingly PhysX enumerates both GPUs correctly right alongside these
errors:

```
"cuda:0" : "Tesla T4" (15 GiB, sm_75, mempool enabled)
"cuda:1" : "Tesla T4" (15 GiB, sm_75, mempool enabled)
```

**Compute works. Graphics does not.** Hence physics yes, rendering no.

One more quirk: `app.close()` tends to hang here. The kernel still finishes,
but do not expect a clean shutdown message.
"""),

("md", """
## So what is free Kaggle actually good for?

**Use it for:**
- Learning the Isaac Sim API without buying hardware
- Physics-only work with `world.step(render=False)`
- State-based RL, where observations are vectors rather than pixels
- Contact dynamics and controller development

**Do not use it for:**
- Synthetic image datasets — the renderer will not start
- Camera-based / pixel RL
- Anything needing more than one 12-hour session (the disk is wiped, so you
  reinstall 20 GB every time)

### The pattern that works

> **Generate on a persistent GPU box → publish artifacts to Kaggle.**

**Lightning AI's free tier** gives 80 GPU hours a month *with persistent
storage* and a container you control, so the install happens once and the
renderer actually works. Upload results as a Kaggle Dataset; Kaggle notebooks
then consume pre-generated data.

| Method | Free allowance | Isaac Sim |
|---|---|---|
| **Lightning AI** | 80 GPU hr/mo, persistent, sudo | ✅ physics + rendering |
| **Kaggle** | 30 GPU hr/wk, 2x T4 | 🟡 physics only |
| **NVIDIA DLI** | hosted labs | ✅ full, zero setup |
| Colab | best-effort T4 | 🟡 same limits as Kaggle |

Kaggle is also excellent for the rest of the robotics-sim stack — **MuJoCo and
MJX run here perfectly**. See the companion notebook, which measures
integrator accuracy and parallel scaling entirely on Kaggle hardware.

### Four things worth remembering

1. **Ask for `NvidiaTeslaT4`.** The default is a P100 that cannot run this,
   and wrong accelerator strings fail silently.
2. **`isaacsim` wheels are pinned to exact Python versions.** Every tutorial
   pinning `==4.5.0` is broken on 3.12.
3. **`ERROR_INCOMPATIBLE_DRIVER` usually means a missing ICD file**, not a bad
   driver. Four lines of JSON.
4. **Downgrade to `numpy<2.1` before importing isaacsim.**

If you get the RTX renderer working on Kaggle, I would genuinely like to know
how — **post it in the comments** and I will update this notebook and credit
you.
"""),
]
