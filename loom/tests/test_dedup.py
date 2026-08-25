# tests/test_dedup.py
#
# Testi za lib/dedup.py in njegovo integracijo v LocalSearchIndex in
# ClusteringEngine.
#
# Ozadje: ena Oneiro sanja lahko proizvede do 4 ločene CanonicalDream
# zapise (osnovna sanja / do 3 AI interpretacije / notes), vsi z
# IDENTIČNIM content, različnim samo metadata.extras.oneiro_interpretation.
# Ker embedding temelji izključno na title+content, dobijo skoraj
# identičen vektor. Brez deduplikacije bi se ista sanja pojavila 2-4x v
# iskalnih rezultatih in bi jo clustering odkril kot "vzorec" — v resnici
# gre samo za isto sanjo večkrat.

import os
import tempfile
from datetime import datetime, timezone

import numpy as np
import pytest

from lib.schema import CanonicalDream, DreamMetadata
from lib.dedup import dedup_group_key, pick_representative, compute_representative_ids
from lib.embeddings import EmbeddingStore, EmbeddingResult
from lib.search import LocalSearchIndex


def _oneiro_dream(dream_id, oneiro_id, interp_source=None, interp_mode=None, content="ista vsebina sanje"):
    return CanonicalDream(
        dream_id=dream_id,
        source_app="oneiro",
        timestamp=datetime.now(timezone.utc).isoformat(),
        content=content,
        language="sl",
        metadata=DreamMetadata(extras={
            "oneiro_id": oneiro_id,
            "oneiro_interpretation_source": interp_source,
            "oneiro_interpretation_mode": interp_mode,
        }),
    )


def _plain_dream(dream_id, source_app="browser_atlas"):
    return CanonicalDream(
        dream_id=dream_id,
        source_app=source_app,
        timestamp=datetime.now(timezone.utc).isoformat(),
        content=f"vsebina {dream_id}",
        language="sl",
    )


# ── dedup_group_key ──────────────────────────────────────────────────────────

def test_group_key_shared_for_oneiro_interpretations():
    base = _oneiro_dream("d1", "oneiro-abc", interp_source=None)
    ai1 = _oneiro_dream("d2", "oneiro-abc", interp_source="ai", interp_mode="jungian")
    ai2 = _oneiro_dream("d3", "oneiro-abc", interp_source="ai", interp_mode="shamanic")

    keys = {dedup_group_key(d) for d in (base, ai1, ai2)}
    assert len(keys) == 1, "Vse tri variante iste sanje morajo dobiti isti group key"


def test_group_key_different_for_different_dreams():
    d1 = _oneiro_dream("d1", "oneiro-abc")
    d2 = _oneiro_dream("d2", "oneiro-xyz")
    assert dedup_group_key(d1) != dedup_group_key(d2)


def test_group_key_is_dream_id_for_non_oneiro_sources():
    """Browser/Atlas in Lab nimajo multiplikacije — group key mora biti
    dream_id sam, brez posebne obravnave."""
    d = _plain_dream("some-id", source_app="browser_atlas")
    assert dedup_group_key(d) == "some-id"


def test_group_key_is_dream_id_for_oneiro_dream_without_oneiro_id():
    """Robni primer — oneiro sanja brez oneiro_id v extras (ne bi se smelo
    zgoditi v praksi, ampak ne sme crashati)."""
    d = CanonicalDream(
        dream_id="d1", source_app="oneiro", timestamp="t",
        content="c", language="sl", metadata=DreamMetadata(extras={}),
    )
    assert dedup_group_key(d) == "d1"


# ── pick_representative ──────────────────────────────────────────────────────

def test_pick_representative_prefers_base_dream():
    base = _oneiro_dream("base-id", "oneiro-abc", interp_source=None)
    ai = _oneiro_dream("ai-id", "oneiro-abc", interp_source="ai", interp_mode="jungian")

    rep = pick_representative([ai, base])  # namerno v "napačnem" vrstnem redu
    assert rep.dream_id == "base-id"


def test_pick_representative_falls_back_to_sorted_dream_id_when_no_base():
    """Če nobena varianta ni 'osnovna sanja' (vse imajo interpretacijo),
    izbira mora biti deterministična — vedno ista ne glede na vrstni red."""
    ai1 = _oneiro_dream("zzz-id", "oneiro-abc", interp_source="ai", interp_mode="jungian")
    ai2 = _oneiro_dream("aaa-id", "oneiro-abc", interp_source="ai", interp_mode="shamanic")

    rep1 = pick_representative([ai1, ai2])
    rep2 = pick_representative([ai2, ai1])  # obrnjen vrstni red

    assert rep1.dream_id == rep2.dream_id == "aaa-id"  # najmanjši po sort


# ── compute_representative_ids ───────────────────────────────────────────────

def test_compute_representative_ids_collapses_multi_entry_dream():
    """
    KLJUČNI REGRESIJSKI TEST — natanko scenarij ki je bil dejansko najden:
    ena sanja s 3 AI interpretacijami mora dati SAMO EN reprezentativen ID.
    """
    dreams = {
        "d1": _oneiro_dream("d1", "oneiro-abc", interp_source="ai", interp_mode="neutral"),
        "d2": _oneiro_dream("d2", "oneiro-abc", interp_source="ai", interp_mode="jungian"),
        "d3": _oneiro_dream("d3", "oneiro-abc", interp_source="ai", interp_mode="shamanic"),
    }
    rep_ids = compute_representative_ids(dreams)
    assert len(rep_ids) == 1


def test_compute_representative_ids_preserves_unrelated_dreams():
    """Sanje ki NISO del multi-entry skupine (drugi viri, ali oneiro brez
    interpretacij) morajo ostati vse — dedup ne sme pojesti nepovezanih sanj."""
    dreams = {
        "d1": _oneiro_dream("d1", "oneiro-abc", interp_source="ai", interp_mode="neutral"),
        "d2": _oneiro_dream("d2", "oneiro-abc", interp_source="ai", interp_mode="jungian"),
        "d3": _plain_dream("d3", source_app="browser_atlas"),
        "d4": _plain_dream("d4", source_app="lab"),
    }
    rep_ids = compute_representative_ids(dreams)
    # d1+d2 -> 1 reprezentant, d3 in d4 ostaneta vsak svoj
    assert len(rep_ids) == 3
    assert "d3" in rep_ids
    assert "d4" in rep_ids


def test_compute_representative_ids_matches_real_collision_scenario():
    """
    Reprodukcija dejanskega najdenega scenarija: 28 sanj, nekatere z 1,
    nekatere z več entryji (do 3), skupno 56 zapisov — po dedup mora
    ostati natanko 28 reprezentantov.
    """
    dreams = {}
    entry_i = 0
    # 13 sanj z natanko 1 entryjem (brez interpretacije)
    for i in range(13):
        oid = f"single-{i}"
        did = f"d{entry_i}"
        dreams[did] = _oneiro_dream(did, oid, interp_source=None)
        entry_i += 1
    # 15 sanj z več entryji — simuliraj povprečje ~2.87 da pridemo na 56 skupaj
    # (13*1 + preostanek razporejen na 15 sanj = 43 entryjev na 15 sanj)
    remaining_entries = 56 - 13
    per_dream = remaining_entries // 15
    extra = remaining_entries % 15
    for i in range(15):
        oid = f"multi-{i}"
        n = per_dream + (1 if i < extra else 0)
        for j in range(n):
            did = f"d{entry_i}"
            dreams[did] = _oneiro_dream(did, oid, interp_source="ai", interp_mode=f"mode-{j}")
            entry_i += 1

    assert len(dreams) == 56, f"Test setup napačen: {len(dreams)} namesto 56"

    rep_ids = compute_representative_ids(dreams)
    assert len(rep_ids) == 28, (
        f"Pričakoval 28 reprezentantov (dejanskih sanj), dobil {len(rep_ids)}"
    )


# ── Integracija: LocalSearchIndex ────────────────────────────────────────────

def test_search_index_dedupes_multi_entry_dream():
    """
    KLJUČNI REGRESIJSKI TEST — LocalSearchIndex.build() z dreams_by_id mora
    dejansko izločiti duplikate iz indeksa, ne samo teoretično prek utility
    funkcije. Brez tega popravka bi se ista sanja pojavila 3x v search
    rezultatih.
    """
    tmp = tempfile.mkdtemp()
    store = EmbeddingStore(os.path.join(tmp, "e.db"))

    dreams_by_id = {
        "d1": _oneiro_dream("d1", "oneiro-abc", interp_source=None),
        "d2": _oneiro_dream("d2", "oneiro-abc", interp_source="ai", interp_mode="jungian"),
        "d3": _oneiro_dream("d3", "oneiro-abc", interp_source="ai", interp_mode="shamanic"),
        "d4": _plain_dream("d4", source_app="browser_atlas"),  # nepovezana sanja
    }

    # Vsak dream_id dobi SVOJ (skoraj identičen, ampak ne popolnoma enak
    # zaradi testne ločljivosti) embedding vektor — realno bi bili še bolj
    # podobni, ampak za test dedup logike ni pomembna podobnost vektorjev,
    # samo da vsak dream_id ima embedding v store.
    for i, did in enumerate(dreams_by_id):
        vec = [0.1 * i, 0.2, 0.3]
        store.save(EmbeddingResult(
            dream_id=did, embedding=vec, model="t", provider="t",
            generated_at=datetime.now(timezone.utc).isoformat(), dimension=3,
        ))

    index = LocalSearchIndex()

    # Brez dreams_by_id — staro obnašanje, brez dedup (backward compat)
    count_no_dedup = index.build(store)
    assert count_no_dedup == 4

    # Z dreams_by_id — dedup aktiven
    count_deduped = index.build(store, dreams_by_id)
    assert count_deduped == 2, (
        f"Pričakoval 2 (1 reprezentant za oneiro skupino + 1 nepovezana sanja), "
        f"dobil {count_deduped}"
    )


def test_search_index_backward_compatible_without_dreams_by_id():
    """build() brez dreams_by_id (npr. star klicatelj) mora delovati kot
    prej — nobenega dedup, samo naloži vse embedinge."""
    tmp = tempfile.mkdtemp()
    store = EmbeddingStore(os.path.join(tmp, "e.db"))
    for i in range(3):
        store.save(EmbeddingResult(
            dream_id=f"d{i}", embedding=[0.1, 0.2, 0.3], model="t", provider="t",
            generated_at=datetime.now(timezone.utc).isoformat(), dimension=3,
        ))
    index = LocalSearchIndex()
    count = index.build(store)
    assert count == 3


# ── Integracija: ClusteringEngine ────────────────────────────────────────────

def test_clustering_dedupes_multi_entry_dreams():
    """
    KLJUČNI REGRESIJSKI TEST — ClusteringEngine.run() z dreams_by_id mora
    dejansko filtrirati duplikate PRED HDBSCAN, ne po njem. Preveri prek
    total_dreams v vrnjenem rezultatu, ki mora odsevati dedupliciran nabor,
    ne surovo število embedingov v store.
    """
    from lib.clustering import ClusteringEngine

    np.random.seed(0)
    tmp = tempfile.mkdtemp()
    store = EmbeddingStore(os.path.join(tmp, "e.db"))

    dreams_by_id = {}
    dim = 20

    # Ena "sanja" s 3 skoraj identičnimi entryji (simulira 3 interpretacije)
    base_vec = np.random.randn(dim)
    for i, mode in enumerate(["neutral", "jungian", "shamanic"]):
        did = f"multi-{i}"
        source = None if i == 0 else "ai"
        dreams_by_id[did] = _oneiro_dream(did, "shared-oneiro-id", interp_source=source, interp_mode=mode)
        vec = (base_vec + np.random.randn(dim) * 0.01).tolist()  # skoraj identičen
        store.save(EmbeddingResult(
            dream_id=did, embedding=vec, model="t", provider="t",
            generated_at=datetime.now(timezone.utc).isoformat(), dimension=dim,
        ))

    # 12 nepovezanih sanj (dovolj za min_cluster_size preverjanje da ne pade
    # na "premalo embedingov" prej kot pridemo do dedup logike)
    for i in range(12):
        did = f"single-{i}"
        dreams_by_id[did] = _plain_dream(did, source_app="browser_atlas")
        vec = np.random.randn(dim).tolist()
        store.save(EmbeddingResult(
            dream_id=did, embedding=vec, model="t", provider="t",
            generated_at=datetime.now(timezone.utc).isoformat(), dimension=dim,
        ))

    assert store.count() == 15, "Test setup: 3 multi-entry + 12 single = 15 embedingov v store"

    engine = ClusteringEngine(
        store=store,
        clusters_db_path=os.path.join(tmp, "c.db"),
        min_cluster_size=3, min_samples=2, umap_components=5,
    )

    result = engine.run(dreams_by_id=dreams_by_id)

    assert result["total_dreams"] == 13, (
        f"Pričakoval 13 (1 reprezentant iz multi-entry skupine + 12 nepovezanih), "
        f"dobil {result['total_dreams']} — dedup se ni pravilno prenesel v clustering"
    )
