TITLE = 'Robot Motion Capture From a GPU That Cannot Render'
SLUG = 'robot-motion-capture-from-a-gpu-that-cannot-render'
SUBTITLE = ("Isaac Sim's renderer does not work on Kaggle. Link world-poses are "
            "just numbers, so 26 robots were recorded anyway.")
TAGS = ['robotics', 'gpu', 'physics']

CELLS = [
("md", """
## The constraint, and the way around it

Isaac Sim's RTX renderer does not initialise on Kaggle's free tier. It wants an
X server and the NVIDIA container runtime, and gets neither. No images, no
video, no camera sensors.

But **rendering is not the only way to see a simulation.** Every link in a robot
has a world pose at every physics step, and those are just numbers. Record them
and the motion can be reconstructed afterwards, anywhere, with matplotlib.

This is not a re-enactment. The positions are exactly what PhysX computed. What
is missing is only the *appearance* - meshes, materials, lighting - not the
motion.

26 robots were captured this way: quadrupeds and humanoids dropped from 0.7 m
and left to settle, arms and hands sweeping their joint ranges. 120 frames each
at 40 fps, from 120 Hz physics.
"""),

("code", r'''
import json, os

EMBEDDED = json.loads(r"""{"n": 26,"n_ok": 26,"capture_fps": 40,"physics_hz": 120,"robots": [{"name": "Galbot","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 77,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "SanctuaryAI","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 77,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "Fraunhofer","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 64,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "RobotEra","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 55,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "XHumanoid","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 54,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "Agibot","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 34,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "1X","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 33,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "FourierIntelligence","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 32,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "Ihmcrobotics","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 25,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "ShadowRobot","mode": "sweep","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 24,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "BoosterRobotics","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 23,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "OpenArm","mode": "sweep","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 22,"n_links": 60,"n_frames": 120,"fps": 40},{"name": "DeepRobotics","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 16,"n_links": 52,"n_frames": 120,"fps": 40},{"name": "WonikRobotics","mode": "sweep","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 16,"n_links": 58,"n_frames": 120,"fps": 40},{"name": "XiaoPeng","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 16,"n_links": 52,"n_frames": 120,"fps": 40},{"name": "Agility","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 14,"n_links": 51,"n_frames": 120,"fps": 40},{"name": "ANYbotics","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 12,"n_links": 53,"n_frames": 120,"fps": 40},{"name": "BostonDynamics","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 12,"n_links": 18,"n_frames": 120,"fps": 40},{"name": "Unitree","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 12,"n_links": 19,"n_frames": 120,"fps": 40},{"name": "Kinova","mode": "sweep","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 7,"n_links": 10,"n_frames": 120,"fps": 40},{"name": "Kuka","mode": "sweep","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 7,"n_links": 47,"n_frames": 120,"fps": 40},{"name": "Fanuc","mode": "sweep","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 6,"n_links": 43,"n_frames": 120,"fps": 40},{"name": "Robotiq","mode": "sweep","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 6,"n_links": 21,"n_frames": 120,"fps": 40},{"name": "UniversalRobots","mode": "sweep","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 6,"n_links": 24,"n_frames": 120,"fps": 40},{"name": "NASA","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 4,"n_links": 59,"n_frames": 120,"fps": 40},{"name": "iRobot","mode": "drop","sweep_api": "set_joint_positions","articulation_methods": ["get_applied_joint_efforts","get_joint_positions","get_joint_velocities","get_joints_default_state","get_joints_state","get_measured_joint_efforts","get_measured_joint_forces","set_joint_efforts","set_joint_positions","set_joint_velocities","set_joints_default_state"],"ok": true,"num_dof": 4,"n_links": 40,"n_frames": 120,"fps": 40}]}""")
DATA = "/kaggle/input/isaac-robot-motion-capture"
p = os.path.join(DATA, "mocap_summary.json")
d = json.load(open(p)) if os.path.exists(p) else EMBEDDED

ok = [r for r in d["robots"] if r.get("ok")]
print(f"{d['n_ok']}/{d['n']} robots captured at {d['capture_fps']} fps "
      f"from {d['physics_hz']} Hz physics")
print()
print(f"{'robot':<22} {'DOF':>4} {'mode':>7} {'links':>6} {'frames':>7}")
for r in sorted(ok, key=lambda r: -r["num_dof"])[:14]:
    print(f"{r['name']:<22} {r['num_dof']:>4} {r['mode']:>7} "
          f"{r['n_links']:>6} {r['n_frames']:>7}")
'''),

("md", """
## How the capture works

The whole technique is a few lines inside the stepping loop. `UsdGeom.XformCache`
is the part worth knowing - it resolves a prim's local-to-world transform and
caches intermediates, so querying 60 links per frame stays cheap.

```python
from pxr import UsdGeom, Usd
import omni.usd

stage = omni.usd.get_context().get_stage()

# every Xformable under the robot is a link we can track
links = [p.GetPath().pathString
         for p in Usd.PrimRange(stage.GetPrimAtPath("/World/bot"))
         if p.IsA(UsdGeom.Xformable)]

xc = UsdGeom.XformCache()
frames = []
for i in range(360):                    # 3 s at 120 Hz
    world.step(render=False)            # render=False: no renderer needed
    if i % 3 == 0:                      # subsample to 40 fps
        xc.Clear()                      # REQUIRED, see below
        frames.append([
            list(xc.GetLocalToWorldTransform(
                stage.GetPrimAtPath(lp)).ExtractTranslation())
            for lp in links])
```

`xc.Clear()` each frame is not optional. `XformCache` caches by design, so
without clearing it you record the first frame 120 times - and the result looks
like a robot that never moves, which is easy to misread as a physics problem.
"""),

("md", """
## The mistake worth copying

My first capture looked fine and was wrong. Checking heights before believing
the videos:

```
Spot height:  t=0     0.084 m
              t=1 s   0.552 m
              t=3 s   0.552 m
```

The robot **rises**. That is not a drop - it spawns intersecting the ground
plane and physics ejects it. Real dynamics, correctly simulated, and "dropped
and settling" would have been a false caption on every video in the set.

The fix is to lift it before releasing:

```python
if mode == "drop":
    pos, orn = art.get_world_pose()
    pos[2] += 0.7                 # actually above the ground
    art.set_world_pose(position=pos, orientation=orn)
```

After which the same check reads the way a drop should:

```
Spot    0.839 -> 0.552   FELL
ANYmal  0.779 -> 0.571   FELL
Cassie  0.822 -> 0.356   FELL
```

One assertion on the data - does the height decrease? - separates a real
recording from a confident-looking artifact. It costs a line, and it is the
difference between publishing physics and publishing a spawn glitch.
"""),

("md", """
## Known bad captures

Four of the 26 do not show what their label claims. They are marked in the
dataset rather than quietly dropped:

| robot | issue |
|---|---|
| Agibot | drop that never falls - height unchanged, likely a fixed root |
| Kuka | joint sweep did not take |
| WonikRobotics | joint sweep did not take |
| SanctuaryAI | rises instead of falling - 0.7 m is not enough clearance for a 77-DOF humanoid whose feet start below the plane |

They are real captures of real simulator state. They are simply not
demonstrations of the motion the filename implies, and a dataset that hides
that is worse than one that says so.

## What the technique is good for

- **Any headless GPU** - CI runners, notebooks, clusters with no display
- **Debugging** - joint trajectories and link paths are more diagnostic than a
  rendered video anyway
- **Datasets** - poses are small. 26 robots x 120 frames x 60 links is 4.3 MB;
  equivalent video is orders of magnitude larger
- **Reproducibility** - anyone can re-render your capture with a different
  camera or overlay without re-running the simulation

The reconstruction is a 3D scatter per frame plus ffmpeg. The linked dataset
includes the renderer and every captured trajectory.
"""),
]
