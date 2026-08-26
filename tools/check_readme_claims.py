"""Cross-check the numbers asserted in README.md against the measured JSON.

A findings-first README is a liability the moment a number in it stops matching
the run that produced it. The CI gates protect the CODE; nothing protected the
PROSE, so a refactor could silently leave the headline figures describing a
result that no longer happens.

This walks a table of (claim, where the truth lives, how to read it) and fails
if the README and the data disagree. Every claim is checked against the JSON a
study actually wrote -- not against a copy of the number kept here, which would
just move the problem.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MODEL = os.path.join(REPO, "model")


def load(name):
    p = os.path.join(MODEL, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def readme():
    with open(os.path.join(REPO, "README.md")) as f:
        return f.read()


# Claims are (label, README substring, getter, formatter) for DETERMINISTIC
# quantities, or (..., tol) for ones derived from a clock. Throughput varies
# run to run on the same machine, so quoting a four-decimal microsecond figure
# as if it were a constant is a claim the data cannot support. Those are
# checked within a tolerance, and the ORDERING they exist to demonstrate is
# checked exactly.
def build_checks():
    checks = []

    cc = load("closed_chain.json")
    if cc:
        checks.append((
            "closed chain: open-loop rocker is completely static",
            "0.0000 rad",
            lambda: cc["motion"]["open_rocker_range_rad"],
            lambda v: f"{v:.4f} rad"))
        checks.append((
            "closed chain: closed-loop rocker travel",
            "0.7191 rad",
            lambda: cc["motion"]["closed_rocker_range_rad"],
            lambda v: f"{v:.4f} rad"))
        sm = cc.get("spawn_manifold")
        if sm:
            checks.append((
                "closed chain: worst gap is the spawn transient",
                "step 0",
                lambda: sm["argmax_step"],
                lambda v: f"step {v}"))

    col = load("collision_cost.json")
    if col:
        rows = {r["label"]: r for r in col["normalised"]["rows"]}
        # ABSOLUTE microsecond figures are not checkable. Under load the
        # same two numbers moved 42% and 76% between runs on this machine, so
        # no tolerance makes them meaningful -- widening it until they pass
        # would be a gate that cannot fail. What IS stable, and what the study
        # actually claims, is the set of RELATIONSHIPS. Those are checked
        # exactly; the README labels the table as a single run.
        checks.append((
            "collision: box is cheaper per contact than sphere (ordering)",
            "box is *cheaper* than the sphere",
            lambda: rows["primitive box"]["us_per_contact"]
                    < rows["primitive sphere"]["us_per_contact"],
            lambda v: ("box is *cheaper* than the sphere" if v
                       else "box is NOT cheaper than the sphere")))
        checks.append((
            "collision: hull cost grows SUB-linearly in vertex count (shape)",
            "sub-linear",
            lambda: (col["normalised"]["controlled_mesh_scaling"]["cost_ratio"]
                     < col["normalised"]["controlled_mesh_scaling"]["vertex_ratio"]),
            lambda v: "sub-linear" if v else "LINEAR OR WORSE"))
        checks.append((
            "collision: a 23.5x hull really is the comparison being made",
            "23.5x the hull vertices",
            lambda: col["normalised"]["controlled_mesh_scaling"]["vertex_ratio"],
            lambda v: f"{v}x the hull vertices"))

    det = load("determinism.json")
    if det:
        # The README quotes a CONSENSUS exponent, not a single run. The whole
        # claim of the determinism study is that two independent perturbation
        # sizes (1 ULP and 1e-12) recover the same exponent, so the figure in
        # the prose is their mean. Checking against just the 1-ULP run reported
        # a mismatch (2.24 vs 2.258) that was really a units-of-claim error in
        # this checker, not a drift in the README -- caught on its first run.
        def consensus(a, b):
            return round((det[a]["lyapunov_exponent_per_s"]
                          + det[b]["lyapunov_exponent_per_s"]) / 2.0, 2)

        checks.append((
            "determinism: smooth-chaos Lyapunov exponent (mean of both seeds)",
            "2.25 /s",
            lambda: consensus("chaos_smooth_1ulp", "chaos_smooth_seeded_1e-12"),
            lambda v: f"{v} /s"))
        checks.append((
            "determinism: contact-chaos Lyapunov exponent (mean of both seeds)",
            "0.35 /s",
            lambda: consensus("chaos_contact_1ulp", "chaos_contact_seeded_1e-12"),
            lambda v: f"{v} /s"))
        # and guard the agreement itself, which is what licenses quoting a mean
        checks.append((
            "determinism: the two seeds agree closely enough to quote a mean",
            "1.2%",
            lambda: abs(det["chaos_smooth_1ulp"]["lyapunov_exponent_per_s"]
                        - det["chaos_smooth_seeded_1e-12"]["lyapunov_exponent_per_s"])
                    / det["chaos_smooth_1ulp"]["lyapunov_exponent_per_s"] * 100,
            lambda v: f"{v:.1f}%"))
        pc = det.get("predictive_check")
        if pc:
            checks.append((
                "determinism: measured 1 mm crossing",
                "9.72 s",
                lambda: pc["measured_1mm_s"],
                lambda v: f"{v:.2f} s"))

    ig = load("integrators.json")
    if ig:
        order = {r["integrator"]: r["observed_order"] for r in ig["order"]}
        for integ, want in (("Euler", "1.002"), ("implicit", "0.999"),
                            ("implicitfast", "1.002"), ("RK4", "3.994")):
            checks.append((
                f"integrator order: {integ}",
                want,
                lambda i=integ: order[i],
                lambda v: f"{v:.3f}"))

    fc = load("friction_cone.json")
    if fc:
        checks.append((
            "friction cone: worst pyramidal direction error",
            "12.76",
            lambda: fc["pyramidal_summary"]["max_abs_error_deg"],
            lambda v: f"{v:.2f}"))
        checks.append((
            "friction cone: worst elliptic direction error",
            "0.71",
            lambda: fc["elliptic_summary"]["max_abs_error_deg"],
            lambda v: f"{v:.2f}"))

    ce = load("crossengine_contact.json")
    if ce:
        checks.append((
            "cross-engine: MuJoCo flat penetration at fine dt",
            "0.10776",
            lambda: ce["dt_sweep"]["mujoco"]["480"],
            lambda v: f"{v:.5f}"))
        checks.append((
            "cross-engine: PhysX at 60 Hz",
            "0.00453",
            lambda: ce["dt_sweep"]["physx"]["60"],
            lambda v: f"{v:.5f}"))

    gv = load("gait_validation.json")
    if gv:
        checks.append((
            "gait: Spot's worst foot excursion",
            "0.7561",
            lambda: gv["attempt7"]["Spot"]["z_range_m"]["FR"],
            lambda v: f"{v:.4f}"))

    return checks


def main():
    text = readme()
    checks = build_checks()
    if not checks:
        print("no JSON outputs found -- run the model/ scripts first")
        return 1

    bad = []
    for check in checks:
        label, substring, get, fmt = check[:4]
        tol = check[4] if len(check) > 4 else None
        try:
            measured = get()
        except (KeyError, TypeError, IndexError) as exc:
            bad.append(f"{label}: could not read the measurement ({exc})")
            continue
        if substring not in text:
            bad.append(f"{label}: README no longer contains {substring!r}")
            continue
        rendered = fmt(measured)
        if rendered == substring:
            continue
        if tol is not None:
            try:
                claimed = float(re.sub(r"[^0-9.eE+-]", "", substring))
                if claimed and abs(measured - claimed) / abs(claimed) <= tol:
                    continue
                bad.append(f"{label}: README says {substring!r}, data says "
                           f"{rendered!r} -- outside +/-{tol:.0%}")
                continue
            except (ValueError, TypeError):
                pass
        bad.append(f"{label}: README says {substring!r}, data says {rendered!r}")

    print(f"checked {len(checks)} README claims against measured JSON")
    if bad:
        print(f"\n{len(bad)} MISMATCH(ES):")
        for b in bad:
            print("  -", b)
        return 1
    print("all claims agree with the data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
