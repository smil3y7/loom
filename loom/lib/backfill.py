"""
Loom
Backfill Processor — CCP v0.1

Handles retroactive processing of existing dream archives.
Designed for archives with 8000+ records and 20+ year spans.

Key properties:
  - Resumable: tracks progress, skips already-processed dreams
  - Batched: processes in configurable batch sizes (default 50)
  - Throttled: delay between batches to avoid overloading API
  - Idempotent: safe to run multiple times
  - Source-agnostic: works with any adapter

Progress is tracked in a simple SQLite file (loom_state.db).
"""

import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Callable

from adapters.base import BaseAdapter
from lib.schema import CanonicalDream


@dataclass
class BackfillProgress:
    source_app: str
    total: int
    processed: int
    skipped: int        # already had embeddings
    failed: int
    started_at: str
    last_processed_at: Optional[str]

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.processed - self.skipped)

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.processed + self.skipped) / self.total * 100, 1)

    def summary(self) -> str:
        return (
            f"[{self.source_app}] "
            f"{self.processed + self.skipped}/{self.total} "
            f"({self.percent}%) — "
            f"new: {self.processed}, skipped: {self.skipped}, failed: {self.failed}"
        )


class BackfillProcessor:
    """
    Manages resumable backfill for a single source adapter.

    Usage:
        processor = BackfillProcessor(
            adapter=browser_atlas_adapter,
            state_db_path="./loom_storage/state.db",
            on_dream=engine.process_dream,   # callback
        )
        processor.run(batch_size=50, delay_ms=100)
    """

    def __init__(
        self,
        adapter: BaseAdapter,
        state_db_path: str,
        on_dream: Optional[Callable[[CanonicalDream], bool]] = None,
        on_progress: Optional[Callable[[BackfillProgress], None]] = None,
    ):
        """
        Args:
            adapter: Source adapter (read-only)
            state_db_path: Path to state tracking database
            on_dream: Callback called for each dream to process.
                      Should return True on success, False on failure.
                      If None, dreams are yielded for external processing.
            on_progress: Optional callback for progress updates
        """
        self.adapter = adapter
        self.state_db_path = state_db_path
        self.on_dream = on_dream
        self.on_progress = on_progress
        self._state_conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # State DB (tracks what's been processed)
    # ------------------------------------------------------------------

    def _get_state_conn(self) -> sqlite3.Connection:
        if self._state_conn is None:
            self._state_conn = sqlite3.connect(self.state_db_path)
            self._state_conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_dreams (
                    dream_id TEXT PRIMARY KEY,
                    source_app TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    status TEXT DEFAULT 'ok'   -- 'ok' | 'failed' | 'skipped'
                )
            """)
            self._state_conn.execute("""
                CREATE TABLE IF NOT EXISTS backfill_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_app TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    total INTEGER,
                    processed INTEGER DEFAULT 0,
                    skipped INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'  -- 'running' | 'completed' | 'interrupted'
                )
            """)
            self._state_conn.commit()
        return self._state_conn

    def is_processed(self, dream_id: str) -> bool:
        """Check if dream already has a successful processing record."""
        conn = self._get_state_conn()
        row = conn.execute(
            "SELECT status FROM processed_dreams WHERE dream_id = ?",
            (dream_id,)
        ).fetchone()
        return row is not None and row[0] == "ok"

    def mark_processed(self, dream_id: str, source_app: str, status: str = "ok"):
        conn = self._get_state_conn()
        conn.execute("""
            INSERT OR REPLACE INTO processed_dreams (dream_id, source_app, processed_at, status)
            VALUES (?, ?, ?, ?)
        """, (dream_id, source_app, datetime.now(timezone.utc).isoformat(), status))
        conn.commit()

    def get_processed_count(self, source_app: str) -> int:
        conn = self._get_state_conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM processed_dreams WHERE source_app = ? AND status = 'ok'",
            (source_app,)
        ).fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Backfill run
    # ------------------------------------------------------------------

    def run(self, batch_size: int = 50, delay_ms: int = 100) -> BackfillProgress:
        """
        Run backfill for the adapter's source.

        Resumes from where previous run left off.
        Safe to interrupt and re-run.

        Args:
            batch_size: Dreams to process per batch before delay
            delay_ms: Milliseconds to wait between batches

        Returns:
            BackfillProgress with final counts
        """
        source_app = self.adapter.SOURCE_APP
        started_at = datetime.now(timezone.utc).isoformat()

        print(f"\n[Backfill] Starting: {source_app}")
        print(f"[Backfill] Counting total dreams...")

        total = self.adapter.count_total()
        already_done = self.get_processed_count(source_app)

        print(f"[Backfill] Total: {total} | Already processed: {already_done}")

        if total == 0:
            print(f"[Backfill] No dreams found in {source_app}. Check adapter path.")
            return BackfillProgress(
                source_app=source_app, total=0, processed=0,
                skipped=0, failed=0, started_at=started_at,
                last_processed_at=None
            )

        # Track run in state DB
        conn = self._get_state_conn()
        run_id = conn.execute("""
            INSERT INTO backfill_runs (source_app, started_at, total, status)
            VALUES (?, ?, ?, 'running')
        """, (source_app, started_at, total)).lastrowid
        conn.commit()

        progress = BackfillProgress(
            source_app=source_app,
            total=total,
            processed=0,
            skipped=already_done,
            failed=0,
            started_at=started_at,
            last_processed_at=None,
        )

        batch_count = 0

        try:
            for dream in self.adapter.fetch_all():
                # Skip already processed
                if self.is_processed(dream.dream_id):
                    continue

                # Process dream
                success = True
                if self.on_dream:
                    try:
                        success = self.on_dream(dream)
                    except Exception as e:
                        print(f"[Backfill] Error processing {dream.dream_id}: {e}")
                        success = False

                if success:
                    self.mark_processed(dream.dream_id, source_app, "ok")
                    progress.processed += 1
                    progress.last_processed_at = datetime.now(timezone.utc).isoformat()
                else:
                    self.mark_processed(dream.dream_id, source_app, "failed")
                    progress.failed += 1

                # Batch delay
                batch_count += 1
                if batch_count >= batch_size:
                    batch_count = 0
                    if self.on_progress:
                        self.on_progress(progress)
                    print(f"\r{progress.summary()}", end="", flush=True)
                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000)

            # Final progress report
            print(f"\n[Backfill] Completed: {progress.summary()}")

            conn.execute("""
                UPDATE backfill_runs
                SET completed_at = ?, processed = ?, skipped = ?, failed = ?, status = 'completed'
                WHERE id = ?
            """, (
                datetime.now(timezone.utc).isoformat(),
                progress.processed,
                progress.skipped,
                progress.failed,
                run_id,
            ))
            conn.commit()

        except KeyboardInterrupt:
            print(f"\n[Backfill] Interrupted. Progress saved. Re-run to continue.")
            conn.execute(
                "UPDATE backfill_runs SET status = 'interrupted', processed = ?, failed = ? WHERE id = ?",
                (progress.processed, progress.failed, run_id)
            )
            conn.commit()

        if self.on_progress:
            self.on_progress(progress)

        return progress

    def reset(self, source_app: Optional[str] = None):
        """
        Clear processing state. Use to force full reprocessing.
        If source_app is None, clears all sources.
        """
        conn = self._get_state_conn()
        if source_app:
            conn.execute(
                "DELETE FROM processed_dreams WHERE source_app = ?",
                (source_app,)
            )
            print(f"[Backfill] Reset state for: {source_app}")
        else:
            conn.execute("DELETE FROM processed_dreams")
            print("[Backfill] Reset all processing state")
        conn.commit()

    def status(self, source_app: str) -> dict:
        """Return current backfill status for a source."""
        total = self.adapter.count_total()
        processed = self.get_processed_count(source_app)

        conn = self._get_state_conn()
        last_run = conn.execute("""
            SELECT started_at, completed_at, status
            FROM backfill_runs
            WHERE source_app = ?
            ORDER BY id DESC LIMIT 1
        """, (source_app,)).fetchone()

        return {
            "source_app": source_app,
            "total": total,
            "processed": processed,
            "remaining": max(0, total - processed),
            "percent": round(processed / total * 100, 1) if total > 0 else 0,
            "last_run": {
                "started_at": last_run[0],
                "completed_at": last_run[1],
                "status": last_run[2],
            } if last_run else None,
        }


# ── Skupne funkcije za CLI vstopne točke ─────────────────────────────────────
#
# loom.py (argparse, cmd_status/cmd_backfill) in cli/menu.py (interaktivni
# meni, action_status/action_backfill) sta prej vsak samostojno implementirala
# isto logiko — adapter health check, backfill status branje, backfill run —
# in se razlikovala samo v tem kako izpišeta rezultat. Ti dve funkciji sta
# "čisti" (brez printanja) — klicna koda v loom.py/cli/menu.py naredi samo
# formatiranje izpisa, ki je med njima namenoma različno (plain print z i18n
# stringi vs. barvni interaktivni meni).

def get_source_status(config, source_name: str) -> dict:
    """
    Vrne health_check + backfill status za en vir, brez printanja.

    Returns:
        {"source_name": str, "health": dict, "backfill": dict | None}
        backfill je None če health['ok'] ni True (ni smiselno brati stanja
        backfilla za vir do katerega se ne da dostopati).
    """
    from adapters.registry import create_adapter

    state_db = config.get("storage", "state_db",
                           default=f"{config.storage_path}/state.db")
    source_config = config.get_source_config(source_name)
    adapter = create_adapter(source_config)
    health = adapter.health_check()

    result = {"source_name": source_name, "health": health, "backfill": None}
    if health["ok"]:
        processor = BackfillProcessor(adapter=adapter, state_db_path=state_db)
        result["backfill"] = processor.status(source_name)
    return result


def run_source_backfill(
    config,
    source_name: str,
    on_dream=None,
    reset: bool = False,
) -> BackfillProgress:
    """
    Poženi backfill za en vir, brez printanja.

    on_dream: enaka funkcija kot BackfillProcessor.run() pričakuje —
        privzeto `lambda d: d.is_valid()` (ista logika kot je bila prej
        podvojena kot _noop_processor v cli/menu.py in inline lambda v loom.py).
    """
    from adapters.registry import create_adapter

    if on_dream is None:
        on_dream = lambda d: d.is_valid()

    state_db = config.get("storage", "state_db",
                           default=f"{config.storage_path}/state.db")
    os.makedirs(os.path.dirname(state_db), exist_ok=True)

    source_config = config.get_source_config(source_name)
    adapter = create_adapter(source_config)
    processor = BackfillProcessor(
        adapter=adapter,
        state_db_path=state_db,
        on_dream=on_dream,
    )
    if reset:
        processor.reset(source_name)

    return processor.run(
        batch_size=config.backfill.get("batch_size", 50),
        delay_ms=config.backfill.get("delay_ms", 100),
    )
