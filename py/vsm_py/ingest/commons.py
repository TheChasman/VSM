"""Loader for UK Parliament election results `candidacies.csv` (electionresults.parliament.uk).

One file is one general election, real or notional. Every contest is cross-checked
against the file's own totals before anything is written.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import IngestError
from .parties import INDEPENDENT, SPEAKER, Registry
from .sources import Source

NATIONS = {"E92000001": "E", "S92000003": "S", "W92000004": "W", "N92000002": "N"}

# Parliamentary Constituencies Act 2020, s.1 (rule 6): seats outside the electoral quota.
PROTECTED = {
    "Orkney and Shetland",
    "Na h-Eileanan an Iar",
    "Ynys Môn",
    "Isle of Wight East",
    "Isle of Wight West",
}


@dataclass
class Contest:
    gss: str
    name: str
    nation: str
    region: str
    electorate: int
    valid: int
    invalid: int | None
    declared_at: str | None
    candidates: list[tuple[int, str, int]]  # (position, party_code, votes)


def _int(value: str, what: str) -> int:
    try:
        return int(value)
    except ValueError as e:
        raise IngestError(f"bad integer for {what}: {value!r}") from e


def parse(path: Path, registry: Registry) -> tuple[dict[str, str], list[Contest]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise IngestError(f"{path}: no rows")

    def party_name(r: dict[str, str]) -> str:
        if r["Candidate is standing as Commons Speaker"] == "true":
            return "__speaker__"
        if r["Candidate is standing as independent"] == "true":
            return "__independent__"
        return r["Main party name"]

    names = {party_name(r) for r in rows} - {"__speaker__", "__independent__"}
    mapping = registry.map_all(names) | {"__speaker__": SPEAKER, "__independent__": INDEPENDENT}

    header = rows[0]
    election = {
        "polling_date": header["General election polling date"],
        "notional": header["General election is notional"],
        "total_valid": header["Total valid votes in general election"],
    }

    by_gss: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        if r["General election polling date"] != election["polling_date"]:
            raise IngestError(f"{path}: rows from more than one general election")
        if r["Election is by-election"] == "true":
            continue
        by_gss[r["Constituency geographic code"]].append(r)

    contests = []
    for gss, rs in sorted(by_gss.items()):
        first = rs[0]
        cands = sorted(
            (
                _int(r["Candidate result position"], f"{gss} position"),
                mapping[party_name(r)],
                _int(r["Candidate vote count"], f"{gss} votes"),
            )
            for r in rs
        )
        valid = _int(first["Election valid vote count"], f"{gss} valid votes")
        total = sum(v for _, _, v in cands)
        if total != valid:
            raise IngestError(f"{path}: {gss} candidate votes sum to {total}, file says {valid} valid")
        positions = [p for p, _, _ in cands]
        if positions != list(range(1, len(cands) + 1)):
            raise IngestError(f"{path}: {gss} result positions are not 1..{len(cands)}: {positions}")
        if len(cands) > 1 and cands[0][2] <= cands[1][2]:
            raise IngestError(f"{path}: {gss} winner does not have the most votes")
        invalid = first["Election invalid vote count"]
        contests.append(
            Contest(
                gss=gss,
                name=first["Constituency name"].strip(),
                nation=NATIONS.get(first["Country geographic code"]) or _bad_nation(gss, first),
                region=first["English region name"] or first["Country name"],
                electorate=_int(first["Electorate"], f"{gss} electorate"),
                valid=valid,
                invalid=_int(invalid, f"{gss} invalid votes") if invalid else None,
                declared_at=first["Declaration time"] or None,
                candidates=cands,
            )
        )

    grand = sum(c.valid for c in contests)
    if election["total_valid"] and _int(election["total_valid"], "total valid") != grand:
        raise IngestError(
            f"{path}: contests sum to {grand} valid votes, file total {election['total_valid']}"
        )
    return election, contests


def _bad_nation(gss: str, row: dict[str, str]) -> str:
    raise IngestError(f"{gss}: unknown country code {row['Country geographic code']!r}")


def load(conn: sqlite3.Connection, source: Source, path: Path, sha256: str, registry: Registry) -> int:
    """Write one election in a single transaction. Re-running replaces that election's rows."""
    if not (source.election_id and source.office and source.boundary_set):
        raise IngestError(f"{source.id}: commons_candidacies needs election_id, office and boundary_set")
    election, contests = parse(path, registry)
    if source.reference_electorate:
        found = {c.name for c in contests} & PROTECTED
        if found != PROTECTED:
            raise IngestError(f"{source.id}: protected seats not found: {sorted(PROTECTED - found)}")

    eid = source.election_id
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO source VALUES (?, ?, ?, ?, ?, ?)",
            (
                source.id,
                source.url,
                source.licence,
                sha256,
                datetime.now(UTC).replace(microsecond=0).isoformat(),
                int(source.redistributable),
            ),
        )
        for p in registry.parties:
            conn.execute(
                "INSERT OR REPLACE INTO party VALUES (?, ?, ?)",
                (p.code, p.name, json.dumps(list(p.aliases), ensure_ascii=False) if p.aliases else None),
            )
        conn.execute(
            "INSERT OR REPLACE INTO election VALUES (?, ?, ?, ?, ?)",
            (eid, source.office, election["polling_date"], source.boundary_set, source.id),
        )
        conn.execute("DELETE FROM candidate_result WHERE election_id = ?", (eid,))
        conn.execute("DELETE FROM contest WHERE election_id = ?", (eid,))
        for c in contests:
            if source.reference_electorate:
                conn.execute(
                    """INSERT INTO constituency
                         (gss_code, name, nation, region, county, electorate, protected)
                       VALUES (?, ?, ?, ?, NULL, ?, ?)
                       ON CONFLICT (gss_code) DO UPDATE SET name = excluded.name, nation = excluded.nation,
                         region = excluded.region, electorate = excluded.electorate,
                         protected = excluded.protected""",
                    (c.gss, c.name, c.nation, c.region, c.electorate, int(c.name in PROTECTED)),
                )
            conn.execute(
                "INSERT INTO contest VALUES (?, ?, ?, ?, ?, ?)",
                (eid, c.gss, c.electorate, c.valid, c.invalid, c.declared_at),
            )
            conn.executemany(
                "INSERT INTO candidate_result VALUES (?, ?, ?, ?, ?, ?)",
                [(eid, c.gss, pos, code, votes, int(pos == 1)) for pos, code, votes in c.candidates],
            )
    return len(contests)
