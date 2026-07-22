# Loom — FastAPI
# api/index.py
#
# REST API za Loom engine.
# Teče lokalno na localhost:8000 (Docker ali Tauri sidecar).
#
# Endpoints:
#   GET  /health
#   GET  /api/status
#   POST /api/ingest
#   POST /api/embed
#   GET  /api/search
#   GET  /api/clusters
#   GET  /api/threads
#   POST /api/threads/{id}/confirm
#   POST /api/threads/{id}/reject
#   GET  /api/dreams/{id}/similar
#   GET  /api/dreams/{id}/clusters

import os
import sys
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lib.schema import CanonicalDream, DreamMetadata
from lib.config import load_config

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Loom",
    description="Semantic Continuity Layer",
    version="0.1.0",
    docs_url="/api/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tauri in lokalni development
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Config in cache — naloži enkrat ob zagonu
_config = None
_dreams_cache = None
_search_engine = None
_clustering_engine = None

def get_config():
    global _config
    if _config is None:
        _config = load_config("config.yaml")
    return _config

def get_ingested_store():
    """IngestedDreamStore — sanje prejete prek /api/ingest (glej lib/ingested_store.py)."""
    from lib.ingested_store import IngestedDreamStore
    config = get_config()
    return IngestedDreamStore(os.path.join(config.storage_path, "ingested.db"))

def get_dreams():
    """
    Naloži sanje enkrat in cacheaj v memoryju.

    Union dveh virov: adapterji (SQLite/JSON datoteke na disku — Browser,
    Atlas, Lab, Oneiro export) IN IngestedDreamStore (sanje prejete prek
    POST /api/ingest, npr. iz Loom Sync extension v "api" delivery mode).
    Brez tega bi bile sanje poslane prek /api/ingest nikoli vidne v
    search/clusters/threads, ker adapterji ne vedo zanje.
    """
    global _dreams_cache
    if _dreams_cache is not None:
        return _dreams_cache
    from adapters.registry import create_adapter
    from lib.ingested_store import merge_dream_sources
    config = get_config()

    adapter_dreams = {}
    for source_name in config.enabled_sources():
        source_config = config.get_source_config(source_name)
        if not source_config:
            continue
        try:
            adapter = create_adapter(source_config)
            for dream in adapter.fetch_all():
                if dream.is_valid():
                    adapter_dreams[dream.dream_id] = dream
        except Exception:
            pass  # Izpusti nedosegljive vire, ne crashaj

    ingested_dreams = {}
    try:
        for dream in get_ingested_store().get_all():
            if dream.is_valid():
                ingested_dreams[dream.dream_id] = dream
    except Exception:
        pass  # Ingested store še ne obstaja ali je prazen — ni fatalno

    _dreams_cache = merge_dream_sources(adapter_dreams, ingested_dreams)
    return _dreams_cache

def invalidate_caches():
    """
    Počisti dreams/search/clustering cache — pokliči po tem ko pridejo nove
    sanje (npr. po /api/ingest), sicer ostanejo nevidne do restarta strežnika.
    """
    global _dreams_cache, _search_engine, _clustering_engine
    _dreams_cache = None
    _search_engine = None
    _clustering_engine = None

def get_search_engine():
    """Zgradi search index enkrat in cacheaj."""
    global _search_engine
    if _search_engine is not None:
        return _search_engine
    from lib.embeddings import EmbeddingStore
    from lib.search import create_search_engine
    config = get_config()
    store = EmbeddingStore(os.path.join(config.storage_path, "embeddings.db"))
    dreams = get_dreams()
    engine = create_search_engine(config, dreams)
    engine.build_index()
    _search_engine = engine
    return engine

def get_clustering_engine():
    """
    ClusteringEngine enkrat zgrajen in cacheaj — prej je vseh 8 clustering
    endpointov vsakič znova ustvarilo EmbeddingStore + ClusteringEngine,
    neskladno s cache patternom uporabljenim za get_dreams()/get_search_engine().
    ClusteringEngine sam po sebi ne cacheira SQL rezultatov (vsak get_clusters()/
    get_threads() klic bere sveže iz clusters.db), zato cachiranje same instance
    ne tvega zastarelih podatkov po confirm/reject/run() klicih.
    """
    global _clustering_engine
    if _clustering_engine is not None:
        return _clustering_engine
    from lib.embeddings import EmbeddingStore
    from lib.clustering import create_clustering_engine
    config = get_config()
    store = EmbeddingStore(os.path.join(config.storage_path, "embeddings.db"))
    _clustering_engine = create_clustering_engine(config, store)
    return _clustering_engine


# ── Pydantic modeli ───────────────────────────────────────────────────────────

class DreamMetadataIn(BaseModel):
    lucid: Optional[bool] = None
    tags: list[str] = []
    emotions: list[str] = []
    emotional_tone: Optional[str] = None
    is_nightmare: Optional[bool] = None
    vividness: Optional[str] = None
    extras: dict = {}

class CanonicalDreamIn(BaseModel):
    dream_id: str
    source_app: str
    timestamp: str
    content: str
    language: str
    title: Optional[str] = None
    parent_dream_id: Optional[str] = None
    cycle_index: Optional[int] = None
    metadata: DreamMetadataIn = DreamMetadataIn()
    source_updated_at: Optional[str] = None

class IngestRequest(BaseModel):
    dreams: list[CanonicalDreamIn]

class ConfirmThreadRequest(BaseModel):
    name: str

class ConfirmClusterRequest(BaseModel):
    confirmed_type: str   # "thread" | "location" | "entity"
    confirmed_name: str


# ── Helper funkcije ──────────────────────────────────────────────────────────────

# Stopwords za slovenščino in angleščino
_STOPWORDS = {
    "sl": {"in", "se", "na", "da", "je", "ki", "so", "za", "ne", "pri",
            "ko", "ga", "mu", "jih", "kar", "ali", "pa", "mi", "to", "sem",
            "bil", "bila", "bilo", "smo", "ste", "so", "bi", "bo", "ter",
            "kot", "po", "iz", "ob", "do", "od", "med", "nad", "pod",
            "ker", "če", "ko", "tam", "tu", "sem", "tja", "ven", "noter"},
    "en": {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "was", "are", "were",
            "be", "been", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "i", "you", "he",
            "she", "it", "we", "they", "me", "him", "her", "us", "them"},
}
_ALL_STOPS = _STOPWORDS["sl"] | _STOPWORDS["en"]


def _suggest_thread_name(dream_ids: list, dreams: dict, fallback: str) -> str:
    """
    Predlaga ime za thread na podlagi najpogostejših besed v naslovih sanj.
    Ignorira stopwords in kratke besede.
    """
    from collections import Counter
    import re

    word_counts = Counter()
    for did in dream_ids[:30]:  # prvih 30 za hitrost
        dream = dreams.get(did)
        if not dream:
            continue
        # Prioriteta naslovu
        text = dream.title or dream.content[:100]
        words = re.findall(r'[a-zA-ZčšžČŠŽ]{4,}', text.lower())
        for w in words:
            if w not in _ALL_STOPS:
                word_counts[w] += 1

    if not word_counts:
        return fallback

    # Top besedi — vzamemo najboljši 2 brez minimalnega praga
    # Prednost besedam ki se pojavijo večkrat
    top = [w for w, _ in word_counts.most_common(2)]

    if top:
        result = " / ".join(w.capitalize() for w in top[:2])
        return result if result != fallback else None
    return None


def _build_timeline(dream_ids: list, dreams: dict) -> list:
    """
    Zgradi časovno premico pojavitev po letih.
    Vrne: [{"year": 2015, "count": 7}, ...]
    """
    from collections import Counter
    year_counts = Counter()
    for did in dream_ids:
        dream = dreams.get(did)
        if dream and dream.timestamp:
            try:
                year = int(dream.timestamp[:4])
                year_counts[year] += 1
            except (ValueError, IndexError):
                pass

    if not year_counts:
        return []

    min_year = min(year_counts)
    max_year = max(year_counts)
    return [
        {"year": y, "count": year_counts.get(y, 0)}
        for y in range(min_year, max_year + 1)
    ]


# ── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Pre-warm dreams cache in background ob zagonu."""
    import asyncio
    async def warm():
        await asyncio.sleep(2)  # počakaj da se strežnik zažene
        try:
            get_dreams()
            get_search_engine()
            print("[Loom] Search index zgran ob zagonu.")
        except Exception as e:
            print(f"[Loom] Cache warmup napaka: {e}")
    asyncio.create_task(warm())

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "loom",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Status ────────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    """Celoten status — embedingi, clustering, storage."""
    config = get_config()

    # Embedding status
    embed_status = {"embedded": 0, "queued": 0, "provider": "unknown"}
    try:
        from lib.embeddings import EmbeddingStore, create_pipeline
        store = EmbeddingStore(os.path.join(config.storage_path, "embeddings.db"))
        embed_status = {
            "embedded": store.count(),
            "queued": store.queue_size(),
            "provider": config.get("embedding", "provider", default="local"),
            "model": config.get("embedding", "model", default="paraphrase-multilingual-MiniLM-L12-v2"),
        }
    except Exception as e:
        embed_status["error"] = str(e)

    # Clustering status
    cluster_status = {"clusters": 0, "threads": 0}
    try:
        ce = get_clustering_engine()
        cluster_status = ce.status()
    except Exception as e:
        cluster_status["error"] = str(e)

    # Sources status
    sources_status = {}
    try:
        from adapters.registry import create_adapter
        for source_name in config.enabled_sources():
            source_config = config.get_source_config(source_name)
            if source_config:
                adapter = create_adapter(source_config)
                sources_status[source_name] = adapter.health_check()
    except Exception as e:
        sources_status["error"] = str(e)

    # Ingested store — sanje prejete prek /api/ingest (npr. extension api mode)
    try:
        sources_status["ingested_api"] = {
            "ok": True,
            "count": get_ingested_store().count(),
        }
    except Exception as e:
        sources_status["ingested_api"] = {"ok": False, "error": str(e)}

    return {
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "embeddings": embed_status,
        "clustering": cluster_status,
        "sources": sources_status,
    }


# ── Ingest ────────────────────────────────────────────────────────────────────

@app.post("/api/ingest")
async def api_ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    """
    Sprejme canonical dream objekte iz source appov (Oneiro, extension).
    Shrani jih v IngestedDreamStore (trajno — prej se je vsebina zavrgla in
    samo dream_id šel v embedding queue, kar je pomenilo da embedding step
    ni nikoli našel dejanske vsebine za embedanje). Takoj vrne odgovor,
    embedding generacija gre v ozadje.
    """
    from lib.schema import CanonicalDream

    accepted = 0
    rejected = 0
    ingested_store = get_ingested_store()

    try:
        from lib.embeddings import EmbeddingStore
        config = get_config()
        embed_store = EmbeddingStore(os.path.join(config.storage_path, "embeddings.db"))

        for dream_in in request.dreams:
            if not dream_in.dream_id or not dream_in.content.strip():
                rejected += 1
                continue

            dream = CanonicalDream.from_dict(dream_in.model_dump())
            if not dream.is_valid():
                rejected += 1
                continue

            ingested_store.save(dream)
            embed_store.enqueue(dream.dream_id, dream.source_app)
            accepted += 1

        if accepted > 0:
            # Nove sanje morajo biti takoj vidne v get_dreams()/search —
            # brez tega bi ostale nevidne do restarta strežnika.
            invalidate_caches()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "accepted": accepted,
        "rejected": rejected,
        "queued_for_embedding": accepted,
        "message": f"Sprejeto {accepted}, zavrnjeno {rejected}",
    }


# ── Embed ─────────────────────────────────────────────────────────────────────

@app.post("/api/embed")
async def api_embed(background_tasks: BackgroundTasks):
    """
    Sproži embedding generacijo za vse čakajoče sanje.
    Teče v ozadju — takoj vrne odgovor.
    """
    config = get_config()

    try:
        from lib.embeddings import EmbeddingStore, create_pipeline
        from adapters.registry import create_adapter

        store = EmbeddingStore(os.path.join(config.storage_path, "embeddings.db"))
        queued = store.queue_size()

        if queued == 0:
            return {"queued": 0, "message": "Ni sanj v vrsti"}

        # Zaženi v ozadju
        def run_embedding():
            pipeline = create_pipeline(config)
            dreams_by_id = {}
            for source_name in config.enabled_sources():
                source_config = config.get_source_config(source_name)
                if source_config:
                    adapter = create_adapter(source_config)
                    for dream in adapter.fetch_all():
                        if dream.is_valid():
                            dreams_by_id[dream.dream_id] = dream
            pipeline.process_queue(dreams_by_id)

        background_tasks.add_task(run_embedding)

        return {
            "queued": queued,
            "message": f"Embedding generacija zagana za {queued} sanj",
            "status": "running",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Search ────────────────────────────────────────────────────────────────────

@app.get("/api/search")
async def api_search(
    q: str,
    limit: int = 50,
    language: Optional[str] = None,
    source_app: Optional[str] = None,
    min_similarity: float = 0.2,
):
    """Semantično iskanje po arhivu. Uporablja cachiran index."""
    try:
        from lib.embeddings import EmbeddingStore
        config = get_config()
        store = EmbeddingStore(os.path.join(config.storage_path, "embeddings.db"))
        if store.count() == 0:
            return {"query": q, "results": [], "total": 0,
                    "message": "Ni embedingov. Najprej poženi embedding generacijo."}

        engine = get_search_engine()
        results = engine.search(
            query=q,
            limit=limit,
            language=language,
            source_app=source_app,
            min_similarity=min_similarity,
        )
        # Enrichaj z full_content iz dreams cache
        enriched = []
        for r in results:
            d = r.__dict__.copy()
            dream = get_dreams().get(r.dream_id)
            if dream:
                d["full_content"] = dream.content
                d["timestamp"] = dream.timestamp
            enriched.append(d)
        return {
            "query": q,
            "results": enriched,
            "total": len(enriched),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Similar dreams ────────────────────────────────────────────────────────────

@app.get("/api/dreams/{dream_id}/similar")
async def api_similar(dream_id: str, limit: int = 8):
    """Najdi sanje podobne dani snji. Uporablja cachiran index."""
    try:
        engine = get_search_engine()
        results = engine.find_similar(dream_id, limit=limit)

        # Enrichaj z full_content iz dreams cache — enako kot pri /api/search
        dreams = get_dreams()
        enriched = []
        for r in results:
            d = r.__dict__.copy()
            dream = dreams.get(r.dream_id)
            if dream:
                d["full_content"] = dream.content
                d["timestamp"] = dream.timestamp
            enriched.append(d)

        return {
            "dream_id": dream_id,
            "results": enriched,
            "total": len(enriched),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Clusters ──────────────────────────────────────────────────────────────────

@app.get("/api/clusters")
async def api_clusters(
    min_size: int = 2,
    candidate_type: Optional[str] = None,
    confirmed_only: bool = False,
):
    """Vrni vse cluster grupe z vzorčnimi sanjami."""
    config = get_config()

    try:
        engine = get_clustering_engine()
        clusters = engine.get_clusters(
            confirmed_only=confirmed_only,
            min_size=min_size,
            candidate_type=candidate_type,
        )

        dreams = get_dreams()
        result = []
        for cluster in clusters:
            d = cluster.to_dict()
            samples = []
            for did in cluster.dream_ids[:10]:
                dream = dreams.get(did)
                if dream:
                    samples.append({
                        "dream_id": did,
                        "date": dream.timestamp[:10],
                        "title": dream.title,
                        "excerpt": dream.content[:150].replace(chr(10), " "),
                        "full_content": dream.content,
                    })
            d["sample_dreams"] = samples
            result.append(d)

        return {"clusters": result, "total": len(result)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dreams/{dream_id}/clusters")
async def api_dream_clusters(dream_id: str):
    """Vrni cluster_id-je za dano sanje."""
    config = get_config()
    try:
        engine = get_clustering_engine()
        cluster_ids = engine.get_clusters_for_dream(dream_id)
        return {"dream_id": dream_id, "cluster_ids": cluster_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clusters/{cluster_id}/confirm")
async def api_confirm_cluster(cluster_id: str, request: ConfirmClusterRequest):
    """Uporabnik potrdi cluster."""
    config = get_config()
    try:
        engine = get_clustering_engine()
        engine.confirm_cluster(cluster_id, request.confirmed_type, request.confirmed_name)
        return {"ok": True, "cluster_id": cluster_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clusters/{cluster_id}/reject")
async def api_reject_cluster(cluster_id: str):
    """Uporabnik zavrne cluster."""
    config = get_config()
    try:
        engine = get_clustering_engine()
        engine.reject_cluster(cluster_id)
        return {"ok": True, "cluster_id": cluster_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Threads ───────────────────────────────────────────────────────────────────

@app.get("/api/threads")
async def api_threads(confirmed_only: bool = False):
    """Vrni vse candidate threads z vzorčnimi sanjami."""
    config = get_config()
    try:
        engine = get_clustering_engine()
        threads = engine.get_threads(confirmed_only=confirmed_only)

        # Enrichaj z vzorčnimi sanjami
        dreams = get_dreams()
        result = []
        for thread in threads:
            d = thread.to_dict()

            # Vzorčne sanje
            samples = []
            for did in thread.dream_ids[:20]:
                dream = dreams.get(did)
                if dream:
                    samples.append({
                        "dream_id": did,
                        "date": dream.timestamp[:10],
                        "title": dream.title,
                        "excerpt": dream.content[:150].replace(chr(10), " "),
                        "full_content": dream.content,
                    })
            d["sample_dreams"] = samples

            # Predlagano ime iz naslovov sanj
            # None če ni dobrega predloga — UI potem prikaže thread.name
            suggested = _suggest_thread_name(
                thread.dream_ids, dreams, None
            )
            # Ne prikazuj sugestije če je enaka generičnemu imenu
            d["suggested_name"] = suggested if suggested and not suggested.lower().startswith("vzorec") else None

            # Časovna premica — pojavitve po letih
            d["timeline"] = _build_timeline(thread.dream_ids, dreams)

            result.append(d)

        return {"threads": result, "total": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/threads/{thread_id}/confirm")
async def api_confirm_thread(thread_id: str, request: ConfirmThreadRequest):
    """Uporabnik potrdi thread."""
    config = get_config()
    try:
        engine = get_clustering_engine()
        engine.confirm_thread(thread_id, request.name)
        return {"ok": True, "thread_id": thread_id, "name": request.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/threads/{thread_id}/reject")
async def api_reject_thread(thread_id: str):
    """Uporabnik zavrne thread."""
    config = get_config()
    try:
        engine = get_clustering_engine()
        engine.reject_thread(thread_id)
        return {"ok": True, "thread_id": thread_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Vercel ASGI handler ───────────────────────────────────────────────────────

try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    handler = None
