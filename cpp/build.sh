#!/usr/bin/env bash
# Build the C++ harness against the MuJoCo library shipped inside the Python
# package -- no separate SDK install, which keeps CI simple.
#
# macOS wrinkle: the dylib's install name is
#   @rpath/mujoco.framework/Versions/A/libmujoco.<ver>.dylib
# but pip ships it as a bare .dylib. So we build a small shim directory with
# the framework layout the linker expects and point rpath at that.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"
MJ="$($PY -c 'import mujoco,os;print(os.path.dirname(mujoco.__file__))')"
LIB="$(ls "$MJ"/libmujoco.*.dylib 2>/dev/null | head -1 || true)"
[ -n "$LIB" ] || { echo "no libmujoco dylib under $MJ" >&2; exit 1; }
VER="$(basename "$LIB" | sed 's/^libmujoco\.//; s/\.dylib$//')"

SHIM="$HERE/.rpath/mujoco.framework/Versions/A"
mkdir -p "$SHIM"
ln -sf "$LIB" "$SHIM/$(basename "$LIB")"

c++ -std=c++17 -O2 -Wall \
    -I"$MJ/include" \
    "$HERE/sim_bench.cpp" \
    "$LIB" \
    -Wl,-rpath,"$HERE/.rpath" \
    -o "$HERE/sim_bench"
echo "built $HERE/sim_bench  (mujoco $VER)"
