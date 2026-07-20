# Loom — Clustering + Thread Detection
# lib/clustering.py
#
# HDBSCAN clustering nad semantičnimi embedingi.
# Zazna ponavljajoče vzorce, lokacije, motive in čustvene strukture.
#
# Filozofija (CCP):
#   - Clusteri so KANDIDATI, ne resnice
#   - Uporabnik vedno potrdi ali zavrne
#   - Engine nikoli ne trdi kaj sanja pomeni
#   - Rezultati so probabilistični, ne deterministični

import os
import json
import sqlite3
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Iterator

from lib.embeddings import EmbeddingStore


# ── Podatkovni modeli ─────────────────────────────────────────────────────────

@dataclass
class DreamCluster:
    """
    En semantični cluster — skupina sanj ki opisujejo podobne izkušnje.
    Cluster je kandidat za thread, lokacijo ali motiv.
    """
    cluster_id: str
    label: str                      # avtomatsko generiran opis
    dream_ids: list[str]
    centroid: list[float]           # povprečni vektor clusterja
    coherence: float                # 0.0-1.0, notranja podobnost
    size: int

    # Temporalni podatki
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    span_days: Optional[int] = None

    # Kandidatni tipi — engine predlaga, user potrdi
    candidate_type: str = "unknown"  # "thread" | "location" | "entity" | "emotion"
    confidence: float = 0.0

    # User feedback
    confirmed: bool = False
    confirmed_type: Optional[str] = None
    confirmed_name: Optional[str] = None
    rejected: bool = False

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "label": self.label,
            "dream_ids": self.dream_ids,
            "coherence": self.coherence,
            "size": self.size,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "span_days": self.span_days,
            "candidate_type": self.candidate_type,
            "confidence": self.confidence,
            "confirmed": self.confirmed,
            "confirmed_type": self.confirmed_type,
            "confirmed_name": self.confirmed_name,
            "rejected": self.rejected,
        }


@dataclass
class CandidateThread:
    """
    Ponavljajoči experiential motiv — thread v CCP terminologiji.
    Ni preprosta oznaka. Je longitudinalni vzorec.

    Primeri: iskanje, padanje, skrite sobe, zamujeni transport,
             poplavljena arhitektura, nestabilna mesta.
    """
    thread_id: str
    name: str                       # candidate ime
    description: str                # kratki opis vzorca
    cluster_ids: list[str]          # clusteri ki sestavljajo thread
    dream_ids: list[str]            # vse sanje v threadu
    recurrence_score: float         # 0.0-1.0
    emotional_signature: dict       # prevladujoča čustva
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    confirmed: bool = False
    rejected: bool = False

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "name": self.name,
            "description": self.description,
            "cluster_ids": self.cluster_ids,
            "dream_ids": self.dream_ids,
            "recurrence_score": self.recurrence_score,
            "emotional_signature": self.emotional_signature,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "confirmed": self.confirmed,
            "rejected": self.rejected,
        }


# ── Clustering engine ─────────────────────────────────────────────────────────

class ClusteringEngine:
    """
    HDBSCAN clustering nad dream embedingi.

    HDBSCAN je idealen za sanje ker:
    - Ne zahteva vnaprejšnjega določanja števila clusterjev
    - Podpira "noise" točke (sanje ki ne sodijo nikamor)
    - Zazna hierarhične strukture
    - Deluje dobro z neenakomernimi gostotami

    Vsak run() je poln refit: prebere VSE embedinge in ponovno izračuna
    UMAP + HDBSCAN od začetka. Ni incremental pristopa — pri velikih
    arhivih (10.000+ sanj) bo to opazno počasnejše z rastjo arhiva.

    Uporabnikove potrditve (confirmed/rejected clusters in threads) se med
    runi ohranijo prek ujemanja dream_id množic (glej _restore_confirmations),
    ker se cluster_id/thread_id vrednosti ob vsakem runu zgenerirajo na novo.
    """

    def __init__(
        self,
        store: EmbeddingStore,
        clusters_db_path: str,
        min_cluster_size: int = 10,
        min_samples: int = 3,
        metric: str = "cosine",
        epsilon: float = 0.0,
        umap_components: int = 50,
        umap_neighbors: int = 15,
    ):
        self.store = store
        self.clusters_db_path = clusters_db_path
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.metric = metric
        self.epsilon = epsilon
        self.umap_components = umap_components
        self.umap_neighbors = umap_neighbors
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.clusters_db_path), exist_ok=True)
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clusters (
                cluster_id      TEXT PRIMARY KEY,
                label           TEXT,
                dream_ids_json  TEXT NOT NULL,
                centroid_json   TEXT NOT NULL,
                coherence       REAL,
                size            INTEGER,
                first_seen      TEXT,
                last_seen       TEXT,
                span_days       INTEGER,
                candidate_type  TEXT DEFAULT 'unknown',
                confidence      REAL DEFAULT 0.0,
                confirmed       INTEGER DEFAULT 0,
                confirmed_type  TEXT,
                confirmed_name  TEXT,
                rejected        INTEGER DEFAULT 0,
                created_at      TEXT,
                updated_at      TEXT
            );

            CREATE TABLE IF NOT EXISTS cluster_dreams (
                cluster_id  TEXT NOT NULL,
                dream_id    TEXT NOT NULL,
                distance    REAL,
                PRIMARY KEY (cluster_id, dream_id)
            );

            CREATE TABLE IF NOT EXISTS threads (
                thread_id               TEXT PRIMARY KEY,
                name                    TEXT,
                description             TEXT,
                cluster_ids_json        TEXT,
                dream_ids_json          TEXT,
                recurrence_score        REAL,
                emotional_signature_json TEXT,
                first_seen              TEXT,
                last_seen               TEXT,
                confirmed               INTEGER DEFAULT 0,
                rejected                INTEGER DEFAULT 0,
                created_at              TEXT,
                updated_at              TEXT
            );

            CREATE TABLE IF NOT EXISTS clustering_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at      TEXT,
                completed_at    TEXT,
                embeddings_used INTEGER,
                clusters_found  INTEGER,
                noise_points    INTEGER,
                status          TEXT DEFAULT 'running'
            );
        """)
        conn.commit()
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.clusters_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Glavna metoda ─────────────────────────────────────────────────────────

    def run(
        self,
        dreams_by_id: dict = None,
        on_progress=None,
    ) -> dict:
        """
        Poženi clustering nad vsemi embedingi. Vedno poln refit (glej opombo
        v docstringu razreda) — prejšnji clustri/threadi se pobrišejo in
        nadomestijo z novimi; potrditve se poskusijo ohraniti.

        Args:
            dreams_by_id: {dream_id: CanonicalDream} za metadata
            on_progress: callback(step, total, message)

        Returns:
            {"clusters": n, "noise": n, "threads": n, "confirmations_restored": n}
        """
        try:
            import hdbscan
        except ImportError:
            raise RuntimeError(
                "hdbscan ni nameščen. Dodaj v requirements.txt: hdbscan>=0.8.33"
            )

        if on_progress:
            on_progress(1, 5, "Nalagam embedinge...")

        # Preden pobrišemo stare rezultate, si zapomnimo uporabnikove potrditve
        # (confirmed clusters/threads) — po novem runu jih poskusimo ujemati
        # nazaj na nove clustre/threade prek prekrivanja dream_id množic.
        previously_confirmed = self._snapshot_confirmations()

        # Naloži vse embedinge
        all_embeddings = list(self.store.get_all())
        if len(all_embeddings) < self.min_cluster_size:
            return {"clusters": 0, "noise": len(all_embeddings), "threads": 0,
                    "message": f"Premalo embedingov ({len(all_embeddings)}). "
                               f"Minimum: {self.min_cluster_size}"}

        dream_ids = [e.dream_id for e in all_embeddings]
        vectors = np.array([e.embedding for e in all_embeddings])

        if on_progress:
            on_progress(2, 5, f"Clustering {len(dream_ids)} sanj...")

        # Normaliziraj vektorje
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vectors_normalized = vectors / norms

        # UMAP dimenzijska redukcija — 384d → 50d
        # Drastično pohitri HDBSCAN in izboljša clustering kvaliteto
        # Za visoko dimenzionalne embedinge je to standard
        if on_progress:
            on_progress(2, 5, f"UMAP redukcija {vectors.shape[1]}d → 50d...")
        try:
            import umap
            reducer = umap.UMAP(
                n_components=self.umap_components,
                n_neighbors=self.umap_neighbors,
                min_dist=0.0,
                metric="cosine",
                random_state=42,
            )
            vectors_reduced = reducer.fit_transform(vectors_normalized)
        except ImportError:
            # UMAP ni nameščen — uporabi PCA kot fallback
            if on_progress:
                on_progress(2, 5, "UMAP ni nameščen, używam PCA fallback...")
            from sklearn.decomposition import PCA
            n_components = min(50, vectors_normalized.shape[0] - 1, vectors_normalized.shape[1])
            pca = PCA(n_components=n_components, random_state=42)
            vectors_reduced = pca.fit_transform(vectors_normalized)

        if on_progress:
            on_progress(3, 5, f"Clustering {len(dream_ids)} sanj...")

        # HDBSCAN na reduciranih vektorjih
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric="euclidean",
            cluster_selection_method="eom",
            cluster_selection_epsilon=self.epsilon,
            prediction_data=True,
        )
        labels = clusterer.fit_predict(vectors_reduced)
        probabilities = clusterer.probabilities_

        # Statistike
        unique_labels = set(labels)
        n_clusters = len(unique_labels - {-1})
        n_noise = int(np.sum(labels == -1))

        if on_progress:
            on_progress(3, 5, f"Najdenih {n_clusters} clusterjev, {n_noise} izoliranih sanj...")

        # Shrani clustering run
        conn = self._connect()

        # Pobriši rezultate prejšnjih runov — clustri/threadi se NE kopičijo.
        # Brez tega vsak nov run doda svoje cluster_id/thread_id poleg starih,
        # in UI prikaže podvojene/zastarele rezultate iz prejšnjih poskusov.
        conn.execute("DELETE FROM cluster_dreams")
        conn.execute("DELETE FROM clusters")
        conn.execute("DELETE FROM threads")
        conn.commit()

        run_id = conn.execute(
            "INSERT INTO clustering_runs (started_at, embeddings_used, status) VALUES (?, ?, 'running')",
            (datetime.now(timezone.utc).isoformat(), len(dream_ids))
        ).lastrowid
        conn.commit()

        # Procesiraj vsak cluster
        saved_clusters = 0
        for cluster_label in sorted(unique_labels - {-1}):
            mask = labels == cluster_label
            cluster_dream_ids = [dream_ids[i] for i in range(len(dream_ids)) if mask[i]]
            cluster_vectors = vectors_normalized[mask]
            cluster_probs = probabilities[mask]

            # Centroid
            centroid = cluster_vectors.mean(axis=0).tolist()

            # Koherentnost — povprečna podobnost do centroida
            coherence = float(np.mean([
                _cosine_sim(v, centroid) for v in cluster_vectors
            ]))

            # Temporalni podatki iz dreams_by_id
            timestamps = []
            emotions = {}
            if dreams_by_id:
                for did in cluster_dream_ids:
                    dream = dreams_by_id.get(did)
                    if dream:
                        timestamps.append(dream.timestamp)
                        for emotion in (dream.metadata.emotions or []):
                            emotions[emotion] = emotions.get(emotion, 0) + 1

            timestamps.sort()
            first_seen = timestamps[0][:10] if timestamps else None
            last_seen = timestamps[-1][:10] if timestamps else None
            span_days = None
            if first_seen and last_seen and first_seen != last_seen:
                from datetime import date
                try:
                    d1 = date.fromisoformat(first_seen)
                    d2 = date.fromisoformat(last_seen)
                    span_days = (d2 - d1).days
                except Exception:
                    pass

            # Candidate type heuristika
            candidate_type, confidence = _classify_cluster(
                size=len(cluster_dream_ids),
                coherence=coherence,
                span_days=span_days or 0,
                emotions=emotions,
            )

            cluster_id = f"cluster_{run_id}_{cluster_label}"
            label = f"Cluster {cluster_label + 1}"

            # Shrani cluster
            conn.execute("""
                INSERT OR REPLACE INTO clusters
                (cluster_id, label, dream_ids_json, centroid_json, coherence, size,
                 first_seen, last_seen, span_days, candidate_type, confidence,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cluster_id, label,
                json.dumps(cluster_dream_ids),
                json.dumps(centroid),
                coherence, len(cluster_dream_ids),
                first_seen, last_seen, span_days,
                candidate_type, confidence,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ))

            # Shrani dream-cluster povezave
            for did, prob in zip(cluster_dream_ids, cluster_probs):
                conn.execute("""
                    INSERT OR REPLACE INTO cluster_dreams (cluster_id, dream_id, distance)
                    VALUES (?, ?, ?)
                """, (cluster_id, did, float(1 - prob)))

            saved_clusters += 1

        conn.commit()

        if on_progress:
            on_progress(4, 5, "Iskam ponavljajoče vzorce (threads)...")

        # Thread detekcija
        n_threads = self._detect_threads(conn, run_id, dreams_by_id)

        # Ponovno uveljavi prejšnje potrditve na novih clustrih/threadih
        # (ujemanje prek prekrivanja dream_id množic, ne prek starih ID-jev
        # ki po novem runu ne obstajajo več).
        restored = self._restore_confirmations(conn, previously_confirmed)

        # Zaključi run
        conn.execute("""
            UPDATE clustering_runs
            SET completed_at = ?, clusters_found = ?, noise_points = ?,
                status = 'completed'
            WHERE id = ?
        """, (datetime.now(timezone.utc).isoformat(), saved_clusters, n_noise, run_id))
        conn.commit()
        conn.close()

        if on_progress:
            on_progress(5, 5, "Končano")

        return {
            "clusters": saved_clusters,
            "noise": n_noise,
            "threads": n_threads,
            "total_dreams": len(dream_ids),
            "confirmations_restored": restored,
        }

    # ── Ohranjanje potrditev med runi ─────────────────────────────────────────

    def _snapshot_confirmations(self) -> dict:
        """
        Zapomni si trenutno potrjene/zavrnjene clustre in threade
        preden jih run() pobriše. Vrne dict z dream_id množicami in
        pripadajočim stanjem, da jih po novem runu lahko ujemamo nazaj.
        """
        conn = self._connect()
        snapshot = {"clusters": [], "threads": []}

        try:
            for row in conn.execute(
                "SELECT dream_ids_json, confirmed, confirmed_type, confirmed_name, rejected "
                "FROM clusters WHERE confirmed = 1 OR rejected = 1"
            ).fetchall():
                snapshot["clusters"].append({
                    "dream_ids": set(json.loads(row["dream_ids_json"])),
                    "confirmed": bool(row["confirmed"]),
                    "confirmed_type": row["confirmed_type"],
                    "confirmed_name": row["confirmed_name"],
                    "rejected": bool(row["rejected"]),
                })

            for row in conn.execute(
                "SELECT dream_ids_json, name, confirmed, rejected "
                "FROM threads WHERE confirmed = 1 OR rejected = 1"
            ).fetchall():
                snapshot["threads"].append({
                    "dream_ids": set(json.loads(row["dream_ids_json"])),
                    "name": row["name"],
                    "confirmed": bool(row["confirmed"]),
                    "rejected": bool(row["rejected"]),
                })
        except sqlite3.OperationalError:
            # Tabeli še ne obstajata (prvi zagon) — ni kaj ohraniti
            pass
        finally:
            conn.close()

        return snapshot

    def _restore_confirmations(self, conn: sqlite3.Connection, snapshot: dict) -> int:
        """
        Poskusi ujemati na novo izračunane clustre/threade s prejšnjimi
        potrjenimi/zavrnjenimi zapisi prek prekrivanja dream_id množic
        (Jaccard prag 0.6 — dovolj strogo da se ne ujemajo naključno
        podobni clustri, dovolj ohlapno da manjše spremembe v clusteringu
        ne izgubijo potrditve).
        """
        THRESHOLD = 0.6
        restored = 0

        def jaccard(a: set, b: set) -> float:
            if not a or not b:
                return 0.0
            inter = len(a & b)
            union = len(a | b)
            return inter / union if union else 0.0

        if snapshot["clusters"]:
            new_clusters = conn.execute(
                "SELECT cluster_id, dream_ids_json FROM clusters"
            ).fetchall()
            for new_row in new_clusters:
                new_ids = set(json.loads(new_row["dream_ids_json"]))
                best, best_score = None, 0.0
                for old in snapshot["clusters"]:
                    score = jaccard(new_ids, old["dream_ids"])
                    if score > best_score:
                        best, best_score = old, score
                if best and best_score >= THRESHOLD:
                    conn.execute("""
                        UPDATE clusters
                        SET confirmed = ?, confirmed_type = ?, confirmed_name = ?, rejected = ?
                        WHERE cluster_id = ?
                    """, (
                        1 if best["confirmed"] else 0,
                        best["confirmed_type"], best["confirmed_name"],
                        1 if best["rejected"] else 0,
                        new_row["cluster_id"],
                    ))
                    restored += 1

        if snapshot["threads"]:
            new_threads = conn.execute(
                "SELECT thread_id, dream_ids_json FROM threads"
            ).fetchall()
            for new_row in new_threads:
                new_ids = set(json.loads(new_row["dream_ids_json"]))
                best, best_score = None, 0.0
                for old in snapshot["threads"]:
                    score = jaccard(new_ids, old["dream_ids"])
                    if score > best_score:
                        best, best_score = old, score
                if best and best_score >= THRESHOLD:
                    if best["confirmed"]:
                        conn.execute("""
                            UPDATE threads SET confirmed = 1, name = ?, rejected = 0
                            WHERE thread_id = ?
                        """, (best["name"], new_row["thread_id"]))
                    else:
                        conn.execute("""
                            UPDATE threads SET rejected = ? WHERE thread_id = ?
                        """, (1 if best["rejected"] else 0, new_row["thread_id"]))
                    restored += 1

        conn.commit()
        return restored

    # ── Thread detekcija ──────────────────────────────────────────────────────

    def _detect_threads(
        self,
        conn: sqlite3.Connection,
        run_id: int,
        dreams_by_id: dict = None,
    ) -> int:
        """
        Zazna candidate threads iz clusterjev.

        Thread je cluster ali skupina clusterjev ki:
        - se pojavlja večkrat (recurrence_score > 0.5)
        - ima temporalno razpršenost (span_days > 30)
        - ima vsaj min_cluster_size sanj
        """
        clusters = conn.execute("""
            SELECT * FROM clusters
            WHERE cluster_id LIKE ? AND rejected = 0
            ORDER BY size DESC
        """, (f"cluster_{run_id}_%",)).fetchall()

        n_threads = 0

        for cluster in clusters:
            dream_ids = json.loads(cluster["dream_ids_json"])
            span_days = cluster["span_days"] or 0
            size = cluster["size"]
            coherence = cluster["coherence"]

            # Recurrence score — kombinacija velikosti, razpona in koherentnosti
            recurrence_score = _compute_recurrence_score(
                size=size,
                span_days=span_days,
                coherence=coherence,
            )

            # Thread postane kandidat pri recurrence_score > 0.4
            # in vsaj 3 sanjah v vsaj 2 različnih mesecih
            if recurrence_score < 0.4 or size < 3:
                continue

            # Preveri temporalno razpršenost
            if dreams_by_id and span_days < 14:
                continue

            thread_id = f"thread_{run_id}_{cluster['cluster_id']}"

            # Čustveni podpis
            emotions = {}
            if dreams_by_id:
                for did in dream_ids:
                    dream = dreams_by_id.get(did)
                    if dream:
                        for e in (dream.metadata.emotions or []):
                            emotions[e] = emotions.get(e, 0) + 1

            # Normaliziraj čustva
            total = sum(emotions.values())
            if total > 0:
                emotions = {k: round(v / total, 2) for k, v in emotions.items()}

            conn.execute("""
                INSERT OR REPLACE INTO threads
                (thread_id, name, description, cluster_ids_json, dream_ids_json,
                 recurrence_score, emotional_signature_json,
                 first_seen, last_seen, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                thread_id,
                f"Vzorec {n_threads + 1}",
                f"Ponavljajoči vzorec v {size} sanjah skozi {span_days} dni",
                json.dumps([cluster["cluster_id"]]),
                json.dumps(dream_ids),
                round(recurrence_score, 3),
                json.dumps(emotions),
                cluster["first_seen"],
                cluster["last_seen"],
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ))
            n_threads += 1

        conn.commit()
        return n_threads

    # ── Bralne metode ─────────────────────────────────────────────────────────

    def get_clusters(
        self,
        confirmed_only: bool = False,
        min_size: int = 1,
        candidate_type: str = None,
    ) -> list[DreamCluster]:
        conn = self._connect()
        query = "SELECT * FROM clusters WHERE rejected = 0 AND size >= ?"
        params = [min_size]
        if confirmed_only:
            query += " AND confirmed = 1"
        if candidate_type:
            query += " AND candidate_type = ?"
            params.append(candidate_type)
        query += " ORDER BY size DESC"

        rows = conn.execute(query, params).fetchall()
        conn.close()

        clusters = []
        for row in rows:
            clusters.append(DreamCluster(
                cluster_id=row["cluster_id"],
                label=row["label"],
                dream_ids=json.loads(row["dream_ids_json"]),
                centroid=json.loads(row["centroid_json"]),
                coherence=row["coherence"] or 0.0,
                size=row["size"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                span_days=row["span_days"],
                candidate_type=row["candidate_type"],
                confidence=row["confidence"] or 0.0,
                confirmed=bool(row["confirmed"]),
                confirmed_type=row["confirmed_type"],
                confirmed_name=row["confirmed_name"],
                rejected=bool(row["rejected"]),
            ))
        return clusters

    def get_threads(self, confirmed_only: bool = False) -> list[CandidateThread]:
        conn = self._connect()
        query = "SELECT * FROM threads WHERE rejected = 0"
        if confirmed_only:
            query += " AND confirmed = 1"
        query += " ORDER BY recurrence_score DESC"

        rows = conn.execute(query).fetchall()
        conn.close()

        threads = []
        for row in rows:
            threads.append(CandidateThread(
                thread_id=row["thread_id"],
                name=row["name"],
                description=row["description"],
                cluster_ids=json.loads(row["cluster_ids_json"]),
                dream_ids=json.loads(row["dream_ids_json"]),
                recurrence_score=row["recurrence_score"],
                emotional_signature=json.loads(row["emotional_signature_json"] or "{}"),
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                confirmed=bool(row["confirmed"]),
                rejected=bool(row["rejected"]),
            ))
        return threads

    def get_clusters_for_dream(self, dream_id: str) -> list[str]:
        """Vrni cluster_id-je za dano sanje."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT cluster_id FROM cluster_dreams WHERE dream_id = ?",
            (dream_id,)
        ).fetchall()
        conn.close()
        return [r["cluster_id"] for r in rows]

    # ── User feedback ─────────────────────────────────────────────────────────

    def confirm_cluster(
        self,
        cluster_id: str,
        confirmed_type: str,
        confirmed_name: str,
    ):
        """Uporabnik potrdi cluster kot thread/lokacijo/entiteto."""
        conn = self._connect()
        conn.execute("""
            UPDATE clusters
            SET confirmed = 1, confirmed_type = ?, confirmed_name = ?,
                updated_at = ?
            WHERE cluster_id = ?
        """, (confirmed_type, confirmed_name,
              datetime.now(timezone.utc).isoformat(), cluster_id))
        conn.commit()
        conn.close()

    def reject_cluster(self, cluster_id: str):
        """Uporabnik zavrne cluster."""
        conn = self._connect()
        conn.execute("""
            UPDATE clusters SET rejected = 1, updated_at = ? WHERE cluster_id = ?
        """, (datetime.now(timezone.utc).isoformat(), cluster_id))
        conn.commit()
        conn.close()

    def confirm_thread(self, thread_id: str, name: str):
        conn = self._connect()
        conn.execute("""
            UPDATE threads SET confirmed = 1, name = ?, updated_at = ?
            WHERE thread_id = ?
        """, (name, datetime.now(timezone.utc).isoformat(), thread_id))
        conn.commit()
        conn.close()

    def reject_thread(self, thread_id: str):
        conn = self._connect()
        conn.execute("""
            UPDATE threads SET rejected = 1, updated_at = ? WHERE thread_id = ?
        """, (datetime.now(timezone.utc).isoformat(), thread_id))
        conn.commit()
        conn.close()

    def status(self) -> dict:
        conn = self._connect()
        n_clusters = conn.execute(
            "SELECT COUNT(*) FROM clusters WHERE rejected = 0"
        ).fetchone()[0]
        n_confirmed = conn.execute(
            "SELECT COUNT(*) FROM clusters WHERE confirmed = 1"
        ).fetchone()[0]
        n_threads = conn.execute(
            "SELECT COUNT(*) FROM threads WHERE rejected = 0"
        ).fetchone()[0]
        last_run = conn.execute(
            "SELECT * FROM clustering_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()

        return {
            "clusters": n_clusters,
            "confirmed_clusters": n_confirmed,
            "threads": n_threads,
            "last_run": dict(last_run) if last_run else None,
        }


# ── Pomožne funkcije ──────────────────────────────────────────────────────────

def _cosine_sim(a, b) -> float:
    a, b = np.array(a), np.array(b)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _classify_cluster(
    size: int,
    coherence: float,
    span_days: int,
    emotions: dict,
) -> tuple[str, float]:
    """
    Heuristična klasifikacija cluster tipa.
    Vrne (candidate_type, confidence).

    Tipe določa kombinacija značilnosti:
    - thread:    dolg razpon, srednja koherentnost, ponavljajoča čustva
    - location:  visoka koherentnost, prostorske asociacije
    - entity:    manjši cluster, visoka koherentnost
    - emotion:   prevladujoče čustvo
    """
    # Prevladujoče čustvo
    dominant_emotion = max(emotions, key=emotions.get) if emotions else None
    emotion_dominance = emotions.get(dominant_emotion, 0) / max(sum(emotions.values()), 1)

    if span_days > 180 and coherence > 0.5:
        return "thread", min(0.9, 0.5 + coherence * 0.4)
    elif coherence > 0.75 and size <= 10:
        return "entity", min(0.85, coherence)
    elif coherence > 0.65:
        return "location", min(0.8, coherence * 0.9)
    elif emotion_dominance > 0.6 and dominant_emotion:
        return "emotion", round(emotion_dominance, 2)
    else:
        return "thread", round(coherence * 0.6, 2)


def _compute_recurrence_score(
    size: int,
    span_days: int,
    coherence: float,
) -> float:
    """
    Izračuna recurrence score (0.0-1.0).

    Višji score = bolj ponavljajoč vzorec.
    Formula upošteva: število sanj, časovni razpon, semantično koherentnost.
    """
    # Velikost: log scale, max pri ~50 sanjah
    size_score = min(1.0, np.log1p(size) / np.log1p(50))

    # Razpon: max pri ~365 dneh
    span_score = min(1.0, span_days / 365) if span_days else 0.0

    # Koherentnost direktno
    coherence_score = coherence

    # Utežena kombinacija
    return round(
        size_score * 0.35 +
        span_score * 0.40 +
        coherence_score * 0.25,
        3
    )


# ── Factory ───────────────────────────────────────────────────────────────────

def create_clustering_engine(config, store: EmbeddingStore) -> ClusteringEngine:
    clusters_db = config.get(
        "storage", "clusters_db",
        default=os.path.join(config.storage_path, "clusters.db")
    )
    clustering_cfg = config._data.get("clustering", {})

    return ClusteringEngine(
        store=store,
        clusters_db_path=clusters_db,
        min_cluster_size=clustering_cfg.get("min_cluster_size", 10),
        min_samples=clustering_cfg.get("min_samples", 3),
        metric=clustering_cfg.get("metric", "cosine"),
        epsilon=clustering_cfg.get("epsilon", 0.0),
        umap_components=clustering_cfg.get("umap_components", 50),
        umap_neighbors=clustering_cfg.get("umap_neighbors", 15),
    )
