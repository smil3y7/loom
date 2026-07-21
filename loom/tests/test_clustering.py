# tests/test_clustering.py
#
# Regresijski testi za lib/clustering.py.
#
# Pokrivajo bug ki je bil dejansko najden in popravljen: ClusteringEngine.run()
# je vsak run shranil nove cluster_id/thread_id vrednosti BREZ brisanja
# prejšnjih — rezultati so se kopičili v bazi namesto da bi se nadomestili.
# Popravek dodaja brisanje + ohranjanje uporabnikovih potrditev prek
# ujemanja dream_id množic (Jaccard prekrivanje).
#
# Ti testi morajo pasti, če se ta logika kadarkoli po nesreči odstrani
# (npr. med prihodnjim refaktorjem clusteringa).

import os
import tempfile
from datetime import datetime, timezone

import numpy as np
import pytest

from lib.embeddings import EmbeddingStore, EmbeddingResult
from lib.clustering import ClusteringEngine


DIM = 40


def _make_embedding(seed_vec: np.ndarray, noise: float = 0.15) -> list:
    """Ustvari šumen, normaliziran vektor okoli danega semena — simulira
    semantično podobne sanje znotraj iste skupine."""
    v = seed_vec + np.random.randn(len(seed_vec)) * noise
    return (v / np.linalg.norm(v)).tolist()


@pytest.fixture
def populated_store():
    """EmbeddingStore s tremi jasno ločenimi semantičnimi skupinami
    (8 sanj vsaka), dovolj za stabilen HDBSCAN clustering v testih."""
    np.random.seed(42)
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "embeddings.db")
    store = EmbeddingStore(db_path)

    seeds = {
        "mesto": np.random.randn(DIM),
        "letenje": np.random.randn(DIM),
        "iskanje": np.random.randn(DIM),
    }

    i = 0
    for _seed_name, seed in seeds.items():
        for _ in range(8):
            store.save(EmbeddingResult(
                dream_id=f"dream_{i}",
                embedding=_make_embedding(seed),
                model="test", provider="test",
                generated_at=datetime.now(timezone.utc).isoformat(),
                dimension=DIM,
            ))
            i += 1

    yield store, tmpdir


@pytest.fixture
def engine(populated_store):
    _store, tmpdir = populated_store
    store, _ = populated_store
    clusters_db = os.path.join(tmpdir, "clusters.db")
    return ClusteringEngine(
        store=store,
        clusters_db_path=clusters_db,
        min_cluster_size=3,
        min_samples=2,
        umap_components=10,  # majhna dimenzija — hitrejši test
    )


def test_run_produces_clusters(engine):
    """Osnovni sanity check — run() na treh ločenih skupinah najde vsaj eno."""
    result = engine.run()
    assert result["clusters"] >= 1
    assert result["total_dreams"] == 24


def test_rerun_does_not_accumulate_clusters(engine):
    """
    KLJUČNI REGRESIJSKI TEST za popravljen bug.

    Pred popravkom: vsak run() je dodal nove vrstice v `clusters`/`threads`
    tabelo brez brisanja starih — baza je po N runih vsebovala N-kratnik
    dejanskih rezultatov, in UI je prikazoval podvojene/zastarele vzorce.
    """
    result1 = engine.run()
    result2 = engine.run()

    import sqlite3
    conn = sqlite3.connect(engine.clusters_db_path)
    total_in_db = conn.execute("SELECT COUNT(*) FROM clusters").fetchone()[0]
    conn.close()

    # Baza sme vsebovati SAMO rezultate zadnjega runa, ne vsote obeh
    assert total_in_db == result2["clusters"], (
        f"Baza vsebuje {total_in_db} clusterjev, pričakovano {result2['clusters']} "
        f"(samo zadnji run) — clustri iz prejšnjega runa niso bili pobrisani."
    )


def test_rerun_old_cluster_ids_are_gone(engine):
    """Cluster ID-ji iz prvega runa ne smejo obstajati po drugem runu —
    dokaz da se ne kopičijo, ne samo da se števila ujemajo po naključju."""
    engine.run()
    clusters_after_run1 = {c.cluster_id for c in engine.get_clusters()}

    engine.run()
    clusters_after_run2 = {c.cluster_id for c in engine.get_clusters()}

    assert clusters_after_run1.isdisjoint(clusters_after_run2), (
        "Cluster ID-ji iz prvega runa se pojavljajo tudi po drugem runu — "
        "stari rezultati niso bili pobrisani."
    )


def test_confirmed_thread_survives_rerun(engine):
    """
    KLJUČNI REGRESIJSKI TEST — stranski učinek popravka dedup buga.

    Ker run() zdaj briše stare threade (da odpravi kopičenje), bi brez
    dodatne logike ohranjanja vsaka uporabnikova potrditev izginila ob
    vsakem ponovnem zagonu clusteringa. Ta test dokazuje da se potrditev
    prenese na novo generiran thread z ustreznim prekrivanjem sanj.
    """
    engine.run()
    threads = engine.get_threads()
    assert len(threads) > 0, "Test predpostavlja da prvi run najde vsaj en thread"

    target = threads[0]
    engine.confirm_thread(target.thread_id, "Moje ime za ta vzorec")

    result2 = engine.run()

    assert result2["confirmations_restored"] >= 1, (
        "Nobena potrditev ni bila obnovljena po ponovnem runu — "
        "uporabnikovo delo bi bilo tiho izgubljeno."
    )

    threads_after = engine.get_threads()
    confirmed_after = [t for t in threads_after if t.confirmed]
    assert any(t.name == "Moje ime za ta vzorec" for t in confirmed_after), (
        "Potrjeno ime ni bilo preneseno na noben thread po ponovnem runu."
    )


def test_rejected_cluster_survives_rerun(engine):
    """Enak princip kot potrditve, ampak za zavrnitve — zavrnjen cluster
    se ne sme 'pojaviti nazaj' kot nepregledan po ponovnem runu."""
    engine.run()
    clusters = engine.get_clusters()
    assert len(clusters) > 0

    target = clusters[0]
    engine.reject_cluster(target.cluster_id)

    engine.run()

    # get_clusters() privzeto izloči zavrnjene (rejected=0 filter) —
    # če je zavrnitev pravilno ohranjena, se ustrezen cluster ne pojavi.
    all_active = engine.get_clusters()
    # Preveri prek direktnega DB dostopa da JE zaznamovan kot rejected,
    # ne samo da manjka (kar bi lahko bilo naključje drugačnega clusteringa)
    import sqlite3
    conn = sqlite3.connect(engine.clusters_db_path)
    rejected_count = conn.execute(
        "SELECT COUNT(*) FROM clusters WHERE rejected = 1"
    ).fetchone()[0]
    conn.close()
    assert rejected_count >= 1, "Zavrnitev ni bila ohranjena po ponovnem runu."


def test_too_few_embeddings_returns_gracefully():
    """Robni primer: manj embedingov kot min_cluster_size ne sme crashati,
    samo vrniti prazen rezultat z razlago."""
    tmpdir = tempfile.mkdtemp()
    store = EmbeddingStore(os.path.join(tmpdir, "e.db"))
    store.save(EmbeddingResult(
        dream_id="only_one", embedding=[0.1] * DIM,
        model="test", provider="test",
        generated_at=datetime.now(timezone.utc).isoformat(), dimension=DIM,
    ))
    engine = ClusteringEngine(
        store=store,
        clusters_db_path=os.path.join(tmpdir, "c.db"),
        min_cluster_size=10,
    )
    result = engine.run()
    assert result["clusters"] == 0
    assert "message" in result
