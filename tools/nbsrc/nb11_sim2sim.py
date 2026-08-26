TITLE = 'MuJoCo vs Isaac Sim Against Closed-Form Physics'
SLUG = 'mujoco-vs-isaac-sim-against-closed-form-physics'
SUBTITLE = ("Both engines measured against Coulomb's law rather than each other. "
            "They agree to 2% - until one of them stops being right.")
TAGS = ['robotics', 'physics', 'reinforcement learning']

CELLS = [
("md", """
## Comparing two simulators cannot tell you which is wrong

The usual cross-engine benchmark runs the same scene in two simulators and
reports the difference. That tells you they disagree. It does not tell you
which one to believe - and the more established engine usually gets treated as
ground truth by default.

So this uses a task with a **closed-form answer**. Launch a box at 2 m/s across
a plane of known friction; Coulomb gives the stopping distance exactly:

$$d = \\frac{v^2}{2\\mu g}$$

Now theory is the referee, and each engine can be scored independently.
"""),

("md", """
## One control that decides whether this is fair

Friction is set **identically on the box and the ground**.

That is not cosmetic. **PhysX averages** the friction of two contacting
materials; **MuJoCo takes the elementwise maximum**. With different values on
the two surfaces, this experiment would measure the *combination rule* and
report it as a solver difference.

Setting them equal makes both rules agree - `max(mu,mu) = avg(mu,mu) = mu` -
so what is left is the solver.

I found that difference the hard way earlier in this series: measured stopping
distances only fit theory once I accounted for PhysX averaging the box's
friction with the ground plane's. Set a robot's foot friction to 0.9 against a
0.5 ground and the effective value is 0.7.
"""),

("code", r'''
import json, os
import numpy as np

MJ = json.loads(r"""{"engine": "mujoco","version": "3.12.0","v0": 2.0,"dt": 0.004166666666666667,"integrator": "RK4","note": "friction identical on box and floor to neutralise differing contact-combination rules","wall_s": 0.1,"runs": [{"mu": 0.2,"stop_x": 1.0194,"final_speed": 0.0,"stopped": true,"analytic": 1.01937,"err_pct_vs_analytic": 0.0},{"mu": 0.3,"stop_x": 0.67968,"final_speed": 0.0,"stopped": true,"analytic": 0.67958,"err_pct_vs_analytic": 0.01},{"mu": 0.4,"stop_x": 0.5098,"final_speed": 0.0,"stopped": true,"analytic": 0.50968,"err_pct_vs_analytic": 0.02},{"mu": 0.5,"stop_x": 0.40786,"final_speed": 0.0,"stopped": true,"analytic": 0.40775,"err_pct_vs_analytic": 0.03},{"mu": 0.6,"stop_x": 0.34001,"final_speed": 0.0,"stopped": true,"analytic": 0.33979,"err_pct_vs_analytic": 0.06},{"mu": 0.8,"stop_x": 0.25578,"final_speed": 0.0,"stopped": true,"analytic": 0.25484,"err_pct_vs_analytic": 0.37},{"mu": 1.0,"stop_x": 0.17117,"final_speed": 0.0,"stopped": true,"analytic": 0.20387,"err_pct_vs_analytic": 16.04}]}""")
IS = json.loads(r"""{"engine": "isaac-sim","version": "6.0.1.0","v0": 2.0,"dt": 0.004166666666666667,"runs": [{"mu": 0.2,"stop_x": 1.01523,"final_speed": 0.00014,"stopped": true,"analytic": 1.01937,"err_pct_vs_analytic": 0.41,"ground_material_applied": true},{"mu": 0.3,"stop_x": 0.67545,"final_speed": 9e-05,"stopped": true,"analytic": 0.67958,"err_pct_vs_analytic": 0.61,"ground_material_applied": true},{"mu": 0.4,"stop_x": 0.50557,"final_speed": 9e-05,"stopped": true,"analytic": 0.50968,"err_pct_vs_analytic": 0.81,"ground_material_applied": true},{"mu": 0.5,"stop_x": 0.40364,"final_speed": 9e-05,"stopped": true,"analytic": 0.40775,"err_pct_vs_analytic": 1.01,"ground_material_applied": true},{"mu": 0.6,"stop_x": 0.3357,"final_speed": 0.0001,"stopped": true,"analytic": 0.33979,"err_pct_vs_analytic": 1.2,"ground_material_applied": true},{"mu": 0.8,"stop_x": 0.25078,"final_speed": 0.0001,"stopped": true,"analytic": 0.25484,"err_pct_vs_analytic": 1.6,"ground_material_applied": true},{"mu": 1.0,"stop_x": 0.1978,"final_speed": 9e-05,"stopped": true,"analytic": 0.20387,"err_pct_vs_analytic": 2.98,"ground_material_applied": true}]}""")
DATA = "/kaggle/input/isaac-sim-kaggle-benchmarks"
for name, fallback in (("sim2sim_mujoco.json", "MJ"), ("sim2sim_isaac.json", "IS")):
    p = os.path.join(DATA, name)
    if os.path.exists(p):
        globals()[fallback] = json.load(open(p))

M = {r["mu"]: r for r in MJ["runs"]}
I = {r["mu"]: r for r in IS["runs"]}
mus = sorted(set(M) & set(I))

print(f"{'mu':>5} {'MuJoCo':>9} {'Isaac':>9} {'analytic':>9} "
      f"{'MJ err%':>8} {'IS err%':>8} {'gap%':>7}")
for mu in mus:
    a = M[mu]["analytic"]
    gap = abs(I[mu]["stop_x"] - M[mu]["stop_x"]) / abs(M[mu]["stop_x"]) * 100
    print(f"{mu:>5.2f} {M[mu]['stop_x']:>9.4f} {I[mu]['stop_x']:>9.4f} {a:>9.4f} "
          f"{M[mu]['err_pct_vs_analytic']:>7.1f}% {I[mu]['err_pct_vs_analytic']:>7.1f}% "
          f"{gap:>6.1f}%")
'''),

("code", r'''
import matplotlib.pyplot as plt

mj_x = np.array([M[m]["stop_x"] for m in mus])
is_x = np.array([I[m]["stop_x"] for m in mus])
an   = np.array([M[m]["analytic"] for m in mus])
mu   = np.array(mus)

fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))

ax[0].plot(mu, an, "k--", lw=2, label=r"Coulomb  $v^2/2\mu g$", zorder=1)
ax[0].plot(mu, mj_x, "o-", lw=2.3, ms=8, color="#e76f51", label="MuJoCo (CPU)")
ax[0].plot(mu, is_x, "s-", lw=2.3, ms=8, color="#2a9d8f", label="Isaac Sim (free T4)")
ax[0].set_xlabel(r"friction coefficient $\mu$")
ax[0].set_ylabel("stopping distance (m)")
ax[0].set_title("Both engines against theory")
ax[0].legend(fontsize=9); ax[0].grid(alpha=.3)

emj = np.abs(mj_x-an)/an*100
eis = np.abs(is_x-an)/an*100
ax[1].plot(mu, emj, "o-", lw=2.3, ms=8, color="#e76f51", label="MuJoCo")
ax[1].plot(mu, eis, "s-", lw=2.3, ms=8, color="#2a9d8f", label="Isaac Sim")
ax[1].axhline(2, color="#8d99ae", ls=":", lw=1.4, label="2% band")
ax[1].set_yscale("log")
ax[1].set_xlabel(r"friction coefficient $\mu$")
ax[1].set_ylabel("error vs theory (%)")
ax[1].set_title("Different failure profiles")
ax[1].legend(fontsize=9); ax[1].grid(alpha=.3, which="both")
plt.tight_layout(); plt.show()

gap = np.abs(is_x-mj_x)/np.abs(mj_x)*100
print(f"cross-engine gap for mu <= 0.8 : {gap[:-1].min():.1f}% - {gap[:-1].max():.1f}%")
print(f"at mu = 1.0                    : {gap[-1]:.1f}%")
print(f"  MuJoCo vs theory: {emj[-1]:.1f}%   Isaac vs theory: {eis[-1]:.1f}%")
'''),

("md", """
## The result

**For mu <= 0.8 the engines agree within 0.4-2.0%.** For rigid-body sliding,
transfer between MuJoCo and Isaac Sim is essentially free - a controller tuned
in one will behave the same in the other.

At mu = 1.0 they diverge by **15.6%**, and this is where the referee earns its
place:

| | error vs theory at mu=1.0 |
|---|---|
| MuJoCo | **16.0%** |
| Isaac Sim | **3.0%** |

**MuJoCo is the one that is wrong.** The box stops 16% short, most plausibly
tipping onto its leading edge rather than sliding flat: at mu=1.0 the friction
force approaches the weight, and the torque about the front edge wins.

Run as a plain A-vs-B comparison, the natural conclusion would have been
"Isaac Sim deviates 15.6% from MuJoCo at high friction" - treating the older,
more established engine as truth. That would have been backwards.
"""),

("md", """
## Two different failure profiles

**MuJoCo is exact until it is not.** 0.0% error through mu=0.6, 0.4% at 0.8,
then a cliff at 1.0.

**Isaac Sim carries a small systematic bias but degrades gracefully.** It runs
0.4% short at mu=0.2, rising smoothly to 1.6% at 0.8, and is still within 3% at
mu=1.0 where MuJoCo has broken down.

Which you prefer depends on the job. For system identification, where you are
fitting parameters against real data in a normal friction range, MuJoCo's
near-exactness is worth more. For contact-heavy manipulation near the limits of
the friction cone, Isaac Sim's graceful degradation is worth more.

Neither is "more accurate" without saying where.

## Reproducing

The MuJoCo half runs on any laptop CPU in seconds. The Isaac Sim half needs an
NVIDIA GPU with RT cores - a free Kaggle T4 does it. Both generators are in the
linked dataset and share a parameter block deliberately, so the two runs cannot
drift apart.

If you extend this to other primitives - spheres rolling, boxes on inclines,
restitution - post what you find. There is very little published data
comparing simulators against analytic solutions rather than against each other.
"""),
]
