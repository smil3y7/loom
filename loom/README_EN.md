# Loom — Backend
### CCP v0.1 — Semantic Continuity Layer · en

For the Slovenian version see [README.md](./README.md).

---

## What Loom is

Loom is the semantic continuity layer for the Sentria ecosystem. It runs as a background service that:

- reads dreams from existing apps (Dream Browser, Atlas, Lucid Lab, Oneiro) — read-only, never modifies source databases
- generates semantic embeddings for each dream (local model, offline after the first download)
- enables search across the archive in Slovenian and English (same results for the same meaning)
- detects recurring patterns via UMAP + HDBSCAN clustering

Philosophy: the engine never interprets what dreams mean — it suggests patterns as candidates, the user confirms or rejects them. See the root [`/README.md`](../README.md) for more.

---

## System requirements

- Docker Desktop
- 4 GB RAM (8 GB recommended)
- ~500 MB disk space (embedding model, dependencies)
- Internet needed only for the first embedding model download (~120MB) — offline after that

---

## Installation

### 1. Folder structure

```
Loom\
    ├── docker-compose.yml
    ├── start.bat
    ├── loom\                ← this code
    ├── sources\
    │   ├── dreamdb\         ← Dream Browser + Atlas SQLite database
    │   ├── lab\             ← Lucid Lab SQLite database
    │   └── oneiro\          ← Oneiro JSON exports
    └── storage\             ← Loom's own data (created automatically)
```

### 2. Copy databases

**Dream Browser + Atlas:** copy `dream_atlas_*.sqlite` into `sources\dreamdb\`

**Lucid Lab:** Docker Desktop → container `lucid_lab` → **Files** → `/app/data/` → save the `.db` file to `sources\lab\`

**Oneiro:** via the Loom Sync browser extension (see [`../loom-extension/README.md`](../loom-extension/README.md)) — or via `/api/ingest` in "api" delivery mode.

### 3. Embedding provider (default: local, no API key)

The default `config.docker.yaml` setting is `provider: local` — the model runs on your machine, no API key required. This is the recommended setting.

Optionally, if you prefer the Hugging Face API instead of the local model (slower, needs internet on every embed call, but lower local RAM usage): set `provider: huggingface_api` in the config and add to `docker-compose.yml`:

```yaml
environment:
  - HF_API_KEY=hf_your_actual_token
```

Token: https://huggingface.co → Settings → Access Tokens → New token (Read)

### 4. Start

Double-click `start.bat`. The first build takes longer (installs torch, hdbscan, downloads the embedding model) — subsequent starts are fast.

---

## Management

```bash
docker exec -it loom_engine python loom.py          # interactive menu
docker exec -it loom_engine python loom.py status    # quick status
```

API docs (Swagger): `http://localhost:8000/api/docs`

### Interactive menu

```
1. Status          check adapters and databases
2. Backfill        import dream archive into Loom
3. Embeddings      generate semantic vectors
4. Search          semantic search across the archive
5. Patterns        detect recurring patterns (clustering)
6. Test adapter     verify a specific source
7. Export          export dreams to JSON
8. Language        change interface language
q. Quit
```

### Recommended order on first use

```
1. Status      → verify Loom can see all databases
2. Backfill    → import archive (4000+ dreams: ~5-10 minutes)
3. Embeddings  → generate vectors (4000+ dreams locally: ~15-20 minutes)
4. Patterns    → detect recurring patterns (4000+ dreams: ~2-5 minutes)
5. Search      → try semantic search
```

---

## Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

CI (`.github/workflows/backend-tests.yml`) runs this automatically on every push touching `loom/**`.

---

## Versioning

A single file — [`/VERSION`](../VERSION) at the repo root — is the single source of truth. The backend reads it dynamically at every startup (`lib/version.py`), no manual step needed here. (UI and extension have their own mechanism — see the root README.)

---

## Syncing between computers

The `storage\` folder contains all Loom data (state, embeddings, clusters, ingested). Copy the entire folder to another computer — no need to rerun backfill or embedding generation.

---

## Adding a new app source

1. Create `adapters/your_name.py` extending `BaseAdapter` (and `SQLiteAdapterMixin` if the source is a SQLite database)
2. Implement `fetch_all()`, `fetch_since()`, `fetch_one()`, `count_total()`
3. Register in `adapters/registry.py`
4. Add an entry to `config.docker.yaml`

Existing apps remain untouched — adapters are strictly read-only.

---

## Troubleshooting

**Status shows an error for a source** — check the file is in the right `sources\` subfolder, and that the filename matches the glob pattern (e.g. `dream_atlas_*.sqlite`)

**Embeddings aren't generating** — if using the `huggingface_api` provider, check `HF_API_KEY` and your internet connection; not relevant for the `local` provider

**Container won't start** — Docker Desktop must be running, check port 8000 isn't in use

---

## Current state

See the root [`/README.md`](../README.md) §"Trenutno stanje" for an accurate, up-to-date overview of what works and known limitations — not duplicated here to avoid drift between the two.
