"""`vsm-geography`: write constituency areas and adjacency into reference.sqlite."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from vsm_py.ingest import IngestError
from vsm_py.ingest.cli import version_info
from vsm_py.ingest.fetch import ensure
from vsm_py.ingest.register import check_codes, load_register
from vsm_py.ingest.sources import load_sources

from . import GeographyError
from .build import areas_km2, check_areas, check_connected, land_edges, load_crossings, read_boundaries

BOUNDARY_SOURCE = "pcon2024_boundaries"

DDL = """
CREATE TABLE IF NOT EXISTS adjacency (
  gss_a TEXT NOT NULL REFERENCES constituency(gss_code),
  gss_b TEXT NOT NULL REFERENCES constituency(gss_code),
  kind TEXT NOT NULL CHECK (kind IN ('land', 'declared_crossing')),
  shared_m REAL,
  note TEXT,
  PRIMARY KEY (gss_a, gss_b),
  CHECK (gss_a < gss_b)
);
"""


def run(data_dir: Path, db: Path) -> int:
    sources = load_sources(data_dir / "sources.toml")
    source = next((s for s in sources if s.id == BOUNDARY_SOURCE), None)
    if source is None:
        raise GeographyError(f"source {BOUNDARY_SOURCE} not in sources.toml")
    try:
        layer = load_register(data_dir / "geographies.toml", sources)[source.layer]
        gdf = read_boundaries(ensure(source, data_dir))
        check_codes(layer, set(gdf["gss_code"]), source.id)
    except IngestError as e:
        raise GeographyError(str(e)) from e
    names = dict(zip(gdf["gss_code"], gdf["name"], strict=True))

    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        known = {r[0] for r in conn.execute("SELECT gss_code FROM constituency")}
        if set(names) != known:
            raise GeographyError(
                f"boundary codes differ from constituency table (run vsm-ingest first): "
                f"{len(set(names) - known)} extra, {len(known - set(names))} missing"
            )
        areas = areas_km2(gdf)
        edges = land_edges(gdf)
        edges += load_crossings(data_dir / "crossings.toml", names)
        check_connected(sorted(names), edges, names)
        warnings = check_areas(areas, names, data_dir / "area_reference.toml")

        with conn:
            conn.executescript(DDL)
            conn.execute("DELETE FROM adjacency")
            conn.executemany(
                "INSERT INTO adjacency VALUES (?, ?, ?, ?, ?)",
                [(e.gss_a, e.gss_b, e.kind, e.shared_m, e.note) for e in edges],
            )
            conn.executemany(
                "UPDATE constituency SET area_km2 = ? WHERE gss_code = ?", [(a, g) for g, a in areas.items()]
            )
            nulls = conn.execute("SELECT COUNT(*) FROM constituency WHERE area_km2 IS NULL").fetchone()[0]
            if nulls:
                raise GeographyError(f"{nulls} constituencies still have no area")
    finally:
        conn.close()
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    land = sum(e.kind == "land" for e in edges)
    print(f"{len(areas)} areas, {land} land edges, {len(edges) - land} declared crossings -> {db}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vsm-geography", description=__doc__)
    parser.add_argument("-V", "--version", action="store_true", help="print version JSON and exit")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("version", help="print version JSON")
    r = sub.add_parser("run", help="compute areas and adjacency")
    r.add_argument("--data-dir", type=Path, default=Path(os.environ.get("VSM_DATA_DIR", "data")))
    r.add_argument("--db", type=Path, default=None, help="default: <data-dir>/reference.sqlite")
    args = parser.parse_args(argv)
    if args.version or args.cmd == "version":
        print(json.dumps(version_info()))
        return 0
    if args.cmd != "run":
        parser.print_help()
        return 2
    try:
        return run(args.data_dir, args.db or args.data_dir / "reference.sqlite")
    except GeographyError as e:
        print(f"vsm-geography: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
