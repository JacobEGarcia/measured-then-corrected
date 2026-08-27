"""A validated trot, finally -- and on one robot of three.

JD: "Background in legged locomotion, manipulation, or multi-body systems."

Eleven attempts. The one that worked changed the FRAME rather than fixing the
test stand: a gait generator's output is the foot trajectory relative to the
TRUNK, so measured there, duty and diagonal-pair phase are well-posed whether
or not the robot balances. See model/gait_validation.py for the ten failures.

RESULT: Spot reproduces the commanded trot to within 4.8 degrees. ANYmal and
A1 do not, for reasons that are identified rather than hand-waved.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = json.load(open(os.path.join(HERE, "gait_trunkframe.json")))
BY = {r["name"]: r for r in RAW["robots"]}
COMMANDED_HZ = RAW["gait_hz"]


def ang_gap(a, b):
    """Smallest absolute angle between two phases, in degrees."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def trot_error(robot):
    """A trot has one signature: diagonal pairs move TOGETHER, and the two
    pairs are 180 degrees apart. Scored directly against that, not against a
    duty number whose stance threshold I chose.
    """
    r = BY[robot]
    ph, quad = r.get("phase_offset_deg"), r.get("measured_quadrant")
    if not ph or not quad:
        return None
    byq = {quad[k]: ph[k] for k in ph}
    if set(byq) != {"FL", "FR", "HL", "HR"}:
        return None
    pair_a = ang_gap(byq["FL"], byq["HR"])          # want 0
    pair_b = ang_gap(byq["FR"], byq["HL"])          # want 0
    between = ang_gap(byq["FL"], byq["FR"])         # want 180
    return {"robot": robot, "phase_by_quadrant": byq,
            "diag_FL_HR_deg": round(pair_a, 2),
            "diag_FR_HL_deg": round(pair_b, 2),
            "between_pairs_deg": round(between, 2),
            "worst_deviation_deg": round(
                max(pair_a, pair_b, abs(between - 180.0)), 2)}


def why_the_others_failed():
    """Named causes, from the recorded data -- not a shrug."""
    out = {}
    for name in ("ANYmal", "A1"):
        r = BY[name]
        feet = r.get("foot_prims", {})
        not_feet = {k: v for k, v in feet.items() if "foot" not in v.lower()}
        swings = r.get("swing_ranges_m", {})
        out[name] = {
            "links_that_are_not_feet": not_feet,
            "max_swing_m": max(swings.values()) if swings else None,
            "cause": ("legs never moved -- max foot excursion "
                      f"{max(swings.values()) if swings else 0} m, so the joint "
                      "targets produced no motion at all"
                      if swings and max(swings.values()) < 1e-3 else
                      f"{len(not_feet)} of 4 legs resolved to a shank or thigh "
                      "rather than a foot, so the tracked points are partway up "
                      "the chain and their phase is not the foot's")}
    return out


if __name__ == "__main__":
    print(f"commanded: trot at {COMMANDED_HZ} Hz, diagonal pairs in antiphase\n")
    results = {}
    for name in ("Spot", "ANYmal", "A1"):
        t = trot_error(name)
        results[name] = t
        if not t:
            print(f"  {name:<8} no phase data")
            continue
        v = "TROT CONFIRMED" if t["worst_deviation_deg"] < 15 else "not a trot"
        print(f"  {name:<8} worst deviation {t['worst_deviation_deg']:>6.1f} deg   {v}")

    s = results["Spot"]
    print(f"\nSpot, measured phase by quadrant:")
    for q in ("FL", "FR", "HL", "HR"):
        print(f"    {q}  {s['phase_by_quadrant'][q]:>6.1f} deg")
    print(f"\n    diagonal FL+HR : {s['diag_FL_HR_deg']:>5.1f} deg apart   (ideal 0)")
    print(f"    diagonal FR+HL : {s['diag_FR_HL_deg']:>5.1f} deg apart   (ideal 0)")
    print(f"    between pairs  : {s['between_pairs_deg']:>5.1f} deg        (ideal 180)")

    print("\nwhy the other two did not:")
    for name, w in why_the_others_failed().items():
        print(f"  {name}: {w['cause']}")

    json.dump({"commanded_hz": COMMANDED_HZ, "trot_error": results,
               "failures": why_the_others_failed()},
              open(os.path.join(HERE, "gait_result.json"), "w"), indent=2)
    print("\nwrote model/gait_result.json")
