"""Make the static SVG figures animate, without rewriting every chart.

The charts are emitted as plain SVG by charts.py. Rather than thread animation
state through a dozen generators, this post-processes the finished markup:

  * every data path gets pathLength="1" so a single CSS keyframe can draw ANY
    line at a uniform rate regardless of its real length
  * every dot, bar and tally circle gets a --i index so CSS can stagger them
  * the figure only animates once it scrolls into view, so a reader arriving
    at a chart sees it draw rather than finding it already finished

Kare's own icons animated by flipping between a small number of hand-drawn
frames -- the watch cursor, the spinning beachball. The animated icons here do
the same thing: two grids, alternated on a steps() timing function, so the
motion stays on the pixel grid instead of sliding between positions.
"""
import re


def animate_svg(svg):
    """Add pathLength and stagger indices to a finished SVG string."""
    # uniform draw rate for every stroked data path
    svg = re.sub(r'(<path d="[^"]*" class="series-[\w-]+")',
                 r'\1 pathLength="1"', svg)

    # stagger dots, bars and tally circles in document order
    counters = {}

    def stamp(m):
        cls = m.group(2)
        key = "dot" if "dot" in cls or "tally" in cls else "bar"
        counters[key] = counters.get(key, 0) + 1
        return f'{m.group(1)}class="{cls}" style="--i:{counters[key]}"'

    svg = re.sub(r'(<(?:circle|rect)\s[^>]*?)class="([\w-]*(?:dot|tally-on|tally-off|bar-[ab]|bar-warn|stance-\w+)[\w-]*)"',
                 stamp, svg)
    return svg


def animated_icon(grids, px=4, ink="var(--ink)", accent="var(--red)",
                  cls="", title="", ms=520):
    """Overlay N pixel grids and flip between them on a steps() timeline."""
    size = len(grids[0])
    w = size * px
    layers = []
    n = len(grids)
    for k, grid in enumerate(grids):
        rects = []
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                if ch == ".":
                    continue
                fill = ink if ch == "X" else accent
                rects.append(f'<rect x="{x*px}" y="{y*px}" width="{px}" '
                             f'height="{px}" fill="{fill}"/>')
        layers.append(f'<g class="fl" style="--k:{k};--n:{n};'
                      f'animation-duration:{ms}ms">{"".join(rects)}</g>')
    return (f'<svg class="px pxa {cls}" viewBox="0 0 {w} {w}" width="{w}" '
            f'height="{w}" shape-rendering="crispEdges" role="img" '
            f'aria-label="{title or cls}">{"".join(layers)}</svg>')
