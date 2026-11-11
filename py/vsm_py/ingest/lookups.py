"""Official ONS lookups into geography_link (ADR-0014): no shares are ever guessed."""

from __future__ import annotations

import csv
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from . import IngestError
from .register import Layer, check_codes
from .sources import Source

SPLIT = {"yes", "true"}


def load_wd_pcon_lad(
    conn: sqlite3.Connection,
    source: Source,
    path: Path,
    sha256: str,
    registry,
    layer: Layer | None,
    layers: dict[str, Layer],
) -> int:
    """Ward → constituency (exact, or `partial` for split wards) and ward → local authority (exact)."""
    wd, pcon, lad = (layers.get(k) for k in ("WD20240704", "PCON2024", "LAD20240704"))
    if not (wd and pcon and lad):
        raise IngestError(f"{source.id}: needs layers WD20240704, PCON2024 and LAD20240704 registered")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise IngestError(f"{path}: no rows")

    check_codes(wd, {r["WD24CD"] for r in rows}, f"{source.id} wards")
    check_codes(pcon, {r["PCON24CD"] for r in rows}, f"{source.id} constituencies")
    check_codes(lad, {r["LAD24CD"] for r in rows}, f"{source.id} local authorities")

    to_pcon: dict[str, set[str]] = defaultdict(set)
    to_lad: dict[str, set[str]] = defaultdict(set)
    flagged: dict[str, bool] = {}
    for r in rows:
        w = r["WD24CD"]
        to_pcon[w].add(r["PCON24CD"])
        to_lad[w].add(r["LAD24CD"])
        flagged[w] = flagged.get(w, False) or r["SPLIT_WARD"].strip().lower() in SPLIT
        if r["SPLIT_WARD"].strip() and r["SPLIT_WARD"].strip().lower() not in SPLIT:
            raise IngestError(f"{source.id}: unknown SPLIT_WARD value {r['SPLIT_WARD']!r} for {w}")

    nested = sorted(w for w, ls in to_lad.items() if len(ls) > 1)
    if nested:
        raise IngestError(f"{source.id}: wards in more than one local authority: {nested[:10]}")
    unflagged = sorted(w for w in to_pcon if len(to_pcon[w]) > 1 and not flagged[w])
    if unflagged:
        raise IngestError(
            f"{source.id}: wards in several constituencies but not flagged split: {unflagged[:10]}"
        )
    # Flagged split but listed under one constituency (ONS anomaly): never claim `exact`.
    lone = sorted(w for w in to_pcon if flagged[w] and len(to_pcon[w]) == 1)
    for w in lone:
        print(
            f"warning: {source.id}: {w} flagged split but listed in one constituency; recorded as partial",
            file=sys.stderr,
        )
    known = {g for (g,) in conn.execute("SELECT gss_code FROM constituency")}
    if known and {r["PCON24CD"] for r in rows} != known:
        raise IngestError(f"{source.id}: constituency codes differ from the constituency table")

    links = []
    for w in sorted(to_pcon):
        split = len(to_pcon[w]) > 1 or flagged[w]
        for p in sorted(to_pcon[w]):
            links.append((wd.id, w, pcon.id, p, "partial" if split else "exact", None if split else 1.0, 0))
        (la,) = to_lad[w]
        links.append((wd.id, w, lad.id, la, "exact", 1.0, 0))

    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO source VALUES (?, ?, ?, ?, datetime('now'), ?)",
            (source.id, source.url, source.licence, sha256, int(source.redistributable)),
        )
        conn.execute(
            "DELETE FROM geography_link WHERE from_layer = ? AND to_layer IN (?, ?)", (wd.id, pcon.id, lad.id)
        )
        conn.executemany("INSERT INTO geography_link VALUES (?, ?, ?, ?, ?, ?, ?)", links)
    return len(to_pcon)
