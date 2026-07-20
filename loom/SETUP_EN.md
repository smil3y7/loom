# Loom — Setup and Configuration
### Technical Documentation · en

---

## What is Loom

Loom is the semantic continuity layer for the Sentria ecosystem. It runs as a background service that:

- reads dreams from existing apps (Dream Browser, Lucid Lab, Oneiro)
- generates semantic embeddings for each dream
- enables search across your archive in Slovenian and English
- detects recurring patterns, locations, and themes

Loom does not replace your existing apps — it only reads their data and adds a semantic layer on top.

---

## System requirements

- Windows 10/11
- Docker Desktop (https://www.docker.com/products/docker-desktop)
- 4 GB RAM (8 GB recommended)
- ~500 MB disk space
- Internet connection for embedding generation

---

## Installation

### 1. Prepare the folder structure

Create the main folder and subfolders:

```
C:\Users\name\Documents\_Dreaming\Loom\
    ├── loom\                ← engine code (from zip)
    ├── sources\
    │   ├── dreamdb\         ← Dream Browser + Atlas SQLite database
    │   ├── lab\             ← Lucid Lab SQLite database
    │   └── oneiro\          ← Oneiro JSON exports
    ├── storage\             ← Loom internal data (created automatically)
    ├── docker-compose.yml   ← from zip
    ├── Dockerfile           ← from zip
    ├── config.docker.yaml   ← from zip
    └── start.bat            ← from zip
```

### 2. Extract Loom

Extract `loom-phase0-clean.zip` into the main folder. The zip contents go directly inside.

### 3. Copy databases

**Dream Browser + Atlas:**
Copy `dream_atlas_*.sqlite` from your `DreamDB\` folder into `sources\dreamdb\`

**Lucid Lab:**
Docker Desktop → container `lucid_lab` → **Files** tab → `/app/data/` → right-click the `.db` file → **Save** → save to `sources\lab\`

**Oneiro:**
Use the Loom Sync browser extension (instructions below).

### 4. Set your Hugging Face API token

Open `docker-compose.yml` and replace `hf_xxxx` with your actual token:

```yaml
environment:
  - HF_API_KEY=hf_your_actual_token
```

Get your token at: https://huggingface.co → Settings → Access Tokens → New token (Read)

### 5. Start

Double-click `start.bat`. Docker Desktop will build and start the Loom container.

---

## Managing Loom

Open Docker Desktop → container `loom_engine` → **Terminal** tab:

```bash
python loom.py          # interactive menu
python loom.py status   # check adapter status
```

### Interactive menu

```
1. Status          check adapters and databases
2. Backfill        import dream archive into Loom
3. Embeddings      generate semantic vectors
4. Search          semantic search across archive
5. Test adapter    verify a specific source
6. Export          export dreams to JSON
7. Language        change interface language
q. Quit
```

### Recommended order on first use

```
1. Status          → verify Loom can see all databases
2. Backfill        → import archive (4000+ dreams: ~5-10 minutes)
3. Embeddings      → generate vectors (4000+ dreams: ~20 minutes)
4. Search          → try semantic search
```

---

## Loom Sync Extension

The Chrome extension exports dreams from Oneiro PWA into Loom.

### Installation

1. Extract `loom-extension.zip`
2. Right-click the folder → Properties → **Unblock** (Windows security setting)
3. Chrome → `chrome://extensions` → Developer mode (enable) → **Load unpacked**
4. Select the `loom-extension\` folder where `manifest.json` is directly visible

### Usage

1. Open Oneiro in your browser
2. Click the Loom Sync icon in the toolbar
3. Click **Sync with Loom**
4. The file downloads to your Downloads folder
5. Move it to `Loom\sources\oneiro\`

---

## Syncing between computers

The `storage\` folder contains all Loom data:

```
storage\
  ├── state.db       ← backfill progress
  └── embeddings.db  ← semantic vectors
```

To move to another computer: copy the entire `storage\` folder. No need to re-run backfill or embedding generation on the new machine.

---

## Adding a new app source

1. Create `adapters/your_app.py` extending `BaseAdapter`
2. Implement `fetch_all()`, `fetch_since()`, `fetch_one()`, `count_total()`
3. Add one line to `adapters/registry.py`
4. Add an entry to `config.docker.yaml`

No changes to existing apps required.

---

## Troubleshooting

**Status shows error for a source:**
- Check that the database file is in the correct `sources\` subfolder
- Check the filename — glob pattern `dream_atlas_*.sqlite` must match

**Embeddings not generating:**
- Check `HF_API_KEY` in `docker-compose.yml`
- Token must start with `hf_`
- Check your internet connection

**Container won't start:**
- Docker Desktop must be running
- Check that port 8000 is not in use

---

## Development phases

| Phase | Description | Status |
|---|---|---|
| 0 | Adapters, backfill, CLI | ✓ Done |
| 1 | Embedding pipeline | ✓ Done |
| 2 | Semantic search | ✓ Done |
| 3 | Supabase storage | Planned |
| 4 | Clustering, thread detection | Planned |
| 5 | FastAPI + Vercel deploy | Planned |
| 6 | Sentria Hub integration | Planned |
| 7 | AI synthesis | Planned |
