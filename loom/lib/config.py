"""
Loom
Config Loader — CCP v0.1

Loads and validates loom/config.yaml.
Resolves glob patterns for database paths (e.g. dream_atlas_*.sqlite).
"""

import glob
import os
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None


DEFAULT_CONFIG = {
    "engine": {
        "host": "localhost",
        "port": 8000,
        "log_level": "info",
    },
    "backfill": {
        "batch_size": 50,        # dreams per batch
        "delay_ms": 100,         # ms between batches (rate limiting)
        "resume": True,          # skip already-processed dreams
    },
    "embedding": {
        "model": "paraphrase-multilingual-MiniLM-L12-v2",
        "provider": "huggingface_api",   # "huggingface_api" | "local"
    },
    "storage": {
        "path": "./loom_storage",
    },
    "sources": {},
}


class Config:
    def __init__(self, data: dict):
        self._data = data

    def get(self, *keys, default=None):
        """Nested key access: config.get("engine", "port", default=8000)"""
        d = self._data
        for key in keys:
            if not isinstance(d, dict) or key not in d:
                return default
            d = d[key]
        return d

    @property
    def sources(self) -> dict:
        return self._data.get("sources", {})

    @property
    def engine(self) -> dict:
        return self._data.get("engine", DEFAULT_CONFIG["engine"])

    @property
    def backfill(self) -> dict:
        return {**DEFAULT_CONFIG["backfill"], **self._data.get("backfill", {})}

    @property
    def storage_path(self) -> str:
        return self._data.get("storage", {}).get("path", "./loom_storage")

    def resolve_source_path(self, source_name: str) -> Optional[str]:
        """
        Resolve the database path for a source, handling glob patterns.

        For sources with a 'pattern' field (e.g. dream_atlas_*.sqlite):
        - Lists all matching files in 'path' directory
        - Returns the most recently modified one

        For sources with a direct 'path' file:
        - Returns path as-is if file exists

        Returns None if no file found.
        """
        source_config = self.sources.get(source_name, {})
        base_path = source_config.get("path", "")
        pattern = source_config.get("pattern")

        if not base_path:
            return None

        if pattern:
            # Glob search in directory
            search = os.path.join(base_path, pattern)
            matches = glob.glob(search)
            if not matches:
                return None
            # Return most recently modified
            return max(matches, key=os.path.getmtime)

        # Direct file path
        if os.path.isfile(base_path):
            return base_path

        return None

    def get_source_config(self, source_name: str) -> Optional[dict]:
        """Return source config with resolved path."""
        source = self.sources.get(source_name)
        if not source:
            return None

        config = dict(source)

        # Resolve glob path if needed
        resolved = self.resolve_source_path(source_name)
        if resolved:
            config["path"] = resolved

        return config

    def enabled_sources(self) -> list[str]:
        """Return names of sources that are enabled (default: all)."""
        return [
            name for name, cfg in self.sources.items()
            if cfg.get("enabled", True)
        ]


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load config from YAML file.
    Falls back to DEFAULT_CONFIG if file not found.
    """
    path = Path(config_path)

    if not path.exists():
        print(f"[Config] No config file at {config_path}, using defaults.")
        return Config(DEFAULT_CONFIG.copy())

    if yaml is None:
        raise ImportError(
            "PyYAML not installed. Run: pip install pyyaml"
        )

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return Config(DEFAULT_CONFIG.copy())

    # Merge with defaults
    merged = {**DEFAULT_CONFIG, **data}
    for key in ("engine", "backfill", "embedding", "storage"):
        if key in DEFAULT_CONFIG and key in data:
            merged[key] = {**DEFAULT_CONFIG[key], **data.get(key, {})}

    return Config(merged)
