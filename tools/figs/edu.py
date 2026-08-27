"""Explanatory diagrams for the guide.

These teach rather than report. charts.py plots things that were measured;
everything here draws a concept, so the numbers in them are illustrative and
the captions say so. Same visual language as the rest of the site: hairline
rules, mono labels, the Apple stripe palette through CSS custom properties.
"""
import math

from charts import frame, txt, esc   # noqa: F401


def sim_loop():
    """What a physics engine actually does, once per timestep.

    Almost every interview question about simulators is really a question
    about one of these five boxes, so it is worth being able to draw it.
    """
    W, H = 520, 330
    cx, cy, R = W / 2, H / 2 + 4, 108
    steps = [("1. FORWARD\nDYNAMICS", "torques and gravity\nbecome accelerations"),
             ("2. COLLISION\nDETECTION", "which shapes are\ntouching, and where"),
             ("3. CONSTRAINT\nSOLVE", "find contact forces that\nstop interpenetration"),
             ("4. INTEGRATE", "accelerations become\nvelocities and positions"),
             ("5. SENSORS", "read out what the\nrobot can observe")]
    out = []
    n = len(steps)
    for i, (title, _) in enumerate(steps):
        a = -math.pi / 2 + i * 2 * math.pi / n
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        a2 = -math.pi / 2 + (i + 1) * 2 * math.pi / n
        x2, y2 = cx + R * math.cos(a2), cy + R * math.sin(a2)
        # arc-ish connector
        mx, my = (x + x2) / 2, (y + y2) / 2
        k = 1.22
        out.append(f'<path d="M {x:.1f},{y:.1f} Q {cx+(mx-cx)*k:.1f},'
                   f'{cy+(my-cy)*k:.1f} {x2:.1f},{y2:.1f}" class="link" fill="none"/>')
    for i, (title, sub) in enumerate(steps):
        a = -math.pi / 2 + i * 2 * math.pi / n
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="13" class="node"/>')
        out.append(txt(x, y + 4, str(i + 1), "figtitle", "middle"))
        lx = x + (34 if math.cos(a) > 0.1 else (-34 if math.cos(a) < -0.1 else 0))
        anc = "start" if math.cos(a) > 0.1 else ("end" if math.cos(a) < -0.1 else "middle")
        for j, line in enumerate(title.split("\n")):
            out.append(txt(lx, y - 4 + j * 11, line, "figtitle", anc))
    out.append(txt(cx, cy - 6, "ONE", "cap", "middle"))
    out.append(txt(cx, cy + 8, "TIMESTEP", "figtitle", "middle"))
    out.append(txt(cx, cy + 24, "1-4 ms", "tick", "middle"))
    out.append(txt(cx, H - 6, "every simulator does these five things, in this order",
                   "cap", "middle"))
    return frame(W, H, "".join(out), "The five stages of one simulation timestep")


def joint_types():
    """The three joints that cover almost every robot you will be handed."""
    W, H = 520, 210
    out = []
    panels = [("REVOLUTE", "hinge. 1 DOF.\nelbows, knees"),
              ("PRISMATIC", "slider. 1 DOF.\ngantries, grippers"),
              ("BALL", "3 DOF at once.\nshoulders, hips")]
    for i, (name, desc) in enumerate(panels):
        ox = 20 + i * 170
        cy = 92
        out.append(f'<rect x="{ox}" y="34" width="150" height="120" class="lane"/>')
        out.append(txt(ox + 75, 26, name, "figtitle", "middle"))
        if i == 0:
            out.append(f'<line x1="{ox+30}" y1="{cy}" x2="{ox+75}" y2="{cy}" class="link"/>')
            out.append(f'<line x1="{ox+75}" y1="{cy}" x2="{ox+112}" y2="{cy-30}" class="series-a"/>')
            out.append(f'<path d="M {ox+100},{cy} A 25,25 0 0,0 {ox+94},{cy-19}" '
                       f'class="series-warn" fill="none"/>')
            out.append(f'<circle cx="{ox+75}" cy="{cy}" r="7" class="node"/>')
        elif i == 1:
            out.append(f'<line x1="{ox+25}" y1="{cy}" x2="{ox+125}" y2="{cy}" class="link"/>')
            out.append(f'<rect x="{ox+58}" y="{cy-11}" width="26" height="22" class="node"/>')
            out.append(f'<line x1="{ox+92}" y1="{cy}" x2="{ox+118}" y2="{cy}" class="series-warn"/>')
            out.append(f'<path d="M {ox+112},{cy-5} L {ox+120},{cy} L {ox+112},{cy+5}" '
                       f'class="series-warn" fill="none"/>')
        else:
            out.append(f'<circle cx="{ox+75}" cy="{cy}" r="17" class="node"/>')
            for a in (0, 60, 120):
                r = math.radians(a)
                out.append(f'<ellipse cx="{ox+75}" cy="{cy}" rx="26" ry="9" '
                           f'transform="rotate({a} {ox+75} {cy})" class="series-a" fill="none"/>')
        for j, line in enumerate(desc.split("\n")):
            out.append(txt(ox + 75, 172 + j * 12, line, "cap", "middle"))
    return frame(W, H, "".join(out), "Revolute, prismatic and ball joints")


def dof_ladder():
    """Degrees of freedom, counted the way an interviewer will ask you to."""
    W, H = 520, 200
    rows = [("a free-floating rigid body", 6, "3 move + 3 rotate"),
            ("a 6-axis industrial arm", 6, "one per revolute joint"),
            ("a quadruped like Spot", 18, "12 leg joints + 6 floating base"),
            ("a humanoid", 30, "varies, plus the floating base")]
    L, T = 250, 46
    bw = 230
    out = [txt(20, 26, "HOW MANY NUMBERS DESCRIBE THE POSE?", "figtitle")]
    vmax = 32
    for i, (name, dof, note) in enumerate(rows):
        y = T + i * 34
        out.append(txt(L - 12, y + 12, name, "tick", "end"))
        w = dof / vmax * bw
        out.append(f'<rect x="{L}" y="{y}" width="{w:.0f}" height="17" class="bar-b"/>')
        out.append(txt(L + w + 8, y + 13, f"{dof}", "barval"))
        out.append(txt(L, y + 30, note, "cap"))
    out.append(txt(20, H - 8,
                   "a floating base is 6 free DOF nobody actuates -- that is why walking is hard",
                   "cap"))
    return frame(W, H, "".join(out), "Degrees of freedom for common robots")


def friction_cone_explainer():
    """Why friction is a CONE, and what the polygon approximation costs."""
    W, H = 520, 250
    out = []
    for panel, ox in (("EXACT: A CONE", 30), ("APPROXIMATED: A PYRAMID", 280)):
        cx, base = ox + 100, 190
        out.append(txt(cx, 26, panel, "figtitle", "middle"))
        out.append(f'<line x1="{ox+20}" y1="{base}" x2="{ox+180}" y2="{base}" class="axis"/>')
        out.append(f'<line x1="{cx}" y1="{base}" x2="{cx}" y2="{base-92}" class="series-a"/>')
        out.append(txt(cx + 8, base - 86, "normal force", "key-a"))
        if ox < 200:
            out.append(f'<path d="M {cx-62},{base-92} L {cx},{base} L {cx+62},{base-92}" '
                       f'class="series-ok" fill="none"/>')
            out.append(f'<ellipse cx="{cx}" cy="{base-92}" rx="62" ry="16" '
                       f'class="series-ok" fill="none"/>')
            out.append(txt(cx, base - 118, "any direction: same limit", "key-ok", "middle"))
        else:
            pts = []
            for k in range(4):
                a = math.radians(45 + k * 90)
                pts.append((cx + 62 * math.cos(a), base - 92 + 16 * math.sin(a)))
            d = "M " + " L ".join(f"{x:.0f},{y:.0f}" for x, y in pts) + " Z"
            out.append(f'<path d="{d}" class="series-warn" fill="none"/>')
            for x, y in pts:
                out.append(f'<line x1="{cx}" y1="{base}" x2="{x:.0f}" y2="{y:.0f}" '
                           f'class="series-warn"/>')
            out.append(txt(cx, base - 118, "corners have MORE grip", "key-warn", "middle"))
        out.append(txt(cx, base + 20, "mu x normal force", "cap", "middle"))
    out.append(txt(W / 2, H - 8,
                   "the pyramid is cheaper in some solvers -- in MuJoCo it is not",
                   "cap", "middle"))
    return frame(W, H, "".join(out), "Exact friction cone beside its pyramid approximation")


def pd_control():
    """A PD controller, drawn as the block diagram an interviewer expects."""
    W, H = 520, 200
    out = []
    y = 92
    boxes = [("TARGET", 20, 78), ("+", 118, 26), ("kp e + kd e'", 168, 108),
             ("ROBOT", 300, 78), ("STATE", 410, 78)]
    for name, x, w in boxes:
        if name == "+":
            out.append(f'<circle cx="{x+13}" cy="{y}" r="13" class="node"/>')
            out.append(txt(x + 13, y + 5, "-", "figtitle", "middle"))
        else:
            out.append(f'<rect x="{x}" y="{y-19}" width="{w}" height="38" class="node"/>')
            out.append(txt(x + w / 2, y + 5, name, "figtitle", "middle"))
    for x1, x2 in ((98, 118), (144, 168), (276, 300), (378, 410)):
        out.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" class="link"/>')
        out.append(f'<path d="M {x2-7},{y-4} L {x2},{y} L {x2-7},{y+4}" class="link" fill="none"/>')
    out.append(f'<path d="M {450},{y+19} L {450},{y+52} L {131},{y+52} L {131},{y+13}" '
               f'class="series-warn" fill="none"/>')
    out.append(txt(290, y + 66, "feedback: subtract where it actually is", "key-warn", "middle"))
    out.append(txt(20, 26, "PD CONTROL -- THE CONTROLLER YOU WILL BE ASKED ABOUT", "figtitle"))
    out.append(txt(20, H - 10,
                   "kp pulls toward the target;  kd resists speed and damps the wobble",
                   "cap"))
    return frame(W, H, "".join(out), "A PD control loop as a block diagram")


def sim2real():
    """The gap, and the four things that cause it."""
    W, H = 520, 240
    out = []
    out.append(f'<rect x="30" y="50" width="170" height="70" class="lane"/>')
    out.append(txt(115, 80, "SIMULATION", "figtitle", "middle"))
    out.append(txt(115, 98, "clean, repeatable", "cap", "middle"))
    out.append(f'<rect x="320" y="50" width="170" height="70" class="lane"/>')
    out.append(txt(405, 80, "REAL ROBOT", "figtitle", "middle"))
    out.append(txt(405, 98, "noisy, worn, hot", "cap", "middle"))
    out.append(f'<line x1="205" y1="85" x2="315" y2="85" class="marker"/>')
    out.append(txt(260, 74, "THE GAP", "key-warn", "middle"))
    causes = [("mass and inertia are guesses", 0), ("friction is not one number", 1),
              ("actuators lag and saturate", 2), ("sensors are noisy and delayed", 3)]
    for text, i in causes:
        y = 150 + i * 21
        out.append(f'<rect x="34" y="{y-9}" width="9" height="9" class="bar-warn"/>')
        out.append(txt(52, y, text, "tick"))
    out.append(txt(300, 150, "FIXES", "figtitle"))
    for text, i in (("system identification", 0), ("domain randomisation", 1),
                    ("actuator models", 2), ("sensor noise models", 3)):
        y = 168 + i * 18
        out.append(f'<rect x="300" y="{y-8}" width="8" height="8" class="bar-b"/>')
        out.append(txt(316, y, text, "tick"))
    out.append(txt(20, 30, "SIM-TO-REAL: WHY THE ROBOT FALLS OVER OUTSIDE", "figtitle"))
    return frame(W, H, "".join(out), "The sim-to-real gap, its causes and its fixes")


def simulator_picker():
    """Which simulator, and why. The comparison question is near-guaranteed."""
    W, H = 520, 250
    cols = [("MuJoCo", ["contact-rich", "fast on CPU", "research default",
                        "MJX = GPU"], "bar-b"),
            ("Isaac Sim", ["photoreal sensors", "GPU, 1000s of envs",
                           "USD scenes", "heavy install"], "bar-a"),
            ("Gazebo", ["ROS-native", "plugins for sensors",
                        "classic robotics", "slower physics"], "bar-warn")]
    out = [txt(20, 24, "PICK BY WHAT THE JOB NEEDS", "figtitle")]
    for i, (name, bullets, cls) in enumerate(cols):
        ox = 20 + i * 168
        out.append(f'<rect x="{ox}" y="40" width="150" height="180" class="lane"/>')
        out.append(f'<rect x="{ox}" y="40" width="150" height="26" class="{cls}"/>')
        out.append(txt(ox + 75, 58, name, "figtitle", "middle"))
        for j, b in enumerate(bullets):
            out.append(f'<rect x="{ox+12}" y="{84+j*30-7}" width="7" height="7" class="node"/>')
            out.append(txt(ox + 26, 84 + j * 30, b, "tick"))
    out.append(txt(20, H - 8,
                   "all three are on this repo's CV -- say which you would choose and why",
                   "cap"))
    return frame(W, H, "".join(out), "Choosing between MuJoCo, Isaac Sim and Gazebo")
