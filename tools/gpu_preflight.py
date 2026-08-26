"""Fail fast if the GPU cannot run what we are about to install.

Drop this at the TOP of an Isaac Sim probe, before the ~18-minute pip install.

Isaac Sim's PhysX requires compute capability >= 7.0. Kaggle's default GPU is
frequently a Tesla P100 (cc 6.0), which passes every check that matters to pip
and then fails inside SimulationApp.__init__ with a single warning line:

    PhysX warning: Minimum GPU compute capability 7.0 is required

By then the run has already burned its install time. Checking first turns a
20-minute failure into a 10-second one, and prints a diagnosis instead of a
stack trace from inside Kit.
"""
import subprocess
import sys

MIN_CC = 7.0


def gpu_info():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,compute_cap",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as exc:                       # no driver at all
        return None, None, f"nvidia-smi unavailable: {exc}"
    if not out:
        return None, None, "nvidia-smi returned nothing"
    first = out.split("\n")[0]
    name, _, cc = first.partition(",")
    try:
        return name.strip(), float(cc.strip()), None
    except ValueError:
        return name.strip(), None, f"could not parse compute_cap from {first!r}"


def require_isaac_capable_gpu(min_cc=MIN_CC, hard=True):
    name, cc, err = gpu_info()
    if err:
        print(f"GPU PREFLIGHT: {err}", flush=True)
        if hard:
            sys.exit(2)
        return False
    ok = cc is not None and cc >= min_cc
    print(f"GPU PREFLIGHT: {name}  compute capability {cc}  "
          f"(need >= {min_cc})  -> {'OK' if ok else 'UNUSABLE'}", flush=True)
    if not ok:
        print("  Isaac Sim's PhysX will fail inside SimulationApp.__init__ on "
              "this device.", flush=True)
        print("  Re-push with:  kaggle kernels push -p . --accelerator "
              "NvidiaTeslaT4", flush=True)
        print("  `enable_gpu: true` alone does NOT pin the GPU model.", flush=True)
        if hard:
            sys.exit(3)
    return ok


if __name__ == "__main__":
    require_isaac_capable_gpu()
