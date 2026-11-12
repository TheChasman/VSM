"""Senedd 2026 results from the Senedd Research briefing PDF (closed lists, D'Hondt).

The briefing carries no GSS codes, so constituency names are matched once, here, to the
official names and codes already loaded into `area` for the layer (ADR-0014 exception):
every constituency must match exactly one code, ignoring case and spacing, or ingest stops.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from . import IngestError
from .parties import INDEPENDENT, Registry
from .register import Layer, check_codes
from .sources import Source

ROW = re.compile(
    r"^\s*(?P<name>\S.*?)\s{2,}(?P<votes>[\d,]+)\s+(?P<share>[\d.]+%)\s+(?P<won>\d+)\s+(?P<cands>\d+|Individual)\s*$"
)
ELECTED = re.compile(r"^\s*(?P<pos>\d+)\s{2,}(?P<member>\S.*?)\s{2,}(?P<party>\S.*?)\s*$")
FIELD = re.compile(r"^\s*(Electorate|Valid votes cast|Total rejected ballot papers):\s*([\d,]+)\s*$")


@dataclass
class ListRow:
    name: str
    votes: int
    seats: int
    candidates: int  # 1 for an individual candidate
    individual: bool


@dataclass
class Constituency:
    name: str
    electorate: int = 0
    valid: int = 0
    rejected: int = 0
    lists: list[ListRow] = field(default_factory=list)
    order: list[str] = field(default_factory=list)  # list names, by seat position


def _num(s: str) -> int:
    return int(s.replace(",", ""))


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().casefold()


def parse_page(text: str) -> Constituency | None:
    lines = text.splitlines()
    try:
        first_field = next(i for i, ln in enumerate(lines) if ln.strip().startswith("Electorate:"))
    except StopIteration:
        return None
    heading = [ln.strip() for ln in lines[:first_field] if ln.strip() and "Research Briefing" not in ln]
    if not heading:
        raise IngestError("constituency page without a heading")
    c = Constituency(name=" ".join(heading))

    section = "fields"
    for ln in lines[first_field:]:
        s = ln.strip()
        if not s:
            continue
        if section == "fields":
            m = FIELD.match(ln)
            if m:
                value = _num(m.group(2))
                key = m.group(1)
                if key == "Electorate":
                    c.electorate = value
                elif key == "Valid votes cast":
                    c.valid = value
                else:
                    c.rejected = value
                continue
            if s.startswith("Political Party"):
                section = "lists"
            continue
        if section == "lists":
            if s.startswith("Elected Members"):
                section = "elected"
                continue
            m = ROW.match(ln)
            if m:
                ind = m.group("cands") == "Individual"
                c.lists.append(
                    ListRow(
                        m.group("name").strip(),
                        _num(m.group("votes")),
                        int(m.group("won")),
                        1 if ind else int(m.group("cands")),
                        ind,
                    )
                )
            elif c.lists and not re.search(r"\d", s):
                c.lists[-1].name += " " + s  # wrapped party name
            continue
        if section == "elected":
            if s.startswith("Position"):
                continue
            m = ELECTED.match(ln)
            if m:
                c.order.append(m.group("party").strip())
            elif c.order and not re.search(r"\d", s) and len(c.order) < 6:
                c.order[-1] += " " + s
            elif re.fullmatch(r"\d+", s):
                break  # page number
    return c


def parse(path: Path) -> list[Constituency]:
    out = [
        c for page in PdfReader(path).pages if (c := parse_page(page.extract_text(extraction_mode="layout")))
    ]
    for c in out:
        where = f"{path.name}: {c.name}"
        if sum(r.votes for r in c.lists) != c.valid:
            raise IngestError(f"{where}: list votes sum to {sum(r.votes for r in c.lists)}, valid {c.valid}")
        if sum(r.seats for r in c.lists) != 6 or len(c.order) != 6:
            raise IngestError(
                f"{where}: expected 6 seats, got {sum(r.seats for r in c.lists)} / {len(c.order)}"
            )
        names = {r.name for r in c.lists}
        unknown = [p for p in c.order if p not in names]
        if unknown:
            raise IngestError(f"{where}: elected members' parties not in the results table: {unknown}")
        for r in c.lists:
            if c.order.count(r.name) != r.seats:
                raise IngestError(f"{where}: {r.name} won {r.seats} but {c.order.count(r.name)} in the order")
            if r.seats > r.candidates:
                raise IngestError(f"{where}: {r.name} won more seats than it had candidates")
    return out


def load(
    conn: sqlite3.Connection,
    source: Source,
    path: Path,
    sha256: str,
    registry: Registry,
    layer: Layer | None = None,
    layers=None,
) -> int:
    if not (layer and source.election_id and source.office and source.boundary_set):
        raise IngestError(f"{source.id}: needs layer, election_id, office and boundary_set")
    parsed = parse(path)
    official = {
        norm(n): g for g, n in conn.execute("SELECT gss_code, name FROM area WHERE layer_id = ?", (layer.id,))
    }
    if not official:
        raise IngestError(f"{source.id}: no names and codes loaded for layer {layer.id}; load them first")
    codes = {}
    for c in parsed:
        gss = official.get(norm(c.name))
        if gss is None:
            raise IngestError(f"{source.id}: {c.name!r} matches no {layer.id} name")
        if gss in codes.values():
            raise IngestError(f"{source.id}: two constituencies match {gss}")
        codes[c.name] = gss
    if set(codes.values()) != set(official.values()):
        missing = sorted(set(official.values()) - set(codes.values()))
        raise IngestError(f"{source.id}: constituencies missing from the results: {missing}")
    check_codes(layer, set(codes.values()), source.id)
    # An "Individual" row is a list of one. The briefing labels some single-candidate parties
    # that way (e.g. Welsh Christian Party); a name in the registry keeps its party code.
    for c in parsed:
        for r in c.lists:
            if r.individual and registry.lookup(r.name):
                r.individual = False
    mapping = registry.map_all({r.name for c in parsed for r in c.lists if not r.individual})

    eid = source.election_id
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO source VALUES (?, ?, ?, ?, datetime('now'), ?)",
            (source.id, source.url, source.licence, sha256, int(source.redistributable)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO election VALUES (?, ?, ?, ?, ?)",
            (eid, source.office, source.polling_date, source.boundary_set, source.id),
        )
        for table in ("seat_order", "list_result", "contest"):
            conn.execute(f"DELETE FROM {table} WHERE election_id = ?", (eid,))
        for c in parsed:
            gss = codes[c.name]
            conn.execute(
                "INSERT INTO contest VALUES (?, ?, ?, ?, ?, NULL, NULL)",
                (eid, gss, c.electorate, c.valid, c.rejected),
            )
            seq_of = {}
            for seq, r in enumerate(sorted(c.lists, key=lambda r: -r.votes), start=1):
                seq_of[r.name] = seq
                conn.execute(
                    "INSERT INTO list_result VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        eid,
                        gss,
                        seq,
                        INDEPENDENT if r.individual else mapping[r.name],
                        r.name if r.individual else None,
                        r.votes,
                        r.seats,
                        r.candidates,
                    ),
                )
            conn.executemany(
                "INSERT INTO seat_order VALUES (?, ?, ?, ?)",
                [(eid, gss, pos, seq_of[name]) for pos, name in enumerate(c.order, start=1)],
            )
    return len(parsed)
