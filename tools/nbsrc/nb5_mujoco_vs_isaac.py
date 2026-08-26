TITLE = 'Where GPU Physics Beats CPU Physics'
SLUG = 'where-gpu-physics-beats-cpu-physics'
SUBTITLE = ("MuJoCo and Isaac Sim measured under one honest protocol. They "
            "trade places at about 100 bodies - and the first two versions of "
            "this benchmark were wrong in opposite directions.")
TAGS = ['robotics', 'physics', 'reinforcement learning']

CELLS = [
("md", """
## The question people actually have

"Should I use a GPU physics engine?" usually gets answered with vibes, or with
a benchmark that measures speed alone - which is easy to win by being wrong,
since any integrator goes faster if it accepts more error.

This notebook answers it with a number: **they trade places at roughly 100
rigid bodies, or about 400 contacts.** Below that, a laptop CPU beats a data
centre GPU, by up to 156x. Above it, the GPU pulls away and keeps going.

Everything here was measured on hardware you can get for free - a Kaggle T4 and
an ordinary laptop.

I am also showing the two earlier versions of this benchmark, because both were
wrong, in opposite directions, and the reason is more useful than the result.
"""),

("md", """
## The result
"""),

("code", r'''
import json, os

EMBEDDED = json.loads(r"""{"protocol": {"settle_steps": 400,"timed_steps": 100,"physics_dt": 0.004,"note": "Identical layout and step budget on both engines. The settle phase is untimed, so every measurement is steady-state contact resolution rather than free fall."},"mujoco": {"version": "3.12.0","accelerator": "CPU (Apple M-series)"},"isaac": {"version": "6.0.1.0","accelerator": "Tesla T4 (free Kaggle tier)"},"comparison": [{"n_boxes": 4,"mujoco_steps_per_s": 54809.54,"isaac_steps_per_s": 351.79,"contacts": 16,"winner": "mujoco"},{"n_boxes": 16,"mujoco_steps_per_s": 4835.12,"isaac_steps_per_s": 303.59,"contacts": 64,"winner": "mujoco"},{"n_boxes": 64,"mujoco_steps_per_s": 462.73,"isaac_steps_per_s": 259.36,"contacts": 256,"winner": "mujoco"},{"n_boxes": 128,"mujoco_steps_per_s": 147.76,"isaac_steps_per_s": 231.41,"contacts": 512,"winner": "isaac"},{"n_boxes": 256,"mujoco_steps_per_s": 57.8,"isaac_steps_per_s": 220.65,"contacts": 1025,"winner": "isaac"},{"n_boxes": 512,"mujoco_steps_per_s": 35.4,"isaac_steps_per_s": 166.28,"contacts": 2067,"winner": "isaac"},{"n_boxes": 1024,"mujoco_steps_per_s": 27.1,"isaac_steps_per_s": 110.29,"contacts": 4127,"winner": "isaac"},{"n_boxes": 2048,"mujoco_steps_per_s": 8.5,"isaac_steps_per_s": 71.7,"contacts": 8530,"winner": "isaac"}]}""")

DATA = "/kaggle/input/isaac-sim-kaggle-benchmarks"
p = os.path.join(DATA, "crossover.json")
d = json.load(open(p)) if os.path.exists(p) else EMBEDDED
C = d["comparison"]

print(d["protocol"]["note"])
print()
print(f"{'bodies':>7} {'contacts':>9} {'MuJoCo CPU':>13} {'Isaac T4':>11} {'ratio':>8}  winner")
for r in C:
    m, i = r["mujoco_steps_per_s"], r["isaac_steps_per_s"]
    print(f"{r['n_boxes']:>7} {str(r['contacts']):>9} {m:>13,.1f} {i:>11,.1f} "
          f"{max(m,i)/min(m,i):>7.1f}x  {r['winner'].upper()}")
'''),

("code", r'''
import matplotlib.pyplot as plt

n  = [r["n_boxes"] for r in C]
mj = [r["mujoco_steps_per_s"] for r in C]
isa= [r["isaac_steps_per_s"] for r in C]
ct = [r["contacts"] for r in C]

fig, ax = plt.subplots(figsize=(9.6, 5.2))
ax.loglog(n, mj,  "o-", lw=2.6, ms=8, color="#e76f51", label="MuJoCo — laptop CPU")
ax.loglog(n, isa, "s-", lw=2.6, ms=8, color="#2a9d8f", label="Isaac Sim — free Kaggle T4")

# shade the interval where the winner changes
flip = next((k for k in range(len(C)-1) if C[k]["winner"] != C[k+1]["winner"]), None)
if flip is not None:
    ax.axvspan(n[flip], n[flip+1], color="#8d99ae", alpha=.18)
    ax.annotate(f"crossover\n~{n[flip]}–{n[flip+1]} bodies\n(~{ct[flip+1]} contacts)",
                xy=((n[flip]+n[flip+1])/2, isa[flip]), xytext=(n[flip]*1.7, max(mj)*0.06),
                fontsize=9.5, color="#31414f",
                arrowprops=dict(arrowstyle="->", color="#31414f", lw=1.2))

ax.set_xlabel("rigid bodies in scene   (contacts below)")
ax.set_ylabel("physics steps / second")
ax.set_title("One protocol, both engines, steady-state contact")
ax.set_xticks(n); ax.set_xticklabels([f"{a}\n{b}" for a, b in zip(n, ct)], fontsize=8)
ax.grid(alpha=.3, which="both"); ax.legend()
plt.tight_layout(); plt.show()
'''),

("md", """
Look at the *shapes*, not just the intersection.

**Isaac Sim is almost flat.** From 4 bodies to 2048 - a 512x increase - it only
loses about 5x throughput. Its cost is dominated by fixed per-step overhead:
Kit's update loop, GPU dispatch, kernel launches. Scene complexity barely
registers against that floor.

**MuJoCo falls off a cliff.** It starts 156x ahead and loses three orders of
magnitude over the same range, because it pays honestly for every contact it
solves.

The practical reading:

| Your scene | Use |
|---|---|
| One arm, one quadruped, a handful of objects | **CPU MuJoCo** — and it is not close |
| Hundreds of interacting bodies, granular piles, clutter | **GPU Isaac Sim** |
| Thousands of *parallel copies* of a small scene | **GPU** — see the caveat below |

That last row is the one this benchmark cannot see, and it matters.
"""),

("md", """
## The caveat that nearly made this benchmark useless

Everything above steps **one scene containing N bodies**. That is Isaac Sim's
worst case and it flatters MuJoCo, because Isaac's actual design win is
different: thousands of *separate environments*, stepped as one batched GPU
operation.

Measured separately on the same free T4, Isaac Lab runs **212,899 environment
steps per second across 4096 parallel cartpoles**, and the wall-clock per step
is essentially identical to running 64. That workload is what GPU simulators
exist for, and no single-scene benchmark - including this one - will show it.

So read the crossover as answering *"one complicated scene: CPU or GPU?"*, not
*"which engine is faster?"*. Benchmarks answer the question they measure, and
the honest move is to say which question that was.
"""),

("md", """
## Speed is the easy half: integrator accuracy

Any engine can be fast if it is willing to be wrong. An undamped pendulum
conserves energy exactly, so drift is pure integrator error - measurable with
no ground-truth dataset at all.
"""),

("code", r'''
import numpy as np

ACC = json.loads(r"""[{"dt": 0.01,"integrator": "Euler","seconds": 10.0,"rel_energy_drift_final": 0.0031773463666467205,"rel_energy_drift_max": 0.0036629493564012},{"dt": 0.01,"integrator": "RK4","seconds": 10.0,"rel_energy_drift_final": 1.18065986619641e-06,"rel_energy_drift_max": 1.5062681917967003e-06},{"dt": 0.005,"integrator": "Euler","seconds": 10.0,"rel_energy_drift_final": 0.0016362684976390192,"rel_energy_drift_max": 0.00181127442613719},{"dt": 0.005,"integrator": "RK4","seconds": 10.0,"rel_energy_drift_final": 1.4087484375721107e-07,"rel_energy_drift_max": 1.7852482235141677e-07},{"dt": 0.002,"integrator": "Euler","seconds": 10.0,"rel_energy_drift_final": 0.0006651717468267735,"rel_energy_drift_max": 0.0007196702355656947},{"dt": 0.002,"integrator": "RK4","seconds": 10.0,"rel_energy_drift_final": 8.817983090127101e-09,"rel_energy_drift_max": 1.1127338774856674e-08},{"dt": 0.001,"integrator": "Euler","seconds": 10.0,"rel_energy_drift_final": 0.0003343047013307526,"rel_energy_drift_max": 0.0003590092287424367},{"dt": 0.001,"integrator": "RK4","seconds": 10.0,"rel_energy_drift_final": 1.0952409019775168e-09,"rel_energy_drift_max": 1.37983345445304e-09}]""")

fig, ax = plt.subplots(figsize=(9.2, 4.8))
for integ, mk, col in [("Euler", "o", "#264653"), ("RK4", "s", "#e9c46a")]:
    rows = sorted([r for r in ACC if r["integrator"] == integ], key=lambda r: r["dt"])
    if not rows: continue
    dts  = [r["dt"] for r in rows]
    drift= [r["rel_energy_drift_final"] for r in rows]
    ax.loglog(dts, drift, mk + "-", lw=2.5, ms=8, color=col, label=f"MuJoCo {integ}")
    big, small = rows[-1], rows[0]
    order = (np.log(big["rel_energy_drift_final"]/small["rel_energy_drift_final"])
             / np.log(big["dt"]/small["dt"]))
    print(f"{integ:>6}: dt reduced {big['dt']/small['dt']:.0f}x -> error reduced "
          f"{big['rel_energy_drift_final']/small['rel_energy_drift_final']:>10,.0f}x"
          f"   => empirical order ~{order:.2f}")

ax.set_xlabel("timestep dt (s)"); ax.set_ylabel("relative energy drift after 10 s")
ax.set_title("Integrator accuracy — lower is better")
ax.grid(alpha=.3, which="both"); ax.legend()
plt.tight_layout(); plt.show()
'''),

("md", """
**Euler measures ~1st order. RK4 measures ~3rd**, not the textbook 4th, because
MuJoCo's RK4 handles constraints and contacts in a way that is not pure
Runge-Kutta. The gap between the textbook number and the measured one is
exactly why you measure.

The consequence is worth real money: **if your simulation is inaccurate, change
integrator before shrinking the timestep.** Dropping dt by 10x buys 10x less
error under Euler and roughly 1000x under RK4, at maybe 4x the cost per step.
People routinely burn compute stepping at 1 kHz with Euler when RK4 at 100 Hz
would be both faster and more accurate.
"""),

("md", """
## Parallelism, isolated

MJX is the same MuJoCo physics compiled through JAX, so batching it isolates
the *parallelism* variable from the *engine* variable.
"""),

("code", r'''
MJX = json.loads(r"""{"engine": "mjx","mujoco_version": "3.12.0","jax_version": "0.11.1","backend": "cpu","devices": ["cpu:0"],"platform": "macOS-26.7-arm64-arm-64bit","batch_scaling": [{"batch_size": 1,"steps_per_env": 300,"total_env_steps": 300,"compile_s": 1.221,"wall_s": 0.0424,"env_steps_per_s": 7082.3,"realtime_factor_total": 35.4,"speedup_vs_batch1": 1.0},{"batch_size": 4,"steps_per_env": 300,"total_env_steps": 1200,"compile_s": 1.326,"wall_s": 0.0495,"env_steps_per_s": 24242.9,"realtime_factor_total": 121.2,"speedup_vs_batch1": 3.42},{"batch_size": 16,"steps_per_env": 300,"total_env_steps": 4800,"compile_s": 1.163,"wall_s": 0.0548,"env_steps_per_s": 87514.3,"realtime_factor_total": 437.6,"speedup_vs_batch1": 12.36},{"batch_size": 64,"steps_per_env": 300,"total_env_steps": 19200,"compile_s": 1.596,"wall_s": 0.0803,"env_steps_per_s": 239185.2,"realtime_factor_total": 1195.9,"speedup_vs_batch1": 33.77},{"batch_size": 256,"steps_per_env": 300,"total_env_steps": 76800,"compile_s": 1.369,"wall_s": 0.0924,"env_steps_per_s": 831288.8,"realtime_factor_total": 4156.4,"speedup_vs_batch1": 117.38},{"batch_size": 1024,"steps_per_env": 300,"total_env_steps": 307200,"compile_s": 1.267,"wall_s": 0.2028,"env_steps_per_s": 1514971.6,"realtime_factor_total": 7574.9,"speedup_vs_batch1": 213.91}]}""")
rows = MJX["batch_scaling"]
bs  = [r["batch_size"] for r in rows]
sp  = [r["speedup_vs_batch1"] for r in rows]

fig, ax = plt.subplots(figsize=(8.6, 4.6))
ax.loglog(bs, sp, "o-", lw=2.5, ms=8, color="#2a9d8f", label="measured")
ax.loglog(bs, bs, "--", lw=1.5, color="gray", label="perfect linear")
ax.set_xlabel("parallel environments"); ax.set_ylabel("speedup vs batch=1")
ax.set_title(f"MJX batch scaling on {MJX['backend'].upper()} — knee near 256")
ax.grid(alpha=.3, which="both"); ax.legend()
plt.tight_layout(); plt.show()

best = rows[-1]
print(f"batch {best['batch_size']}: {best['env_steps_per_s']:,.0f} env steps/s "
      f"= {best['speedup_vs_batch1']:.0f}x speedup")
print(f"efficiency vs perfect scaling: "
      f"{100*best['speedup_vs_batch1']/best['batch_size']:.1f}%")
'''),

("md", """
**1.5 million environment steps per second on a laptop CPU**, from vectorization
alone. But 1024x the environments returned only 214x the throughput - about
21% of ideal, with the curve bending away near 256.

Every parallel simulator has a saturation point. Running 8192 environments
because a paper did may be buying VRAM that returns almost nothing. Measure
your own knee.
"""),

("md", """
## How the first two versions of this benchmark were wrong

I ran this three times and got three different answers. The first two were
artifacts of my own protocol, and the failure mode generalises.

**Version 1 said MuJoCo wins everywhere, by up to 145x.** The scene was sparse
- boxes scattered widely, few of them touching - so it mostly measured free
fall. Isaac's fixed overhead dominated and MuJoCo looked untouchable.

**Version 2 said Isaac wins everywhere.** I made the scene contact-rich but used
*adaptive step counts* (200 steps at 512 bodies, 30 at 4096) to dodge a timeout.
That silently changed what was being measured: at 30 steps a 4096-box scene is
still in mid-air. Different body counts were measuring different physics.

The tell was in the data both times, and I missed it once:

```
bodies:      512    1024    2048    4096
contacts:   1002     755     528     120     <- falling as bodies rise
```

Contacts should *rise* with body count. Watching them fall is the sound of a
benchmark measuring the wrong thing.

**Version 3** - this one - settles every scene for 400 untimed steps, then times
exactly 100 steady-state steps, with identical layout and step budget on both
engines. Now contacts scale as expected (~2 per settled body) and throughput
decreases monotonically.

The transferable lesson: **a benchmark number that looks plausible is not
evidence.** Both wrong versions produced clean, believable curves. What caught
them was a *secondary* quantity - the contact count - that had no reason to
misbehave unless the setup was broken. Always log something you are not
optimising for.
"""),

("md", """
## Reproducing

Generators for both engines are in the linked dataset and emit an identical
JSON schema so results can be joined directly. The MuJoCo and MJX sides run on
any machine, including this notebook. The Isaac Sim side needs an NVIDIA GPU
with **RT cores** — a T4, L4, L40S or any RTX card. Not an A100 or H100: those
have no RT cores, which remains the most counterintuitive constraint in cloud
robotics simulation.

If you run this on different hardware, **post your numbers below**. A crossover
table across GPU and CPU types would be more useful than any single column,
and I have not seen one published.
"""),
]
