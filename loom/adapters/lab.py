"""
Loom
LucidLab Adapter — CCP v0.1

Source: lucidlab.db (SQLite, Docker volume)
App: Lucid Lab — dream journal with lucid dreaming course

Schema notes:
  - dreams: one record per night (title, date, notes)
  - sleep_cycles: dream content segments (contents, comments)
  - dream_entries: lucid-specific metadata per sleep cycle
    (is_lucid, method, stability_score, vividness, trigger_type)
  - lookup_values: bilingual label system (label_sl / label_en)

Each sleep_cycle becomes one CanonicalDream.
dream_entries metadata is merged into DreamMetadata.
"""

import sqlite3
from typing import Iterator, Optional
from datetime import datetime, timezone

from adapters.base import BaseAdapter, SQLiteAdapterMixin
from lib.schema import (
    CanonicalDream,
    DreamMetadata,
    make_dream_id,
    make_parent_id,
)


SOURCE_APP = "lab"


class LucidLabAdapter(BaseAdapter, SQLiteAdapterMixin):

    SOURCE_APP = SOURCE_APP

    def __init__(self, db_path: str, preferred_language: str = "sl"):
        """
        Args:
            db_path: Path to lucidlab.db.
                     Via Docker shared volume: /loom/sources/lab/lucidlab.db
                     Via WSL2 on Windows: \\\\wsl$\\docker-desktop-data\\...
            preferred_language: "sl" or "en" — which lookup labels to use.
                                 Defaults to "sl" to match Slovenian content.
        """
        self.db_path = db_path
        self.preferred_language = preferred_language
        self._conn: Optional[sqlite3.Connection] = None
        self._lookup_cache: Optional[dict] = None

    # Connection management (_connect, _get_conn, close, __enter__, __exit__)
    # je podedovano iz SQLiteAdapterMixin — glej adapters/base.py.

    # ------------------------------------------------------------------
    # Lookup value resolution
    # ------------------------------------------------------------------

    def _load_lookups(self) -> dict:
        """
        Cache all lookup values for label resolution.
        Returns dict: {category_slug: {value: label}}
        """
        if self._lookup_cache is not None:
            return self._lookup_cache

        conn = self._get_conn()
        label_col = "label_sl" if self.preferred_language == "sl" else "label_en"

        rows = conn.execute(f"""
            SELECT lc.slug as category, lv.value, lv.{label_col} as label
            FROM lookup_values lv
            JOIN lookup_categories lc ON lv.category_id = lc.id
            WHERE lv.active = 1
        """).fetchall()

        cache = {}
        for row in rows:
            cat = row["category"]
            if cat not in cache:
                cache[cat] = {}
            cache[cat][row["value"]] = row["label"]

        self._lookup_cache = cache
        return cache

    def _resolve(self, category: str, value: Optional[str]) -> Optional[str]:
        """Resolve a lookup value to its human-readable label."""
        if not value:
            return None
        lookups = self._load_lookups()
        return lookups.get(category, {}).get(value, value)

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    def count_total(self) -> int:
        conn = self._get_conn()
        row = conn.execute("""
            SELECT COUNT(*) as n FROM sleep_cycles sc
            JOIN dreams d ON sc.dream_id = d.id
            WHERE sc.contents IS NOT NULL AND TRIM(sc.contents) != ''
        """).fetchone()
        return row["n"] if row else 0

    def fetch_all(self) -> Iterator[CanonicalDream]:
        """Yield all sleep cycles as canonical dreams."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT
                sc.id as sc_id,
                sc.dream_id as dream_id,
                sc.time as sc_time,
                sc.contents,
                sc.comments,
                sc.created_at as sc_created_at,
                d.title as dream_title,
                d.date as dream_date,
                d.notes as dream_notes,
                d.created_at as dream_created_at,
                de.is_lucid,
                de.method,
                de.stability_score,
                de.vividness,
                de.trigger_type,
                de.duration_estimate,
                ROW_NUMBER() OVER (
                    PARTITION BY sc.dream_id
                    ORDER BY sc.id
                ) as cycle_index
            FROM sleep_cycles sc
            JOIN dreams d ON sc.dream_id = d.id
            LEFT JOIN dream_entries de ON de.sleep_cycle_id = sc.id
            WHERE sc.contents IS NOT NULL
              AND TRIM(sc.contents) != ''
            ORDER BY d.date, sc.dream_id, sc.id
        """).fetchall()

        for row in rows:
            dream = self._row_to_canonical(row)
            if dream and dream.is_valid():
                yield dream

    def fetch_since(self, timestamp: str) -> Iterator[CanonicalDream]:
        """Yield sleep cycles created after given ISO timestamp."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT
                sc.id as sc_id,
                sc.dream_id as dream_id,
                sc.time as sc_time,
                sc.contents,
                sc.comments,
                sc.created_at as sc_created_at,
                d.title as dream_title,
                d.date as dream_date,
                d.notes as dream_notes,
                d.created_at as dream_created_at,
                de.is_lucid,
                de.method,
                de.stability_score,
                de.vividness,
                de.trigger_type,
                de.duration_estimate,
                ROW_NUMBER() OVER (
                    PARTITION BY sc.dream_id
                    ORDER BY sc.id
                ) as cycle_index
            FROM sleep_cycles sc
            JOIN dreams d ON sc.dream_id = d.id
            LEFT JOIN dream_entries de ON de.sleep_cycle_id = sc.id
            WHERE sc.contents IS NOT NULL
              AND TRIM(sc.contents) != ''
              AND (sc.created_at >= ? OR d.created_at >= ?)
            ORDER BY d.date, sc.dream_id, sc.id
        """, (timestamp, timestamp)).fetchall()

        for row in rows:
            dream = self._row_to_canonical(row)
            if dream and dream.is_valid():
                yield dream

    def fetch_one(self, local_id: str) -> Optional[CanonicalDream]:
        """Fetch single sleep cycle by id."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT
                sc.id as sc_id,
                sc.dream_id as dream_id,
                sc.time as sc_time,
                sc.contents,
                sc.comments,
                sc.created_at as sc_created_at,
                d.title as dream_title,
                d.date as dream_date,
                d.notes as dream_notes,
                d.created_at as dream_created_at,
                de.is_lucid,
                de.method,
                de.stability_score,
                de.vividness,
                de.trigger_type,
                de.duration_estimate,
                1 as cycle_index
            FROM sleep_cycles sc
            JOIN dreams d ON sc.dream_id = d.id
            LEFT JOIN dream_entries de ON de.sleep_cycle_id = sc.id
            WHERE sc.id = ?
        """, (local_id,)).fetchone()

        if not row:
            return None
        return self._row_to_canonical(row)

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def _row_to_canonical(self, row: sqlite3.Row) -> Optional[CanonicalDream]:
        try:
            sc_id = row["sc_id"]
            dream_id_local = row["dream_id"]

            # Build content: main content + dream-level notes + comments
            content_parts = []

            main = self._safe_str(row["contents"])
            if main:
                content_parts.append(main)

            # dream.notes is a brief dream-level summary — include if present
            dream_notes = self._safe_str(row["dream_notes"])
            if dream_notes:
                content_parts.append(f"[Opombe sanj / Dream notes]\n{dream_notes}")

            comments = self._safe_str(row["comments"])
            if comments:
                content_parts.append(f"[Komentarji / Comments]\n{comments}")

            content = "\n\n".join(content_parts)
            if not content.strip():
                return None

            # Timestamp: prefer sleep_cycle created_at, fall back to dream date
            timestamp = self._build_timestamp(
                sc_created_at=self._safe_str(row["sc_created_at"]),
                dream_date=self._safe_str(row["dream_date"]),
                sc_time=self._safe_str(row["sc_time"]),
            )

            canonical_id = make_dream_id(SOURCE_APP, f"sc:{sc_id}")
            parent_id = make_parent_id(SOURCE_APP, str(dream_id_local))

            language = self._detect_language(content)

            # Resolve lookup labels for method and trigger
            method_label = self._resolve("lucid_method", row["method"])
            trigger_label = self._resolve("trigger_type", row["trigger_type"])
            vividness_label = self._resolve("vividness", row["vividness"])

            metadata = DreamMetadata(
                lucid=self._safe_bool(row["is_lucid"]),
                vividness=vividness_label or self._safe_str(row["vividness"]) or None,
                method=method_label or self._safe_str(row["method"]) or None,
                stability_score=row["stability_score"],
                duration_estimate=row["duration_estimate"],
                extras={
                    "trigger_type": trigger_label or row["trigger_type"],
                    "sleep_cycle_id": sc_id,
                    "dream_id": dream_id_local,
                }
            )

            return CanonicalDream(
                dream_id=canonical_id,
                source_app=SOURCE_APP,
                timestamp=timestamp,
                title=self._safe_str(row["dream_title"]) or None,
                content=content,
                language=language,
                parent_dream_id=parent_id,
                cycle_index=row["cycle_index"] if "cycle_index" in row.keys() else None,
                metadata=metadata,
            )

        except Exception as e:
            # sqlite3.Row nima .get() — varno prek try/except namesto direktnega .get()
            try:
                sc_id = row["sc_id"]
            except (KeyError, IndexError):
                sc_id = "?"
            print(f"[LucidLabAdapter] Skipping record sc:{sc_id}: {e}")
            return None

    def _build_timestamp(
        self,
        sc_created_at: str,
        dream_date: str,
        sc_time: str,
    ) -> str:
        """
        Build ISO-8601 timestamp. Priority:
        1. sleep_cycle.created_at (most precise)
        2. dream.date + sleep_cycle.time
        3. dream.date alone
        """
        # Try created_at first
        if sc_created_at:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                try:
                    dt = datetime.strptime(sc_created_at, fmt)
                    return dt.replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    continue

        # Fall back to date + time
        date = None
        if dream_date:
            for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
                try:
                    date = datetime.strptime(dream_date, fmt).date()
                    break
                except ValueError:
                    continue

        if not date:
            date = datetime.now(timezone.utc).date()

        hour, minute = 0, 0
        if sc_time:
            for fmt in ("%H:%M", "%H.%M"):
                try:
                    t = datetime.strptime(sc_time.strip(), fmt)
                    hour, minute = t.hour, t.minute
                    break
                except ValueError:
                    continue

        dt = datetime(date.year, date.month, date.day, hour, minute,
                      tzinfo=timezone.utc)
        return dt.isoformat()
