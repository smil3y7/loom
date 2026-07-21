# tests/test_adapters.py
#
# Regresijski testi za adapters/browser_atlas.py in adapters/lab.py.
#
# Pokrivajo bug ki je bil dejansko najden in popravljen: error-handling
# fallback v _row_to_canonical() je klical `row.get('SleepCycleID')` na
# sqlite3.Row objektu — ki NE podpira metode .get() (za razliko od dict).
# Če bi glavni try blok kadarkoli vrgel izjemo, bi "varna" except veja
# sama vrgla AttributeError in prekrila pravo napako namesto da bi jo
# gladko zabeležila in nadaljevala.
#
# Test ima dva dela:
#   1. Statični pregled izvorne kode — .get() se ne sme več pojaviti
#      neposredno na sqlite3.Row objektu v teh datotekah.
#   2. Vedenjski dokaz da sqlite3.Row dejansko nima .get() (dokumentira ZAKAJ
#      je bug obstajal) in da je nadomestni vzorec (try/except IndexError) varen.

import re
import sqlite3
import os

import pytest


ADAPTERS_DIR = os.path.join(os.path.dirname(__file__), "..", "adapters")


def test_sqlite_row_has_no_get_method():
    """
    Dokumentira osnovni vzrok buga: sqlite3.Row ni dict in nima .get().
    Če Python kdaj doda .get() na Row (malo verjetno, a za dokumentacijo
    namena tega testa), preostali testi v tej datoteki ostanejo veljavni,
    ta pa bi takrat padel in opozoril da se je predpostavka spremenila.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE t (a INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    row = conn.execute("SELECT * FROM t").fetchone()
    conn.close()

    assert not hasattr(row, "get"), (
        "sqlite3.Row nenadoma podpira .get() — preveri ali je popravek "
        "v adapterjih (try/except namesto .get()) še vedno potreben."
    )


def test_sqlite_row_missing_column_raises_indexerror_not_keyerror():
    """Preveri natančen tip izjeme ki jo mora ujeti fallback koda —
    IndexError, ne KeyError kot bi pričakovali pri navadnem dictu."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE t (a INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    row = conn.execute("SELECT * FROM t").fetchone()
    conn.close()

    with pytest.raises(IndexError):
        _ = row["nonexistent_column"]


def test_safe_row_access_pattern_does_not_crash():
    """
    Dokaže da je popravljen vzorec (try/except IndexError/KeyError) varen
    na sqlite3.Row, tudi ko stolpec ne obstaja — enak vzorec kot je zdaj
    uporabljen v browser_atlas.py in lab.py exception handlerjih.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE t (a INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    row = conn.execute("SELECT * FROM t").fetchone()
    conn.close()

    # Točno ta vzorec je zdaj v adapters/browser_atlas.py:346 in adapters/lab.py:312
    try:
        sc_id = row["SleepCycleID"]  # stolpec ne obstaja
    except (KeyError, IndexError):
        sc_id = "?"

    assert sc_id == "?"  # ni crashalo, gladko se je izteklo na fallback


def test_no_row_get_calls_remain_in_browser_atlas_adapter():
    """Statični regresijski test — prepreči da bi se `.get()` na row
    objektu po nesreči vrnil v kodo (npr. med copy-paste popravkom)."""
    path = os.path.join(ADAPTERS_DIR, "browser_atlas.py")
    content = open(path).read()
    assert not re.search(r"row\.get\(", content), (
        f"{path} ponovno vsebuje row.get() klic — sqlite3.Row te metode "
        "nima, to bo crashalo v except vejah."
    )


def test_no_row_get_calls_remain_in_lab_adapter():
    """Enako za lab.py — bug je bil prisoten v obeh adapterjih."""
    path = os.path.join(ADAPTERS_DIR, "lab.py")
    content = open(path).read()
    assert not re.search(r"row\.get\(", content), (
        f"{path} ponovno vsebuje row.get() klic — sqlite3.Row te metode "
        "nima, to bo crashalo v except vejah."
    )
