"""The source manifest, data/sources.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import IngestError

# "boundaries" sources are fetched and verified here, then read by the geography stage.
LOADERS = {"commons_candidacies", "boundaries", "ons_wd_pcon_lad_lookup"}


@dataclass(frozen=True)
class Source:
    id: str
    url: str
    licence: str
    sha256: str
    file: str
    loader: str
    redistributable: bool
    fetch: str = "http"  # "http" or "manual" (placed by hand, e.g. BES files)
    election_id: str | None = None
    office: str | None = None
    boundary_set: str | None = None
    # The election whose electorates define constituency.electorate.
    reference_electorate: bool = False
    # Geography layer (data/geographies.toml) whose GSS codes this source uses.
    layer: str | None = None

    def path(self, data_dir: Path) -> Path:
        base = "raw" if self.redistributable else "private"
        return data_dir / base / self.file


def load_sources(path: Path) -> list[Source]:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    out: list[Source] = []
    seen: set[str] = set()
    for entry in raw.get("source", []):
        try:
            src = Source(**entry)
        except TypeError as e:
            raise IngestError(f"{path}: bad source entry {entry.get('id', '?')}: {e}") from e
        if src.id in seen:
            raise IngestError(f"{path}: duplicate source id {src.id}")
        if src.loader not in LOADERS:
            raise IngestError(f"{path}: source {src.id} has unknown loader {src.loader}")
        if src.fetch not in {"http", "manual"}:
            raise IngestError(f"{path}: source {src.id} has unknown fetch mode {src.fetch}")
        seen.add(src.id)
        out.append(src)
    return out
