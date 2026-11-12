"""Scottish Parliament (Holyrood) results: the ONS constituency → region lookup and the
Electoral Management Board for Scotland (EMB) "votes and seats" workbook (AMS: FPTP
constituencies plus a D'Hondt regional top-up of seven seats per region).

The workbook carries no GSS codes, so names are matched once, here, to the official names
loaded from the ONS lookup (ADR-0014 exception, as for the Senedd briefing): every name must
match exactly one code, ignoring case and spacing, or ingest stops. Two EMB region names differ
from the ONS ones, as do two island constituencies; all four are listed in NAME_ALIASES.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from . import IngestError
from .parties import INDEPENDENT, Registry
from .register import Layer, check_codes
from .sources import Source

SPC, SPR = "SPC2021", "SPR2021"
CONSTITUENCY_SEATS, REGIONS, REGION_SEATS = 73, 8, 7
TICK = "ü"  # Wingdings check mark in the EMB "Seats" sheets
# Constituency columns that are not parties: independents, aggregated per constituency.
INDEPENDENT_COLUMNS = {"Independent Candidates", "Candidate - No description"}
# EMB spelling -> ONS SPC20NM / SPR20NM (normalised).
NAME_ALIASES = {
    "orkney": "orkney islands",
    "shetland": "shetland islands",
    "south of scotland": "south scotland",
    "west of scotland": "west scotland",
}


def norm(name: str) -> str:
    n = re.sub(r"\s+", " ", name).strip().casefold()
    return NAME_ALIASES.get(n, n)


def clean(cell) -> str:
    return re.sub(r"\s+", " ", str(cell)).strip() if cell is not None else ""


@dataclass
class ConstituencyResult:
    name: str
    electorate: int
    valid: int
    rejected: int
    votes: dict[str, int]  # column (party or independent heading) -> votes, non-zero only
    winner: str = ""


@dataclass
class RegionResult:
    name: str
    electorate: int = 0
    valid: int = 0
    rejected: int = 0
    votes: dict[str, int] = field(default_factory=dict)  # party or individual -> votes
    seats: dict[str, int] = field(default_factory=dict)
    individuals: set[str] = field(default_factory=set)


def _header(rows: list[tuple], first: str) -> int:
    for i, r in enumerate(rows):
        if r and clean(r[0]) == first:
            return i
    raise IngestError(f"no header row starting {first!r}")


def parse_constituencies(votes_rows: list[tuple], seats_rows: list[tuple]) -> list[ConstituencyResult]:
    h = _header(votes_rows, "Constituency")
    head = [clean(c) for c in votes_rows[h]]
    i_elec, i_total = head.index("Electorate"), head.index("Total Votes")
    i_rej = head.index("Rejected Papers")  # the first; a later one is a share
    parties = [(j, head[j]) for j in range(i_total + 1, i_rej)]
    out: dict[str, ConstituencyResult] = {}
    for r in votes_rows[h + 1 :]:
        name = clean(r[0])
        if name == "Total":
            break
        if not name:
            continue
        votes = {p: int(r[j]) for j, p in parties if r[j]}
        rejected = int(r[i_rej])
        c = ConstituencyResult(name, int(r[i_elec]), int(r[i_total]) - rejected, rejected, votes)
        if sum(votes.values()) != c.valid:
            raise IngestError(f"{name}: candidate votes sum to {sum(votes.values())}, valid {c.valid}")
        out[name] = c

    h = _header(seats_rows, "Constituency")
    head = [clean(c) for c in seats_rows[h]]
    for r in seats_rows[h + 1 :]:
        name = clean(r[0])
        if name == "Total":
            break
        if not name:
            continue
        ticks = [head[j] for j in range(2, len(head)) if clean(r[j]) == TICK]
        if name not in out or len(ticks) != 1:
            raise IngestError(f"{name}: expected one winner in the seats sheet, got {ticks}")
        if ticks[0] not in out[name].votes:
            raise IngestError(f"{name}: winner {ticks[0]} has no votes")
        out[name].winner = ticks[0]
    missing = [n for n, c in out.items() if not c.winner]
    if missing or len(out) != CONSTITUENCY_SEATS:
        raise IngestError(f"expected {CONSTITUENCY_SEATS} constituencies with winners: {len(out)}, {missing}")
    return list(out.values())


def parse_regions(votes_rows: list[tuple], seats_rows: list[tuple]) -> list[RegionResult]:
    h = _header(votes_rows, "Region")
    head = [clean(c) for c in votes_rows[h]]
    cols = [(j, head[j]) for j in range(1, head.index("Total"))]
    regions = {name: RegionResult(name) for _, name in cols}
    individual = False
    for r in votes_rows[h + 1 :]:
        label = clean(r[0])
        if label in ("Registered Parties", ""):
            continue
        if label == "Individual Candidates":
            individual = True
            continue
        if label == "Rejected Papers":
            for j, name in cols:
                regions[name].rejected = int(r[j])
            continue
        if label == "Total":
            for j, name in cols:
                regions[name].valid = int(r[j]) - regions[name].rejected
            continue
        if label == "Electorate":
            for j, name in cols:
                regions[name].electorate = int(r[j])
            break
        for j, name in cols:
            if r[j]:
                regions[name].votes[label] = int(r[j])
                if individual:
                    regions[name].individuals.add(label)

    h = _header(seats_rows, "Region")
    head = [clean(c) for c in seats_rows[h]]
    seat_cols = [(j, head[j]) for j in range(1, head.index("Total"))]
    if [n for _, n in seat_cols] != [n for _, n in cols]:
        raise IngestError("region columns differ between the votes and seats sheets")
    for r in seats_rows[h + 1 :]:
        label = clean(r[0])
        if label == "Total":
            break
        if label in ("Registered Parties", "Individual Candidates", ""):
            continue
        for j, name in seat_cols:
            if r[j]:
                if label not in regions[name].votes:
                    raise IngestError(f"{name}: {label} won a seat without votes")
                regions[name].seats[label] = int(r[j])

    for g in regions.values():
        if sum(g.votes.values()) != g.valid:
            raise IngestError(f"{g.name}: list votes sum to {sum(g.votes.values())}, valid {g.valid}")
        if sum(g.seats.values()) != REGION_SEATS:
            raise IngestError(f"{g.name}: expected {REGION_SEATS} list seats, got {sum(g.seats.values())}")
        for p in g.individuals:
            if g.seats.get(p, 0) > 1:
                raise IngestError(f"{g.name}: individual {p} won more than one seat")
    return list(regions.values())


def read_workbook(path: Path) -> dict[str, list[tuple]]:
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        return {ws.title: list(ws.iter_rows(values_only=True)) for ws in wb.worksheets}
    finally:
        wb.close()


def _source_row(conn: sqlite3.Connection, source: Source, sha256: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO source VALUES (?, ?, ?, ?, datetime('now'), ?)",
        (source.id, source.url, source.licence, sha256, int(source.redistributable)),
    )


def load_spc_spr_lookup(
    conn: sqlite3.Connection,
    source: Source,
    path: Path,
    sha256: str,
    registry,
    layer: Layer | None,
    layers: dict[str, Layer],
) -> int:
    """ONS SPC → SPR lookup (f=json): names and codes for both layers, plus exact links."""
    spc, spr = layers.get(SPC), layers.get(SPR)
    if not (spc and spr):
        raise IngestError(f"{source.id}: needs layers {SPC} and {SPR} registered")
    feats = [f["attributes"] for f in json.loads(path.read_text(encoding="utf-8")).get("features", [])]
    if not feats:
        raise IngestError(f"{source.id}: no features")
    cfield = next(k for k in feats[0] if re.fullmatch(r"SPC\d\dCD", k))
    rfield = cfield.replace("SPC", "SPR")
    constituencies = {f[cfield]: f[cfield.replace("CD", "NM")].strip() for f in feats}
    regions: dict[str, str] = {}
    for f in feats:
        name = f[rfield.replace("CD", "NM")].strip()
        if regions.setdefault(f[rfield], name) != name:
            raise IngestError(f"{source.id}: region {f[rfield]} has two names")
    if len(constituencies) != len(feats) or len(constituencies) != CONSTITUENCY_SEATS:
        raise IngestError(f"{source.id}: expected {CONSTITUENCY_SEATS} distinct constituencies")
    if len(regions) != REGIONS:
        raise IngestError(f"{source.id}: expected {REGIONS} regions, got {len(regions)}")
    check_codes(spc, set(constituencies), source.id)
    check_codes(spr, set(regions), source.id)
    with conn:
        _source_row(conn, source, sha256)
        conn.execute("DELETE FROM geography_link WHERE from_layer = ? AND to_layer = ?", (SPC, SPR))
        for lid, rows in ((SPC, constituencies), (SPR, regions)):
            conn.execute("DELETE FROM area WHERE layer_id = ?", (lid,))
            conn.executemany("INSERT INTO area VALUES (?, ?, ?)", [(lid, g, n) for g, n in rows.items()])
        conn.executemany(
            "INSERT INTO geography_link VALUES (?, ?, ?, ?, 'exact', 1.0, 0)",
            [(SPC, f[cfield], SPR, f[rfield]) for f in feats],
        )
    return len(feats)


def _codes(conn: sqlite3.Connection, layer_id: str, names: list[str], source: Source) -> dict[str, str]:
    official = {
        norm(n): g for g, n in conn.execute("SELECT gss_code, name FROM area WHERE layer_id = ?", (layer_id,))
    }
    if not official:
        raise IngestError(f"{source.id}: no names and codes loaded for {layer_id}; load them first")
    out: dict[str, str] = {}
    for n in names:
        g = official.get(norm(n))
        if g is None:
            raise IngestError(f"{source.id}: {n!r} matches no {layer_id} name")
        if g in out.values():
            raise IngestError(f"{source.id}: two names match {g}")
        out[n] = g
    if set(out.values()) != set(official.values()):
        raise IngestError(
            f"{source.id}: missing from the results: {sorted(set(official.values()) - set(out.values()))}"
        )
    return out


def load_emb_workbook(
    conn: sqlite3.Connection,
    source: Source,
    path: Path,
    sha256: str,
    registry: Registry,
    layer: Layer | None,
    layers: dict[str, Layer],
) -> int:
    if not (source.election_id and source.office and source.boundary_set and source.polling_date):
        raise IngestError(f"{source.id}: needs election_id, office, boundary_set and polling_date")
    spc, spr = layers.get(SPC), layers.get(SPR)
    if not (spc and spr):
        raise IngestError(f"{source.id}: needs layers {SPC} and {SPR} registered")
    sheets = read_workbook(path)
    cons = parse_constituencies(sheets["Constituency - Votes"], sheets["Constituency - Seats"])
    regs = parse_regions(sheets["Region - Votes"], sheets["Region - Seats"])
    if len(regs) != REGIONS:
        raise IngestError(f"{source.id}: expected {REGIONS} regions, got {len(regs)}")
    check_summary(sheets["Summary"], cons, regs)

    ccode = _codes(conn, SPC, [c.name for c in cons], source)
    rcode = _codes(conn, SPR, [g.name for g in regs], source)
    check_codes(spc, set(ccode.values()), source.id)
    check_codes(spr, set(rcode.values()), source.id)
    names = {p for c in cons for p in c.votes if p not in INDEPENDENT_COLUMNS}
    names |= {p for g in regs for p in g.votes if p not in g.individuals}
    mapping = registry.map_all(names)
    for col in INDEPENDENT_COLUMNS:
        mapping[col] = INDEPENDENT

    eid = source.election_id
    with conn:
        _source_row(conn, source, sha256)
        conn.execute(
            "INSERT OR REPLACE INTO election VALUES (?, ?, ?, ?, ?)",
            (eid, source.office, source.polling_date, source.boundary_set, source.id),
        )
        for table in ("seat_order", "list_result", "candidate_result", "contest"):
            conn.execute(f"DELETE FROM {table} WHERE election_id = ?", (eid,))
        for c in cons:
            gss = ccode[c.name]
            conn.execute(
                "INSERT INTO contest VALUES (?, ?, ?, ?, ?, NULL, NULL)",
                (eid, gss, c.electorate, c.valid, c.rejected),
            )
            ranked = sorted(c.votes.items(), key=lambda kv: (-kv[1], kv[0]))
            conn.executemany(
                "INSERT INTO candidate_result VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (eid, gss, seq, mapping[p], v, int(p == c.winner))
                    for seq, (p, v) in enumerate(ranked, start=1)
                ],
            )
        for g in regs:
            gss = rcode[g.name]
            conn.execute(
                "INSERT INTO contest VALUES (?, ?, ?, ?, ?, NULL, NULL)",
                (eid, gss, g.electorate, g.valid, g.rejected),
            )
            ranked = sorted(g.votes.items(), key=lambda kv: (-kv[1], kv[0]))
            conn.executemany(
                "INSERT INTO list_result VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        eid,
                        gss,
                        seq,
                        INDEPENDENT if p in g.individuals else mapping[p],
                        p if p in g.individuals else None,
                        v,
                        g.seats.get(p, 0),
                        1 if p in g.individuals else None,  # party list sizes are not in the workbook
                    )
                    for seq, (p, v) in enumerate(ranked, start=1)
                ],
            )
    return len(cons) + len(regs)


def check_summary(rows: list[tuple], cons: list[ConstituencyResult], regs: list[RegionResult]) -> None:
    """The Summary sheet's votes and seats (constituency, region) must agree with the detail sheets."""
    h = _header(rows, "Party")
    head = [clean(c) for c in rows[h]]
    iv = [j for j, c in enumerate(head) if c == "Votes"][:2]
    js = [j for j, c in enumerate(head) if c == "Seats"][:2]
    detail: dict[str, tuple[int, int, int, int]] = {}
    for r in rows[h + 1 :]:
        label = clean(r[0])
        if not label or label.startswith("Others"):
            continue
        key = label.casefold()
        if label == "Total":
            got = (
                sum(c.valid for c in cons),
                len(cons),
                sum(g.valid for g in regs),
                sum(sum(g.seats.values()) for g in regs),
            )
        else:
            got = (
                sum(v for c in cons for p, v in c.votes.items() if p.casefold() == key),
                sum(1 for c in cons if c.winner.casefold() == key),
                sum(v for g in regs for p, v in g.votes.items() if p.casefold() == key),
                sum(n for g in regs for p, n in g.seats.items() if p.casefold() == key),
            )
        want = (int(r[iv[0]]), int(r[js[0]]), int(r[iv[1]]), int(r[js[1]]))
        if got != want:
            raise IngestError(f"Summary {label}: {want} disagrees with the detail sheets {got}")
        detail[label] = got
        if label == "Total":
            break
    if "Total" not in detail:
        raise IngestError("Summary: no Total row")
