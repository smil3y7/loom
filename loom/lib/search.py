# Loom — Semantic Search
# lib/search.py
#
# Semantično iskanje po arhivu sanj.
# Deluje nad lokalnimi embedingi (EmbeddingStore).
#
# Faza 2: lokalni cosine similarity index
# Faza 3: Supabase pgvector (zamenja lokalni index, ista vmesnika)
#
# Iskanje je multilingvalno:
#   "staro mesto" in "old town" vrneta iste sanje
#   ker embedingi ne ločijo jezika — samo semantiko

import os
import math
from dataclasses import dataclass, field

from lib.schema import CanonicalDream
from lib.embeddings import EmbeddingStore, HuggingFaceProvider


# ── Rezultat iskanja ──────────────────────────────────────────────────────────

@dataclass
class SearchResult:
    dream_id: str
    source_app: str
    timestamp: str
    title: str | None
    excerpt: str
    similarity: float       # 0.0 - 1.0
    language: str
    metadata: dict = field(default_factory=dict)

    def format(self) -> str:
        title = self.title or "(brez naslova)"
        date = self.timestamp[:10]
        sim = f"{self.similarity:.0%}"
        src = self.source_app.replace("browser_atlas", "browser")
        return (
            f"  [{sim}] {date} · {src} · {self.language}\n"
            f"  {title}\n"
            f"  {self.excerpt}"
        )


# ── Lokalni vector index ──────────────────────────────────────────────────────

class LocalSearchIndex:
    """
    Hiter lokalni vector index brez zunanjih odvisnosti (numpy je edina
    odvisnost, že prisoten prek lib/clustering.py — ni novega paketa).

    Vektorizirana implementacija: ob build() se vsi embedingi enkrat
    naložijo v eno L2-normalizirano numpy matriko. search() nato računa
    podobnost z enim matričnim množenjem namesto s Python zanko čez vse
    vektorje — pri 4000+ sanjah to je bistveno hitreje kot prejšnja čista
    Python O(n) implementacija (seznam torok + zip/sum na klic).

    Za 8000 sanj z 384d vektorji:
      Memory: ~12MB
      Search: en (n, 384) @ (384,) matrični produkt namesto 8000 ločenih
              Python for-zanko klicev _cosine_similarity()

    Faza 3 ga zamenja s Supabase pgvector.
    """

    def __init__(self):
        self._dream_ids: list[str] = []
        self._matrix = None  # np.ndarray (n, dim), L2-normalizirane vrstice
        self._built = False

    def build(self, store: EmbeddingStore) -> int:
        """Naloži vse embedinge iz store v index in zgradi normalizirano matriko."""
        import numpy as np

        dream_ids = []
        vectors = []
        for result in store.get_all():
            dream_ids.append(result.dream_id)
            vectors.append(result.embedding)

        self._dream_ids = dream_ids
        if vectors:
            matrix = np.array(vectors, dtype=np.float64)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)  # izogni se deljenju z 0
            self._matrix = matrix / norms
        else:
            self._matrix = np.zeros((0, 0))
        self._built = True
        return len(self._dream_ids)

    def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        exclude_ids: list[str] = None,
    ) -> list[tuple[str, float]]:
        """Vrni top-k (dream_id, similarity) parov."""
        import numpy as np

        if not self._built or self._matrix is None or len(self._dream_ids) == 0:
            return []

        q = np.array(query_vector, dtype=np.float64)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        q = q / q_norm

        # En matrični produkt namesto zanke — vrne cosine similarity
        # za vse sanje hkrati, ker sta obe strani že L2-normalizirani.
        similarities = self._matrix @ q

        exclude = set(exclude_ids or [])
        # argsort padajoče, izloči exclude_ids, obreži na limit
        order = np.argsort(-similarities)
        results = []
        for idx in order:
            dream_id = self._dream_ids[idx]
            if dream_id in exclude:
                continue
            results.append((dream_id, float(similarities[idx])))
            if len(results) >= limit:
                break
        return results

    def find_similar(
        self,
        dream_id: str,
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        """Najdi podobne sanje brez klicanja API."""
        if dream_id not in self._dream_ids:
            return []
        idx = self._dream_ids.index(dream_id)
        vector = self._matrix[idx].tolist()
        return self.search(vector, limit=limit + 1,
                           exclude_ids=[dream_id])[:limit]

    @property
    def size(self) -> int:
        return len(self._dream_ids)

    @property
    def is_built(self) -> bool:
        return self._built


# ── Search engine ─────────────────────────────────────────────────────────────

class SearchEngine:
    """
    Glavni search engine.

    Tok:
      1. Sprejme query string (sl ali en — oba delujeta)
      2. Generira embedding za query
      3. Similarity search prek LocalSearchIndex
      4. Enricha z dream metadata
      5. Vrne rankirane SearchResult objekte
    """

    def __init__(
        self,
        store: EmbeddingStore,
        dreams_by_id: dict[str, CanonicalDream],
        embedding_provider=None,
    ):
        self.store = store
        self.dreams_by_id = dreams_by_id
        self.provider = embedding_provider or HuggingFaceProvider()
        self.index = LocalSearchIndex()
        self._indexed = False

    def build_index(self) -> int:
        """Zgradi search index iz obstoječih embedingov."""
        count = self.index.build(self.store)
        self._indexed = True
        print(f"[Search] Index zgrajen: {count} sanj")
        return count

    def search(
        self,
        query: str,
        limit: int = 10,
        language: str = None,
        source_app: str = None,
        min_similarity: float = 0.2,
    ) -> list[SearchResult]:
        """
        Semantično iskanje po arhivu.

        Args:
            query:          iskalni niz (sl, en, mešano)
            limit:          max rezultatov
            language:       filtriraj po jeziku ("sl" | "en" | None)
            source_app:     filtriraj po viru ali None za vse
            min_similarity: minimalna podobnost (default 0.3)
        """
        if not self._indexed:
            self.build_index()

        if self.index.size == 0:
            return []

        # Embed query
        try:
            vectors = self.provider.embed([query])
            query_vector = vectors[0]
        except Exception as e:
            print(f"[Search] Query embedding napaka: {e}")
            return []

        # Vector search — vzemi več za filtriranje
        raw = self.index.search(query_vector, limit=limit * 3)

        results = []
        for dream_id, similarity in raw:
            if similarity < min_similarity:
                break  # sortirano — konec

            dream = self.dreams_by_id.get(dream_id)
            if not dream:
                continue

            if language and dream.language != language:
                continue
            if source_app and dream.source_app != source_app:
                continue

            results.append(SearchResult(
                dream_id=dream_id,
                source_app=dream.source_app,
                timestamp=dream.timestamp,
                title=dream.title,
                excerpt=_make_excerpt(dream.content),
                similarity=round(similarity, 4),
                language=dream.language,
                metadata={
                    "lucid": dream.metadata.lucid,
                    "tags": dream.metadata.tags,
                    "parent_dream_id": dream.parent_dream_id,
                    "cycle_index": dream.cycle_index,
                },
            ))

            if len(results) >= limit:
                break

        return results

    def find_similar(
        self,
        dream_id: str,
        limit: int = 10,
        min_similarity: float = 0.2,
    ) -> list[SearchResult]:
        """
        Najdi sanje podobne dani snji.
        Ne kliče embedding API — uporablja shranjeni vektor.
        """
        if not self._indexed:
            self.build_index()

        raw = self.index.find_similar(dream_id, limit=limit * 2)

        results = []
        for similar_id, similarity in raw:
            if similarity < min_similarity:
                break

            dream = self.dreams_by_id.get(similar_id)
            if not dream:
                continue

            results.append(SearchResult(
                dream_id=similar_id,
                source_app=dream.source_app,
                timestamp=dream.timestamp,
                title=dream.title,
                excerpt=_make_excerpt(dream.content),
                similarity=round(similarity, 4),
                language=dream.language,
                metadata={
                    "lucid": dream.metadata.lucid,
                    "tags": dream.metadata.tags,
                },
            ))

            if len(results) >= limit:
                break

        return results

    def status(self) -> dict:
        return {
            "indexed": self.index.size,
            "total_embedded": self.store.count(),
            "total_dreams": len(self.dreams_by_id),
        }


# ── CLI interaktivno iskanje ──────────────────────────────────────────────────

def run_search_cli(engine: SearchEngine):
    """
    Interaktivno iskanje iz terminala.
    Kliče se iz loom.py search ukaza.
    """
    print("\n  Semantično iskanje (sl + en)")
    print("  Vtipkaj besedo ali stavek, prazna vrstica = izhod\n")

    while True:
        try:
            query = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query:
            break

        results = engine.search(query, limit=8)

        if not results:
            print("  Ni rezultatov.\n")
            continue

        print(f"\n  Rezultati za: '{query}'\n")
        for i, r in enumerate(results, 1):
            print(f"  {i}.")
            print(r.format())
            print()


# ── Pomožne funkcije ──────────────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _make_excerpt(content: str, max_len: int = 200) -> str:
    text = " ".join(content.split())
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > max_len * 0.8:
        truncated = truncated[:last_space]
    return truncated + "..."


# ── Factory ───────────────────────────────────────────────────────────────────

def create_search_engine(
    config,
    dreams_by_id: dict[str, CanonicalDream],
) -> SearchEngine:
    storage_path = config.storage_path
    db_path = os.path.join(storage_path, "embeddings.db")
    store = EmbeddingStore(db_path)
    model = config.get("embedding", "model",
                       default="paraphrase-multilingual-MiniLM-L12-v2")
    provider_name = config.get("embedding", "provider", default="huggingface_api")

    # Uporabi isti provider kot embedding pipeline
    if provider_name == "local":
        from lib.embeddings import LocalProvider
        provider = LocalProvider(model)
    else:
        provider = HuggingFaceProvider(model)

    return SearchEngine(
        store=store,
        dreams_by_id=dreams_by_id,
        embedding_provider=provider,
    )
