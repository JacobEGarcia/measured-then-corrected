# Authoring and validating a robot across three simulators

A 3-DOF arm designed from scratch, emitted to MJCF, URDF and SDF from one
parameter source, and validated at two levels.

## Why one source

Hand-authoring the same robot three times is how formats drift: someone fixes
an inertia in the MJCF, the URDF keeps the old one, and two simulators quietly
disagree forever. `robot_spec.py` holds the parameters; `emit.py` generates all
three files. Drift is impossible by construction, and CI fails if a generated
file differs from what is committed.

## Level 1 — the numbers agree

    151 comparisons, 0 mismatches
    worst field: base.mass mjcf-spec, diff 4.4e-16

Mass, inertia, joint axis, limits, damping, joint friction and geometry, each
checked across all three formats against the spec. Including the conversion
that causes most cross-format bugs: **MJCF `size` is a HALF extent; URDF and
SDF `<box size>` is the FULL extent.**

## Level 2 — the robots agree

    2000 random configurations
    max  abs FK error: 3.331e-16 m
    mean abs FK error: 6.578e-17 m

An independent forward kinematic chain in plain numpy, built from the URDF
joint origins, compared against MuJoCo's own FK.

**This is the check that matters, and it caught a bug the 151 numeric
comparisons all passed.** The first run reported 147/147 numbers correct and an
FK error of 0.23 m. In URDF the link frame sits at the JOINT, not at the body
centre, so `<origin xyz="0 0 0"/>` put every centre of mass on its own joint
axis. Correct masses, correct inertias, attached to the wrong places.

> Comparing numbers proves the FILES agree.
> Comparing kinematics proves the ROBOTS agree.

A model with correct kinematics and wrong inertia loads, simulates, looks
plausible, and quietly ruins sim-to-real transfer. That is what level 2 exists
to catch.

## Cross-engine import

The same authored URDF imported into Isaac Sim 6.0:

| property | result |
|---|---|
| DOF / joint names | 3, `j_link1..3` — as authored |
| mass | exact to 7 digits |
| inertia | equivalent (see below) |
| joint damping | 0.120 / 0.100 / 0.080 — as authored |
| drive stiffness | 0.0 — no actuators added |
| joint limits | enforced; j_link2 settles on its -1.745 limit in BOTH engines |

### The inertia scare

Isaac's `diagonalInertia` came back **permuted** — the smallest component in
the first slot instead of the third. That looks like a serious importer bug: it
would mean Isaac thinks each link is long along X when it is long along Z.

It is not a bug. `principalAxes` is `(0.5, 0.5, 0.5, 0.5)` — a 120 degree
rotation about (1,1,1), which cyclically permutes the axes. The permuted
diagonal expressed in *that* frame is the same tensor as mine in the identity
frame.

Reading one more attribute was the difference between a finding and a false
defect report against NVIDIA.

### What is still unexplained

MuJoCo and Isaac agree on j_link1 exactly and on j_link2's resting limit, but
diverge on j_link3 (MuJoCo -1.401 rad, Isaac +1.146 rad). Isaac's arm falls
markedly more slowly through the transient.

Every model property has been verified identical on both sides: mass, inertia,
damping, drive stiffness, limits, DOF count. Stale-USD caching was ruled out
with a unique output path. **The cause is not identified.** It is recorded here
as an open question rather than attributed to a guess.

## Reproducing

    python model/emit.py       # regenerate all three formats
    python model/validate.py   # 151 comparisons + 2000-config FK
    pytest tests/              # 17 gates, see ../tests/
