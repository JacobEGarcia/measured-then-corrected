TITLE = 'CI That Actually Catches Broken Physics'
SLUG = 'ci-that-actually-catches-broken-physics'
SUBTITLE = ("17 gates asserting closed-form physics, plus four tests that prove "
            "the gates reject broken input.")
TAGS = ['robotics', 'physics']

CELLS = [
("md", """
## The failure CI has to catch

A broken robot model does not crash. It loads, it simulates, it looks entirely
plausible, and its dynamics are wrong. Nothing throws. The damage shows up
later, as a policy that will not transfer.

That is what these gates exist for, and it drives two design choices that are
not obvious.
"""),

("md", """
## 1. Assert against closed-form physics, not golden files

Golden-value tests rot. Someone regenerates the golden file after a change and
the test passes forever afterwards, regardless of whether the change was
correct. The test becomes a record of what the code does rather than what it
should do.

Where an analytic answer exists, assert against **that** - it cannot be
regenerated:

```python
def test_coulomb_stopping_distance(mu, tol_pct):
    # d = v^2 / (2*mu*g).  Friction that is subtly wrong passes an
    # "it slid and stopped" check and fails this one.
    analytic = v0**2 / (2*mu*G)
    assert abs(measured - analytic)/analytic*100 < tol_pct


def test_gravity_recovered_from_freefall():
    # fit z = a*t^2 + b*t + c; -2a must be g.
    # Timestep-independent, unlike comparing raw positions -- a 60 Hz
    # first-order integrator sits ~35 mm off the analytic curve while
    # being entirely correct.
    a, _, _ = np.polyfit(ts, zs, 2)
    assert abs(-2*a - 9.81) < 0.05
```

The full set:

| gate | asserts |
|---|---|
| `test_formats_agree` | 151 cross-format comparisons, zero mismatches |
| `test_forward_kinematics` | FK error < 1e-12 m over 2000 configurations |
| `test_inertia_is_physical` | triangle inequality on every tensor |
| `test_gravity_recovered_from_freefall` | fitted `-2a` equals 9.81 |
| `test_rest_height_equals_half_extent` | settled box centre at exactly 0.05 m |
| `test_coulomb_stopping_distance` | `v^2/(2*mu*g)` at three friction values |
| `test_coulomb_is_mass_independent` | 5x the mass changes distance < 5% |
| `test_rk4_beats_euler_on_energy_drift` | integrator regression |
| `test_simulation_is_deterministic` | same input, identical output |
"""),

("md", """
## 2. Test that the gates actually bite

A suite that passes on a broken model is worse than no suite, because it
converts "unknown" into "verified". So four tests feed each gate deliberately
broken input and assert rejection.

The sharpest one replaces Coulomb friction with **linear velocity drag**:

```python
def test_gate_rejects_velocity_drag_masquerading_as_friction():
    # Linear drag decelerates light objects faster, so stopping distance
    # becomes mass-DEPENDENT -- exactly what the real gate must notice.
    m.dof_damping[:3] = 2.0          # drag, not Coulomb
    ...
    with pytest.raises(AssertionError):
        assert spread < 5.0
```

A box under drag still slides and still stops. It looks like friction. The
mass-independence gate is the thing that can tell them apart, and this test
proves it can - rather than assuming it.

The others confirm the gates reject unphysical inertia tensors, inverted joint
limits, and a world with the wrong gravity.
"""),

("md", """
## 3. Regenerate, do not trust the committed artifact

The model is generated from a single parameter file. CI regenerates it and
**fails if the result differs from what is checked in**:

```yaml
- name: fail if generated files differ from committed ones
  run: |
    if ! git diff --exit-code -- model/arm3.xml model/arm3.urdf model/arm3.sdf; then
      echo "::error::Generated model differs from the committed files."
      echo "Someone edited a format by hand instead of editing robot_spec.py."
      exit 1
    fi
```

That enforces single-source-of-truth **mechanically** rather than by
convention. Hand-editing one of three formats is precisely how they drift
apart, and a code review will not reliably catch a changed inertia digit.

The matrix runs a pinned MuJoCo and `latest`, so an upstream change surfaces in
CI rather than in someone's training run.

```
17 passed in 0.6s
```

## The general point

Every gate here encodes something that can be checked without trusting the
thing being tested. That is the whole idea: `v^2/(2*mu*g)` does not care what
your simulator believes, a triangle inequality does not care what your CAD tool
exported, and a regenerated file does not care what someone edited by hand.

Full suite and workflow are in the linked dataset.
"""),
]
