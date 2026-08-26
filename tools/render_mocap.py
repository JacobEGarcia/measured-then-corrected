"""Turn captured link poses into 3D skeleton animations.

Isaac Sim's renderer does not work on Kaggle, so there are no images from the
simulation. But every link's world position was recorded at 40 fps, and a point
cloud animated from those positions is a real recording of what the physics
did -- the robot really did fall and settle exactly like this.
"""
import json, os, shutil, subprocess, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: registers 3d projection

d = json.load(open("out/mocap.json"))
robots = [r for r in d["robots"] if r.get("ok")]
os.makedirs("media/mocap", exist_ok=True)
plt.rcParams.update({"figure.dpi": 110})


def render(rec, out_mp4, trail=8):
    F = np.array(rec["frames"])              # (frames, links, 3)
    n_f, n_l, _ = F.shape
    lo, hi = F.reshape(-1, 3).min(0), F.reshape(-1, 3).max(0)
    pad = max(0.12, float((hi - lo).max()) * 0.12)
    frame_dir = f"media/mocap/_{rec['name']}"
    shutil.rmtree(frame_dir, ignore_errors=True); os.makedirs(frame_dir)

    for i in range(n_f):
        fig = plt.figure(figsize=(6.4, 5.2))
        ax = fig.add_subplot(111, projection="3d")
        # ground plane
        gx, gy = np.meshgrid(np.linspace(lo[0]-pad, hi[0]+pad, 2),
                             np.linspace(lo[1]-pad, hi[1]+pad, 2))
        ax.plot_surface(gx, gy, np.zeros_like(gx), color="#8d99ae", alpha=.18)
        # motion trail
        for k in range(max(0, i-trail), i):
            a = (k - (i-trail)) / max(1, trail)
            ax.scatter(F[k, :, 0], F[k, :, 1], F[k, :, 2],
                       s=6, color="#2a9d8f", alpha=.10 + .25*a, depthshade=False)
        p = F[i]
        ax.scatter(p[:, 0], p[:, 1], p[:, 2], s=34, c=p[:, 2],
                   cmap="viridis", edgecolor="#1d3557", linewidth=.4,
                   depthshade=False)
        ax.set_xlim(lo[0]-pad, hi[0]+pad); ax.set_ylim(lo[1]-pad, hi[1]+pad)
        ax.set_zlim(0, max(hi[2]+pad, 0.4))
        ax.set_box_aspect((1, 1, 0.8))
        ax.set_xticklabels([]); ax.set_yticklabels([])
        ax.set_zlabel("height (m)", fontsize=8)
        ax.view_init(elev=16, azim=35 + i*0.7)     # slow orbit
        ax.set_title(f"{rec['name']}  ·  {rec['num_dof']} DOF  ·  {rec['mode']}\n"
                     f"t = {i/rec['fps']:.2f}s   ({n_l} links tracked)",
                     fontsize=10)
        plt.tight_layout(); plt.savefig(f"{frame_dir}/f{i:04d}.png"); plt.close()

    subprocess.run(
        f'ffmpeg -y -loglevel error -framerate {rec["fps"]} '
        f'-i {frame_dir}/f%04d.png -c:v libx264 -pix_fmt yuv420p -crf 20 '
        f'-vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" {out_mp4}', shell=True, check=True)
    shutil.rmtree(frame_dir, ignore_errors=True)
    return os.path.getsize(out_mp4)


only = sys.argv[1:] or None
for rec in robots:
    if only and rec["name"] not in only:
        continue
    out = f"media/mocap/{rec['name']}.mp4"
    sz = render(rec, out)
    print(f"  {rec['name']:<12} {rec['n_frames']:>4} frames -> {out} ({sz/1e6:.2f} MB)")
