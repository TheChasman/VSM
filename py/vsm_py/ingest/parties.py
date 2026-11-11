"""Project party registry, data/parties.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import IngestError

INDEPENDENT = "IND"
SPEAKER = "SPK"


@dataclass(frozen=True)
class Party:
    code: str
    name: str
    aliases: tuple[str, ...]


class Registry:
    def __init__(self, parties: list[Party]):
        self.parties = parties
        self._by_alias: dict[str, str] = {}
        codes: set[str] = set()
        for p in parties:
            if p.code in codes:
                raise IngestError(f"party registry: duplicate code {p.code}")
            codes.add(p.code)
            for alias in (p.name, *p.aliases):
                prior = self._by_alias.setdefault(alias, p.code)
                if prior != p.code:
                    raise IngestError(f"party registry: {alias!r} maps to both {prior} and {p.code}")
        for required in (INDEPENDENT, SPEAKER):
            if required not in codes:
                raise IngestError(f"party registry: missing required code {required}")

    @classmethod
    def load(cls, path: Path) -> Registry:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        return cls([Party(e["code"], e["name"], tuple(e.get("aliases", []))) for e in raw.get("party", [])])

    def lookup(self, name: str) -> str | None:
        return self._by_alias.get(name)

    def map_all(self, names: set[str]) -> dict[str, str]:
        """Map every name or stop, listing all unmapped spellings at once."""
        missing = sorted(n for n in names if n not in self._by_alias)
        if missing:
            listed = "\n  ".join(missing)
            raise IngestError(f"unmapped party names; add aliases to data/parties.toml:\n  {listed}")
        return {n: self._by_alias[n] for n in names}
