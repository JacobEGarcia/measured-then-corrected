#!/usr/bin/env bash
# isaacfree — provision Isaac Sim on a Lightning AI Studio (or any Ubuntu GPU box).
#
# Run this ON the Lightning box:
#   bash 02-lightning-setup.sh
#
# This is the ONLY machine where Isaac Sim lives. It has persistent disk, so
# the ~20GB install happens once instead of every session. Everything Kaggle
# consumes is generated here and uploaded as a Dataset.
set -euo pipefail

ISAAC_VERSION="${ISAAC_VERSION:-6.0.1.0}"
VENV="${VENV:-$HOME/isaacenv}"

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

say "1/6  GPU check"
if ! command -v nvidia-smi >/dev/null; then
  echo "FATAL: no nvidia-smi. This Studio has no GPU attached."
  echo "In the Lightning UI, switch the machine type to a GPU (T4 recommended)."
  exit 1
fi
nvidia-smi --query-gpu=name,memory.total,compute_cap,driver_version \
           --format=csv,noheader
CC=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1)
case "$CC" in
  8.0|9.0) echo "WARNING: cc $CC (A100/H100 class) has NO RT cores."
           echo "         Isaac Sim RTX rendering will be unsupported or crawl."
           echo "         Switch to a T4 / L4 / L40S Studio." ;;
  *)       echo "OK: cc $CC has RT cores." ;;
esac

say "2/6  Credit burn warning"
cat <<'NOTE'
Lightning free tier = 80 GPU hours/month (15 credits).
Those hours are GPU-dependent: a T4 stretches to roughly 22 hr, an L40S far
less. STOP THE STUDIO when you are not actively using it -- an idle GPU
Studio burns credits for nothing. The CPU-only Studio runs free 24/7, so do
editing and analysis there and only start the GPU for generation runs.
NOTE

say "3/6  System dependencies"
sudo apt-get update -qq
sudo apt-get install -y -qq --no-install-recommends \
  libglu1-mesa libxrandr2 libxinerama1 libxcursor1 libxi6 libgl1 \
  libglib2.0-0 libsm6 libxext6 libxrender1 libxkbcommon-x11-0 \
  mesa-vulkan-drivers vulkan-tools ffmpeg unzip
echo "vulkaninfo:"; vulkaninfo --summary 2>/dev/null | head -12 || \
  echo "  (vulkaninfo unavailable -- usually still fine headless)"

say "4/6  Python env at $VENV"
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install -q --upgrade pip setuptools wheel

say "5/6  Isaac Sim $ISAAC_VERSION (this is the ~20GB, ~20min step)"
pip install "isaacsim[all,extscache]==${ISAAC_VERSION}" \
    --extra-index-url https://pypi.nvidia.com

say "6/6  Headless smoke test"
cat > "$HOME/.isaac_env" <<'ENVEOF'
export ACCEPT_EULA=Y
export OMNI_KIT_ACCEPT_EULA=YES
export PRIVACY_CONSENT=Y
export OMNI_CACHE_ROOT=$HOME/.cache/omni
ENVEOF
# shellcheck disable=SC1091
source "$HOME/.isaac_env"
mkdir -p "$OMNI_CACHE_ROOT"

python - <<'PY'
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})
import omni.usd
from pxr import UsdGeom
stage = omni.usd.get_context().get_stage()
UsdGeom.Xform.Define(stage, "/World")
UsdGeom.Sphere.Define(stage, "/World/ball")
print("SMOKE_OK prims=", len(list(stage.Traverse())))
app.close()
PY

cat <<EOM

Done. Activate the environment in future sessions with:

    source $VENV/bin/activate && source \$HOME/.isaac_env

FIRST RUN IS SLOW. Isaac Sim compiles shaders on first launch and it can take
10+ minutes with no output. That is normal -- do not kill it. Subsequent runs
hit \$OMNI_CACHE_ROOT and start in well under a minute, which is exactly why
this box has persistent disk and Kaggle does not.
EOM
