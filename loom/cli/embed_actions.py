# Loom CLI — Embedding akcije za meni
# cli/embed_actions.py
#
# Ločena datoteka da menu.py ostane pregleden.
# Importaj v menu.py kjer je potrebno.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cli.i18n import t, get
from cli.menu import (
    clear, print_header, print_footer, print_desc,
    press_enter, show_error, show_ok, confirm,
    source_submenu, print_menu, get_choice, prompt,
)


def action_embed():
    """Meni za embedding generacijo."""
    clear()
    print_header(t("EMBED_TITLE"))
    print_desc(t("EMBED_DESC"))

    lang = get()
    items = [
        ("run_all",    "Generiraj vse",        "procesira vse sanje v vrsti"),
        ("run_source", "Generiraj za vir",      "samo iz izbranega vira"),
        ("status",     t("EMBED_STATUS_TITLE"), "preveri pipeline in statistiko"),
    ] if lang.LANG_CODE == "sl" else [
        ("run_all",    "Generate all",         "process all queued dreams"),
        ("run_source", "Generate for source",  "from selected source only"),
        ("status",     t("EMBED_STATUS_TITLE"), "check pipeline and stats"),
    ]

    print_menu(items, extra_items=[("b", t("BACK"))])
    choice = get_choice(items, extra_keys=["b"])

    if choice == "b":
        return
    elif choice == "status":
        action_embed_status()
    elif choice == "run_all":
        action_embed_run(source=None)
    elif choice == "run_source":
        source = source_submenu(t("EMBED_TITLE"), include_all=False)
        if source:
            action_embed_run(source=source)


def action_embed_status():
    """Prikaži status embedding pipeline."""
    clear()
    print_header(t("EMBED_STATUS_TITLE"))
    print_footer()

    from lib.config import load_config
    from lib.embeddings import create_pipeline

    config = load_config("config.yaml")
    pipeline = create_pipeline(config)

    print(f"\n  {t('EMBED_CHECKING')}\n")

    # Provider health
    health = pipeline.health_check()
    icon = "✓" if health["ok"] else "✗"
    mode = health.get("mode", "")
    print(f"  {icon} Provider: {health['message']}")

    if mode == "mock":
        print()
        for line in t("EMBED_MOCK_WARNING").split("\n"):
            print(f"  ⚠ {line}")

    # Stats
    status = pipeline.status()
    print(f"\n  Model:      {status['model']}")
    print(f"  Provider:   {status['provider']}")
    print(f"  {t('EMBED_GENERATED'):12s} {status['embedded']}")
    print(f"  {t('EMBED_QUEUED'):12s} {status['queued']}")

    press_enter()


def action_embed_run(source=None):
    """Poženi embedding generacijo."""
    clear()
    print_header(t("EMBED_TITLE"))
    print_footer()

    from lib.config import load_config
    from lib.embeddings import create_pipeline
    from adapters.registry import create_adapter

    config = load_config("config.yaml")
    pipeline = create_pipeline(config)

    # Preveri mock način
    health = pipeline.health_check()
    if health.get("mode") == "mock":
        print()
        for line in t("EMBED_MOCK_WARNING").split("\n"):
            print(f"  ⚠ {line}")
        print()
        if not confirm():
            return

    # Naloži sanje iz adapterjev v spomin (za batch processing)
    print(f"\n  Nalagam sanje...")
    dreams_by_id = {}

    sources = [source] if source else config.enabled_sources()

    for source_name in sources:
        source_config = config.get_source_config(source_name)
        if not source_config:
            continue
        try:
            adapter = create_adapter(source_config)
            for dream in adapter.fetch_all():
                if dream.is_valid():
                    dreams_by_id[dream.dream_id] = dream
                    # Dodaj v embedding vrsto
                    pipeline.store.enqueue(dream.dream_id, dream.source_app)
        except Exception as e:
            show_error(f"{source_name}: {e}")

    total = len(dreams_by_id)
    queued = pipeline.store.queue_size()

    if queued == 0:
        print(f"\n  {t('EMBED_NONE')}")
        press_enter()
        return

    print(f"  Sanj skupaj: {total} · Za procesiranje: {queued}")
    print(f"\n  {t('EMBED_RUNNING')}\n")
    print(f"  {'─'*50}")

    last_pct = [-1]  # mutable za closure

    def on_progress(processed, total_q, failed):
        if total_q == 0:
            return
        pct = int(processed / total_q * 100)
        if pct != last_pct[0]:
            last_pct[0] = pct
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r  [{bar}] {pct:3d}%  {processed}/{total_q}  napak: {failed}  ", end="", flush=True)

    try:
        stats = pipeline.process_queue(dreams_by_id, on_progress=on_progress)
        print()  # nova vrstica po progress baru
        show_ok(
            f"{t('EMBED_COMPLETE')}: "
            f"{stats['processed']} {t('EMBED_GENERATED')}, "
            f"{stats['failed']} napak"
        )
    except Exception as e:
        print()
        show_error(str(e))

    press_enter()
