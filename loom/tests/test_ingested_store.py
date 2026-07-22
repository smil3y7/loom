# tests/test_ingested_store.py
#
# Regresijski testi za lib/ingested_store.py in POST /api/ingest.
#
# Pokrivajo bug ki je bil dejansko najden: /api/ingest je sprejel celoten
# CanonicalDream objekt, ampak ga je zavrgel — shranil je samo dream_id v
# embedding queue. Ko je embedding step iskal vsebino prek get_dreams(),
# ta je bral izključno iz adapterjev (datoteke na disku), zato so bile vse
# tako poslane sanje tiho izgubljene.

import os
import tempfile
from datetime import datetime, timezone

import pytest

from lib.schema import CanonicalDream, DreamMetadata
from lib.ingested_store import IngestedDreamStore, merge_dream_sources


def _make_dream(dream_id="d1", content="Vsebina sanje", **kwargs):
    defaults = dict(
        source_app="oneiro",
        timestamp=datetime.now(timezone.utc).isoformat(),
        content=content,
        language="sl",
    )
    defaults.update(kwargs)
    return CanonicalDream(dream_id=dream_id, **defaults)


def test_round_trip_preserves_all_fields():
    """to_dict() → from_dict() ne sme izgubiti podatkov — to je osnova
    na kateri temelji trajno shranjevanje v SQLite."""
    original = _make_dream(
        title="Naslov",
        parent_dream_id="parent-1",
        cycle_index=2,
        metadata=DreamMetadata(
            lucid=True, tags=["a", "b"], emotions=["radost"],
            emotional_tone="positive", is_nightmare=False,
        ),
    )
    restored = CanonicalDream.from_dict(original.to_dict())

    assert restored.dream_id == original.dream_id
    assert restored.content == original.content
    assert restored.title == original.title
    assert restored.parent_dream_id == original.parent_dream_id
    assert restored.cycle_index == original.cycle_index
    assert restored.metadata.lucid == original.metadata.lucid
    assert restored.metadata.tags == original.metadata.tags
    assert restored.metadata.emotional_tone == original.metadata.emotional_tone


def test_save_and_retrieve_dream():
    with tempfile.TemporaryDirectory() as tmp:
        store = IngestedDreamStore(os.path.join(tmp, "ingested.db"))
        dream = _make_dream(content="Prava vsebina sanje")

        store.save(dream)

        loaded = store.get("d1")
        assert loaded is not None
        assert loaded.content == "Prava vsebina sanje"


def test_content_persists_across_store_instances():
    """
    KLJUČNI REGRESIJSKI TEST.

    Simulira restart strežnika — nova instanca IngestedDreamStore mora
    videti podatke shranjene prek stare instance. Brez tega bi bila
    "trajnost" samo v memory cache, ne na disku.
    """
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "ingested.db")

        store1 = IngestedDreamStore(db_path)
        store1.save(_make_dream(dream_id="persistent-1", content="Preživi restart"))

        # Nova instanca — brez sklicevanja na store1
        store2 = IngestedDreamStore(db_path)
        loaded = store2.get("persistent-1")

        assert loaded is not None
        assert loaded.content == "Preživi restart"


def test_save_upserts_not_duplicates():
    """Ponovno poslana sanja z istim dream_id prepiše, ne podvoji."""
    with tempfile.TemporaryDirectory() as tmp:
        store = IngestedDreamStore(os.path.join(tmp, "ingested.db"))

        store.save(_make_dream(dream_id="d1", content="Prva verzija"))
        store.save(_make_dream(dream_id="d1", content="Popravljena verzija"))

        assert store.count() == 1
        assert store.get("d1").content == "Popravljena verzija"


def test_merge_prefers_adapter_source_on_collision():
    """
    Adapter-sourced sanje (iz 'uradnega' izvoznega vira) morajo prevladati
    nad ingested pri istem dream_id — adapter velja za avtoritativen vir.
    """
    adapter_dreams = {"shared-id": _make_dream("shared-id", content="Iz adapterja")}
    ingested_dreams = {"shared-id": _make_dream("shared-id", content="Iz ingesta")}

    merged = merge_dream_sources(adapter_dreams, ingested_dreams)

    assert merged["shared-id"].content == "Iz adapterja"


def test_merge_includes_ingested_only_dreams():
    """Sanje ki obstajajo SAMO v ingested store (še niso pristale v nobeni
    adapter-berljivi datoteki) se morajo pojaviti v končnem naboru."""
    adapter_dreams = {"a1": _make_dream("a1")}
    ingested_dreams = {"a1": _make_dream("a1"), "i1": _make_dream("i1", content="Samo ingest")}

    merged = merge_dream_sources(adapter_dreams, ingested_dreams)

    assert set(merged.keys()) == {"a1", "i1"}
    assert merged["i1"].content == "Samo ingest"


def test_empty_store_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        store = IngestedDreamStore(os.path.join(tmp, "ingested.db"))
        assert store.count() == 0
        assert list(store.get_all()) == []
        assert store.get("nonexistent") is None
