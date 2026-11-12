"""Canonical content digest of reference.sqlite, for reproducibility checks (`just verify`).

SQLite files are not byte-for-byte reproducible (page layout, free lists), so two builds are
compared by content: every table in name order, every row sorted, as canonical JSON. Columns
that record *when* a build ran, not what it holds, are left out (VOLATILE).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

# table -> columns excluded from the digest
VOLATILE: dict[str, set[str]] = {"source": {"retrieved"}}


def _cell(v: object) -> object:
    if isinstance(v, bytes):
        return {"hex": v.hex()}
    if isinstance(v, float):
        return {"float": v.hex()}
    return v


def digest(db: Path) -> str:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        h = hashlib.sha256()
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for t in tables:
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{t}")')]
            keep = [c for c in cols if c not in VOLATILE.get(t, set())]
            rows = [
                json.dumps([_cell(v) for v in row], ensure_ascii=False, separators=(",", ":"))
                for row in conn.execute("SELECT " + ", ".join(f'"{c}"' for c in keep) + f' FROM "{t}"')
            ]
            rows.sort()
            h.update(json.dumps({"table": t, "columns": keep}, separators=(",", ":")).encode())
            h.update(b"\n")
            for r in rows:
                h.update(r.encode())
                h.update(b"\n")
        return h.hexdigest()
    finally:
        conn.close()
