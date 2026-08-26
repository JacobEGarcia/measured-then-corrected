"""Gates for the closed-chain and collision-cost studies.

Each test asserts the SPECIFIC claim the study makes, so that if a MuJoCo
upgrade changes the behaviour the claim is retracted by a failing build rather
than left standing in a README.
"""
import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))

import closed_chain as cc
import collision_cost as col


# ---------------------------------------------------------------- closed chain

def test_open_chain_rocker_is_completely_disconnected():
    """The headline claim: drop the loop closure (as URDF forces you to) and
    the rocker becomes a free body that never learns the coupler exists."""
    _, _, q_open = cc.simulate(closed=False)
    rocker_travel = float(q_open[:, 2].max() - q_open[:, 2].min())
    assert rocker_travel < 1e-9, (
        f"open-chain rocker moved {rocker_travel:.3e} rad; it should be "
        "perfectly static -- nothing drives it")


def test_closing_the_loop_actually_drives_the_rocker():
    _, _, q_cl = cc.simulate(closed=True)
    rocker_travel = float(q_cl[:, 2].max() - q_cl[:, 2].min())
    assert rocker_travel > 0.3, (
        f"closed-loop rocker only moved {rocker_travel:.4f} rad; the equality "
        "constraint is not transmitting motion")


def test_loop_closure_is_soft_and_tunable():
    """Not a hard constraint: the default leaves millimetres of gap."""
    rows = cc.loop_stiffness_sweep()
    default = [r for r in rows if r["solref_label"] == "default"
               and r["solimp"].startswith("0.9 ")][0]
    tightest = min(rows, key=lambda r: r["mean_gap_mm"])
    assert default["mean_gap_mm"] > 1.0, (
        "default loop closure is tighter than 1 mm -- the 'soft constraint' "
        "claim in the study no longer holds")
    assert default["mean_gap_mm"] / tightest["mean_gap_mm"] > 20, (
        "tuning solref/solimp no longer buys >20x; the sweep's conclusion "
        "needs rewriting")


def test_max_gap_is_a_spawn_artifact_not_a_stiffness_problem():
    """The correction that mattered: I blamed softness, but the worst gap is
    at step 0, before the solver has run at all."""
    r = cc.spawn_manifold_check()
    assert r["argmax_step"] == 0, (
        f"worst loop gap moved to step {r['argmax_step']}; it used to be the "
        "spawn transient, so the diagnosis needs re-checking")
    assert r["settled_max_mm"] < 0.5, (
        f"settled gap {r['settled_max_mm']} mm -- once past the transient the "
        "loop should hold to well under half a millimetre")
    assert r["gap_at_spawn_mm"] > 10 * r["settled_max_mm"], (
        "spawn gap is no longer dramatically worse than the settled gap")


# -------------------------------------------------------------- collision cost

@pytest.fixture(scope="module")
def rows():
    out = []
    for kind, sub, label in (("sphere", 0, "primitive sphere"),
                             ("box", 0, "primitive box"),
                             ("mesh", 0, "mesh (icosa, 12 v)"),
                             ("mesh", 2, "mesh (subdiv 2)")):
        m = col.scene(kind, subdiv=sub)
        r = col.bench(m, steps=600, warmup=100)
        r.update({"kind": kind, "label": label,
                  "hull_vertices": int(m.mesh_vertnum[0]) if kind == "mesh" else 0})
        out.append(r)
    return col.normalise(out)["rows"]


def test_mesh_cost_grows_with_hull_vertices(rows):
    small = [r for r in rows if r["hull_vertices"] == 12][0]
    big = [r for r in rows if r["hull_vertices"] > 100][0]
    assert big["us_per_contact"] > 2 * small["us_per_contact"], (
        "a 23x larger convex hull no longer costs >2x per contact; the "
        "'convexify your collision meshes' recommendation may be obsolete")


def test_mesh_vertex_scaling_is_sublinear(rows):
    """GJK/MPR on a convex hull should not pay linearly in vertex count.
    If this ever goes super-linear, mesh budgets need rethinking."""
    small = [r for r in rows if r["hull_vertices"] == 12][0]
    big = [r for r in rows if r["hull_vertices"] > 100][0]
    vratio = big["hull_vertices"] / small["hull_vertices"]
    cratio = big["us_per_contact"] / small["us_per_contact"]
    assert cratio < vratio, (
        f"cost scaled {cratio:.2f}x for {vratio:.2f}x vertices -- that is "
        "linear or worse, contradicting the sub-linear hull claim")


def test_raw_steps_per_second_is_a_misleading_shape_comparison(rows):
    """Guards the CONFOUND, not just the result. The box looks slower than the
    sphere in raw steps/s purely because it makes ~4x the contacts; per
    contact it is cheaper. If this inverts, the study's caveat is wrong."""
    sph = [r for r in rows if r["label"] == "primitive sphere"][0]
    box = [r for r in rows if r["label"] == "primitive box"][0]
    assert box["steps_per_s"] < sph["steps_per_s"], "box no longer looks slower raw"
    assert box["mean_contacts"] > 2 * sph["mean_contacts"], "box contact count changed"
    assert box["us_per_contact"] < sph["us_per_contact"], (
        "per contact the box is no longer cheaper than the sphere -- the "
        "'raw steps/s is the wrong metric' argument loses its example")
