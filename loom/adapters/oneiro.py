"""
Loom
Oneiro Adapter — CCP v0.1

Source: JSON export from IndexedDB (DreamInterpreterDB)
App: Oneiro PWA — https://oneiro-delta.vercel.app/

IndexedDB cannot be read by external processes.
Integration path: Oneiro exports dreams as JSON → adapter reads file.

Two modes:
  1. File mode: reads a single exported JSON file
  2. Watch mode: watches a directory for new export files (incremental sync)

Export format (from Oneiro):
  Array of dream objects matching IndexedDB "dreams" store schema.
  See sampleRecord in schema documentation.

Adapter is stateless — it maps whatever JSON it receives.
De-duplication is handled by the engine (dream_id is stable UUID from Oneiro).
"""

import json
import os
from typing import Iterator, Optional
from datetime import datetime, timezone
from pathlib import Path

from adapters.base import BaseAdapter
from lib.schema import (
    CanonicalDream,
    DreamMetadata,
    make_dream_id,
)


SOURCE_APP = "oneiro"


class OneiroAdapter(BaseAdapter):

    SOURCE_APP = SOURCE_APP

    def __init__(self, export_path: str):
        """
        Args:
            export_path: Path to exported JSON file, or directory containing
                         export files (adapter uses most recent in that case).
        """
        self.export_path = Path(export_path)

    # ------------------------------------------------------------------
    # File resolution
    # ------------------------------------------------------------------

    def _resolve_file(self) -> Optional[Path]:
        """
        Return the JSON file to read.
        - If export_path is a file: use it directly
        - If export_path is a directory: use most recently modified *.json
        """
        if self.export_path.is_file():
            return self.export_path

        if self.export_path.is_dir():
            json_files = sorted(
                self.export_path.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            if json_files:
                return json_files[0]

        return None

    def _load_dreams(self) -> list[dict]:
        """Load and parse dream records from export file."""
        file_path = self._resolve_file()
        if not file_path:
            raise FileNotFoundError(
                f"No export file found at: {self.export_path}\n"
                "Export dreams from Oneiro first: Settings → Export → JSON"
            )

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle two export formats:
        # 1. Direct array: [{dream}, {dream}, ...]
        # 2. Wrapped: {"dreams": [{dream}, ...]} or {"stores": {"dreams": [...]}}
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "dreams" in data:
                dreams = data["dreams"]
                return dreams if isinstance(dreams, list) else []
            if "stores" in data and "dreams" in data["stores"]:
                # Full IndexedDB export format
                store = data["stores"]["dreams"]
                if isinstance(store, list):
                    return store
                if isinstance(store, dict) and "records" in store:
                    return store["records"]

        return []

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    def count_total(self) -> int:
        try:
            return len(self._load_dreams())
        except FileNotFoundError:
            return 0

    def fetch_all(self) -> Iterator[CanonicalDream]:
        """Yield all dreams from export file."""
        records = self._load_dreams()
        # Sort by createdAt for chronological backfill
        records.sort(key=lambda r: r.get("createdAt", ""), reverse=False)

        for record in records:
            dream = self._record_to_canonical(record)
            if dream and dream.is_valid():
                yield dream

    def fetch_since(self, timestamp: str) -> Iterator[CanonicalDream]:
        """Yield dreams created after given ISO timestamp."""
        records = self._load_dreams()
        for record in records:
            created_at = record.get("createdAt", "")
            if created_at and created_at >= timestamp:
                dream = self._record_to_canonical(record)
                if dream and dream.is_valid():
                    yield dream

    def fetch_one(self, local_id: str) -> Optional[CanonicalDream]:
        """Fetch single dream by Oneiro UUID."""
        records = self._load_dreams()
        for record in records:
            if record.get("id") == local_id:
                return self._record_to_canonical(record)
        return None

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def _record_to_canonical(self, record: dict) -> Optional[CanonicalDream]:
        """Map Oneiro IndexedDB record to CanonicalDream."""
        try:
            oneiro_id = record.get("id")
            if not oneiro_id:
                return None

            content = self._safe_str(record.get("content", ""))
            if not content:
                return None

            # Oneiro uses its own UUID as dream_id
            # We wrap it in our namespace for stability
            canonical_id = make_dream_id(SOURCE_APP, oneiro_id)

            # Timestamp: prefer createdAt, fall back to date + time
            timestamp = self._build_timestamp(
                created_at=record.get("createdAt"),
                date=record.get("date"),
                time=record.get("time"),
            )

            # Language: Oneiro declares it explicitly
            language = record.get("language")
            if language not in ("sl", "en"):
                language = self._detect_language(content, declared=language)

            # Tags: Oneiro stores as array or null
            tags = self._safe_list(record.get("tags"))

            # Emotions from emotionalTone field
            emotional_tone = record.get("emotionalTone")
            emotions = [emotional_tone] if emotional_tone else []

            metadata = DreamMetadata(
                lucid=self._safe_bool(record.get("isLucid")),
                tags=tags,
                emotions=emotions,
                emotional_tone=emotional_tone,
                is_nightmare=self._safe_bool(record.get("isNightmare")),
                is_recurring=self._safe_bool(record.get("isRecurring")),
                vividness=record.get("intensity"),   # "vivid", "faint", etc.
                extras={
                    "oneiro_id": oneiro_id,
                    "characters": self._safe_list(record.get("characters")),
                    "body_sensations": self._safe_list(record.get("bodySensations")),
                    "sleep_context": record.get("sleepContext"),
                    "schema_version": record.get("schemaVersion"),
                    "last_edited_at": record.get("lastEditedAt"),
                }
            )

            return CanonicalDream(
                dream_id=canonical_id,
                source_app=SOURCE_APP,
                timestamp=timestamp,
                title=self._safe_str(record.get("title")) or None,
                content=content,
                language=language,
                parent_dream_id=None,   # Oneiro has no night grouping
                cycle_index=None,
                metadata=metadata,
                source_updated_at=record.get("lastEditedAt"),
            )

        except Exception as e:
            print(f"[OneiroAdapter] Skipping record {record.get('id')}: {e}")
            return None

    def _build_timestamp(
        self,
        created_at: Optional[str],
        date: Optional[str],
        time: Optional[str],
    ) -> str:
        """Build ISO-8601 timestamp from Oneiro fields."""
        # Try createdAt (most precise)
        if created_at:
            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                        "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(created_at, fmt)
                    return dt.replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    continue

        # Fall back to date + time
        if date:
            for fmt in ("%Y-%m-%d",):
                try:
                    d = datetime.strptime(date, fmt).date()
                    hour, minute = 0, 0
                    if time:
                        for tfmt in ("%H:%M", "%H.%M"):
                            try:
                                t = datetime.strptime(time.strip(), tfmt)
                                hour, minute = t.hour, t.minute
                                break
                            except ValueError:
                                continue
                    dt = datetime(d.year, d.month, d.day, hour, minute,
                                  tzinfo=timezone.utc)
                    return dt.isoformat()
                except ValueError:
                    continue

        return datetime.now(timezone.utc).isoformat()
