"""
Loom — Semantic Continuity Layer
CLI vstopna točka

Brez argumentov:     odpre interaktivni meni
Z argumenti:         direktni ukazi (za skripte in napredne uporabnike)

Uporaba:
    python loom.py                           # interaktivni meni
    python loom.py status                    # direktno
    python loom.py backfill
    python loom.py backfill --source browser_atlas
    python loom.py backfill --reset
    python loom.py test-adapter browser_atlas
    python loom.py export browser_atlas
    python loom.py export browser_atlas --limit 50
    python loom.py lang sl                   # nastavi jezik
    python loom.py lang en
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))


# ── Direktni ukazi (neinteraktivni) ──────────────────────────────────────────

def cmd_status(config, args):
    from adapters.registry import create_adapter
    from lib.backfill import BackfillProcessor
    from cli.i18n import t, load
    load()

    print(f"\n=== {t('APP_TITLE')} — {t('STATUS_TITLE')} ===\n")

    sources = config.enabled_sources()
    if not sources:
        print(f"  {t('STATUS_NO_SOURCES')}")
        return

    state_db = config.get("storage", "state_db",
                           default=f"{config.storage_path}/state.db")

    for source_name in sources:
        source_config = config.get_source_config(source_name)
        try:
            adapter = create_adapter(source_config)
            health = adapter.health_check()
            icon = "✓" if health["ok"] else "✗"
            print(f"  [{source_name}] {icon} {health['message']}")

            if health["ok"]:
                processor = BackfillProcessor(adapter=adapter, state_db_path=state_db)
                st = processor.status(source_name)
                print(f"           {st['processed']}/{st['total']} "
                      f"({st['percent']}%) · {st['remaining']} {t('STATUS_BACKFILL_LEFT')}")
                if st["last_run"]:
                    r = st["last_run"]
                    print(f"           {t('STATUS_LAST_RUN')}: {r['started_at'][:10]} ({r['status']})")
        except Exception as e:
            print(f"  [{source_name}] ✗ {e}")
    print()


def cmd_backfill(config, args):
    from adapters.registry import create_adapter
    from lib.backfill import BackfillProcessor
    from cli.i18n import t, load
    load()

    sources = [args.source] if args.source else config.enabled_sources()
    state_db = config.get("storage", "state_db",
                           default=f"{config.storage_path}/state.db")
    os.makedirs(os.path.dirname(state_db), exist_ok=True)

    for source_name in sources:
        source_config = config.get_source_config(source_name)
        try:
            adapter = create_adapter(source_config)
            processor = BackfillProcessor(
                adapter=adapter,
                state_db_path=state_db,
                on_dream=lambda d: d.is_valid(),
            )
            if args.reset:
                processor.reset(source_name)
            processor.run(
                batch_size=config.backfill.get("batch_size", 50),
                delay_ms=config.backfill.get("delay_ms", 100),
            )
        except Exception as e:
            print(f"[{source_name}] {t('ERROR_PREFIX')}: {e}")
            raise


def cmd_test_adapter(config, args):
    from adapters.registry import create_adapter
    from adapters.browser_atlas import BrowserAtlasAdapter
    from cli.i18n import t, load
    load()

    source_name = args.source
    source_config = config.get_source_config(source_name)
    if not source_config:
        print(f"Vir '{source_name}' ni v configu.")
        sys.exit(1)

    adapter = create_adapter(source_config)
    health = adapter.health_check()
    print(f"\n{'✓' if health['ok'] else '✗'} {health['message']}\n")

    if not health["ok"]:
        sys.exit(1)

    count = 0
    for dream in adapter.fetch_all():
        if count >= 3:
            break
        print(f"  {dream.dream_id}")
        print(f"  {dream.timestamp} · {dream.language}")
        if dream.title:
            print(f"  {dream.title}")
        print(f"  {dream.content[:120].replace(chr(10), ' ')}...")
        print()
        count += 1

    if isinstance(adapter, BrowserAtlasAdapter):
        try:
            nodes = adapter.fetch_atlas_nodes()
            print(f"  Atlas nodes: {len(nodes)}")
        except Exception:
            pass


def cmd_export(config, args):
    from adapters.registry import create_adapter
    from cli.i18n import t, load
    load()

    source_name = args.source
    source_config = config.get_source_config(source_name)
    if not source_config:
        print(f"Vir '{source_name}' ni v configu.")
        sys.exit(1)

    adapter = create_adapter(source_config)
    limit = getattr(args, "limit", 100)
    dreams = []
    for i, dream in enumerate(adapter.fetch_all()):
        if i >= limit:
            break
        dreams.append(dream.to_dict())

    filename = f"export_{source_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(dreams, f, ensure_ascii=False, indent=2)
    print(f"Izvoženo v {filename} ({len(dreams)} sanj)")


def cmd_lang(config, args):
    from cli.i18n import set_language, available
    langs = dict(available())
    if args.code not in langs:
        print(f"Neznani jezik: {args.code}. Razpoložljivi: {', '.join(langs.keys())}")
        sys.exit(1)
    set_language(args.code)
    print(f"Jezik nastavljen na: {langs[args.code]}")


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description="Loom — Semantic Continuity Layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Brez argumentov se odpre interaktivni meni."
    )
    parser.add_argument("--config", default="config.yaml")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status")

    bp = sub.add_parser("backfill")
    bp.add_argument("--source")
    bp.add_argument("--reset", action="store_true")

    tp = sub.add_parser("test-adapter")
    tp.add_argument("source")

    ep = sub.add_parser("export")
    ep.add_argument("source")
    ep.add_argument("--limit", type=int, default=100)

    sp = sub.add_parser("search")
    sp.add_argument("query", help="Iskalni niz")
    sp.add_argument("--top-k", type=int, default=10)
    sp.add_argument("--lang", choices=["sl", "en"], default=None)

    lp = sub.add_parser("lang")
    lp.add_argument("code", help="Koda jezika: sl, en, ...")

    return parser


# ── Vstopna točka ─────────────────────────────────────────────────────────────


def cmd_search(config, args):
    from lib.search import create_search_engine
    from lib.embeddings import EmbeddingStore
    from adapters.registry import create_adapter
    import os

    print('[Search] Nalagam arhiv sanj...')
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
            print(f'  [{source_name}] napaka: {e}')

    print(f'[Search] Naloženih {len(dreams_by_id)} sanj')

    engine = create_search_engine(config, dreams_by_id)
    count = engine.build_index()

    if count == 0:
        print('[Search] Ni indeksiranih sanj. Najprej poženi backfill in embedinge.')
        return

    if hasattr(args, 'query') and args.query:
        # Direktno iskanje z argumentom
        results = engine.search(args.query, limit=getattr(args, 'limit', 10))
        if not results:
            print('Ni rezultatov.')
            return
        print(f"\nRezultati za: '{args.query}'\n")
        for i, r in enumerate(results, 1):
            date = r.timestamp[:10]
            title = r.title or '(brez naslova)'
            src = r.source_app.replace('browser_atlas', 'browser')
            print(f'  {i}. [{r.similarity:.0%}] {date} · {src} · {r.language}')
            print(f'     {title}')
            print(f'     {r.excerpt}')
            print()
    else:
        # Interaktivni način
        from lib.search import run_search_cli
        run_search_cli(engine)

def main():
    parser = build_parser()
    args = parser.parse_args()

    # Brez argumentov → interaktivni meni
    if not args.command:
        from cli.menu import run
        run()
        return

    from lib.config import load_config
    config = load_config(args.config)

    commands = {
        "status":       cmd_status,
        "backfill":     cmd_backfill,
        "test-adapter": cmd_test_adapter,
        "export":       cmd_export,
        "search":       cmd_search,
        "lang":         cmd_lang,
    }
    commands[args.command](config, args)


if __name__ == "__main__":
    main()
