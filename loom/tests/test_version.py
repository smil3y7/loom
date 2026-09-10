# tests/test_version.py
#
# Test za lib/version.py — bere koren VERSION file, edini vir resnice
# za verzijo Loom projekta (backend, UI in extension so prej vsak
# hardcodirali "0.1.0" ločeno, brez enotnega vira).
#
# Vključuje regresijski test za bug: prvotna implementacija je šla vedno
# "dve mapi gor" od lib/version.py, kar deluje za lokalni git checkout
# (loom/lib/version.py → loom/ → <repo>/VERSION) ampak NE znotraj Docker
# containerja, kjer WORKDIR /loom pomeni da je koda na /loom/lib/version.py
# in Docker build context sploh ne vidi monorepo korena — "dve mapi gor"
# pristane na "/" (filesystem root), ne na smiselni lokaciji. Container je
# zato vedno vračal fallback "0.0.0-unknown".

import os
import subprocess
import sys
import tempfile
import shutil

import pytest

from lib.version import get_version


def test_get_version_reads_root_version_file():
    v = get_version()
    assert v, "get_version() ne sme vrniti prazen string"
    assert v != "0.0.0-unknown", (
        "Vrnjena je fallback vrednost — VERSION file ni bil najden na "
        "nobeni od kandidatnih poti"
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


def test_env_var_override_takes_priority():
    """
    KLJUČNI REGRESIJSKI TEST — LOOM_VERSION env var mora imeti prednost
    pred branjem datoteke. To je varnostna mreža za primere ko noben
    kandidatni file-path ne deluje (npr. nestandardna Docker postavitev).
    """
    proc = subprocess.run(
        [sys.executable, "-c", "from lib.version import get_version; print(get_version())"],
        cwd=os.path.join(os.path.dirname(__file__), ".."),
        env={**os.environ, "LOOM_VERSION": "9.9.9-test-override"},
        capture_output=True, text=True,
    )
    assert proc.stdout.strip() == "9.9.9-test-override", proc.stderr


def test_docker_style_path_resolves_one_level_up():
    """
    KLJUČNI REGRESIJSKI TEST za popravljen bug.

    Simulira Docker container filesystem layout: version.py na
    <tmp>/loom/lib/version.py, VERSION bind-mountan na <tmp>/loom/VERSION
    (ENO mapo gor od lib/, ne dve — ker Docker build context ne vidi
    monorepo korena). Pred popravkom je koda gledala samo "dve mapi gor",
    kar bi tukaj pristalo izven <tmp> in vrnilo "0.0.0-unknown".
    """
    tmp = tempfile.mkdtemp()
    try:
        lib_dir = os.path.join(tmp, "loom", "lib")
        os.makedirs(lib_dir)

        # Kopiraj dejansko version.py kodo (ne samo testiraj logiko na novo)
        src = os.path.join(os.path.dirname(__file__), "..", "lib", "version.py")
        shutil.copy(src, os.path.join(lib_dir, "version.py"))

        # VERSION ENO mapo gor od lib/ — simulira Docker bind mount na /loom/VERSION
        with open(os.path.join(tmp, "loom", "VERSION"), "w") as f:
            f.write("7.7.7-docker-sim\n")

        proc = subprocess.run(
            [sys.executable, "-c", "from version import get_version; print(get_version())"],
            cwd=lib_dir,
            env={k: v for k, v in os.environ.items() if k != "LOOM_VERSION"},
            capture_output=True, text=True,
        )
        assert proc.stdout.strip() == "7.7.7-docker-sim", (
            f"Docker-style layout (VERSION eno mapo gor) ni bil razrešen. "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    finally:
        shutil.rmtree(tmp)


def test_local_checkout_style_path_resolves_two_levels_up():
    """Simulira lokalni git checkout layout: version.py na
    <tmp>/repo/loom/lib/version.py, VERSION na <tmp>/repo/VERSION (DVE
    mapi gor od lib/) — to je bilo že prej pravilno, preveri da ostane."""
    tmp = tempfile.mkdtemp()
    try:
        lib_dir = os.path.join(tmp, "repo", "loom", "lib")
        os.makedirs(lib_dir)

        src = os.path.join(os.path.dirname(__file__), "..", "lib", "version.py")
        shutil.copy(src, os.path.join(lib_dir, "version.py"))

        with open(os.path.join(tmp, "repo", "VERSION"), "w") as f:
            f.write("5.5.5-local-sim\n")

        proc = subprocess.run(
            [sys.executable, "-c", "from version import get_version; print(get_version())"],
            cwd=lib_dir,
            env={k: v for k, v in os.environ.items() if k != "LOOM_VERSION"},
            capture_output=True, text=True,
        )
        assert proc.stdout.strip() == "5.5.5-local-sim", (
            f"Lokalni checkout layout (VERSION dve mapi gor) ni bil razrešen. "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    finally:
        shutil.rmtree(tmp)


def test_reads_fresh_on_every_call_no_stale_process_cache():
    """
    KLJUČNI REGRESIJSKI TEST — get_version() ne sme cacheirati vrednosti za
    življenjsko dobo procesa. Prejšnja implementacija je cacheirala v modulni
    globalni spremenljivki po prvem klicu — v dolgo živečem procesu (Docker
    container, Tauri sidecar) je to pomenilo, da posodobitev /VERSION filea
    ni bila vidna dokler proces ni bil ročno restartan (potrjeno v praksi kot
    UI/Engine version mismatch v Nastavitvah).
    """
    tmp = tempfile.mkdtemp()
    try:
        lib_dir = os.path.join(tmp, "repo", "loom", "lib")
        os.makedirs(lib_dir)
        src = os.path.join(os.path.dirname(__file__), "..", "lib", "version.py")
        shutil.copy(src, os.path.join(lib_dir, "version.py"))

        version_path = os.path.join(tmp, "repo", "VERSION")
        with open(version_path, "w") as f:
            f.write("1.0.0-before\n")

        proc = subprocess.run(
            [
                sys.executable, "-c",
                "from version import get_version\n"
                "print(get_version())\n"
                "with open(r'" + version_path + "', 'w') as f:\n"
                "    f.write('2.0.0-after\\n')\n"
                "print(get_version())\n"
            ],
            cwd=lib_dir,
            env={k: v for k, v in os.environ.items() if k != "LOOM_VERSION"},
            capture_output=True, text=True,
        )
        first, second = proc.stdout.strip().split("\n")
        assert first == "1.0.0-before", proc.stderr
        assert second == "2.0.0-after", (
            f"Druga vrednost bi morala odražati posodobljen VERSION file "
            f"znotraj ISTEGA procesa, ne stale cache. stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    finally:
        shutil.rmtree(tmp)


def test_missing_version_file_falls_back_gracefully():
    """Če nobena kandidatna pot ne obstaja in ni env var, mora vrniti
    fallback namesto crashat."""
    tmp = tempfile.mkdtemp()
    try:
        lib_dir = os.path.join(tmp, "isolated", "lib")
        os.makedirs(lib_dir)
        src = os.path.join(os.path.dirname(__file__), "..", "lib", "version.py")
        shutil.copy(src, os.path.join(lib_dir, "version.py"))
        # Namerno NE ustvarimo nobenega VERSION filea

        proc = subprocess.run(
            [sys.executable, "-c", "from version import get_version; print(get_version())"],
            cwd=lib_dir,
            env={k: v for k, v in os.environ.items() if k != "LOOM_VERSION"},
            capture_output=True, text=True,
        )
        assert proc.stdout.strip() == "0.0.0-unknown"
        assert proc.returncode == 0, "Ne sme crashati tudi če VERSION manjka povsod"
    finally:
        shutil.rmtree(tmp)
