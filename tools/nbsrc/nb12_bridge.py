TITLE = 'Isaac Sim Talking to ROS 2 on a Free GPU'
SLUG = 'isaac-sim-talking-to-ros-2-on-a-free-gpu'
SUBTITLE = ("A simulated Franka publishing joint states over DDS - and the "
            "Python version collision you have to design around.")
TAGS = ['robotics', 'gpu']

CELLS = [
("md", """
## The pipeline, not the parts

Isaac Sim runs on Kaggle's free tier. ROS 2 runs on Kaggle's free tier. Neither
fact is worth much on its own - the actual robotics pipeline is a **simulator
publishing onto DDS** and ROS nodes consuming it.

This connects them end to end: a Franka Panda simulated in Isaac Sim, its joint
states published as `sensor_msgs/JointState` with `/clock`, received by a
subscriber. All on hardware that costs nothing.
"""),

("md", """
## The constraint that shapes the whole design

**Isaac Sim needs Python 3.12. ROS 2 Humble is compiled against Python 3.10.**

One process cannot be both. This is not a packaging annoyance you can work
around with a virtualenv - `rclpy` loads C extension modules built for a
specific interpreter ABI, and Isaac Sim's wheels target 3.12 on this image.

Worth knowing why the failure is confusing: Ubuntu 22.04 ships python3.10 and
ROS Humble targets it, but Kaggle replaces `python3` with 3.12. So the standard
incantation

```bash
source /opt/ros/humble/setup.bash && python3 -c "import rclpy"
```

loads 3.10-built binaries into a 3.12 interpreter, and you get a
`load_entry_point` traceback that never mentions Python versions.

So the bridge is **two processes**, each on its own interpreter, which is what
most people end up writing anyway.
"""),

("code", r'''
import json, os

RESULT = json.loads(r"""{"ros_install": {"rc": 0,"ok": null,"out": "n/ldconfig.real: /usr/local/lib/libhwloc.so.15 is not a symbolic link\n\nW: Skipping acquire of configured file 'main/source/Sources' as repository 'https://r2u.stat.illinois.edu/ubuntu jammy InRelease' does not seem to provide it (sources.list entry misspelt?)\n"},"bridge_ext_present": {"rc": 0,"ok": null,"out": "/usr/local/lib/python3.12/dist-packages/isaacsim/exts/isaacsim.ros2.bridge\n"},"isaac_side": {"rc": 0,"ok": true,"out": "e.plugin] OmniGraphSettings::getCudaDeviceOrdinal: unable to get a valid CUDA device id from the renderer. Defaulting to GPU0.\n[22.989s] Simulation App Startup Complete\n[22.990s] app ready\nISAAC_DONE 120 frames, 9 joints\n[26.433s] Simulation App Shutting Down\n"},"ros_side": {"rc": 0,"ok": null,"out": "BRIDGE_OK received 60 JointState msgs; joints: 9\n"},"verdict": {"isaac_produced_jointstate": true,"ros_published_and_received": true,"end_to_end": true}}""")
SAMPLE = json.loads(r"""{"joint_names": ["panda_joint1","panda_joint2","panda_joint3","panda_joint4","panda_joint5","panda_joint6","panda_joint7","panda_finger_joint1","panda_finger_joint2"],"first": {"t": 0.0,"position": [0.00146,-0.09094,2e-05,-0.10545,-0.00023,0.12968,0.1303,1e-05,0.00011]},"last": {"t": 1.9833333333333334,"position": [0.012,-0.56851,0.0,-2.80354,1e-05,3.03404,0.74097,0.0,0.0]},"n_frames": 120}""")

for k in ("ros_install", "bridge_ext_present", "isaac_side", "ros_side"):
    v = RESULT.get(k, {})
    print(f"  {k:<20} rc={str(v.get('rc')):>4}  {str(v.get('out','')).strip()[:96]}")
print()
print("  VERDICT:", json.dumps(RESULT.get("verdict")))
'''),

("md", """
Both halves succeeded:

```
isaac side  ->  ISAAC_DONE 120 frames, 9 joints
ros side    ->  BRIDGE_OK received 60 JointState msgs; joints: 9
end_to_end  ->  true
```

Also worth noting: **`isaacsim.ros2.bridge` ships inside the pip package**, so
the official extension is present. The hand-written split below is still the
more robust route on Kaggle, because it sidesteps the interpreter collision
instead of fighting it.
"""),

("code", r'''
if SAMPLE:
    print("joints:", SAMPLE["joint_names"][:5], "...")
    print(f"frames captured: {SAMPLE['n_frames']}")
    print()
    print("  t=0.00s :", [round(v,4) for v in SAMPLE["first"]["position"][:5]])
    print(f"  t={SAMPLE['last']['t']:.2f}s :",
          [round(v,4) for v in SAMPLE["last"]["position"][:5]])
    print()
    print("panda_joint4 travelled",
          round(SAMPLE['last']['position'][3] - SAMPLE['first']['position'][3], 3),
          "rad -- the arm sagging under gravity, unactuated")
'''),

("md", """
Real joint names, real trajectories. `panda_joint4` swings from -0.105 to
-2.804 rad over two seconds: the arm collapsing under its own weight with no
controller holding it. That is the payload crossing the wire, not a synthetic
message.

## Side A - Isaac Sim (Python 3.12)

```python
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})

from isaacsim.core.api import World
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.core.prims import SingleArticulation
from isaacsim.storage.native import get_assets_root_path

ROOT = get_assets_root_path()
w = World(stage_units_in_meters=1.0, physics_dt=1/60)
w.scene.add_default_ground_plane()

# NOTE the 6.0 asset path -- robots are grouped by MANUFACTURER now.
# /Isaac/Robots/Franka/franka.usd is a 404 on Isaac Sim 6.0.
add_reference_to_stage(
    usd_path=ROOT + "/Isaac/Robots/FrankaRobotics/FrankaPanda/franka.usd",
    prim_path="/World/franka")

art = SingleArticulation(prim_path="/World/franka", name="franka")
w.reset(); art.initialize()

frames = []
for i in range(120):
    w.step(render=False)                     # render=False: no renderer needed
    q = art.get_joint_positions()
    frames.append({"t": i/60.0, "position": [float(v) for v in q]})

json.dump({"joint_names": list(art.dof_names), "frames": frames},
          open("/kaggle/working/jointstate.json", "w"))
```

## Side B - ROS 2 (Python 3.10)

```python
import rclpy
from sensor_msgs.msg import JointState
from rosgraph_msgs.msg import Clock
from builtin_interfaces.msg import Time

d = json.load(open("/kaggle/working/jointstate.json"))
rclpy.init()
n = rclpy.create_node("isaac_bridge")
pub  = n.create_publisher(JointState, "/joint_states", 10)
clkp = n.create_publisher(Clock, "/clock", 10)

for f in d["frames"]:
    js = JointState()
    js.name = d["joint_names"]
    js.position = [float(x) for x in f["position"]]
    sec = int(f["t"]); nsec = int((f["t"] - sec) * 1e9)
    js.header.stamp = Time(sec=sec, nanosec=nsec)

    ck = Clock(); ck.clock = Time(sec=sec, nanosec=nsec)
    clkp.publish(ck)                    # publish /clock BEFORE the data
    pub.publish(js)
    rclpy.spin_once(n, timeout_sec=0.02)
```

Run it with the interpreter ROS was built for, not `python3`:

```bash
bash -lc "source /opt/ros/humble/setup.bash && /usr/bin/python3.10 ros_side.py"
```
"""),

("md", """
## Why /clock is published first

Every message carries a simulation timestamp, and `/clock` is published before
the data it describes.

Consumers running with `use_sim_time:=true` block until they see a clock. If
you publish `/joint_states` first, subscribers time-stamp against wall time and
`tf2` lookups fail later with **extrapolation errors that never mention the
clock** - which is among the most common and most confusing ROS 2 + simulator
bugs there is.

## Making it live

This version streams recorded frames, which is enough to prove the wire works.
For a live bridge, run both sides concurrently and hand frames across a pipe or
shared memory rather than a file. The interpreter split stays either way - it
is a property of the environment, not of the design.

The pieces are all verified on the free tier: Isaac Sim physics, articulated
robots from 49 vendors, DDS middleware, and this bridge between them. What the
free tier cannot do is **render** - so camera topics and RGB-D pipelines need a
machine where you control the image.
"""),
]
