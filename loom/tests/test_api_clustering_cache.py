# tests/test_api_clustering_cache.py
#
# Regresijski test za get_clustering_engine() cache (popravek E).
#
# Tveganje pri dodajanju cache-a: ClusteringEngine instanca se zdaj deli
# med vsemi API klici namesto da bi se ustvarila na novo vsak request.
# Ker ClusteringEngine sam po sebi ne cacheira SQL rezultatov (vsak
# get_clusters()/get_threads() bere sveže iz clusters.db), TO NE SME
# povzročiti da confirm/reject spremembe ne bi bile takoj vidne v
# naslednjem API klicu. Ta test to eksplicitno preveri prek pravega
# HTTP cikla, ne samo enote v izolaciji.

import os
import tempfile
from datetime import datetime, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api.index as api_module
from lib.config import Config
from lib.embeddings import EmbeddingStore, EmbeddingResult


@pytest.fixture
def client_with_clusters():
    """Izoliran storage s tremi semantičnimi skupinami, dovolj za stabilen
    clustering rezultat v testu."""
    np.random.seed(3)
    tmp = tempfile.mkdtemp()
    api_module._config = Config({
        "storage": {"path": tmp},
        "sources": {},
        "clustering": {"min_cluster_size": 3, "min_samples": 2, "umap_components": 8},
    })
    api_module.invalidate_caches()

    store = EmbeddingStore(os.path.join(tmp, "embeddings.db"))
    seeds = {"a": np.random.randn(24), "b": np.random.randn(24), "c": np.random.randn(24)}
    for name, seed in seeds.items():
        for i in range(6):
            v = seed + np.random.randn(24) * 0.1
            v = (v / np.linalg.norm(v)).tolist()
            store.save(EmbeddingResult(
                dream_id=f"{name}_{i}", embedding=v, model="t", provider="t",
                generated_at=datetime.now(timezone.utc).isoformat(), dimension=24,
            ))

    client = TestClient(api_module.app)
    yield client, tmp

    api_module._config = None
    api_module.invalidate_caches()


def test_confirm_via_api_is_immediately_visible_in_next_clusters_call(client_with_clusters):
    """
    KLJUČNI REGRESIJSKI TEST za cache popravek (E).

    Poišče cluster prek /api/clusters, ga potrdi prek /api/clusters/{id}/confirm,
    nato PONOVNO pokliče /api/clusters — potrjeno stanje mora biti vidno takoj,
    ne šele po restartu strežnika. Če bi cache vračal zamrznjeno kopijo
    ClusteringEngine z zastarelim stanjem, bi ta test padel.
    """
    client, _tmp = client_with_clusters

    # Poženi clustering (prek engine direktno — /api/clusters/run ni endpoint,
    # clustering run gre prek CLI; API samo bere rezultate)
    engine = api_module.get_clustering_engine()
    engine.run()

    r1 = client.get("/api/clusters")
    assert r1.status_code == 200
    clusters = r1.json()["clusters"]
    assert len(clusters) > 0, "Test predpostavlja da clustering najde vsaj en cluster"

    target_id = clusters[0]["cluster_id"]
    assert clusters[0]["confirmed"] is False

    r2 = client.post(
        f"/api/clusters/{target_id}/confirm",
        json={"confirmed_type": "location", "confirmed_name": "Testna lokacija"},
    )
    assert r2.status_code == 200

    # Ključni del — nov GET klic mora takoj videti spremembo
    r3 = client.get("/api/clusters")
    updated = {c["cluster_id"]: c for c in r3.json()["clusters"]}
    assert updated[target_id]["confirmed"] is True
    assert updated[target_id]["confirmed_name"] == "Testna lokacija"


def test_clustering_engine_is_reused_not_recreated(client_with_clusters):
    """Dokaže da caching dejansko deluje — dva zaporedna klica get_clustering_engine()
    vrneta ISTO instanco, ne dveh ločenih objektov."""
    client, _tmp = client_with_clusters

    engine1 = api_module.get_clustering_engine()
    engine2 = api_module.get_clustering_engine()

    assert engine1 is engine2


def test_invalidate_caches_forces_new_clustering_engine_instance(client_with_clusters):
    """invalidate_caches() mora počistiti tudi clustering engine cache,
    ne samo dreams/search — sicer bi po /api/ingest ostal star engine."""
    client, _tmp = client_with_clusters

    engine1 = api_module.get_clustering_engine()
    api_module.invalidate_caches()
    engine2 = api_module.get_clustering_engine()

    assert engine1 is not engine2
