"""Render actual frames from the actual models, offscreen, as PNG data URIs.

There are no photographs of any of this -- the simulations ran headless on a
Kaggle T4 whose RTX renderer never initialised. What there IS is the models
themselves, and MuJoCo can rasterise them offscreen on the CPU. So the imagery
on the page is not stock footage or an illustration of a robot: it is the
robot, in the pose the study put it in, rendered from the same XML the physics
ran on.

Sequences are emitted as arrays of base64 PNGs and played back in JS. That is
a video in every way that matters here, and unlike an mp4 it needs no external
host, no codec, and stays inside the artifact CSP.
"""
import base64
import io
import os

import numpy as np
import mujoco
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
W, H = 300, 210

# every scene gets the same studio: a soft floor, two lights, no clutter
STUDIO = """
  <visual>
    <headlight ambient="0.5 0.5 0.5" diffuse="0.5 0.5 0.5" specular="0.1 0.1 0.1"/>
    <rgba haze="0.9 0.9 0.92 1"/>
    <global offwidth="640" offheight="480"/>
  </visual>
  <asset>
    <texture name="grid" type="2d" builtin="checker" rgb1="0.92 0.92 0.92"
             rgb2="0.82 0.82 0.82" width="300" height="300"/>
    <material name="grid" texture="grid" texrepeat="6 6" reflectance="0"/>
  </asset>
"""

FLOOR = ('<geom name="floor" type="plane" size="4 4 0.05" material="grid"/>'
         '<light pos="0.6 -0.6 1.6" dir="-0.4 0.4 -1" diffuse="0.7 0.7 0.7"/>'
         '<light pos="-0.8 0.5 1.2" dir="0.5 -0.3 -1" diffuse="0.35 0.35 0.35"/>')


def png_b64(px):
    im = Image.fromarray(px)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def camera(distance, azimuth, elevation, lookat):
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(cam)
    cam.distance, cam.azimuth, cam.elevation = distance, azimuth, elevation
    cam.lookat[:] = lookat
    return cam


def shoot(model, data, cam, w=W, h=H):
    r = mujoco.Renderer(model, height=h, width=w)
    r.update_scene(data, cam)
    px = r.render()
    r.close()
    return px


def sequence(xml, cam, steps, every, setup=None, ctrl=None, frames=40):
    """Step the model and grab a frame every `every` steps."""
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    if setup:
        setup(m, d)
    mujoco.mj_forward(m, d)
    r = mujoco.Renderer(m, height=H, width=W)
    out = []
    for i in range(steps):
        if ctrl:
            ctrl(m, d, i)
        mujoco.mj_step(m, d)
        if i % every == 0 and len(out) < frames:
            r.update_scene(d, cam)
            out.append(png_b64(r.render()))
    r.close()
    return out


def _studio(xml, floor_material=True):
    """Inject lights and a checkered floor material into an existing model."""
    lights = ('<light pos="0.7 -0.7 1.8" dir="-0.4 0.4 -1" diffuse="0.75 0.75 0.75"'
              ' castshadow="true"/>'
              '<light pos="-0.9 0.6 1.3" dir="0.5 -0.3 -1" diffuse="0.3 0.3 0.3"'
              ' castshadow="false"/>')
    xml = xml.replace("<worldbody>", STUDIO + "<worldbody>" + lights, 1)
    if floor_material:
        import re
        xml = re.sub(r'(<geom[^>]*type="plane"[^>]*)/>',
                     r'\1 material="grid"/>', xml, count=1)
    return xml


def arm_swing(frames=36):
    """The 3-DOF arm released from a raised pose and swinging under gravity.
    Real dynamics on the same XML every other study uses."""
    xml = _studio(open(os.path.join(REPO, "model", "arm3.xml")).read())
    cam = camera(1.5, 118, -18, [0.05, 0, 0.30])

    def setup(m, d):
        d.qpos[:3] = [0.9, -1.1, 1.3]

    return sequence(xml, cam, steps=frames * 14, every=14, setup=setup, frames=frames)


GRIP_XML = """
<mujoco model="pinch">
  <option timestep="0.0005" gravity="0 0 -9.81" cone="elliptic" integrator="implicitfast"/>
  <default><geom friction="0.4 0.005 0.0001" solref="0.004 1"/></default>
  <worldbody>
    <geom type="plane" size="2 2 0.05" pos="0 0 0"/>
    <body name="fL" pos="-0.05 0 0.42">
      <joint name="jL" type="slide" axis="1 0 0" damping="12"/>
      <geom type="box" size="0.012 0.035 0.045" mass="0.2" rgba="0.35 0.38 0.42 1"/>
    </body>
    <body name="fR" pos="0.05 0 0.42">
      <joint name="jR" type="slide" axis="-1 0 0" damping="12"/>
      <geom type="box" size="0.012 0.035 0.045" mass="0.2" rgba="0.35 0.38 0.42 1"/>
    </body>
    <body name="obj" pos="0 0 0.42">
      <freejoint/>
      <geom type="box" size="0.028 0.028 0.028" mass="0.5" rgba="0.87 0.23 0.25 1"/>
    </body>
  </worldbody>
  <actuator>
    <motor joint="jL" gear="1"/><motor joint="jR" gear="1"/>
  </actuator>
</mujoco>
"""


def grasp_pair(frames=34):
    """Two runs of the same grasp, one below the Coulomb threshold and one
    above it. F_min = m*g/(2*mu) = 6.13 N for this block; 4 N drops it, 9 N
    holds. The measured threshold was 6.44 N."""
    xml = _studio(GRIP_XML)
    cam = camera(0.62, 108, -12, [0, 0, 0.36])
    out = {}
    for label, force in (("slips", 4.0), ("holds", 9.0)):
        def ctrl(m, d, i, f=force):
            d.ctrl[:] = f
        out[label] = sequence(xml, cam, steps=frames * 26, every=26,
                              ctrl=ctrl, frames=frames)
    return out


STACK_XML = """
<mujoco>
  <option timestep="0.002" gravity="0 0 -9.81" iterations="{it}"/>
  <worldbody>
    <geom type="plane" size="2 2 0.05"/>
    <body name="light" pos="0 0 0.05"><freejoint/>
      <geom type="box" size="0.05 0.05 0.05" mass="1" rgba="0.20 0.56 0.80 1"/></body>
    <body name="heavy" pos="0 0 0.151"><freejoint/>
      <geom type="box" size="0.05 0.05 0.05" mass="{m}" rgba="0.87 0.23 0.25 1"/></body>
  </worldbody>
</mujoco>
"""


def stack_pair(frames=30):
    """Equal masses beside a 1000:1 ratio. The heavy block visibly drives the
    light one into the floor -- the failure mode the stability study measured
    as 50 mm of squash."""
    cam = camera(0.75, 112, -8, [0, 0, 0.10])
    out = {}
    for label, mass in (("ratio 1", 1.0), ("ratio 1000", 1000.0)):
        xml = _studio(STACK_XML.format(m=mass, it=100))
        out[label] = sequence(xml, cam, steps=frames * 10, every=10, frames=frames)
    return out


def grasp_slider(forces=(3.0, 4.5, 6.0, 6.5, 7.5, 10.0), frames=24):
    """One rendered sequence per grip force, so the slider on the page is
    backed by real MuJoCo runs rather than a JavaScript re-implementation.
    The closed form says F_min = m*g/(2*mu) = 6.13 N; measured 6.44 N.
    """
    xml = _studio(GRIP_XML)
    cam = camera(0.62, 108, -12, [0, 0, 0.36])
    out = {}
    for f in forces:
        def ctrl(m, d, i, ff=f):
            d.ctrl[:] = ff
        out[f"{f:g}"] = sequence(xml, cam, steps=frames * 30, every=30,
                                 ctrl=ctrl, frames=frames)
    return out


def stack_slider(ratios=(1, 10, 100, 1000), frames=22):
    """One sequence per mass ratio. The light block is 1 kg throughout."""
    cam = camera(0.75, 112, -8, [0, 0, 0.10])
    out = {}
    for r in ratios:
        xml = _studio(STACK_XML.format(m=float(r), it=100))
        out[str(r)] = sequence(xml, cam, steps=frames * 11, every=11, frames=frames)
    return out
