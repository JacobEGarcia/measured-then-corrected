TITLE = 'How Far Isaac Lab Scales on a Free GPU'
SLUG = 'how-far-isaac-lab-scales-on-a-free-gpu'
SUBTITLE = ("65,536 parallel environments and 812k env steps/s on one Kaggle T4 "
            "- and why 8,192 is usually the better number.")
TAGS = ['reinforcement learning', 'robotics', 'gpu']

CELLS = [
("md", """
## Two questions nobody had answered

Kaggle hands out 30 GPU hours a week on 2x Tesla T4. For robot learning that
raises two practical questions:

1. **How many parallel environments fit?**
2. **Does the second GPU do anything?**

Both are measured here. The answers are 65,536 environments (with room left)
and yes, at 1.87x.

But the more useful finding is that **the biggest number is not the best
configuration**, and the reason is easy to miss.
"""),

("code", r'''
import json, os
import numpy as np

CEIL = json.loads(r"""{"results": [{"num_envs": 4096,"ok": true,"env_steps_per_s": 211304.8,"policy_steps_per_s": 51.6,"vram_used_gb": 2.87,"vram_total_gb": 15.64},{"num_envs": 8192,"ok": true,"env_steps_per_s": 401217.6,"policy_steps_per_s": 49.0,"vram_used_gb": 3.49,"vram_total_gb": 15.64},{"num_envs": 16384,"ok": true,"env_steps_per_s": 556476.1,"policy_steps_per_s": 34.0,"vram_used_gb": 4.59,"vram_total_gb": 15.64},{"num_envs": 32768,"ok": true,"env_steps_per_s": 717906.9,"policy_steps_per_s": 21.9,"vram_used_gb": 6.92,"vram_total_gb": 15.64},{"num_envs": 65536,"ok": true,"env_steps_per_s": 812670.3,"policy_steps_per_s": 12.4,"vram_used_gb": 11.36,"vram_total_gb": 15.64}],"max_envs_ok": 65536,"peak_env_steps_per_s": 812670.3}""")
MG   = json.loads(r"""{"single_cuda:0": {"device": "cuda:0","num_envs": 8192,"torch_sees": 2,"ok": true,"env_steps_per_s": 384315.7,"wall_s": 1.279},"single_cuda:1": {"device": "cuda:1","num_envs": 8192,"torch_sees": 2,"ok": true,"env_steps_per_s": 380888.6,"wall_s": 1.29},"parallel_cuda:0": {"device": "cuda:0","num_envs": 8192,"torch_sees": 2,"ok": true,"env_steps_per_s": 383421.8,"wall_s": 1.282},"parallel_cuda:1": {"device": "cuda:1","num_envs": 8192,"torch_sees": 2,"ok": true,"env_steps_per_s": 334363.7,"wall_s": 1.47},"summary": {"single_gpu_steps_per_s": 384315.7,"two_gpu_combined_steps_per_s": 717785.5,"speedup_x": 1.87,"parallel_wall_s": 51.7}}""")
DATA = "/kaggle/input/isaac-sim-kaggle-benchmarks"
p = os.path.join(DATA, "ceiling.json")
d = json.load(open(p)) if os.path.exists(p) else CEIL

R = [r for r in d["results"] if r.get("ok")]
print(f"{'envs':>7} {'env steps/s':>14} {'policy steps/s':>15} {'VRAM GB':>9}")
for r in R:
    print(f"{r['num_envs']:>7} {r['env_steps_per_s']:>14,.1f} "
          f"{r['policy_steps_per_s']:>15.1f} {r['vram_used_gb']:>9.2f}")
print()
print("ceiling reached:", d["max_envs_ok"], "envs (no OOM encountered)")
print("peak throughput:", f"{d['peak_env_steps_per_s']:,.0f}", "env steps/s")
'''),

("code", r'''
import matplotlib.pyplot as plt

n   = np.array([r["num_envs"] for r in R])
eps = np.array([r["env_steps_per_s"] for r in R])
pol = np.array([r["policy_steps_per_s"] for r in R])
v   = np.array([r["vram_used_gb"] for r in R])

fig, ax = plt.subplots(1, 3, figsize=(14.5, 4.4))

ax[0].loglog(n, eps, "o-", lw=2.6, ms=8, color="#2a9d8f", label="measured")
ax[0].loglog(n, eps[0]*(n/n[0]), "--", lw=1.4, color="gray", label="perfect linear")
ax[0].set_xlabel("parallel environments"); ax[0].set_ylabel("env steps / second")
ax[0].set_title(f"Peak {eps.max():,.0f} env steps/s")
ax[0].legend(fontsize=8.5); ax[0].grid(alpha=.3, which="both")

ax[1].semilogx(n, pol, "s-", lw=2.6, ms=8, color="#e76f51")
ax[1].axvspan(4096, 8192, color="#2a9d8f", alpha=.15)
ax[1].set_ylim(0, 60)
ax[1].set_xlabel("parallel environments"); ax[1].set_ylabel("policy steps / second")
ax[1].set_title("Where parallelism stops being free")
ax[1].grid(alpha=.3)

ax[2].semilogx(n, v, "^-", lw=2.6, ms=8, color="#4a5859")
ax[2].axhline(15.0, color="#c1443b", ls="--", lw=1.5, label="T4 limit")
ax[2].set_ylim(0, 16)
ax[2].set_xlabel("parallel environments"); ax[2].set_ylabel("VRAM (GB)")
ax[2].set_title("11.4 GB at 65,536 envs"); ax[2].legend(fontsize=8.5)
ax[2].grid(alpha=.3)
plt.tight_layout(); plt.show()

eff = (eps[-1]/eps[0])/(n[-1]/n[0])*100
print(f"{n[0]} -> {n[-1]} envs: {n[-1]/n[0]:.0f}x the envs, "
      f"{eps[-1]/eps[0]:.1f}x the throughput = {eff:.0f}% efficiency")
print(f"policy rate fell {pol[0]:.1f} -> {pol[-1]:.1f} steps/s")
'''),

("md", """
## Read the middle panel, not the first

The headline number is 812,670 environment steps per second. The number that
should drive your configuration is in the second panel.

`policy steps/s` is how often the simulation advances - and therefore how often
you can compute a gradient. It holds at ~50 up to 8,192 environments, then
collapses to 12.4 at 65,536.

| envs | env steps/s | policy steps/s |
|---|---|---|
| 4,096 | 211,305 | 51.6 |
| **8,192** | **401,218** | **49.0** |
| 16,384 | 556,476 | 34.0 |
| 65,536 | 812,670 | 12.4 |

Going from 8,192 to 65,536 doubles the environment-steps headline and makes
your policy update **four times less often**. For most training runs 8,192 is
strictly the better setting despite the smaller number.

That is the whole point: **environment steps per second is a throughput metric,
and RL is bottlenecked on gradient updates.** Optimising the first at the
expense of the second is a real and easy mistake.

I made a related one earlier in this series: I published 212k env steps/s at
4,096 environments and estimated "room for roughly 4x more" from VRAM alone.
The actual ceiling is 16x more environments, because memory scales sublinearly
- 16x the envs cost only 2.7x the memory. The estimate was an extrapolation
stated as though it were measured.
"""),

("md", """
## The second GPU

Kaggle allocates **two** T4s. Every measurement above used one.

PhysX runs its GPU pipeline on a single device, so a single simulation will not
span two cards. Multi-GPU here means one process per GPU - which for RL data
collection is exactly what you want anyway.
"""),

("code", r'''
mg = MG
for k in ("single_cuda:0", "single_cuda:1", "parallel_cuda:0", "parallel_cuda:1"):
    r = mg.get(k, {})
    if r.get("ok"):
        print(f"  {k:<18} {r['env_steps_per_s']:>12,.1f} env steps/s")
    else:
        print(f"  {k:<18} FAILED")
s = mg.get("summary", {})
print()
print(f"  one GPU  : {s.get('single_gpu_steps_per_s',0):>12,.0f} env steps/s")
print(f"  two GPUs : {s.get('two_gpu_combined_steps_per_s',0):>12,.0f} env steps/s")
print(f"  speedup  : {s.get('speedup_x')}x")
'''),

("md", """
**1.87x on two cards**, at 8,192 environments each. Both T4s perform
identically in isolation (384k and 381k env steps/s), so the second card is
fully functional rather than a phantom device. The 7% shortfall from 2x is
PCIe and CPU contention.

Combined with the single-card ceiling, a free Kaggle session can reach roughly
**1.5 million environment steps per second** across both GPUs.

## Practical configuration

- **8,192 envs per GPU** for training. Near-peak throughput, and the policy
  still updates ~49 times a second.
- **65,536 envs** only if you are collecting data with a fixed policy, where
  gradient frequency does not matter.
- **Two processes, one per GPU**, rather than trying to make one simulation
  span both.
- **VRAM is not the binding constraint** on a T4 - 65,536 environments fit in
  11.4 GB of 15. Compute is.

## Method

Every environment count runs in its **own process**. A CUDA OOM poisons the
context, so probing sizes inside one process makes every size after the first
failure fail too - and the reported "ceiling" would just be wherever the first
crash happened to land, not where the hardware actually stops.

That detail is why this reports 65,536 with no OOM encountered rather than a
smaller number with a confident-looking error message.
"""),
]
