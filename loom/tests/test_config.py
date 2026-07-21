# tests/test_config.py
#
# Regresijski testi za lib/config.py in create_pipeline() v lib/embeddings.py.
#
# Pokrivajo bug ki je bil dejansko najden in popravljen: create_pipeline()
# je hardcodiral batch_size=32, delay_ms=500 ne glede na to kaj je pisalo
# v config.yaml (embedding.batch_size, embedding.delay_ms). Za lokalni
# provider je to pomenilo nepotrebno ~500ms čakanja na vsak batch, čeprav
# lokalni model rate-limitinga ne rabi.

import pytest

from lib.config import Config, DEFAULT_CONFIG
from lib.embeddings import create_pipeline


def test_config_get_nested_key_with_default():
    cfg = Config({"embedding": {"provider": "local"}})
    assert cfg.get("embedding", "provider") == "local"
    assert cfg.get("embedding", "model", default="fallback") == "fallback"
    assert cfg.get("nonexistent", "key", default=123) == 123


def test_create_pipeline_reads_batch_size_and_delay_from_config():
    """
    KLJUČNI REGRESIJSKI TEST za popravljen bug.

    Pred popravkom: batch_size in delay_ms sta bila hardcodirana v
    create_pipeline() ne glede na config — ta test bi s staro kodo padel,
    ker bi pipeline.batch_size vedno bil 32 in pipeline.delay_ms vedno 500.
    """
    cfg = Config({
        "embedding": {
            "model": "test-model",
            "provider": "local",
            "batch_size": 16,
            "delay_ms": 0,
        },
        "storage": {"path": "/tmp/loom-test-storage"},
    })

    pipeline = create_pipeline(cfg)

    assert pipeline.batch_size == 16, (
        f"batch_size={pipeline.batch_size}, pričakovano 16 iz configa "
        "(hardcoded vrednost bi bila 32)"
    )
    assert pipeline.delay_ms == 0, (
        f"delay_ms={pipeline.delay_ms}, pričakovano 0 iz configa "
        "(hardcoded vrednost bi bila 500)"
    )


def test_create_pipeline_local_provider_defaults_to_zero_delay():
    """Če delay_ms ni eksplicitno nastavljen, mora biti privzeta vrednost
    za lokalni provider 0 (rate limiting ni potreben brez zunanjega API-ja)."""
    cfg = Config({
        "embedding": {"model": "test-model", "provider": "local"},
        "storage": {"path": "/tmp/loom-test-storage"},
    })
    pipeline = create_pipeline(cfg)
    assert pipeline.delay_ms == 0


def test_create_pipeline_api_provider_defaults_to_rate_limited_delay():
    """Za huggingface_api provider mora privzeti delay ostati >0, da ne
    prekoračimo rate limita brezplačnega API-ja."""
    cfg = Config({
        "embedding": {"model": "test-model", "provider": "huggingface_api"},
        "storage": {"path": "/tmp/loom-test-storage"},
    })
    pipeline = create_pipeline(cfg)
    assert pipeline.delay_ms > 0


def test_storage_path_falls_back_to_default():
    cfg = Config({})
    assert cfg.storage_path == "./loom_storage"
