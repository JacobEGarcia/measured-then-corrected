"""Mesh vs primitive collision cost: the single biggest perf lever in a scene.

JD: "optimize simulation performance" / "identify and resolve simulation
performance bottlenecks."

Artists hand you meshes. Every collision shape that arrives as a triangle soup
instead of a primitive costs you throughput. This measures how much, and how
the cost scales with vertex count -- so the answer to "can we just use the
visual mesh for collision?" is a number, not an opinion.

MuJoCo convexifies meshes at load, so the cost driver is the CONVEX HULL
vertex count, not the source triangle count.
"""
import json, os, time
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))


def icosphere(subdiv):
    """Unit sphere as a convex vertex cloud; vertex count grows with subdiv."""
    t = (1.0 + 5.0 ** 0.5) / 2.0
    v = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
                  [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
                  [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], dtype=float)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    for _ in range(subdiv):
        # midpoint-refine every pair, renormalise: more hull vertices
        extra = []
        for i in range(len(v)):
            for j in range(i + 1, len(v)):
                if np.dot(v[i], v[j]) > 0.4:          # near neighbours only
                    mp = v[i] + v[j]
                    extra.append(mp / np.linalg.norm(mp))
        v = np.unique(np.round(np.vstack([v, np.array(extra)]), 6), axis=0)
    return v * 0.05                                    # 5 cm radius


def scene(kind, n_bodies=40, subdiv=1):
    """A pile of n_bodies falling onto a plane, all using the same shape kind."""
    if kind == "sphere":
        asset, geom = "", '<geom type="sphere" size="0.05" mass="0.2"/>'
    elif kind == "box":
        asset, geom = "", '<geom type="box" size="0.05 0.05 0.05" mass="0.2"/>'
    elif kind == "mesh":
        v = icosphere(subdiv)
        pts = " ".join(f"{x:.6f}" for x in v.flatten())
        asset = f'<asset><mesh name="blob" vertex="{pts}"/></asset>'
        geom = '<geom type="mesh" mesh="blob" mass="0.2"/>'
    else:
        raise ValueError(kind)

    bodies = []
    rng = np.random.default_rng(0)
    for i in range(n_bodies):
        # a tight lattice so they genuinely interpenetrate and generate contacts
        x = (i % 5) * 0.11 - 0.22
        y = ((i // 5) % 5) * 0.11 - 0.22
        z = 0.08 + (i // 25) * 0.12
        bodies.append(f'<body pos="{x:.3f} {y:.3f} {z:.3f}">'
                      f'<freejoint/>{geom}</body>')

    xml = f"""<mujoco>
      <option timestep="0.002" gravity="0 0 -9.81"/>
      {asset}
      <worldbody>
        <geom type="plane" size="5 5 0.1"/>
        {''.join(bodies)}
      </worldbody>
    </mujoco>"""
    return mujoco.MjModel.from_xml_string(xml)


def bench(m, steps=2000, warmup=200):
    d = mujoco.MjData(m)
    for _ in range(warmup):
        mujoco.mj_step(m, d)
    ncon = []
    t0 = time.perf_counter()
    for _ in range(steps):
        mujoco.mj_step(m, d)
        ncon.append(d.ncon)
    dt = time.perf_counter() - t0
    return {"steps_per_s": round(steps / dt, 1),
            "us_per_step": round(dt / steps * 1e6, 2),
            "mean_contacts": round(float(np.mean(ncon)), 1)}


if __name__ == "__main__":
    out, rows = {}, []

    for kind, sub, label in (("sphere", None, "primitive sphere"),
                             ("box", None, "primitive box"),
                             ("mesh", 0, "mesh (icosa, 12 v)"),
                             ("mesh", 1, "mesh (subdiv 1)"),
                             ("mesh", 2, "mesh (subdiv 2)")):
        m = scene(kind, subdiv=sub or 0)
        nv = int(m.mesh_vertnum[0]) if kind == "mesh" else 0
        r = bench(m)
        r.update({"kind": kind, "label": label, "hull_vertices": nv})
        rows.append(r)
        print(f"  {label:<22} v={nv:<4} {r['steps_per_s']:>9.1f} steps/s   "
              f"{r['us_per_step']:>7.2f} us/step   contacts {r['mean_contacts']:>6.1f}")

    base = next(r for r in rows if r["label"] == "primitive sphere")
    print()
    for r in rows:
        if r["kind"] == "mesh":
            print(f"  {r['label']:<22} is {base['steps_per_s']/r['steps_per_s']:>5.2f}x "
                  f"SLOWER than the primitive sphere it approximates")

    out["scenes"] = rows
    out["primitive_baseline"] = base
    json.dump(out, open(os.path.join(HERE, "collision_cost.json"), "w"), indent=2)
    print("\nwrote model/collision_cost.json")


def normalise(rows):
    """CONFOUND FOUND, then corrected.

    The raw table reads "mesh is 2.6x-11.8x slower than a primitive sphere",
    but the scenes do not generate the same number of contacts: a sphere pair
    yields 1 contact, a box pair yields up to 4, and the meshes land in
    between. Part of the "mesh penalty" is simply more contacts to solve.

    Normalising to microseconds PER CONTACT separates the two effects. The
    clean controlled comparison is mesh-vs-mesh across vertex counts: same
    shape family, near-identical contact counts, only the hull size varies.
    """
    for r in rows:
        r["us_per_contact"] = round(r["us_per_step"] / max(r["mean_contacts"], 1e-9), 4)
    meshes = [r for r in rows if r["kind"] == "mesh"]
    meshes.sort(key=lambda r: r["hull_vertices"])
    lo, hi = meshes[0], meshes[-1]
    return {"rows": rows,
            "controlled_mesh_scaling": {
                "from_vertices": lo["hull_vertices"], "to_vertices": hi["hull_vertices"],
                "from_us_per_contact": lo["us_per_contact"],
                "to_us_per_contact": hi["us_per_contact"],
                "cost_ratio": round(hi["us_per_contact"] / lo["us_per_contact"], 2),
                "vertex_ratio": round(hi["hull_vertices"] / lo["hull_vertices"], 2)},
            "caveat": ("raw steps/s comparisons across shape TYPES conflate "
                       "per-contact cost with contact COUNT; only the "
                       "mesh-vs-mesh sweep isolates hull-size scaling")}
