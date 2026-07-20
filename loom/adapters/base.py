"""
Loom
Base Adapter Interface — CCP v0.1

All source app adapters extend this base class.
Adapters are thin: they map, transport, synchronize.
They never generate embeddings, perform clustering, or own continuity logic.
"""

from abc import ABC, abstractmethod
from typing import Iterator, Optional
from lib.schema import CanonicalDream


class BaseAdapter(ABC):
    """
    Abstract base for all source app adapters.

    Design rules:
    - Adapters are read-only from source (never write to source DB)
    - Adapters map source schema → CanonicalDream
    - Adapters are stateless between calls
    - Adapters must handle missing/null fields gracefully
    - Adapters must be resumable (backfill can be interrupted and restarted)
    """

    SOURCE_APP: str = ""    # override in subclass: "browser_atlas" | "lab" | "oneiro"

    # ------------------------------------------------------------------
    # Core interface — must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def fetch_all(self) -> Iterator[CanonicalDream]:
        """
        Yield all dreams from source.
        Used for initial backfill of existing archives.
        Must be resumable: engine tracks which dream_ids are already processed.
        Must yield, not return list — archives can be 8000+ records.
        """
        pass

    @abstractmethod
    def fetch_since(self, timestamp: str) -> Iterator[CanonicalDream]:
        """
        Yield dreams created or modified after given ISO-8601 timestamp.
        Used for incremental sync after initial backfill.
        """
        pass

    @abstractmethod
    def fetch_one(self, local_id: str) -> Optional[CanonicalDream]:
        """
        Fetch single dream by source-local ID (not canonical dream_id).
        Used for on-demand enrichment requests.
        """
        pass

    @abstractmethod
    def count_total(self) -> int:
        """
        Return total dream count in source.
        Used for backfill progress tracking.
        """
        pass

    # ------------------------------------------------------------------
    # Optional interface — override when source supports it
    # ------------------------------------------------------------------

    def fetch_updated(self, since: str) -> Iterator[CanonicalDream]:
        """
        Yield dreams that were modified (not created) after timestamp.
        Default falls back to fetch_since — override if source tracks updates separately.
        """
        return self.fetch_since(since)

    def health_check(self) -> dict:
        """
        Verify adapter can reach its source.
        Returns {"ok": True/False, "message": "...", "count": n}
        """
        try:
            count = self.count_total()
            return {"ok": True, "message": f"Connected. {count} dreams available.", "count": count}
        except Exception as e:
            return {"ok": False, "message": str(e), "count": 0}

    # ------------------------------------------------------------------
    # Helpers available to all adapters
    # ------------------------------------------------------------------

    def _safe_str(self, value, fallback: str = "") -> str:
        """Safely convert any value to string, return fallback if None/empty."""
        if value is None:
            return fallback
        s = str(value).strip()
        return s if s else fallback

    def _safe_list(self, value) -> list:
        """Safely convert tags/emotions to list."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Handle comma-separated strings
            return [t.strip() for t in value.split(",") if t.strip()]
        return []

    def _safe_bool(self, value) -> Optional[bool]:
        """Safely convert SQLite INTEGER (0/1) or Python bool to Optional[bool]."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return None

    def _detect_language(self, text: str, declared: Optional[str] = None) -> str:
        """
        Return language code for a dream text.

        Priority:
          1. Declared language from source app — trusted as-is
          2. langdetect automatic detection (55+ languages)
          3. Fallback to "other" if detection fails

        langdetect works reliably for ~20+ words.
        Very short entries may return imprecise results — acceptable for dreams.
        Adding a new language requires zero code changes here.
        """
        if declared and declared in ("sl", "en", "other"):
            return declared

        if not text or not text.strip():
            return "other"

        try:
            from langdetect import detect, LangDetectException
            lang = detect(text)
            # Normalize to our supported codes
            # langdetect returns ISO 639-1 codes: "sl", "en", "de", "fr", ...
            return lang if lang else "other"
        except Exception:
            # langdetect not installed or detection failed
            # Silent fallback — never crash on language detection
            return "other"
