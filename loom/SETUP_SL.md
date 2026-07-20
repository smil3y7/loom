# Loom — Namestitev in konfiguracija
### Tehnična dokumentacija · sl

---

## Kaj je Loom

Loom je semantična kontinuitetna plast za Sentria ekosistem. Deluje kot ozadnji servis ki:

- bere sanje iz obstoječih appov (Dream Browser, Lucid Lab, Oneiro)
- generira semantične embedinge za vsako sanje
- omogoča iskanje po arhivu v slovenščini in angleščini
- zazna ponavljajoče vzorce, lokacije in teme

Loom ne nadomešča obstoječih appov — samo bere njihove podatke in doda semantično plast.

---

## Sistemske zahteve

- Windows 10/11
- Docker Desktop (https://www.docker.com/products/docker-desktop)
- 4 GB RAM (priporočeno 8 GB)
- ~500 MB prostora na disku
- Internetna povezava za embedding generacijo

---

## Namestitev

### 1. Pripravi mapno strukturo

Ustvari glavno mapo in podmape:

```
C:\Users\ime\Documents\_Sanjanje\Loom\
    ├── loom\                ← engine koda (iz zipa)
    ├── sources\
    │   ├── dreamdb\         ← Dream Browser + Atlas SQLite baza
    │   ├── lab\             ← Lucid Lab SQLite baza
    │   └── oneiro\          ← Oneiro JSON exporti
    ├── storage\             ← Loom lastni podatki (samodejno)
    ├── docker-compose.yml   ← iz zipa
    ├── Dockerfile           ← iz zipa
    ├── config.docker.yaml   ← iz zipa
    └── start.bat            ← iz zipa
```

### 2. Razpakiraj Loom

Razpakiraj `loom-phase0-clean.zip` v glavno mapo. Vsebina zipa gre direktno noter.

### 3. Kopiraj baze

**Dream Browser + Atlas:**
Kopiraj `dream_atlas_*.sqlite` iz `DreamDB\` v `sources\dreamdb\`

**Lucid Lab:**
Docker Desktop → container `lucid_lab` → zavihek **Files** → `/app/data/` → desni klik na `.db` datoteko → **Save** → shrani v `sources\lab\`

**Oneiro:**
Uporabi Loom Sync browser extension (navodila spodaj).

### 4. Nastavi Hugging Face API token

Odpri `docker-compose.yml` in zamenjaj `hf_xxxx` z dejanskim tokenom:

```yaml
environment:
  - HF_API_KEY=hf_tvoj_dejanski_token
```

Token dobiš na: https://huggingface.co → Settings → Access Tokens → New token (Read)

### 5. Zaženi

Dvoklik na `start.bat`. Docker Desktop zgradi in zažene Loom container.

---

## Upravljanje

Odpri Docker Desktop → container `loom_engine` → zavihek **Terminal**:

```bash
python loom.py          # interaktivni meni
python loom.py status   # stanje adapterjev
```

### Interaktivni meni

```
1. Status          preveri adapterje in baze
2. Backfill        uvozi arhiv sanj v Loom
3. Embedingi       generiraj semantične vektorje
4. Iskanje         semantično iskanje po arhivu
5. Test adapterja  preveri posamezen vir
6. Izvoz           izvozi sanje v JSON
7. Jezik           spremeni jezik vmesnika
q. Izhod
```

### Priporočen vrstni red ob prvi uporabi

```
1. Status          → preveri da Loom vidi vse baze
2. Backfill        → uvozi arhiv (za 4000+ sanj ~5-10 minut)
3. Embedingi       → generiraj vektorje (za 4000+ sanj ~20 minut)
4. Iskanje         → preizkusi semantično iskanje
```

---

## Loom Sync Extension

Extension za Chrome omogoča izvoz sanj iz Oneiro PWA.

### Namestitev

1. Razpakiraj `loom-extension.zip`
2. Desni klik na mapo → Properties → **Unblock** (Windows varnostna nastavitev)
3. Chrome → `chrome://extensions` → Developer mode (vklopi) → **Load unpacked**
4. Izberi mapo `loom-extension\` kjer je `manifest.json` direktno vidna

### Uporaba

1. Odpri Oneiro v brskalniku
2. Klikni ikono Loom Sync v orodni vrstici
3. Klikni **Sync z Loom**
4. Datoteka se prenese v Downloads
5. Premakni jo v `Loom\sources\oneiro\`

---

## Sync med računalniki

Mapa `storage\` vsebuje vse Loom podatke:

```
storage\
  ├── state.db       ← backfill stanje
  └── embeddings.db  ← semantični vektorji
```

Za prenos na drugi računalnik: kopiraj celo `storage\` mapo. Na novem računalniku ni potrebno znova poganjati backfill ali embedding generacije.

---

## Dodajanje novega app vira

1. Ustvari `adapters/novo_ime.py` ki razširja `BaseAdapter`
2. Implementiraj `fetch_all()`, `fetch_since()`, `fetch_one()`, `count_total()`
3. Dodaj v `adapters/registry.py` eno vrstico
4. Dodaj vnos v `config.docker.yaml`

Nobenih sprememb v obstoječih appih ni potrebnih.

---

## Odpravljanje težav

**Status prikazuje napako za vir:**
- Preveri da je datoteka v pravi podmapi `sources\`
- Preveri ime datoteke — glob pattern `dream_atlas_*.sqlite` mora ustrezati

**Embedingi se ne generirajo:**
- Preveri `HF_API_KEY` v `docker-compose.yml`
- Token mora začeti z `hf_`
- Preveri internetno povezavo

**Container se ne zažene:**
- Docker Desktop mora biti zagnan
- Preveri da port 8000 ni zaseden

---

## Faze razvoja

| Faza | Opis | Status |
|---|---|---|
| 0 | Adapterji, backfill, CLI | ✓ Končano |
| 1 | Embedding pipeline | ✓ Končano |
| 2 | Semantično iskanje | ✓ Končano |
| 3 | Supabase storage | V načrtu |
| 4 | Clustering, thread detekcija | V načrtu |
| 5 | FastAPI + Vercel deploy | V načrtu |
| 6 | Sentria Hub integracija | V načrtu |
| 7 | AI sinteza | V načrtu |
