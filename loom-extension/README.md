# Loom Sync — Browser Extension
### Oneiro → Loom · v0.1

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

## Preklopitev na API (Faza 5)

Ko bo Loom API živ, spremenite **eno vrstico** v `background.js`:

```javascript
// ZDAJ (download mode):
const DELIVERY_MODE = "download";

// PO PREKLOPU (api mode):
const DELIVERY_MODE = "api";
const LOOM_API_URL = "https://your-loom.vercel.app/ingest"; // vaš URL
```

Nato v `chrome://extensions` klikni **reload** na Loom Sync. To je vse.

---

## Tehnične podrobnosti

- Extension bere IndexedDB **samo ko je Oneiro odprt** v brskalniku
- Nobeni podatki ne gredo skozi strežnik v download načinu
- `dream_id` je identičen tistemu ki ga generira Python adapter
  (deterministični UUID5 iz enakega namespace)
- Extension nikoli ne piše v Oneiro — samo bere
