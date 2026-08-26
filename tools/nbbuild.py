"""
Build Kaggle-ready .ipynb files from plain-Python sources in tools/nbsrc/.

Why not write .ipynb directly: notebook JSON is unreviewable and merges badly.
Each source module declares TITLE, SLUG, SUBTITLE, TAGS and CELLS, where CELLS
is a list of ("md"|"code", text). Zero dependencies -- ipynb is just JSON.

    python3 tools/nbbuild.py           # build all
    python3 tools/nbbuild.py nb5       # build one
"""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "nbsrc")
OUT = os.path.join(ROOT, "notebooks")

# Every notebook opens with the same credibility header. On Kaggle, a reader
# deciding whether to upvote skims the first screen -- it needs to say what
# this is, what it costs, and that it actually ran.
HEADER = """# {title}

**{subtitle}**

---

> Part of an open series on running **NVIDIA Isaac Sim on free GPUs**.
> Isaac Sim is free software (Apache 2.0) — only compute ever costs money,
> and this series is about not paying for that either.
>
> If this is useful, an upvote helps other people find it. Questions in the
> comments get answered.

---
"""

FOOTER = """
---

## Reproducing this

Every notebook in this series runs on free infrastructure. Nothing here needs
a paid GPU.

| Method | Free allowance | Best for |
|---|---|---|
| Kaggle | 30 GPU hr/week, 2x T4 | Running this notebook as-is |
| Lightning AI | 80 GPU hr/month, persistent disk | Heavy Isaac Sim generation |
| Google Colab | best-effort T4 | Quick smoke tests |
| NVIDIA DLI | free hosted labs | Learning the Isaac Sim GUI |

**The one gotcha worth remembering:** Isaac Sim needs **RT cores**. A T4, L4,
L40S or any RTX card is fine. An **A100 or H100 is not** — those have no RT
cores, so the RTX renderer is unsupported or unusably slow. It is the most
counterintuitive constraint in cloud robotics simulation, and it bites people
who assume the more expensive GPU must be the better one.

*Series index and full source: see the linked dataset description.*
"""


def load(name):
    path = os.path.join(SRC, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cell(kind, text, idx=0):
    """nbformat >=4.5 requires a per-cell id; Kaggle warns loudly without one.
    Derived from the index so rebuilds stay byte-stable (a random id would
    make every rebuild look like a diff)."""
    lines = text.strip("\n").split("\n")
    src = [l + "\n" for l in lines[:-1]] + [lines[-1]]
    cid = "c%03d" % idx
    if kind == "md":
        return {"cell_type": "markdown", "metadata": {}, "id": cid,
                "source": src}
    return {"cell_type": "code", "metadata": {}, "id": cid, "source": src,
            "execution_count": None, "outputs": []}


def build(name):
    m = load(name)
    cells = [_cell("md", HEADER.format(title=m.TITLE, subtitle=m.SUBTITLE), 0)]
    cells += [_cell(k, t, i) for i, (k, t) in enumerate(m.CELLS, start=1)]
    cells.append(_cell("md", FOOTER, len(m.CELLS) + 1))

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.13"},
            "kaggle": {"accelerator": "nvidiaTeslaT4",
                       "dataSources": [],
                       "isInternetEnabled": True,
                       "language": "python",
                       "sourceType": "notebook"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    os.makedirs(OUT, exist_ok=True)
    dest = os.path.join(OUT, m.SLUG + ".ipynb")
    with open(dest, "w") as f:
        json.dump(nb, f, indent=1)
    n_code = sum(1 for c in cells if c["cell_type"] == "code")
    print("  %-42s %2d cells (%d code)  %s"
          % (m.SLUG + ".ipynb", len(cells), n_code, m.TITLE[:34]))
    return dest


def main():
    names = sys.argv[1:] or sorted(
        f[:-3] for f in os.listdir(SRC)
        if f.endswith(".py") and not f.startswith("_"))
    print("building %d notebook(s) -> notebooks/" % len(names))
    for n in names:
        build(n)


if __name__ == "__main__":
    main()
