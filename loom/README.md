# Loom — Backend
### CCP v0.1 — Semantic Continuity Layer · sl

Za angleško verzijo glej [README_EN.md](./README_EN.md).

---

## Kaj je Loom

Loom je semantična kontinuitetna plast za Sentria ekosistem. Deluje kot ozadnji servis ki:

- bere sanje iz obstoječih appov (Dream Browser, Atlas, Lucid Lab, Oneiro) — read-only, izvornih baz nikoli ne spreminja
- generira semantične embedinge za vsako sanje (lokalni model, brez interneta po prvem prenosu)
- omogoča iskanje po arhivu v slovenščini in angleščini (isti rezultati za isti pomen)
- zazna ponavljajoče vzorce prek UMAP + HDBSCAN clusteringa

Filozofija: engine nikoli ne interpretira kaj sanje pomenijo — vzorce predlaga kot kandidate, uporabnik jih potrdi ali zavrne. Podrobneje v korenskem [`/README.md`](../README.md).

---

## Sistemske zahteve

- Docker Desktop
- 4 GB RAM (priporočeno 8 GB)
- ~500 MB prostora na disku (embedding model, odvisnosti)
- Internet potreben samo za prvi prenos embedding modela (~120MB) — po tem engine teče brez povezave

---

## Namestitev

### 1. Mapna struktura

```
Loom\
    ├── docker-compose.yml
    ├── start.bat
    ├── loom\                ← ta koda
    ├── sources\
    │   ├── dreamdb\         ← Dream Browser + Atlas SQLite baza
    │   ├── lab\             ← Lucid Lab SQLite baza
    │   └── oneiro\          ← Oneiro JSON exporti
    └── storage\             ← Loom lastni podatki (nastane samodejno)
```

### 2. Kopiraj baze

**Dream Browser + Atlas:** kopiraj `dream_atlas_*.sqlite` v `sources\dreamdb\`

**Lucid Lab:** Docker Desktop → container `lucid_lab` → **Files** → `/app/data/` → shrani `.db` v `sources\lab\`

**Oneiro:** prek Loom Sync browser extension (glej [`../loom-extension/README.md`](../loom-extension/README.md)) — ali prek `/api/ingest` v "api" delivery mode.

### 3. Embedding provider (privzeto: lokalno, brez API ključa)

Privzeta nastavitev v `config.docker.yaml` je `provider: local` — model teče na tvojem računalniku, ni potreben noben API ključ. To je priporočena nastavitev.

Opcijsko, če želiš namesto lokalnega modela uporabiti Hugging Face API (počasnejše, potrebuje internet ob vsakem embedanju, ampak manjša lokalna poraba RAM-a): nastavi `provider: huggingface_api` v configu in v `docker-compose.yml` dodaj:

```yaml
environment:
  - HF_API_KEY=hf_tvoj_dejanski_token
```

Token: https://huggingface.co → Settings → Access Tokens → New token (Read)

### 4. Zaženi

Dvoklik na `start.bat`. Prvi build traja dlje (namesti torch, hdbscan, prenese embedding model) — kasnejši zagon je hiter.

---

## Upravljanje

```bash
docker exec -it loom_engine python loom.py          # interaktivni meni
docker exec -it loom_engine python loom.py status    # hitri status
```

API dokumentacija (Swagger): `http://localhost:8000/api/docs`

### Interaktivni meni

```
1. Status          preveri adapterje in baze
2. Backfill        uvozi arhiv sanj v Loom
3. Embedingi       generiraj semantične vektorje
4. Iskanje         semantično iskanje po arhivu
5. Vzorci          zaznaj ponavljajoče vzorce (clustering)
6. Test adapterja  preveri posamezen vir
7. Izvoz           izvozi sanje v JSON
8. Jezik           spremeni jezik vmesnika
q. Izhod
```

### Priporočen vrstni red ob prvi uporabi

```
1. Status     → preveri da Loom vidi vse baze
2. Backfill   → uvozi arhiv (za 4000+ sanj ~5-10 minut)
3. Embedingi  → generiraj vektorje (za 4000+ sanj lokalno ~15-20 minut)
4. Vzorci     → zaznaj ponavljajoče vzorce (za 4000+ sanj ~2-5 minut)
5. Iskanje    → preizkusi semantično iskanje
```

---

## Testi

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

CI (`.github/workflows/backend-tests.yml`) to poganja samodejno ob vsakem pushu ki spremeni `loom/**`.

---

## Verzioniranje

Ena datoteka — [`/VERSION`](../VERSION) v korenu repozitorija — je edini vir resnice. Backend jo bere dinamično ob vsakem zagonu (`lib/version.py`), ni potreben noben ročni korak tukaj. (UI in extension imata svoj mehanizem — glej korenski README.)

---

## Sync med računalniki

Mapa `storage\` vsebuje vse Loom podatke (state, embeddings, clusters, ingested). Kopiraj celo mapo na drug računalnik — brez potrebe po ponovnem backfillu ali embedanju.

---

## Dodajanje novega app vira

1. Ustvari `adapters/novo_ime.py` ki razširja `BaseAdapter` (in `SQLiteAdapterMixin` če je vir SQLite baza)
2. Implementiraj `fetch_all()`, `fetch_since()`, `fetch_one()`, `count_total()`
3. Dodaj v `adapters/registry.py`
4. Dodaj vnos v `config.docker.yaml`

Obstoječi appi ostanejo nedotaknjeni — adapterji so izključno read-only.

---

## Odpravljanje težav

**Status prikazuje napako za vir** — preveri da je datoteka v pravi podmapi `sources\`, in da ime ustreza glob patternu (npr. `dream_atlas_*.sqlite`)

**Embedingi se ne generirajo** — če uporabljaš `huggingface_api` provider, preveri `HF_API_KEY` in internetno povezavo; pri `local` provider to ni relevantno

**Container se ne zažene** — Docker Desktop mora teči, preveri da port 8000 ni zaseden

---

## Trenutno stanje

Glej korenski [`/README.md`](../README.md) §"Trenutno stanje" za natančen, ažuren pregled kaj deluje in kaj so znane omejitve — ne podvajam tega tukaj, da se ne razideta.
