#!/usr/bin/env bash
# Kaggle allows only TWO concurrent batch sessions. Pushing a third fails with
#   "Maximum batch GPU session count of 2 reached."
# So work has to be fed in as slots free, not fired all at once.
#
#   bash tools/queue_runner.sh <dir1> [dir2 ...]
set -uo pipefail
# The token is read from the environment, never written here. An earlier
# version hardcoded it, which put a live credential into every commit in this
# repository's history -- caught by a secret scan before the first push, and
# purged with git filter-branch. Treat any token that has ever been in a file
# as compromised and rotate it.
: "${KAGGLE_API_TOKEN:?set KAGGLE_API_TOKEN before running (export KAGGLE_API_TOKEN=...)}"
K=/Users/jacobgarcia/2099/isaacfree/.venv/bin/kaggle

for dir in "$@"; do
  slug=$(python3 -c "import json;print(json.load(open('$dir/kernel-metadata.json'))['id'].split('/')[1])")
  echo "=== queueing $slug"
  for attempt in $(seq 1 200); do
    out=$($K kernels push -p "$dir" --accelerator NvidiaTeslaT4 2>&1 | tail -1)
    if echo "$out" | grep -q "successfully pushed"; then
      echo "    pushed (attempt $attempt)"
      break
    fi
    if echo "$out" | grep -q "Maximum batch"; then
      sleep 60          # a slot is busy; wait and retry
      continue
    fi
    echo "    push failed: $out"; break
  done
  # wait for THIS job to finish before feeding the next one
  for i in $(seq 1 200); do
    s=$($K kernels status "jacobegarcia/$slug" 2>&1 | sed 's/.*KernelWorkerStatus\.//' | tr -d '"' | tr -d '\n')
    case "$s" in
      COMPLETE|ERROR|CANCEL*) echo "    $slug -> $s"; break;;
    esac
    sleep 30
  done
done
echo "QUEUE DRAINED"
