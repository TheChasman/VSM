"""The geography register, data/geographies.toml (ADR-0014)."""

from __future__ import annotations

import json
import re
import sqlite3
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import IngestError
from .sources import Source

GSS = re.compile(r"^[ENSWK]\d{8}$")


@dataclass(frozen=True)
class Layer:
    id: str
    description: str
    gss_prefixes: tuple[str, ...]
    drawn_by: tuple[str, ...]
    valid_from: str
    source: str
    profiles: tuple[str, ...]
    valid_to: str | None = None

    def admits(self, code: str) -> bool:
        return bool(GSS.match(code)) and code[:3] in self.gss_prefixes


def load_register(path: Path, sources: list[Source]) -> dict[str, Layer]:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    by_id = {s.id: s for s in sources}
    layers: dict[str, Layer] = {}
    for e in raw.get("layer", []):
        layer = Layer(
            id=e["id"],
            description=e["description"],
            gss_prefixes=tuple(e["gss_prefixes"]),
            drawn_by=tuple(e["drawn_by"]),
            valid_from=e["valid_from"],
            source=e["source"],
            profiles=tuple(e.get("profiles", [])),
            valid_to=e.get("valid_to"),
        )
        where = f"{path}: layer {layer.id}"
        if layer.id in layers:
            raise IngestError(f"{where}: duplicate id")
        if not layer.gss_prefixes or any(not re.fullmatch(r"[ENSWK]\d\d", p) for p in layer.gss_prefixes):
            raise IngestError(f"{where}: gss_prefixes must be like E14")
        for field in ("valid_from", "valid_to"):
            value = getattr(layer, field)
            if value is not None:
                try:
                    date.fromisoformat(value)
                except ValueError as err:
                    raise IngestError(f"{where}: {field} {value!r} is not an ISO date") from err
        if layer.source not in by_id:
            raise IngestError(f"{where}: source {layer.source} is not in sources.toml")
        layers[layer.id] = layer

    for s in sources:
        if s.layer is None:
            if s.loader == "boundaries":
                raise IngestError(f"source {s.id}: boundary sources must name a registered layer")
            continue
        if s.layer not in layers:
            raise IngestError(f"source {s.id}: layer {s.layer} is not in {path.name} (ADR-0014)")
    return layers


def write_register(conn: sqlite3.Connection, layers: dict[str, Layer]) -> None:
    with conn:
        conn.execute("DELETE FROM geography_layer")
        conn.executemany(
            "INSERT INTO geography_layer VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    lay.id,
                    lay.description,
                    json.dumps(list(lay.gss_prefixes)),
                    json.dumps(list(lay.drawn_by)),
                    lay.valid_from,
                    lay.valid_to,
                    lay.source,
                )
                for lay in layers.values()
            ],
        )


def check_codes(layer: Layer, codes: set[str], what: str) -> None:
    bad = sorted(c for c in codes if not layer.admits(c))
    if bad:
        shown = ", ".join(bad[:10]) + (" …" if len(bad) > 10 else "")
        raise IngestError(
            f"{what}: {len(bad)} codes outside layer {layer.id} {list(layer.gss_prefixes)}: {shown}"
        )
