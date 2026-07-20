# Loom
### CCP v0.1 — Semantic Continuity Layer

---

## Struktura map

```
C:\Users\sasod\Documents\_Sanjanje\Loom\
    ├── docker-compose.yml          ← tukaj
    ├── start.bat                   ← dvoklik za zagon
    ├── loom\         ← engine koda
    │   ├── Dockerfile
    │   ├── config.docker.yaml
    │   ├── loom.py
    │   ├── lib\
    │   └── adapters\
    └── sources\                    ← SEM daš baze
        ├── dreamdb\
        │   └── dream_atlas_*.sqlite
        ├── lab\
        │   └── lucidlab.db
        └── oneiro\
            └── export_*.json
```

---

## Setup (enkrat)

### 1. Ustvari mapo sources\

```
C:\Users\sasod\Documents\_Sanjanje\Loom\sources\dreamdb\
C:\Users\sasod\Documents\_Sanjanje\Loom\sources\lab\
C:\Users\sasod\Documents\_Sanjanje\Loom\sources\oneiro\
```

### 2. Kopiraj baze

**Browser + Atlas:**
Kopiraj `dream_atlas_*.sqlite` iz DreamDB mape v `sources\dreamdb\`

**LucidLab:**
Kopiraj `lucidlab.db` iz Docker volumna v `sources\lab\`

Najlažje iz Docker Desktop:
- Klikni na `lucid_lab` container
- Zavihek **Files**
- Navigiraj na `/app/data/lucidlab.db`
- Desni klik → **Save**
- Shrani v `sources\lab\lucidlab.db`

**Oneiro:**
Exportiraj sanje iz Oneire kot JSON, shrani v `sources\oneiro\`

### 3. Zaženi

Dvoklik na `start.bat`

### 4. Testiraj

Docker Desktop → `loom_engine` → Terminal:

```bash
python loom.py status
python loom.py test-adapter browser_atlas
python loom.py test-adapter lab
python loom.py test-adapter oneiro
```

---

## Sinhronizacija baz

Baze so statične kopije — engine jih ne posodablja avtomatsko.

Ko hočeš svežo sinhronizacijo:
1. Kopiraj novo verzijo baze v `sources\`
2. V terminalu: `python loom.py backfill --source browser_atlas`
   (backfill preskoči že procesirane sanje — hiter)

---

## CLI ukazi

```bash
python loom.py status                       # zdravje + backfill stanje
python loom.py backfill                     # backfill vseh virov
python loom.py backfill --source lab        # samo Lab
python loom.py backfill --reset             # pobriši stanje, procesira vse znova
python loom.py test-adapter browser_atlas   # preveri adapter + vzorčni zapisi
python loom.py export browser_atlas         # izvozi canonical JSON
python loom.py export browser_atlas --limit 20
```

---

## Faze razvoja

- [x] **Faza 0** — Shema, adapterji, backfill infrastruktura, Docker
- [ ] **Faza 1** — Embedding pipeline
- [ ] **Faza 2** — Semantično iskanje
- [ ] **Faza 3** — Storage (Supabase)
- [ ] **Faza 4** — Clustering + detekcija threadov
- [ ] **Faza 5** — FastAPI + Vercel
- [ ] **Faza 6** — Opcijska AI sinteza
