#!/usr/bin/env bash
# Push a Kaggle kernel with the accelerator PINNED.
#
# Why this wrapper exists: `kaggle kernels push -p .` runs on whatever GPU
# Kaggle hands out, and its default is often a Tesla P100 (compute capability
# 6.0). Isaac Sim's PhysX requires cc >= 7.0, so a P100 run installs for
# ~18 minutes, starts Kit, and then dies inside SimulationApp.__init__ with
# nothing but a warning line to explain it.
#
# `enable_gpu: true` in kernel-metadata.json does NOT pin the model. Only
# --accelerator does. This has now cost two full runs, so plain pushes of
# GPU kernels are refused here rather than left to discipline.
set -euo pipefail

DIR="${1:-.}"
ACC="${2:-NvidiaTeslaT4}"
K="$(dirname "$0")/../.venv/bin/kaggle"

META="$DIR/kernel-metadata.json"
[ -f "$META" ] || { echo "no kernel-metadata.json in $DIR" >&2; exit 1; }

if grep -q '"enable_gpu"[[:space:]]*:[[:space:]]*"\?true' "$META"; then
  echo "GPU kernel -> pinning accelerator to $ACC"
  "$K" kernels push -p "$DIR" --accelerator "$ACC"
else
  echo "CPU kernel -> pushing without accelerator"
  "$K" kernels push -p "$DIR"
fi
