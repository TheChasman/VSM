import geopandas as gpd
import pytest
from shapely.geometry import box

from vsm_py.geography import GeographyError
from vsm_py.geography.build import (
    BNG,
    Edge,
    areas_km2,
    check_areas,
    check_connected,
    components,
    land_edges,
    load_crossings,
)


def grid() -> gpd.GeoDataFrame:
    # Three 10 km squares in a row (A, B, C), D touching C only at a corner, and an island E.
    km = 1000
    shapes = {
        "E1": box(0, 0, 10 * km, 10 * km),
        "E2": box(10 * km, 0, 20 * km, 10 * km),
        "E3": box(20 * km, 0, 30 * km, 10 * km),
        "E4": box(30 * km, 10 * km, 40 * km, 20 * km),
        "E5": box(100 * km, 100 * km, 105 * km, 105 * km),
    }
    return gpd.GeoDataFrame(
        {"gss_code": list(shapes), "name": [f"Seat {c}" for c in shapes]},
        geometry=list(shapes.values()),
        crs=BNG,
    )


NAMES = {f"E{i}": f"Seat E{i}" for i in range(1, 6)}


def test_areas_in_square_km():
    a = areas_km2(grid())
    assert a["E1"] == pytest.approx(100.0) and a["E5"] == pytest.approx(25.0)


def test_northern_ireland_uses_irish_grid():
    # A 10 km square in BNG near Belfast, measured in Irish Grid, differs slightly from 100 km².
    g = gpd.GeoDataFrame(
        {"gss_code": ["N1"], "name": ["NI"]}, geometry=[box(330e3, 530e3, 340e3, 540e3)], crs=BNG
    )
    a = areas_km2(g)["N1"]
    assert a != pytest.approx(100.0, abs=1e-9) and a == pytest.approx(100.0, rel=0.01)


def test_land_edges_need_a_shared_line_not_a_point():
    edges = {(e.gss_a, e.gss_b) for e in land_edges(grid())}
    assert edges == {("E1", "E2"), ("E2", "E3")}  # E3–E4 touch at a corner only


def test_disconnected_seats_must_be_declared():
    edges = land_edges(grid())
    with pytest.raises(GeographyError, match=r"(?s)E4 \(Seat E4\).*E5 \(Seat E5\)"):
        check_connected(sorted(NAMES), edges, NAMES)
    edges += [Edge("E3", "E4", "declared_crossing"), Edge("E4", "E5", "declared_crossing")]
    check_connected(sorted(NAMES), edges, NAMES)


def test_northern_ireland_is_checked_separately_from_gb():
    names = {"E1": "a", "E2": "b", "N1": "c", "N2": "d"}
    check_connected(sorted(names), [Edge("E1", "E2", "land"), Edge("N1", "N2", "land")], names)


def test_crossings_file_checks_names(tmp_path):
    p = tmp_path / "crossings.toml"
    p.write_text('[[crossing]]\na = "E5"\na_name = "Seat E5"\nb = "E4"\nb_name = "Seat E4"\nvia = "ferry"\n')
    (edge,) = load_crossings(p, NAMES)
    assert (edge.gss_a, edge.gss_b, edge.kind, edge.note) == ("E4", "E5", "declared_crossing", "ferry")
    p.write_text('[[crossing]]\na = "E5"\na_name = "Wrong"\nb = "E4"\nb_name = "Seat E4"\nvia = "ferry"\n')
    with pytest.raises(GeographyError, match="not 'Wrong'"):
        load_crossings(p, NAMES)


def test_area_reference_thresholds(tmp_path):
    p = tmp_path / "ref.toml"
    areas = {"E1": 100.0}
    p.write_text('[[seat]]\ngss_code = "E1"\nname = "Seat E1"\narea_km2 = 102.0\n')
    assert len(check_areas(areas, NAMES, p)) == 1  # 1.96 %: warn
    p.write_text('[[seat]]\ngss_code = "E1"\nname = "Seat E1"\narea_km2 = 110.0\n')
    with pytest.raises(GeographyError, match="9.09 %"):
        check_areas(areas, NAMES, p)


def test_components_largest_first():
    assert components(["a", "b", "c"], [Edge("a", "b", "land")]) == [["a", "b"], ["c"]]
