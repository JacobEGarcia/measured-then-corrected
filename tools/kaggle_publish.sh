#!/usr/bin/env bash
# Push one notebook to Kaggle. Private by default; --public requires typing
# a confirmation, because a notebook's first impression cannot be re-done.
set -euo pipefail

SLUG="${1:-}"
PUBLIC="${2:-}"
[ -z "$SLUG" ] && { echo "usage: $0 <slug> [--public]"; exit 1; }

DIR="dist/$SLUG"
[ -d "$DIR" ] || { echo "not staged: $DIR (run tools/kaggle_prep.py first)"; exit 1; }

command -v kaggle >/dev/null || { echo "kaggle CLI missing: pip install kaggle"; exit 1; }
[ -f "$HOME/.kaggle/kaggle.json" ] || {
  echo "No API token at ~/.kaggle/kaggle.json"
  echo "Kaggle -> Settings -> API -> Create New Token, then chmod 600 it."
  exit 1; }

if [ "$PUBLIC" = "--public" ]; then
  python3 - "$DIR" <<'PY'
import json, sys, os
p = os.path.join(sys.argv[1], "kernel-metadata.json")
m = json.load(open(p)); m["is_private"] = "false"
json.dump(m, open(p, "w"), indent=2)
print("marked PUBLIC:", m["title"])
PY
  echo
  echo "This will publish to your public Kaggle profile and start the 90-day"
  echo "medal-eligibility window for this notebook."
  read -r -p 'Type PUBLISH to continue: ' ans
  [ "$ans" = "PUBLISH" ] || { echo "aborted."; exit 1; }
fi

kaggle kernels push -p "$DIR"
echo "pushed. Check status: kaggle kernels status <user>/$SLUG"
