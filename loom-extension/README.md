# Loom Sync — Browser Extension
### Oneiro → Loom

---

## Instalacija (enkrat)

1. Odpri Chrome → naslovna vrstica → `chrome://extensions`
2. Zgoraj desno: **Developer mode** → vklopi
3. Klikni **Load unpacked**
4. Izberi mapo `loom-extension/`
5. Ikona Loom Sync se pojavi v orodni vrstici

---

## Uporaba

1. Odpri **Oneiro** v brskalniku (`https://oneiro-delta.vercel.app`)
2. Klikni ikono **Loom Sync** v orodni vrstici
3. Klikni **Sync z Loom**
4. Datoteka se shrani v Downloads mapo
5. Premakni jo v `Loom/sources/oneiro/`

**Samo nove sanje** — sync samo sanj od zadnjega exporta naprej.

---

## Preklopitev na API način

Loom backend zdaj dejansko shrani sanje poslane prek `/api/ingest` (prej ni — glej opombo spodaj), torej je API način funkcionalen. Spremeni v `background.js`:

```javascript
// ZDAJ (download mode):
const DELIVERY_MODE = "download";

// PO PREKLOPU (api mode):
const DELIVERY_MODE = "api";
const LOOM_API_URL = "http://localhost:8000/api/ingest"; // ne pozabi /api prefiksa
```

Nato v `chrome://extensions` klikni **reload** na Loom Sync.

**Znana omejitev pri API načinu:** `dream_id` generiran v `background.js` (`makeUuid5`) uporablja poenostavljeno FNV hash funkcijo, **ni** bit-kompatibilen s pravim UUID5 ki ga generira Python backend (`lib/schema.py: make_dream_id`). To pomeni da ista sanja poslana prek extension in kasneje prebrana prek morebitnega direktnega Oneiro adapterja dobi **različna** `dream_id` — ne bo prepoznana kot ista sanja. Ni kritično dokler je edini vir za Oneiro sanje extension sam (ni duplikacije), ampak ni pravi UUID5. Popravek bi zahteval SubtleCrypto SHA-1 implementacijo v JS namesto trenutnega FNV hasha — ni bilo prioritetno dokler je bil "api" način neuporaben (glej git zgodovino za kontekst popravka `/api/ingest`).

---

## Tehnične podrobnosti

- Extension **ne bere več IndexedDB neposredno**. Oneiro zdaj podpira šifriranje vsebine at-rest (PIN/geslo) — ko je nastavljeno, so zapisi v IndexedDB vedno šifrirani, ne glede na to, ali je uporabnik trenutno odklenjen (ključ živi samo v pomnilniku odprte Oneiro strani). Neposredno branje bi zato vedno vrnilo 0 uporabnih sanj.
- Namesto tega extension prosi Oneiro stran samo prek `postMessage` mostu (`docs/loom-sync-protocol.md` v Oneiro repozitoriju) — Oneiro (ker je odprt in odklenjen) odgovori z že dešifrirano vsebino. Extension nikoli ne vidi šifriranega bloka niti ključa.
- **Zahteva Oneiro različico z nameščenim mostom** (`src/bridge/loomSyncBridge.js`). Če je Oneiro tab star (brez tega popravka), sync po 5 sekundah javi "Oneiro ni odgovoril".
- Če je Oneiro zaklenjen (PIN ni vnešen), sync javi jasno napako namesto tihega "0 sanj".
- Extension bere podatke **samo ko je Oneiro odprt** v brskalniku (nespremenjeno).
- Nobeni podatki ne gredo skozi strežnik v download načinu.
- Extension nikoli ne piše v Oneiro — samo bere.

---

## Verzioniranje

`manifest.json` mora imeti verzijo usklajeno z [`/VERSION`](../VERSION) (koren repozitorija). Chrome zahteva statičen niz — ne more se brati dinamično. Pred pakiranjem za Chrome Web Store poženi:

```bash
node scripts/sync-extension-version.js
```

CI (`.github/workflows/extension-check.yml`) preveri ob vsakem pushu da `manifest.json` ni zaostal za `/VERSION`.

