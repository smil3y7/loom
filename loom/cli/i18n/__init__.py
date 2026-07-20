# Loom CLI — i18n loader
#
# Dodajanje novega jezika:
#   1. Kopiraj sl.py ali en.py v nov_jezik.py (npr. de.py)
#   2. Prevedi vrednosti (ne ključev)
#   3. Dodaj vnos v AVAILABLE_LANGUAGES spodaj
#   To je vse.

import importlib
import os

# ── Registrirani jeziki ───────────────────────────────────────────────────────
# Dodaj nov jezik sem: "koda": "ime_datoteke_brez_.py"

AVAILABLE_LANGUAGES = {
    "sl": "sl",
    "en": "en",
    # "de": "de",   # primer za nemščino ko bo datoteka de.py narejena
}

DEFAULT_LANGUAGE = "sl"
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", ".loom_settings")

# ── Naložen jezik ─────────────────────────────────────────────────────────────

_current: object = None


def load(lang_code: str = None) -> object:
    """
    Naloži jezikovni modul. Vrne modul z vsemi string konstantami.

    Prioriteta:
      1. lang_code argument
      2. shranjene nastavitve (.loom_settings)
      3. DEFAULT_LANGUAGE
    """
    global _current

    if lang_code is None:
        lang_code = _load_saved_language()

    if lang_code not in AVAILABLE_LANGUAGES:
        lang_code = DEFAULT_LANGUAGE

    module_name = AVAILABLE_LANGUAGES[lang_code]

    try:
        _current = importlib.import_module(f"cli.i18n.{module_name}")
    except ImportError:
        # Fallback na slovenščino
        _current = importlib.import_module("cli.i18n.sl")

    return _current


def get() -> object:
    """Vrni trenutno naložen jezikovni modul. Naloži default če še ni naložen."""
    global _current
    if _current is None:
        load()
    return _current


def t(key: str, **kwargs) -> str:
    """
    Vrni preveden string po ključu.
    Podpira format placeholderje: t("BACKFILL_RUNNING", source="browser_atlas")

    Če ključ ne obstaja, vrni ključ sam (nikoli ne crashaj).
    """
    lang = get()
    value = getattr(lang, key, key)
    if kwargs and isinstance(value, str):
        try:
            value = value.format(**kwargs)
        except KeyError:
            pass
    return value


def set_language(lang_code: str) -> bool:
    """Nastavi jezik in ga shrani za naslednje zagone."""
    if lang_code not in AVAILABLE_LANGUAGES:
        return False
    load(lang_code)
    _save_language(lang_code)
    return True


def available() -> list[tuple[str, str]]:
    """
    Vrni seznam (koda, ime) za vse razpoložljive jezike.
    Npr: [("sl", "Slovenščina"), ("en", "English")]
    """
    result = []
    for code, module_name in AVAILABLE_LANGUAGES.items():
        try:
            mod = importlib.import_module(f"cli.i18n.{module_name}")
            name = getattr(mod, "LANG_NAME", code.upper())
            result.append((code, name))
        except ImportError:
            result.append((code, code.upper()))
    return result


def current_code() -> str:
    """Vrni kodo trenutnega jezika."""
    lang = get()
    return getattr(lang, "LANG_CODE", DEFAULT_LANGUAGE)


# ── Persistent nastavitve ─────────────────────────────────────────────────────

def _load_saved_language() -> str:
    try:
        path = os.path.abspath(SETTINGS_FILE)
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    if line.startswith("language="):
                        return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return DEFAULT_LANGUAGE


def _save_language(lang_code: str):
    try:
        path = os.path.abspath(SETTINGS_FILE)
        # Read existing settings
        settings = {}
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.split("=", 1)
                        settings[k.strip()] = v.strip()
        settings["language"] = lang_code
        with open(path, "w") as f:
            for k, v in settings.items():
                f.write(f"{k}={v}\n")
    except Exception:
        pass
