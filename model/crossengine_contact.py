"""Do the MuJoCo contact findings survive a different solver? Measured in PhysX.

JD: "Experience with physics engines (PhysX, MuJoCo, Bullet, or similar)" /
"validate simulation fidelity."

Two results were measured in MuJoCo elsewhere in this repo:

  A. penetration is MASS-INDEPENDENT when load equals the contacting body's
     own mass (model/contact_tuning.py, model/stability_frontier.py)
  B. the requested contact timeconst is silently CLAMPED to 2*dt, so
     penetration is flat in dt until the clamp engages, then degrades

Neither is a law of physics; both are artefacts of how MuJoCo parameterises
soft contact in TIME units. PhysX is a different solver -- TGS, penetration
based, with an explicit contact offset and rest offset in LENGTH units -- so
there is no reason to assume either carries over.

PREDICTIONS, recorded in the Kaggle probe BEFORE the run:
  A. expected YES, but via the rest offset rather than time normalisation
  B. expected NO -- PhysX has no timeconst, so there is nothing to clamp

Both predictions were confirmed. One of the two REASONS was not: rest_offset
read 0.0 for the whole mass sweep, so whatever makes PhysX mass-independent,
it is not the mechanism I named. Right answer, unverified reasoning.

Isaac Sim 6.0.1 / PhysX on a Kaggle T4; identical experiment in both engines
(one 10 cm box, 2 s settle on a plane).
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- measured -------------------------------------------------------------

MASS_SWEEP_60HZ = {          # kg -> penetration in mm
    "physx":  {0.5: 0.00453, 5.0: 0.00453, 50.0: 0.00452, 500.0: 0.00453},
    "mujoco": {0.5: 0.27583, 5.0: 0.27583, 50.0: 0.27583, 500.0: 0.27583},
}

DT_SWEEP = {                 # Hz -> penetration in mm, 5 kg box
    "physx":  {480: 0.00005, 240: 0.00016, 120: 0.00066, 60: 0.00453, 30: 0.01081},
    "mujoco": {480: 0.10776, 240: 0.10776, 120: 0.10776, 60: 0.27583, 30: 0.67503},
}

REST_OFFSET_SWEEP = {        # PhysX rest_offset in m -> penetration in mm
    0.0: 0.00453, 0.001: -0.99728, 0.005: -4.99684,
}


def agreements():
    """Where the two engines agree, despite sharing no solver code."""
    out = {}
    for eng, d in MASS_SWEEP_60HZ.items():
        v = list(d.values())
        out[eng] = {"spread_mm": round(max(v) - min(v), 6),
                    "range_of_mass": "0.5 kg to 500 kg (1000x)"}
    return out


def disagreements():
    """Where they do not. MuJoCo is FLAT in dt until 2*dt passes solref's
    0.02 s default (between 120 Hz and 60 Hz, exactly as predicted); PhysX
    varies continuously across the whole range with no plateau."""
    mj = DT_SWEEP["mujoco"]
    px = DT_SWEEP["physx"]
    fine = [480, 240, 120]
    return {
        "mujoco_flat_region_hz": fine,
        "mujoco_flat_value_mm": mj[480],
        "mujoco_is_flat_at_fine_dt": len({mj[h] for h in fine}) == 1,
        "mujoco_clamp_onset_between_hz": [120, 60],
        "mujoco_2dt_at_120hz": round(2 / 120, 5),   # 0.01667 < 0.02 -> no clamp
        "mujoco_2dt_at_60hz": round(2 / 60, 5),     # 0.03333 > 0.02 -> clamped
        "physx_is_flat_at_fine_dt": len({px[h] for h in fine}) == 1,
        "physx_monotonic_in_dt": all(px[a] < px[b] for a, b in
                                     zip([480, 240, 120, 60], [240, 120, 60, 30])),
    }


def stiffness_gap():
    return [{"hz": hz,
             "mujoco_mm": DT_SWEEP["mujoco"][hz],
             "physx_mm": DT_SWEEP["physx"][hz],
             "mujoco_over_physx": round(DT_SWEEP["mujoco"][hz] / DT_SWEEP["physx"][hz])}
            for hz in (480, 240, 120, 60, 30)]


def rest_offset_is_a_geometric_standoff():
    """PhysX's rest_offset maps almost 1:1 to a standoff DISTANCE: at 5 mm the
    box comes to rest 5 mm ABOVE geometric contact (negative penetration).
    MuJoCo has no equivalent -- its contact is a time-parameterised spring, so
    'rest 5 mm apart' is not something you can ask for."""
    return [{"rest_offset_m": k, "penetration_mm": v,
             "standoff_mm": round(-v, 5)} for k, v in REST_OFFSET_SWEEP.items()]


if __name__ == "__main__":
    print("AGREEMENT -- penetration is mass-independent in BOTH engines\n")
    print(f"  {'mass':>9} {'PhysX mm':>12} {'MuJoCo mm':>12}")
    for m in (0.5, 5.0, 50.0, 500.0):
        print(f"  {m:>7.1f}kg {MASS_SWEEP_60HZ['physx'][m]:>12.5f} "
              f"{MASS_SWEEP_60HZ['mujoco'][m]:>12.5f}")
    for eng, a in agreements().items():
        print(f"    {eng:<7} spread {a['spread_mm']:.6f} mm over {a['range_of_mass']}")

    print("\nDISAGREEMENT -- how each responds to the timestep\n")
    print(f"  {'rate':>8} {'PhysX mm':>12} {'MuJoCo mm':>12}   {'ratio':>8}")
    for r in stiffness_gap():
        print(f"  {r['hz']:>6} Hz {r['physx_mm']:>12.5f} {r['mujoco_mm']:>12.5f}"
              f"   {r['mujoco_over_physx']:>7}x")
    d = disagreements()
    print(f"\n    MuJoCo is FLAT at 480/240/120 Hz ({d['mujoco_flat_value_mm']} mm),")
    print(f"    then degrades. 2*dt = {d['mujoco_2dt_at_120hz']} at 120 Hz (under")
    print(f"    solref's 0.02 s default) but {d['mujoco_2dt_at_60hz']} at 60 Hz (over it).")
    print("    That is the 2*dt clamp again -- a third independent reproduction.")
    print(f"\n    PhysX is monotonic across the whole range, no plateau: "
          f"{d['physx_monotonic_in_dt']}")

    print("\nPHYSX-ONLY KNOB -- rest_offset is a geometric standoff\n")
    for r in rest_offset_is_a_geometric_standoff():
        print(f"    rest_offset {r['rest_offset_m']:.3f} m -> box rests "
              f"{r['standoff_mm']:>8.3f} mm above contact")

    json.dump({"mass_sweep": MASS_SWEEP_60HZ, "dt_sweep": DT_SWEEP,
               "rest_offset": REST_OFFSET_SWEEP,
               "agreements": agreements(), "disagreements": disagreements(),
               "stiffness_gap": stiffness_gap()},
              open(os.path.join(HERE, "crossengine_contact.json"), "w"), indent=2)
    print("\nwrote model/crossengine_contact.json")
