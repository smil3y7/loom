# Loom — Version helper
# lib/version.py
#
# Bere /VERSION (koren repozitorija) — edini vir resnice za verzijo Loom
# projekta. Backend jo bere dinamično ob vsakem klicu (poceni, datoteka je
# nekaj bajtov) — nikoli ne rabi ročne posodobitve tukaj, za razliko od
# UI (bere ob buildu) in extension (rabi ročni sync script, ker Chrome
# zahteva statičen niz v manifest.json).

import os

_VERSION_CACHE = None


def get_version() -> str:
    """Vrne trenutno verzijo iz korenskega VERSION filea. Cacheirano po
    prvem branju znotraj enega procesa (datoteka se ne spreminja med tekom)."""
    global _VERSION_CACHE
    if _VERSION_CACHE is not None:
        return _VERSION_CACHE

    # loom/lib/version.py → loom/ → koren repozitorija
    here = os.path.dirname(os.path.abspath(__file__))
    version_path = os.path.join(here, "..", "..", "VERSION")

    try:
        with open(version_path) as f:
            _VERSION_CACHE = f.read().strip()
    except FileNotFoundError:
        # Robno stanje — VERSION file ne bi smel manjkati, ampak ne crashaj
        # zato samo ker se verzija ne izpiše pravilno.
        _VERSION_CACHE = "0.0.0-unknown"

    return _VERSION_CACHE
