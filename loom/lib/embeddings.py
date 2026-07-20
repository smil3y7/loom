# Loom — Embedding Pipeline
# lib/embeddings.py
#
# Generira multilingualne semantične embedinge za canonical dream objekte.
#
# Podprta providera:
#   huggingface_api  — Hugging Face Inference API (brez lokalnega GPU)
#   local            — sentence-transformers lokalno (hitrejše za bulk)
#
# Embedingi so:
#   - generirani async, nikoli ne blokirajo uvoza
#   - shranjeni append-only (nikoli ne prepisuješ obstoječih)
#   - resumable (preskoči že generirane)
#   - multilingvalni (sl + en + ostali brez sprememb)

import os
import time
import json
import sqlite3
from typing import Optional, Iterator
from datetime import datetime, timezone
from dataclasses import dataclass

from lib.schema import CanonicalDream


# ── Konfiguracija ─────────────────────────────────────────────────────────────

# Priporočen model: dobro pokriva sl + en, hiter, brezplačen na HF
DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Dimenzija vektorja za ta model
MODEL_DIMENSIONS = {
    "paraphrase-multilingual-MiniLM-L12-v2": 384,
    "multilingual-e5-small": 384,
    "paraphrase-multilingual-mpnet-base-v2": 768,
}


# ── Embedding rezultat ────────────────────────────────────────────────────────

@dataclass
class EmbeddingResult:
    dream_id: str
    embedding: list[float]
    model: str
    provider: str
    generated_at: str
    dimension: int

    def to_dict(self) -> dict:
        return {
            "dream_id": self.dream_id,
            "embedding": self.embedding,
            "model": self.model,
            "provider": self.provider,
            "generated_at": self.generated_at,
            "dimension": self.dimension,
        }


# ── Provider: Hugging Face Inference API ──────────────────────────────────────

class HuggingFaceProvider:
    """
    Kliče Hugging Face Inference API za generiranje embedingov.
    Brezplačen tier: ~1000 klicev/dan, rate limit ~10/s.
    API ključ: HF_API_KEY environment variable.

    Brez API ključa deluje v "mock" načinu — vrne naključne vektorje.
    Primerno za testiranje pipeline brez HF accounta.
    """

    BASE_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction"

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.api_key = os.environ.get("HF_API_KEY", "")
        self.dimension = MODEL_DIMENSIONS.get(model, 384)

        if not self.api_key:
            print("[Embeddings] HF_API_KEY ni nastavljen — mock način (testiranje)")

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generiraj embedinge za seznam tekstov. Vrne seznam vektorjev."""
        if not self.api_key:
            return self._mock_embed(texts)
        return self._api_embed(texts)

    def _api_embed(self, texts: list[str]) -> list[list[float]]:
        import urllib.request
        import urllib.error

        url = f"{self.BASE_URL}/{self.model}"
        payload = json.dumps({
            "inputs": texts,
            "options": {"wait_for_model": True}
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            # HF vrne [[vec1], [vec2], ...] ali [vec1, vec2, ...]
            if isinstance(result[0][0], list):
                # Mean pooling če je 3D (tokens × dim)
                return [_mean_pool(v) for v in result]
            return result

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HF API napaka {e.code}: {body}")

        except Exception as e:
            raise RuntimeError(f"HF API nedosegljiv: {e}")

    def _mock_embed(self, texts: list[str]) -> list[list[float]]:
        """
        Mock embedingi za testiranje brez API ključa.
        Deterministični: isti tekst → isti vektor.
        NE za produkcijo — semantično ničvredni.
        """
        import hashlib
        results = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            # Razširi hash na dimension float vrednosti med -1 in 1
            vec = []
            for i in range(self.dimension):
                byte = h[i % len(h)]
                vec.append((byte / 127.5) - 1.0)
            results.append(vec)
        return results

    def health_check(self) -> dict:
        if not self.api_key:
            return {"ok": True, "mode": "mock", "message": "Mock način (brez HF_API_KEY)"}
        try:
            result = self.embed(["test"])
            if result and len(result[0]) == self.dimension:
                return {"ok": True, "mode": "api", "message": f"HF API dosegljiv · {self.dimension}d"}
            return {"ok": False, "mode": "api", "message": "Nepričakovan format odgovora"}
        except Exception as e:
            return {"ok": False, "mode": "api", "message": str(e)}


# ── Provider: Lokalni sentence-transformers ───────────────────────────────────

class LocalProvider:
    """
    Poganja model lokalno prek sentence-transformers.
    Hitrejše za bulk processing, zahteva ~500MB RAM za MiniLM.
    Instalacija: pip install sentence-transformers

    Primerno ko imaš dovolj RAM in hočeš procesirati brez API limitov.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model_name = model
        self.dimension = MODEL_DIMENSIONS.get(model, 384)
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"[Embeddings] Nalagam model {self.model_name}...")
                self._model = SentenceTransformer(self.model_name)
                print(f"[Embeddings] Model naložen.")
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers ni nameščen.\n"
                    "Namesti z: pip install sentence-transformers\n"
                    "Ali nastavi provider: huggingface_api"
                )

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._load()
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    def health_check(self) -> dict:
        try:
            self._load()
            result = self.embed(["test"])
            return {
                "ok": True,
                "mode": "local",
                "message": f"Lokalni model naložen · {self.dimension}d"
            }
        except Exception as e:
            return {"ok": False, "mode": "local", "message": str(e)}


# ── Embedding store (SQLite) ──────────────────────────────────────────────────

class EmbeddingStore:
    """
    Lokalno shranjevanje embedingov v SQLite.
    Append-only: nikoli ne briše ali prepisuje obstoječih embedingov.

    Shranjevanje je ločeno od vector indexa (FAISS/pgvector).
    Ta store je source of truth; vector index se rekonstruira iz njega.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = self._connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                dream_id      TEXT PRIMARY KEY,
                embedding_json TEXT NOT NULL,
                model         TEXT NOT NULL,
                provider      TEXT NOT NULL,
                dimension     INTEGER NOT NULL,
                generated_at  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embedding_queue (
                dream_id    TEXT PRIMARY KEY,
                source_app  TEXT NOT NULL,
                queued_at   TEXT NOT NULL,
                attempts    INTEGER DEFAULT 0,
                last_error  TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def has_embedding(self, dream_id: str) -> bool:
        conn = self._connect()
        row = conn.execute(
            "SELECT 1 FROM embeddings WHERE dream_id = ?", (dream_id,)
        ).fetchone()
        conn.close()
        return row is not None

    def save(self, result: EmbeddingResult):
        conn = self._connect()
        conn.execute("""
            INSERT OR IGNORE INTO embeddings
              (dream_id, embedding_json, model, provider, dimension, generated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            result.dream_id,
            json.dumps(result.embedding),
            result.model,
            result.provider,
            result.dimension,
            result.generated_at,
        ))
        # Remove from queue if present
        conn.execute(
            "DELETE FROM embedding_queue WHERE dream_id = ?", (result.dream_id,)
        )
        conn.commit()
        conn.close()

    def get(self, dream_id: str) -> Optional[EmbeddingResult]:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM embeddings WHERE dream_id = ?", (dream_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return EmbeddingResult(
            dream_id=row["dream_id"],
            embedding=json.loads(row["embedding_json"]),
            model=row["model"],
            provider=row["provider"],
            generated_at=row["generated_at"],
            dimension=row["dimension"],
        )

    def get_all(self) -> Iterator[EmbeddingResult]:
        conn = self._connect()
        rows = conn.execute("SELECT * FROM embeddings ORDER BY generated_at").fetchall()
        conn.close()
        for row in rows:
            yield EmbeddingResult(
                dream_id=row["dream_id"],
                embedding=json.loads(row["embedding_json"]),
                model=row["model"],
                provider=row["provider"],
                generated_at=row["generated_at"],
                dimension=row["dimension"],
            )

    def count(self) -> int:
        conn = self._connect()
        row = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
        conn.close()
        return row[0] if row else 0

    # ── Queue management ──────────────────────────────────────────────────────

    def enqueue(self, dream_id: str, source_app: str):
        """Doda dream_id v vrsto za embedding generacijo."""
        if self.has_embedding(dream_id):
            return  # že ima embedding
        conn = self._connect()
        conn.execute("""
            INSERT OR IGNORE INTO embedding_queue (dream_id, source_app, queued_at)
            VALUES (?, ?, ?)
        """, (dream_id, source_app, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    def dequeue_batch(self, size: int = 32) -> list[dict]:
        """Vrni naslednji batch iz vrste (max attempts: 3)."""
        conn = self._connect()
        rows = conn.execute("""
            SELECT dream_id, source_app, attempts
            FROM embedding_queue
            WHERE attempts < 3
            ORDER BY queued_at
            LIMIT ?
        """, (size,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def mark_failed(self, dream_id: str, error: str):
        conn = self._connect()
        conn.execute("""
            UPDATE embedding_queue
            SET attempts = attempts + 1, last_error = ?
            WHERE dream_id = ?
        """, (error[:500], dream_id))
        conn.commit()
        conn.close()

    def queue_size(self) -> int:
        conn = self._connect()
        row = conn.execute(
            "SELECT COUNT(*) FROM embedding_queue WHERE attempts < 3"
        ).fetchone()
        conn.close()
        return row[0] if row else 0

    def status(self) -> dict:
        return {
            "embedded": self.count(),
            "queued": self.queue_size(),
        }


# ── Embedding pipeline ────────────────────────────────────────────────────────

class EmbeddingPipeline:
    """
    Glavni pipeline za generiranje embedingov.

    Tok:
      1. Adapter poda canonical dream objekte
      2. Pipeline jih doda v vrsto (enqueue)
      3. process_queue() jih procesira v batchih
      4. Rezultati gredo v EmbeddingStore

    Podpira:
      - Batch processing (default 32 tekstov naenkrat)
      - Rate limiting (delay med batchi)
      - Retry logiko (max 3 poskusi na dream)
      - Resumable (preskoči že generirane)
      - Mock način (brez API ključa)
    """

    def __init__(
        self,
        store: EmbeddingStore,
        provider: str = "huggingface_api",
        model: str = DEFAULT_MODEL,
        batch_size: int = 32,
        delay_ms: int = 500,
    ):
        self.store = store
        self.model = model
        self.batch_size = batch_size
        self.delay_ms = delay_ms

        # Inicializiraj provider
        if provider == "local":
            self.provider = LocalProvider(model)
            self.provider_name = "local"
        else:
            self.provider = HuggingFaceProvider(model)
            self.provider_name = "huggingface_api"

    def enqueue_dreams(self, dreams: Iterator[CanonicalDream]) -> int:
        """
        Doda sanje v vrsto za embedding generacijo.
        Preskoči tiste ki že imajo embedding.
        Vrne število dodanih v vrsto.
        """
        count = 0
        for dream in dreams:
            if not self.store.has_embedding(dream.dream_id):
                self.store.enqueue(dream.dream_id, dream.source_app)
                count += 1
        return count

    def process_queue(
        self,
        dreams_by_id: dict[str, CanonicalDream],
        on_progress=None,
    ) -> dict:
        """
        Procesira vrsto embedingov.

        Args:
            dreams_by_id: {dream_id: CanonicalDream} — za dostop do vsebine
            on_progress: optional callback(processed, total, failed)

        Returns:
            {"processed": n, "failed": n, "skipped": n}
        """
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        total = self.store.queue_size()

        if total == 0:
            print("[Embeddings] Vrsta je prazna.")
            return stats

        print(f"[Embeddings] Procesiranje {total} embedingov...")

        # Sledimo unikatnim dream_id-jem ki so kadarkoli padli, in tistim ki so
        # kasneje vseeno uspeli — brez tega bi ena sanja, ki pade 3x preden se
        # opusti (glej dequeue_batch/mark_failed retry logiko), v stats["failed"]
        # prispevala 3, namesto 1 — ali pa bi štela kot "failed" tudi če je na
        # naslednjem poskusu vseeno uspela.
        ever_failed_ids = set()
        succeeded_ids = set()

        while True:
            batch_items = self.store.dequeue_batch(self.batch_size)
            if not batch_items:
                break

            # Zberi tekste za batch
            batch_dreams = []
            for item in batch_items:
                dream = dreams_by_id.get(item["dream_id"])
                if dream:
                    batch_dreams.append(dream)
                else:
                    stats["skipped"] += 1

            if not batch_dreams:
                continue

            texts = [_prepare_text(d) for d in batch_dreams]

            try:
                vectors = self.provider.embed(texts)

                for dream, vector in zip(batch_dreams, vectors):
                    result = EmbeddingResult(
                        dream_id=dream.dream_id,
                        embedding=vector,
                        model=self.model,
                        provider=self.provider_name,
                        generated_at=datetime.now(timezone.utc).isoformat(),
                        dimension=len(vector),
                    )
                    self.store.save(result)
                    stats["processed"] += 1
                    succeeded_ids.add(dream.dream_id)

            except Exception as e:
                print(f"[Embeddings] Batch napaka: {e}")
                for item in batch_items:
                    self.store.mark_failed(item["dream_id"], str(e))
                    ever_failed_ids.add(item["dream_id"])

            if on_progress:
                on_progress(stats["processed"], total, len(ever_failed_ids - succeeded_ids))

            print(
                f"\r[Embeddings] {stats['processed']}/{total} "
                f"· napak: {len(ever_failed_ids - succeeded_ids)}",
                end="", flush=True
            )

            if self.delay_ms > 0:
                time.sleep(self.delay_ms / 1000)

        # Končno število failed = sanje ki so padle in NISO kasneje uspele
        stats["failed"] = len(ever_failed_ids - succeeded_ids)

        print(f"\n[Embeddings] Končano: {stats}")
        return stats

    def embed_single(self, dream: CanonicalDream) -> Optional[EmbeddingResult]:
        """
        Generiraj embedding za eno sanje on-demand.
        Vrne obstoječi embedding če že obstaja.
        """
        existing = self.store.get(dream.dream_id)
        if existing:
            return existing

        try:
            text = _prepare_text(dream)
            vectors = self.provider.embed([text])
            result = EmbeddingResult(
                dream_id=dream.dream_id,
                embedding=vectors[0],
                model=self.model,
                provider=self.provider_name,
                generated_at=datetime.now(timezone.utc).isoformat(),
                dimension=len(vectors[0]),
            )
            self.store.save(result)
            return result
        except Exception as e:
            print(f"[Embeddings] Napaka za {dream.dream_id}: {e}")
            return None

    def health_check(self) -> dict:
        return self.provider.health_check()

    def status(self) -> dict:
        store_status = self.store.status()
        return {
            "model": self.model,
            "provider": self.provider_name,
            "embedded": store_status["embedded"],
            "queued": store_status["queued"],
        }


# ── Pomožne funkcije ──────────────────────────────────────────────────────────

def _prepare_text(dream: CanonicalDream) -> str:
    """
    Pripravi tekst za embedding.
    Naslov + vsebina, očiščena za embedding model.
    Dolžina je omejena — MiniLM ima max 512 tokenov (~380 besed).
    """
    parts = []
    if dream.title:
        parts.append(dream.title)
    # Vsebina: prvih ~1500 znakov (dovolj za semantiko, ne preveč za model)
    content = dream.content.strip()
    if len(content) > 1500:
        content = content[:1500] + "..."
    parts.append(content)
    return " | ".join(parts)


def _mean_pool(token_embeddings: list[list[float]]) -> list[float]:
    """Mean pooling za 3D HF output (tokens × dimension → dimension)."""
    if not token_embeddings:
        return []
    dim = len(token_embeddings[0])
    result = [0.0] * dim
    for vec in token_embeddings:
        for i, v in enumerate(vec):
            result[i] += v
    n = len(token_embeddings)
    return [v / n for v in result]


# ── Factory ───────────────────────────────────────────────────────────────────

def create_pipeline(config) -> EmbeddingPipeline:
    """
    Ustvari EmbeddingPipeline iz config objekta.
    Uporabi v CLI in API handlerjih.
    """
    model = config.get("embedding", "model", default=DEFAULT_MODEL)
    provider = config.get("embedding", "provider", default="huggingface_api")
    storage_path = config.storage_path
    db_path = os.path.join(storage_path, "embeddings.db")

    # batch_size/delay_ms morata priti iz configa — prej sta bila hardcodana
    # na 32/500ms ne glede na config.docker.yaml, kar je pri lokalnem
    # provider-ju (ki ne rabi rate-limitinga) po nepotrebnem upočasnilo
    # generacijo embedingov.
    batch_size = config.get("embedding", "batch_size", default=32)
    default_delay = 0 if provider == "local" else 500
    delay_ms = config.get("embedding", "delay_ms", default=default_delay)

    store = EmbeddingStore(db_path)
    pipeline = EmbeddingPipeline(
        store=store,
        provider=provider,
        model=model,
        batch_size=batch_size,
        delay_ms=delay_ms,
    )
    return pipeline
