"""One montage of every captured robot, plus the individual clips."""
import json, os, shutil, subprocess
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

d = json.load(open("out/mocap.json"))
robots = [r for r in d["robots"] if r.get("ok")]
robots.sort(key=lambda r: -r["num_dof"])
N = len(robots)
cols = 6
rows = -(-N // cols)
F = {r["name"]: np.array(r["frames"]) for r in robots}
n_frames = min(len(v) for v in F.values())

frame_dir = "media/_grid"
shutil.rmtree(frame_dir, ignore_errors=True); os.makedirs(frame_dir)
plt.rcParams.update({"figure.dpi": 96})

for i in range(n_frames):
    fig = plt.figure(figsize=(cols*2.5, rows*2.5))
    for k, r in enumerate(robots):
        ax = fig.add_subplot(rows, cols, k+1, projection="3d")
        P = F[r["name"]]
        lo, hi = P.reshape(-1,3).min(0), P.reshape(-1,3).max(0)
        pad = max(0.1, float((hi-lo).max())*0.1)
        p = P[i]
        ax.scatter(p[:,0], p[:,1], p[:,2], s=9, c=p[:,2], cmap="viridis",
                   depthshade=False)
        ax.set_xlim(lo[0]-pad, hi[0]+pad); ax.set_ylim(lo[1]-pad, hi[1]+pad)
        ax.set_zlim(0, max(hi[2]+pad, 0.3))
        ax.set_box_aspect((1,1,0.85))
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        ax.view_init(elev=15, azim=35 + i*0.6)
        ax.set_title(f"{r['name']}\n{r['num_dof']} DOF · {r['mode']}", fontsize=7.5, pad=1)
        for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
            pane.pane.set_alpha(0.04)
    fig.suptitle(f"NVIDIA Isaac Sim on a free Kaggle T4 — {N} robots, "
                 f"physics only, no renderer     t = {i/40:.2f}s",
                 fontsize=13, y=0.995)
    plt.tight_layout(rect=[0,0,1,0.97])
    plt.savefig(f"{frame_dir}/f{i:04d}.png"); plt.close()
    if i % 30 == 0: print(f"  grid frame {i}/{n_frames}", flush=True)

subprocess.run(f'ffmpeg -y -loglevel error -framerate 40 -i {frame_dir}/f%04d.png '
               f'-c:v libx264 -pix_fmt yuv420p -crf 23 '
               f'-vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" media/robot_grid.mp4',
               shell=True, check=True)
shutil.rmtree(frame_dir, ignore_errors=True)
print("wrote media/robot_grid.mp4", round(os.path.getsize("media/robot_grid.mp4")/1e6,2), "MB")
