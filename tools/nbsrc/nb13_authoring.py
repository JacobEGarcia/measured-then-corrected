TITLE = 'Authoring a Robot for Three Simulators'
SLUG = 'authoring-a-robot-for-three-simulators'
SUBTITLE = ("MJCF, URDF and SDF generated from a single parameter block - and "
            "the frame bug that 147 passing numeric checks did not catch.")
TAGS = ['robotics', 'physics']

CELLS = [
("md", """
## The problem with authoring a robot three times

A robot that must run in MuJoCo, Isaac Sim and Gazebo needs MJCF, URDF and SDF.
Hand-writing all three is how they drift: someone corrects an inertia in the
MJCF, the URDF keeps the old value, and two simulators quietly disagree forever.

So this generates all three from **one parameter block**. Drift becomes
impossible by construction, and CI fails if a committed file differs from what
the generator produces.

The robot is a 3-DOF arm: analytic inertia tensors from box geometry, joint
limits, per-joint damping, Coulomb joint friction, contact friction.
"""),

("code", r'''
import json, os
V = json.loads(r"""{"cross_validation": {"comparisons": 151,"mismatches": [],"worst_field": "base.mass mjcf-spec","worst_abs_diff": 4.440892098500626e-16},"forward_kinematics": {"samples": 2000,"max_abs_err_m": 3.3306690738754696e-16,"mean_abs_err_m": 6.57755100386126e-17},"conventions_checked": ["MJCF size is a HALF extent; URDF/SDF box size is the FULL extent","inertia stated explicitly in all three, never compiler-inferred","URDF joint origin offset by -half_length to sit at the child's lower face"]}""")
C = json.loads(r"""{"mujoco_final_q": [0.5,-1.746708,-1.40076],"isaac_final_q": [0.5,-1.745,1.145936],"isaac_masses": [{"prim": "base","mass": 2.3328,"diag_inertia": [0.0034992,0.0034992,0.00559872],"principal_axes_wxyz": [1.0,0.0,0.0,0.0],"axes_is_identity": true},{"prim": "link1","mass": 2.7216,"diag_inertia": [0.00163296,0.0185976,0.0185976],"principal_axes_wxyz": [0.5,0.5,0.5,0.5],"axes_is_identity": false},{"prim": "link2","mass": 1.62,"diag_inertia": [0.000675,0.0081135,0.0081135],"principal_axes_wxyz": [0.5,0.5,0.5,0.5],"axes_is_identity": false},{"prim": "link3","mass": 0.7776,"diag_inertia": [0.00020736,0.0022032,0.0022032],"principal_axes_wxyz": [0.5,0.5,0.5,0.5],"axes_is_identity": false}],"spec_masses": {"base": 2.3328,"link1": 2.7216,"link2": 1.62,"link3": 0.7776}}""")

cv = V["cross_validation"]; fk = V["forward_kinematics"]
print(f"cross-validation : {cv['comparisons']} comparisons, "
      f"{len(cv['mismatches'])} mismatches")
print(f"  worst field    : {cv['worst_field']}  diff {cv['worst_abs_diff']:.3e}")
print()
print(f"forward kinematics: {fk['samples']} random configurations")
print(f"  max  abs error : {fk['max_abs_err_m']:.3e} m")
print(f"  mean abs error : {fk['mean_abs_err_m']:.3e} m")
print()
for c in V["conventions_checked"]: print(" *", c)
'''),

("md", """
## Two levels of validation, and only one of them works

**Level 1 — the numbers agree.** 151 comparisons across all three formats:
mass, inertia, joint axis, limits, damping, joint friction, geometry. Including
the conversion that causes most cross-format bugs:

> **MJCF `size` is a HALF extent. URDF and SDF `<box size>` is the FULL
> extent.**

**Level 2 — the robots agree.** An independent forward-kinematic chain written
in plain numpy from the URDF joint origins, compared against MuJoCo's own FK
over 2000 random configurations.

Level 2 is the one that matters, and here is why.

## The bug that passed every numeric check

The first validation run reported **147 of 147 numbers correct** and a forward
kinematics error of **0.23 m**.

In URDF the link frame sits at the **joint**, not at the body's centre. My
inertial and geometry origins were `xyz="0 0 0"`, which placed every centre of
mass directly **on its own joint axis**. Correct masses. Correct inertia
tensors. Attached to the wrong places.

```xml
<!-- wrong: centre of mass lands on the joint -->
<inertial><origin xyz="0 0 0"/>            ...</inertial>

<!-- right: body centre sits half a link above the joint -->
<inertial><origin xyz="0 0 0.14"/>         ...</inertial>
```

No amount of XML diffing finds that. Both files are internally consistent and
describe different robots.

> Comparing numbers proves the FILES agree.
> Comparing kinematics proves the ROBOTS agree.

A model with correct kinematics and wrong inertia loads, simulates, looks
entirely plausible, and quietly ruins sim-to-real transfer.
"""),

("md", """
## Importing the same file into Isaac Sim

The authored URDF, loaded into Isaac Sim 6.0 and compared against MuJoCo.
"""),

("code", r'''
print("masses, authored vs imported:")
spec = C["spec_masses"]
for m in (C["isaac_masses"] or []):
    want = spec.get(m["prim"])
    if want is None: continue
    print(f"  {m['prim']:<7} authored {want:<9} imported {m['mass']:<9} "
          f"match={abs(m['mass']-want) < 1e-6}")
print()
print("resting pose after a 3 s drop from q0 = [0.5, -0.8, 1.2]:")
print("  MuJoCo :", C["mujoco_final_q"])
print("  Isaac  :", C["isaac_final_q"])
'''),

("md", """
Masses match to seven digits. Joint damping imported as authored
(0.120 / 0.100 / 0.080). Drive stiffness is **0.0**, so the importer added no
actuators. `j_link1` agrees exactly, and `j_link2` settles onto its -1.745 rad
limit in **both** engines.

## The inertia scare that was not a bug

Isaac's `diagonalInertia` came back **permuted** — the smallest component in
the first slot instead of the third. For links that are long in Z, that would
mean Isaac believes they are long in X: rotational inertia about the bending
axis roughly 11x too large.

It is not a bug. The `principalAxes` quaternion is `(0.5, 0.5, 0.5, 0.5)` — a
120 degree rotation about (1,1,1), which cyclically permutes the axes. The
permuted diagonal expressed in *that* frame is the same tensor.

```
authored (identity frame) : [0.0185976, 0.0185976, 0.00163296]
Isaac    (rotated frame)  : [0.00163296, 0.0185976, 0.0185976]
principalAxes             : (0.5, 0.5, 0.5, 0.5)  -> 120 deg about (1,1,1)
```

**USD stores diagonal inertia in a principal-axis frame.** Reading the diagonal
without the quaternion produces a confident, wrong conclusion — in this case a
false defect report against NVIDIA's importer.

## What is still open

MuJoCo and Isaac agree on `j_link1` and on `j_link2`'s resting limit, but
diverge on `j_link3` (-1.401 vs +1.146 rad), and Isaac's arm falls more slowly
through the transient.

Every model property has been verified identical on both sides — mass, inertia,
damping, drive stiffness, limits, DOF count — and stale-USD caching was ruled
out with a unique output path. **The cause is not identified.**

It is recorded as an open question rather than attributed to a guess. If you
know what causes it, the comments are open.
"""),
]
