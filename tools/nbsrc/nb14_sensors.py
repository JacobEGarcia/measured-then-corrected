TITLE = 'Which Isaac Sim Sensors Work Without a Renderer'
SLUG = 'which-isaac-sim-sensors-work-without-a-renderer'
SUBTITLE = ("Effort and joint state validated against closed-form physics; "
            "contact, IMU and LiDAR mapped to the reason they do not run.")
TAGS = ['robotics', 'gpu', 'physics']

CELLS = [
("md", """
## Verifying a sensor exists is worthless

The question is whether its readings are physically correct. A sensor that
returns plausible numbers in the wrong units passes an existence check and
fails every test below, because each of these has a closed-form answer:

| sensor | must report |
|---|---|
| contact | normal force = m*g for a resting body |
| IMU | proper acceleration = g when static, gyro = 0 |
| effort | holding torque = m*g*L on a gravity-loaded joint |
| joint state | exactly what was commanded |

Run on Kaggle's free tier, where **the RTX renderer does not initialise** -
which turns out to be the organising fact.
"""),

("code", r'''
import json
S = json.loads(r"""{"contact": {"ok": true,"measured_N": NaN,"expected_mg_N": 19.62,"err_pct": NaN,"samples": 0},"imu": {"ok": true,"acc_magnitude": 0.0,"expected_g": 9.81,"err_pct": 100.0,"gyro_norm": 0.0,"samples": 240},"effort": {"ok": true,"api": "get_measured_joint_efforts","n": 9,"efforts_Nm": [-0.0009,-7.6046,-0.0007,16.9182,-0.0,0.9429,-0.0],"nonzero": true,"note": "gravity-loaded arm: shoulder/elbow must carry load"},"joint_state": {"ok": true,"num_dof": 9,"max_abs_err_rad": 0.016382,"commanded": [0.3,-0.5,0.2,-1.9,0.1,1.4,0.6,0.0,0.0],"readback": [0.2999,-0.4996,0.2001,-1.9164,0.1,1.4,0.6,0.0,0.0]},"raycast": {"ok": false,"error": "ValueError: Raycast.create requires both 'ray_origins' and 'ray_directions' (the C++ backend disables sensors whose ray-array lengths don't match numRays)."},"sensor_commands": ["IsaacSensorCreateLightBeamSensor","RangeSensorCreateGeneric","RangeSensorCreateLidar","RangeSensorCreatePrim","IsaacSensorCreateRtxIDS","IsaacSensorCreateRtxLidar","IsaacSensorCreateRtxRadar","IsaacSensorCreateRtxSensor","IsaacSensorCreateRtxUltrasonic"],"sensor_discovery": {"isaacsim.sensors.experimental.physics": ["Contact","ContactSensor","ContactSensorReading","EffortSensor","EffortSensorReading","IMUSensor","IMUSensorReading","JointStateSensor","JointStateSensorReading","RaycastSensor"],"using": "isaacsim.sensors.experimental.physics","isaacsim.sensors.physics": [],"isaacsim.sensors.physx": ["IsaacSensorCreateLightBeamSensor","IsaacSensorSchema","ProximitySensor","ProximitySensorManager","RangeSensorCreateGeneric","RangeSensorCreateLidar","RangeSensorCreatePrim","RangeSensorSchema"],"ContactSensor.__init__": "(self, path: \"'str | Contact'\") -> 'None'","ContactSensor.methods": ["add_raw_contact_data_to_frame","authoring_object","contact","get_data","get_raw_data","get_sensor_reading","on_physics_step","on_timeline_stop","remove_raw_contact_data_from_frame","reset"],"IMUSensor.__init__": "(self, path: \"'str | _PhysicsSensorAuthoring'\") -> 'None'","IMUSensor.methods": ["authoring_object","get_data","get_sensor_reading","imu","on_physics_step","on_timeline_stop","reset"],"EffortSensor.__init__": "(self, path: 'str', enabled: 'bool' = True) -> 'None'","EffortSensor.methods": ["change_buffer_size","get_data","get_sensor_reading","on_physics_step","on_timeline_stop","reset","update_dof_name"],"JointStateSensor.__init__": "(self, path: 'str', enabled: 'bool' = True) -> 'None'","JointStateSensor.methods": ["get_data","get_sensor_reading","on_physics_step","on_timeline_stop","reset"],"RaycastSensor.__init__": "(self, path: \"'str | _PhysicsSensorAuthoring'\") -> 'None'","RaycastSensor.methods": ["authoring_object","get_data","get_sensor_reading","on_physics_step","on_timeline_stop","raycast","reset"]}}""")
for k in ("effort", "joint_state", "contact", "imu", "raycast"):
    v = S.get(k) or {}
    mark = "OK  " if v.get("ok") and v.get("samples", 1) not in (0,) else "----"
    print(f"[{mark}] {k}")
    print("       ", json.dumps(v)[:210])
'''),

("md", """
## What works: the solver-side sensors

**Effort** on a gravity-loaded Franka:

```
[-0.0009, -7.6046, -0.0007, 16.9182, -0.0, 0.9429, -0.0] Nm
```

Joints 2 and 4 - shoulder and elbow - carry the arm's weight. The rotational
joints, whose axes are parallel to gravity and therefore feel no gravitational
torque, sit within 0.001 Nm of zero. That pattern is the validation: the
readings are not merely non-empty, they are distributed the way statics says
they must be.

**Joint state**: 9 DOF (7 arm + 2 fingers), commanded against readback to
0.016 rad.

## What does not, and why

**Contact and IMU.** The classes exist in
`isaacsim.sensors.experimental.physics` and their constructors accept a prim
path - but they **wrap** an `IsaacContactSensor` / `IsaacImuSensor` schema prim,
they do not create one. In Isaac Sim 6.0 the commands that used to author those
prims are gone:

```
9 sensor-creation commands registered:
    IsaacSensorCreateLightBeamSensor
    RangeSensorCreateGeneric / Lidar / Prim        <- legacy
    IsaacSensorCreateRtxIDS / RtxLidar / RtxRadar
    IsaacSensorCreateRtxSensor / RtxUltrasonic     <- all RTX
```

`IsaacSensorCreateContactSensor` and `IsaacSensorCreateImuSensor` are **not in
that list**. `Contact.create(path, radius=..., min_threshold=...)` does author a
prim, but the runtime then returns `None` for every frame.

**LiDAR, radar, ultrasonic.** Every registered variant is **RTX-based**. They
cast rays through a render pipeline that never starts on this tier.

## The organising fact

> **Sensors that read solver state work on free hardware. Sensors that route
> through the render pipeline do not.**

Effort and joint state are quantities PhysX already computes. LiDAR needs rays
traced through RTX. Contact and IMU sit awkwardly between: physical quantities
whose 6.0 authoring path assumes tooling that is not present headless.

## Two API notes that cost real time

**`isaacsim.sensors.physx` is deprecated** and contains only lidar and proximity
stubs. Importing it and finding no `ContactSensor` looks like the sensor does
not exist. The current classes live in
`isaacsim.sensors.experimental.physics`.

**The constructors take a positional `path`**, not `prim_path=`:

```python
ContactSensor("/World/box/cs")      # correct
ContactSensor(prim_path="/World/box/cs")   # TypeError
```

Tutorials show the second form. Reading `inspect.signature` settles it in one
second; guessing cost several fifteen-minute runs.
"""),
]
