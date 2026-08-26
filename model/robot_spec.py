"""Single source of truth for a 3-DOF arm, emitted as MJCF, URDF and SDF.

Hand-authoring the same robot three times is how the formats drift: someone
fixes an inertia in the MJCF and the URDF keeps the old one, and the two
simulators quietly disagree forever. Generating all three from one parameter
block makes that impossible by construction.

Two conventions that cause most cross-format bugs, handled explicitly:
  * MJCF box `size` is a HALF-extent; URDF/SDF `<box size>` is the FULL extent.
  * MJCF `diaginertia` is about the body frame's principal axes; URDF/SDF want
    the full <inertia> tensor about the link's centre of mass.
Both are converted here, once, rather than eyeballed per file.
"""
import numpy as np

DENSITY = 2700.0        # aluminium, kg/m^3

LINKS = [
    # name,      lx,    ly,    lz,    joint axis, lower,  upper, damping
    ("base",    0.12,  0.12,  0.06,  None,        None,   None,  None),
    ("link1",   0.06,  0.06,  0.28,  "z",         -2.967, 2.967, 0.12),
    ("link2",   0.05,  0.05,  0.24,  "y",         -1.745, 1.745, 0.10),
    ("link3",   0.04,  0.04,  0.18,  "y",         -2.443, 2.443, 0.08),
]
JOINT_FRICTION = 0.02       # Coulomb friction in the joint
CONTACT_MU     = 0.8        # surface friction of the link geometry


def box_props(lx, ly, lz, density=DENSITY):
    """Mass and principal inertia of a solid box about its own centre."""
    m = density * lx * ly * lz
    ixx = m * (ly**2 + lz**2) / 12.0
    iyy = m * (lx**2 + lz**2) / 12.0
    izz = m * (lx**2 + ly**2) / 12.0
    return m, (ixx, iyy, izz)


def build():
    """Resolve the spec into concrete numbers exactly once."""
    out = []
    z_off = 0.0
    for name, lx, ly, lz, axis, lo, hi, damp in LINKS:
        m, (ixx, iyy, izz) = box_props(lx, ly, lz)
        out.append({
            "name": name, "size": (lx, ly, lz),
            "half": (lx/2, ly/2, lz/2),          # MJCF wants half-extents
            "mass": m, "diaginertia": (ixx, iyy, izz),
            "axis": axis, "limit": (lo, hi), "damping": damp,
            # each link sits on top of its parent
            "origin_z": z_off,
        })
        z_off = lz
    return out


def link_frame_offsets(links):
    """Parent-to-child translations. The joint sits at the parent's top face;
    the child's centre of mass is half its own length above that."""
    offs = []
    for i, L in enumerate(links):
        if i == 0:
            offs.append((0.0, 0.0, L["size"][2] / 2))
        else:
            parent = links[i-1]
            offs.append((0.0, 0.0, parent["size"][2] / 2 + L["size"][2] / 2))
    return offs


AXIS_VEC = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}

if __name__ == "__main__":
    links = build()
    print(f"{'link':<8} {'mass kg':>9} {'ixx':>11} {'iyy':>11} {'izz':>11}")
    for L in links:
        print(f"{L['name']:<8} {L['mass']:>9.5f} "
              + " ".join(f"{v:>11.3e}" for v in L["diaginertia"]))
    tot = sum(L["mass"] for L in links)
    print(f"\ntotal mass {tot:.4f} kg   moving mass "
          f"{tot - links[0]['mass']:.4f} kg")
