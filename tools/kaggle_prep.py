"""
Generate Kaggle kernel/dataset metadata and stage each notebook for push.

    python3 tools/kaggle_prep.py --user <kaggle-username>

Creates dist/<slug>/ containing the .ipynb plus kernel-metadata.json, ready
for `kaggle kernels push -p dist/<slug>`.

Everything is staged PRIVATE by default. Flipping a notebook public is a
separate, deliberate step (tools/kaggle_publish.sh) because publishing is
irreversible in the ways that matter -- a bad first impression on a notebook
cannot be undone by editing it later.
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "nbsrc")
NB = os.path.join(ROOT, "notebooks")
DIST = os.path.join(ROOT, "dist")

# Datasets each notebook expects to be attached, by Kaggle slug.
DATASET_DEPS = {
    "free-labeled-training-data-with-isaac-sim": [
        "isaac-sim-synthetic-robot-vision", "real-objects-testset"],
    "does-domain-randomization-actually-help": [
        "isaac-sim-synthetic-robot-vision", "isaac-sim-domain-randomized",
        "real-objects-testset"],
    "mujoco-vs-isaac-sim-a-practical-benchmark": [
        "mujoco-vs-isaac-benchmark"],
}

DATASETS = {
    "isaac-sim-synthetic-robot-vision": {
        "title": "Isaac Sim Synthetic Robot Vision",
        "subtitle": "Pixel-perfect boxes and masks, rendered not labeled",
    },
    "isaac-sim-domain-randomized": {
        "title": "Isaac Sim Domain-Randomized Vision",
        "subtitle": "Matched treatment arm for a controlled DR experiment",
    },
    "mujoco-vs-isaac-benchmark": {
        "title": "MuJoCo vs Isaac Sim: Physics Benchmark",
        "subtitle": "Throughput and integrator energy-drift, both engines",
    },
}


def load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(SRC, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def prep_kernel(mod, user):
    # Kaggle 400s the push if the title does not slugify to the id, so treat
    # a mismatch as a build error rather than discovering it at push time.
    from slugcheck import slugify
    want = slugify(mod.TITLE)
    if want != mod.SLUG:
        raise SystemExit(
            f"slug mismatch in {mod.__name__}:\n"
            f"  TITLE slugifies to: {want}\n"
            f"  SLUG is           : {mod.SLUG}\n"
            f"Kaggle will reject this push. Fix one of them.")
    slug = mod.SLUG
    d = os.path.join(DIST, slug)
    os.makedirs(d, exist_ok=True)
    shutil.copy(os.path.join(NB, slug + ".ipynb"), d)

    meta = {
        "id": f"{user}/{slug}",
        "title": mod.TITLE,
        "code_file": slug + ".ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "true",          # deliberate: never auto-public
        "enable_gpu": "true",
        # CRITICAL: enable_gpu alone gets Kaggle's DEFAULT GPU, which is a
        # Tesla P100 -- compute capability 6.0, Pascal, NO RT cores, and below
        # PhysX's 7.0 minimum. Isaac Sim cannot work on it. Only these exact
        # strings are recognised: NvidiaTeslaT4 | NvidiaTeslaP100 | Tpu1VmV38.
        # Anything else silently falls back to P100.
        "machine_shape": "NvidiaTeslaT4",
        "enable_internet": "true",
        "keywords": getattr(mod, "TAGS", []),
        "dataset_sources": [f"{user}/{s}" for s in DATASET_DEPS.get(slug, [])],
        "competition_sources": [],
        "kernel_sources": [],
    }
    with open(os.path.join(d, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  staged  dist/{slug}/  ({len(meta['dataset_sources'])} dataset deps)")
    return d


def prep_datasets(user):
    for slug, info in DATASETS.items():
        d = os.path.join(DIST, "datasets", slug)
        os.makedirs(d, exist_ok=True)
        meta = {
            "title": info["title"],
            "id": f"{user}/{slug}",
            "subtitle": info["subtitle"],
            "licenses": [{"name": "CC0-1.0"}],
            "keywords": ["robotics", "computer vision", "physics"],
        }
        with open(os.path.join(d, "dataset-metadata.json"), "w") as f:
            json.dump(meta, f, indent=2)
        print(f"  staged  dist/datasets/{slug}/  (drop data files here)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True, help="your Kaggle username")
    args = ap.parse_args()

    print("notebooks:")
    for f in sorted(os.listdir(SRC)):
        if f.endswith(".py") and not f.startswith("_"):
            prep_kernel(load(f[:-3]), args.user)
    print("\ndatasets:")
    prep_datasets(args.user)
    print("\nAll staged PRIVATE. Nothing is public until you run "
          "tools/kaggle_publish.sh explicitly.")


if __name__ == "__main__":
    main()
