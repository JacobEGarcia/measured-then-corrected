TITLE = 'Reinforcement Learning in Isaac Lab on a Free GPU'
SLUG = 'reinforcement-learning-in-isaac-lab-on-a-free-gpu'
SUBTITLE = ("Around 200,000 environment steps per second on Kaggle's free T4 "
            "- and the five-layer install trap standing between you and it.")
TAGS = ['reinforcement learning', 'robotics', 'gpu']

CELLS = [
("md", """
## The claim

**NVIDIA Isaac Lab runs on Kaggle's free GPU tier, at roughly 200,000
environment steps per second** (178k-221k measured across three runs).

Isaac Lab is NVIDIA's RL framework for robotics - the one behind most of the
recent quadruped and manipulation results. The usual assumption is that you
need a workstation RTX card or a rented cloud GPU to touch it.

You do not. You need a free Kaggle account and about twenty minutes of install,
most of which is spent working around traps that produce spectacularly
unhelpful error messages.

This notebook has the measurements and the workarounds. Both were earned the
hard way: five separate attempts, each failing with the *same* error message
for a different underlying reason.

### What works on the free tier

| Capability | Free Kaggle T4 |
|---|---|
| GPU PhysX pipeline | yes |
| Rigid body + contact dynamics | yes |
| Articulated robots (Franka, ANYmal, 50 vendors) | yes |
| Contact / IMU / Effort / JointState sensors | yes |
| Isaac Lab, 197 Gym environments | yes |
| Vectorized RL environments | yes |
| **RTX rendering** | **no** |

The last row is the real constraint, and it is narrower than it sounds.
State-based RL - which is most robotics RL - needs no renderer at all.
Camera-based tasks are the casualty.
"""),

("md", """
## The result first

Isaac Lab, `Isaac-Cartpole-Direct-v0`, on one free T4:
"""),

("code", r'''
import json, os

EMBEDDED = json.loads(r"""{"vectorized_scaling": [{"num_envs": 64,"env_steps_per_s": 3864.8,"policy_steps_per_s": 60.4,"vram_used_gb": 2.33},{"num_envs": 256,"env_steps_per_s": 13917.0,"policy_steps_per_s": 54.4,"vram_used_gb": 3.0},{"num_envs": 1024,"env_steps_per_s": 55565.9,"policy_steps_per_s": 54.3,"vram_used_gb": 3.81},{"num_envs": 4096,"env_steps_per_s": 212899.1,"policy_steps_per_s": 52.0,"vram_used_gb": 4.22}]}""")

DATA = "/kaggle/input/isaac-sim-kaggle-benchmarks"
p = os.path.join(DATA, "isaaclab_vec.json")
data = json.load(open(p)) if os.path.exists(p) else EMBEDDED
rows = data["vectorized_scaling"]

print(f"{'envs':>6} {'env steps/s':>14} {'policy steps/s':>16} {'VRAM GB':>9}")
for r in rows:
    print(f"{r['num_envs']:>6} {r['env_steps_per_s']:>14,.1f} "
          f"{r['policy_steps_per_s']:>16.1f} {r['vram_used_gb']:>9.2f}")
'''),

("md", """
Read the **third column**, not the second.

`policy steps/s` is how many times per second the simulation advances. It sits
at roughly 52-60 whether you are running 64 environments or 4096. Sixty-four
times the work, the same wall-clock.

That is the entire argument for GPU simulation, in one column. The GPU is not
making each step faster - each step costs about the same either way. It is
making *thousands of steps happen at once*. On a CPU, 64x the environments
costs 64x the time.

The second column is that same fact restated as a headline: **around 200,000
environment steps per second**, on hardware that costs nothing.

A word on that number. Three separate runs of this notebook measured 212,899,
221,002 and 178,533 steps/s at 4096 environments - a spread of about +/-11%.
Kaggle's GPUs are shared infrastructure, so throughput depends on what else is
on the machine. Quoting six significant figures from a single run would be
false precision; the honest claim is "roughly 200k, plus or minus ten percent".

The cell further down runs the benchmark live and prints your numbers next to
these, so you can see your own variance rather than taking mine on trust.
"""),

("code", r'''
import matplotlib.pyplot as plt

n    = [r["num_envs"] for r in rows]
eps  = [r["env_steps_per_s"] for r in rows]
pol  = [r["policy_steps_per_s"] for r in rows]
vram = [r["vram_used_gb"] for r in rows]

fig, ax = plt.subplots(1, 3, figsize=(14.5, 4.3))

ax[0].loglog(n, eps, "o-", lw=2.6, ms=8, color="#2a9d8f", label="measured")
ax[0].loglog(n, [eps[0]*(x/n[0]) for x in n], "--", lw=1.4, color="gray",
             label="perfect linear")
ax[0].set_xlabel("parallel environments"); ax[0].set_ylabel("env steps / second")
ax[0].set_title("Throughput"); ax[0].legend(fontsize=8.5)

ax[1].semilogx(n, pol, "s-", lw=2.6, ms=8, color="#e76f51")
ax[1].set_ylim(0, max(pol)*1.35)
ax[1].set_xlabel("parallel environments"); ax[1].set_ylabel("policy steps / second")
ax[1].set_title("Wall-clock per step is FLAT")
for x, y in zip(n, pol):
    ax[1].annotate(f"{y:.0f}", (x, y), textcoords="offset points",
                   xytext=(0, 9), ha="center", fontsize=8.5)

ax[2].semilogx(n, vram, "^-", lw=2.6, ms=8, color="#4a5859")
ax[2].axhline(15.0, color="#c1443b", ls="--", lw=1.4, label="T4 limit")
ax[2].set_ylim(0, 16)
ax[2].set_xlabel("parallel environments"); ax[2].set_ylabel("VRAM (GB)")
ax[2].set_title("Headroom to spare"); ax[2].legend(fontsize=8.5)

for a in ax: a.grid(alpha=.3, which="both")
plt.tight_layout(); plt.show()

eff = (eps[-1]/eps[0]) / (n[-1]/n[0]) * 100
print(f"parallel efficiency, {n[0]} -> {n[-1]} envs: {eff:.0f}% of perfect linear")
print(f"VRAM at {n[-1]} envs: {vram[-1]:.2f} GB of ~15 GB "
      f"-> room for roughly {15/vram[-1]:.0f}x more")
'''),

("md", """
**86% of perfect linear scaling** from 64 to 4096 environments, using 4.2 GB
of the T4's 15 GB. There is headroom for substantially more.

### What that buys you in practice

A typical Isaac Lab locomotion task trains in roughly 100-500M environment
steps. At 212k steps/second:

| Budget | Wall-clock on a free T4 |
|---|---|
| 100M steps | ~8-9 minutes |
| 500M steps | ~40-47 minutes |

(Ranges reflect the +/-11% run-to-run spread.)

Both fit inside Kaggle's 12-hour session limit with room to spare, and inside
the free weekly quota of 30 GPU hours. Training a quadruped locomotion policy
on donated hardware is genuinely practical.
"""),

("md", """
## Now the part that will actually cost you an afternoon

Isaac Lab environments **construct** fine on Kaggle and then die on the first
`step()`:

```
RuntimeError: nvrtc: error: failed to open libnvrtc-builtins.so.13.0.
  Make sure that libnvrtc-builtins.so.13.0 is installed correctly.
```

I hit this five times. The message never changed. The cause did - three times.

**Trap 1 - the package on PyPI is a stub.** `pip install nvidia-cuda-nvrtc-cu13`
succeeds, reports success, and installs nothing useful: it is version 0.0.1, a
0.0 MB placeholder. Nothing warns you.

**Trap 2 - the real wheels are on NVIDIA's index, under a different name.**
`nvidia-cuda-nvrtc` (no `-cu13` suffix) on `pypi.nvidia.com`, where version
**13.0.88** matches `torch 2.11.0+cu130`.

**Trap 3 - installing it is still not enough.** NVRTC does not find its
builtins via `LD_LIBRARY_PATH`. It looks **next to whichever `libnvrtc.so` the
process actually loaded** - and torch ships its own copy in `torch/lib`, wins
the load, then looks for builtins in a directory that does not have them.

The fix is to copy the builtins beside every `libnvrtc.so` on disk. In Kaggle's
image that is twelve locations.
"""),

("code", r'''
import glob, os, shutil, subprocess, sys

NV = "--extra-index-url https://pypi.nvidia.com"

def pip(spec):
    subprocess.run(f'{sys.executable} -m pip install -q --timeout 120 '
                   f'--retries 5 {spec}', shell=True)

# Everything comes from NVIDIA's index. This is the load-bearing detail:
# plain PyPI either lacks these packages or serves stubs.
pip(f'"isaacsim[all,extscache]==6.0.1.0" {NV}')
pip('"numpy<2.1"')                      # isaacsim breaks on numpy >= 2.1
pip(f'isaaclab {NV}')
pip(f'"nvidia-cuda-nvrtc==13.0.88" {NV}')

# --- verify the file actually arrived, rather than trusting pip's exit code --
libs = glob.glob("/usr/local/lib/python3.12/dist-packages/nvidia/**/libnvrtc*.so*",
                 recursive=True)
builtins = [x for x in libs if "builtins" in os.path.basename(x)]
print("builtins found:", sorted(os.path.basename(x) for x in builtins))
assert any("builtins.so.13" in os.path.basename(x) for x in builtins),     "libnvrtc-builtins.so.13.x missing - the PyPI stub problem"

# --- put them where NVRTC will actually look --------------------------------
targets = {os.path.dirname(x) for x in
           glob.glob("/usr/local/lib/python3.12/dist-packages/**/libnvrtc.so*",
                     recursive=True)}
copied = 0
for d in targets:
    for b in builtins:
        dst = os.path.join(d, os.path.basename(b))
        if not os.path.exists(dst):
            shutil.copy2(b, dst); copied += 1
print(f"mirrored builtins into {len(targets)} libnvrtc.so directories "
      f"({copied} files copied)")
'''),

("md", """
### Two more things that will bite you

**Do not preload the NVIDIA libraries with `ctypes`.** My first fix attempt
used `ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)` to force the libraries in.
Isaac Sim then segfaulted at startup inside `XOpenDisplay` - exit code 139, no
Python traceback. `RTLD_GLOBAL` dumps those symbols into the global namespace
and breaks Kit's plugin loader.

**Setting `LD_LIBRARY_PATH` inside a running process does nothing.** The
dynamic linker reads it at `exec`. Assigning `os.environ["LD_LIBRARY_PATH"]`
mid-script is a widespread pattern and it is inert - you must set it on a
subprocess, before launch.

Which leads to the structural recommendation.
"""),

("md", """
## Run Isaac Sim in a subprocess, not in your notebook kernel

Kit registers asynchronous extension hooks at startup. In a notebook those fire
between cells, and one of them pulls in a UI widget chain that is broken
headless:

```
ImportError: cannot import name 'ButtonItem' from 'omni.kit.window.property'
```

Worse: when Kit fails hard it takes the whole process with it. In a notebook
that is `DeadKernelError` - no traceback, and every result you had computed is
gone. Isaac Sim also **segfaults on shutdown** inside `app.close()`, which in a
kernel means losing the session at the very end of a successful run.

A subprocess turns all of that into a return code.

The general rule, worth more than the specific fix: **write results to disk
before shutting down anything that might not shut down cleanly.**
"""),

("code", r'''
import textwrap

CHILD = textwrap.dedent("""
    import json, os, time
    from isaaclab.app import AppLauncher
    app = AppLauncher(headless=True).app          # must precede isaaclab imports

    import gymnasium as gym, torch, isaaclab_tasks  # noqa: registers Isaac-*
    from isaaclab_tasks.utils import parse_env_cfg

    TASK = "Isaac-Cartpole-Direct-v0"     # state-based: no camera, no renderer
    rows = []
    for n in (64, 256, 1024, 4096):
        cfg = parse_env_cfg(TASK, device="cuda:0", num_envs=n)
        env = gym.make(TASK, cfg=cfg); env.reset()
        act = torch.zeros((n, env.unwrapped.action_space.shape[-1]), device="cuda:0")

        for _ in range(20): env.step(act)          # warm up, exclude JIT cost
        torch.cuda.synchronize()

        t0 = time.perf_counter(); N = 100
        for _ in range(N): env.step(act)
        torch.cuda.synchronize(); wall = time.perf_counter() - t0

        free, tot = torch.cuda.mem_get_info()
        rows.append({"num_envs": n,
                     "env_steps_per_s": round(N*n/wall, 1),
                     "policy_steps_per_s": round(N/wall, 1),
                     "vram_used_gb": round((tot-free)/1e9, 2)})
        print(rows[-1], flush=True)
        env.close()

    json.dump({"vectorized_scaling": rows}, open("/kaggle/working/vec.json", "w"))
    print("CHILD_DONE", flush=True)
    app.close()
""")
open("child.py", "w").write(CHILD)

env = dict(os.environ)
env.update({"ACCEPT_EULA": "Y", "OMNI_KIT_ACCEPT_EULA": "YES",
            "PRIVACY_CONSENT": "Y"})
env.pop("DISPLAY", None)          # no X server here; let nothing try to find one

# Set the library path ON THE CHILD, before exec. Assigning it in this process
# would do nothing -- the dynamic linker reads it at exec time.
nvrtc_dir = os.path.dirname(builtins[0]) if builtins else ""
env["LD_LIBRARY_PATH"] = nvrtc_dir + ":" + env.get("LD_LIBRARY_PATH", "")

r = subprocess.run([sys.executable, "-u", "child.py"], env=env,
                   capture_output=True, text=True)
print(r.stdout[-2500:])
print("child exit code:", r.returncode)

live = None
if os.path.exists("/kaggle/working/vec.json"):
    live = json.load(open("/kaggle/working/vec.json"))["vectorized_scaling"]
    print("\n--- this session vs the reference run ---")
    ref = {x["num_envs"]: x["env_steps_per_s"] for x in rows}
    for x in live:
        r0 = ref.get(x["num_envs"])
        delta = f"{(x['env_steps_per_s']/r0-1)*100:+.1f}%" if r0 else "-"
        print(f"  {x['num_envs']:>5} envs: {x['env_steps_per_s']:>11,.1f} steps/s "
              f"(reference {r0:>11,.1f}, {delta})" if r0 else
              f"  {x['num_envs']:>5} envs: {x['env_steps_per_s']:>11,.1f} steps/s")

# Report failure loudly. Kit dies by SIGNAL rather than exception -- a segfault
# gives returncode -11 and often no stdout at all, so a notebook that only
# prints stdout will look like it succeeded while having done nothing.
# Judge success on CHILD_DONE, not on the return code.
#
# Isaac Sim SEGFAULTS during app.close() -- returncode -11 -- AFTER the work is
# finished and the results are on disk. Treating a non-zero exit as failure
# reports a successful run as broken, which is exactly the mistake this cell
# made in its first version.
done = "CHILD_DONE" in r.stdout

if done:
    print("\nLive run OK — the numbers above were produced by this session.")
    if r.returncode != 0:
        print(f"(exit {r.returncode} is the known Isaac Sim shutdown segfault, "
              f"raised after results were written. Harmless.)")
else:
    print("\n" + "=" * 62)
    print("LIVE RUN FAILED — no CHILD_DONE marker.")
    print("The numbers above are measured values from the dataset, not this session.")
    print("=" * 62)
    print("\n--- child stderr (last 3000 chars) ---")
    print(r.stderr[-3000:] or "(empty)")
'''),

("md", """
## What to actually train

`isaaclab_tasks` registers **197** environments. Not all of them are usable
here - anything with `RGB`, `Depth`, `Camera` or `Albedo` in the name needs the
renderer, which does not work on Kaggle.

The state-based ones do:

| Task | What it is |
|---|---|
| `Isaac-Cartpole-Direct-v0` | the classic; fastest to iterate on |
| `Isaac-Ant-v0` | locomotion, 8 DOF |
| `Isaac-Humanoid-v0` | locomotion, 21 DOF |
| `Isaac-Velocity-Flat-Anymal-C-v0` | quadruped velocity tracking |
| `Isaac-Repose-Cube-Allegro-Direct-v0` | in-hand manipulation |

Filter for them programmatically rather than by eye:
"""),

("code", r'''
# Run this INSIDE the child process (it needs isaaclab_tasks imported).
FILTER = r"""
import gymnasium as gym, isaaclab_tasks  # noqa
vision = ("RGB", "Depth", "Camera", "Albedo", "Theia", "ResNet")
ids = sorted(k for k in gym.registry if k.startswith("Isaac-"))
state_based = [k for k in ids if not any(v in k for v in vision)]
print(f"{len(ids)} Isaac envs registered, {len(state_based)} state-based "
      f"(usable without a renderer)")
for k in state_based[:15]:
    print("  ", k)
"""
print(FILTER)
'''),

("md", """
## Honest limits

**No rendering.** Camera-based RL and photorealistic synthetic data are out.
For those you need a box where the RTX renderer initialises - Lightning AI's
free tier is one.

**Reinstall every session.** Kaggle wipes the disk, so the ~20 GB install
repeats. Budget 15-20 minutes per session, or cache the environment as a
Kaggle Dataset and attach it instead.

**12-hour session cap.** Checkpoint aggressively; a training run that outlives
its session and saved nothing has produced nothing.

**These numbers are one task on one GPU.** Cartpole is cheap. A humanoid with
contact-rich terrain will be substantially slower, and the parallel efficiency
will differ. Measure your own task rather than trusting this table.

---

Found this useful? An upvote helps other people find it. Corrections and
questions in the comments get answered - especially if you run this on
different hardware, because a table across GPU types would be worth more than
this single column.
"""),
]
