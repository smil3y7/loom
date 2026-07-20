# Loom CLI — Slovenščina (sl)
# Prevod: dodaj nov jezik tako da kopiraš to datoteko in prevedeš vrednosti.
# Ključev (levo od =) ne spreminjaj.

LANG_NAME = "Slovenščina"
LANG_CODE = "sl"

# ── Splošno ──────────────────────────────────────────────────────────────────

APP_TITLE        = "Loom"
APP_SUBTITLE     = "Semantična kontinuitetna plast"
PROMPT           = "Izbira"
BACK             = "Nazaj"
QUIT             = "Izhod"
HELP             = "Pomoč"
CONFIRM_YES      = "Da"
CONFIRM_NO       = "Ne"
CONFIRM_PROMPT   = "Potrdi? [d/n]"
PRESS_ENTER      = "Pritisni Enter za nadaljevanje..."
INVALID_CHOICE   = "Neveljavna izbira. Poskusi znova."
ERROR_PREFIX     = "Napaka"
SUCCESS_PREFIX   = "OK"
LOADING          = "Nalagam..."
DONE             = "Končano"
CANCELLED        = "Preklicano"

# ── Glavni meni ───────────────────────────────────────────────────────────────

MENU_MAIN_TITLE  = "Glavni meni"

MENU_ITEMS = {
    "status":       ("Status",          "preveri adapterje in baze"),
    "backfill":     ("Backfill",         "uvozi arhiv sanj v Loom"),
    "test":         ("Test adapterja",   "preveri posamezen vir"),
    "export":       ("Izvoz",            "izvozi sanje v JSON"),
    "language":     ("Jezik",            "spremeni jezik vmesnika"),
    "help":         ("Pomoč",            "razlaga ukazov"),
    "quit":         ("Izhod",            "zapri Loom"),
}

# ── Status ────────────────────────────────────────────────────────────────────

STATUS_TITLE         = "Status"
STATUS_DESC          = "Preveri ali Loom vidi vse vire sanj in prikaže napredek uvoza."
STATUS_CHECKING      = "Preverjam adapterje..."
STATUS_ADAPTER_OK    = "Dosegljiv"
STATUS_ADAPTER_FAIL  = "Nedosegljiv"
STATUS_BACKFILL_DONE = "uvoženo"
STATUS_BACKFILL_LEFT = "preostane"
STATUS_LAST_RUN      = "Zadnji zagon"
STATUS_NEVER_RUN     = "Še ni bilo zagona"
STATUS_NO_SOURCES    = "Ni konfiguriranih virov. Preveri config.yaml."

# ── Backfill ──────────────────────────────────────────────────────────────────

BACKFILL_TITLE   = "Backfill"
BACKFILL_DESC    = (
    "Procesira vse sanje iz izbranih virov in jih pripravi\n"
    "za semantično analizo. Varno je večkrat zagnati —\n"
    "že procesirane sanje preskoči."
)
BACKFILL_SELECT_SOURCE  = "Izberi vir:"
BACKFILL_ALL_SOURCES    = "Vsi viri"
BACKFILL_RESET_PROMPT   = "Pobriši obstoječe stanje in procesiraj vse znova?"
BACKFILL_RUNNING        = "Uvažam sanje iz"
BACKFILL_COMPLETE       = "Backfill končan"
BACKFILL_SKIPPED        = "preskočenih (že uvoženih)"
BACKFILL_FAILED         = "napak"
BACKFILL_NO_DREAMS      = "Ni sanj za uvoz. Preveri pot do baze v config.yaml."

# ── Test adapterja ────────────────────────────────────────────────────────────

TEST_TITLE          = "Test adapterja"
TEST_DESC           = "Preveri ali adapter uspešno bere vir in prikaže vzorčne zapise."
TEST_SELECT_SOURCE  = "Izberi adapter za testiranje:"
TEST_CONNECTING     = "Vzpostavljam povezavo z"
TEST_SHOWING        = "Vzorčni zapisi"
TEST_DREAM_ID       = "ID"
TEST_TIMESTAMP      = "Čas"
TEST_LANGUAGE       = "Jezik"
TEST_TITLE_FIELD    = "Naslov"
TEST_CONTENT        = "Vsebina"
TEST_LUCID          = "Lucidna"
TEST_TAGS           = "Oznake"
TEST_ATLAS_NODES    = "Atlas lokacije (potrjene)"
TEST_NO_RECORDS     = "Ni zapisov. Baza je morda prazna ali pot napačna."

# ── Izvoz ─────────────────────────────────────────────────────────────────────

EXPORT_TITLE        = "Izvoz"
EXPORT_DESC         = (
    "Izvozi sanje iz izbranega vira v JSON datoteko.\n"
    "Primerno za pregled canonical formata ali debugiranje."
)
EXPORT_SELECT       = "Izberi vir za izvoz:"
EXPORT_LIMIT        = "Število zapisov (Enter = 100):"
EXPORT_RUNNING      = "Izvažam..."
EXPORT_DONE         = "Izvoženo v"
EXPORT_INVALID_NUM  = "Neveljavna številka, uporabljam 100."

# ── Jezik ─────────────────────────────────────────────────────────────────────

LANGUAGE_TITLE      = "Izbira jezika"
LANGUAGE_DESC       = "Izberi jezik vmesnika."
LANGUAGE_CURRENT    = "Trenutni jezik"
LANGUAGE_CHANGED    = "Jezik spremenjen. Ponovni zagon ni potreben."

# ── Pomoč ─────────────────────────────────────────────────────────────────────

HELP_TITLE  = "Pomoč"
HELP_TEXT   = """
STATUS
  Preveri ali Loom uspešno vidi vse konfigurirane vire (baze sanj).
  Prikaže tudi napredek uvoza za vsak vir.

BACKFILL
  Uvozi arhiv sanj iz izbranega vira v Loom.
  Operacija je varna za večkratno zaganjanje — sanje ki so
  že uvožene preskoči. Priporočeno ob prvi uporabi in ob
  dodajanju novih sanj v vir.

TEST ADAPTERJA
  Preveri ali adapter uspešno komunicira z virom in prikaže
  prve zapise v canonical formatu. Uporabi za diagnostiko
  ko status poroča napako.

IZVOZ
  Izvozi sanje iz vira v JSON datoteko za pregled.
  Datoteka prikaže točno tisto kar Loom "vidi" iz vira —
  koristno za preverjanje pravilnosti mapiranja.

VIRI
  browser_atlas  — Dream Browser + Dream Atlas (SQLite)
  lab            — Lucid Lab (SQLite, Docker)
  oneiro         — Oneiro PWA (JSON export)

KONFIGURACIJA
  Nastavitve so v datoteki config.yaml (ali config.docker.yaml
  znotraj Docker containerja).
"""

# ── Atlas specifično ──────────────────────────────────────────────────────────

ATLAS_NODES_TITLE    = "Atlas lokacije"
ATLAS_STABILITY      = "stabilnost"
ATLAS_DREAMS_LINKED  = "povezanih sanj"
ATLAS_IS_HOME        = "Domača lokacija"

# ── Embedingi ─────────────────────────────────────────────────────────────────

EMBED_TITLE         = "Embedingi"
EMBED_DESC          = (
    "Generira semantične vektorje za sanje.\n"
    "Potrebno za iskanje, clustering in detekcijo vzorcev.\n"
    "Varno je večkrat zagnati — preskoči že generirane."
)
EMBED_STATUS_TITLE  = "Status embedingov"
EMBED_CHECKING      = "Preverjam embedding pipeline..."
EMBED_PROVIDER_OK   = "Provider dosegljiv"
EMBED_PROVIDER_FAIL = "Provider nedosegljiv"
EMBED_GENERATED     = "generiranih"
EMBED_QUEUED        = "v vrsti"
EMBED_NONE          = "Ni sanj za embedding. Najprej poženi Backfill."
EMBED_RUNNING       = "Generiram embedinge..."
EMBED_COMPLETE      = "Embedingi končani"
EMBED_MOCK_WARNING  = (
    "Opozorilo: HF_API_KEY ni nastavljen.\n"
    "Embedingi so v mock načinu — za testiranje pipeline,\n"
    "ne za semantično analizo. Nastavi HF_API_KEY za pravo delovanje."
)

MENU_ITEMS_EMBED = ("Embedingi", "generiraj semantične vektorje")

# ── Iskanje ───────────────────────────────────────────────────────────────────

SEARCH_TITLE        = "Iskanje"
SEARCH_DESC         = (
    "Semantično iskanje po arhivu sanj.\n"
    "Deluje v slovenščini in angleščini — ni potrebno ujemanje besed,\n"
    "išče po pomenu. 'staro mesto' najde sanje o mestih tudi\n"
    "če teh besed ni v besedilu."
)
SEARCH_PROMPT       = "Iskalni niz"
SEARCH_SIMILAR      = "Podobne sanje"
SEARCH_TOP_K        = "Število rezultatov (Enter = 10)"
SEARCH_LANG_FILTER  = "Filtriraj po jeziku? [sl/en/Enter = vse]"
SEARCH_RUNNING      = "Iščem..."
SEARCH_RESULTS      = "Rezultati"
SEARCH_NO_RESULTS   = "Ni rezultatov. Poskusi z drugačnim iskalnim nizom."
SEARCH_NOT_READY    = "Ni embedingov. Najprej poženi Backfill → Embedingi."
SEARCH_SIMILARITY   = "Podobnost"
SEARCH_SOURCE       = "Vir"
SEARCH_DATE         = "Datum"
SEARCH_RECURRING    = "Ponavljajoči vzorci"
SEARCH_RECURRING_DESC = (
    "Poišče skupine semantično podobnih sanj.\n"
    "Predogled pred pravim clusteringom (Faza 4)."
)
SEARCH_GROUPS_FOUND = "skupin najdenih"
SEARCH_GROUP        = "Skupina"
SEARCH_DREAMS       = "sanj"

MENU_ITEMS_SEARCH   = ("Iskanje", "semantično iskanje po arhivu")

MENU_ITEMS_SEARCH = ("Iskanje", "semantično iskanje po arhivu")

MENU_ITEMS_CLUSTER = ("Vzorci", "ponavljajoči vzorci in threads")
