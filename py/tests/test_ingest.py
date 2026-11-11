import csv
import hashlib
import shutil
from pathlib import Path

import httpx
import pytest

from vsm_py.ingest import IngestError, commons
from vsm_py.ingest.cli import main, version_info
from vsm_py.ingest.fetch import ensure
from vsm_py.ingest.parties import Registry
from vsm_py.ingest.schema import connect
from vsm_py.ingest.sources import Source, load_sources

FIX = Path(__file__).parent / "fixtures"
CSV_BYTES = (FIX / "candidacies.csv").read_bytes()
CSV_SHA = hashlib.sha256(CSV_BYTES).hexdigest()


def source(**kw) -> Source:
    base = dict(
        id="t",
        url="https://example.invalid/c.csv",
        licence="OPL-3.0",
        sha256=CSV_SHA,
        file="t/c.csv",
        loader="commons_candidacies",
        redistributable=True,
        election_id="GE2024",
        office="commons",
        boundary_set="WM2023",
    )
    return Source(**(base | kw))


def mock_client(body: bytes = CSV_BYTES, status: int = 200) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status, content=body)))


@pytest.fixture
def registry() -> Registry:
    return Registry.load(FIX / "parties.toml")


# --- fetch -------------------------------------------------------------------------


def test_download_verifies_and_stores(tmp_path):
    p = ensure(source(), tmp_path, mock_client())
    assert p == tmp_path / "raw/t/c.csv" and p.read_bytes() == CSV_BYTES


def test_checksum_mismatch_stops_and_leaves_nothing(tmp_path):
    with pytest.raises(IngestError, match="checksum mismatch"):
        ensure(source(), tmp_path, mock_client(b"tampered"))
    assert list((tmp_path / "raw/t").iterdir()) == []


def test_existing_file_is_never_overwritten(tmp_path):
    dest = tmp_path / "raw/t/c.csv"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"old copy")
    with pytest.raises(IngestError, match="checksum mismatch"):
        ensure(source(), tmp_path, mock_client())
    assert dest.read_bytes() == b"old copy"


def test_archived_copy_used_when_offline(tmp_path):
    dest = tmp_path / "raw/t/c.csv"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(CSV_BYTES)
    assert ensure(source(), tmp_path, mock_client(status=503)) == dest


def test_offline_without_archive_stops(tmp_path):
    with pytest.raises(IngestError, match="download failed"):
        ensure(source(), tmp_path, mock_client(status=503))


def test_unpinned_source_reports_hash(tmp_path):
    with pytest.raises(IngestError, match=CSV_SHA):
        ensure(source(sha256=""), tmp_path, mock_client())


def test_private_sources_go_to_data_private(tmp_path):
    assert source(redistributable=False).path(tmp_path) == tmp_path / "private/t/c.csv"


def test_manual_source_must_be_placed(tmp_path):
    with pytest.raises(IngestError, match="by hand"):
        ensure(source(fetch="manual"), tmp_path)


# --- registry and parsing ------------------------------------------------------------


def test_unmapped_parties_are_all_listed(tmp_path):
    reg = Registry.load(FIX / "parties.toml")
    with pytest.raises(IngestError, match=r"(?s)Martian.*Venusian"):
        reg.map_all({"Labour", "Venusian", "Martian"})


def test_alias_clash_is_rejected():
    from vsm_py.ingest.parties import Party

    with pytest.raises(IngestError, match="maps to both"):
        Registry(
            [
                Party("IND", "Independent", ()),
                Party("SPK", "Speaker", ()),
                Party("A", "Alpha", ("X",)),
                Party("B", "Beta", ("X",)),
            ]
        )


def test_parse_maps_parties_and_independents(registry):
    _, contests = commons.parse(FIX / "candidacies.csv", registry)
    testford = next(c for c in contests if c.gss == "E14000001")
    assert testford.candidates == [(1, "LAB", 120), (2, "CON", 60), (3, "IND", 20)]
    assert testford.nation == "E" and testford.region == "South East"
    orkney = next(c for c in contests if c.gss == "S14000001")
    assert orkney.declared_at == "2024-07-05T03:10:00" and orkney.region == "Scotland"


def _rewrite(tmp_path, change) -> Path:
    rows = list(csv.DictReader((FIX / "candidacies.csv").open(encoding="utf-8")))
    change(rows)
    out = tmp_path / "c.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return out


def test_vote_total_disagreement_stops(tmp_path, registry):
    path = _rewrite(tmp_path, lambda rows: rows[0].update({"Candidate vote count": "121"}))
    with pytest.raises(IngestError, match="sum to 201"):
        commons.parse(path, registry)


def test_grand_total_disagreement_stops(tmp_path, registry):
    def change(rows):
        for r in rows:
            r["Total valid votes in general election"] = "301"

    with pytest.raises(IngestError, match="file total 301"):
        commons.parse(_rewrite(tmp_path, change), registry)


# --- load ------------------------------------------------------------------------------


def test_load_writes_tables_and_reruns_cleanly(tmp_path, registry):
    conn = connect(tmp_path / "ref.sqlite")
    src = source(reference_electorate=False)
    for _ in range(2):
        assert commons.load(conn, src, FIX / "candidacies.csv", CSV_SHA, registry) == 2
    assert conn.execute("SELECT COUNT(*) FROM candidate_result").fetchone()[0] == 5
    winners = conn.execute(
        "SELECT gss_code, party_code FROM candidate_result WHERE elected = 1 ORDER BY gss_code"
    ).fetchall()
    assert winners == [("E14000001", "LAB"), ("S14000001", "LD")]
    assert conn.execute("SELECT COUNT(*) FROM constituency").fetchone()[0] == 0  # not the reference election
    assert conn.execute("SELECT licence, redistributable FROM source").fetchone() == ("OPL-3.0", 1)


def test_reference_electorate_requires_all_protected_seats(tmp_path, registry):
    conn = connect(tmp_path / "ref.sqlite")
    with pytest.raises(IngestError, match="protected seats not found"):
        commons.load(conn, source(reference_electorate=True), FIX / "candidacies.csv", CSV_SHA, registry)
    assert conn.execute("SELECT COUNT(*) FROM election").fetchone()[0] == 0


# --- manifest and CLI ----------------------------------------------------------------


def test_repository_manifest_and_registry_load():
    data = Path(__file__).resolve().parents[2] / "data"
    sources = load_sources(data / "sources.toml")
    assert {s.election_id for s in sources} >= {"GE2024", "GE2019N"}
    assert all(len(s.sha256) == 64 for s in sources)
    reg = Registry.load(data / "parties.toml")
    assert {"LAB", "CON", "LD", "REF", "GRN", "SNP", "PC"} <= {p.code for p in reg.parties}


def test_cli_run_on_fixture(tmp_path, capsys, monkeypatch):
    (tmp_path / "raw/t").mkdir(parents=True)
    shutil.copy(FIX / "candidacies.csv", tmp_path / "raw/t/c.csv")
    shutil.copy(FIX / "parties.toml", tmp_path / "parties.toml")
    (tmp_path / "sources.toml").write_text(
        '[[source]]\nid = "t"\nurl = "https://example.invalid"\nlicence = "OPL-3.0"\n'
        f'sha256 = "{CSV_SHA}"\nfile = "t/c.csv"\nloader = "commons_candidacies"\n'
        'redistributable = true\nelection_id = "GE2024"\noffice = "commons"\nboundary_set = "WM2023"\n'
    )
    assert main(["run", "--data-dir", str(tmp_path)]) == 0
    assert "t: 2 contests" in capsys.readouterr().out


def test_version_json(monkeypatch):
    monkeypatch.setenv("VSM_ENV", "dev")
    info = version_info()
    assert info["version"] == "0.1.0" and info["environment"] == "dev" and info["commit"]
