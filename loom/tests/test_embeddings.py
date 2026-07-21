# tests/test_embeddings.py
#
# Regresijski testi za lib/embeddings.py — EmbeddingPipeline.process_queue().
#
# Pokrivajo bug ki je bil dejansko najden in popravljen: stats["failed"] se
# je povečal enkrat na VSAK poskus (attempt), ne enkrat na sanjo. Sanja ki
# je padla vse 3 poskuse je v statistiki štela kot 3 neuspele sanje namesto
# ene. Prav tako se je sanja, ki je padla enkrat in nato uspela na retryu,
# napačno štela med "failed" v končnem izpisu.

import os
import tempfile
from datetime import datetime, timezone

from lib.embeddings import EmbeddingStore, EmbeddingPipeline
from lib.schema import CanonicalDream


def _make_dream(dream_id: str) -> CanonicalDream:
    return CanonicalDream(
        dream_id=dream_id,
        source_app="test",
        timestamp=datetime.now(timezone.utc).isoformat(),
        content=f"Vsebina sanje {dream_id} — dovolj dolga za smiseln test.",
        language="sl",
    )


class _FlakyProvider:
    """
    Ponaredek embedding providerja ki nadzorovano pade N-krat preden uspe.
    Simulira tranzientno napako (npr. omrežni izpad, rate limit).
    """

    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.call_count = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise RuntimeError(f"Simulirana napaka (poskus {self.call_count})")
        return [[0.1, 0.2, 0.3] for _ in texts]


class _AlwaysFailsProvider:
    """Ponaredek ki vedno pade — simulira trajno pokvarjeno sanjo/vir."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("Trajna napaka")


def _make_pipeline(tmpdir: str, provider) -> EmbeddingPipeline:
    store = EmbeddingStore(os.path.join(tmpdir, "e.db"))
    pipeline = EmbeddingPipeline(store=store, provider="local", batch_size=10, delay_ms=0)
    pipeline.provider = provider  # zamenjaj z ponaredkom po konstrukciji
    return pipeline


def test_dream_that_recovers_after_retry_is_not_counted_as_failed():
    """
    KLJUČNI REGRESIJSKI TEST.

    Sanja katere batch pade enkrat, nato pa uspe na naslednjem poskusu
    znotraj istega process_queue() klica, se NE sme šteti kot 'failed'
    v končni statistiki — na koncu je bila uspešno embedana.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = _FlakyProvider(fail_times=1)  # pade 1x, nato uspe
        pipeline = _make_pipeline(tmpdir, provider)

        dream = _make_dream("dream_flaky")
        pipeline.store.enqueue(dream.dream_id, dream.source_app)

        stats = pipeline.process_queue({dream.dream_id: dream})

        assert stats["processed"] == 1
        assert stats["failed"] == 0, (
            f"stats['failed']={stats['failed']}, pričakovano 0 — sanja je "
            "na koncu uspela, ne sme šteti kot neuspela samo zato ker je "
            "prvi poskus padel."
        )


def test_permanently_failing_dream_counted_once_not_per_attempt():
    """
    KLJUČNI REGRESIJSKI TEST.

    Sanja ki pade vse 3 dovoljene poskuse se sme v končni statistiki
    pojaviti kot ENA neuspela sanja, ne tri (kar bi se zgodilo če bi
    stats['failed'] naraščal na vsak posamezen poskus).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = _AlwaysFailsProvider()
        pipeline = _make_pipeline(tmpdir, provider)

        dream = _make_dream("dream_broken")
        pipeline.store.enqueue(dream.dream_id, dream.source_app)

        stats = pipeline.process_queue({dream.dream_id: dream})

        assert stats["processed"] == 0
        assert stats["failed"] == 1, (
            f"stats['failed']={stats['failed']}, pričakovano 1 — ena trajno "
            "pokvarjena sanja se ne sme šteti trikrat (enkrat na poskus)."
        )


def test_mixed_success_and_permanent_failure():
    """En dream uspe takoj, drug trajno pade — statistika mora ločiti oba
    pravilno brez medsebojnega vpliva."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EmbeddingStore(os.path.join(tmpdir, "e.db"))
        pipeline = EmbeddingPipeline(store=store, provider="local", batch_size=1, delay_ms=0)

        good_dream = _make_dream("dream_good")
        bad_dream = _make_dream("dream_bad")
        pipeline.store.enqueue(good_dream.dream_id, good_dream.source_app)
        pipeline.store.enqueue(bad_dream.dream_id, bad_dream.source_app)

        class _SelectiveProvider:
            def embed(self, texts):
                # batch_size=1, torej en text na klic — prepoznamo po vsebini
                if "dream_bad" in texts[0]:
                    raise RuntimeError("ta sanja vedno pade")
                return [[0.1, 0.2, 0.3]]

        pipeline.provider = _SelectiveProvider()

        stats = pipeline.process_queue({
            good_dream.dream_id: good_dream,
            bad_dream.dream_id: bad_dream,
        })

        assert stats["processed"] == 1
        assert stats["failed"] == 1
