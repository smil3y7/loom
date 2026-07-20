# Loom CLI — Clustering akcije za meni
# cli/cluster_actions.py

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cli.i18n import t, get
from cli.menu import (
    clear, print_header, print_footer, print_desc,
    press_enter, show_error, show_ok, confirm,
    print_menu, get_choice, prompt,
)


def action_cluster():
    """Vstopni meni za clustering."""
    clear()
    lang = get()
    is_sl = lang.LANG_CODE == "sl"

    title = "Vzorci in Threads" if is_sl else "Patterns and Threads"
    desc = (
        "Zazna ponavljajoče vzorce v tvojih sanjah.\n"
        "Clustering grupira semantično podobne sanje skupaj.\n"
        "Rezultati so predlogi — ti odločiš kaj je smiselno."
    ) if is_sl else (
        "Detect recurring patterns in your dreams.\n"
        "Clustering groups semantically similar dreams together.\n"
        "Results are suggestions — you decide what feels meaningful."
    )

    print_header(title)
    print_desc(desc)

    items = [
        ("run",     "Zaznej vzorce"      if is_sl else "Detect patterns",
                    "poženi clustering na embedingih" if is_sl else "run clustering on embeddings"),
        ("threads", "Ponavljajoči vzorci" if is_sl else "Recurring threads",
                    "poglej candidate threads" if is_sl else "view candidate threads"),
        ("clusters","Vsi grupi"          if is_sl else "All clusters",
                    "poglej vse semantične grupe" if is_sl else "view all semantic clusters"),
        ("status",  "Status"             if is_sl else "Status",
                    "statistike clusteringa" if is_sl else "clustering statistics"),
    ]

    print_menu(items, extra_items=[("b", t("BACK"))])
    choice = get_choice(items, extra_keys=["b"])

    if choice == "b":
        return
    elif choice == "run":
        action_cluster_run()
    elif choice == "threads":
        action_view_threads()
    elif choice == "clusters":
        action_view_clusters()
    elif choice == "status":
        action_cluster_status()


def _load_engine():
    """Naloži clustering engine."""
    from lib.config import load_config
    from lib.embeddings import EmbeddingStore
    from lib.clustering import create_clustering_engine

    config = load_config("config.yaml")
    db_path = os.path.join(config.storage_path, "embeddings.db")
    store = EmbeddingStore(db_path)
    engine = create_clustering_engine(config, store)
    return engine, store, config


def _load_dreams(config):
    """Naloži vse sanje iz adapterjev."""
    from adapters.registry import create_adapter
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
    return dreams_by_id


def action_cluster_run():
    """Poženi clustering."""
    clear()
    lang = get()
    is_sl = lang.LANG_CODE == "sl"
    title = "Zaznavanje vzorcev" if is_sl else "Detecting patterns"
    print_header(title)
    print_footer()

    try:
        engine, store, config = _load_engine()

        # Preveri ali ima dovolj embedingov
        n_embedded = store.count()
        if n_embedded < 10:
            msg = (f"Premalo embedingov ({n_embedded}). Najprej poženi Embedinge."
                   if is_sl else
                   f"Too few embeddings ({n_embedded}). Run Embeddings first.")
            print(f"\n  ⚠ {msg}")
            press_enter()
            return

        print(f"\n  Embedingov: {n_embedded}")
        msg = "Nalagam sanje za metadata..." if is_sl else "Loading dreams for metadata..."
        print(f"  {msg}")
        dreams_by_id = _load_dreams(config)

        steps = [""] * 5
        def on_progress(step, total, message):
            print(f"\r  [{step}/{total}] {message}          ", end="", flush=True)

        print()
        result = engine.run(
            dreams_by_id=dreams_by_id,
            on_progress=on_progress,
        )
        print()

        show_ok(
            f"{'Končano' if is_sl else 'Done'}: "
            f"{result['clusters']} {'grupi' if is_sl else 'clusters'}, "
            f"{result['threads']} {'vzorci' if is_sl else 'threads'}, "
            f"{result['noise']} {'izoliranih' if is_sl else 'isolated'}"
        )

    except Exception as e:
        show_error(str(e))

    press_enter()


def action_view_threads():
    """Prikaži candidate threads."""
    clear()
    lang = get()
    is_sl = lang.LANG_CODE == "sl"
    title = "Ponavljajoči vzorci" if is_sl else "Recurring threads"
    print_header(title)
    print_footer()

    try:
        engine, _, _ = _load_engine()
        threads = engine.get_threads()

        if not threads:
            msg = ("Ni zaznanih vzorcev. Najprej poženi Zaznavanje vzorcev."
                   if is_sl else
                   "No patterns detected yet. Run pattern detection first.")
            print(f"\n  {msg}")
            press_enter()
            return

        print(f"\n  {'Vzorcev' if is_sl else 'Patterns'}: {len(threads)}\n")
        print(f"  {'─'*52}")

        # Naloži dreams za prikaz naslovov
        from lib.config import load_config
        from adapters.registry import create_adapter
        config = load_config("config.yaml")
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
            except Exception:
                pass

        for i, thread in enumerate(threads, 1):
            score = f"{thread.recurrence_score:.0%}"
            status = ""
            if thread.confirmed:
                status = " ✓"
            elif thread.rejected:
                status = " ✗"

            print(f"\n  {i}. {thread.name}{status}")
            print(f"     {thread.description}")
            print(f"     {'Rezultat' if is_sl else 'Score'}: {score} · "
                  f"{len(thread.dream_ids)} {'sanj' if is_sl else 'dreams'} · "
                  f"{thread.first_seen or '?'} → {thread.last_seen or '?'}")

            if thread.emotional_signature:
                top_emotions = sorted(
                    thread.emotional_signature.items(),
                    key=lambda x: x[1], reverse=True
                )[:3]
                emotions_str = ", ".join(f"{e} ({v:.0%})" for e, v in top_emotions)
                print(f"     {'Čustva' if is_sl else 'Emotions'}: {emotions_str}")

            # Prikaži naslove prvih 5 sanj v vzorcu
            sample_ids = thread.dream_ids[:5]
            sample_titles = []
            for did in sample_ids:
                dream = dreams_by_id.get(did)
                if dream and dream.title:
                    date = dream.timestamp[:10]
                    sample_titles.append(f"{date} — {dream.title}")
                elif dream:
                    date = dream.timestamp[:10]
                    excerpt = dream.content[:50].replace("\n", " ")
                    sample_titles.append(f"{date} — {excerpt}...")
            if sample_titles:
                label = "Vzorčne sanje" if is_sl else "Sample dreams"
                print(f"     {label}:")
                for t_str in sample_titles:
                    print(f"       · {t_str}")

        print(f"\n  {'─'*52}")

        # Akcije
        action_prompt = ("Vnesi številko za potrditev/zavrnitev, ali Enter za nazaj"
                        if is_sl else
                        "Enter number to confirm/reject, or Enter to go back")
        choice = prompt(action_prompt)

        if choice and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(threads):
                _thread_action(engine, threads[idx], is_sl)

    except Exception as e:
        show_error(str(e))

    press_enter()


def _thread_action(engine, thread, is_sl):
    """Potrdi ali zavrni thread."""
    print(f"\n  {thread.name}")
    print(f"  {thread.description}\n")

    items = [
        ("confirm", "Potrdi vzorec" if is_sl else "Confirm pattern", ""),
        ("reject",  "Zavrni"        if is_sl else "Reject", ""),
        ("skip",    "Preskoči"      if is_sl else "Skip", ""),
    ]
    print_menu(items)
    choice = get_choice(items)

    if choice == "confirm":
        new_name = prompt(
            f"Ime vzorca (Enter = '{thread.name}')"
            if is_sl else
            f"Pattern name (Enter = '{thread.name}')"
        )
        name = new_name if new_name else thread.name
        engine.confirm_thread(thread.thread_id, name)
        show_ok(f"{'Vzorec potrjen' if is_sl else 'Pattern confirmed'}: {name}")

    elif choice == "reject":
        engine.reject_thread(thread.thread_id)
        show_ok("Zavrnjen." if is_sl else "Rejected.")


def action_view_clusters():
    """Prikaži vse cluster grupe."""
    clear()
    lang = get()
    is_sl = lang.LANG_CODE == "sl"
    title = "Semantični grupi" if is_sl else "Semantic clusters"
    print_header(title)
    print_footer()

    try:
        engine, _, _ = _load_engine()
        clusters = engine.get_clusters(min_size=2)

        if not clusters:
            msg = ("Ni grupi. Najprej poženi Zaznavanje vzorcev."
                   if is_sl else
                   "No clusters yet. Run pattern detection first.")
            print(f"\n  {msg}")
            press_enter()
            return

        print(f"\n  {'Grupov' if is_sl else 'Clusters'}: {len(clusters)}\n")
        print(f"  {'─'*52}")

        for cluster in clusters[:20]:  # max 20 za prikaz
            status = " ✓" if cluster.confirmed else ""
            ctype = cluster.candidate_type
            conf = f"{cluster.confidence:.0%}"
            span = f"{cluster.span_days}d" if cluster.span_days else "?"

            print(f"\n  {cluster.label}{status}")
            print(f"     {len(cluster.dream_ids)} {'sanj' if is_sl else 'dreams'} · "
                  f"koherentnost {cluster.coherence:.2f} · "
                  f"razpon {span}")
            print(f"     {'Tip' if is_sl else 'Type'}: {ctype} ({conf}) · "
                  f"{cluster.first_seen or '?'} → {cluster.last_seen or '?'}")

        if len(clusters) > 20:
            print(f"\n  ... in še {len(clusters) - 20} grupi")

    except Exception as e:
        show_error(str(e))

    press_enter()


def action_cluster_status():
    """Status clusteringa."""
    clear()
    lang = get()
    is_sl = lang.LANG_CODE == "sl"
    title = "Status vzorcev" if is_sl else "Pattern status"
    print_header(title)
    print_footer()

    try:
        engine, store, _ = _load_engine()
        status = engine.status()
        n_embedded = store.count()

        print(f"\n  {'Embedingov':25s} {n_embedded}")
        print(f"  {'Grupi':25s} {status['clusters']}")
        print(f"  {'Potrjeni grupi':25s} {status['confirmed_clusters']}")
        print(f"  {'Candidate threads':25s} {status['threads']}")

        if status["last_run"]:
            run = status["last_run"]
            print(f"\n  {'Zadnji clustering':25s} {(run.get('completed_at') or run.get('started_at') or '')[:10]}")
            print(f"  {'Status':25s} {run.get('status', '?')}")

        if n_embedded == 0:
            print(f"\n  ⚠ {'Najprej poženi Embedinge.' if is_sl else 'Run Embeddings first.'}")
        elif status["clusters"] == 0:
            print(f"\n  ⚠ {'Najprej poženi Zaznavanje vzorcev.' if is_sl else 'Run pattern detection first.'}")

    except Exception as e:
        show_error(str(e))

    press_enter()
