"""
Loom
Browser + Atlas Adapter — CCP v0.1

Source: dream_atlas_*.sqlite
Shared by Dream Browser and Dream Atlas apps.

Schema notes:
  - Dreams table: one record per night (date, title, location FK)
  - SleepCycle table: one record per dream segment within that night
  - Each SleepCycle becomes one CanonicalDream (sleep cycle as unit)
  - SleepCycles are linked to their parent Dream via parent_dream_id
  - Atlas_Nodes + Atlas_NodeDreams: user-confirmed locations → imported as
    confirmed persistent structures (not re-derived by engine)

Adapter is read-only. Never writes to source database.
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


SOURCE_APP = "browser_atlas"


class BrowserAtlasAdapter(BaseAdapter, SQLiteAdapterMixin):

    SOURCE_APP = SOURCE_APP

    def __init__(self, db_path: str):
        """
        Args:
            db_path: Full path to dream_atlas_*.sqlite file.
                     Engine passes this from config at instantiation.
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # Connection management (_connect, _get_conn, close, __enter__, __exit__)
    # je podedovano iz SQLiteAdapterMixin — glej adapters/base.py.

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    def count_total(self) -> int:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as n FROM SleepCycle sc "
            "JOIN Dreams d ON sc.DreamID = d.DreamID "
            "WHERE sc.Contents IS NOT NULL AND TRIM(sc.Contents) != ''"
        ).fetchone()
        return row["n"] if row else 0

    def fetch_all(self) -> Iterator[CanonicalDream]:
        """Yield all sleep cycles as canonical dreams. Suitable for backfill."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT
                sc.SleepCycleID,
                sc.DreamID,
                sc.Contents,
                sc.Comments,
                sc.Time_,
                sc.Bookmark,
                d.Date_,
                d.DreamTitle,
                l.Location as LocationName,
                ROW_NUMBER() OVER (
                    PARTITION BY sc.DreamID
                    ORDER BY sc.SleepCycleID
                ) as cycle_index
            FROM SleepCycle sc
            JOIN Dreams d ON sc.DreamID = d.DreamID
            LEFT JOIN Location l ON d.Location = l.LocationId
            WHERE sc.Contents IS NOT NULL
              AND TRIM(sc.Contents) != ''
            ORDER BY d.Date_, sc.DreamID, sc.SleepCycleID
        """).fetchall()

        for row in rows:
            dream = self._row_to_canonical(row)
            if dream and dream.is_valid():
                yield dream

    def fetch_since(self, timestamp: str) -> Iterator[CanonicalDream]:
        """
        Yield sleep cycles for dreams on or after the given date.
        Browser/Atlas has no updated_at — uses Date_ for filtering.
        """
        # Extract date portion from ISO timestamp
        date_cutoff = timestamp[:10]  # "YYYY-MM-DD"

        conn = self._get_conn()
        rows = conn.execute("""
            SELECT
                sc.SleepCycleID,
                sc.DreamID,
                sc.Contents,
                sc.Comments,
                sc.Time_,
                sc.Bookmark,
                d.Date_,
                d.DreamTitle,
                l.Location as LocationName,
                ROW_NUMBER() OVER (
                    PARTITION BY sc.DreamID
                    ORDER BY sc.SleepCycleID
                ) as cycle_index
            FROM SleepCycle sc
            JOIN Dreams d ON sc.DreamID = d.DreamID
            LEFT JOIN Location l ON d.Location = l.LocationId
            WHERE sc.Contents IS NOT NULL
              AND TRIM(sc.Contents) != ''
              AND d.Date_ >= ?
            ORDER BY d.Date_, sc.DreamID, sc.SleepCycleID
        """, (date_cutoff,)).fetchall()

        for row in rows:
            dream = self._row_to_canonical(row)
            if dream and dream.is_valid():
                yield dream

    def fetch_one(self, local_id: str) -> Optional[CanonicalDream]:
        """Fetch single sleep cycle by SleepCycleID."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT
                sc.SleepCycleID,
                sc.DreamID,
                sc.Contents,
                sc.Comments,
                sc.Time_,
                sc.Bookmark,
                d.Date_,
                d.DreamTitle,
                l.Location as LocationName,
                1 as cycle_index
            FROM SleepCycle sc
            JOIN Dreams d ON sc.DreamID = d.DreamID
            LEFT JOIN Location l ON d.Location = l.LocationId
            WHERE sc.SleepCycleID = ?
        """, (local_id,)).fetchone()

        if not row:
            return None
        return self._row_to_canonical(row)

    # ------------------------------------------------------------------
    # Atlas-specific: import confirmed locations
    # ------------------------------------------------------------------

    def fetch_atlas_nodes(self) -> list[dict]:
        """
        Return user-confirmed Atlas locations as structured dicts.
        These are imported into the engine as already-confirmed persistent
        structures — not re-derived. This gives the engine a head start
        from years of user curation.

        Returns list of:
        {
            "node_id": int,
            "name": str,
            "type": str,
            "stability": float,
            "is_home": bool,
            "notes": str | None,
            "search_terms": list[str],
            "connected_dream_ids": list[str]   # canonical dream_ids
        }
        """
        conn = self._get_conn()

        nodes = conn.execute("""
            SELECT
                n.Id as node_id,
                n.Name as name,
                n.Type as type,
                n.Stability as stability,
                n.IsHome as is_home,
                n.Notes as notes,
                n.SearchTerms as search_terms
            FROM Atlas_Nodes n
            ORDER BY n.Stability DESC
        """).fetchall()

        result = []
        for node in nodes:
            # Fetch dream connections for this node
            dream_rows = conn.execute("""
                SELECT nd.SleepCycleId
                FROM Atlas_NodeDreams nd
                WHERE nd.NodeId = ?
            """, (node["node_id"],)).fetchall()

            connected_dream_ids = [
                make_dream_id(SOURCE_APP, f"sc:{r['SleepCycleId']}")
                for r in dream_rows
            ]

            search_terms = self._safe_list(node["search_terms"])

            result.append({
                "node_id": node["node_id"],
                "name": node["name"],
                "type": self._safe_str(node["type"], "Personal"),
                "stability": node["stability"] or 10.0,
                "is_home": self._safe_bool(node["is_home"]) or False,
                "notes": node["notes"],
                "search_terms": search_terms,
                "connected_dream_ids": connected_dream_ids,
            })

        return result

    def fetch_dream_categories(self, sleep_cycle_id: int) -> list[str]:
        """Return category display names for a sleep cycle's parent dream."""
        conn = self._get_conn()

        # Get the DreamID for this sleep cycle
        sc = conn.execute(
            "SELECT DreamID FROM SleepCycle WHERE SleepCycleID = ?",
            (sleep_cycle_id,)
        ).fetchone()
        if not sc:
            return []

        rows = conn.execute("""
            SELECT dc.DisplayName
            FROM DCDreamCategories ddc
            JOIN DreamCategories dc ON ddc.CategoryID = dc.CategoryID
            WHERE ddc.SleepCycleID = ?
        """, (sleep_cycle_id,)).fetchall()

        return [r["DisplayName"] for r in rows if r["DisplayName"]]

    def fetch_dream_signs(self, sleep_cycle_id: int) -> list[str]:
        """Return dream sign names for a sleep cycle."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT DreamSignName
            FROM DreamSign
            WHERE SleepCycleID = ?
        """, (sleep_cycle_id,)).fetchall()
        return [r["DreamSignName"] for r in rows if r["DreamSignName"]]

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def _row_to_canonical(self, row: sqlite3.Row) -> Optional[CanonicalDream]:
        """Map a joined SleepCycle+Dreams row to CanonicalDream."""
        try:
            sleep_cycle_id = row["SleepCycleID"]
            dream_id_local = row["DreamID"]

            content = self._safe_str(row["Contents"])
            if not content:
                return None

            # Append comments to content if present
            # Comments are the dreamer's waking notes — semantically relevant
            comments = self._safe_str(row["Comments"])
            if comments:
                content = f"{content}\n\n[Opombe / Notes]\n{comments}"

            # Build ISO timestamp from Date_ + Time_
            timestamp = self._build_timestamp(
                self._safe_str(row["Date_"]),
                self._safe_str(row["Time_"])
            )

            # Stable canonical IDs
            canonical_id = make_dream_id(SOURCE_APP, f"sc:{sleep_cycle_id}")
            parent_id = make_parent_id(SOURCE_APP, str(dream_id_local))

            # Language detection — no declared language in source, use heuristic
            language = self._detect_language(content)

            # Categories and dream signs as tags
            categories = self.fetch_dream_categories(sleep_cycle_id)
            signs = self.fetch_dream_signs(sleep_cycle_id)
            tags = list(set(categories + signs))

            # Location as extra metadata
            location_name = self._safe_str(row["LocationName"])

            metadata = DreamMetadata(
                lucid=None,  # Browser doesn't track lucidity per cycle
                tags=tags,
                extras={
                    "location": location_name if location_name else None,
                    "bookmark": self._safe_bool(row["Bookmark"]),
                    "sleep_cycle_id": sleep_cycle_id,
                    "dream_id": dream_id_local,
                }
            )

            return CanonicalDream(
                dream_id=canonical_id,
                source_app=SOURCE_APP,
                timestamp=timestamp,
                title=self._safe_str(row["DreamTitle"]) or None,
                content=content,
                language=language,
                parent_dream_id=parent_id,
                cycle_index=row["cycle_index"] if "cycle_index" in row.keys() else None,
                metadata=metadata,
            )

        except Exception as e:
            # Log but don't crash — bad records are skipped, not fatal.
            # sqlite3.Row nima .get() — direktno indeksiranje bi vrglo
            # KeyError če stolpec ne obstaja, zato varno prek try/except.
            try:
                sc_id = row["SleepCycleID"]
            except (KeyError, IndexError):
                sc_id = "?"
            print(f"[BrowserAtlasAdapter] Skipping record sc:{sc_id}: {e}")
            return None

    def _build_timestamp(self, date_str: str, time_str: str) -> str:
        """
        Build ISO-8601 timestamp from source date and time strings.
        Source formats vary — handle gracefully.

        Date formats seen: "YYYY-MM-DD", "DD.MM.YYYY", "M/D/YYYY"
        Time formats seen: "HH:MM", "H:MM", empty
        """
        # Normalize date
        date = None
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                date = datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                continue

        if not date:
            # Fallback: use today if date is unparseable
            date = datetime.now(timezone.utc).date()

        # Normalize time
        hour, minute = 0, 0
        if time_str:
            for fmt in ("%H:%M", "%H.%M", "%I:%M %p"):
                try:
                    t = datetime.strptime(time_str.strip(), fmt)
                    hour, minute = t.hour, t.minute
                    break
                except ValueError:
                    continue

        dt = datetime(date.year, date.month, date.day, hour, minute,
                      tzinfo=timezone.utc)
        return dt.isoformat()
