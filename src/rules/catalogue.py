"""Shared lists of factions (towns) and templates, loaded from the JSON files in data/.

Both files have the same shape: a list of {"id": ..., "name": ...}. Formats and
commands refer to entries by id; players may type the id or the name.
"""

import json
from dataclasses import dataclass
from pathlib import Path


class CatalogueError(ValueError):
    """A catalogue file is not valid."""


@dataclass(frozen=True)
class Entry:
    id: str
    name: str


class Catalogue:
    def __init__(self, entries: list[Entry]):
        self.entries = tuple(entries)
        self._by_key = {}
        for entry in self.entries:
            self._by_key[entry.id.lower()] = entry
            self._by_key[entry.name.lower()] = entry

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(e.id for e in self.entries)

    def __contains__(self, entry_id: str) -> bool:
        return any(e.id == entry_id for e in self.entries)

    def find(self, text: str) -> Entry | None:
        """Find an entry by id or name, ignoring case."""
        return self._by_key.get(text.strip().lower())

    def name_of(self, entry_id: str) -> str:
        return next(e.name for e in self.entries if e.id == entry_id)


def parse_catalogue(data: object, label: str) -> Catalogue:
    """Build a catalogue from parsed JSON, or raise CatalogueError naming the problem."""
    if not isinstance(data, list) or not data:
        raise CatalogueError(f"{label}: expected a non-empty list of entries")

    entries: list[Entry] = []
    seen: set[str] = set()
    for i, raw in enumerate(data, start=1):
        if not isinstance(raw, dict) or set(raw) != {"id", "name"}:
            raise CatalogueError(f'{label}: entry {i} must have exactly "id" and "name"')
        entry_id, name = raw["id"], raw["name"]
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise CatalogueError(f"{label}: entry {i} has an empty id")
        if not isinstance(name, str) or not name.strip():
            raise CatalogueError(f"{label}: entry {i} ({entry_id}) has an empty name")
        if entry_id.lower() in seen:
            raise CatalogueError(f"{label}: duplicate id {entry_id!r}")
        seen.add(entry_id.lower())
        entries.append(Entry(entry_id, name))
    return Catalogue(entries)


def load_catalogue(path: Path) -> Catalogue:
    with open(path, encoding="utf-8") as f:
        return parse_catalogue(json.load(f), path.name)
