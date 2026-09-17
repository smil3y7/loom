# Changelog

Vse pomembne spremembe Loom projekta (backend, UI, extension) so zabeležene tukaj.

Ta datoteka se začenja **od zdaj naprej** — ne poskuša rekonstruirati natančnih datumov za vso razvojno zgodovino pred tem (backfill, embedingi, clustering, prvotni UI so nastali v prejšnjih razvojnih sejah brez natančnega beleženja po verzijah). Za pregled kaj trenutno deluje glej [`/README.md`](./README.md) §"Trenutno stanje".

Format sledi [Keep a Changelog](https://keepachangelog.com/), verzije [Semantic Versioning](https://semver.org/) (glej [`/VERSION`](./VERSION)).

---

## [0.4.1] — 2026-09-10

### Fixed
- Oneiro se je preselil na novo domeno (`oneiro-delta.vercel.app` → `sentria-oneiro.vercel.app`) — posodobljeno na treh mestih, ki so prej imela staro domeno hardcoded: `manifest.json` `host_permissions` (brez tega Chrome extensionu ne dovoli dostopa do taba na novi domeni, ne glede na JS), `background.js` in `popup.js` `ONEIRO_URL` konstanta.

---

## [0.4.0] — 2026-09-10

### Added
- **`/api/ingest` avtentikacija** (`lib/auth.py`, novo) — zahteva veljaven `X-Loom-Token` header; token se generira lokalno ob prvem dostopu (`secrets.token_urlsafe(32)`) in shrani v `{storage_path}/api_token`. `GET /api/token` / `POST /api/token/regenerate` za prikaz/regeneracijo prek Loom UI.
- Loom UI Nastavitve → nova sekcija "Povezava z Loom Sync extensionom" — prikaže pairing token za copy-paste, gumb za regeneracijo (z opozorilom da invalidira star pairing).
- Loom Sync extension — popolnoma nov settings zaslon (⚙ gumb v headerju): preklop način pošiljanja (prenos datoteke / direktno v Loom), nastavljiv API URL, polje za pairing token. Prej sta bila oba `DELIVERY_MODE`/`LOOM_API_URL` hardcoded konstanti v kodi.
- Extension: zgodovina zadnjih 10 sinhronizacij (prej se je shranil samo zadnji zapis, vsak nov sync je prejšnjega prepisal), noga s prikazom verzije extensiona.
- Extension `manifest.json` dobil fiksen `"key"` (Chrome extension ID zdaj stabilen: `olpdijedjldpggopmkmkijdahigpodob`, ne glede na to iz katere mape/poti je naložen unpacked, ali kasneje objavljen na Chrome Web Store z istim ključem).
- Testi: `loom/tests/test_auth.py` (6), razširjen `loom/tests/test_api_ingest.py` (+5 za token avtentikacijo).

### Changed
- **CORS zaklep** (`api/index.py`) — `allow_origins=["*"]` zamenjan z eksplicitno allowlist (Loom UI dev/preview strežnik + fiksen extension origin). `LOOM_ALLOWED_ORIGINS` env var za dodatne origine (npr. bodoč Tauri origin, še ne znan). PREJ: katerakoli spletna stran v istem brskalniku bi lahko poslala cross-origin zahtevo na kateri koli endpoint tega API-ja.
- `background.js`: `buildTimestamp(date, time)` — `time` parameter odstranjen (mrtev, protokol v2 nima ločenega `time` polja na Dream objektu, samo `date`).

### Security
- Kombinacija zgornjih dveh sprememb zapira vrzel, kjer bi zlonamerna/kompromitirana spletna stran v istem brskalniku lahko vrinila poljubne "sanje" v lokalni arhiv prek `/api/ingest` brez uporabnikove vednosti (glej razpravo pred to verzijo — prej ne CORS ne token nista obstajala).

---

## [0.3.0] — 2026-09-10

### Added
- `GET /api/dreams/{dream_id}/cycles` (`loom/api/index.py`) — vrne vse spalne cikle iste noči (isti `parent_dream_id`, urejeno po `cycle_index`); sanje brez nočnega grupiranja (Oneiro) vrne kot edini cikel, da UI lahko endpoint kliče brezpogojno
- `FullTextModal.jsx` prikaže cycle-switcher (zavihki "Cikel N od M"), kadar sanja pripada večciklni noči — prej je modal vedno prikazal samo en cikel, ostali cikli iste noči so bili nevidni/nepovezani
- `components/ConfirmRejectWorkflow.jsx` — deljena potrdi/zavrni/preimenuj komponenta; uporabljata jo `Clusters.jsx` in `Patterns.jsx`
- Clusters stran zdaj dejansko omogoča potrditev/zavrnitev/preimenovanje (backend endpointi in `api.js` klienti so obstajali že prej, ampak `Clusters.jsx` jih nikoli ni klical — stran je bila samo read-only prikaz)
- Testi: `loom/tests/test_api_cycles.py` (4), `loom/tests/test_version.py` +1 regresijski, `loom-ui/src/components/__tests__/FullTextModal.test.jsx` (3), `loom-ui/src/components/__tests__/ConfirmRejectWorkflow.test.jsx` (4)

### Fixed
- **`lib/version.py` je cacheiral verzijo za celotno življenjsko dobo procesa**, kar je nasprotovalo lastnemu komentarju ("bere dinamično ob vsakem klicu") — posledica: po bumpu `/VERSION` je dolgo živeč backend proces še naprej vračal staro verzijo dokler ni bil ročno restartan, kar se je pokazalo kot UI/Engine version mismatch v Nastavitvah. Cache odstranjen, dodan regresijski test ki dokazano pade na stari kodi.

### Changed
- `Patterns.jsx` prepisan na `ConfirmRejectWorkflow` — odstranjena podvojena dialog logika; mimogrede popravljen `alert()` anti-pattern (napaka iz confirm/reject klica se je prej pokazala kot browser popup in dialog se je zaprl skupaj z izgubljenim rename vnosom; zdaj napaka ostane v dialogu, dialog ostane odprt, vnos se ohrani)
- `clusters.about` i18n besedilo prepisano — prej generičen enostavčni opis, zdaj razloži razmerje cluster↔thread (cluster je širša surova množica, thread prečiščena podmnožica ki se ponavlja) in kaj potrditev/zavrnitev dejansko naredi (persistentno čez re-clustering rune, sanje se ne izbrišejo)
- `candidate_type` na Clusters strani prikazan preveden (`clusters.candidateType.*`), prej surov string ("thread"/"location"/...)

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
