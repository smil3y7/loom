# Loom UI

React (Vite) frontend za Loom. Ločeno deployan od backenda (npr. Vercel) —
komunicira z backend API-jem prek `VITE_API_URL`.

Za splošen pregled projekta glej korenski [`/README.md`](../README.md). Za backend glej [`../loom/README.md`](../loom/README.md).

---

## Struktura

```
src/
  App.jsx              routing, sidebar, engine online/offline status
  index.css            design tokens, svetla/temna tema
  main.jsx             entry point
  lib/
    api.js             vsi API klici — ena točka za URL (glej §API URL spodaj)
    theme.jsx           light/dark/system context
  i18n/
    index.jsx           vsi UI stringi, sl+en — brez hardcoded besedila
  components/
    FullTextModal.jsx   skupna komponenta za prikaz celotnega besedila sanje
  pages/
    Dashboard.jsx        statistike, hitro iskanje, status virov
    Search.jsx           semantično iskanje, filtri, similar dreams panel
    Patterns.jsx         vzorci — časovna premica, confirm/reject workflow
    Clusters.jsx         surove semantične grupe
    Settings.jsx         jezik, tema, API URL, verzija (UI + backend)
    Help.jsx              FAQ
```

---

## Lokalni razvoj

```bash
npm install
npm run dev
# → http://localhost:5173
# Pričakuje Loom backend na localhost:8000 (glej ../loom/README.md)
```

---

## API URL — kako se določi

Prioriteta (glej `src/lib/api.js`):

1. `localStorage.getItem('loom_api_url')` — če je uporabnik ročno nastavil v Settings strani
2. `VITE_API_URL` iz `.env` — build-time privzeta vrednost
3. `http://localhost:8000` — trdi fallback

Za lokalni razvoj kopiraj `.env.example` v `.env.local` in prilagodi po potrebi — privzeto že kaže na `localhost:8000`.

---

## Testi

```bash
npm run test
```

CI (`.github/workflows/ui-tests.yml`) poganja teste + `npm run build` samodejno ob vsakem pushu ki spremeni `loom-ui/**`.

---

## Verzioniranje

UI verzija se bere iz [`/VERSION`](../VERSION) (koren repozitorija) **ob buildu** — glej `vite.config.js`, ki datoteko prebere in vgradi kot `__APP_VERSION__`. Ni potreben noben ročni korak; vsak `npm run build` ali `npm run dev` samodejno uporabi trenutno vrednost iz `/VERSION`.

Prikazana je v UI-ju na strani **Nastavitve** — skupaj z verzijo backenda (prebrano prek `/health` API klica), da je neujemanje med UI in backend verzijo takoj vidno.

---

## Deploy (Vercel)

1. Build command: `npm run build`
2. Output directory: `dist`
3. Environment variable: `VITE_API_URL` — nastavi na dejanski naslov backend API-ja
4. `vercel.json` že vsebuje SPA rewrite pravilo (vse poti → `index.html`, potrebno za React Router)

Trenutna placeholder domena v dokumentaciji je `loom-sentria.vercel.app` — zamenjaj z dejansko domeno ob prvem deployu.
