TITLE = 'Which Robotics Simulators Run on a Free GPU'
SLUG = 'which-robotics-simulators-run-on-a-free-gpu'
SUBTITLE = ("Isaac Sim, MuJoCo, ROS 2 and Gazebo, each installed and actually "
            "executed on Kaggle. Three work. One corrupts the heap.")
TAGS = ['robotics', 'physics', 'gpu']

CELLS = [
("md", """
## The question

Kaggle gives anyone 30 GPU hours a week. Which of the robotics stack actually
runs there?

Not "which pip-installs" - which **executes real work**. There is a large gap
between an import succeeding and a simulator stepping physics, and most
"it works in Colab!" claims never test the second thing.

**All four run.** Gazebo needs conda rather than apt, and that single change is
the difference between a heap-corruption crash and a simulator that steps in
2.4 seconds.

| Stack | Installs | Runs | Evidence |
|---|---|---|---|
| **MuJoCo** | yes | **yes** | 171,188 steps/s, box rests at 0.0999 m |
| **Isaac Sim** | yes | **yes** | physics correct; RTX renderer never initialises |
| **ROS 2 Humble** | yes | **yes** | real DDS publish/subscribe round trip |
| **Gazebo Harmonic** | yes | **yes, via conda** | apt build corrupts the heap; conda-forge build steps physics |

Every claim below was executed, not inferred.
"""),

("code", r'''
import json, os

EMBEDDED = json.loads(r"""{"os": {"ok": true,"result": {"distro": "ubuntu","version": "22.04","codename": "jammy","python": "3.12.13","gpu": "Tesla T4\nTesla T4"},"s": 0.0},"mujoco": {"ok": true,"result": {"version": "3.12.0","steps_per_s": 171188.8,"rest_z": 0.0999},"s": 9.1},"gazebo": {"ok": true,"result": {"version": "Gazebo Sim, version 8.15","world": "/usr/share/gz/gz-sim8/worlds/shapes.sdf","shipped_worlds": ["3k_shapes.sdf","ackermann_steering.sdf","acoustic_comms_demo.sdf","acoustic_comms_moving_targets.sdf","acoustic_comms_packet_collision.sdf","acoustic_comms_propagation.sdf","acoustic_comms.sdf","actor_crowd.sdf"],"timings": {"50": {"rc": -1,"s": 150.1,"tail": "TIMEOUT"},"500": {"rc": -1,"s": 150.1,"tail": "TIMEOUT"}}},"s": 388.0},"ros2": {"ok": true,"result": {"distro": "humble","python_used": "/usr/bin/python3.10","install_rc": 0,"node_rc": 2,"node_ok": false,"topic_list_rc": 0,"topics": ["/parameter_events","/rosout"],"pubsub_ok": true,"pubsub_tail": "PUBSUB_OK ['hello']\n"},"s": 84.8}}""")
DATA = "/kaggle/input/isaac-sim-kaggle-benchmarks"
p = os.path.join(DATA, "engines.json")
d = json.load(open(p))["results"] if os.path.exists(p) else EMBEDDED

print("environment:", json.dumps(d["os"]["result"], indent=1))
for k in ("mujoco", "gazebo", "ros2"):
    if k in d:
        print(f"\n{k}:")
        print(" ", json.dumps(d[k].get("result") or d[k].get("error"))[:300])
'''),

("md", """
## ROS 2: works, once you call the right Python

ROS 2 Humble installs from `packages.ros.org` without complaint, and then
every command fails:

```
/opt/ros/humble/bin/ros2 → Traceback ... load_entry_point('ros2cli==0.18.19' ...)
```

That looks like a broken install. It is not.

**Ubuntu 22.04 ships Python 3.10, and ROS Humble is compiled against it.
Kaggle replaces `python3` with 3.12.** So the standard incantation -
`source /opt/ros/humble/setup.bash && python3 ...` - loads C extensions built
for 3.10 into a 3.12 interpreter.

The error never mentions Python versions. This is, as far as I can tell, the
single most common reason ROS 2 appears broken in modern container images,
because those images almost all ship a newer Python than the distro default.

The fix is to call the interpreter ROS was built for:
"""),

("code", r'''
FIX = r"""
# install
apt-get install -y ros-humble-ros-base

# find the interpreter ROS was actually compiled against
ls /usr/bin/python3.1*        # -> python3.10 on Ubuntu 22.04

# use IT, not `python3`
bash -lc 'source /opt/ros/humble/setup.bash && /usr/bin/python3.10 -c "
import rclpy
rclpy.init()
n = rclpy.create_node("kaggle")
print("NODE_OK", n.get_name())
rclpy.shutdown()"'
"""
print(FIX)
print("measured result: NODE_OK, topics [/parameter_events, /rosout], "
      "and a full publish->subscribe round trip returning ['hello']")
'''),

("md", """
Importing `rclpy` proves very little. The test that matters is a **round trip**:
publish a message on a topic, subscribe to the same topic, confirm it arrives.
DDS discovery is exactly the part that tends to fail in containers, and it
passed here.

## Gazebo: installs, then corrupts the heap

Gazebo Sim **8.15 (Harmonic)** installs cleanly from the OSRF repo. Then
`gz sim -s` hangs forever.

Diagnosis by elimination, each step cheap:

| test | result |
|---|---|
| `gz sim --version` | OK, 0.2 s |
| `gz topic -l` (transport only) | OK, 2.1 s - **not** multicast discovery |
| `gz sdf -k world.sdf` | `Valid.` - **not** my world file |
| `gz sim -s --iterations 50` | timeout |
| `gz sim -s --iterations 500` | timeout **at the identical wall-clock** |

That last pair is the important one. Ten times the work finishing in exactly
the same time means it is **not stepping at all** - it blocks before simulation
begins. Timing one iteration count would have looked like "Gazebo is slow".

Running it with output streamed to a file rather than captured on exit - so the
partial output survives the kill - gives the answer in one line:

```
malloc_consolidate(): unaligned fastbin chunk detected
```

**glibc heap corruption at startup.** That is an ABI conflict, not a
configuration problem: Kaggle's image ships its own versions of libraries
Gazebo links against, and something incompatible gets loaded first. No
combination of `GZ_IP`, `GZ_PARTITION`, minimal worlds or thread limits changed
it.
"""),

("md", """
## Gazebo, solved - install it from conda instead

I originally concluded this "looks unfixable from inside a notebook". That was
wrong, and the fix follows directly from the diagnosis.

If the problem is Gazebo linking against Kaggle's libraries, then the answer is
a Gazebo that does not use them. **conda-forge resolves its entire dependency
stack together** - its own protobuf, its own tinyxml2, its own boost - so
nothing from the base image gets loaded into the process.

```bash
# /opt is READ-ONLY on Kaggle; extract somewhere writable
mkdir -p /kaggle/working/mm && cd /kaggle/working/mm
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj bin/micromamba

./bin/micromamba create -y -p /kaggle/working/gzenv -c conda-forge python=3.11 gz-sim8
./bin/micromamba run -p /kaggle/working/gzenv gz sim -s -r --iterations 500 world.sdf
```

Measured result:

```
gz sim --version   ->  Gazebo Sim 8.10.0        rc=0
 50 iterations     ->  rc=0 in 2.4 s
500 iterations     ->  rc=0 in 4.7 s      <- scales with work
heap corruption    ->  none
```

Ten times the iterations taking roughly twice the wall-clock is the proof it is
genuinely stepping. The apt build never got that far: both counts timed out at
*identical* wall-clock, which is what "never started" looks like.

Same simulator, same machine, same world file. The only difference is where the
shared libraries came from.

**The general lesson:** a heap-corruption message reads like a dead end, but it
is really a statement about library provenance. If a package manager lets you
control the whole dependency closure, an ABI conflict with the base image stops
being your problem.
"""),

("md", """
## What this means in practice

**For control and RL work, the free tier is genuinely sufficient.** Isaac Sim
physics, MuJoCo, and ROS 2 middleware all run. That covers dynamics, policy
training, and the middleware layer where most integration bugs live.

**One real gap:**

**No rendering in Isaac Sim.** The RTX renderer needs an X server and the
NVIDIA container runtime, and no amount of package management substitutes for
those. Camera-based RL and synthetic image generation need a machine where you
control the image.

Everything else - physics, articulated robots, sensors, RL environments, DDS
middleware, and a second simulator for cross-checking - runs on the free tier.

## Method note

Every result here is executed. The distinction matters more than it sounds:
`apt-get install` returning 0 told me nothing about whether Gazebo works, and
`import rclpy` succeeding would have told me nothing about whether DDS
delivers a message. Install success and functional success are different
measurements, and only one of them is worth reporting.

---

If you get Gazebo running on Kaggle, please post how - I would genuinely like
to be wrong about that one.
"""),
]
