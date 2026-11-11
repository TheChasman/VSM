"""Areas, land adjacency, declared crossings and connectivity checks."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import shapely

from . import GeographyError

BNG = 27700
IRISH_GRID = 29902
WARN_PCT = 1.0
FAIL_PCT = 5.0


@dataclass(frozen=True)
class Edge:
    gss_a: str
    gss_b: str
    kind: str  # "land" or "declared_crossing"
    shared_m: float | None = None
    note: str | None = None

    def __post_init__(self):
        if not self.gss_a < self.gss_b:
            raise ValueError(f"edge must be ordered: {self.gss_a} < {self.gss_b}")


def read_boundaries(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None or gdf.crs.to_epsg() != BNG:
        # ArcGIS GeoJSON with outSR=27700 carries BNG coordinates; some readers lose the CRS.
        gdf = gdf.set_crs(BNG, allow_override=True)
    gdf = gdf.rename(columns={"PCON24CD": "gss_code", "PCON24NM": "name"})
    missing = {"gss_code", "name"} - set(gdf.columns)
    if missing:
        raise GeographyError(f"{path}: missing columns {sorted(missing)}")
    if gdf["gss_code"].duplicated().any():
        raise GeographyError(f"{path}: duplicate GSS codes")
    gdf["geometry"] = shapely.make_valid(gdf.geometry.values)
    return gdf.sort_values("gss_code").reset_index(drop=True)


def areas_km2(gdf: gpd.GeoDataFrame) -> dict[str, float]:
    ni = gdf["gss_code"].str.startswith("N")
    out: dict[str, float] = {}
    for part, epsg in ((gdf[~ni], BNG), (gdf[ni], IRISH_GRID)):
        if part.empty:
            continue
        projected = part.to_crs(epsg) if epsg != BNG else part
        for gss, area in zip(projected["gss_code"], projected.geometry.area, strict=True):
            out[gss] = area / 1e6
    return out


def land_edges(gdf: gpd.GeoDataFrame) -> list[Edge]:
    """Pairs whose shared boundary is longer than zero (a single touching point is not contiguity)."""
    geoms = gdf.geometry.values
    codes = gdf["gss_code"].tolist()
    left, right = shapely.STRtree(geoms).query(geoms, predicate="intersects")
    edges = []
    for i, j in zip(left, right, strict=True):
        if i >= j:
            continue
        shared = shapely.intersection(shapely.boundary(geoms[i]), shapely.boundary(geoms[j]))
        length = shapely.length(shared)
        if length > 0:
            a, b = sorted((codes[i], codes[j]))
            edges.append(Edge(a, b, "land", shared_m=float(length)))
    return edges


def load_crossings(path: Path, names: dict[str, str]) -> list[Edge]:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    edges = []
    for c in raw.get("crossing", []):
        for side in ("a", "b"):
            gss, name = c[side], c[f"{side}_name"]
            if names.get(gss) != name:
                raise GeographyError(f"{path}: {gss} is {names.get(gss)!r}, not {name!r}")
        a, b = sorted((c["a"], c["b"]))
        edges.append(Edge(a, b, "declared_crossing", note=c["via"]))
    return edges


def components(nodes: list[str], edges: list[Edge]) -> list[list[str]]:
    parent = {n: n for n in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in edges:
        parent[find(e.gss_a)] = find(e.gss_b)
    groups: dict[str, list[str]] = {}
    for n in nodes:
        groups.setdefault(find(n), []).append(n)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: (-len(g), g[0]))


def check_connected(codes: list[str], edges: list[Edge], names: dict[str, str]) -> None:
    """Great Britain and Northern Ireland must each be one connected graph."""
    for label, members in (
        ("Great Britain", [c for c in codes if not c.startswith("N")]),
        ("Northern Ireland", [c for c in codes if c.startswith("N")]),
    ):
        if not members:
            continue
        keep = set(members)
        parts = components(members, [e for e in edges if e.gss_a in keep and e.gss_b in keep])
        if len(parts) > 1:
            detached = "\n  ".join(", ".join(f"{g} ({names[g]})" for g in part) for part in parts[1:])
            raise GeographyError(
                f"{label} graph has {len(parts)} components. Declare crossings in data/crossings.toml for:\n"
                f"  {detached}"
            )


def check_areas(areas: dict[str, float], names: dict[str, str], reference: Path) -> list[str]:
    """Compare against reference figures: warn above 1 %, fail above 5 %."""
    raw = tomllib.loads(reference.read_text(encoding="utf-8"))
    warnings = []
    for ref in raw.get("seat", []):
        gss = ref["gss_code"]
        if names.get(gss) != ref["name"]:
            raise GeographyError(f"{reference}: {gss} is {names.get(gss)!r}, not {ref['name']!r}")
        got, want = areas[gss], ref["area_km2"]
        pct = abs(got - want) / want * 100
        msg = f"{ref['name']}: {got:,.1f} km² vs reference {want:,.1f} km² ({pct:.2f} %)"
        if pct > FAIL_PCT:
            raise GeographyError(msg)
        if pct > WARN_PCT:
            warnings.append(msg)
    return warnings
