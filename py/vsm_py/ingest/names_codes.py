"""Official names and codes for a layer, from an ArcGIS FeatureServer query (f=json)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import IngestError
from .register import Layer, check_codes
from .sources import Source


def load(
    conn: sqlite3.Connection,
    source: Source,
    path: Path,
    sha256: str,
    registry,
    layer: Layer | None = None,
    layers=None,
) -> int:
    if not (layer and source.code_field and source.name_field):
        raise IngestError(f"{source.id}: needs layer, code_field and name_field")
    features = json.loads(path.read_text(encoding="utf-8")).get("features", [])
    rows = [
        (f["attributes"][source.code_field], f["attributes"][source.name_field].strip()) for f in features
    ]
    if not rows:
        raise IngestError(f"{source.id}: no features")
    if len({g for g, _ in rows}) != len(rows):
        raise IngestError(f"{source.id}: duplicate codes")
    check_codes(layer, {g for g, _ in rows}, source.id)
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO source VALUES (?, ?, ?, ?, datetime('now'), ?)",
            (source.id, source.url, source.licence, sha256, int(source.redistributable)),
        )
        conn.execute("DELETE FROM area WHERE layer_id = ?", (layer.id,))
        conn.executemany("INSERT INTO area VALUES (?, ?, ?)", [(layer.id, g, n) for g, n in rows])
    return len(rows)
