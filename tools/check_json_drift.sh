#!/usr/bin/env bash
# Compare regenerated measured JSON against what is committed, ignoring
# clock-derived fields. See tools/json_stable.py for why.
set -uo pipefail
PY="${PY:-python}"
fail=0
for f in model/*.json; do
  committed=$(mktemp)
  git show "HEAD:$f" > "$committed" 2>/dev/null || { rm -f "$committed"; continue; }
  if ! diff -q <("$PY" tools/json_stable.py "$committed") \
                <("$PY" tools/json_stable.py "$f") > /dev/null; then
    echo "DRIFT: $f"
    diff <("$PY" tools/json_stable.py "$committed") \
         <("$PY" tools/json_stable.py "$f") | head -20
    fail=1
  fi
  rm -f "$committed"
done
[ "$fail" -eq 0 ] && echo "no drift in deterministic fields"
exit "$fail"
