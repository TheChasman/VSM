"""`vsm-ingest`: fetch, verify and load every source in data/sources.toml."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from vsm_py import __version__

from . import IngestError, commons, council, holyrood, lookups, names_codes, senedd
from .fetch import ensure, sha256_file
from .parties import Registry
from .register import load_register, write_register
from .schema import connect
from .sources import load_sources


def record_only(conn, source, path, sha256, registry, layer=None, layers=None) -> int:
    """Fetch and verify only; the file is read by a later stage (e.g. geography)."""
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO source VALUES (?, ?, ?, ?, datetime('now'), ?)",
            (source.id, source.url, source.licence, sha256, int(source.redistributable)),
        )
    return 0


LOADERS = {
    "commons_candidacies": commons.load,
    "boundaries": record_only,
    "ons_wd_pcon_lad_lookup": lookups.load_wd_pcon_lad,
    "arcgis_names_codes": names_codes.load,
    "senedd_briefing_pdf": senedd.load,
    "ons_spc_spr_lookup": holyrood.load_spc_spr_lookup,
    "holyrood_emb_xlsx": holyrood.load_emb_workbook,
    "ons_wd_lad_2022_xlsx": council.load_wd_lad_lookup,
    "lg2022_emb_xlsx": council.load_emb_workbook,
    "lg2022_ballot_zip": council.load_ballot_zip,
    "lg2022_stage_pdf": council.load_stage_pdf,
}


def version_info() -> dict[str, str]:
    try:
        commit = (
            subprocess.run(
                ["git", "rev-parse", "--short=7", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=Path(__file__).resolve().parent,
            ).stdout.strip()
            or "unknown"
        )
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    env = os.environ.get("VSM_ENV", "").strip() or "unknown"
    return {"version": __version__, "environment": env, "commit": commit}


def run(data_dir: Path, db: Path, only: set[str] | None) -> int:
    sources = load_sources(data_dir / "sources.toml")
    registry = Registry.load(data_dir / "parties.toml")
    unknown = (only or set()) - {s.id for s in sources}
    if unknown:
        raise IngestError(f"unknown source ids: {sorted(unknown)}")
    layers = load_register(data_dir / "geographies.toml", sources)
    conn = connect(db)
    try:
        write_register(conn, layers)
        for s in sources:
            if only and s.id not in only:
                continue
            path = ensure(s, data_dir)
            n = LOADERS[s.loader](
                conn, s, path, sha256_file(path), registry, layers.get(s.layer or ""), layers
            )
            unit = {
                "commons_candidacies": "contests",
                "ons_wd_pcon_lad_lookup": "wards",
                "arcgis_names_codes": "areas",
                "senedd_briefing_pdf": "contests",
                "ons_spc_spr_lookup": "constituencies",
                "holyrood_emb_xlsx": "contests",
                "ons_wd_lad_2022_xlsx": "wards",
                "lg2022_emb_xlsx": "wards",
                "lg2022_ballot_zip": "wards with ballots",
                "lg2022_stage_pdf": "stages",
            }.get(s.loader)
            print(f"{s.id}: {n} {unit} -> {db}" if unit else f"{s.id}: verified {path}")
    finally:
        conn.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vsm-ingest", description=__doc__)
    parser.add_argument("-V", "--version", action="store_true", help="print version JSON and exit")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("version", help="print version JSON")
    r = sub.add_parser("run", help="fetch, verify and load sources")
    r.add_argument("--data-dir", type=Path, default=Path(os.environ.get("VSM_DATA_DIR", "data")))
    r.add_argument("--db", type=Path, default=None, help="default: <data-dir>/reference.sqlite")
    r.add_argument("--only", action="append", help="source id (repeatable)")
    args = parser.parse_args(argv)

    if args.version or args.cmd == "version":
        print(json.dumps(version_info()))
        return 0
    if args.cmd != "run":
        parser.print_help()
        return 2
    try:
        return run(args.data_dir, args.db or args.data_dir / "reference.sqlite", set(args.only or []) or None)
    except IngestError as e:
        print(f"vsm-ingest: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
