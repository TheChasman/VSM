"""`vsm-ingest`: fetch, verify and load every source in data/sources.toml."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from vsm_py import __version__

from . import IngestError, commons
from .fetch import ensure, sha256_file
from .parties import Registry
from .schema import connect
from .sources import load_sources

LOADERS = {"commons_candidacies": commons.load}


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
    conn = connect(db)
    try:
        for s in sources:
            if only and s.id not in only:
                continue
            path = ensure(s, data_dir)
            n = LOADERS[s.loader](conn, s, path, sha256_file(path), registry)
            print(f"{s.id}: {n} contests -> {db}")
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
