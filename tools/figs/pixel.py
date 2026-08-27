"""16x16 bitmap icons, drawn on a grid the way Susan Kare drew them.

Kare designed the original Macintosh icons on graph paper at 32x32 and 16x16,
one pixel at a time, with no antialiasing and no curves that were not made of
steps. These are authored the same way: each icon is a list of strings, one
character per pixel, and rendered as square SVG rects with shape-rendering set
to crispEdges so nothing gets smoothed back into a curve.

Two glyph weights are used: 'X' is ink, 'o' is the accent colour, '.' is empty.
"""


def render(grid, size=16, px=4, ink="var(--ink)", accent="var(--red)",
           cls="", title=""):
    """Turn a pixel grid into SVG. One rect per lit pixel -- inefficient and
    exactly right: the blockiness IS the medium."""
    w = size * px
    rects = []
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            fill = ink if ch == "X" else accent
            rects.append(f'<rect x="{x*px}" y="{y*px}" width="{px}" '
                         f'height="{px}" fill="{fill}"/>')
    t = f"<title>{title}</title>" if title else ""
    return (f'<svg class="px {cls}" viewBox="0 0 {w} {w}" width="{w}" height="{w}" '
            f'shape-rendering="crispEdges" role="img" '
            f'aria-label="{title or cls}">{t}{"".join(rects)}</svg>')


# ---------------------------------------------------------------- the icons
# A bomb, because on a classic Mac a bomb is what you got when something went
# wrong. It marks every correction on this page.
BOMB = [
    "................",
    "..............X.",
    ".............o..",
    "......XXX...o...",
    ".....XXXXX.o....",
    "....XXXXXXX.....",
    "...XXXXXXXXX....",
    "...XXX.XXXXX....",
    "...XX...XXXX....",
    "...XX...XXXX....",
    "...XXX.XXXXX....",
    "...XXXXXXXXX....",
    "....XXXXXXX.....",
    ".....XXXXX......",
    "......XXX.......",
    "................",
]

MAC = [
    "................",
    ".XXXXXXXXXXXXX..",
    ".X...........X..",
    ".X.ooooooooo.X..",
    ".X.o.......o.X..",
    ".X.o.X...X.o.X..",
    ".X.o.......o.X..",
    ".X.o.X...X.o.X..",
    ".X.o..XXX..o.X..",
    ".X.ooooooooo.X..",
    ".X...........X..",
    ".XXXXXXXXXXXXX..",
    "..X.........X...",
    "..XXXXXXXXXXX...",
    "................",
    "................",
]

STOPWATCH = [
    "................",
    "......XXXX......",
    "......X..X......",
    "....XXXXXXXX....",
    "...XX......XX...",
    "..XX...X....XX..",
    "..X....X.....X..",
    ".XX....X......XX",
    ".X.....XXXo....X",
    ".X............X.",
    "..X..........X..",
    "..XX........XX..",
    "...XX......XX...",
    "....XXXXXXXX....",
    "................",
    "................",
]

QUADRUPED = [
    "................",
    "................",
    "....XXXXXXXX....",
    "...XXXXXXXXXX...",
    "..XXXXXXXXXXXX..",
    "..XX........XX..",
    "..X..........X..",
    "..XX........XX..",
    "..X.X......X.X..",
    "..X.X......X.X..",
    "....X......X....",
    "....X......X....",
    "...ooo....ooo...",
    "................",
    "................",
    "................",
]

GRIPPER = [
    "................",
    "......XXXX......",
    "......XXXX......",
    "......XXXX......",
    "....XXXXXXXX....",
    "....X......X....",
    "...XX......XX...",
    "...XX......XX...",
    "...XX.oooo.XX...",
    "...XX.oooo.XX...",
    "...XX.oooo.XX...",
    "...XX......XX...",
    "....X......X....",
    "................",
    "................",
    "................",
]

CUBE = [
    "................",
    "................",
    "....XXXXXXXX....",
    "...X.......XX...",
    "..X.......X.X...",
    ".XXXXXXXXX..X...",
    ".X.......X..X...",
    ".X.......X..X...",
    ".X.......X..X...",
    ".X.......X.X....",
    ".X.......XX.....",
    ".XXXXXXXXX......",
    "................",
    "................",
    "................",
    "................",
]

SCALES = [
    "................",
    ".......XX.......",
    ".XXXXXXXXXXXXXX.",
    ".X.....XX.....X.",
    ".X.....XX.....X.",
    "XXX....XX....XXX",
    "X.X....XX....X.X",
    "XXX....XX....XXX",
    ".......XX.......",
    ".......XX.......",
    "......oooo......",
    ".....oooooo.....",
    "....XXXXXXXX....",
    "...XXXXXXXXXX...",
    "................",
    "................",
]

WRENCH = [
    "................",
    "..........XXX...",
    ".........XXXXX..",
    ".........XX.XX..",
    "........XXX.XX..",
    ".......XXXXXX...",
    "......XXXXX.....",
    ".....XXXX.......",
    "....XXXX........",
    "...XXXX.........",
    "..XXXX..........",
    ".XXXX...........",
    ".XXX............",
    "..X.............",
    "................",
    "................",
]

MAGNIFIER = [
    "................",
    "....XXXXXX......",
    "...X......X.....",
    "..X..oooo..X....",
    "..X.o....o.X....",
    "..X.o....o.X....",
    "..X..oooo..X....",
    "...X......X.....",
    "....XXXXXX......",
    "........XXX.....",
    ".........XXX....",
    "..........XXX...",
    "...........XXX..",
    "............XX..",
    "................",
    "................",
]

FLOPPY = [
    "................",
    ".XXXXXXXXXXXXXX.",
    ".X............X.",
    ".X..XXXXXXXX..X.",
    ".X..X......X..X.",
    ".X..X......X..X.",
    ".X..X......X..X.",
    ".X..XXXXXXXX..X.",
    ".X............X.",
    ".X.oooooooooo.X.",
    ".X.o........o.X.",
    ".X.o..XXXX..o.X.",
    ".X.o........o.X.",
    ".XXXXXXXXXXXXXX.",
    "................",
    "................",
]

CHECK = [
    "................",
    "..............X.",
    ".............XX.",
    "............XX..",
    "...........XX...",
    "..........XX....",
    ".X.......XX.....",
    ".XX.....XX......",
    "..XX...XX.......",
    "...XX.XX........",
    "....XXX.........",
    ".....X..........",
    "................",
    "................",
    "................",
    "................",
]

TREE = [
    "................",
    ".......XX.......",
    ".......XX.......",
    "....XXXXXXXX....",
    "....X......X....",
    "....X......X....",
    "..XXXX....XXXX..",
    "..X..X....X..X..",
    "..X..X....X..X..",
    "..X..X....X..X..",
    ".XX..XX..XX..XX.",
    "................",
    "................",
    "................",
    "................",
    "................",
]

LOOP = [
    "................",
    ".......XX.......",
    "......XXXX......",
    ".....XX..XX.....",
    "....XX....XX....",
    "...XX......XX...",
    "..XX........XX..",
    "..X..........X..",
    "..XX........XX..",
    "...XX......XX...",
    "....oo....oo....",
    ".....oo..oo.....",
    "......oooo......",
    ".......oo.......",
    "................",
    "................",
]

ICONS = {"bomb": BOMB, "mac": MAC, "stopwatch": STOPWATCH,
         "quadruped": QUADRUPED, "gripper": GRIPPER, "cube": CUBE,
         "scales": SCALES, "wrench": WRENCH, "magnifier": MAGNIFIER,
         "floppy": FLOPPY, "check": CHECK, "tree": TREE, "loop": LOOP}


def icon(name, px=4, **kw):
    return render(ICONS[name], px=px, title=name, cls=f"ico-{name}", **kw)
