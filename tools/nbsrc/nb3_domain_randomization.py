TITLE = 'Physics Domain Randomization Without a Renderer'
SLUG = 'physics-domain-randomization-without-a-renderer'
SUBTITLE = ("The sim2real axis that actually breaks controllers - randomizing "
            "mass and friction instead of colors, verified against Coulomb's "
            "law on a free GPU.")
TAGS = ['robotics', 'computer vision', 'deep learning']

CELLS = [
("md", """
## Two different questions wear the same name

"Domain randomization" usually means **appearance** randomization: scramble
colors, lighting, textures and camera pose so a vision model does not overfit
to your renderer. That is a real technique and it needs a renderer.

**Physics** domain randomization scrambles mass, friction, damping and
restitution instead. Different question, different failure mode:

| | Randomizing appearance | Randomizing physics |
|---|---|---|
| Asks | does my *vision model* survive a new camera? | does my *controller* survive a real robot? |
| Needs a renderer | yes | **no** |
| Breaks when wrong | detections drop | the robot falls over |

This notebook is the second one. It was originally the first - I had it built
around Isaac Sim's Replicator randomizing colors and lights, and then
discovered the RTX renderer does not initialise on Kaggle's free tier at all.

The pivot turned out to be an upgrade. Physics DR is the axis that actually
kills robotics projects, and it runs on free hardware because it never touches
a pixel.
"""),

("md", """
## The experiment

A cube is launched at 2 m/s across a plane and left to slide to rest. Vary the
friction coefficient; vary the mass; measure how far it travels.

This is deliberately a system with a closed-form answer, because the point is
not "randomization changes things" - of course it does. The point is checking
that it changes them **correctly**, which is the part people skip.

Coulomb friction gives stopping distance:

$$d = \\frac{v^2}{2\\mu g}$$

Two predictions fall out, and they are independently checkable:

1. **Distance falls as friction rises** - the obvious one.
2. **Distance does not depend on mass at all.** Friction force scales with
   mass, so deceleration is `mu*g` regardless. This is the non-obvious one, and
   it is the better test: an engine that fakes friction usually gets it wrong.
"""),

("code", r'''
import json, os

EMBEDDED = json.loads(r"""{"runs": [{"mass": 1.0,"friction_set": 0.05,"friction_readback": 0.05000000074505806,"stop_x_m": 0.6093,"final_speed": 0.0459,"monotonic": false},{"mass": 1.0,"friction_set": 0.3,"friction_readback": 0.30000001192092896,"stop_x_m": 0.4617,"final_speed": 0.046,"monotonic": false},{"mass": 1.0,"friction_set": 0.9,"friction_readback": 0.8999999761581421,"stop_x_m": 0.2659,"final_speed": 0.0456,"monotonic": false},{"mass": 5.0,"friction_set": 0.3,"friction_readback": 0.30000001192092896,"stop_x_m": 0.4857,"final_speed": 0.0462,"monotonic": false}],"friction_changes_distance": true,"mass_independent (Coulomb check)": true}""")

DATA = "/kaggle/input/isaac-sim-kaggle-benchmarks"
p = os.path.join(DATA, "physics_dr.json")
dr = json.load(open(p)) if os.path.exists(p) else EMBEDDED
runs = dr["runs"]

print(f"{'mass':>6} {'friction set':>13} {'readback':>10} {'stop x (m)':>12}")
for r in runs:
    print(f"{r['mass']:>6.1f} {r['friction_set']:>13.2f} "
          f"{r['friction_readback']:>10.3f} {r['stop_x_m']:>12.4f}")
'''),

("md", """
Note the `readback` column. That is the friction coefficient read back off the
prim *after* applying the material, not the value we asked for. It exists
because of a bug described further down - and it is the single most useful
column in the table.
"""),

("code", r'''
import matplotlib.pyplot as plt
import numpy as np

m1 = [r for r in runs if r["mass"] == 1.0]
mu = np.array([r["friction_set"] for r in m1])
d  = np.array([r["stop_x_m"] for r in m1])

fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.5))

ax[0].plot(mu, d, "o-", lw=2.6, ms=9, color="#2a9d8f", label="Isaac Sim (measured)")
ax[0].set_xlabel(r"friction coefficient $\mu$")
ax[0].set_ylabel("stopping distance (m)")
ax[0].set_title("Friction shortens the slide")
ax[0].grid(alpha=.3); ax[0].legend(fontsize=9)

pair = [r for r in runs if r["friction_set"] == 0.3]
if len(pair) == 2:
    masses = [r["mass"] for r in pair]
    dists  = [r["stop_x_m"] for r in pair]
    ax[1].bar([f"{m:g} kg" for m in masses], dists,
              color=["#2a9d8f", "#264653"], width=.55)
    spread = abs(dists[0] - dists[1]) / max(dists) * 100
    ax[1].axhline(np.mean(dists), color="#e76f51", ls="--", lw=1.5,
                  label=f"mean (differ by {spread:.1f}%)")
    ax[1].set_ylabel("stopping distance (m)")
    ax[1].set_title(r"Same $\mu$, 5x the mass" "\n" "Coulomb says this should not matter")
    ax[1].legend(fontsize=9); ax[1].grid(alpha=.3, axis="y")

plt.tight_layout(); plt.show()
'''),

("code", r'''
# Prediction 2, stated numerically: mass should not matter.
if len(pair) == 2:
    a, b = pair[0]["stop_x_m"], pair[1]["stop_x_m"]
    print(f"mass {pair[0]['mass']:g} kg -> {a:.4f} m")
    print(f"mass {pair[1]['mass']:g} kg -> {b:.4f} m")
    print(f"difference: {abs(a-b):.4f} m  ({abs(a-b)/max(a,b)*100:.1f}%)")
    print()
    print("Coulomb mass-independence holds:", abs(a-b)/max(a,b) < 0.10)
'''),

("md", """
**Five times the mass moves the stopping distance by about 5%.** PhysX is
reproducing Coulomb friction correctly, not approximating it with something
that happens to look similar.

That is worth more than it may seem. If you are about to spend a week
randomizing friction to make a policy robust, it is worth ten minutes first
confirming that the friction parameter you are randomizing behaves like
friction.
"""),

("md", """
## Checking against theory turns up a trap

Now compare the measured distances against $d = v^2/(2\\mu g)$ directly. They
do not match - and the way they fail is informative.
"""),

("code", r'''
v, g = 2.0, 9.81

print(f"{'mu set':>8} {'measured':>10} {'d(mu)':>10} {'d(mu_avg)':>11}")
for r in m1:
    mu_set = r["friction_set"]
    d_naive = v**2 / (2 * mu_set * g)              # cube's mu alone
    mu_avg  = (mu_set + 0.5) / 2                   # averaged with ground plane
    d_avg   = v**2 / (2 * mu_avg * g)
    print(f"{mu_set:>8.2f} {r['stop_x_m']:>10.4f} {d_naive:>10.3f} {d_avg:>11.3f}")

print()
print("Neither fits perfectly - but note WHICH way each is wrong.")
'''),

("md", """
Using the cube's coefficient alone predicts distances that are far too long at
low friction. Averaging the cube's coefficient with the ground plane's fits
better at *every* friction value tested - which points at **material combine
modes**.

PhysX does not use your material's friction directly. It *combines* the two
materials in contact, and averaging is its documented default. I did not read
the combine mode off the prim here, so treat this as inference that happens to
match the documentation rather than a direct measurement - but the direction of
the error is consistent across all three runs.

So setting the cube to `mu = 0.9` against a ground plane at `mu = 0.5` gives an
effective `mu` of 0.7, not 0.9.

This matters for domain randomization specifically. If you randomize a robot's
foot friction across `[0.1, 1.0]` believing you have covered that range, but
the ground is fixed at 0.5, your *effective* range is only `[0.3, 0.75]` - and
your policy never sees the slippery or grippy extremes you thought you were
training against.

The low-friction row also has a second, more boring explanation worth
separating out: at `mu = 0.05` the cube had not finished stopping when the
measurement ended (its final speed was still ~0.05 m/s). Two different problems
producing one wrong number.
"""),

("md", """
## The bug that nearly published a false positive

The first version of this experiment reported success. It was measuring
nothing.

```python
try:
    pm = PhysicsMaterial(..., static_friction=fric, dynamic_friction=fric)
    cube.apply_physics_material(pm)
except Exception:
    pass                    # <- the entire problem
```

The material application was failing. The bare `except` swallowed it. Every run
used default friction, so the results looked like this:

```
mass 0.5, friction 0.2  ->  0.1689
mass 0.5, friction 0.9  ->  0.1689     <- identical
mass 5.0, friction 0.2  -> -0.9199
mass 5.0, friction 0.9  -> -0.9199     <- identical
```

And the automated check said **`randomization_has_effect: True`**, because the
spread across all four runs exceeded its threshold. The check passed. The
experiment was worthless.

Two things gave it away, and neither was the assertion:

1. **Friction did nothing** - the pairs are byte-identical.
2. **Mass did everything** - which contradicts Coulomb friction, the very law
   the experiment exists to exercise.

The fix was not a better threshold. It was removing the bare `except` and
**reading the friction value back off the prim after setting it**. A parameter
you set but never verify is a parameter you are only assuming.

If you take one thing from this notebook, take that: *assert on physics, not on
variance.* A test that only checks "did the numbers move" will happily pass
while measuring the wrong quantity.
"""),

("md", """
## Using this for sim2real

The workflow this enables, entirely on free hardware:

1. **Verify your randomization does what you think.** Read parameters back.
   Check them against a closed-form case where one exists.
2. **Account for combine modes.** Randomize both surfaces, or compute the
   effective range you are actually covering.
3. **Sweep, do not guess.** Train across a distribution, then evaluate on
   held-out values *outside* the training range. That out-of-range column is
   the one that predicts real-robot behaviour.
4. **Expect non-monotonicity.** Randomizing harder is not monotonically better:
   too wide a distribution and the policy learns a conservative average that is
   good nowhere. Most write-ups report DR as strictly beneficial; the
   interesting result is finding where your task turns over.

Point 4 is the natural next experiment and it needs no renderer either - which
is the broader point. Losing RTX rendering costs you camera-based work. It
costs you nothing at all for the dynamics questions that decide whether a
controller survives contact with a real robot.

---

Corrections and questions welcome below. If you run this against a different
engine, post the numbers - a cross-engine comparison of friction fidelity would
be genuinely useful and I have not seen one.
"""),
]
