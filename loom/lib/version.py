# Loom — Version helper
# lib/version.py
#
# Bere /VERSION (koren repozitorija) — edini vir resnice za verzijo Loom
# projekta. Backend jo bere dinamično ob vsakem klicu (poceni, datoteka je
# nekaj bajtov) — nikoli ne rabi ročne posodobitve tukaj, za razliko od
# UI (bere ob buildu) in extension (rabi ročni sync script, ker Chrome
# zahteva statičen niz v manifest.json).
#
# Pot do VERSION ni ista v vseh okoljih kjer ta koda teče:
#   - Lokalno (python loom.py iz git checkouta): lib/version.py je na
#     <repo>/loom/lib/version.py, VERSION je na <repo>/VERSION — dve
#     mapi gor od lib/.
#   - V Docker containerju: WORKDIR je /loom, COPY lib/ ./lib/ pomeni da
#     je koda na /loom/lib/version.py — ampak Docker build context je
#     samo loom/ mapa (ne cel repo), zato monorepo koren sploh ni viden
#     znotraj containerja. VERSION se mora bind-mountati eksplicitno
#     (glej docker-compose.yml: "../VERSION:/loom/VERSION:ro"), kar
#     pomeni da je znotraj containerja dosegljiva ENO mapo gor od lib/
#     (/loom/VERSION), ne dve.
#
# Zato poskusimo več kandidatnih poti, v vrstnem redu od najbolj
# specifičnega (env var override) do najbolj splošnega (privzeti fallback).

import os

_VERSION_CACHE = None


def get_version() -> str:
    """Vrne trenutno verzijo. Cacheirano po prvem branju znotraj procesa."""
    global _VERSION_CACHE
    if _VERSION_CACHE is not None:
        return _VERSION_CACHE

    # 1. Eksplicitni override — uporabno za edge-case deploye ali debug
    env_version = os.environ.get("LOOM_VERSION")
    if env_version:
        _VERSION_CACHE = env_version.strip()
        return _VERSION_CACHE

    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "VERSION"),        # /loom/VERSION (Docker bind mount)
        os.path.join(here, "..", "..", "VERSION"),  # <repo>/VERSION (lokalni checkout)
    ]

    for path in candidates:
        try:
            with open(path) as f:
                _VERSION_CACHE = f.read().strip()
                return _VERSION_CACHE
        except FileNotFoundError:
            continue

    # Nobena kandidatna pot ni obstajala — ne crashaj zato samo ker se
    # verzija ne izpiše pravilno, samo označi da je neznana.
    _VERSION_CACHE = "0.0.0-unknown"
    return _VERSION_CACHE
