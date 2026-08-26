"""
isaacfree — hardened Isaac Sim bootstrap for Kaggle / Colab notebooks.

Usage in a notebook (first cell):

    !pip -q install nothing 2>/dev/null; import sys; sys.path.insert(0,'/kaggle/input/isaacfree-setup')
    from kaggle_bootstrap import preflight, install, ISAAC_VERSION
    preflight()          # prints a go/no-go report, raises nothing
    install()            # only call if preflight said GO

Design notes
------------
Everything here is defensive on purpose. Isaac Sim on a free notebook GPU has
four independent ways to fail (GPU class, GLIBC, disk, network), and the
failure messages the installer gives you are unhelpful. Diagnosing up front is
much cheaper than a 20-minute install that dies at 95%.
"""

import os
import platform
import shutil
import subprocess
import sys

ISAAC_VERSION = "6.0.1.0"
NVIDIA_INDEX = "https://pypi.nvidia.com"
MIN_GLIBC = (2, 34)
MIN_FREE_GB = 25

# Turing (7.5) is the oldest arch with RT cores. T4 = 7.5, L4 = 8.9, L40S = 8.9.
# A100 (8.0) and H100 (9.0) have NO RT cores -- Isaac Sim's RTX renderer is
# unsupported or unusably slow there. This is the single most counterintuitive
# gotcha in free/cloud Isaac Sim work.
NO_RT_CORE_ARCHS = {(8, 0), (9, 0)}


def _sh(cmd):
    try:
        return subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60
        ).stdout.strip()
    except Exception:
        return ""


def _gpu_info():
    out = _sh("nvidia-smi --query-gpu=name,memory.total,compute_cap "
              "--format=csv,noheader")
    if not out:
        return None
    gpus = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        name, mem, cap = parts[0], parts[1], parts[2]
        try:
            cc = tuple(int(x) for x in cap.split("."))
        except ValueError:
            cc = (0, 0)
        gpus.append({"name": name, "mem": mem, "cc": cc})
    return gpus


def _glibc():
    try:
        v = platform.libc_ver()[1]
        return tuple(int(x) for x in v.split(".")[:2])
    except Exception:
        return (0, 0)


def _best_writable_dir():
    """Kaggle caps /kaggle/working at ~20GB while the root disk has more.
    Isaac Sim needs ~20GB of wheels plus a runtime shader cache, so picking the
    roomiest writable mount matters."""
    candidates = ["/kaggle/temp", "/kaggle/working", "/content", "/tmp",
                  os.path.expanduser("~")]
    best, best_free = None, -1
    for c in candidates:
        if not os.path.isdir(c) or not os.access(c, os.W_OK):
            continue
        free = shutil.disk_usage(c).free / 1e9
        if free > best_free:
            best, best_free = c, free
    return best, best_free


def _internet():
    return _sh("curl -s -o /dev/null -w '%{http_code}' "
               "--max-time 10 https://pypi.nvidia.com") == "200"


def preflight(verbose=True):
    """Print a go/no-go report. Returns True if install() is worth attempting."""
    ok = True
    say = print if verbose else (lambda *a, **k: None)

    say("=" * 62)
    say("  isaacfree preflight — Isaac Sim %s" % ISAAC_VERSION)
    say("=" * 62)

    # --- GPU ---
    gpus = _gpu_info()
    if not gpus:
        say("  [FAIL] No NVIDIA GPU visible.")
        say("         Kaggle: Settings -> Accelerator -> GPU T4 x2")
        say("         Colab:  Runtime -> Change runtime type -> T4 GPU")
        ok = False
    else:
        for g in gpus:
            cc = g["cc"]
            if cc in NO_RT_CORE_ARCHS:
                say("  [WARN] %s (cc %d.%d) has NO RT cores." % (g["name"], *cc))
                say("         RTX rendering will be unsupported or crawl.")
                say("         Prefer T4 / L4 / L40S / any RTX card.")
            elif cc >= (7, 5):
                say("  [ OK ] %s, %s, cc %d.%d (RT cores present)"
                    % (g["name"], g["mem"], *cc))
            else:
                say("  [FAIL] %s (cc %d.%d) predates RT cores."
                    % (g["name"], *cc))
                ok = False

    # --- GLIBC ---
    gl = _glibc()
    if sys.platform != "linux":
        say("  [FAIL] Host is %s, not Linux. Isaac Sim is Linux/Windows only."
            % sys.platform)
        say("         There is no macOS build at any version.")
        ok = False
    elif gl >= MIN_GLIBC:
        say("  [ OK ] GLIBC %d.%d (need >= %d.%d)" % (*gl, *MIN_GLIBC))
    else:
        say("  [FAIL] GLIBC %d.%d < %d.%d — the isaacsim wheels will not load."
            % (*gl, *MIN_GLIBC))
        say("         This is a base-image problem, not fixable in-notebook.")
        ok = False

    # --- Disk ---
    d, free = _best_writable_dir()
    if free >= MIN_FREE_GB:
        say("  [ OK ] %.0f GB free at %s" % (free, d))
    else:
        say("  [FAIL] only %.0f GB free at %s (need ~%d GB)"
            % (free, d, MIN_FREE_GB))
        ok = False

    # --- Network ---
    if _internet():
        say("  [ OK ] pypi.nvidia.com reachable")
    else:
        say("  [FAIL] Cannot reach pypi.nvidia.com.")
        say("         Kaggle: notebook settings -> Internet -> ON")
        ok = False

    say("-" * 62)
    say("  VERDICT: %s" % ("GO — run install()" if ok else "NO-GO — see above"))
    if not ok:
        say("  Fallback: skip local generation and load the pre-generated")
        say("  Kaggle Dataset instead. See README 'architectural decision'.")
    say("=" * 62)
    return ok


def install(version=ISAAC_VERSION, extras="all,extscache"):
    """pip-install Isaac Sim, with the env vars headless operation needs."""
    target, _ = _best_writable_dir()

    # Headless Isaac Sim refuses to start without these acknowledgements.
    os.environ["ACCEPT_EULA"] = "Y"
    os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"
    os.environ["PRIVACY_CONSENT"] = "Y"
    # Keep the multi-GB shader/asset cache off the size-capped working dir.
    os.environ["OMNI_CACHE_ROOT"] = os.path.join(target, "omni_cache")
    os.environ["TMPDIR"] = os.path.join(target, "tmp")
    for p in (os.environ["OMNI_CACHE_ROOT"], os.environ["TMPDIR"]):
        os.makedirs(p, exist_ok=True)

    spec = "isaacsim[%s]==%s" % (extras, version)
    cmd = [sys.executable, "-m", "pip", "install", spec,
           "--extra-index-url", NVIDIA_INDEX]
    print("+ " + " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("\n  pip install failed.")
        print("  This is common and usually not repairable in place.")
        print("  Delete the runtime / restart the session and retry once.")
        print("  If it fails twice, use the pre-generated dataset path.")
    return r.returncode == 0


def smoke_test():
    """Prove the install works headlessly. Returns True on success."""
    code = (
        "from isaacsim import SimulationApp\n"
        "app = SimulationApp({'headless': True})\n"
        "import omni.usd\n"
        "from pxr import UsdGeom\n"
        "stage = omni.usd.get_context().get_stage()\n"
        "UsdGeom.Xform.Define(stage, '/World')\n"
        "UsdGeom.Sphere.Define(stage, '/World/ball')\n"
        "print('SMOKE_OK prims=', len(list(stage.Traverse())))\n"
        "app.close()\n"
    )
    r = subprocess.run([sys.executable, "-c", code],
                       capture_output=True, text=True)
    print(r.stdout[-2000:])
    if r.returncode != 0:
        print(r.stderr[-2000:])
    return "SMOKE_OK" in r.stdout


CACHE_TRICK = """
Avoiding the 20GB reinstall every session
-----------------------------------------
Kaggle wipes the disk between sessions, so a naive workflow reinstalls Isaac
Sim (~20 min) every single time. Two ways around it:

1. PREFERRED — do not install Isaac Sim on Kaggle at all. Generate artifacts
   on the persistent Lightning AI box, publish them as a Kaggle Dataset, and
   have the Kaggle notebook consume the dataset. Kaggle then only needs a GPU
   for light training, which takes seconds to set up.

2. If you genuinely need Isaac Sim resident on Kaggle: install once, then

       !tar -C /kaggle/temp -czf /kaggle/working/isaac_env.tgz site-packages

   and publish that tarball as a private Kaggle Dataset. Later sessions attach
   the dataset and untar instead of pip-installing. Watch the 20GB output cap
   on /kaggle/working -- split the archive if needed.

Option 1 is better in almost every case, and it is what this project does.
"""

if __name__ == "__main__":
    if preflight():
        if install():
            print("smoke test:", "PASS" if smoke_test() else "FAIL")
    print(CACHE_TRICK)
