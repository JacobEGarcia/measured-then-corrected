# Robot simulation: authoring, validation, and the traps in between

A working set of simulation-engineering artifacts — a robot authored from
scratch for three simulators, validated to machine precision, wrapped in CI
that asserts against closed-form physics rather than stored golden values.

Everything here was measured. Where a prediction of mine turned out wrong, the
wrong prediction is documented next to the correction, because those are the
parts worth reading.

---

## The robot

`model/robot_spec.py` holds the parameters. `model/emit.py` generates **MJCF,
URDF and SDF** from that single source, so the three formats cannot drift.

```bash
python model/emit.py        # regenerate all three
python model/validate.py    # 151 comparisons + 2000-config FK
pytest tests/               # 17 gates
```

**Validation runs at two levels, and only the second one works:**

| level | result |
|---|---|
| numbers agree | 151 cross-format comparisons, **0 mismatches** |
| robots agree | 2000 random configs, **max FK error 3.3e-16 m** |

The first validation run reported **147/147 numbers correct with 0.23 m of FK
error**. In URDF the link frame sits at the *joint*, so `<origin xyz="0 0 0"/>`
put every centre of mass on its own joint axis — correct masses, correct
inertias, attached to the wrong places.

> Comparing numbers proves the FILES agree.
> Comparing kinematics proves the ROBOTS agree.

---

## Contact mechanics — `model/contact_tuning.py`

Two measured results that contradict intuition:

**Penetration does not scale with load.** Identical to four decimals across a
1000x mass range, because MuJoCo's `solref` is parameterised in *time*
(timeconst, dampratio) rather than stiffness. I predicted the opposite.

**The contact timeconst is silently clamped to 2·dt.** Verified four ways:

| dt | requested tc | penetration | matches tc = |
|---|---|---|---|
| 0.001 | 0.0001 | 0.0011 mm | 0.002 = 2·dt |
| 0.002 | 0.0001 | 0.0044 mm | 0.004 = 2·dt |
| 0.005 | 0.0001 | 0.0273 mm | 0.010 = 2·dt |
| 0.010 | 0.0001 | 0.1078 mm | 0.020 = 2·dt |

Practical rule: **to halve penetration, halve your timestep.** Tuning `solref`
below 2·dt does nothing at all.

---

## Actuator models — `model/actuators.py`

All four checks exact to 0.00% against closed form.

**The term people forget:** a gearbox multiplies rotor inertia by **N²**.

```
N=1    reflected 0.00002 kg·m²  vs link 0.0871  ->  qacc 28.16
N=100  reflected 0.20000 kg·m²  vs link 0.0871  ->  qacc  8.54
```

At 100:1 a 2e-5 kg·m² rotor contributes **2.3x more inertia than the entire
link**. Omit it and your arm accelerates 3.3x too fast — a sim-to-real gap no
amount of friction tuning will close.

**A gotcha:** MuJoCo's `forcerange` clips the *actuator* force, which `gear`
then multiplies. A 50:1 gear with `forcerange="2"` delivers up to **100 Nm** at
the joint, not 2.

---

## System identification — `model/sysid.py`

Recover damping and joint friction from noisy encoder data, then predict a
trajectory the optimiser never saw.

```
identifiable parameters:   19.3% mean error
held-out prediction:       1.53 -> 0.0083 rad RMS   (185x better than nominal)
```

**Run a sensitivity analysis before fitting anything:**

```
damping_j1     0.000e+00    NOT identifiable
damping_j2     4.207e+00    identifiable
damping_j3     2.166e+00    identifiable
frictionloss   2.791e+00    identifiable
```

`j_link1`'s axis is parallel to gravity and there is no actuation, so it never
rotates — **10x its damping changes the observed trajectory by exactly
0.00e+00 rad.** No optimiser can recover a parameter that leaves no trace.

Two hypotheses of mine died on the way:

1. *"More excitation will fix it"* — five trajectories instead of one moved the
   error 168.8% -> 168.3%. No effect.
2. *"The parameters are unidentifiable"* — evaluating the objective at the
   known-true values showed they fit **35x better** than the optimiser's
   answer, with a ridge between. A trapped optimiser, not an unidentifiable
   system. Multi-start halved the error.

Also worth knowing: the first fit predicted held-out motion **20x better than
nominal** with parameters that were 200-400% wrong. **Good prediction is not
evidence of correct physics.**

---

## CI — `tests/`, `.github/workflows/simulation-ci.yml`

38 gates, ~90 s.

**Gates assert closed-form physics, not golden files.** Golden values rot the
moment someone regenerates them; `v²/(2μg)` cannot be regenerated.

**Four tests verify the gates actually bite** — a suite that passes on a broken
model converts "unknown" into "verified". The sharpest replaces Coulomb
friction with linear velocity drag and confirms the mass-independence gate
rejects it, proving that test can distinguish real friction from something that
merely looks like it.

**CI regenerates the model from spec** and fails if the output differs from
what is committed, enforcing single-source-of-truth mechanically.

---

## C++ harness — `cpp/`

```bash
PYTHON=/path/to/venv/bin/python bash cpp/build.sh
./cpp/sim_bench model/arm3.xml 20000
```

```
throughput : 142,241 steps/s   (284x realtime)
  collision  : 0.0019 ms  (26.9%)
  make cnstr : 0.0015 ms  (21.0%)
  solve      : 0.0007 ms  (10.0%)
```

For this model **collision detection costs ~3x the constraint solver** — so
tuning solver iterations would be wasted effort.

**MuJoCo's profiling is opt-in.** Without installing `mjcb_time` the entire
timer array reads zero, which looks exactly like "every phase is free".

---

## Closed kinematic chains — `model/closed_chain.py`

**URDF cannot express a loop.** Every link has exactly one parent, so four-bar
linkages, parallel jaws, delta arms and differential drives are outside the
format's data model. MJCF closes a loop with `<equality><connect>`; SDF with a
second `<joint>` back to an existing link.

What the missing closure costs, on a four-bar:

```
                open chain      closed loop
crank travel    1.7659 rad      1.2334 rad
rocker travel   0.0000 rad      0.7191 rad
```

**The rocker never moves at all.** Export a four-bar to URDF, drop the closure,
and half the mechanism is inert — but it still simulates, and still looks
plausible in a viewer.

**A loop closure is a soft constraint, not a hard one.** The default leaves
11.5 mm of mean gap between the pivots; `solref`/`solimp` tighten it 109x.

**Wrong diagnosis, then the correction.** A 57 mm *maximum* gap looked like the
constraint was too soft, but stiffening moved the mean 109x and the max barely
at all. The max is at **step 0**: `qpos` was set to a configuration where the
loop is already broken by 60.7 mm, and the solver spends ~200 steps hauling it
shut. Settled gap is 0.036 mm. Loop-closed models must be initialised **on the
constraint manifold** — a tree model accepts any joint vector, a loop-closed
one does not.

---

## Collision cost — `model/collision_cost.py`

Raw throughput says meshes are catastrophic:

```
primitive sphere      21,793 steps/s
mesh (282 hull v)      1,842 steps/s     11.8x slower
```

**That number is measuring the wrong thing.** The scenes do not generate the
same number of contacts — a sphere pair yields 1, a box pair up to 4. Per
contact:

```
                    hull v   us/step   contacts   us/CONTACT
primitive sphere         0     45.89       40.0       1.1473
primitive box            0    126.25      160.0       0.7891
mesh                    12    120.86      109.5       1.1037
mesh                   282    542.89      103.9       5.2251
```

**Per contact the box is *cheaper* than the sphere** — it only looked slow
because it makes 4x the contacts. The clean comparison is mesh-vs-mesh at
near-equal contact counts: **23.5x the hull vertices costs 4.73x**, i.e.
roughly `sqrt(n)`, consistent with hull-based GJK/MPR.

A gate guards the confound itself, so the "raw steps/s is the wrong metric"
argument fails loudly if its own example ever inverts.

---

## Determinism and the chaos horizon — `model/determinism.py`

Three questions that get conflated in every "my run isn't reproducible" report:

```
repeated runs, same model      bit-identical
re-parsed model, same XML      bit-identical
untouched box added 3 m away   changes nothing
```

So reproducibility failures here are not solver nondeterminism. What *does*
bound them is chaos:

```
double pendulum (smooth)    lambda = 2.24 /s    e-folding 0.44 s
box on a 20 deg incline     lambda = 0.35 /s    e-folding 2.9 s
```

**Contact chaos is 6.5x slower than smooth chaos** — friction and inelastic
contact dissipate.

Validated three ways: two perturbation sizes (1 ULP and 1e-12) recover the same
exponent to **1.2%**, and the exponent fitted on one run blind-predicts the
other's 1 mm crossing at 9.18 s against **9.72 s measured**.

**Two floating-point traps, both now gated:**

- a 1-ULP-at-1.0 nudge (`2.22e-16`) added to a coordinate of `2.0`, whose ULP
  is `4.44e-16`, **rounds away entirely**. The two runs were bit-identical and
  the result read as "no chaos".
- `nextafter(0.0, 1.0)` is the smallest **denormal** (`4.94e-324`), not a
  usable ULP. It produced a meaningless `2e305x` growth figure.

**And a bad experiment design.** The first scene was a settling pile of boxes —
dissipative, contractive, and therefore incapable of exhibiting a chaos horizon
at all. Growth factor came out exactly `1.000`.

---

## Stability frontier — `model/stability_frontier.py`

The first sweep found **no instability anywhere** — an equal-mass tower is not a
hard contact problem, so there was no frontier. Rebuilt around **mass ratio**,
which dominates timestep as a failure axis:

```
ratio 1      survives dt = 0.032
ratio 10000  fails    at dt = 0.001
```

**Solver iterations buy nothing.** 1 vs 50 gives identical squash to 1e-3 mm.
The squash is the soft-contact model behaving as specified, not a convergence
failure — so the standard "raise iterations for stiff contacts" advice does not
apply here.

The first sweep did independently reproduce the **2·dt clamp**: penetration was
identical (1.637 mm) for dt from 0.0005 to 0.008, then jumped at 0.016 —
exactly where `2*dt` passes `solref`'s 0.02 s default.

### Reconciling a contradiction

`contact_tuning.py` measured penetration as mass-**independent**; this sweep saw
it scale **237x**. Same total load, delivered two ways:

```
load     one box on the floor     the same load on a 1 kg box
2 kg               0.1078 mm                        0.2072 mm
1000 kg            0.1078 mm                       49.1324 mm
```

**Both were right.** Mass normalisation cancels only when the load equals the
contact's own effective mass. A stack breaks that assumption, and the residual
error *is* the mass ratio. This is why a heavy body on a light one is the
classic solver killer.

---

## Layout

```
model/      robot spec, three generators, validation, sysid, contact,
            actuators, closed chains, collision cost, determinism, stability
tests/      38 CI gates, four of which test the gates themselves
cpp/        C++ profiling harness + build script
.github/    CI workflow
```
