"""Scottish council elections, 2022: wards, declared results, ballot preference profiles and
declared stage totals (STV, Weighted Inclusive Gregory Method, five decimal places).

Sources, all matched to the ONS May 2022 ward codes once, here (ADR-0014 exception, as for
Holyrood):

- ONS "Ward to Local Authority District (May 2022) Lookup in the UK": codes, names and the
  ward -> council links for Scotland's 355 wards.
- The Electoral Management Board for Scotland (EMB) returning-officer results workbook: per
  ward, the electorate, ballots counted and rejected, and per candidate the first preferences,
  whether elected and at which stage.
- The preference profiles as published by each returning officer, from Denis Mollison's
  collection (Heriot-Watt University) in "ballot format": one file per ward.
- City of Edinburgh Council "Candidate Votes Per Stage" reports (PDF): declared stage totals.

Ward names are matched within a council after `ward_key` normalisation (case, spacing,
punctuation, "Ward N -" prefixes and "Ward" suffixes, "&" for "and"); two names that differ
by more are listed in WARD_ALIASES. Ballot files are matched to EMB wards by their candidate
names (case and spacing ignored), then cross-checked: ballots counted, first preferences per
candidate, and elected count against the ward's vacancies. Nothing downstream joins by name.
"""

from __future__ import annotations

import re
import unicodedata
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import IngestError
from .register import check_codes
from .sources import Source

WARD_LAYER, LAD_LAYER = "WD2022S", "LAD2022S"
WARDS, COUNCILS, VACANCIES = 355, 32, 1226
DECIMALS = 5
SCALE = 10**DECIMALS

# ward_key of the EMB spelling -> ward_key of the ONS WD22NM.
WARD_ALIASES = {
    "sgìrùigeaguscarlabhagh": "sgìrùigeaguscàrlabhagh",  # EMB "Sgìr’ Ùige agus Carlabhagh"
    "eileanacheò": "eileanáchèo",  # EMB "Eilean a' Cheò", ONS "Eilean á Chèo"
}
# EMB "Authority Name" -> ONS LAD22NM.
COUNCIL_ALIASES = {
    "Comhairle nan Eilean Siar": "Na h-Eileanan Siar",
    "The City of Edinburgh Council": "City of Edinburgh",
    "Orkney Islands Council": "Orkney Islands",
    "Shetland Islands Council": "Shetland Islands",
}


def council_name(emb_authority: str) -> str:
    if emb_authority in COUNCIL_ALIASES:
        return COUNCIL_ALIASES[emb_authority]
    name = re.sub(r"^The\s+", "", emb_authority)
    name = re.sub(r"\s+Council$", "", name)
    return name.replace(" & ", " and ")


def ward_key(name: str) -> str:
    s = unicodedata.normalize("NFC", name).casefold().strip()
    s = re.sub(r"^ward\s*\d+\s*[-–:.]?\s*", "", s)
    s = re.sub(r"^\d+\s*[-–:.]?\s*", "", s)
    s = re.sub(r"\s*\(ward\s*\d+\)$", "", s)
    s = re.sub(r"\s+ward$", "", s)
    s = s.replace("&", " and ")
    s = "".join(ch for ch in s if ch.isalnum())
    return WARD_ALIASES.get(s, s)


# name_key of a ballot-file spelling -> name_key of the EMB spelling, where they differ by more
# than case, spacing and apostrophes.
CANDIDATE_ALIASES = {
    "peter a donnghaile": "peter ó donnghaile",  # Highland, Eilean a' Cheò: accent lost
}


def name_key(name: str) -> str:
    """Candidate names: case, spacing and apostrophes ignored (EMB "ONEILL", RO "O'NEILL")."""
    s = re.sub(r"['’‘`]", "", unicodedata.normalize("NFC", name))
    s = re.sub(r"\s+", " ", s).strip().casefold()
    return CANDIDATE_ALIASES.get(s, s)


def repair(text: str) -> str:
    """Undo UTF-8 read as Windows-1252 ("Ã“" for "Ó"), in a few names on both sides."""
    if not re.search("[ÃÂâ]", text):
        return text
    try:
        return text.encode("cp1252").decode("utf-8")
    except UnicodeError:
        return text


# --- Ballot files -------------------------------------------------------------------------


@dataclass
class WardBallots:
    path: str
    number: int
    name: str
    seats: int
    valid: int
    candidates: list[str]
    ballots: list[tuple[int, tuple[int, ...]]]  # (papers, candidate indices in preference order)


def _candidate_name(line: str) -> str:
    """`Name, party` or, as some councils publish it, `"Name" "Description", `."""
    if line.startswith('"'):
        return repair(line[1:].split('"', 1)[0].strip())
    return repair(line.rsplit(",", 1)[0].strip())


def parse_ballot_dat(text: str, where: str) -> WardBallots:
    """Mollison "ballot format": `N name`, `seats candidates lines valid`, one `name, party`
    line per candidate, then `papers rank_1 … rank_n` (0 = no preference) per line."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    try:
        number, name = lines[0].split(" ", 1)
        seats, n_cand, n_lines, valid = (int(x) for x in lines[1].split())
        candidates = [_candidate_name(ln) for ln in lines[2 : 2 + n_cand]]
    except (ValueError, IndexError) as e:
        raise IngestError(f"{where}: bad header: {e}") from e
    body = lines[2 + n_cand :]
    if len(candidates) != n_cand or len(body) != n_lines:
        raise IngestError(f"{where}: expected {n_lines} ballot lines, got {len(body)}")
    ballots = []
    for ln in body:
        v = [int(x) for x in ln.split()]
        if len(v) != n_cand + 1 or v[0] <= 0:
            raise IngestError(f"{where}: bad ballot line {ln!r}")
        ranked = sorted((r, j) for j, r in enumerate(v[1:]) if r)
        if [r for r, _ in ranked] != list(range(1, len(ranked) + 1)):
            raise IngestError(f"{where}: ranks {v[1:]} do not run 1, 2, 3 … without gaps")
        ballots.append((v[0], tuple(j for _, j in ranked)))
    total = sum(w for w, _ in ballots)
    if total != valid:
        raise IngestError(f"{where}: ballots sum to {total}, header says {valid}")
    return WardBallots(where, int(number), name.strip(), seats, valid, candidates, ballots)


def match_candidates(ballot_names: list[str], emb_names: list[str]) -> list[int]:
    """Index into `emb_names` of each ballot-file candidate (case and spacing ignored)."""
    index = {name_key(n): i for i, n in enumerate(emb_names)}
    out = []
    for n in ballot_names:
        if name_key(n) not in index:
            raise IngestError(f"no EMB candidate for {n!r}")
        out.append(index[name_key(n)])
    if sorted(out) != list(range(len(emb_names))):
        raise IngestError(f"candidates {ballot_names} do not pair one-to-one with {emb_names}")
    return out


# --- EMB workbook -------------------------------------------------------------------------


@dataclass
class EmbCandidate:
    name: str
    party: str
    votes: int
    stage_elected: int | None


@dataclass
class EmbWard:
    council: str
    name: str
    electorate: int
    valid: int
    rejected: int
    candidates: list[EmbCandidate] = field(default_factory=list)


def parse_emb_rows(rows) -> dict[tuple[str, str], EmbWard]:
    """RawDetails sheet rows (header removed), one per candidate."""
    wards: dict[tuple[str, str], EmbWard] = {}
    for r in rows:
        if not r or not r[1]:
            continue
        key = (str(r[1]).strip(), str(r[2]).strip())
        w = wards.setdefault(key, EmbWard(key[0], key[1], int(r[3]), int(r[4]), int(r[10])))
        if (w.electorate, w.valid, w.rejected) != (int(r[3]), int(r[4]), int(r[10])):
            raise IngestError(f"{key[0]} / {key[1]}: ward totals differ between rows")
        elected = str(r[13]).strip() == "Yes"
        stage = int(r[14]) if r[14] is not None else None
        name = repair(re.sub(r"\s+", " ", str(r[12])).strip())
        if elected and stage is None:
            raise IngestError(f"{key[0]} / {key[1]}: {name} elected without a stage")
        if not elected and stage is not None:
            raise IngestError(f"{key[0]} / {key[1]}: {name} has a stage but was not elected")
        w.candidates.append(EmbCandidate(name, str(r[16]).strip(), int(r[17]), stage))
    for w in wards.values():
        fp = sum(c.votes for c in w.candidates)
        if fp != w.valid:
            raise IngestError(
                f"{w.council} / {w.name}: first preferences sum to {fp}, ballots counted {w.valid}"
            )
    return wards


# --- Stage reports ------------------------------------------------------------------------

NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def fixed(text: str) -> int:
    """'1,594' or '1,598.00000' -> units of 10^-5, exactly."""
    neg = text.startswith("-")
    whole, _, frac = text.lstrip("-").replace(",", "").partition(".")
    if len(frac) > DECIMALS:
        raise IngestError(f"{text}: more than {DECIMALS} decimal places")
    value = int(whole) * SCALE + int((frac + "0" * DECIMALS)[:DECIMALS])
    return -value if neg else value


@dataclass
class StageReport:
    valid: int
    seats: int
    quota: int
    stages: list[list[int]]  # per stage: one total per candidate, then non-transferable


def _header_int(text: str, label: str) -> int:
    m = re.search(rf"{label}\s+([\d,]+)", text)
    if not m:
        raise IngestError(f"stage report: no {label!r}")
    return int(m.group(1).replace(",", ""))


def parse_stage_text(text: str, names: list[str]) -> StageReport:
    """Text of a "Candidate Votes Per Stage" report. Each candidate's last number in a stage is
    its total; non-transferable is the sum of the plain and "due to rounding" totals."""
    valid = _header_int(text, "Total Number of Valid Votes")
    seats = _header_int(text, "Positions to be Filled")
    quota = _header_int(text, "Quota")
    blocks = re.split(r"^Stage (\d+)\s*$", text, flags=re.M)
    keys = {name_key(n): n for n in names}
    by_len = sorted(keys, key=len, reverse=True)
    stages: list[list[int]] = []
    for i in range(1, len(blocks), 2):
        number, block = int(blocks[i]), blocks[i + 1]
        if number != len(stages) + 1:
            raise IngestError(f"stage report: stage {number} out of order")
        body = block.split("Candidate Name Affiliation", 1)[-1].splitlines()
        segments: dict[str, list[str]] = {}
        current: str | None = None
        for ln in body:
            folded = name_key(ln)
            who = next((k for k in by_len if folded.startswith(k + " ") or folded == k), None)
            if who is not None:
                current = keys[who]
                segments[current] = [folded[len(who) :]]
            elif ln.startswith("Non-transferable"):
                current = ln
                segments[ln] = [ln]
            elif re.search(r"Total$|^Report Name", ln):
                current = None
            elif current is not None:
                segments[current].append(ln)
        row = []
        for n in names:
            if n not in segments:
                raise IngestError(f"stage {number}: no total for {n!r}")
            nums = NUMBER.findall(" ".join(segments[n]))
            if not nums:
                raise IngestError(f"stage {number}: no total for {n!r}")
            row.append(fixed(nums[-1]))
        nt = [k for k in segments if k.startswith("Non-transferable")]
        if len(nt) != 2:
            raise IngestError(f"stage {number}: expected two non-transferable lines, got {len(nt)}")
        row.append(sum(fixed(NUMBER.findall(k)[-1]) for k in nt))
        stages.append(row)
    if not stages:
        raise IngestError("stage report: no stages")
    return StageReport(valid, seats, quota, stages)


# --- Loaders ------------------------------------------------------------------------------


def _source_row(conn, source: Source, sha256: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO source VALUES (?, ?, ?, ?, datetime('now'), ?)",
        (source.id, source.url, source.licence, sha256, int(source.redistributable)),
    )


def _xlsx_rows(path: Path, sheet: str | None = None) -> list[tuple]:
    import warnings

    import openpyxl

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # slicer extensions
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet] if sheet else wb.worksheets[0]
        return [tuple(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def load_wd_lad_lookup(
    conn, source: Source, path: Path, sha256: str, registry, layer=None, layers=None
) -> int:
    """ONS WD22CD, WD22NM, WD22NMW, LAD22CD, LAD22NM: Scottish rows only."""
    rows = _xlsx_rows(path)
    head = [str(c).strip() if c else "" for c in rows[0]]
    want = ["WD22CD", "WD22NM", "LAD22CD", "LAD22NM"]
    if any(h not in head for h in want):
        raise IngestError(f"{source.id}: header {head} lacks {want}")
    ix = [head.index(h) for h in want]
    scot = [
        tuple(str(r[i]).strip() for i in ix) for r in rows[1:] if r[ix[0]] and str(r[ix[0]]).startswith("S")
    ]
    wards = {wd: (wn, lc) for wd, wn, lc, _ in scot}
    lads = {lc: ln for _, _, lc, ln in scot}
    if len(scot) != len(wards) or len(wards) != WARDS or len(lads) != COUNCILS:
        raise IngestError(
            f"{source.id}: expected {WARDS} wards in {COUNCILS} councils, got {len(wards)} in {len(lads)}"
        )
    check_codes(layers[WARD_LAYER], set(wards), source.id)
    check_codes(layers[LAD_LAYER], set(lads), source.id)
    with conn:
        _source_row(conn, source, sha256)
        conn.execute(
            "DELETE FROM geography_link WHERE from_layer = ? AND to_layer = ?", (WARD_LAYER, LAD_LAYER)
        )
        for lay in (WARD_LAYER, LAD_LAYER):
            conn.execute("DELETE FROM area WHERE layer_id = ?", (lay,))
        conn.executemany(
            "INSERT INTO area VALUES (?, ?, ?)", [(WARD_LAYER, c, n) for c, (n, _) in wards.items()]
        )
        conn.executemany("INSERT INTO area VALUES (?, ?, ?)", [(LAD_LAYER, c, n) for c, n in lads.items()])
        conn.executemany(
            "INSERT INTO geography_link VALUES (?, ?, ?, ?, 'exact', 1.0, 0)",
            [(WARD_LAYER, c, LAD_LAYER, lc) for c, (_, lc) in wards.items()],
        )
    return len(wards)


def _ward_codes(conn, source: Source, wards: dict[tuple[str, str], EmbWard]) -> dict[tuple[str, str], str]:
    """(EMB authority, EMB ward) -> WD22CD, pairing every ward exactly once within its council."""
    ons: dict[str, dict[str, str]] = defaultdict(dict)
    for code, name, lad in conn.execute(
        """SELECT a.gss_code, a.name, l.name FROM area a
           JOIN geography_link g ON g.from_layer = a.layer_id AND g.from_code = a.gss_code
                                 AND g.to_layer = ?
           JOIN area l ON l.layer_id = g.to_layer AND l.gss_code = g.to_code
           WHERE a.layer_id = ?""",
        (LAD_LAYER, WARD_LAYER),
    ):
        k = ward_key(name)
        if k in ons[lad]:
            raise IngestError(f"{source.id}: two ONS wards in {lad} share the key {k!r}")
        ons[lad][k] = code
    if len(ons) != COUNCILS:
        raise IngestError(f"{source.id}: load the ONS ward lookup first ({len(ons)} councils in area)")
    out: dict[tuple[str, str], str] = {}
    missing = []
    for key in wards:
        lad = council_name(key[0])
        code = ons.get(lad, {}).get(ward_key(key[1]))
        if code is None:
            missing.append(f"{key[0]} / {key[1]}")
        else:
            out[key] = code
    if missing:
        raise IngestError(f"{source.id}: no ONS ward for:\n  " + "\n  ".join(sorted(missing)))
    if len(set(out.values())) != len(out):
        raise IngestError(f"{source.id}: two EMB wards matched one ONS ward")
    return out


def load_emb_workbook(
    conn, source: Source, path: Path, sha256: str, registry, layer=None, layers=None
) -> int:
    rows = _xlsx_rows(path, "RawDetails")
    if not rows or rows[0][12] != "CandidateName" or rows[0][17] != "NumberOfFirstPreferenceVotes":
        raise IngestError(f"{source.id}: RawDetails header changed: {rows[0] if rows else None}")
    wards = parse_emb_rows(rows[1:])
    if len(wards) != WARDS or len({k[0] for k in wards}) != COUNCILS:
        raise IngestError(f"{source.id}: expected {WARDS} wards in {COUNCILS} councils, got {len(wards)}")
    codes = _ward_codes(conn, source, wards)
    check_codes(layer, set(codes.values()), source.id)
    mapping = registry.map_all({c.party for w in wards.values() for c in w.candidates})
    eid = source.election_id
    with conn:
        _source_row(conn, source, sha256)
        conn.execute(
            "INSERT OR REPLACE INTO election VALUES (?, ?, ?, ?, ?)",
            (eid, source.office, source.polling_date, source.boundary_set, source.id),
        )
        for table in ("stv_stage", "stv_ballot", "stv_candidate", "candidate_result", "contest"):
            conn.execute(f"DELETE FROM {table} WHERE election_id = ?", (eid,))
        for key, w in wards.items():
            gss = codes[key]
            conn.execute(
                "INSERT INTO contest VALUES (?, ?, ?, ?, ?, NULL, NULL)",
                (eid, gss, w.electorate, w.valid, w.rejected),
            )
            for seq, c in enumerate(w.candidates, start=1):
                conn.execute(
                    "INSERT INTO candidate_result VALUES (?, ?, ?, ?, ?, ?)",
                    (eid, gss, seq, mapping[c.party], c.votes, int(c.stage_elected is not None)),
                )
                conn.execute(
                    "INSERT INTO stv_candidate VALUES (?, ?, ?, ?, ?)",
                    (eid, gss, seq, c.name, c.stage_elected),
                )
    return len(wards)


def _emb_candidates(conn, eid: str) -> dict[str, list[tuple[int, str, int, int]]]:
    """gss -> [(seq, name, first preferences, elected)]."""
    out: dict[str, list[tuple[int, str, int, int]]] = defaultdict(list)
    for gss, seq, name, votes, elected in conn.execute(
        """SELECT c.gss_code, c.candidate_seq, s.name, c.votes, c.elected
           FROM candidate_result c JOIN stv_candidate s USING (election_id, gss_code, candidate_seq)
           WHERE c.election_id = ? ORDER BY c.gss_code, c.candidate_seq""",
        (eid,),
    ):
        out[gss].append((seq, name, votes, elected))
    return out


def load_ballot_zip(conn, source: Source, path: Path, sha256: str, registry, layer=None, layers=None) -> int:
    eid = source.election_id
    emb = _emb_candidates(conn, eid)
    if len(emb) != WARDS:
        raise IngestError(f"{source.id}: load the EMB results for {eid} first")
    valid = dict(conn.execute("SELECT gss_code, valid_votes FROM contest WHERE election_id = ?", (eid,)))
    by_names: dict[frozenset[str], str] = {}
    for gss, cands in emb.items():
        k = frozenset(name_key(n) for _, n, _, _ in cands)
        if k in by_names:
            raise IngestError(f"{source.id}: wards {by_names[k]} and {gss} have the same candidates")
        by_names[k] = gss

    files: list[WardBallots] = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.filename.endswith(".dat"):
                files.append(parse_ballot_dat(z.read(info).decode("utf-8"), info.filename))
    rows: list[tuple[str, int, list[tuple[int, str]]]] = []
    seen: set[str] = set()
    for f in files:
        gss = by_names.get(frozenset(name_key(n) for n in f.candidates))
        if gss is None:
            raise IngestError(f"{source.id}: {f.path}: candidates match no EMB ward")
        if gss in seen:
            raise IngestError(f"{source.id}: {f.path}: second file for {gss}")
        seen.add(gss)
        cands = emb[gss]
        order = match_candidates(f.candidates, [n for _, n, _, _ in cands])
        seq = [cands[i][0] for i in order]
        if f.valid != valid[gss]:
            raise IngestError(f"{source.id}: {f.path}: {f.valid} ballots, EMB counted {valid[gss]}")
        fp: dict[int, int] = defaultdict(int)
        for w, ranking in f.ballots:
            fp[seq[ranking[0]]] += w
        for s, _, votes, _ in cands:
            if fp[s] != votes:
                raise IngestError(
                    f"{source.id}: {f.path}: candidate {s} has {fp[s]} first preferences, EMB {votes}"
                )
        elected = sum(e for _, _, _, e in cands)
        if elected != min(f.seats, len(cands)):
            raise IngestError(
                f"{source.id}: {f.path}: {elected} elected for {f.seats} seats, {len(cands)} candidates"
            )
        rows.append((gss, f.seats, [(w, " ".join(str(seq[j]) for j in ranking)) for w, ranking in f.ballots]))
    if seen != set(emb):
        missing = sorted(set(emb) - seen)
        raise IngestError(f"{source.id}: no ballot file for {missing}")
    if sum(s for _, s, _ in rows) != VACANCIES:
        raise IngestError(f"{source.id}: vacancies sum to {sum(s for _, s, _ in rows)}, expected {VACANCIES}")
    with conn:
        _source_row(conn, source, sha256)
        conn.execute("DELETE FROM stv_ballot WHERE election_id = ?", (eid,))
        for gss, seats, ballots in rows:
            conn.execute(
                "UPDATE contest SET seats = ? WHERE election_id = ? AND gss_code = ?", (seats, eid, gss)
            )
            conn.executemany(
                "INSERT INTO stv_ballot VALUES (?, ?, ?, ?, ?)",
                [(eid, gss, i, w, r) for i, (w, r) in enumerate(ballots, start=1)],
            )
    return len(rows)


def load_stage_pdf(conn, source: Source, path: Path, sha256: str, registry, layer=None, layers=None) -> int:
    """One ward's declared stage totals. The ward is identified by its candidates."""
    import pypdf

    text = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(path).pages)
    eid = source.election_id
    emb = _emb_candidates(conn, eid)
    m = re.search(r"Contest Name\s+(.+)", text)
    if not m:
        raise IngestError(f"{source.id}: no contest name")
    contest = m.group(1).strip()
    # The report prints candidate names as on the ballot; find the ward whose names all appear.
    folded = name_key(text)
    hits = [g for g, cands in emb.items() if all(name_key(n) in folded for _, n, _, _ in cands)]
    hits = [g for g in hits if len(emb[g]) == max(len(emb[h]) for h in hits)] if hits else []
    if len(hits) != 1:
        raise IngestError(f"{source.id}: {contest!r} matches {len(hits)} wards by candidate names")
    gss = hits[0]
    cands = emb[gss]
    rep = parse_stage_text(text, [n for _, n, _, _ in cands])
    valid, seats = conn.execute(
        "SELECT valid_votes, seats FROM contest WHERE election_id = ? AND gss_code = ?", (eid, gss)
    ).fetchone()
    if (rep.valid, rep.seats) != (valid, seats):
        raise IngestError(
            f"{source.id}: report says {rep.valid} valid, {rep.seats} seats; contest {valid}, {seats}"
        )
    if rep.quota != valid // (seats + 1) + 1:
        raise IngestError(f"{source.id}: quota {rep.quota} is not the Droop quota")
    if [v // SCALE for v in rep.stages[0][:-1]] != [v for _, _, v, _ in cands]:
        raise IngestError(f"{source.id}: stage 1 disagrees with the EMB first preferences")
    for k, row in enumerate(rep.stages, start=1):
        if sum(row) != valid * SCALE:
            raise IngestError(f"{source.id}: stage {k} sums to {sum(row)}, not {valid * SCALE}")
    with conn:
        _source_row(conn, source, sha256)
        conn.execute("DELETE FROM stv_stage WHERE election_id = ? AND gss_code = ?", (eid, gss))
        conn.executemany(
            "INSERT INTO stv_stage VALUES (?, ?, ?, ?, ?)",
            [
                (eid, gss, k, seq, v)
                for k, row in enumerate(rep.stages, start=1)
                for seq, v in zip([s for s, _, _, _ in cands] + [0], row, strict=True)
            ],
        )
    return len(rep.stages)
