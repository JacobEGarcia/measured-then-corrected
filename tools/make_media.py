"""Render the session's real measured data into figures and an animation."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = "media"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 10})

# ---- 1. Isaac Sim free fall, measured on a free Kaggle T4 -----------------
traj = json.load(open("/tmp/fin5/trajectory.json"))
h = np.array(traj["heights"]); t = np.arange(len(h)) * traj["dt"]
below = np.flatnonzero(h <= 0.11)
fc = below[0] if below.size else len(h)
tf, zf = t[:fc], h[:fc]
a, b, c = np.polyfit(tf, zf, 2)
g = -2 * a

fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(t, h, lw=2.6, color="#2a9d8f", label="Isaac Sim PhysX (free Kaggle T4)")
ax.plot(tf, h[0] - 0.5 * 9.81 * tf**2, "--", lw=1.8, color="crimson",
        label=r"analytic  $z_0-\frac{1}{2}gt^2$")
ax.scatter(tf, zf, s=18, color="#264653", zorder=3,
           label=f"{fc} pre-impact samples (fitted)")
ax.axhline(0.1, color="gray", ls=":", lw=1.2, label="resting height = half extent")
ax.set_xlabel("time (s)"); ax.set_ylabel("cube height (m)")
ax.set_title(f"Isaac Sim on a free Kaggle T4 — recovered g = {g:.4f} m/s²  "
             f"(error {abs(g-9.81)/9.81*100:.3f}%)")
ax.legend(fontsize=8.5); ax.grid(alpha=0.3); ax.set_ylim(0, 1.08)
plt.tight_layout(); plt.savefig(f"{OUT}/isaac_freefall.png"); plt.close()
print("wrote isaac_freefall.png   g =", round(g, 4))

# ---- 2 & 3. Benchmark figures from the measured JSON ----------------------
mj = json.load(open("out/bench_mujoco.json"))
mx = json.load(open("out/bench_mjx.json"))

fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.4))
n = [r["n_boxes"] for r in mj["throughput"]]
ax[0].loglog(n, [r["steps_per_s"] for r in mj["throughput"]], "o-", lw=2.4, ms=7,
             color="#e76f51")
ax[0].set_xlabel("bodies"); ax[0].set_ylabel("physics steps / s")
ax[0].set_title("MuJoCo throughput vs scene complexity")
for integ, mk, col in [("Euler", "o", "#264653"), ("RK4", "s", "#e9c46a")]:
    rows = [r for r in mj["accuracy"] if r["integrator"] == integ]
    ax[1].loglog([r["dt"] for r in rows],
                 [r["rel_energy_drift_final"] for r in rows],
                 mk + "-", lw=2.4, ms=7, color=col, label=f"MuJoCo {integ}")
ax[1].set_xlabel("timestep dt (s)"); ax[1].set_ylabel("relative energy drift @10s")
ax[1].set_title("Integrator accuracy — Euler ~1st, RK4 ~3rd order")
ax[1].legend()
for a_ in ax: a_.grid(alpha=0.3, which="both")
plt.tight_layout(); plt.savefig(f"{OUT}/mujoco_benchmark.png"); plt.close()
print("wrote mujoco_benchmark.png")

rows = mx["batch_scaling"]
bs = [r["batch_size"] for r in rows]
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.4))
ax[0].loglog(bs, [r["env_steps_per_s"] for r in rows], "o-", lw=2.4, ms=7,
             color="#2a9d8f")
ax[0].set_xlabel("parallel environments"); ax[0].set_ylabel("env steps / s")
ax[0].set_title(f"MJX throughput ({mx['backend'].upper()}) — 1.5M steps/s on a laptop")
ax[1].loglog(bs, [r["speedup_vs_batch1"] for r in rows], "o-", lw=2.4, ms=7,
             color="#2a9d8f", label="measured")
ax[1].loglog(bs, bs, "--", lw=1.5, color="gray", label="perfect linear")
ax[1].set_xlabel("parallel environments"); ax[1].set_ylabel("speedup vs batch=1")
ax[1].set_title("Saturation knee near 256 — 21% of ideal at 1024")
ax[1].legend()
for a_ in ax: a_.grid(alpha=0.3, which="both")
plt.tight_layout(); plt.savefig(f"{OUT}/mjx_scaling.png"); plt.close()
print("wrote mjx_scaling.png")
