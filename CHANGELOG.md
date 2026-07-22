# Changelog

Vse pomembne spremembe Loom projekta (backend, UI, extension) so zabeležene tukaj.

Ta datoteka se začenja **od zdaj naprej** — ne poskuša rekonstruirati natančnih datumov za vso razvojno zgodovino pred tem (backfill, embedingi, clustering, prvotni UI so nastali v prejšnjih razvojnih sejah brez natančnega beleženja po verzijah). Za pregled kaj trenutno deluje glej [`/README.md`](./README.md) §"Trenutno stanje".

Format sledi [Keep a Changelog](https://keepachangelog.com/), verzije [Semantic Versioning](https://semver.org/) (glej [`/VERSION`](./VERSION)).

---

## [0.1.0] — 2026-07-22

### Added
- `IngestedDreamStore` (`loom/lib/ingested_store.py`) — `/api/ingest` zdaj trajno shrani prejeto vsebino sanj namesto da jo zavrže; `get_dreams()` združuje adapter-sourced in ingested sanje
- Backend test suite — pytest, 55 testov (`loom/tests/`)
- UI test suite — vitest, 8 testov (`loom-ui/src/lib/__tests__/`)
- CI — GitHub Actions za backend teste, UI teste + build, extension sintaktični check (`.github/workflows/`)
- Enoten sistem verzioniranja — `/VERSION` kot vir resnice; backend bere dinamično, UI vgradi ob buildu, extension ima sync script (`scripts/sync-extension-version.js`) ker Chrome zahteva statičen niz
- Prikaz UI + backend verzije v Settings strani, z opozorilom ob neujemanju
- `docs/monetization-plan.md` — načrt za ecosystem-wide premium sloj (ne samostojen Loom subscription)
- `SQLiteAdapterMixin` (`loom/adapters/base.py`) — skupna connection-management logika za SQLite-based adapterje

### Fixed
- **Clustering rezultati so se kopičili med runi** — `ClusteringEngine.run()` ni brisal prejšnjih clustrov/threadov, samo dodajal nove; UI je prikazoval podvojene/zastarele rezultate. Popravljeno z brisanjem pred vsakim runom + ohranjanjem uporabnikovih potrditev prek ujemanja dream_id množic
- Nastavitev "API URL" v UI ni imela nobenega efekta — shranila se je v `localStorage`, ampak `api.js` je nikoli ni prebral nazaj
- `/api/ingest` je sprejel vsebino sanj in jo zavrgel — embedding step je nato nikoli našel dejanske vsebine za embedanje (glej "Added" zgoraj za popravek)
- Extension "api" način je klical napačen URL (`/ingest` namesto `/api/ingest`) — bi vrnil 404 ob vsakem poskusu
- `sqlite3.Row.get()` klic v error-handling fallbacku (`browser_atlas.py`, `lab.py`) — `sqlite3.Row` te metode nima, "varna" except veja je sama padla z `AttributeError` namesto da bi gladko zabeležila napako
- `create_pipeline()` je ignoriral `delay_ms`/`batch_size` iz configa, hardcodiral 500ms zamik ne glede na provider — nepotrebno upočasnilo lokalno embedanje
- Hardcoded angleški/slovenski stringi mimo i18n sistema (`App.jsx`, `api.js`) — kršitev projektne zahteve "brez hardcoded stringov"
- Statistika neuspelih embedingov je štela poskuse namesto unikatnih sanj — ena trajno pokvarjena sanja je v statistiki štela kot 3 neuspele
- `loom-extension/README.md` je napačno trdil da je `dream_id` iz extension bit-kompatibilen s Python UUID5 — dejansko uporablja poenostavljeno FNV hash funkcijo (dokumentacijski popravek, ne kode)

### Changed
- `LocalSearchIndex` (iskanje) vektoriziran z numpy — izmerjena ~300x pohitritev pri 4000 sanjah (179ms → 0.6ms na iskanje)
- Konsolidirana odpravlja podvajanja: `loom.py` ↔ `cli/menu.py` (status/backfill logika, `lib/backfill.py`), `browser_atlas.py` ↔ `lab.py` (connection management, `SQLiteAdapterMixin`)
- Vseh 8 clustering API endpointov zdaj uporablja `get_clustering_engine()` cache, konsistentno z `get_dreams()`/`get_search_engine()` patternom
- Odstranjena mrtva koda: `ContinuityEnrichment`, `RelatedDream`, `CandidateLocation`, `CandidateEntity`, podvojeni `CandidateThread`, `CCPEvent` iz `lib/schema.py` (nikoli uvoženi/uporabljeni)
- Odstranjen mrtev `force_full` parameter iz `ClusteringEngine.run()` in lažen "incremental" docstring (dejansko obnašanje: vedno poln refit)
- Konsolidirana backend dokumentacija — `loom/README.md` + `README_EN.md` nadomestita prej podvojene/protislovne `SETUP_SL.md`, `SETUP_EN.md`, `GITHUB_SETUP.md`
- Dodan `loom-ui/README.md` (prej ni obstajal)
