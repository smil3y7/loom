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


def get_version() -> str:
    """Vrne trenutno verzijo, sveže prebrano iz /VERSION ob vsakem klicu.

    NAMERNO BREZ CACHEA: prejšnja implementacija je verzijo cacheirala v
    modulni globalni spremenljivki po prvem branju znotraj procesa — kar je
    neposredno nasprotovalo lastnemu docstringu/komentarju ("bere dinamično
    ob vsakem klicu"). Posledica: če se /VERSION posodobi (npr. extension
    version sync commit), dolgo živeč backend proces (Docker container,
    Tauri sidecar) je še naprej vračal STARO verzijo dokler ni bil ročno
    restartan — kar se je v praksi pokazalo kot UI/Engine version mismatch
    v Nastavitvah, čeprav je /VERSION na disku že imel pravilno vrednost.
    Branje datoteke je poceni (nekaj bajtov), zato cache ni bil potreben za
    performance — samo za slabšo konsistentnost.
    """
    # 1. Eksplicitni override — uporabno za edge-case deploye ali debug
    env_version = os.environ.get("LOOM_VERSION")
    if env_version:
        return env_version.strip()

    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "VERSION"),        # /loom/VERSION (Docker bind mount)
        os.path.join(here, "..", "..", "VERSION"),  # <repo>/VERSION (lokalni checkout)
    ]

    for path in candidates:
        try:
            with open(path) as f:
                return f.read().strip()
        except FileNotFoundError:
            continue

    # Nobena kandidatna pot ni obstajala — ne crashaj zato samo ker se
    # verzija ne izpiše pravilno, samo označi da je neznana.
    return "0.0.0-unknown"
