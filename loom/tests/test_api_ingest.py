# tests/test_api_ingest.py
#
# API-level regresijski test za POST /api/ingest — preveri celoten cikel
# skozi FastAPI, ne samo lib/ingested_store.py v izolaciji.

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import api.index as api_module
from lib.config import Config


@pytest.fixture
def client_with_isolated_storage():
    """Vsak test dobi svoj prazen storage — brez tega bi si testi delili
    stanje prek modulskih globalnih cache-ov (_config, _dreams_cache)."""
    tmp = tempfile.mkdtemp()
    api_module._config = Config({"storage": {"path": tmp}, "sources": {}})
    api_module.invalidate_caches()
    yield TestClient(api_module.app), tmp
    api_module._config = None
    api_module.invalidate_caches()


def _valid_payload(dream_id="test-dream-1"):
    return {
        "dreams": [{
            "dream_id": dream_id,
            "source_app": "oneiro",
            "timestamp": "2026-01-01T10:00:00Z",
            "content": "Sanjala sem o starem mestu z ozkimi uličicami.",
            "language": "sl",
            "title": "Staro mesto",
            "metadata": {"lucid": False, "tags": ["mesto"], "emotions": []},
        }]
    }


def test_ingest_accepts_valid_dream(client_with_isolated_storage):
    client, _tmp = client_with_isolated_storage
    r = client.post("/api/ingest", json=_valid_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] == 1
    assert body["rejected"] == 0


def test_ingest_rejects_empty_content(client_with_isolated_storage):
    client, _tmp = client_with_isolated_storage
    payload = _valid_payload()
    payload["dreams"][0]["content"] = "   "  # samo presledki
    r = client.post("/api/ingest", json=payload)
    assert r.status_code == 200
    assert r.json()["accepted"] == 0
    assert r.json()["rejected"] == 1


def test_ingested_dream_is_immediately_visible_in_get_dreams(client_with_isolated_storage):
    """
    KLJUČNI REGRESIJSKI TEST za popravljen bug.

    Pred popravkom: /api/ingest je shranil samo dream_id v embedding queue,
    dejanska vsebina se ni shranila nikamor. get_dreams() bere izključno
    iz adapterjev, zato ta sanja NIKOLI ne bi bila najdena — ne v iskanju,
    ne v clusteringu. Ta test bi s staro kodo padel.
    """
    client, _tmp = client_with_isolated_storage
    r = client.post("/api/ingest", json=_valid_payload(dream_id="visible-test"))
    assert r.status_code == 200
    assert r.json()["accepted"] == 1

    dreams = api_module.get_dreams()
    assert "visible-test" in dreams, (
        "Sanja poslana prek /api/ingest ni vidna v get_dreams() — "
        "vsebina se ni dejansko shranila."
    )
    assert dreams["visible-test"].content == "Sanjala sem o starem mestu z ozkimi uličicami."


def test_ingested_dream_survives_cache_invalidation(client_with_isolated_storage):
    """Podatek mora biti na disku, ne samo v memory cache — po
    invalidate_caches() (simulira nov proces/restart) mora ostati viden."""
    client, _tmp = client_with_isolated_storage
    client.post("/api/ingest", json=_valid_payload(dream_id="durable-test"))

    api_module.invalidate_caches()  # simulira restart / nov proces

    dreams = api_module.get_dreams()
    assert "durable-test" in dreams


def test_ingest_status_reports_ingested_count(client_with_isolated_storage):
    """/api/status mora prikazati koliko sanj je bilo sprejetih prek
    /api/ingest — sicer uporabnik nima vpogleda ali je sync sploh deloval."""
    client, _tmp = client_with_isolated_storage
    client.post("/api/ingest", json=_valid_payload(dream_id="status-test"))

    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["sources"]["ingested_api"]["count"] == 1
