# Loom CLI — Interaktivni meni
# Navigacija z številkami, razlage ob vsakem ukazu.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cli.i18n import t, get, available, set_language, current_code


# ── Vizualni elementi ─────────────────────────────────────────────────────────

WIDTH = 56

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def line(char="─"):
    return char * WIDTH

def box_top():    return "╔" + "═" * WIDTH + "╗"
def box_mid():    return "╠" + "═" * WIDTH + "╣"
def box_bot():    return "╚" + "═" * WIDTH + "╝"
def box_row(text=""):
    return "║  " + text + " " * max(0, WIDTH - 2 - len(text)) + "║"

def print_header(subtitle=None):
    lang = get()
    print(box_top())
    print(box_row(f"{lang.APP_TITLE}"))
    if subtitle:
        print(box_row(subtitle))
    else:
        print(box_row(lang.APP_SUBTITLE))
    print(box_mid())

def print_footer():
    print(box_bot())

def print_desc(text):
    """Izpiše opis ukaza pod menijem."""
    print()
    for line_text in text.split("\n"):
        print(f"  {line_text}")
    print()

def prompt(text=None):
    lang = get()
    label = text or lang.PROMPT
    return input(f"\n  {label}: ").strip()

def press_enter():
    input(f"\n  {t('PRESS_ENTER')}")

def show_error(msg):
    print(f"\n  ✗ {t('ERROR_PREFIX')}: {msg}")

def show_ok(msg):
    print(f"\n  ✓ {msg}")

def confirm(question=None):
    lang = get()
    q = question or lang.CONFIRM_PROMPT
    ans = input(f"\n  {q} ").strip().lower()
    return ans in ("d", "y", "da", "yes", "1")


# ── Meni builder ──────────────────────────────────────────────────────────────

def print_menu(items: list[tuple], extra_items: list[tuple] = None):
    """
    items: [(key, label, description), ...]
    extra_items: [(key, label), ...]  — brez opisa, za h/q
    """
    print()
    for i, (key, label, desc) in enumerate(items, 1):
        row = f"{i}. {label}"
        if desc:
            row += f"  —  {desc}"
        print(box_row(row))

    if extra_items:
        print(box_row())
        for key, label in extra_items:
            print(box_row(f"{key}. {label}"))

    print_footer()


def get_choice(items: list[tuple], extra_keys: list[str] = None) -> str:
    """Vrni ključ izbrane možnosti ali extra_key."""
    extra_keys = extra_keys or []
    valid_nums = {str(i): item[0] for i, item in enumerate(items, 1)}

    while True:
        raw = prompt()
        if raw.lower() in extra_keys:
            return raw.lower()
        if raw in valid_nums:
            return valid_nums[raw]
        print(f"  {t('INVALID_CHOICE')}")


# ── Podmeniji ─────────────────────────────────────────────────────────────────

def source_submenu(action_label: str, include_all: bool = True) -> str | None:
    """
    Prikaže seznam virov, vrne ime vira ali None (nazaj).
    action_label: kratek opis akcije (npr. "Backfill", "Test")
    """
    from lib.config import load_config
    config = load_config("config.yaml")
    sources = config.enabled_sources()

    clear()
    print_header(action_label)

    items = []
    if include_all:
        items.append(("__all__", t("BACKFILL_ALL_SOURCES"), ""))
    for s in sources:
        items.append((s, s, ""))

    print_menu(items, extra_items=[("b", t("BACK"))])

    choice = get_choice(items, extra_keys=["b"])
    if choice == "b":
        return None
    return choice


# ── Akcije ────────────────────────────────────────────────────────────────────

def action_status():
    clear()
    print_header(t("STATUS_TITLE"))
    print_desc(t("STATUS_DESC"))
    print_footer()

    from lib.config import load_config
    from lib.backfill import get_source_status

    config = load_config("config.yaml")
    sources = config.enabled_sources()

    if not sources:
        show_error(t("STATUS_NO_SOURCES"))
        press_enter()
        return

    print(f"\n  {t('STATUS_CHECKING')}\n")

    for source_name in sources:
        try:
            result = get_source_status(config, source_name)
            health = result["health"]
            icon = "✓" if health["ok"] else "✗"
            status_label = t("STATUS_ADAPTER_OK") if health["ok"] else t("STATUS_ADAPTER_FAIL")
            print(f"  {icon} {source_name:20s} {status_label}")

            if result["backfill"]:
                st = result["backfill"]
                done, total, left, pct = st["processed"], st["total"], st["remaining"], st["percent"]
                print(f"    {'':20s} {done}/{total} ({pct}%) · {left} {t('STATUS_BACKFILL_LEFT')}")

                if st["last_run"]:
                    run_date = st["last_run"]["started_at"][:10]
                    run_status = st["last_run"]["status"]
                    print(f"    {'':20s} {t('STATUS_LAST_RUN')}: {run_date} ({run_status})")
                else:
                    print(f"    {'':20s} {t('STATUS_NEVER_RUN')}")
        except Exception as e:
            print(f"  ✗ {source_name:20s} {t('ERROR_PREFIX')}: {e}")
        print()

    press_enter()


def action_backfill():
    source = source_submenu(t("BACKFILL_TITLE"), include_all=True)
    if source is None:
        return

    clear()
    print_header(t("BACKFILL_TITLE"))
    print_desc(t("BACKFILL_DESC"))
    print_footer()

    # Ask about reset
    do_reset = confirm(t("BACKFILL_RESET_PROMPT"))

    from lib.config import load_config
    from lib.backfill import run_source_backfill

    config = load_config("config.yaml")
    sources = [source] if source != "__all__" else config.enabled_sources()

    print()
    for source_name in sources:
        try:
            print(f"\n  {t('BACKFILL_RUNNING')} {source_name}...")
            progress = run_source_backfill(
                config, source_name, on_dream=_noop_processor, reset=do_reset,
            )
            show_ok(f"{t('BACKFILL_COMPLETE')}: {progress.processed} {t('STATUS_BACKFILL_DONE')}, "
                    f"{progress.skipped} {t('BACKFILL_SKIPPED')}, "
                    f"{progress.failed} {t('BACKFILL_FAILED')}")
        except Exception as e:
            show_error(str(e))

    press_enter()


def action_test():
    source = source_submenu(t("TEST_TITLE"), include_all=False)
    if source is None:
        return

    clear()
    print_header(t("TEST_TITLE"))
    print_desc(t("TEST_DESC"))
    print_footer()

    from lib.config import load_config
    from adapters.registry import create_adapter
    from adapters.browser_atlas import BrowserAtlasAdapter

    config = load_config("config.yaml")
    source_config = config.get_source_config(source)

    print(f"\n  {t('TEST_CONNECTING')} {source}...")

    try:
        adapter = create_adapter(source_config)
        health = adapter.health_check()

        icon = "✓" if health["ok"] else "✗"
        print(f"  {icon} {health['message']}\n")

        if not health["ok"]:
            press_enter()
            return

        print(f"  {t('TEST_SHOWING')}:\n")
        count = 0
        for dream in adapter.fetch_all():
            if count >= 3:
                break
            print(f"  {'─'*50}")
            print(f"  {t('TEST_DREAM_ID'):12s} {dream.dream_id}")
            print(f"  {t('TEST_TIMESTAMP'):12s} {dream.timestamp}")
            print(f"  {t('TEST_LANGUAGE'):12s} {dream.language}")
            if dream.title:
                print(f"  {t('TEST_TITLE_FIELD'):12s} {dream.title}")
            preview = dream.content[:120].replace("\n", " ")
            print(f"  {t('TEST_CONTENT'):12s} {preview}...")
            if dream.metadata.lucid is not None:
                print(f"  {t('TEST_LUCID'):12s} {dream.metadata.lucid}")
            if dream.metadata.tags:
                print(f"  {t('TEST_TAGS'):12s} {', '.join(dream.metadata.tags)}")
            print()
            count += 1

        if count == 0:
            print(f"  {t('TEST_NO_RECORDS')}")

        # Atlas nodes
        if isinstance(adapter, BrowserAtlasAdapter):
            try:
                nodes = adapter.fetch_atlas_nodes()
                if nodes:
                    print(f"\n  {t('TEST_ATLAS_NODES')}: {len(nodes)}")
                    for node in nodes[:3]:
                        home = f" · {t('ATLAS_IS_HOME')}" if node["is_home"] else ""
                        print(f"    - {node['name']} "
                              f"({t('ATLAS_STABILITY')}: {node['stability']}, "
                              f"{len(node['connected_dream_ids'])} {t('ATLAS_DREAMS_LINKED')})"
                              f"{home}")
            except Exception:
                pass

    except Exception as e:
        show_error(str(e))

    press_enter()


def action_export():
    source = source_submenu(t("EXPORT_TITLE"), include_all=False)
    if source is None:
        return

    clear()
    print_header(t("EXPORT_TITLE"))
    print_desc(t("EXPORT_DESC"))
    print_footer()

    raw = prompt(t("EXPORT_LIMIT"))
    try:
        limit = int(raw) if raw else 100
    except ValueError:
        print(f"  {t('EXPORT_INVALID_NUM')}")
        limit = 100

    import json
    from datetime import datetime
    from lib.config import load_config
    from adapters.registry import create_adapter

    config = load_config("config.yaml")
    source_config = config.get_source_config(source)

    print(f"\n  {t('EXPORT_RUNNING')}")

    try:
        adapter = create_adapter(source_config)
        dreams = []
        for i, dream in enumerate(adapter.fetch_all()):
            if i >= limit:
                break
            dreams.append(dream.to_dict())

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{source}_{ts}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(dreams, f, ensure_ascii=False, indent=2)

        show_ok(f"{t('EXPORT_DONE')} {filename}")
    except Exception as e:
        show_error(str(e))

    press_enter()


def action_language():
    clear()
    print_header(t("LANGUAGE_TITLE"))
    print_desc(t("LANGUAGE_DESC"))

    langs = available()
    current = current_code()

    items = []
    for code, name in langs:
        marker = " ◄" if code == current else ""
        items.append((code, f"{name}{marker}", ""))

    print_menu(items, extra_items=[("b", t("BACK"))])
    choice = get_choice(items, extra_keys=["b"])

    if choice == "b":
        return

    set_language(choice)
    show_ok(t("LANGUAGE_CHANGED"))
    press_enter()


def action_help():
    clear()
    print_header(t("HELP_TITLE"))
    print_footer()
    print(t("HELP_TEXT"))
    press_enter()


# ── Noop processor (placeholder) ─────────────────────────────────────────────

def _noop_processor(dream) -> bool:
    return dream.is_valid()


# ── Glavni meni ───────────────────────────────────────────────────────────────

def run():
    """Zaženi interaktivni meni."""
    from cli.i18n import load
    load()
    from cli.embed_actions import action_embed
    from cli.search_actions import action_search
    from cli.cluster_actions import action_cluster

    ACTIONS = {
        "status":   action_status,
        "backfill": action_backfill,
        "embed":    action_embed,
        "search":   action_search,
        "cluster":  action_cluster,
        "test":     action_test,
        "export":   action_export,
        "language": action_language,
        "help":     action_help,
    }

    while True:
        clear()
        lang = get()
        print_header()

        items = [
            ("status",   *lang.MENU_ITEMS["status"]),
            ("backfill", *lang.MENU_ITEMS["backfill"]),
            ("embed",    *lang.MENU_ITEMS_EMBED),
            ("search",   *lang.MENU_ITEMS_SEARCH),
            ("cluster",  *lang.MENU_ITEMS_CLUSTER),
            ("test",     *lang.MENU_ITEMS["test"]),
            ("export",   *lang.MENU_ITEMS["export"]),
            ("language", *lang.MENU_ITEMS["language"]),
            ("help",     *lang.MENU_ITEMS["help"]),
        ]

        print_menu(items, extra_items=[("q", lang.MENU_ITEMS["quit"][0])])

        choice = get_choice(items, extra_keys=["q", "h"])

        if choice == "q":
            clear()
            break
        elif choice == "h":
            action_help()
        elif choice in ACTIONS:
            ACTIONS[choice]()


if __name__ == "__main__":
    run()
