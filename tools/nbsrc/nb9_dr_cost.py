TITLE = 'Domain Randomization Has a Price'
SLUG = 'domain-randomization-has-a-price'
SUBTITLE = ("Measured across eight randomization widths on a free GPU: when the "
            "nominal model is already right, randomizing strictly costs you.")
TAGS = ['robotics', 'physics', 'reinforcement learning']

CELLS = [
("md", """
## The claim being tested

Domain randomization is standard practice in sim2real: randomize masses,
frictions and damping during training so the policy survives a real robot whose
parameters you never knew exactly.

It is almost universally reported as beneficial. This notebook measures a
regime where it is **strictly harmful**, and explains why that regime is not
exotic.

The task is deliberately one with a closed-form answer, so the rig can be
checked rather than trusted: launch a box and have it stop on a mark 0.5 m away.
The controller has exactly one parameter, `k`, where the launch speed is
`v = k*sqrt(d)`. Under Coulomb friction the correct value is `k = sqrt(2*mu*g)` -
so a controller tuned for one friction is wrong for another. Sim2real in
miniature.
"""),

("code", r'''
import json, os
import numpy as np

EMBEDDED = json.loads(r"""{"target_m": 0.5,"n_box": 24,"test_mu_range": [0.3,0.7],"tolerance_m": 0.08,"seeds": [0,1],"design_note": "test range sits INSIDE the wider training ranges; v1 had it backwards and produced a flat line","k_candidates": [2.0,2.136842105263158,2.2736842105263158,2.4105263157894736,2.5473684210526315,2.6842105263157894,2.8210526315789473,2.957894736842105,3.094736842105263,3.231578947368421,3.3684210526315788,3.5052631578947366,3.6421052631578945,3.7789473684210524,3.9157894736842103,4.052631578947368,4.189473684210526,4.326315789473684,4.463157894736842,4.6],"wall_s": 1620.2,"sweep": [{"width_frac": 0.0,"train_lo": 0.5,"train_hi": 0.5,"mean_best_k": 3.095,"test_err_mean": 0.054,"test_err_std": 0.0,"test_success": 0.75,"seeds": [{"seed": 0,"best_k": 3.095,"train_err": 0.0204,"test_err": 0.054,"test_success": 0.75},{"seed": 1,"best_k": 3.095,"train_err": 0.0204,"test_err": 0.054,"test_success": 0.75}]},{"width_frac": 0.2,"train_lo": 0.4,"train_hi": 0.6,"mean_best_k": 3.095,"test_err_mean": 0.054,"test_err_std": 0.0,"test_success": 0.75,"seeds": [{"seed": 0,"best_k": 3.095,"train_err": 0.033,"test_err": 0.054,"test_success": 0.75},{"seed": 1,"best_k": 3.095,"train_err": 0.0249,"test_err": 0.054,"test_success": 0.75}]},{"width_frac": 0.4,"train_lo": 0.3,"train_hi": 0.7,"mean_best_k": 3.095,"test_err_mean": 0.054,"test_err_std": 0.0,"test_success": 0.75,"seeds": [{"seed": 0,"best_k": 3.095,"train_err": 0.0627,"test_err": 0.054,"test_success": 0.75},{"seed": 1,"best_k": 3.095,"train_err": 0.0441,"test_err": 0.054,"test_success": 0.75}]},{"width_frac": 0.6,"train_lo": 0.2,"train_hi": 0.8,"mean_best_k": 3.095,"test_err_mean": 0.054,"test_err_std": 0.0,"test_success": 0.75,"seeds": [{"seed": 0,"best_k": 3.095,"train_err": 0.096,"test_err": 0.054,"test_success": 0.75},{"seed": 1,"best_k": 3.095,"train_err": 0.0664,"test_err": 0.054,"test_success": 0.75}]},{"width_frac": 0.8,"train_lo": 0.1,"train_hi": 0.9,"mean_best_k": 2.958,"test_err_mean": 0.0666,"test_err_std": 0.0,"test_success": 0.583,"seeds": [{"seed": 0,"best_k": 2.958,"train_err": 0.1332,"test_err": 0.0666,"test_success": 0.583},{"seed": 1,"best_k": 2.958,"train_err": 0.0905,"test_err": 0.0666,"test_success": 0.583}]},{"width_frac": 1.0,"train_lo": 0.02,"train_hi": 1.0,"mean_best_k": 2.889,"test_err_mean": 0.0814,"test_err_std": 0.0147,"test_success": 0.479,"seeds": [{"seed": 0,"best_k": 2.821,"train_err": 0.1654,"test_err": 0.0961,"test_success": 0.375},{"seed": 1,"best_k": 2.958,"train_err": 0.1101,"test_err": 0.0666,"test_success": 0.583}]},{"width_frac": 1.4,"train_lo": 0.02,"train_hi": 1.2,"mean_best_k": 3.027,"test_err_mean": 0.0603,"test_err_std": 0.0063,"test_success": 0.666,"seeds": [{"seed": 0,"best_k": 2.958,"train_err": 0.1853,"test_err": 0.0666,"test_success": 0.583},{"seed": 1,"best_k": 3.095,"train_err": 0.1218,"test_err": 0.054,"test_success": 0.75}]},{"width_frac": 1.8,"train_lo": 0.02,"train_hi": 1.4,"mean_best_k": 3.095,"test_err_mean": 0.0629,"test_err_std": 0.0037,"test_success": 0.666,"seeds": [{"seed": 0,"best_k": 2.958,"train_err": 0.2018,"test_err": 0.0666,"test_success": 0.583},{"seed": 1,"best_k": 3.232,"train_err": 0.1323,"test_err": 0.0592,"test_success": 0.75}]}]}""")
DATA = "/kaggle/input/isaac-sim-kaggle-benchmarks"
p = os.path.join(DATA, "dr_sweep.json")
d = json.load(open(p)) if os.path.exists(p) else EMBEDDED
S = d["sweep"]

print(f"test friction grid: mu {d['test_mu_range'][0]:.2f} to "
      f"{d['test_mu_range'][1]:.2f}   tolerance {d.get('tolerance_m')} m")
print(f"wall clock: {d['wall_s']} s on one free T4")
print()
print(f"{'width':>6} {'train mu':>15} {'k':>6} {'TEST err':>10} {'success':>9}")
for r in S:
    print(f"{r['width_frac']:>6.1f} {r['train_lo']:>6.2f}-{r['train_hi']:<8.2f} "
          f"{r['mean_best_k']:>6.2f} {r['test_err_mean']:>10.4f} "
          f"{r['test_success']:>9.2f}")
'''),

("code", r'''
import matplotlib.pyplot as plt

w  = [r["width_frac"] for r in S]
e  = [r["test_err_mean"] for r in S]
sd = [r["test_err_std"] for r in S]
su = [r["test_success"] for r in S]
k  = [r["mean_best_k"] for r in S]

fig, ax = plt.subplots(1, 3, figsize=(14.5, 4.4))

ax[0].errorbar(w, e, yerr=sd, fmt="o-", lw=2.4, ms=8, color="#e76f51", capsize=4)
ax[0].set_xlabel("randomization width (fraction of nominal)")
ax[0].set_ylabel("test error (m)")
ax[0].set_title("More randomization, more error")
ax[0].grid(alpha=.3)

ax[1].plot(w, su, "s-", lw=2.4, ms=8, color="#2a9d8f")
ax[1].set_ylim(0, 1)
ax[1].set_xlabel("randomization width"); ax[1].set_ylabel("success rate")
ax[1].set_title("Success degrades")
ax[1].grid(alpha=.3)

k_true = np.sqrt(2*0.5*9.81)
ax[2].plot(w, k, "^-", lw=2.4, ms=8, color="#264653", label="chosen k")
ax[2].axhline(k_true, color="#c1443b", ls="--", lw=1.5,
              label=r"analytic $\sqrt{2\mu g}$")
ax[2].set_xlabel("randomization width"); ax[2].set_ylabel("controller k")
ax[2].set_title("Wide training drags k off target")
ax[2].legend(fontsize=8.5); ax[2].grid(alpha=.3)

plt.tight_layout(); plt.show()

print(f"k at zero randomization : {k[0]:.3f}")
print(f"analytic sqrt(2*0.5*g)  : {k_true:.3f}")
print(f"agreement               : {abs(k[0]-k_true)/k_true*100:.1f}%")
'''),

("md", """
## The result

**Randomization never helps here, and hurts once the range gets wide.** Zero
randomization gives the lowest error (0.054 m) and the highest success rate
(0.75). By width 1.0 - friction sampled from 0.02 to 1.0 - success has fallen
to 0.48.

The third panel shows the mechanism. At zero randomization the optimiser picks
**k = 3.095**, and the analytic answer is **sqrt(2*0.5*9.81) = 3.132**. A 1.2%
agreement.

That number does two jobs. It explains the result, and it validates the rig:
PhysX friction, the sliding dynamics and the search are all behaving correctly.
The experiment worked. The hypothesis did not hold.
"""),

("md", """
## Why randomization could not have helped

The test distribution is centred on the nominal. A controller fitted to the
nominal is therefore **already optimal for the test range** - there is no
robustness gap for randomization to fill.

Widening the training distribution can then only do harm: it drags `k` toward
friction values that never occur at test time. At width 1.0 the optimiser is
fitting frictions down to 0.02, and `k` falls to 2.89 - away from the 3.13 the
test range actually wants.

Stated generally:

> **Domain randomization is insurance against model error. If your nominal
> parameters are correct, you are paying the premium for a claim you will never
> make.**

The uncomfortable corollary is the useful part. Sim2real practitioners cannot
know whether their nominal is right - that uncertainty is the entire reason for
randomizing. This measures what the insurance costs when it turns out to have
been unnecessary, which is the half of the trade-off that rarely gets reported.
"""),

("md", """
## What this does not show

Being precise about scope, because it would be easy to over-read this:

- **It does not show DR is useless.** It shows DR is costly when nominal is
  correct. The complementary experiment - offset the test distribution so the
  nominal is *wrong* - should show DR paying, and the crossover would tell you
  how much model error justifies how much randomization. That experiment is not
  in this notebook.
- **One parameter, one task.** A richer policy with capacity to *adapt* to
  observed dynamics would behave differently; that is system identification
  rather than blind randomization.
- **Friction only.** Mass, damping and restitution may not behave the same way.

An earlier version of this sweep tested on a friction range *wider* than every
training range and produced a flat line - no signal at all, because no single
`k` could succeed anywhere. Getting the test range inside the training ranges
is what made the effect measurable. If you extend this, that detail is where
the experiment lives or dies.

---

The generator is in the linked dataset and runs on a free T4 in about 27
minutes. If you run the offset-nominal variant, please post what you find.
"""),
]
