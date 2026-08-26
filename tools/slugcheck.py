"""Kaggle requires a kernel's title to slugify to its id, or the push 400s.

This enforces that invariant at build time instead of discovering it on push.
"""
import importlib.util
import os
import re
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nbsrc")


def slugify(title):
    """Match Kaggle's slug derivation: lowercase, non-alnum -> hyphen, collapse."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(SRC, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    bad = 0
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".py") or f.startswith("_"):
            continue
        m = load(f[:-3])
        want = slugify(m.TITLE)
        ok = want == m.SLUG
        bad += not ok
        print(f"  [{'ok  ' if ok else 'FAIL'}] {f[:-3]}")
        if not ok:
            print(f"         TITLE slugifies to : {want}")
            print(f"         SLUG is            : {m.SLUG}")
        if len(want) > 50:
            print(f"         [warn] slug is {len(want)} chars — Kaggle prefers shorter")
    print("-" * 60)
    print("mismatches:", bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
