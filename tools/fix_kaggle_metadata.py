"""
Repair metadata on existing Kaggle content.

Three defects found on the account, all fixable without touching the data:

1. Mojibake -- UTF-8 bytes that were decoded as Latin-1 somewhere upstream,
   so em-dashes render as 'a EUR "' and degree signs as 'A°'. Repaired by
   re-encoding latin-1 -> utf-8.
2. Empty descriptions -- two datasets have none at all, which is most of why
   their usability scores are 0.24 and 0.06. Usability feeds discoverability,
   and undiscovered content cannot be upvoted.
3. Private visibility -- handled separately in flip_public.py, because that
   one is a publish action and needs explicit sign-off.

    python3 tools/fix_kaggle_metadata.py --dry-run
    python3 tools/fix_kaggle_metadata.py --apply
"""
import argparse
import json
import os
import re
import subprocess

KAGGLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      ".venv", "bin", "kaggle")
USER = "jacobegarcia"


# Mojibake alphabet, built programmatically: any char cp1252 encodes into
# 0x80-0xFF can be a continuation byte of a UTF-8 sequence that was
# mis-decoded. Building it from the codec beats hand-listing the characters.
_CONT = "".join(sorted({bytes([b]).decode("cp1252") for b in range(0x80, 0x100)
                        if bytes([b]).decode("cp1252", errors="ignore")}))
_LEAD = "\u00c2\u00c3\u00e2\u00e3\u00d0\u00f0"
_RUN = re.compile("[" + re.escape(_LEAD) + "][" + re.escape(_CONT) + "]+")


def demojibake(s):
    """Repair UTF-8-read-as-cp1252 damage, one damaged RUN at a time.

    A whole-string re-encode fails on mixed text: these descriptions contain
    genuine non-Latin-1 characters (phi, sqrt, pi) alongside the corrupted
    runs, so encoding the entire string raises and the repair is skipped.
    Repairing per run fixes the damage and leaves valid characters alone.
    """
    if not s:
        return s

    def _fix(m):
        run = m.group(0)
        try:
            return run.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return run          # not actually mojibake -- leave it be

    return _RUN.sub(_fix, s)


DESCRIPTIONS = {
    "palmer-penguins-linked-from-seaborn-data": {
        "subtitle": "The Palmer Penguins dataset, mirrored from seaborn-data",
        "description": """# Palmer Penguins

A mirror of the **Palmer Penguins** dataset as distributed with
[seaborn-data](https://github.com/mwaskom/seaborn-data), provided here so
notebooks can attach it directly instead of reaching out to the network.

## Why this mirror exists

Kaggle notebooks run with internet disabled by default. `seaborn.load_dataset`
fetches over HTTP, so any notebook using it fails in the default environment.
Attaching this dataset makes those notebooks reproducible offline.

## What it contains

Body measurements for three penguin species observed on the Palmer
Archipelago, Antarctica: **Adelie**, **Chinstrap**, and **Gentoo**.

| Column | Meaning |
|---|---|
| `species` | Penguin species |
| `island` | Island in the Palmer Archipelago |
| `bill_length_mm` | Bill length (mm) |
| `bill_depth_mm` | Bill depth (mm) |
| `flipper_length_mm` | Flipper length (mm) |
| `body_mass_g` | Body mass (g) |
| `sex` | Male / female |

Rows contain missing values, which is deliberate on the part of the original
authors -- it makes the set useful for teaching missing-data handling rather
than only classification.

## Suggested uses

- A cleaner, less overused substitute for Iris in classification teaching
- Missing-data imputation practice
- Exploratory plotting and pair-plot demonstrations

## Provenance and credit

Collected by **Dr. Kristen Gorman** at Palmer Station, Antarctica LTER, and
released as the `palmerpenguins` R package by Allison Horst, Alison Hill, and
Kristen Gorman. Original data are released CC0. Please cite the original
authors rather than this mirror.
""",
        "keywords": ["beginner", "classification", "tabular", "education",
                     "biology"],
    },
    "titanic-baseline-predictions-notebook-output": {
        "subtitle": "Reference submission file from a 5-fold CV gradient boosting baseline",
        "description": """# Titanic Baseline Predictions

The **output** of a Titanic baseline model, published so the submission format
can be inspected and diffed without re-running the notebook.

## What this is

`submission_hgb.csv` -- predictions from a `HistGradientBoostingClassifier`
pipeline with 5-fold cross-validation.

| Metric | Value |
|---|---|
| Cross-validated accuracy | 0.8271 |
| Public leaderboard score | 0.75119 |

That gap between CV and leaderboard is the interesting part and the reason
this file is worth publishing. A ~7.6 point drop from cross-validation to the
held-out set is typical of Titanic and a useful calibration reminder: **CV
score on a small dataset is an optimistic estimate**, not a prediction of
leaderboard position.

## Format

| Column | Type | Meaning |
|---|---|---|
| `PassengerId` | int | Passenger identifier from `test.csv` |
| `Survived` | int (0/1) | Predicted survival |

418 rows, matching the competition test set exactly.

## Suggested uses

- Verifying your own submission has the correct shape and column names
- A reference point for whether a new model is actually beating a solid
  baseline rather than beating a weak one
- Teaching the CV-versus-leaderboard generalization gap

## License

CC0 -- these are model outputs on a public tutorial competition.
""",
        "keywords": ["beginner", "tabular", "classification", "education"],
    },
}


def fetch(slug):
    d = f"/tmp/fixmeta/{slug}"
    os.makedirs(d, exist_ok=True)
    subprocess.run([KAGGLE, "datasets", "metadata", f"{USER}/{slug}", "-p", d],
                   capture_output=True, text=True)
    p = os.path.join(d, "dataset-metadata.json")
    return (json.load(open(p)) if os.path.exists(p) else None), d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not (args.apply or args.dry_run):
        ap.error("pass --dry-run or --apply")

    slugs = ["phyllotaxis-spiral-geometry-reference",
             "palmer-penguins-linked-from-seaborn-data",
             "titanic-baseline-predictions-notebook-output"]

    for slug in slugs:
        raw, d = fetch(slug)
        if not raw:
            print(f"[skip] {slug}: could not fetch metadata")
            continue
        info = raw.get("info", raw)

        new = {
            "id": f"{USER}/{slug}",
            "title": info.get("title") or slug.replace("-", " ").title(),
            "licenses": info.get("licenses") or [{"name": "CC0-1.0"}],
        }
        desc = info.get("description") or ""
        sub = info.get("subtitle") or ""
        kw = info.get("keywords") or []

        changes = []
        fixed_desc, fixed_sub = demojibake(desc), demojibake(sub)
        if fixed_desc != desc:
            changes.append("repaired mojibake in description")
        if fixed_sub != sub:
            changes.append("repaired mojibake in subtitle")

        override = DESCRIPTIONS.get(slug)
        if override and not desc.strip():
            fixed_desc = override["description"]
            fixed_sub = override["subtitle"]
            kw = kw or override["keywords"]
            changes.append(f"added description ({len(fixed_desc)} chars)")
            changes.append(f"added subtitle + {len(kw)} keywords")

        new["description"] = fixed_desc
        new["subtitle"] = fixed_sub
        new["keywords"] = kw

        print(f"\n=== {slug}")
        print(f"    usability now: {info.get('usabilityRating', 0):.2f}"
              f"  private: {info.get('isPrivate')}")
        if changes:
            for c in changes:
                print(f"    + {c}")
        else:
            print("    (no metadata changes needed)")

        if args.apply and changes:
            with open(os.path.join(d, "dataset-metadata.json"), "w") as f:
                json.dump(new, f, indent=2)
            r = subprocess.run(
                [KAGGLE, "datasets", "metadata", f"{USER}/{slug}", "--update", "-p", d],
                capture_output=True, text=True)
            print("    ->", (r.stdout + r.stderr).strip()[:160])


if __name__ == "__main__":
    main()
