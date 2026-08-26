"""Emit MJCF, URDF and SDF from robot_spec. One source, three files."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robot_spec import build, link_frame_offsets, AXIS_VEC, JOINT_FRICTION, CONTACT_MU

L = build()
OFF = link_frame_offsets(L)


def mjcf():
    s = ['<mujoco model="arm3">',
         '  <compiler angle="radian"/>',
         '  <option timestep="0.002" gravity="0 0 -9.81" integrator="RK4"/>',
         '  <worldbody>',
         '    <geom name="floor" type="plane" size="5 5 .1" friction="%g 0 0"/>' % CONTACT_MU]
    ind = "    "
    open_bodies = 0
    for i, lk in enumerate(L):
        hx, hy, hz = lk["half"]
        ox, oy, oz = OFF[i]
        s.append(f'{ind}<body name="{lk["name"]}" pos="{ox:g} {oy:g} {oz:g}">')
        ind += "  "; open_bodies += 1
        # inertial stated EXPLICITLY -- never let the compiler infer it, or the
        # three formats will disagree the moment a geom changes.
        ixx, iyy, izz = lk["diaginertia"]
        s.append(f'{ind}<inertial pos="0 0 0" mass="{lk["mass"]:.9g}" '
                 f'diaginertia="{ixx:.9g} {iyy:.9g} {izz:.9g}"/>')
        if lk["axis"]:
            ax = " ".join(str(v) for v in AXIS_VEC[lk["axis"]])
            lo, hi = lk["limit"]
            s.append(f'{ind}<joint name="j_{lk["name"]}" type="hinge" axis="{ax}" '
                     f'pos="0 0 {-hz:g}" range="{lo:.6g} {hi:.6g}" '
                     f'damping="{lk["damping"]:g}" frictionloss="{JOINT_FRICTION:g}"/>')
        # MJCF size is a HALF-extent
        s.append(f'{ind}<geom name="g_{lk["name"]}" type="box" '
                 f'size="{hx:g} {hy:g} {hz:g}" friction="{CONTACT_MU:g} 0 0"/>')
    for _ in range(open_bodies):
        ind = ind[:-2]; s.append(f'{ind}</body>')
    s += ['  </worldbody>', '</mujoco>']
    return "\n".join(s)


def _inertia_xml(lk, pad, zc=0.0):
    ixx, iyy, izz = lk["diaginertia"]
    return (f'{pad}<inertial>\n'
            f'{pad}  <origin xyz="0 0 {zc:g}" rpy="0 0 0"/>\n'
            f'{pad}  <mass value="{lk["mass"]:.9g}"/>\n'
            f'{pad}  <inertia ixx="{ixx:.9g}" ixy="0" ixz="0" '
            f'iyy="{iyy:.9g}" iyz="0" izz="{izz:.9g}"/>\n'
            f'{pad}</inertial>')


def urdf():
    s = ['<?xml version="1.0"?>', '<robot name="arm3">']
    for i, lk in enumerate(L):
        lx, ly, lz = lk["size"]          # URDF box size is the FULL extent
        # link frame sits at the JOINT; body centre is half a length above it
        zc = 0.0 if i == 0 else lk["half"][2]
        s.append(f'  <link name="{lk["name"]}">')
        s.append(_inertia_xml(lk, "    ", zc))
        for tag in ("visual", "collision"):
            s.append(f'    <{tag}>')
            s.append(f'      <origin xyz="0 0 {zc:g}" rpy="0 0 0"/>')
            s.append(f'      <geometry><box size="{lx:g} {ly:g} {lz:g}"/></geometry>')
            s.append(f'    </{tag}>')
        s.append('  </link>')
    for i, lk in enumerate(L):
        if not lk["axis"]:
            continue
        ox, oy, oz = OFF[i]
        hz = lk["half"][2]
        ax = " ".join(str(v) for v in AXIS_VEC[lk["axis"]])
        lo, hi = lk["limit"]
        s += [f'  <joint name="j_{lk["name"]}" type="revolute">',
              f'    <parent link="{L[i-1]["name"]}"/>',
              f'    <child link="{lk["name"]}"/>',
              # URDF joint origin is parent->child; the joint sits at the
              # child's lower face, so shift by -hz relative to the body pos.
              f'    <origin xyz="{ox:g} {oy:g} {oz - hz:g}" rpy="0 0 0"/>',
              f'    <axis xyz="{ax}"/>',
              f'    <limit lower="{lo:.6g}" upper="{hi:.6g}" effort="150" velocity="6"/>',
              f'    <dynamics damping="{lk["damping"]:g}" friction="{JOINT_FRICTION:g}"/>',
              '  </joint>']
    s.append('</robot>')
    return "\n".join(s)


def sdf():
    s = ['<?xml version="1.0"?>', '<sdf version="1.9">', '  <model name="arm3">']
    z = 0.0
    for i, lk in enumerate(L):
        lx, ly, lz = lk["size"]
        z += OFF[i][2]
        s.append(f'    <link name="{lk["name"]}">')
        s.append(f'      <pose>0 0 {z:g} 0 0 0</pose>')
        ixx, iyy, izz = lk["diaginertia"]
        s += [f'      <inertial><mass>{lk["mass"]:.9g}</mass>',
              f'        <inertia><ixx>{ixx:.9g}</ixx><ixy>0</ixy><ixz>0</ixz>',
              f'        <iyy>{iyy:.9g}</iyy><iyz>0</iyz><izz>{izz:.9g}</izz></inertia>',
              '      </inertial>']
        for tag in ("visual", "collision"):
            s += [f'      <{tag} name="{tag}_{lk["name"]}">',
                  f'        <geometry><box><size>{lx:g} {ly:g} {lz:g}</size></box></geometry>',
                  f'      </{tag}>']
        s.append('    </link>')
    for i, lk in enumerate(L):
        if not lk["axis"]:
            continue
        ax = " ".join(str(v) for v in AXIS_VEC[lk["axis"]])
        lo, hi = lk["limit"]
        s += [f'    <joint name="j_{lk["name"]}" type="revolute">',
              f'      <parent>{L[i-1]["name"]}</parent>',
              f'      <child>{lk["name"]}</child>',
              f'      <axis><xyz>{ax}</xyz>',
              f'        <limit><lower>{lo:.6g}</lower><upper>{hi:.6g}</upper></limit>',
              f'        <dynamics><damping>{lk["damping"]:g}</damping>'
              f'<friction>{JOINT_FRICTION:g}</friction></dynamics>',
              '      </axis>', '    </joint>']
    s += ['  </model>', '</sdf>']
    return "\n".join(s)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    for name, fn in (("arm3.xml", mjcf), ("arm3.urdf", urdf), ("arm3.sdf", sdf)):
        p = os.path.join(here, name)
        open(p, "w").write(fn() + "\n")
        print(f"  wrote {name:<12} {os.path.getsize(p):>6} bytes")
