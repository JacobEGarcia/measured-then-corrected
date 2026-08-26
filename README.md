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

17 gates, ~0.6 s.

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

## Layout

```
model/      robot spec, three generators, validation, sysid, contact + actuator studies
tests/      17 CI gates, four of which test the gates themselves
cpp/        C++ profiling harness + build script
.github/    CI workflow
```
