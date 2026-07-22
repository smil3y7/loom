# Loom — Ingested Dream Store
# lib/ingested_store.py
#
# Rešuje vrzel v /api/ingest: prej je endpoint sprejel celoten CanonicalDream
# objekt (npr. iz Loom Sync extension v "api" delivery mode), ampak ga je
# zavrgel — shranil je samo dream_id v embedding queue. Ko je embedding step
# iskal vsebino prek get_dreams(), je ta bral izključno iz adapterjev
# (SQLite/JSON datoteke na disku), zato so bile vse tako poslane sanje tiho
# izgubljene (končale so kot "skipped" v statistiki).
#
# IngestedDreamStore je dodaten vir poleg adapterjev, ne zamenjava zanje.
# get_dreams() v api/index.py sanje iz obeh virov združi (union).

import os
import sqlite3
import json
from datetime import datetime, timezone
from typing import Iterator

from lib.schema import CanonicalDream


class IngestedDreamStore:
    """
    Trajno shranjevanje sanj prejetih prek /api/ingest.

    Ločena SQLite datoteka (privzeto storage/ingested.db), skladno z
    obstoječim vzorcem — vsak Loom podsistem ima svojo db datoteko
    (state.db, embeddings.db, clusters.db).
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = self._connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingested_dreams (
                dream_id           TEXT PRIMARY KEY,
                source_app         TEXT NOT NULL,
                timestamp          TEXT NOT NULL,
                title              TEXT,
                content            TEXT NOT NULL,
                language           TEXT NOT NULL,
                parent_dream_id    TEXT,
                cycle_index        INTEGER,
                metadata_json      TEXT NOT NULL,
                source_updated_at  TEXT,
                ingested_at        TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, dream: CanonicalDream) -> None:
        """Upsert — ponovno poslana sanja (isti dream_id) prepiše prejšnjo verzijo."""
        conn = self._connect()
        d = dream.to_dict()
        conn.execute("""
            INSERT OR REPLACE INTO ingested_dreams
            (dream_id, source_app, timestamp, title, content, language,
             parent_dream_id, cycle_index, metadata_json, source_updated_at, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dream.dream_id, dream.source_app, dream.timestamp, dream.title,
            dream.content, dream.language, dream.parent_dream_id, dream.cycle_index,
            json.dumps(d["metadata"]), dream.source_updated_at,
            dream.ingested_at or datetime.now(timezone.utc).isoformat(),
        ))
        conn.commit()
        conn.close()

    def get_all(self) -> Iterator[CanonicalDream]:
        conn = self._connect()
        rows = conn.execute("SELECT * FROM ingested_dreams").fetchall()
        conn.close()
        for row in rows:
            yield CanonicalDream.from_dict({
                "dream_id": row["dream_id"],
                "source_app": row["source_app"],
                "timestamp": row["timestamp"],
                "title": row["title"],
                "content": row["content"],
                "language": row["language"],
                "parent_dream_id": row["parent_dream_id"],
                "cycle_index": row["cycle_index"],
                "metadata": json.loads(row["metadata_json"]),
                "source_updated_at": row["source_updated_at"],
                "ingested_at": row["ingested_at"],
            })

    def count(self) -> int:
        conn = self._connect()
        n = conn.execute("SELECT COUNT(*) FROM ingested_dreams").fetchone()[0]
        conn.close()
        return n

    def get(self, dream_id: str) -> "CanonicalDream | None":
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM ingested_dreams WHERE dream_id = ?", (dream_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return CanonicalDream.from_dict({
            "dream_id": row["dream_id"],
            "source_app": row["source_app"],
            "timestamp": row["timestamp"],
            "title": row["title"],
            "content": row["content"],
            "language": row["language"],
            "parent_dream_id": row["parent_dream_id"],
            "cycle_index": row["cycle_index"],
            "metadata": json.loads(row["metadata_json"]),
            "source_updated_at": row["source_updated_at"],
            "ingested_at": row["ingested_at"],
        })


def merge_dream_sources(
    adapter_dreams: dict[str, CanonicalDream],
    ingested_dreams: dict[str, CanonicalDream],
) -> dict[str, CanonicalDream]:
    """
    Združi sanje iz adapterjev (SQLite/JSON datoteke na disku) in iz
    IngestedDreamStore (prejete prek /api/ingest).

    Adapter-sourced ima prednost ob koliziji dream_id — če je sanja že
    dosegljiva prek "uradnega" izvoznega vira (Oneiro JSON export, ki ga
    bere OneiroAdapter), ta velja za avtoritativno. Ingested zapolni
    vrzel za sanje ki so bile poslane prek API-ja, a še niso pristale v
    nobeni datoteki ki jo adapter bere.

    Izločena kot samostojna, čista funkcija — testirljiva brez potrebe
    po pravi bazi ali HTTP klicu.
    """
    merged = dict(ingested_dreams)
    merged.update(adapter_dreams)  # adapter dreams overridajo ingested na koliziji
    return merged
