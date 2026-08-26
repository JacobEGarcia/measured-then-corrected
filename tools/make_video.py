"""Animate the REAL Isaac Sim trajectory measured on a free Kaggle T4."""
import json, os, shutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

traj = json.load(open("/tmp/fin5/trajectory.json"))
h = np.array(traj["heights"]); dt = traj["dt"]
t = np.arange(len(h)) * dt
below = np.flatnonzero(h <= 0.11)
fc = below[0] if below.size else len(h)
a, _, _ = np.polyfit(t[:fc], h[:fc], 2)
g = -2 * a

FR = "media/_frames"
shutil.rmtree(FR, ignore_errors=True); os.makedirs(FR)
plt.rcParams.update({"figure.dpi": 110, "font.size": 10})
HALF = 0.1   # cube half-extent

for i in range(len(h)):
    fig, (axl, axr) = plt.subplots(1, 2, figsize=(11, 4.6),
                                   gridspec_kw={"width_ratios": [1, 1.5]})
    # --- left: the cube itself ---
    axl.add_patch(patches.Rectangle((-1.2, -0.06), 2.4, 0.06,
                                    color="#8d99ae"))            # ground
    axl.add_patch(patches.Rectangle((-HALF, h[i] - HALF), 2 * HALF, 2 * HALF,
                                    facecolor="#e63946", edgecolor="#6a040f",
                                    lw=1.5))
    axl.set_xlim(-0.7, 0.7); axl.set_ylim(-0.08, 1.15)
    axl.set_aspect("equal"); axl.set_xticks([])
    axl.set_ylabel("height (m)")
    axl.set_title(f"t = {t[i]:5.2f} s      z = {h[i]:.4f} m", fontfamily="monospace")
    axl.grid(alpha=0.25, axis="y")

    # --- right: trajectory filling in ---
    axr.plot(t, h, lw=1, color="#d8d8d8")
    axr.plot(t[:i+1], h[:i+1], lw=2.6, color="#2a9d8f")
    axr.scatter([t[i]], [h[i]], s=55, color="#e63946", zorder=4)
    axr.axhline(0.1, color="gray", ls=":", lw=1.2)
    axr.set_xlim(0, t[-1]); axr.set_ylim(0, 1.1)
    axr.set_xlabel("time (s)"); axr.set_ylabel("cube height (m)")
    axr.set_title(f"Isaac Sim PhysX on a free Kaggle T4  —  recovered g = {g:.4f} m/s²")
    axr.grid(alpha=0.3)

    fig.suptitle("Real measured trajectory, 120 steps @ 60 Hz", y=0.995, fontsize=9,
                 color="#555")
    plt.tight_layout()
    plt.savefig(f"{FR}/f{i:04d}.png"); plt.close()

print("rendered", len(h), "frames")
