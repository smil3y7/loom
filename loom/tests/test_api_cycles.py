# tests/test_api_cycles.py
#
# API-level test za GET /api/dreams/{dream_id}/cycles — grupiranje spalnih
# ciklov iste noči (parent_dream_id/cycle_index, glej lib/schema.py
# make_parent_id). Uporablja isti pattern kot test_api_ingest.py: pošlje
# sanje prek POST /api/ingest (IngestedDreamStore je enakovreden vir kot
# adapterji za get_dreams(), zato ni potrebe po pravih adapter fixturah).

import tempfile

import pytest
from fastapi.testclient import TestClient

import api.index as api_module
from lib.config import Config


@pytest.fixture
def client():
    """Vsak test dobi svoj prazen storage/cache — isti izolacijski pattern
    kot test_api_ingest.py, brez tega bi si testi delili modulske globalne
    cache-e (_config, _dreams_cache)."""
    tmp = tempfile.mkdtemp()
    api_module._config = Config({"storage": {"path": tmp}, "sources": {}})
    api_module.invalidate_caches()
    yield TestClient(api_module.app)
    api_module._config = None
    api_module.invalidate_caches()


def _dream(dream_id, parent_dream_id=None, cycle_index=None, title=None, content="Sanjska vsebina."):
    d = {
        "dream_id": dream_id,
        "source_app": "browser_atlas",
        "timestamp": f"2026-03-{10 + (cycle_index or 0)}T04:00:00Z",
        "content": content,
        "language": "sl",
        "title": title,
    }
    if parent_dream_id:
        d["parent_dream_id"] = parent_dream_id
    if cycle_index is not None:
        d["cycle_index"] = cycle_index
    return d


def test_single_cycle_dream_without_parent_returns_itself(client):
    """Sanja brez parent_dream_id (npr. Oneiro) mora endpoint vseeno
    obravnavati brezpogojno — vrne samo dano sanjo kot edini cikel, ne 404
    in ne prazen seznam."""
    r = client.post("/api/ingest", json={"dreams": [_dream("solo-1")]})
    assert r.json()["accepted"] == 1

    r = client.get("/api/dreams/solo-1/cycles")
    assert r.status_code == 200
    body = r.json()
    assert body["total_cycles"] == 1
    assert body["parent_dream_id"] is None
    assert body["cycles"][0]["dream_id"] == "solo-1"


def test_multi_cycle_night_groups_and_orders_by_cycle_index(client):
    """Ključni test — več ciklov iste noči (isti parent_dream_id) se
    vrnejo skupaj, urejeni po cycle_index, ne po vrstnem redu vstavljanja."""
    parent = "night-2026-03-15"
    dreams = [
        _dream("cycle-3", parent_dream_id=parent, cycle_index=3, title="Tretji cikel"),
        _dream("cycle-1", parent_dream_id=parent, cycle_index=1, title="Prvi cikel"),
        _dream("cycle-2", parent_dream_id=parent, cycle_index=2, title="Drugi cikel"),
        _dream("other-night", parent_dream_id="night-other", cycle_index=1, title="Druga noč"),
    ]
    r = client.post("/api/ingest", json={"dreams": dreams})
    assert r.json()["accepted"] == 4

    r = client.get("/api/dreams/cycle-2/cycles")
    assert r.status_code == 200
    body = r.json()
    assert body["parent_dream_id"] == parent
    assert body["total_cycles"] == 3
    # Vrstni red mora biti po cycle_index (1, 2, 3), ne po vrstnem redu
    # vstavljanja (poslano kot 3, 1, 2) — in "other-night" ne sme biti zraven.
    assert [c["dream_id"] for c in body["cycles"]] == ["cycle-1", "cycle-2", "cycle-3"]
    assert [c["cycle_index"] for c in body["cycles"]] == [1, 2, 3]


def test_unknown_dream_id_returns_404(client):
    r = client.get("/api/dreams/does-not-exist/cycles")
    assert r.status_code == 404


def test_cycles_include_full_content_and_title(client):
    """UI (FullTextModal) rabi full_content + title na vsakem ciklu, ne
    samo na primarnem — preveri da enrichment ni omejen na prvi element."""
    parent = "night-2026-04-01"
    dreams = [
        _dream("c1", parent_dream_id=parent, cycle_index=1, title="Uvod", content="Prva sanja te noči."),
        _dream("c2", parent_dream_id=parent, cycle_index=2, title="Nadaljevanje", content="Druga sanja te noči."),
    ]
    client.post("/api/ingest", json={"dreams": dreams})

    r = client.get("/api/dreams/c1/cycles")
    cycles = r.json()["cycles"]
    assert cycles[0]["full_content"] == "Prva sanja te noči."
    assert cycles[1]["full_content"] == "Druga sanja te noči."
    assert cycles[1]["title"] == "Nadaljevanje"
