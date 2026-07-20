# Loom — GitHub + Vercel Setup
## Enkratna konfiguracija za deployment

---

## 1. GitHub repozitorij

```bash
# V mapi loom/ (kjer je loom.py):
git init
git add .
git commit -m "Loom v0.1 — Phase 0"

# Ustvari repozitorij na GitHub (github.com → New repository)
# Ime: loom  (ali kar hočeš)
# Visibility: Private priporočeno (vsebuje config poti)

git remote add origin https://github.com/TVOJE_IME/loom.git
git branch -M main
git push -u origin main
```

---

## 2. Vercel projekt

1. Pojdi na [vercel.com](https://vercel.com) → **Add New Project**
2. Importaj GitHub repozitorij `loom`
3. Framework Preset: **Other**
4. Root Directory: `.` (pusti prazno)
5. Klikni **Deploy**

Vercel bo zaznal `vercel.json` in `api/` mapo avtomatsko.

Po deploymentu dobiš URL, npr: `https://loom-xyz.vercel.app`

Preveri da deluje:
```
https://loom-xyz.vercel.app/api/health
```
Mora vrniti:
```json
{"status": "ok", "service": "Loom", "version": "0.1.0"}
```

---

## 3. GitHub Secrets (za auto-deploy)

V GitHub repozitoriju → **Settings → Secrets and variables → Actions**

Dodaj tri secrets:

### VERCEL_TOKEN
1. Vercel → Settings → Tokens → **Create Token**
2. Ime: `github-actions`, Scope: `Full Account`
3. Kopiraj token → GitHub secret `VERCEL_TOKEN`

### VERCEL_ORG_ID
```bash
# V terminalu (kjer imaš Vercel CLI):
vercel whoami --json
# Vzami "id" vrednost
```
Ali: Vercel → Settings → General → **Team ID**

### VERCEL_PROJECT_ID
```bash
# Po prvem Vercel deploymentu se ustvari .vercel/project.json
# Vzami "projectId" vrednost
cat .vercel/project.json
```
Ali: Vercel → tvoj projekt → Settings → General → **Project ID**

---

## 4. Environment Variables na Vercelu

Vercel → tvoj projekt → **Settings → Environment Variables**

| Key | Value | Environment |
|-----|-------|-------------|
| `HF_API_KEY` | tvoj Hugging Face API ključ | Production, Preview |

### Kako dobiš HF_API_KEY:
1. [huggingface.co](https://huggingface.co) → prijava/registracija
2. Settings → Access Tokens → **New token**
3. Ime: `loom`, Role: `read`
4. Kopiraj token

Brez tega ključa embedingi delujejo v mock načinu (za testiranje OK,
za semantično analizo ne).

---

## 5. Lokalni .env (za Docker razvoj)

Ustvari `.env` datoteko v `loom/` mapi (gitignored):

```env
HF_API_KEY=hf_tvoj_kljuc_tukaj
```

Docker Compose jo pobere avtomatsko. Dodaj v `docker-compose.yml`:

```yaml
services:
  loom:
    env_file: .env
    ...
```

---

## 6. Workflow po setupu

```
Sprememba kode
    → git add . && git commit -m "opis"
    → git push origin main
    → GitHub Actions požene teste
    → Vercel auto-deploya na produkcijo
    → https://loom-xyz.vercel.app/api/health potrdi
```

---

## Struktura na Vercelu

```
/api/health.py    →  GET /api/health   (živ že zdaj)

Faza 5 (prihodnost):
/api/ingest.py    →  POST /api/ingest  (sprejme sanje iz Oneire/extensiona)
/api/search.py    →  GET /api/search   (semantično iskanje)
/api/enrich.py    →  GET /api/enrich   (enrichment za dream_id)
```

---

## Troubleshooting

**Build failed na Vercelu:**
Preveri `requirements.txt` — Vercel namesti vse pakete ob buildu.
Odkomentiraj samo tisto kar dejansko rabiš (pyyaml za zdaj zadostuje).

**Health endpoint vrne 500:**
Vercel → projekt → **Functions** → klikni na `health` → poglej logs.

**GitHub Actions failed:**
Actions → klikni na failed run → poglej kateri step je padel.
Najpogostejši razlog: manjkajoč secret.
