# Loom

![Backend testi](https://github.com/smil3y7/loom/actions/workflows/backend-tests.yml/badge.svg)
![UI testi](https://github.com/smil3y7/loom/actions/workflows/ui-tests.yml/badge.svg)
![Extension](https://github.com/smil3y7/loom/actions/workflows/extension-check.yml/badge.svg)

Semantična kontinuitetna plast za sanjski dnevnik. Del ekosistema **Sentria**.

---

## Kaj Loom je

Loom bere sanje iz obstoječih dnevniških aplikacij, generira semantične vektorje (embedinge) za vsako sanje in zazna ponavljajoče se vzorce skozi čas — ne da bi kadarkoli interpretiral kaj sanje pomenijo.

Filozofija izhaja iz internega dokumenta **CCP (Canonical Continuity Protocol)**: engine je non-authoritarian in probabilističen. Vzorce predlaga kot kandidate; uporabnik jih potrdi ali zavrne.

Arhitekturna prioriteta je **privacy-first, local-first**: podatki ostanejo na uporabnikovem računalniku, embedding model (`paraphrase-multilingual-MiniLM-L12-v2`) teče lokalno brez interneta po prvem prenosu.

## Kaj Loom ni

- Ni terapevtsko orodje in ne nadomešča strokovne pomoči
- Ni orakelj — ne trdi, da ve, kaj sanje pomenijo
- Ni nadzorno orodje — ne deli, ne prodaja in ne profilira podatkov

---

## Struktura repozitorija

```
loom/               Python engine — adapterji, embedingi, clustering, FastAPI
loom-ui/            React frontend (Vite) — deployan ločeno na Vercel
loom-extension/     Chrome extension (Manifest V3) — sync sanj iz Oneiro PWA
.github/workflows/  CI — testi za vse tri komponente
```

Vsak del ima lasten `README.md` s podrobnostmi. Ta datoteka je samo vstopna točka.

---

## Lokalni razvoj

### Backend

```bash
cd loom
docker compose up -d --build

# Docker Desktop → container loom_engine → Terminal
python loom.py status
python loom.py            # interaktivni meni
```

API dokumentacija: `http://localhost:8000/api/docs`

### UI

```bash
cd loom-ui
npm install
npm run dev
# → http://localhost:5173, pričakuje backend na localhost:8000
```

### Extension

`chrome://extensions` → Developer mode → Load unpacked → izberi `loom-extension/`

---

## Testi

```bash
# Backend (pytest, 55 testov)
cd loom && pip install -r requirements.txt && python -m pytest tests/ -v

# UI (vitest, 8 testov)
cd loom-ui && npm install && npm run test
```

CI poganja oboje samodejno ob vsakem pushu/PR-ju ki spremeni pripadajočo mapo (glej `.github/workflows/`). Extension nima pravega test suita — samo sintaktični check JS, veljavnost `manifest.json`, in preverjanje da je `manifest.json` verzija usklajena z `/VERSION`.

---

## Verzioniranje

[`/VERSION`](./VERSION) je edini vir resnice za verzijo celotnega projekta. Ker imajo tri komponente različne tehnične omejitve, se bere na tri različne načine:

| Komponenta | Kako se posodobi | Ročni korak? |
|---|---|---|
| Backend | Bere `/VERSION` dinamično ob vsakem zagonu (`loom/lib/version.py`) | Ne |
| UI | Bere `/VERSION` ob buildu, vgradi kot `__APP_VERSION__` (`loom-ui/vite.config.js`) | Ne |
| Extension | Chrome zahteva statičen niz v `manifest.json` — ne more se brati dinamično | Da — `node scripts/sync-extension-version.js` pred pakiranjem |

UI stran **Nastavitve** prikaže obe verziji (UI + backend) in opozori ob neujemanju.

Sprememba verzije: uredi `/VERSION`, zgradi UI (`npm run build`), za extension poženi sync script. CI preveri da `manifest.json` ni zaostal.

Zgodovina sprememb: [`CHANGELOG.md`](./CHANGELOG.md).

---

## Trenutno stanje

Testirano na realnem arhivu enega uporabnika: **4373 sanj, razpon 2005–2026**.

**Deluje:**
- Backfill iz Browser/Atlas in Lucid Lab virov
- Lokalna generacija embedingov
- Semantično iskanje (jezikovno neodvisno, sl+en), vektorizirano z numpy — ~300x hitrejše od prvotne implementacije
- Clustering (UMAP + HDBSCAN) — najde ~90 semantično koherentnih grup na testnem arhivu, brez kopičenja rezultatov med runi
- Detekcija ponavljajočih vzorcev z longitudinalnim razponom
- REST API s cache-anim iskalnim indeksom
- `/api/ingest` trajno shrani prejete sanje (`IngestedDreamStore`) — extension "api" način je zdaj funkcionalen
- React UI — dashboard, iskanje, vzorci, grupi, nastavitve (vklj. prikaz verzije); dvojezičen (sl/en), svetla/temna tema
- Test suite (55 backend + 8 UI testov) in CI za vse tri komponente

**Znane omejitve:**
- Prikaz celotnega besedila prikaže en spalni cikel, ne vseh ciklov iste noči
- Oneiro integracija prek extension je še vedno pretežno ročna (export/API način obstaja, ampak ni bila testirana v produkciji v velikem obsegu)
- UUID5 generacija v extension uporablja poenostavljeno hash funkcijo, ni bit-kompatibilna s Python backendom — glej [`loom-extension/README.md`](./loom-extension/README.md) §"Preklopitev na API način"
- Deployment (Vercel za UI, Tauri za backend distribucijo) še ni bil izveden — vse testiranje je lokalno prek Dockerja

---

## Nameravana distribucija

Ciljna platforma je **desktop aplikacija (Tauri)**, ne cloud SaaS — zaradi privacy-first usmeritve za splošno (ne nujno tehnično) javnost. Python engine teče kot lokalni sidecar proces znotraj Tauri lupine. Trenutni Docker setup služi izključno razvoju.

Monetizacija je predvidena kot naročnina z minimalnim licenčnim strežnikom (samo preverjanje licence, brez prenosa podatkov o sanjah).

---

## Širši Sentria ekosistem

Loom je ena od komponent večjega projekta ki povezuje: dnevniško beleženje sanj, vizualno mapiranje (Orbis/Dream Atlas), AI-podprto beleženje (Oneiro), orodja za lucidno sanjanje (Lucid Lab), zvočna okolja za spanje (Limina) in raziskovalno pisanje (Conscious Flow). Loomova vloga je semantični spomin, ki te aplikacije poveže brez poseganja v njihove izvorne podatkovne baze.
