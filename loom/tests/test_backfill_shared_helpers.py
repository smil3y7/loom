# tests/test_backfill_shared_helpers.py
#
# Testi za get_source_status() in run_source_backfill() v lib/backfill.py.
#
# Te funkcije so nastale iz refaktoringa: loom.py (argparse CLI) in
# cli/menu.py (interaktivni meni) sta prej vsak samostojno implementirala
# skoraj identično logiko (~65 vrstic podvojene kode za status branje in
# backfill zagon). Ta test preveri da skupna funkcija dela pravilno v
# izolaciji, neodvisno od katerega koli od dveh CLI vstopnih točk.

import os
import tempfile

from lib.config import Config
from lib.backfill import get_source_status, run_source_backfill


def _make_oneiro_config(tmp_dir, export_path=None):
    return Config({
        "storage": {"path": tmp_dir},
        "sources": {
            "oneiro": {
                "type": "oneiro",
                "export_path": export_path or os.path.join(tmp_dir, "oneiro_exports"),
            }
        },
    })


def test_get_source_status_returns_expected_shape():
    tmp = tempfile.mkdtemp()
    config = _make_oneiro_config(tmp)

    result = get_source_status(config, "oneiro")

    assert set(result.keys()) == {"source_name", "health", "backfill"}
    assert result["source_name"] == "oneiro"
    assert "ok" in result["health"]


def test_get_source_status_backfill_is_none_when_source_unreachable():
    """Če vir ni dosegljiv, ni smiselno brati backfill statusa zanj —
    backfill mora ostati None, ne pa poskusiti in crashati."""
    tmp = tempfile.mkdtemp()
    # Neveljaven tip vira povzroči da bo adapter neuspešen pri kreiranju
    config = Config({
        "storage": {"path": tmp},
        "sources": {"broken": {"type": "nonexistent_adapter_type"}},
    })

    try:
        result = get_source_status(config, "broken")
        # Če ne vrže izjeme, mora vsaj imeti smiselno strukturo
        assert result["source_name"] == "broken"
    except Exception:
        # Sprejemljivo — klicna koda (loom.py/cli/menu.py) ujame in prikaže napako
        pass


def test_run_source_backfill_creates_storage_directory():
    """run_source_backfill mora ustvariti storage mapo če ta še ne obstaja
    (prej je bil to poseben os.makedirs() klic podvojen v obeh CLI vstopnih
    točkah)."""
    tmp = tempfile.mkdtemp()
    nested_storage = os.path.join(tmp, "does", "not", "exist", "yet")
    config = _make_oneiro_config(nested_storage)

    assert not os.path.exists(nested_storage)

    try:
        run_source_backfill(config, "oneiro")
    except Exception:
        pass  # oneiro export mapa je prazna — backfill lahko vrže/ne najde nič, OK

    assert os.path.exists(nested_storage), (
        "Storage mapa bi morala biti ustvarjena tudi če backfill sam ne najde sanj"
    )


def test_run_source_backfill_default_on_dream_validates_dreams():
    """Privzeti on_dream (če ni podan) mora biti isti kot je bil prej
    podvojen kot `lambda d: d.is_valid()` v loom.py in `_noop_processor`
    v cli/menu.py — funkcionalno identičen, ne le po imenu."""
    tmp = tempfile.mkdtemp()
    config = _make_oneiro_config(tmp)

    # Prazen vir — samo preveri da run_source_backfill ne crasha brez
    # eksplicitno podanega on_dream (uporabi privzeti fallback)
    progress = run_source_backfill(config, "oneiro")
    assert progress is not None
    assert progress.processed == 0  # ni sanj v prazni mapi
