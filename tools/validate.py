"""Validate every built notebook before it goes anywhere near Kaggle.

Checks: valid ipynb JSON, code cells parse as Python (magics stripped),
required Kaggle metadata present, no leaked absolute local paths, and that
markdown cells are non-trivial.
"""
import ast
import glob
import json
import os
import re
import sys

FAIL = 0


def err(nb, msg):
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {nb}: {msg}")


def strip_magics(src):
    """Replace IPython magics and shell escapes with `pass`, following
    backslash continuations so multi-line !commands do not read as indents."""
    out = []
    in_magic = False
    for line in src.split("\n"):
        s = line.strip()
        if in_magic:
            out.append("pass  # magic continuation")
            in_magic = s.endswith("\\")
            continue
        if s.startswith(("%", "!")):
            out.append("pass  # magic")
            in_magic = s.endswith("\\")
        else:
            out.append(line)
    return "\n".join(out)


def check(path):
    name = os.path.basename(path)
    try:
        nb = json.load(open(path))
    except Exception as e:
        return err(name, f"invalid JSON: {e}")

    if nb.get("nbformat") != 4:
        err(name, "nbformat != 4")
    kg = nb.get("metadata", {}).get("kaggle", {})
    if not kg.get("isInternetEnabled"):
        err(name, "kaggle metadata: internet not enabled")
    if not kg.get("accelerator"):
        err(name, "kaggle metadata: no accelerator set")

    n_code = n_md = 0
    for i, c in enumerate(nb["cells"]):
        src = "".join(c["source"])
        if c["cell_type"] == "code":
            n_code += 1
            try:
                ast.parse(strip_magics(src))
            except SyntaxError as e:
                err(name, f"cell {i} syntax: {e}")
        else:
            n_md += 1

        # Local paths must never ship in a published notebook.
        for pat in (r"/Users/[a-z]+", r"/home/[a-z]+/", r"\.venv"):
            if re.search(pat, src):
                err(name, f"cell {i} leaks a local path matching {pat!r}")

    if n_md < 3:
        err(name, f"only {n_md} markdown cells — too thin to earn a medal")
    print(f"  [ ok ] {name:<52} {n_code:2d} code / {n_md:2d} md")


def main():
    files = sorted(glob.glob("notebooks/*.ipynb"))
    if not files:
        print("no notebooks built — run tools/nbbuild.py")
        sys.exit(1)
    print(f"validating {len(files)} notebooks")
    for f in files:
        check(f)
    print("-" * 68)
    print("FAILURES:", FAIL)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
