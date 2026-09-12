# tests/test_api_ingest.py
#
# API-level regresijski test za POST /api/ingest — preveri celoten cikel
# skozi FastAPI, ne samo lib/ingested_store.py v izolaciji.
#
# Od uvedbe X-Loom-Token avtentikacije (lib/auth.py) vsak klic potrebuje
# veljaven token — fixture ga pridobi prek get_or_create_token() na isti
# izolirani storage poti, ki jo uporablja tudi endpoint sam.

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import api.index as api_module
from lib.config import Config
from lib.auth import get_or_create_token


@pytest.fixture
def client_with_isolated_storage():
    """Vsak test dobi svoj prazen storage — brez tega bi si testi delili
    stanje prek modulskih globalnih cache-ov (_config, _dreams_cache)."""
    tmp = tempfile.mkdtemp()
    api_module._config = Config({"storage": {"path": tmp}, "sources": {}})
    api_module.invalidate_caches()
    token = get_or_create_token(tmp)
    auth_headers = {"X-Loom-Token": token}
    yield TestClient(api_module.app), tmp, auth_headers
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
    client, _tmp, auth = client_with_isolated_storage
    r = client.post("/api/ingest", json=_valid_payload(), headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] == 1
    assert body["rejected"] == 0


def test_ingest_rejects_empty_content(client_with_isolated_storage):
    client, _tmp, auth = client_with_isolated_storage
    payload = _valid_payload()
    payload["dreams"][0]["content"] = "   "  # samo presledki
    r = client.post("/api/ingest", json=payload, headers=auth)
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
    client, _tmp, auth = client_with_isolated_storage
    r = client.post("/api/ingest", json=_valid_payload(dream_id="visible-test"), headers=auth)
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
    client, _tmp, auth = client_with_isolated_storage
    client.post("/api/ingest", json=_valid_payload(dream_id="durable-test"), headers=auth)

    api_module.invalidate_caches()  # simulira restart / nov proces

    dreams = api_module.get_dreams()
    assert "durable-test" in dreams


def test_ingest_status_reports_ingested_count(client_with_isolated_storage):
    """/api/status mora prikazati koliko sanj je bilo sprejetih prek
    /api/ingest — sicer uporabnik nima vpogleda ali je sync sploh deloval."""
    client, _tmp, auth = client_with_isolated_storage
    client.post("/api/ingest", json=_valid_payload(dream_id="status-test"), headers=auth)

    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["sources"]["ingested_api"]["count"] == 1


# ── X-Loom-Token avtentikacija ─────────────────────────────────────────────

def test_ingest_without_token_is_rejected(client_with_isolated_storage):
    """KLJUČNI REGRESIJSKI TEST — prej je /api/ingest sprejel karkoli brez
    ikakršne avtentikacije (glej CHANGELOG 0.3.0)."""
    client, _tmp, _auth = client_with_isolated_storage
    r = client.post("/api/ingest", json=_valid_payload())  # brez headerja
    assert r.status_code == 401


def test_ingest_with_wrong_token_is_rejected(client_with_isolated_storage):
    client, _tmp, _auth = client_with_isolated_storage
    r = client.post("/api/ingest", json=_valid_payload(), headers={"X-Loom-Token": "napacen-token"})
    assert r.status_code == 401


def test_wrong_token_does_not_persist_data(client_with_isolated_storage):
    """Zavrnjena zahteva ne sme pustiti nobene sledi — preveri da sanja z
    napačnim tokenom dejansko ni pristala v store-u."""
    client, _tmp, _auth = client_with_isolated_storage
    client.post("/api/ingest", json=_valid_payload(dream_id="should-not-exist"), headers={"X-Loom-Token": "x"})
    dreams = api_module.get_dreams()
    assert "should-not-exist" not in dreams


def test_get_token_creates_and_returns_consistent_token(client_with_isolated_storage):
    client, _tmp, auth = client_with_isolated_storage
    r = client.get("/api/token")
    assert r.status_code == 200
    assert r.json()["token"] == auth["X-Loom-Token"]


def test_regenerate_token_invalidates_old_pairing(client_with_isolated_storage):
    client, _tmp, auth = client_with_isolated_storage
    # Star token deluje pred regeneracijo
    r = client.post("/api/ingest", json=_valid_payload(dream_id="before-regen"), headers=auth)
    assert r.status_code == 200

    r = client.post("/api/token/regenerate")
    assert r.status_code == 200
    new_token = r.json()["token"]
    assert new_token != auth["X-Loom-Token"]

    # Star token po regeneraciji ne dela več
    r = client.post("/api/ingest", json=_valid_payload(dream_id="after-regen"), headers=auth)
    assert r.status_code == 401

    # Nov token dela
    r = client.post("/api/ingest", json=_valid_payload(dream_id="after-regen-2"), headers={"X-Loom-Token": new_token})
    assert r.status_code == 200
