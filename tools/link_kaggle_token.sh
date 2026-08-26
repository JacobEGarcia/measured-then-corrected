#!/usr/bin/env bash
# Move a freshly-downloaded kaggle.json into place and verify it works.
#   bash tools/link_kaggle_token.sh
set -euo pipefail

SRC=""
for c in "$HOME/Downloads/kaggle.json" "$HOME/Downloads/kaggle (1).json" \
         "$HOME/Desktop/kaggle.json"; do
  [ -f "$c" ] && { SRC="$c"; break; }
done

if [ -z "$SRC" ]; then
  echo "No kaggle.json found in ~/Downloads or ~/Desktop."
  echo
  echo "Get one:  https://www.kaggle.com/settings  ->  API  ->  Create New Token"
  echo "That downloads kaggle.json. Then re-run this script."
  exit 1
fi

mkdir -p "$HOME/.kaggle"
mv "$SRC" "$HOME/.kaggle/kaggle.json"
chmod 600 "$HOME/.kaggle/kaggle.json"
echo "installed token from $SRC"

KG=".venv/bin/kaggle"
[ -x "$KG" ] || KG="kaggle"
echo -n "verifying... "
if $KG config view >/dev/null 2>&1; then
  USER=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.kaggle/kaggle.json')))['username'])")
  echo "OK — authenticated as: $USER"
  echo
  echo "Next:  python3 tools/kaggle_prep.py --user $USER"
else
  echo "FAILED — token present but the API rejected it."
  echo "Try creating a fresh token (the old one is invalidated when you make a new one)."
  exit 1
fi
