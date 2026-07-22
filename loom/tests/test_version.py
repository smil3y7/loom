# tests/test_version.py
#
# Test za lib/version.py — bere koren VERSION file, edini vir resnice
# za verzijo Loom projekta (backend, UI in extension so prej vsak
# hardcodirali "0.1.0" ločeno, brez enotnega vira).

import os

from lib.version import get_version


def test_get_version_reads_root_version_file():
    v = get_version()
    assert v, "get_version() ne sme vrniti prazen string"
    assert v != "0.0.0-unknown", (
        "Vrnjena je fallback vrednost — VERSION file ni bil najden na "
        "pričakovani poti relativno na lib/version.py"
    )


def test_version_matches_actual_root_file_content():
    """Preveri da get_version() dejansko bere pravo datoteko, ne
    hardcodirane vrednosti ki se slučajno ujema."""
    here = os.path.dirname(os.path.abspath(__file__))
    version_path = os.path.join(here, "..", "..", "VERSION")

    with open(version_path) as f:
        expected = f.read().strip()

    assert get_version() == expected


def test_version_looks_like_semver():
    """Ne strogo semver validacija, samo sanity check da je oblika smiselna
    (X.Y.Z, morda z dodatnim sufiksom) — lovi grobe napake kot prazen file
    ali napačno formatiran vsebino."""
    v = get_version()
    parts = v.split("-")[0].split(".")
    assert len(parts) == 3, f"Pričakoval X.Y.Z obliko, dobil: {v!r}"
    assert all(p.isdigit() for p in parts), f"Deli verzije morajo biti številke: {v!r}"
