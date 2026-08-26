#!/usr/bin/env bash
# Turn a directory of rendered frames into an mp4.
#
# Why this instead of WebRTC streaming: Isaac Sim can stream its viewport over
# WebRTC, but getting that through a notebook's proxy is a fight you will lose.
# Rendering frames to disk and stitching them is the same artifact with none of
# the pain, and it works identically on Kaggle, Colab, and Lightning.
set -euo pipefail
IN="${1:?usage: frames_to_mp4.sh <frame-dir> [out.mp4] [fps]}"
OUT="${2:-out/render.mp4}"
FPS="${3:-30}"
PATTERN="${PATTERN:-rgb_%04d.png}"

mkdir -p "$(dirname "$OUT")"
ffmpeg -y -framerate "$FPS" -i "$IN/$PATTERN" \
       -c:v libx264 -pix_fmt yuv420p -crf 18 \
       -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" \
       "$OUT"
echo "wrote $OUT"
