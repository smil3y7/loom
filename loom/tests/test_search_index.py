# tests/test_search_index.py
#
# Testi za LocalSearchIndex — pokrivajo optimizacijo iz čistega Python
# O(n) loopa na numpy vektorizirano matrično množenje. Preverjajo
# NUMERIČNO ENAKOST z referenčno _cosine_similarity() implementacijo,
# ne samo da "nekaj vrne" — vektorizacija bi lahko tiho vrnila napačne
# rezultate (napačna os pri normalizaciji, napačen argsort predznak ipd.)
# in bila hkrati hitra in napačna.

import os
import tempfile
from datetime import datetime, timezone

import numpy as np
import pytest

from lib.embeddings import EmbeddingStore, EmbeddingResult
from lib.search import LocalSearchIndex, _cosine_similarity


@pytest.fixture
def indexed_store():
    np.random.seed(7)
    tmp = tempfile.mkdtemp()
    store = EmbeddingStore(os.path.join(tmp, "e.db"))
    raw_vectors = {}
    for i in range(50):
        v = np.random.randn(32).tolist()
        raw_vectors[f"d{i}"] = v
        store.save(EmbeddingResult(
            dream_id=f"d{i}", embedding=v, model="t", provider="t",
            generated_at=datetime.now(timezone.utc).isoformat(), dimension=32,
        ))
    return store, raw_vectors


def test_build_returns_count(indexed_store):
    store, _ = indexed_store
    index = LocalSearchIndex()
    n = index.build(store)
    assert n == 50
    assert index.size == 50
    assert index.is_built


def test_search_matches_reference_cosine_similarity(indexed_store):
    """
    KLJUČNI REGRESIJSKI TEST — numerična enakost z referenčno
    implementacijo. Vektorizacija je optimizacija, ne sme spremeniti
    rezultatov, samo hitrost.
    """
    store, raw_vectors = indexed_store
    index = LocalSearchIndex()
    index.build(store)

    query = np.random.RandomState(99).randn(32).tolist()

    new_results = index.search(query, limit=15)

    reference = sorted(
        ((did, _cosine_similarity(query, v)) for did, v in raw_vectors.items()),
        key=lambda x: x[1], reverse=True,
    )[:15]

    assert [r[0] for r in new_results] == [r[0] for r in reference]
    for (new_id, new_score), (ref_id, ref_score) in zip(new_results, reference):
        assert new_id == ref_id
        assert abs(new_score - ref_score) < 1e-9


def test_find_similar_excludes_self(indexed_store):
    store, _ = indexed_store
    index = LocalSearchIndex()
    index.build(store)

    similar = index.find_similar("d5", limit=10)

    assert len(similar) == 10
    assert "d5" not in [s[0] for s in similar]


def test_search_respects_exclude_ids(indexed_store):
    store, _ = indexed_store
    index = LocalSearchIndex()
    index.build(store)

    query = np.random.RandomState(1).randn(32).tolist()
    results = index.search(query, limit=20, exclude_ids=["d0", "d1", "d2"])

    result_ids = [r[0] for r in results]
    assert "d0" not in result_ids
    assert "d1" not in result_ids
    assert "d2" not in result_ids


def test_search_respects_limit(indexed_store):
    store, _ = indexed_store
    index = LocalSearchIndex()
    index.build(store)

    results = index.search([0.1] * 32, limit=3)
    assert len(results) == 3


def test_unbuilt_index_returns_empty_gracefully():
    index = LocalSearchIndex()
    assert index.search([0.1] * 32) == []
    assert index.find_similar("anything") == []
    assert index.size == 0
    assert not index.is_built


def test_empty_store_builds_to_empty_index():
    tmp = tempfile.mkdtemp()
    store = EmbeddingStore(os.path.join(tmp, "empty.db"))
    index = LocalSearchIndex()
    n = index.build(store)
    assert n == 0
    assert index.is_built  # built je True tudi če je prazen — je pa size 0
    assert index.search([0.1] * 32) == []


def test_zero_vector_query_does_not_crash():
    """Robni primer — poizvedba z ničelnim vektorjem ne sme crashati z
    deljenjem z nič pri normalizaciji."""
    tmp = tempfile.mkdtemp()
    store = EmbeddingStore(os.path.join(tmp, "e.db"))
    store.save(EmbeddingResult(
        dream_id="d1", embedding=[1.0, 0.0, 0.0], model="t", provider="t",
        generated_at=datetime.now(timezone.utc).isoformat(), dimension=3,
    ))
    index = LocalSearchIndex()
    index.build(store)

    results = index.search([0.0, 0.0, 0.0])
    assert results == []
