"""Strip machine-dependent fields so measured JSON can be diffed meaningfully.

A strict `git diff` on the measured JSON is the right idea -- if a study starts
producing different numbers, that is a finding to review, not a nuisance. But
throughput figures are wall-clock and vary run to run on the same machine, so a
naive diff always fails and the gate gets ignored, which is worse than not
having it.

Anything derived from a timer is dropped here. Everything else -- penetrations,
angles, convergence orders, Lyapunov exponents, stability verdicts -- is
deterministic and must not move.
"""
import json
import os
import re
import sys

# keys whose values come from a clock, directly or by division
VOLATILE = re.compile(
    r"(steps_per_s|us_per_step|us_per_contact|wall_s?|cost_per_simsec|"
    r"_seconds?$|elapsed|cost_ratio)", re.I)
# cost_ratio is one us_per_contact divided by another, so it inherits the
# jitter of both. It swung 4.73 -> 5.53 between two runs on an idle machine,
# which is why the README now quotes a range and a shape rather than a
# three-significant-figure constant.


# Fields that are machine-dependent even though no clock is involved. The
# determinism study measures how fast a perturbation grows, and a 1-ULP
# perturbation sits exactly at the scale of the floating-point differences
# between machines -- so the trajectories it records can never reproduce on a
# second machine (that is the study's own thesis). Even the 1e-12-seeded runs
# differ in their raw trajectory fields; only the fitted exponents (quoted to
# 3 decimals) and the threshold-crossing times come out identical everywhere.
# The pile-of-boxes contact counts in collision_cost are chaotic the same way:
# mean_contacts came out 109.5, 109.7 and 118.5 on three machines. Gating
# these byte-exact produces a gate that fails on every machine but one, which
# is worse than not gating them. Everything else stays byte-exact.
CHAOS_KEYS = re.compile(r"^chaos_.*1ulp")
TRAJECTORY = re.compile(
    r"^(final_separation_m|growth_factor|e_folding_time_s|predicted_1mm_s)$")


SIG_BY_FILE = {"integrators.json": 4}
DEFAULT_SIG = 12


def strip(obj, filename="", parent_key=""):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if VOLATILE.search(k):
                continue
            if filename == "determinism.json":
                if TRAJECTORY.search(k):
                    continue
                if CHAOS_KEYS.search(parent_key) and (
                        k == "lyapunov_exponent_per_s"
                        or k.startswith("t_reach_")):
                    continue
            if filename == "collision_cost.json" and k == "mean_contacts":
                continue
            out[k] = strip(v, filename, k)
        return out
    if isinstance(obj, list):
        return [strip(v, filename, parent_key) for v in obj]
    if isinstance(obj, float):
        # -0.0 and 0.0 are the same number; the sign flips with the machine's
        # rounding path. Values at the noise floor of the units involved
        # (1e-17 m FK residuals, 1e-14 rad static ranges) carry no
        # cross-machine signal. And two machines disagree in the final digits
        # of any long accumulation, so compare at 12 significant figures --
        # four orders of magnitude finer than any claim the README makes.
        # integrators.json needs coarser: its energy-drift and convergence
        # metrics accumulate over millions of steps and agree across machines
        # only to about four significant figures (a real integrator
        # regression moves them by orders of magnitude, so nothing is lost).
        sig = SIG_BY_FILE.get(filename, DEFAULT_SIG)
        if obj == 0.0 or abs(obj) < 1e-12:
            return 0.0
        return float(f"{obj:.{sig}g}")
    return obj


def canonical(path):
    with open(path) as f:
        return json.dumps(strip(json.load(f), os.path.basename(path)),
                          indent=2, sort_keys=True)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(canonical(p))
