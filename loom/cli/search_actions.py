# Loom CLI — Search akcije za meni
# cli/search_actions.py

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cli.i18n import t, get
from cli.menu import (
    clear, print_header, print_footer, print_desc,
    press_enter, show_error, print_menu, get_choice, prompt,
)


def action_search():
    """Vstopni meni za iskanje."""
    clear()
    lang = get()
    is_sl = lang.LANG_CODE == "sl"

    title = "Iskanje" if is_sl else "Search"
    desc = (
        "Semantično iskanje po arhivu sanj.\n"
        "Deluje v slovenščini in angleščini — isti rezultati.\n"
        "Primer: 'staro mesto', 'letenje', 'vlak', 'chase'"
    ) if is_sl else (
        "Semantic search across your dream archive.\n"
        "Works in Slovenian and English — same results.\n"
        "Example: 'old town', 'flying', 'train', 'staro mesto'"
    )

    print_header(title)
    print_desc(desc)

    items = [
        ("search",
         "Išči po arhivu"       if is_sl else "Search archive",
         "vtipkaj besedo ali stavek" if is_sl else "type a word or phrase"),
        ("similar",
         "Podobne sanje"        if is_sl else "Find similar dreams",
         "po dream ID"          if is_sl else "by dream ID"),
        ("status",
         "Status indexa"        if is_sl else "Index status",
         "koliko sanj je indeksiranih" if is_sl else "how many dreams are indexed"),
    ]

    print_menu(items, extra_items=[("b", t("BACK"))])
    choice = get_choice(items, extra_keys=["b"])

    if choice == "b":
        return
    elif choice == "search":
        action_search_query()
    elif choice == "similar":
        action_search_similar()
    elif choice == "status":
        action_search_status()


def _load_engine():
    """Naloži search engine — bere vse adapterje in zgradi index."""
    from lib.config import load_config
    from lib.search import create_search_engine
    from adapters.registry import create_adapter

    config = load_config("config.yaml")

    print("\n  Nalagam arhiv sanj...")
    dreams_by_id = {}
    for source_name in config.enabled_sources():
        source_config = config.get_source_config(source_name)
        if not source_config:
            continue
        try:
            adapter = create_adapter(source_config)
            for dream in adapter.fetch_all():
                if dream.is_valid():
                    dreams_by_id[dream.dream_id] = dream
        except Exception as e:
            print(f"  ⚠ {source_name}: {e}")

    print(f"  Naloženih {len(dreams_by_id)} sanj")
    engine = create_search_engine(config, dreams_by_id)
    engine.build_index()
    return engine


def action_search_query():
    """Interaktivno iskanje."""
    clear()
    lang = get()
    is_sl = lang.LANG_CODE == "sl"
    print_header("Iskanje po arhivu" if is_sl else "Search archive")
    print_footer()

    try:
        engine = _load_engine()
    except Exception as e:
        show_error(str(e))
        press_enter()
        return

    status = engine.status()
    if status["indexed"] == 0:
        print(f"\n  ⚠ {'Ni indeksiranih sanj. Najprej poženi Embedinge.' if is_sl else 'No indexed dreams. Run Embeddings first.'}")
        press_enter()
        return

    print(f"\n  Indeksiranih: {status['indexed']} sanj")
    print(f"  {'Vtipkaj besedo ali stavek, prazna vrstica = izhod' if is_sl else 'Type a word or phrase, empty line = exit'}\n")

    while True:
        try:
            query = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query:
            break

        results = engine.search(query, limit=8)

        if not results:
            print(f"  {'Ni rezultatov.' if is_sl else 'No results.'}\n")
            continue

        print(f"\n  {'Rezultati za' if is_sl else 'Results for'}: '{query}'\n")
        for i, r in enumerate(results, 1):
            date = r.timestamp[:10]
            title_str = r.title or ("(brez naslova)" if is_sl else "(no title)")
            src = r.source_app.replace("browser_atlas", "browser")
            print(f"  {i}. [{r.similarity:.0%}] {date} · {src} · {r.language}")
            print(f"     {title_str}")
            print(f"     {r.excerpt}\n")

    press_enter()


def action_search_similar():
    """Najdi podobne sanje po dream_id."""
    clear()
    lang = get()
    is_sl = lang.LANG_CODE == "sl"
    print_header("Podobne sanje" if is_sl else "Similar dreams")
    print_footer()

    dream_id = prompt("Vnesi dream_id" if is_sl else "Enter dream_id")
    if not dream_id:
        return

    try:
        engine = _load_engine()
        results = engine.find_similar(dream_id, limit=8)

        if not results:
            print(f"\n  {'Ni podobnih sanj ali dream_id ni znan.' if is_sl else 'No similar dreams or unknown dream_id.'}")
        else:
            print(f"\n  {'Podobne sanje za' if is_sl else 'Similar dreams for'}: {dream_id[:24]}...\n")
            for i, r in enumerate(results, 1):
                date = r.timestamp[:10]
                title_str = r.title or ("(brez naslova)" if is_sl else "(no title)")
                src = r.source_app.replace("browser_atlas", "browser")
                print(f"  {i}. [{r.similarity:.0%}] {date} · {src} · {r.language}")
                print(f"     {title_str}")
                print(f"     {r.excerpt}\n")

    except Exception as e:
        show_error(str(e))

    press_enter()


def action_search_status():
    """Status search indexa."""
    clear()
    lang = get()
    is_sl = lang.LANG_CODE == "sl"
    print_header("Status indexa" if is_sl else "Index status")
    print_footer()

    try:
        engine = _load_engine()
        s = engine.status()
        print(f"\n  {'Indeksirano':22s} {s['indexed']}")
        print(f"  {'Z embedingom':22s} {s['total_embedded']}")
        print(f"  {'Skupaj sanj':22s} {s['total_dreams']}")

        if s["indexed"] == 0:
            print(f"\n  ⚠ {'Najprej poženi Embedinge.' if is_sl else 'Run Embeddings first.'}")
        elif s["indexed"] < s["total_dreams"]:
            diff = s["total_dreams"] - s["indexed"]
            print(f"\n  ⚠ {diff} {'sanj brez embedinga.' if is_sl else 'dreams missing embeddings.'}")
        else:
            print(f"\n  ✓ {'Vse sanje so indeksirane.' if is_sl else 'All dreams are indexed.'}")

    except Exception as e:
        show_error(str(e))

    press_enter()
