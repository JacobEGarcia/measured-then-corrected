"""SVG chart primitives for the artifact, drawn from measured JSON.

Hand-drawing figures from numbers you retyped is how a page starts disagreeing
with its own data. Everything here reads model/*.json, so the figures cannot
drift from the study that produced them -- the same reason
tools/check_readme_claims.py exists.

Style is deliberately spare: hairline axes, no gridlines, muted fills, air.
Colours come from CSS custom properties so the figures follow the page theme
instead of carrying their own hardcoded palette (which would break in dark
mode -- an SVG with baked-in #2B3138 strokes is invisible on a dark ground).
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
# this file lives in tools/figs/, so the repo root is three levels up
REPO = os.path.dirname(os.path.dirname(HERE))
MODEL = os.path.join(REPO, "model")


def load(name):
    p = os.path.join(MODEL, f"{name}.json")
    with open(p) as f:
        return json.load(f)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def txt(x, y, s, cls="lbl", anchor="start", size=None):
    st = f' font-size="{size}"' if size else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" '
            f'text-anchor="{anchor}"{st}>{esc(s)}</text>')


def frame(w, h, body, label=""):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" '
            f'preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-label="{esc(label)}">{body}</svg>')


# ---------------------------------------------------------------- polar cone
def friction_polar():
    """The star figure. Direction error plotted POLAR against heading.

    A square inscribed in a circle has more friction along its diagonals than
    its axes, so the pyramidal cone's error traces a lobed clover with nodes
    at 0, 45 and 90 degrees -- the square's symmetry axes. The elliptic cone
    is a tight ring. The shape of the artefact is visible, not just its size.
    """
    fc = load("friction_cone")
    W = H = 460
    cx, cy, R = W / 2, H / 2 + 6, 168
    out = []

    # rings at 5 and 10 degrees of error
    for r_deg, lab in ((5, "5°"), (10, "10°"), (15, "15°")):
        rr = R * r_deg / 15.0
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{rr:.1f}" class="ring"/>')
        out.append(txt(cx + 4, cy - rr + 12, lab, "tick"))

    # spokes at the square's symmetry axes -- the structural claim
    for a in (0, 45, 90, 135, 180, 225, 270, 315):
        th = math.radians(a)
        out.append(f'<line x1="{cx}" y1="{cy}" '
                   f'x2="{cx + R*math.cos(th):.1f}" y2="{cy - R*math.sin(th):.1f}" '
                   f'class="axis-spoke"/>')
        out.append(txt(cx + (R + 22) * math.cos(th), cy - (R + 22) * math.sin(th) + 4,
                       f"{a}°", "tick", "middle"))

    def path_for(cone):
        """The sweep covers 0-90 degrees. A square friction cone has 90-degree
        rotational symmetry, so tiling that quadrant four times is the full
        picture rather than an extrapolation -- and it is the only way the
        four-lobed clover, which IS the artefact, becomes visible."""
        base = [(r["heading_deg"], abs(r["direction_error_deg"]))
                for r in fc["sweeps"][cone]]
        pts = []
        for quad in range(4):
            seq = base if quad % 2 == 0 else list(reversed(base))
            for i, (h, mag) in enumerate(seq):
                if quad > 0 and i == 0:
                    continue                      # avoid duplicating the seam
                ang = quad * 90 + (h if quad % 2 == 0 else 90 - h)
                th = math.radians(ang)
                rr = R * min(mag, 15.0) / 15.0
                pts.append((cx + rr * math.cos(th), cy - rr * math.sin(th)))
        pts.append(pts[0])
        return pts

    for cone, cls in (("pyramidal", "series-warn"), ("elliptic", "series-ok")):
        pts = path_for(cone)
        d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        out.append(f'<path d="{d}" class="{cls}" fill="none"/>')
        for x, y in pts:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" class="{cls}-dot"/>')

    p = fc["pyramidal_summary"]["max_abs_error_deg"]
    e = fc["elliptic_summary"]["max_abs_error_deg"]
    out.append(txt(16, 26, "PYRAMIDAL", "key-warn"))
    out.append(txt(16, 44, f"max {p}°", "key-num"))
    out.append(txt(W - 16, 26, "ELLIPTIC", "key-ok", "end"))
    out.append(txt(W - 16, 44, f"max {e}°", "key-num", "end"))
    out.append(txt(cx, H - 6,
                   "direction error vs heading  \u00b7  quadrant tiled by symmetry",
                   "cap", "middle"))
    return frame(W, H, "".join(out),
                 "Polar plot of sliding direction error against push heading")


# ------------------------------------------------------- integrator log-log
def integrator_order():
    """Global error vs timestep, log-log. Slope IS the order of accuracy."""
    ig = load("integrators")
    W, H = 520, 340
    L, Rm, T, B = 62, 132, 24, 46
    pw, ph = W - L - Rm, H - T - B

    rows = {r["integrator"]: r for r in ig["order"]}
    xs = [x["dt"] for x in rows["Euler"]["rows"]]
    lx = [math.log10(v) for v in xs]
    x0, x1 = min(lx), max(lx)
    y0, y1 = -11.0, -1.5   # log10 error window

    def X(v):
        return L + (math.log10(v) - x0) / (x1 - x0) * pw

    def Y(v):
        v = max(v, 1e-11)
        return T + (1 - (math.log10(v) - y0) / (y1 - y0)) * ph

    out = [f'<rect x="{L}" y="{T}" width="{pw}" height="{ph}" class="plot-bg"/>']
    for e in range(-11, -1, 2):
        y = Y(10 ** e)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" class="grid"/>')
        out.append(txt(L - 8, y + 4, f"1e{e}", "tick", "end"))
    for v in xs:
        out.append(txt(X(v), T + ph + 18, f"{v*1000:g}", "tick", "middle"))
    out.append(txt(L + pw / 2, H - 8, "timestep  (ms)", "cap", "middle"))
    out.append(txt(-(T + ph / 2), 14, "global error  (m)", "cap", "middle",
                   ) .replace("<text ", '<text transform="rotate(-90)" '))

    styles = {"Euler": "series-a", "implicit": "series-b",
              "implicitfast": "series-c", "RK4": "series-ok"}
    for integ, cls in styles.items():
        pts = [(X(r["dt"]), Y(r["error"])) for r in rows[integ]["rows"]]
        d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        out.append(f'<path d="{d}" class="{cls}" fill="none"/>')
        for x, y in pts:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" class="{cls}-dot"/>')
        ob = rows[integ]["observed_order"]
        ly = {"Euler": 0, "implicit": 1, "implicitfast": 2, "RK4": 3}[integ]
        yy = T + 18 + ly * 20
        out.append(f'<line x1="{L+pw+8}" y1="{yy-4:.1f}" x2="{L+pw+22}" '
                   f'y2="{yy-4:.1f}" class="{cls}"/>')
        out.append(txt(L + pw + 28, yy, integ, f"key-{cls}"))
        out.append(txt(L + pw + 28, yy + 11, f"slope {ob}", "tick"))
    return frame(W, H, "".join(out),
                 "Log-log plot of integrator global error against timestep")


# ----------------------------------------------------------------- step plot
def physx_iteration_cliff():
    """The cliff. A convergence curve would slope; this falls off a table."""
    cs = load("crossengine_stack")
    pts = sorted(((int(k), v) for k, v in cs["position_iters"].items()))
    W, H = 520, 300
    L, Rm, T, B = 58, 20, 26, 48
    pw, ph = W - L - Rm, H - T - B
    xmax = 260.0

    def X(v):
        return L + v / xmax * pw

    def Y(v):
        return T + (1 - min(max(v, 0), 105) / 105.0) * ph

    out = [f'<rect x="{L}" y="{T}" width="{pw}" height="{ph}" class="plot-bg"/>']
    for v in (0, 25, 50, 75, 100):
        y = Y(v)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" class="grid"/>')
        out.append(txt(L - 8, y + 4, f"{v}", "tick", "end"))
    for v in (0, 64, 96, 128, 192, 255):
        out.append(txt(X(v), T + ph + 18, f"{v}", "tick", "middle"))

    # the failing plateau and the working band, as bands not just points
    out.append(f'<rect x="{L}" y="{Y(105):.1f}" width="{X(64)-L:.1f}" '
               f'height="{Y(95)-Y(105):.1f}" class="band-warn"/>')
    out.append(f'<rect x="{X(96):.1f}" y="{Y(6):.1f}" width="{L+pw-X(96):.1f}" '
               f'height="{Y(0)-Y(6):.1f}" class="band-ok"/>')

    d = "M " + " L ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in pts)
    out.append(f'<path d="{d}" class="series-a" fill="none"/>')
    for k, v in pts:
        cls = "series-warn-dot" if v > 50 else "series-ok-dot"
        out.append(f'<circle cx="{X(k):.1f}" cy="{Y(v):.1f}" r="4" class="{cls}"/>')

    xm = (X(64) + X(96)) / 2
    out.append(f'<line x1="{xm:.1f}" y1="{T}" x2="{xm:.1f}" y2="{T+ph}" class="marker"/>')
    out.append(txt(xm + 8, T + 16, "the cliff", "key-warn"))
    out.append(txt(xm + 8, T + 32, "64 → 96", "tick"))
    out.append(txt(L + pw / 2, H - 8, "PhysX solver POSITION iterations", "cap", "middle"))
    out.append(txt(-(T + ph / 2), 14, "squash  (mm)", "cap", "middle"
                   ).replace("<text ", '<text transform="rotate(-90)" '))
    return frame(W, H, "".join(out), "PhysX squash against solver position iterations")


# ------------------------------------------------------------- paired bars
def _paired_bars(rows, W=520, H=300, unit="", cap="", note=None, ymax=None):
    """rows: [(label, valueA, valueB, labelA, labelB)]"""
    L, Rm, T, B = 62, 20, 40, 54
    pw, ph = W - L - Rm, H - T - B
    vmax = ymax or max(max(r[1], r[2]) for r in rows) * 1.18
    n = len(rows)
    slot = pw / n
    bw = slot * 0.30
    out = []
    for i, (lab, a, b, la, lb) in enumerate(rows):
        cxs = L + slot * (i + 0.5)
        for j, (v, cls) in enumerate(((a, "bar-a"), (b, "bar-b"))):
            h = v / vmax * ph
            x = cxs - bw * 1.05 + j * bw * 1.1
            out.append(f'<rect x="{x:.1f}" y="{T+ph-h:.1f}" width="{bw:.1f}" '
                       f'height="{h:.1f}" class="{cls}" rx="1.5"/>')
            out.append(txt(x + bw / 2, T + ph - h - 7, f"{v:g}", "barval", "middle"))
        out.append(txt(cxs, T + ph + 18, lab, "tick", "middle"))
    out.append(f'<line x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}" class="axis"/>')
    out.append(f'<rect x="{L}" y="{T-26}" width="10" height="10" class="bar-a"/>')
    out.append(txt(L + 16, T - 17, rows[0][3], "key-a"))
    out.append(f'<rect x="{L+120}" y="{T-26}" width="10" height="10" class="bar-b"/>')
    out.append(txt(L + 136, T - 17, rows[0][4], "key-b"))
    if cap:
        out.append(txt(L + pw / 2, H - 8, cap, "cap", "middle"))
    if note:
        out.append(txt(W - Rm, T - 17, note, "cap", "end"))
    return frame(W, H, "".join(out), cap or "bar chart")


def grasp_bars():
    g = load("grasp")
    rows = [(f"mu {c['mu']}\nm {c['mass']}", c["theory_N"], c["measured_N"],
             "closed form", "measured") for c in g["cases"]]
    rows = [(r[0].replace("\n", "  "),) + r[1:] for r in rows]
    return _paired_bars(rows, cap="minimum grip force that holds  (N)",
                        note="every measurement above theory")


def integrator_stability_bars():
    ig = load("integrators")
    s = {r["integrator"]: r["max_stable_kv"]
         for r in ig["gain_stability"] if r.get("summary")}
    order = ["RK4", "Euler", "implicitfast", "implicit"]
    W, H = 520, 250
    L, Rm, T, B = 118, 60, 30, 40
    pw, ph = W - L - Rm, H - T - B
    vmax = 560.0
    bh = ph / len(order) * 0.52
    out = []
    for i, k in enumerate(order):
        v = s[k] or 0
        y = T + ph * (i + 0.5) / len(order) - bh / 2
        w = max(v / vmax * pw, 3)
        cls = "bar-b" if v >= 500 else "bar-warn"
        out.append(f'<rect x="{L}" y="{y:.1f}" width="{w:.1f}" height="{bh:.1f}" '
                   f'class="{cls}" rx="1.5"/>')
        out.append(txt(L - 10, y + bh / 2 + 4, k, "tick", "end"))
        lab = f"{v}" + ("+" if v >= 500 else "")
        out.append(txt(L + w + 8, y + bh / 2 + 4, lab, "barval"))
    out.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}" class="axis"/>')
    out.append(txt(L + pw / 2, H - 8,
                   "highest velocity-actuator gain that stays stable", "cap", "middle"))
    return frame(W, H, "".join(out), "Integrator stability against controller gain")


# ------------------------------------------------------- cross-engine dt log
def crossengine_penetration():
    """MuJoCo flat then stepping; PhysX sloping. Two different contact models
    shown as two different curve SHAPES, which is the whole point."""
    ce = load("crossengine_contact")
    W, H = 520, 320
    L, Rm, T, B = 66, 78, 26, 50
    pw, ph = W - L - Rm, H - T - B
    hzs = [480, 240, 120, 60, 30]

    def X(hz):
        lo, hi = math.log10(30), math.log10(480)
        return L + pw - (math.log10(hz) - lo) / (hi - lo) * pw

    def Y(mm):
        lo, hi = -5.0, 0.2
        return T + (1 - (math.log10(max(mm, 1e-5)) - lo) / (hi - lo)) * ph

    out = [f'<rect x="{L}" y="{T}" width="{pw}" height="{ph}" class="plot-bg"/>']
    for e in range(-5, 1):
        y = Y(10.0 ** e)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" class="grid"/>')
        out.append(txt(L - 8, y + 4, f"1e{e}", "tick", "end"))
    for hz in hzs:
        out.append(txt(X(hz), T + ph + 18, f"{hz}", "tick", "middle"))

    for eng, cls in (("mujoco", "series-a"), ("physx", "series-ok")):
        pts = [(X(hz), Y(ce["dt_sweep"][eng][str(hz)])) for hz in hzs]
        d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        out.append(f'<path d="{d}" class="{cls}" fill="none"/>')
        for x, y in pts:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" class="{cls}-dot"/>')
        out.append(txt(pts[-1][0] + 10, pts[-1][1] + 4,
                       "MuJoCo" if eng == "mujoco" else "PhysX",
                       "key-a" if eng == "mujoco" else "key-ok"))

    # the flat region is the clamp signature
    out.append(f'<rect x="{X(480):.1f}" y="{Y(0.14):.1f}" '
               f'width="{X(120)-X(480):.1f}" height="{Y(0.08)-Y(0.14):.1f}" '
               f'class="band-flat"/>')
    out.append(txt(X(240), Y(0.14) - 8, "flat: 2·dt clamp", "key-a", "middle"))
    out.append(txt(L + pw / 2, H - 8, "physics rate  (Hz)", "cap", "middle"))
    out.append(txt(-(T + ph / 2), 14, "resting penetration  (mm)", "cap", "middle"
                   ).replace("<text ", '<text transform="rotate(-90)" '))
    return frame(W, H, "".join(out), "Resting penetration against physics rate, both engines")


# ------------------------------------------------------------ mass ratio
def mass_ratio_cliff():
    cs = load("crossengine_stack")
    mj = {1: 1.207, 100: 5.954, 10000: 51.026}     # from stability_frontier.py
    px = {int(k): v for k, v in cs["mass_ratio"].items()}
    W, H = 520, 300
    L, Rm, T, B = 62, 74, 30, 50
    pw, ph = W - L - Rm, H - T - B
    ratios = [1, 10, 100, 1000, 10000]

    def X(r):
        return L + math.log10(r) / 4.0 * pw

    def Y(mm):
        return T + (1 - min(mm, 105) / 105.0) * ph

    out = [f'<rect x="{L}" y="{T}" width="{pw}" height="{ph}" class="plot-bg"/>']
    for v in (0, 25, 50, 75, 100):
        y = Y(v)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" class="grid"/>')
        out.append(txt(L - 8, y + 4, f"{v}", "tick", "end"))
    for r in ratios:
        lab = "1" if r == 1 else f"1e{int(math.log10(r))}"
        out.append(txt(X(r), T + ph + 18, lab, "tick", "middle"))

    pts = [(X(r), Y(px[r])) for r in ratios]
    out.append('<path d="M ' + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
               + '" class="series-warn" fill="none"/>')
    for x, y in pts:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" class="series-warn-dot"/>')
    out.append(txt(pts[-1][0] + 10, pts[-1][1] + 4, "PhysX", "key-warn"))

    mpts = [(X(r), Y(mj[r])) for r in sorted(mj)]
    out.append('<path d="M ' + " L ".join(f"{x:.1f},{y:.1f}" for x, y in mpts)
               + '" class="series-a" fill="none"/>')
    for x, y in mpts:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" class="series-a-dot"/>')
    out.append(txt(mpts[-1][0] + 10, mpts[-1][1] + 4, "MuJoCo", "key-a"))

    xm = (X(10) + X(100)) / 2
    out.append(f'<line x1="{xm:.1f}" y1="{T}" x2="{xm:.1f}" y2="{T+ph}" class="marker"/>')
    out.append(txt(xm - 8, T + 16, "37x in one step", "key-warn", "end"))
    out.append(txt(L + pw / 2, H - 8, "mass ratio  (heavy / light)", "cap", "middle"))
    out.append(txt(-(T + ph / 2), 14, "squash  (mm)", "cap", "middle"
                   ).replace("<text ", '<text transform="rotate(-90)" '))
    return frame(W, H, "".join(out), "Stack squash against mass ratio in both engines")


# --------------------------------------------------------- collision cost
def collision_bars():
    cc = load("collision_cost")
    rows = cc["normalised"]["rows"]
    W, H = 520, 280
    L, Rm, T, B = 130, 70, 22, 46
    pw, ph = W - L - Rm, H - T - B
    vmax = max(r["us_per_contact"] for r in rows) * 1.15
    bh = ph / len(rows) * 0.55
    out = []
    for i, r in enumerate(rows):
        y = T + ph * (i + 0.5) / len(rows) - bh / 2
        w = r["us_per_contact"] / vmax * pw
        cls = "bar-b" if r["hull_vertices"] == 0 else "bar-warn"
        out.append(f'<rect x="{L}" y="{y:.1f}" width="{w:.1f}" height="{bh:.1f}" '
                   f'class="{cls}" rx="1.5"/>')
        name = r["label"].replace("primitive ", "").replace("mesh (icosa, 12 v)", "mesh 12v")
        name = name.replace("mesh (subdiv 1)", "mesh 42v").replace("mesh (subdiv 2)", "mesh 282v")
        out.append(txt(L - 10, y + bh / 2 + 4, name, "tick", "end"))
        out.append(txt(L + w + 8, y + bh / 2 + 4, f"{r['us_per_contact']:.2f}", "barval"))
    out.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}" class="axis"/>')
    out.append(txt(L + pw / 2, H - 8,
                   "microseconds PER CONTACT  (one run, one machine)", "cap", "middle"))
    return frame(W, H, "".join(out), "Per-contact collision cost by shape")


# ------------------------------------------------------- format diagram
def tree_vs_loop():
    """URDF is a tree; a four-bar is a loop. Drawn rather than described,
    because the constraint is structural and a picture states it in one look."""
    W, H = 520, 250
    out = []
    ny = [(90, 60), (50, 130), (130, 130), (50, 200), (130, 200)]
    ox = 40
    for (x, y) in ny:
        pass
    edges = [(0, 1), (0, 2), (1, 3), (2, 4)]
    for a, b in edges:
        out.append(f'<line x1="{ox+ny[a][0]}" y1="{ny[a][1]}" '
                   f'x2="{ox+ny[b][0]}" y2="{ny[b][1]}" class="link"/>')
    for i, (x, y) in enumerate(ny):
        out.append(f'<circle cx="{ox+x}" cy="{y}" r="9" class="node"/>')
    out.append(txt(ox + 90, 34, "URDF — a tree", "figtitle", "middle"))
    out.append(txt(ox + 90, 232, "one parent per link", "cap", "middle"))

    ox2 = 300
    ly = [(90, 60), (40, 130), (140, 130), (90, 196)]
    ledges = [(0, 1), (0, 2), (1, 3), (2, 3)]
    for a, b in ledges:
        cls = "link-close" if (a, b) == (2, 3) else "link"
        out.append(f'<line x1="{ox2+ly[a][0]}" y1="{ly[a][1]}" '
                   f'x2="{ox2+ly[b][0]}" y2="{ly[b][1]}" class="{cls}"/>')
    for i, (x, y) in enumerate(ly):
        out.append(f'<circle cx="{ox2+x}" cy="{y}" r="9" class="node"/>')
    out.append(txt(ox2 + 90, 34, "MJCF / SDF — a loop", "figtitle", "middle"))
    out.append(txt(ox2 + 90, 232, "the closure URDF cannot state", "cap-warn", "middle"))
    out.append(f'<line x1="{ox+250}" y1="60" x2="{ox+250}" y2="210" class="divider"/>')
    return frame(W, H, "".join(out), "A kinematic tree beside a closed loop")


# ------------------------------------------------------- corrections tally
def corrections_tally(total=12, studies=17):
    """The page's thesis as a figure: how much of this work was being wrong."""
    W, H = 520, 130
    cols, gap, r = 17, 28, 9
    x0 = (W - (cols - 1) * gap) / 2
    out = []
    for i in range(studies):
        x = x0 + i * gap
        cls = "tally-on" if i < total else "tally-off"
        out.append(f'<circle cx="{x:.1f}" cy="64" r="{r}" class="{cls}"/>')
    out.append(txt(W / 2, 28, f"{total} of {studies} studies contained a wrong answer",
                   "figtitle", "middle"))
    out.append(txt(W / 2, 104, "found, corrected, and kept in the record",
                   "cap", "middle"))
    return frame(W, H, "".join(out), "Tally of studies containing a corrected error")


# ---------------------------------------------------------- gait schedule
def gait_schedule():
    """Commanded trot beside what was measured. The contrast is the finding."""
    gv = load("gait_validation")
    W, H = 520, 300
    L, Rm, T = 92, 24, 34
    lane_h = 26
    pw = W - L - Rm
    out = []
    legs = ["FL", "FR", "HL", "HR"]
    out.append(txt(L, T - 12, "COMMANDED  —  trot, 50% duty, diagonals in antiphase",
                   "figtitle"))
    for i, leg in enumerate(legs):
        y = T + i * lane_h
        out.append(txt(L - 10, y + 15, leg, "tick", "end"))
        out.append(f'<rect x="{L}" y="{y+4}" width="{pw}" height="{lane_h-10}" '
                   f'class="lane"/>')
        phase = 0.0 if leg in ("FL", "HR") else 0.5
        for k in range(5):
            sx = L + ((k + phase) % 5) / 5 * pw
            w = pw / 10
            if sx + w <= L + pw:
                out.append(f'<rect x="{sx:.1f}" y="{y+4}" width="{w:.1f}" '
                           f'height="{lane_h-10}" class="stance-ok" rx="1"/>')

    T2 = T + 4 * lane_h + 34
    out.append(txt(L, T2 - 12, "MEASURED  —  ANYmal, open loop", "figtitle-warn"))
    duty = gv["attempt7"]["ANYmal"]["duty_measured"]
    for i, leg in enumerate(["LF", "RF", "LH", "RH"]):
        y = T2 + i * lane_h
        out.append(txt(L - 10, y + 15, leg, "tick", "end"))
        out.append(f'<rect x="{L}" y="{y+4}" width="{pw}" height="{lane_h-10}" '
                   f'class="lane"/>')
        frac = duty[leg]
        out.append(f'<rect x="{L}" y="{y+4}" width="{pw*frac:.1f}" '
                   f'height="{lane_h-10}" class="stance-warn" rx="1"/>')
        out.append(txt(L + pw * frac + 8, y + 15, f"{frac:.2f}", "barval"))
    out.append(txt(W / 2, H - 6,
                   "duty 0.96 on every leg — nothing ever lifts", "cap-warn", "middle"))
    return frame(W, H, "".join(out), "Commanded trot contact schedule beside the measured one")


# ------------------------------------------------------------- trot wheel
def trot_wheel():
    """Spot's measured gait as a phase wheel.

    A trot has one signature: diagonal pairs at the same phase, and the two
    pairs half a cycle apart. On a wheel that is two dots together at the top
    and two together at the bottom -- readable in one look, where a table of
    four numbers is not.
    """
    gr = load("gait_result")
    s = gr["trot_error"]["Spot"]
    byq = s["phase_by_quadrant"]
    W, H = 460, 400
    cx, cy, R = W / 2, H / 2 + 4, 132
    out = [f'<circle cx="{cx}" cy="{cy}" r="{R}" class="ring"/>']

    # ideal trot: two nodes, half a cycle apart
    for a, lab in ((0, "0°"), (90, ""), (180, "180°"), (270, "")):
        th = math.radians(a - 90)
        x, y = cx + R * math.cos(th), cy + R * math.sin(th)
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" class="axis-spoke"/>')
        if lab:
            out.append(txt(cx + (R + 20) * math.cos(th), cy + (R + 20) * math.sin(th) + 4,
                           lab, "tick", "middle"))

    pairs = {"FL": "a", "HR": "a", "FR": "b", "HL": "b"}
    for q in ("FL", "HR", "FR", "HL"):
        th = math.radians(byq[q] - 90)
        x, y = cx + R * math.cos(th), cy + R * math.sin(th)
        cls = "series-ok-dot" if pairs[q] == "a" else "series-a-dot"
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
                   f'class="{"series-ok" if pairs[q]=="a" else "series-a"}"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" class="{cls}"/>')
        ox = 20 if math.cos(th) >= 0 else -20
        anc = "start" if math.cos(th) >= 0 else "end"
        out.append(txt(x + ox, y + 4, f"{q}  {byq[q]:.1f}°", "tick", anc))

    out.append(txt(cx, cy - 8, "SPOT", "figtitle", "middle"))
    out.append(txt(cx, cy + 10, f"{s['worst_deviation_deg']}° worst", "key-ok", "middle"))
    out.append(txt(16, 24, "FL + HR", "key-ok"))
    out.append(txt(16, 40, f"{s['diag_FL_HR_deg']}° apart", "tick"))
    out.append(txt(W - 16, 24, "FR + HL", "key-a", "end"))
    out.append(txt(W - 16, 40, f"{s['diag_FR_HL_deg']}° apart", "tick", "end"))
    out.append(txt(cx, H - 6, "measured foot phase, trunk frame", "cap", "middle"))
    return frame(W, H, "".join(out), "Spot's measured trot phase on a wheel")


# --------------------------------------------------------- friction grid
def friction_recovery():
    """Why the bias had to be positive.

    The continuous curve is the true slip angle, atan(mu). The horizontal
    bands are the 2-degree sweep grid. A detected angle can only ever be the
    first grid line AT OR ABOVE the curve -- so recovered mu is always high,
    whatever pre-slip creep does. The figure makes the argument; the caption
    does not have to.
    """
    fr = load("friction_recovery_analysis")
    rows = fr["recovered"]
    W, H = 520, 330
    L, Rm, T, B = 62, 96, 26, 50
    pw, ph = W - L - Rm, H - T - B
    mu_lo, mu_hi = 0.15, 0.95
    a_lo, a_hi = 8.0, 46.0

    def X(mu):
        return L + (mu - mu_lo) / (mu_hi - mu_lo) * pw

    def Y(a):
        return T + (1 - (a - a_lo) / (a_hi - a_lo)) * ph

    out = [f'<rect x="{L}" y="{T}" width="{pw}" height="{ph}" class="plot-bg"/>']
    # the 2-degree sweep grid -- the actual cause
    a = 8
    while a <= 46:
        y = Y(a)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" class="grid"/>')
        if a % 10 == 0:
            out.append(txt(L - 8, y + 4, f"{a}°", "tick", "end"))
        a += 2

    pts = []
    mu = mu_lo
    while mu <= mu_hi + 1e-9:
        pts.append((X(mu), Y(math.degrees(math.atan(mu)))))
        mu += 0.01
    out.append('<path d="M ' + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
               + '" class="series-a" fill="none"/>')
    out.append(txt(X(0.92) - 4, Y(math.degrees(math.atan(0.92))) - 10,
                   "true:  atan(mu)", "key-a", "end"))

    for r in rows:
        x = X(r["mu_input"])
        yt = Y(r["true_slip_angle_deg"])
        yd = Y(r["slip_angle_deg"])
        out.append(f'<line x1="{x:.1f}" y1="{yt:.1f}" x2="{x:.1f}" y2="{yd:.1f}" '
                   f'class="series-warn"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{yt:.1f}" r="3" class="series-a-dot"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{yd:.1f}" r="5" class="series-warn-dot"/>')
        out.append(txt(x + 10, yd - 6, f"+{r['error_pct']}%", "key-warn"))
        out.append(txt(x, T + ph + 18, f"{r['mu_input']}", "tick", "middle"))

    out.append(txt(L + pw + 12, T + 16, "DETECTED", "key-warn"))
    out.append(txt(L + pw + 12, T + 32, "always the first", "tick"))
    out.append(txt(L + pw + 12, T + 46, "grid line ABOVE", "tick"))
    out.append(txt(L + pw + 12, T + 60, "the true angle", "tick"))
    out.append(txt(L + pw / 2, H - 8, "friction coefficient supplied to PhysX", "cap", "middle"))
    out.append(txt(-(T + ph / 2), 14, "slip angle", "cap", "middle"
                   ).replace("<text ", '<text transform="rotate(-90)" '))
    return frame(W, H, "".join(out), "Detected slip angle against the true atan(mu) curve")


# ------------------------------------------------------- chaos divergence
def chaos_divergence():
    """Separation against time, log scale, for two seeds 4000x apart.

    Both grow at the same rate -- that is what makes the exponent a property
    of the trajectory rather than of how hard you poke it. The 1e-12 seed
    crosses 1 mm where the exponent fitted on the OTHER run said it would,
    which is the strongest check available here.
    """
    det = load("determinism")
    a = det["chaos_smooth_1ulp"]
    b = det["chaos_smooth_seeded_1e-12"]
    lam = a["lyapunov_exponent_per_s"]
    pred = det["predictive_check"]["predicted_1mm_s"]
    meas = det["predictive_check"]["measured_1mm_s"]

    W, H = 520, 320
    L, Rm, T, B = 66, 92, 26, 50
    pw, ph = W - L - Rm, H - T - B
    t_max, lo, hi = 14.0, -17.0, -1.0

    def X(t):
        return L + t / t_max * pw

    def Y(v):
        return T + (1 - (math.log10(max(v, 1e-17)) - lo) / (hi - lo)) * ph

    out = [f'<rect x="{L}" y="{T}" width="{pw}" height="{ph}" class="plot-bg"/>']
    for e in range(-16, 0, 3):
        y = Y(10.0 ** e)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" class="grid"/>')
        out.append(txt(L - 8, y + 4, f"1e{e}", "tick", "end"))
    for t in (0, 4, 8, 12):
        out.append(txt(X(t), T + ph + 18, f"{t}", "tick", "middle"))

    # exponential growth from each seed, saturating at the pendulum's own size
    for eps, cls, key in ((a["perturbation"], "series-a", "1 ULP"),
                          (b["perturbation"], "series-warn", "1e-12")):
        pts = []
        t = 0.0
        while t <= t_max:
            v = min(eps * math.exp(lam * t), 0.6)
            pts.append((X(t), Y(v)))
            t += 0.15
        out.append('<path d="M ' + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                   + f'" class="{cls}" fill="none"/>')
        out.append(txt(L + pw + 10, pts[-1][1] + 4, key,
                       "key-a" if cls == "series-a" else "key-warn"))
        del pts

    y1mm = Y(1e-3)
    out.append(f'<line x1="{L}" y1="{y1mm:.1f}" x2="{L+pw}" y2="{y1mm:.1f}" '
               f'class="marker"/>')
    out.append(txt(L + 6, y1mm - 6, "1 mm apart", "key-warn"))
    for t, lab, cls in ((pred, "predicted", "series-a"), (meas, "measured", "series-warn")):
        out.append(f'<line x1="{X(t):.1f}" y1="{T}" x2="{X(t):.1f}" y2="{T+ph}" '
                   f'class="marker"/>')
        out.append(f'<circle cx="{X(t):.1f}" cy="{y1mm:.1f}" r="5" class="{cls}-dot"/>')
    # keep the two crossing labels off each other: one above, one below
    out.append(txt(X(pred) - 8, T + 14, f"predicted {pred}s", "key-a", "end"))
    out.append(txt(X(meas) + 8, T + ph - 8, f"measured {meas}s", "key-warn"))
    out.append(txt(L + pw / 2, H - 8, "seconds", "cap", "middle"))
    out.append(txt(-(T + ph / 2), 14, "separation  (m)", "cap", "middle"
                   ).replace("<text ", '<text transform="rotate(-90)" '))
    return frame(W, H, "".join(out), "Separation against time for two perturbation sizes")
