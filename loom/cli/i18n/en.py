# Loom CLI — English (en)
# Translation: add a new language by copying this file and translating the values.
# Do not change the keys (left side of =).

LANG_NAME = "English"
LANG_CODE = "en"

# ── General ───────────────────────────────────────────────────────────────────

APP_TITLE        = "Loom"
APP_SUBTITLE     = "Semantic Continuity Layer"
PROMPT           = "Choice"
BACK             = "Back"
QUIT             = "Quit"
HELP             = "Help"
CONFIRM_YES      = "Yes"
CONFIRM_NO       = "No"
CONFIRM_PROMPT   = "Confirm? [y/n]"
PRESS_ENTER      = "Press Enter to continue..."
INVALID_CHOICE   = "Invalid choice. Please try again."
ERROR_PREFIX     = "Error"
SUCCESS_PREFIX   = "OK"
LOADING          = "Loading..."
DONE             = "Done"
CANCELLED        = "Cancelled"

# ── Main menu ─────────────────────────────────────────────────────────────────

MENU_MAIN_TITLE  = "Main menu"

MENU_ITEMS = {
    "status":       ("Status",          "check adapters and sources"),
    "backfill":     ("Backfill",         "import dream archive into Loom"),
    "test":         ("Test adapter",     "verify a specific source"),
    "export":       ("Export",           "export dreams to JSON"),
    "language":     ("Language",         "change interface language"),
    "help":         ("Help",             "command reference"),
    "quit":         ("Quit",             "exit Loom"),
}

# ── Status ────────────────────────────────────────────────────────────────────

STATUS_TITLE         = "Status"
STATUS_DESC          = "Check whether Loom can reach all dream sources and show import progress."
STATUS_CHECKING      = "Checking adapters..."
STATUS_ADAPTER_OK    = "Reachable"
STATUS_ADAPTER_FAIL  = "Unreachable"
STATUS_BACKFILL_DONE = "imported"
STATUS_BACKFILL_LEFT = "remaining"
STATUS_LAST_RUN      = "Last run"
STATUS_NEVER_RUN     = "Never run"
STATUS_NO_SOURCES    = "No sources configured. Check config.yaml."

# ── Backfill ──────────────────────────────────────────────────────────────────

BACKFILL_TITLE   = "Backfill"
BACKFILL_DESC    = (
    "Processes all dreams from selected sources and prepares them\n"
    "for semantic analysis. Safe to run multiple times —\n"
    "already processed dreams are skipped."
)
BACKFILL_SELECT_SOURCE  = "Select source:"
BACKFILL_ALL_SOURCES    = "All sources"
BACKFILL_RESET_PROMPT   = "Clear existing state and reprocess everything?"
BACKFILL_RUNNING        = "Importing dreams from"
BACKFILL_COMPLETE       = "Backfill complete"
BACKFILL_SKIPPED        = "skipped (already imported)"
BACKFILL_FAILED         = "errors"
BACKFILL_NO_DREAMS      = "No dreams to import. Check the source path in config.yaml."

# ── Test adapter ──────────────────────────────────────────────────────────────

TEST_TITLE          = "Test adapter"
TEST_DESC           = "Verify that the adapter can read the source and show sample records."
TEST_SELECT_SOURCE  = "Select adapter to test:"
TEST_CONNECTING     = "Connecting to"
TEST_SHOWING        = "Sample records"
TEST_DREAM_ID       = "ID"
TEST_TIMESTAMP      = "Time"
TEST_LANGUAGE       = "Language"
TEST_TITLE_FIELD    = "Title"
TEST_CONTENT        = "Content"
TEST_LUCID          = "Lucid"
TEST_TAGS           = "Tags"
TEST_ATLAS_NODES    = "Atlas locations (confirmed)"
TEST_NO_RECORDS     = "No records found. Database may be empty or path incorrect."

# ── Export ────────────────────────────────────────────────────────────────────

EXPORT_TITLE        = "Export"
EXPORT_DESC         = (
    "Export dreams from a selected source to a JSON file.\n"
    "Useful for inspecting the canonical format or debugging."
)
EXPORT_SELECT       = "Select source to export:"
EXPORT_LIMIT        = "Number of records (Enter = 100):"
EXPORT_RUNNING      = "Exporting..."
EXPORT_DONE         = "Exported to"
EXPORT_INVALID_NUM  = "Invalid number, using 100."

# ── Language ──────────────────────────────────────────────────────────────────

LANGUAGE_TITLE      = "Language selection"
LANGUAGE_DESC       = "Choose the interface language."
LANGUAGE_CURRENT    = "Current language"
LANGUAGE_CHANGED    = "Language changed. No restart required."

# ── Help ──────────────────────────────────────────────────────────────────────

HELP_TITLE  = "Help"
HELP_TEXT   = """
STATUS
  Checks whether Loom can successfully reach all configured sources.
  Also shows import progress for each source.

BACKFILL
  Imports the dream archive from a selected source into Loom.
  Safe to run multiple times — already imported dreams are skipped.
  Recommended on first use and after adding new dreams to a source.

TEST ADAPTER
  Verifies that the adapter communicates with the source successfully
  and displays the first records in canonical format. Use for
  diagnostics when status reports an error.

EXPORT
  Exports dreams from a source to a JSON file for inspection.
  The file shows exactly what Loom "sees" from the source —
  useful for verifying correct field mapping.

SOURCES
  browser_atlas  — Dream Browser + Dream Atlas (SQLite)
  lab            — Lucid Lab (SQLite, Docker)
  oneiro         — Oneiro PWA (JSON export)

CONFIGURATION
  Settings are in config.yaml (or config.docker.yaml
  inside the Docker container).
"""

# ── Atlas specific ────────────────────────────────────────────────────────────

ATLAS_NODES_TITLE    = "Atlas locations"
ATLAS_STABILITY      = "stability"
ATLAS_DREAMS_LINKED  = "linked dreams"
ATLAS_IS_HOME        = "Home location"

# ── Embeddings ────────────────────────────────────────────────────────────────

EMBED_TITLE         = "Embeddings"
EMBED_DESC          = (
    "Generates semantic vectors for dreams.\n"
    "Required for search, clustering and pattern detection.\n"
    "Safe to run multiple times — skips already generated."
)
EMBED_STATUS_TITLE  = "Embedding status"
EMBED_CHECKING      = "Checking embedding pipeline..."
EMBED_PROVIDER_OK   = "Provider reachable"
EMBED_PROVIDER_FAIL = "Provider unreachable"
EMBED_GENERATED     = "generated"
EMBED_QUEUED        = "queued"
EMBED_NONE          = "No dreams to embed. Run Backfill first."
EMBED_RUNNING       = "Generating embeddings..."
EMBED_COMPLETE      = "Embeddings complete"
EMBED_MOCK_WARNING  = (
    "Warning: HF_API_KEY is not set.\n"
    "Embeddings are in mock mode — suitable for testing the pipeline,\n"
    "not for semantic analysis. Set HF_API_KEY for real embeddings."
)

MENU_ITEMS_EMBED = ("Embeddings", "generate semantic vectors")

# ── Search ────────────────────────────────────────────────────────────────────

SEARCH_TITLE        = "Search"
SEARCH_DESC         = (
    "Semantic search across the dream archive.\n"
    "Works in Slovenian and English — no exact word match needed,\n"
    "searches by meaning. 'old station' finds dreams about stations\n"
    "even if those exact words aren't in the text."
)
SEARCH_PROMPT       = "Search query"
SEARCH_SIMILAR      = "Similar dreams"
SEARCH_TOP_K        = "Number of results (Enter = 10)"
SEARCH_LANG_FILTER  = "Filter by language? [sl/en/Enter = all]"
SEARCH_RUNNING      = "Searching..."
SEARCH_RESULTS      = "Results"
SEARCH_NO_RESULTS   = "No results. Try a different search query."
SEARCH_NOT_READY    = "No embeddings yet. Run Backfill → Embeddings first."
SEARCH_SIMILARITY   = "Similarity"
SEARCH_SOURCE       = "Source"
SEARCH_DATE         = "Date"
SEARCH_RECURRING    = "Recurring patterns"
SEARCH_RECURRING_DESC = (
    "Finds groups of semantically similar dreams.\n"
    "Preview before full clustering (Phase 4)."
)
SEARCH_GROUPS_FOUND = "groups found"
SEARCH_GROUP        = "Group"
SEARCH_DREAMS       = "dreams"

MENU_ITEMS_SEARCH   = ("Search", "semantic search across archive")

MENU_ITEMS_SEARCH = ("Search", "semantic search across archive")

MENU_ITEMS_CLUSTER = ("Patterns", "recurring patterns and threads")
