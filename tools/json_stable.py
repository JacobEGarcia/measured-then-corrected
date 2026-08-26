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


def strip(obj):
    if isinstance(obj, dict):
        return {k: strip(v) for k, v in obj.items() if not VOLATILE.search(k)}
    if isinstance(obj, list):
        return [strip(v) for v in obj]
    return obj


def canonical(path):
    with open(path) as f:
        return json.dumps(strip(json.load(f)), indent=2, sort_keys=True)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(canonical(p))
