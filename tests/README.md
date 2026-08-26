# Simulation CI

Physics regression gates that run on every commit. The failure they catch is
silent: a model that loads fine, simulates fine, and has wrong dynamics.

    pytest tests/          # 17 gates, ~0.6 s

## Two design choices

**Gates assert against closed-form physics, not golden files.** Golden values
rot — someone regenerates the file and the test passes forever regardless of
correctness. `d = v^2/(2*mu*g)` and `g = 9.81` cannot be regenerated.

**Four tests verify the gates actually bite.** A suite that passes on a broken
model is worse than no suite, because it converts "unknown" into "verified".
`test_ci_gates_bite.py` feeds each gate deliberately broken input and asserts
rejection.

The sharpest of those: it replaces Coulomb friction with **linear velocity
drag** and confirms the mass-independence gate rejects it. Drag decelerates
light objects faster, so stopping distance becomes mass-dependent — proving the
friction test can tell real Coulomb friction from something that merely looks
like it.

## The gates

| test | asserts |
|---|---|
| `test_formats_agree` | 151 cross-format comparisons, zero mismatches |
| `test_forward_kinematics` | FK error < 1e-12 m over 2000 configs |
| `test_inertia_is_physical` | triangle inequality on every tensor |
| `test_gravity_recovered_from_freefall` | fitted `-2a` equals 9.81 |
| `test_rest_height_equals_half_extent` | settled box centre at exactly 0.05 m |
| `test_coulomb_stopping_distance` | `v^2/(2*mu*g)` within 2-3% at three frictions |
| `test_coulomb_is_mass_independent` | 5x the mass changes distance < 5% |
| `test_rk4_beats_euler_on_energy_drift` | integrator regression |
| `test_simulation_is_deterministic` | same input, identical output |

## CI

`.github/workflows/simulation-ci.yml` runs on push, PR and weekly.

It **regenerates the model from `robot_spec.py`** rather than testing the
committed artifacts, then fails if the output differs from what is checked in:

    ::error:: Generated model differs from the committed files.
    Someone edited a format by hand instead of editing robot_spec.py.

That enforces the single-source-of-truth invariant mechanically instead of by
convention. The matrix tests a pinned MuJoCo and `latest`, so upstream drift
surfaces in CI rather than in someone's training run.
