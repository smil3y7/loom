"""
Loom
Adapter Registry — CCP v0.1

Central registry for all source app adapters.
Engine uses this to instantiate adapters from config without
knowing anything about source-specific details.

Adding a new adapter:
  1. Create adapters/your_app.py extending BaseAdapter
  2. Register it here in ADAPTER_REGISTRY
  3. Add config entry in config.yaml
  That's it. No changes to engine core.
"""

from typing import Optional
from adapters.base import BaseAdapter
from adapters.browser_atlas import BrowserAtlasAdapter
from adapters.lab import LucidLabAdapter
from adapters.oneiro import OneiroAdapter


# Registry maps config "type" strings to adapter classes
ADAPTER_REGISTRY: dict[str, type] = {
    "browser_atlas": BrowserAtlasAdapter,
    "lab": LucidLabAdapter,
    "oneiro": OneiroAdapter,
}


def create_adapter(source_config: dict) -> BaseAdapter:
    """
    Instantiate an adapter from a config source block.

    Config block format:
      type: "browser_atlas" | "lab" | "oneiro"
      path: "/path/to/db"          # for sqlite adapters
      export_path: "/path/to/dir"  # for oneiro
      ... (adapter-specific options)

    Raises:
      ValueError if adapter type is unknown.
    """
    adapter_type = source_config.get("type")
    if not adapter_type:
        raise ValueError("Source config missing 'type' field")

    adapter_class = ADAPTER_REGISTRY.get(adapter_type)
    if not adapter_class:
        available = ", ".join(ADAPTER_REGISTRY.keys())
        raise ValueError(
            f"Unknown adapter type: '{adapter_type}'. "
            f"Available: {available}"
        )

    # Build kwargs from config, excluding 'type' and 'app_ids'
    kwargs = {k: v for k, v in source_config.items()
              if k not in ("type", "app_ids", "pattern", "enabled")}

    # Handle path-based adapters
    if adapter_type in ("browser_atlas", "lab"):
        db_path = source_config.get("path") or source_config.get("db_path")
        if not db_path:
            raise ValueError(f"Adapter '{adapter_type}' requires 'path' config")
        if adapter_type == "lab":
            preferred_language = source_config.get("preferred_language", "sl")
            return adapter_class(db_path=db_path, preferred_language=preferred_language)
        return adapter_class(db_path=db_path)

    # Handle export-based adapters
    if adapter_type == "oneiro":
        export_path = source_config.get("export_path") or source_config.get("path")
        if not export_path:
            raise ValueError("Oneiro adapter requires 'export_path' config")
        return adapter_class(export_path=export_path)

    # Generic instantiation for future adapters
    return adapter_class(**kwargs)


def list_registered_adapters() -> list[str]:
    """Return names of all registered adapter types."""
    return list(ADAPTER_REGISTRY.keys())
