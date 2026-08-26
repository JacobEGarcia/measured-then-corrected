"""Gates for the friction-cone study."""
import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
import friction_cone as fc

HEADINGS = list(range(0, 91, 5))


@pytest.fixture(scope="module")
def sweeps():
    return {c: [fc.slide_heading(c, h) for h in HEADINGS]
            for c in ("pyramidal", "elliptic")}


def test_elliptic_cone_is_isotropic(sweeps):
    """Coulomb friction is direction-independent, so with the exact cone the
    box must slide the way it was launched, at every heading."""
    e = np.abs([r["direction_error_deg"] for r in sweeps["elliptic"]])
    assert e.max() < 2.0, (
        f"elliptic cone shows {e.max():.3f} deg of direction error; it should "
        "be isotropic to well under a degree")


def test_pyramidal_cone_is_measurably_anisotropic(sweeps):
    p = np.abs([r["direction_error_deg"] for r in sweeps["pyramidal"]])
    assert p.max() > 5.0, (
        f"pyramidal cone only shows {p.max():.3f} deg of error; the "
        "polygon-approximation artefact this study documents has changed")


def test_pyramidal_error_vanishes_on_the_squares_symmetry_axes(sweeps):
    """The signature that identifies this as a square-vs-circle artefact
    rather than generic noise: error is exactly zero at 0, 45 and 90 degrees,
    and antisymmetric about 45."""
    by_h = {r["heading_deg"]: r["direction_error_deg"] for r in sweeps["pyramidal"]}
    for h in (0, 45, 90):
        assert abs(by_h[h]) < 1e-6, f"error at {h} deg is {by_h[h]}, expected 0"
    for h in (5, 20, 35):
        assert by_h[h] == pytest.approx(-by_h[90 - h], abs=1e-6), (
            f"error at {h} and {90-h} deg are not antisymmetric")


def test_the_exact_cone_is_not_slower(sweeps):
    """Guards the REFUTED prediction. I documented pyramidal as the cheap
    option; it is dominated on both axes. If pyramidal ever becomes faster,
    the module's correction note needs rewriting."""
    p = fc.cone_cost("pyramidal", reps=2)
    e = fc.cone_cost("elliptic", reps=2)
    assert e["steps_per_s"] > p["steps_per_s"], (
        f"elliptic {e['steps_per_s']} steps/s vs pyramidal {p['steps_per_s']}; "
        "the exact cone is no longer the faster one")


def test_pyramidal_builds_more_constraint_rows():
    """The partial mechanism: more rows per contact. Stated as partial because
    1.33x the rows does not explain 2.6x the wall-clock."""
    p = fc.constraint_rows("pyramidal")
    e = fc.constraint_rows("elliptic")
    assert p["ncon"] == e["ncon"], "contact counts should match"
    assert p["nefc"] > e["nefc"], (
        f"pyramidal {p['nefc']} rows vs elliptic {e['nefc']}")
