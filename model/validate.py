"""Prove the three formats describe the same robot.

Two levels, and the second is the one that matters:

  1. CROSS-VALIDATE the numbers -- mass, inertia, joint axis, limits, damping,
     friction, geometry. Catches copy-paste drift.
  2. FORWARD KINEMATICS -- an independent FK written in plain numpy from the
     URDF joint chain, compared against MuJoCo's own FK over random
     configurations. Matching XML numbers proves the FILES agree. Matching FK
     proves the ROBOTS agree, which is a different and stronger claim.

The full/half extent conversion is checked explicitly, because that is the
single most common cross-format bug: MJCF `size` is a half-extent, URDF and SDF
`<box size>` is the full extent, and getting it wrong yields a robot that is
correct in one simulator and double-sized in the other.
"""
import json, os, sys, xml.etree.ElementTree as ET
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from robot_spec import build, link_frame_offsets, AXIS_VEC, JOINT_FRICTION, CONTACT_MU

SPEC = build()
OFF = link_frame_offsets(SPEC)
TOL = 1e-9
report = {"comparisons": 0, "mismatches": [], "worst": ("", 0.0)}


def cmp(field, a, b, tol=TOL):
    report["comparisons"] += 1
    d = abs(float(a) - float(b))
    if d > report["worst"][1]:
        report["worst"] = (field, d)
    if d > tol:
        report["mismatches"].append({"field": field, "a": float(a),
                                     "b": float(b), "diff": d})


# ---------- parse URDF ----------
u = ET.parse(os.path.join(HERE, "arm3.urdf")).getroot()
u_links = {l.get("name"): l for l in u.findall("link")}
u_joints = {j.get("name"): j for j in u.findall("joint")}

# ---------- parse SDF ----------
s = ET.parse(os.path.join(HERE, "arm3.sdf")).getroot()
s_model = s.find("model")
s_links = {l.get("name"): l for l in s_model.findall("link")}
s_joints = {j.get("name"): j for j in s_model.findall("joint")}

# ---------- MJCF via MuJoCo ----------
m = mujoco.MjModel.from_xml_path(os.path.join(HERE, "arm3.xml"))
d = mujoco.MjData(m)

for i, L in enumerate(SPEC):
    n = L["name"]
    bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)

    # mass, three ways
    cmp(f"{n}.mass mjcf-spec", m.body_mass[bid], L["mass"])
    cmp(f"{n}.mass urdf-spec",
        u_links[n].find("inertial/mass").get("value"), L["mass"])
    cmp(f"{n}.mass sdf-spec",
        s_links[n].find("inertial/mass").text, L["mass"])

    # URDF inertial origin must sit at the body centre, i.e. +half above the
    # joint for every moving link. This is what the FK check caught.
    uo = [float(v) for v in u_links[n].find("inertial/origin").get("xyz").split()]
    want_zc = 0.0 if i == 0 else L["half"][2]
    cmp(f"{n}.inertial_origin_z urdf", uo[2], want_zc)

    # inertia, three ways
    ui = u_links[n].find("inertial/inertia")
    si = s_links[n].find("inertial/inertia")
    for k, key in enumerate(("ixx", "iyy", "izz")):
        cmp(f"{n}.{key} mjcf-spec", m.body_inertia[bid][k], L["diaginertia"][k])
        cmp(f"{n}.{key} urdf-spec", ui.get(key), L["diaginertia"][k])
        cmp(f"{n}.{key} sdf-spec", si.find(key).text, L["diaginertia"][k])

    # geometry -- THE half/full extent trap, checked rather than assumed
    gid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"g_{n}")
    ubox = [float(v) for v in
            u_links[n].find("collision/geometry/box").get("size").split()]
    sbox = [float(v) for v in
            s_links[n].find("collision/geometry/box/size").text.split()]
    for k in range(3):
        cmp(f"{n}.halfsize mjcf-spec", m.geom_size[gid][k], L["half"][k])
        cmp(f"{n}.fullsize urdf = 2x mjcf", ubox[k], 2 * m.geom_size[gid][k])
        cmp(f"{n}.fullsize sdf  = 2x mjcf", sbox[k], 2 * m.geom_size[gid][k])

    if not L["axis"]:
        continue
    jn = f"j_{n}"
    jid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, jn)
    want_axis = np.array(AXIS_VEC[L["axis"]], dtype=float)

    for k in range(3):
        cmp(f"{jn}.axis[{k}] mjcf-spec", m.jnt_axis[jid][k], want_axis[k])
        cmp(f"{jn}.axis[{k}] urdf-spec",
            u_joints[jn].find("axis").get("xyz").split()[k], want_axis[k])
        cmp(f"{jn}.axis[{k}] sdf-spec",
            s_joints[jn].find("axis/xyz").text.split()[k], want_axis[k])

    lo, hi = L["limit"]
    cmp(f"{jn}.lower mjcf-spec", m.jnt_range[jid][0], lo, 1e-6)
    cmp(f"{jn}.upper mjcf-spec", m.jnt_range[jid][1], hi, 1e-6)
    ul = u_joints[jn].find("limit")
    cmp(f"{jn}.lower urdf-spec", ul.get("lower"), lo, 1e-6)
    cmp(f"{jn}.upper urdf-spec", ul.get("upper"), hi, 1e-6)
    sl = s_joints[jn].find("axis/limit")
    cmp(f"{jn}.lower sdf-spec", sl.find("lower").text, lo, 1e-6)
    cmp(f"{jn}.upper sdf-spec", sl.find("upper").text, hi, 1e-6)

    cmp(f"{jn}.damping mjcf-spec", m.dof_damping[jid], L["damping"])
    cmp(f"{jn}.damping urdf-spec",
        u_joints[jn].find("dynamics").get("damping"), L["damping"])
    cmp(f"{jn}.damping sdf-spec",
        s_joints[jn].find("axis/dynamics/damping").text, L["damping"])

    cmp(f"{jn}.frictionloss mjcf-spec", m.dof_frictionloss[jid], JOINT_FRICTION)
    cmp(f"{jn}.friction urdf-spec",
        u_joints[jn].find("dynamics").get("friction"), JOINT_FRICTION)
    cmp(f"{jn}.friction sdf-spec",
        s_joints[jn].find("axis/dynamics/friction").text, JOINT_FRICTION)


# ---------- independent FK from the URDF chain ----------
def rot(axis, q):
    c, s_ = np.cos(q), np.sin(q)
    if axis == "x": return np.array([[1,0,0],[0,c,-s_],[0,s_,c]])
    if axis == "y": return np.array([[c,0,s_],[0,1,0],[-s_,0,c]])
    return np.array([[c,-s_,0],[s_,c,0],[0,0,1]])


def fk_numpy(q):
    """Tip position from the URDF joint origins alone -- no MuJoCo involved."""
    T = np.eye(4)
    qi = 0
    for i, L in enumerate(SPEC):
        if L["axis"]:
            jn = f"j_{L['name']}"
            o = [float(v) for v in u_joints[jn].find("origin").get("xyz").split()]
            J = np.eye(4); J[:3, 3] = o
            T = T @ J
            R = np.eye(4); R[:3, :3] = rot(L["axis"], q[qi]); qi += 1
            T = T @ R
            # link frame is AT the joint; the body extends +half above it
            up = np.eye(4); up[2, 3] = L["half"][2]
            T = T @ up
        else:
            b = np.eye(4); b[:3, 3] = OFF[i]
            T = T @ b
    return T[:3, 3]          # T already sits at the last link's centre


rng = np.random.default_rng(0)
errs = []
site_body = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, SPEC[-1]["name"])
for _ in range(2000):
    q = np.array([rng.uniform(*L["limit"]) for L in SPEC if L["axis"]])
    d.qpos[:] = q
    mujoco.mj_forward(m, d)
    mj_tip = d.xpos[site_body].copy()      # MuJoCo body frame IS the centre
    errs.append(np.abs(fk_numpy(q) - mj_tip).max())

errs = np.array(errs)
out = {
  "cross_validation": {
     "comparisons": report["comparisons"],
     "mismatches": report["mismatches"],
     "worst_field": report["worst"][0],
     "worst_abs_diff": report["worst"][1]},
  "forward_kinematics": {
     "samples": len(errs),
     "max_abs_err_m": float(errs.max()),
     "mean_abs_err_m": float(errs.mean())},
  "conventions_checked": [
     "MJCF size is a HALF extent; URDF/SDF box size is the FULL extent",
     "inertia stated explicitly in all three, never compiler-inferred",
     "URDF joint origin offset by -half_length to sit at the child's lower face"],
}
json.dump(out, open(os.path.join(HERE, "validation.json"), "w"), indent=2)

print(f"cross-validation : {report['comparisons']} comparisons, "
      f"{len(report['mismatches'])} mismatches")
print(f"  worst field    : {report['worst'][0]}  diff {report['worst'][1]:.3e}")
print(f"forward kinematics: {len(errs)} random configs")
print(f"  max  abs error : {errs.max():.3e} m")
print(f"  mean abs error : {errs.mean():.3e} m")
if report["mismatches"]:
    print("\nMISMATCHES:")
    for x in report["mismatches"][:8]: print("  ", x)
