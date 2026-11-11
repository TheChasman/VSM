import csv
import hashlib
import shutil
import sqlite3
from pathlib import Path

import httpx
import pytest

from vsm_py.ingest import IngestError, commons
from vsm_py.ingest.cli import main, version_info
from vsm_py.ingest.fetch import ensure
from vsm_py.ingest.parties import Registry
from vsm_py.ingest.register import load_register, write_register
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
        'layer = "PCON2024"\n'
    )
    (tmp_path / "geographies.toml").write_text(REGISTER)
    assert main(["run", "--data-dir", str(tmp_path)]) == 0
    assert "t: 2 contests" in capsys.readouterr().out
    with sqlite3.connect(tmp_path / "reference.sqlite") as conn:
        assert conn.execute("SELECT layer_id FROM geography_layer").fetchall() == [("PCON2024",)]


def test_codes_outside_the_layer_stop_ingest(tmp_path, registry):
    layers = load_register(_register(tmp_path, '["W07"]'), [source(layer="PCON2024")])
    conn = connect(tmp_path / "ref.sqlite")
    with pytest.raises(IngestError, match=r"2 codes outside layer PCON2024.*E14000001, S14000001"):
        commons.load(conn, source(), FIX / "candidacies.csv", CSV_SHA, registry, layers["PCON2024"])


def test_register_rejects_unregistered_layers_and_bad_entries(tmp_path):
    reg = _register(tmp_path)
    with pytest.raises(IngestError, match="layer LAD2024 is not in geographies.toml"):
        load_register(reg, [source(layer="LAD2024")])
    with pytest.raises(IngestError, match="boundary sources must name a registered layer"):
        load_register(reg, [source(loader="boundaries")])
    with pytest.raises(IngestError, match="source t is not in sources.toml"):
        load_register(reg, [source(id="other")])
    with pytest.raises(IngestError, match="must be like E14"):
        load_register(_register(tmp_path, '["E1"]'), [source()])


def test_register_admits_by_prefix_and_shape(tmp_path):
    layer = load_register(_register(tmp_path), [source()])["PCON2024"]
    assert layer.admits("E14000001") and layer.admits("S14000001")
    assert not layer.admits("E05000001") and not layer.admits("E14")


REGISTER = (
    '[[layer]]\nid = "PCON2024"\ndescription = "t"\ngss_prefixes = ["E14", "S14"]\ndrawn_by = ["BCE"]\n'
    'valid_from = "2024-05-31"\nsource = "t"\n'
)


def _register(tmp_path: Path, prefixes: str = '["E14", "S14"]') -> Path:
    p = tmp_path / "geographies.toml"
    p.write_text(REGISTER.replace('["E14", "S14"]', prefixes))
    return p


def test_version_json(monkeypatch):
    monkeypatch.setenv("VSM_ENV", "dev")
    info = version_info()
    assert info["version"] == "0.1.0" and info["environment"] == "dev" and info["commit"]


# --- ONS ward lookup ----------------------------------------------------------------------

LOOKUP_HEADER = "WD24CD,WD24NM,PCON24CD,PCON24NM,LAD24CD,LAD24NM,SPLIT_WARD\n"
LOOKUP_LAYERS = """
[[layer]]
id = "PCON2024"
description = "c"
gss_prefixes = ["E14"]
drawn_by = ["BCE"]
valid_from = "2024-05-31"
source = "lu"

[[layer]]
id = "WD20240704"
description = "w"
gss_prefixes = ["E05"]
drawn_by = ["LGBCE"]
valid_from = "2024-07-04"
source = "lu"

[[layer]]
id = "LAD20240704"
description = "l"
gss_prefixes = ["E06", "E07"]
drawn_by = ["Parliament"]
valid_from = "2024-07-04"
source = "lu"
"""


def _lookup(tmp_path, body: str):
    from vsm_py.ingest import lookups

    (tmp_path / "geographies.toml").write_text(LOOKUP_LAYERS)
    src = source(id="lu", loader="ons_wd_pcon_lad_lookup", layer="WD20240704")
    layers = load_register(tmp_path / "geographies.toml", [src])
    path = tmp_path / "lu.csv"
    path.write_text(LOOKUP_HEADER + body)
    conn = connect(tmp_path / "ref.sqlite")
    write_register(conn, layers)
    n = lookups.load_wd_pcon_lad(conn, src, path, "x", None, layers["WD20240704"], layers)
    return n, conn


def test_lookup_links_exact_and_partial(tmp_path):
    n, conn = _lookup(
        tmp_path,
        "E05000001,A,E14000001,P1,E07000001,L1,\n"
        "E05000002,B,E14000001,P1,E07000001,L1,Yes\n"
        "E05000002,B,E14000002,P2,E07000001,L1,Yes\n",
    )
    assert n == 2
    rows = conn.execute(
        "SELECT from_code, to_code, relation, share FROM geography_link"
        " WHERE to_layer = 'PCON2024' ORDER BY 1, 2"
    ).fetchall()
    assert rows == [
        ("E05000001", "E14000001", "exact", 1.0),
        ("E05000002", "E14000001", "partial", None),
        ("E05000002", "E14000002", "partial", None),
    ]
    assert (
        conn.execute("SELECT COUNT(*) FROM geography_link WHERE to_layer = 'LAD20240704'").fetchone()[0] == 2
    )


def test_lookup_flagged_lone_ward_is_partial_not_exact(tmp_path, capsys):
    _, conn = _lookup(tmp_path, "E05000003,C,E14000001,P1,E07000001,L1,TRUE\n")
    assert conn.execute("SELECT relation FROM geography_link WHERE to_layer = 'PCON2024'").fetchone() == (
        "partial",
    )
    assert "E05000003 flagged split" in capsys.readouterr().err


def test_lookup_unflagged_split_and_cross_authority_wards_stop(tmp_path):
    with pytest.raises(IngestError, match="not flagged split"):
        _lookup(tmp_path, "E05000004,D,E14000001,P1,E07000001,L1,\nE05000004,D,E14000002,P2,E07000001,L1,\n")
    with pytest.raises(IngestError, match="more than one local authority"):
        _lookup(tmp_path, "E05000005,E,E14000001,P1,E07000001,L1,\nE05000005,E,E14000001,P1,E06000001,L2,\n")


def test_partial_links_cannot_carry_a_share(tmp_path):
    conn = connect(tmp_path / "ref.sqlite")
    conn.execute("INSERT INTO geography_layer VALUES ('A', 'a', '[]', '[]', '2024-01-01', NULL, 's')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO geography_link VALUES ('A', 'x', 'A', 'y', 'partial', 0.5, 0)")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO geography_link VALUES ('A', 'x', 'A', 'y', 'exact', NULL, 0)")


def test_register_rewrite_keeps_referenced_layers(tmp_path):
    from vsm_py.ingest.register import write_register

    layers = load_register(_register(tmp_path), [source()])
    conn = connect(tmp_path / "ref.sqlite")
    write_register(conn, layers)
    conn.execute("INSERT INTO area VALUES ('PCON2024', 'E14000001', 'A')")
    conn.commit()
    write_register(conn, layers)  # second run must not trip the foreign key
    assert conn.execute("SELECT COUNT(*) FROM area").fetchone()[0] == 1
