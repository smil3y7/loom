# tests/test_sqlite_adapter_mixin.py
#
# Testi za SQLiteAdapterMixin (adapters/base.py).
#
# Nastal iz refaktoringa: BrowserAtlasAdapter in LucidLabAdapter sta prej
# vsak imela byte-for-byte identično implementacijo _connect/_get_conn/
# close/__enter__/__exit__ (~20 vrstic podvojene kode). Ta test preveri
# da mixin deluje identično na obeh in da se obnašanje ni spremenilo.

import os
import sqlite3
import tempfile

from adapters.base import SQLiteAdapterMixin
from adapters.browser_atlas import BrowserAtlasAdapter
from adapters.lab import LucidLabAdapter


def _make_test_db(tmp_dir: str) -> str:
    db_path = os.path.join(tmp_dir, "test.sqlite")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE dummy (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    return db_path


def test_both_adapters_inherit_mixin():
    assert issubclass(BrowserAtlasAdapter, SQLiteAdapterMixin)
    assert issubclass(LucidLabAdapter, SQLiteAdapterMixin)


def test_connection_is_lazy():
    """Connection se ne sme odpreti dokler ni dejansko potrebna —
    pomembno za robno delovanje ko baza (še) ne obstaja."""
    adapter = BrowserAtlasAdapter(db_path="/nonexistent/path.sqlite")
    assert adapter._conn is None


def test_get_conn_caches_connection():
    tmp = tempfile.mkdtemp()
    db_path = _make_test_db(tmp)
    adapter = BrowserAtlasAdapter(db_path=db_path)

    conn1 = adapter._get_conn()
    conn2 = adapter._get_conn()

    assert conn1 is conn2, "Ponovni _get_conn() klic mora vrniti isto connection instanco"
    adapter.close()


def test_connection_has_row_factory():
    tmp = tempfile.mkdtemp()
    db_path = _make_test_db(tmp)
    adapter = BrowserAtlasAdapter(db_path=db_path)

    conn = adapter._get_conn()
    assert conn.row_factory == sqlite3.Row
    adapter.close()


def test_connection_is_read_only():
    """PRAGMA query_only mora biti nastavljen — adapterji nikoli ne smejo
    pisati v izvorne baze (CCP princip: adapterji so read-only)."""
    tmp = tempfile.mkdtemp()
    db_path = _make_test_db(tmp)
    adapter = BrowserAtlasAdapter(db_path=db_path)

    conn = adapter._get_conn()
    result = conn.execute("PRAGMA query_only").fetchone()
    assert result[0] == 1

    # Dejanski poskus pisanja mora odpovedati
    try:
        conn.execute("INSERT INTO dummy (id) VALUES (1)")
        conn.commit()
        assert False, "Pisanje bi moralo odpovedati zaradi query_only pragma"
    except sqlite3.OperationalError:
        pass  # pričakovano

    adapter.close()


def test_close_clears_connection():
    tmp = tempfile.mkdtemp()
    db_path = _make_test_db(tmp)
    adapter = BrowserAtlasAdapter(db_path=db_path)

    adapter._get_conn()
    assert adapter._conn is not None
    adapter.close()
    assert adapter._conn is None


def test_close_is_safe_to_call_when_never_connected():
    """close() ne sme crashati če connection nikoli ni bila odprta."""
    adapter = BrowserAtlasAdapter(db_path="/nonexistent/path.sqlite")
    adapter.close()  # ne sme vreči izjeme


def test_context_manager_closes_connection():
    tmp = tempfile.mkdtemp()
    db_path = _make_test_db(tmp)

    with BrowserAtlasAdapter(db_path=db_path) as adapter:
        adapter._get_conn()
        assert adapter._conn is not None

    assert adapter._conn is None, "__exit__ mora zapreti connection"


def test_mixin_behaves_identically_on_lab_adapter():
    """Isti mixin mora dati isto obnašanje na obeh adapterjih — ne samo
    na BrowserAtlasAdapter kjer je bilo testirano zgoraj."""
    tmp = tempfile.mkdtemp()
    db_path = _make_test_db(tmp)
    adapter = LucidLabAdapter(db_path=db_path)

    assert adapter._conn is None
    conn = adapter._get_conn()
    assert conn.row_factory == sqlite3.Row
    adapter.close()
    assert adapter._conn is None
