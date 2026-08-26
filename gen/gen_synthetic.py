"""
Isaac Sim synthetic data generator -- produces Kaggle Datasets #1 and #2.

Runs ON THE LIGHTNING BOX. Emits a COCO-style detection dataset of simple
graspable objects on a table, with an on/off switch for domain randomization
so notebook 3 can run a genuine controlled experiment.

    # Dataset #1 -- canonical, no randomization (the "naive synthetic" arm)
    python gen/gen_synthetic.py --out out/synth_plain --n 2000 --no-dr

    # Dataset #2 -- domain randomized (the treatment arm)
    python gen/gen_synthetic.py --out out/synth_dr    --n 2000 --dr

Design note: the two arms MUST differ only in randomization. Same object set,
same count, same camera intrinsics, same seed policy. Otherwise notebook 3's
comparison measures the wrong thing, and a controlled experiment that is not
actually controlled is worse than no experiment.
"""
import argparse
import json
import os

for k, v in [("ACCEPT_EULA", "Y"), ("OMNI_KIT_ACCEPT_EULA", "YES"),
             ("PRIVACY_CONSENT", "Y")]:
    os.environ.setdefault(k, v)

from isaacsim import SimulationApp                    # noqa: E402

simulation_app = SimulationApp({"headless": True,
                                "renderer": "RayTracedLighting"})

import omni.replicator.core as rep                    # noqa: E402

CLASSES = ["cube", "sphere", "cylinder", "cone"]


def build_scene(use_dr, seed):
    rep.set_global_seed(seed)

    # --- static scene ------------------------------------------------------
    table = rep.create.plane(scale=2.0, position=(0, 0, 0))
    camera = rep.create.camera(position=(0, -2.2, 1.6),
                               rotation=(-35, 0, 0),
                               focal_length=24.0)

    shapes = {
        "cube": rep.create.cube,
        "sphere": rep.create.sphere,
        "cylinder": rep.create.cylinder,
        "cone": rep.create.cone,
    }
    props = []
    for name, ctor in shapes.items():
        p = ctor(semantics=[("class", name)], scale=0.12,
                 position=(0, 0, 0.2))
        props.append(p)

    # --- per-frame randomization ------------------------------------------
    # Object POSE is randomized in BOTH arms. If objects sat still in the
    # control arm, we would be comparing "varied data vs identical data"
    # rather than isolating appearance randomization, and the result would be
    # trivially in favour of DR for the wrong reason.
    with rep.trigger.on_frame():
        for p in props:
            with p:
                rep.modify.pose(
                    position=rep.distribution.uniform((-0.7, -0.7, 0.06),
                                                      (0.7, 0.7, 0.06)),
                    rotation=rep.distribution.uniform((0, -180, 0),
                                                      (0, 180, 0)),
                )
        if use_dr:
            # --- the treatment: appearance + optics randomization ----------
            for p in props:
                with p:
                    rep.randomizer.color(
                        colors=rep.distribution.uniform((0, 0, 0), (1, 1, 1)))
            with table:
                rep.randomizer.color(
                    colors=rep.distribution.uniform((0, 0, 0), (1, 1, 1)))
            rep.create.light(
                light_type="Sphere",
                intensity=rep.distribution.uniform(2000, 30000),
                temperature=rep.distribution.uniform(2000, 10000),
                position=rep.distribution.uniform((-3, -3, 2), (3, 3, 5)),
                scale=rep.distribution.uniform(0.5, 2.0),
            )
            with camera:
                rep.modify.pose(
                    position=rep.distribution.uniform((-0.5, -2.6, 1.2),
                                                      (0.5, -1.8, 2.0)))
        else:
            # --- the control: one fixed, "studio" lighting setup -----------
            rep.create.light(light_type="Sphere", intensity=12000,
                             temperature=6500, position=(1.5, -1.5, 3.0))
    return camera


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--res", type=int, nargs=2, default=[640, 480])
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dr", dest="dr", action="store_true")
    g.add_argument("--no-dr", dest="dr", action="store_false")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    camera = build_scene(args.dr, args.seed)

    rp = rep.create.render_product(camera, tuple(args.res))
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(
        output_dir=args.out,
        rgb=True,
        bounding_box_2d_tight=True,
        semantic_segmentation=True,
    )
    writer.attach([rp])

    print(f"generating {args.n} frames -> {args.out}  (DR={'ON' if args.dr else 'OFF'})")
    rep.orchestrator.run_until_complete(num_frames=args.n)

    meta = {
        "n_frames": args.n,
        "resolution": args.res,
        "domain_randomization": args.dr,
        "classes": CLASSES,
        "seed": args.seed,
        "generator": "isaacfree/gen/gen_synthetic.py",
        "engine": "Isaac Sim 6.0.1.0 + Replicator",
        "note": ("Control and treatment arms differ ONLY in appearance/optics "
                 "randomization. Object pose is randomized in both."),
    }
    with open(os.path.join(args.out, "dataset_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print("wrote", os.path.join(args.out, "dataset_meta.json"))
    simulation_app.close()


if __name__ == "__main__":
    main()
