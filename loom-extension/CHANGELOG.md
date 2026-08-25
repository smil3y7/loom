# Loom Sync Extension — Changelog

Ta datoteka sledi samo extensionu. Za celoten projekt (backend, UI) glej [`/CHANGELOG.md`](../CHANGELOG.md).

**Opomba o verzioniranju:** extension je trenutno verzioniran neodvisno od `/VERSION` (backend+UI enotnega vira) — verjetno ker se je razvijal vzporedno, mimo `scripts/sync-extension-version.js`. Če želiš enotno verzijo za ves projekt, to velja uskladiti; če je extension mišljen kot ločeno vzdrževan (npr. s strani Oneiro razvijalca), je neodvisno verzioniranje smiselno. Vredno eksplicitne odločitve.

---

## [0.2.3]

### Fixed
- **Preostala kolizija `dream_id` — isti mode regeneriran večkrat.** Popravek v 0.2.2 je diferenciral samo po `interp.mode` ("neutral"/"jungian"/"shamanic"), kar ni zadostovalo če je uporabnik isti mode večkrat regeneriral (Oneiro obdrži vse verzije kot ločene zapise z istim mode, različnim interpretation.id). Potrjeno na realnem exportu: sanja z dvema ločenima "neutral" interpretacijama je trčila na isti `dream_id`.
  - Popravek: diferenciator zdaj uporablja Oneirov lastni `interpretation.id` (zagotovljeno unikaten na zapis), z `mode` kot fallback če `id` manjka.
  - Dodano `metadata.extras.oneiro_interpretation_id` — vidno v shranjenih podatkih, ne samo interno uporabljeno.
- Popup zdaj (glej ločen popup.js commit/spremembo) jasneje loči "N zapisov" od "M sanj", ker en dream lahko proizvede več canonical zapisov (eden na interpretacijo) — prejšnje sporočilo "N sanj izvoženih" je zavajajoče kazalo N=število zapisov, ne dejansko število sanj.

### Known issue
- Star export (pred 0.2.2/0.2.3) ni retroaktivno popravljiv — `interpretation.id` v starih datotekah sploh ni bil zajet. Potreben je svež izvoz s to verzijo.

