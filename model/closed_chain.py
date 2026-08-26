"""Closed kinematic chains: what URDF cannot express, and what it costs.

JD: "Experience creating and validating robot models (URDF, MJCF, or SDF
formats)" / "Background in ... multi-body systems."

URDF is a TREE. Every link has exactly one parent, so it cannot represent a
loop: four-bar linkages, parallel jaws, delta arms, differential drives. This
is not a tooling gap -- it is the file format's data model.

MJCF and SDF both express loops, by different mechanisms:
  MJCF -- an explicit <equality> constraint closing the loop
  SDF  -- a second <joint> that reconnects to an existing link

This measures the difference: a four-bar linkage built as an open chain (what
you get if you export a loop to URDF and drop the closure) versus the same
mechanism with the loop closed.
"""
import json, os
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))

# A planar four-bar: ground -> crank -> coupler, with the coupler's far end
# constrained back to a fixed rocker pivot. Classic loop.
FOURBAR = """
<mujoco model="fourbar">
  <option timestep="0.001" gravity="0 0 -9.81" integrator="RK4"/>
  <worldbody>
    <body name="crank" pos="0 0 0.5">
      <joint name="j_crank" type="hinge" axis="0 1 0" damping="0.01"/>
      <geom type="capsule" fromto="0 0 0 0.20 0 0" size="0.012" mass="0.3"/>
      <body name="coupler" pos="0.20 0 0">
        <joint name="j_coupler" type="hinge" axis="0 1 0" damping="0.01"/>
        <geom type="capsule" fromto="0 0 0 0.35 0 0" size="0.010" mass="0.4"/>
        <site name="tip" pos="0.35 0 0" size="0.008"/>
      </body>
    </body>
    <body name="rocker" pos="0.45 0 0.5">
      <joint name="j_rocker" type="hinge" axis="0 1 0" damping="0.01"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.25" size="0.012" mass="0.3"/>
      <site name="rock_tip" pos="0 0 -0.25" size="0.008"/>
    </body>
  </worldbody>
  {equality}
</mujoco>
"""

CLOSED = """
  <equality>
    <!-- THE LOOP CLOSURE. URDF has no equivalent: it cannot state that two
         links in different branches must stay connected. -->
    <connect name="loop" site1="tip" site2="rock_tip"/>
  </equality>
"""


def build(closed):
    return mujoco.MjModel.from_xml_string(
        FOURBAR.format(equality=CLOSED if closed else ""))


def simulate(closed, steps=3000, q0=0.6):
    m = build(closed)
    d = mujoco.MjData(m)
    d.qpos[0] = q0
    mujoco.mj_forward(m, d)
    tip = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "tip")
    rock = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "rock_tip")
    gaps, qs = [], []
    for _ in range(steps):
        mujoco.mj_step(m, d)
        gaps.append(float(np.linalg.norm(d.site_xpos[tip] - d.site_xpos[rock])))
        qs.append(d.qpos.copy())
    return m, np.array(gaps), np.array(qs)


CLOSED_TUNED = """
  <equality>
    <connect name="loop" site1="tip" site2="rock_tip"
             solref="{sr}" solimp="{si}"/>
  </equality>
"""


def build_tuned(solref, solimp):
    return mujoco.MjModel.from_xml_string(
        FOURBAR.format(equality=CLOSED_TUNED.format(sr=solref, si=solimp)))


def loop_stiffness_sweep():
    """A loop closure is a SOFT constraint, exactly like a contact.

    The default leaves 11 mm of mean gap -- the linkage visibly comes apart
    under load. solref/solimp tighten it, and the same 2*dt clamp found in the
    contact study applies here too.
    """
    rows = []
    for sr, label in (("0.02 1", "default"), ("0.005 1", "stiffer"),
                      ("0.002 1", "stiffer still"), ("0.001 1", "at 2*dt limit")):
        for si in ("0.9 0.95 0.001", "0.99 0.9999 0.0001"):
            m = build_tuned(sr, si)
            d = mujoco.MjData(m)
            d.qpos[0] = 0.6
            mujoco.mj_forward(m, d)
            tip = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "tip")
            rock = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "rock_tip")
            gaps = []
            for _ in range(3000):
                mujoco.mj_step(m, d)
                gaps.append(float(np.linalg.norm(d.site_xpos[tip] - d.site_xpos[rock])))
            g = np.array(gaps)
            rows.append({"solref": sr, "solref_label": label, "solimp": si,
                         "mean_gap_mm": round(float(g.mean()) * 1000, 4),
                         "max_gap_mm": round(float(g.max()) * 1000, 4)})
    return rows


def spawn_manifold_check(solref="0.002 1", solimp="0.99 0.9999 0.0001", q0=0.6):
    """WRONG PREDICTION, then the correction.

    I read a 57 mm max loop gap and assumed the constraint was too soft, so I
    swept solref/solimp. The mean improved 109x (11.518 mm -> 0.106 mm) but the
    max barely moved (60.6 mm -> 56.9 mm). That asymmetry was the tell.

    The max occurs at STEP 0. Setting qpos[0]=0.6 places the mechanism in a
    configuration where the loop is already broken by 60.7 mm; the solver then
    hauls the pivots together over ~200 steps. No stiffness value fixes an
    initial condition.

    The real lesson for loop-closed models: you cannot set qpos arbitrarily.
    A tree model accepts any joint vector, but a loop-closed model has a
    CONSTRAINT MANIFOLD, and off-manifold spawns produce a startup transient
    that looks exactly like a physics bug.
    """
    m = build_tuned(solref, solimp)
    d = mujoco.MjData(m)
    d.qpos[0] = q0
    mujoco.mj_forward(m, d)
    tip = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "tip")
    rock = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "rock_tip")
    gap_at_spawn = float(np.linalg.norm(d.site_xpos[tip] - d.site_xpos[rock]))
    gaps = []
    for _ in range(3000):
        mujoco.mj_step(m, d)
        gaps.append(float(np.linalg.norm(d.site_xpos[tip] - d.site_xpos[rock])))
    g = np.array(gaps)
    settle = 200
    return {"gap_at_spawn_mm": round(gap_at_spawn * 1000, 4),
            "argmax_step": int(g.argmax()),
            "max_gap_mm": round(float(g.max()) * 1000, 4),
            "mean_first_100_steps_mm": round(float(g[:100].mean()) * 1000, 4),
            "settled_mean_mm": round(float(g[settle:].mean()) * 1000, 4),
            "settled_max_mm": round(float(g[settle:].max()) * 1000, 4),
            "diagnosis": ("max gap is at step 0 -- an off-manifold spawn, not a "
                          "soft constraint. Loop-closed models must be "
                          "initialised ON the constraint manifold.")}


if __name__ == "__main__":
    out = {}
    m_open, gap_open, q_open = simulate(closed=False)
    m_cl, gap_cl, q_cl = simulate(closed=True)

    out["dof"] = {"open_chain_nv": int(m_open.nv), "closed_chain_nv": int(m_cl.nv),
                  "equality_constraints": int(m_cl.neq)}
    print("degrees of freedom")
    print(f"  open  chain : nv={m_open.nv}  (3 independent joints)")
    print(f"  closed loop : nv={m_cl.nv}  with {m_cl.neq} equality constraint")
    print("  NOTE: nv is unchanged -- MuJoCo keeps the tree coordinates and")
    print("        enforces the loop as a CONSTRAINT, rather than reducing DOF.")

    out["loop_gap"] = {
        "open_mean_m": float(gap_open.mean()), "open_max_m": float(gap_open.max()),
        "closed_mean_m": float(gap_cl.mean()), "closed_max_m": float(gap_cl.max())}
    print("\nloop closure error (distance between the two pivot sites)")
    print(f"  open  chain : mean {gap_open.mean():.5f} m   max {gap_open.max():.5f} m")
    print(f"  closed loop : mean {gap_cl.mean():.3e} m   max {gap_cl.max():.3e} m")
    print(f"  ratio       : {gap_open.mean()/max(gap_cl.mean(),1e-12):.0f}x tighter")

    # the mechanism's actual behaviour differs, not just its bookkeeping
    out["motion"] = {
        "open_crank_range_rad": float(q_open[:, 0].max() - q_open[:, 0].min()),
        "closed_crank_range_rad": float(q_cl[:, 0].max() - q_cl[:, 0].min()),
        "open_rocker_range_rad": float(q_open[:, 2].max() - q_open[:, 2].min()),
        "closed_rocker_range_rad": float(q_cl[:, 2].max() - q_cl[:, 2].min())}
    print("\njoint travel over 3 s")
    print(f"  crank  : open {out['motion']['open_crank_range_rad']:.4f} rad   "
          f"closed {out['motion']['closed_crank_range_rad']:.4f} rad")
    print(f"  rocker : open {out['motion']['open_rocker_range_rad']:.4f} rad   "
          f"closed {out['motion']['closed_rocker_range_rad']:.4f} rad")
    print("\n  In the open chain the rocker is a free pendulum -- it has no idea")
    print("  the coupler exists. Closing the loop couples them, which is the")
    print("  entire point of the mechanism.")

    out["format_support"] = {
        "URDF": "cannot express -- strictly a tree, one parent per link",
        "MJCF": "<equality><connect> between two sites",
        "SDF": "a second <joint> reconnecting to an existing link"}
    print("\nformat support")
    for k, v in out["format_support"].items():
        print(f"  {k:<5}: {v}")

    out["loop_stiffness_sweep"] = loop_stiffness_sweep()
    out["spawn_manifold"] = spawn_manifold_check()
    json.dump(out, open(os.path.join(HERE, "closed_chain.json"), "w"), indent=2)
    print("\nwrote model/closed_chain.json")
