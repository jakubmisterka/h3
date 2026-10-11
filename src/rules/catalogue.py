"""The lists of towns and templates, loaded from the JSON files in `data/`.

Every entry has an `id` and a `name`; a kind of entry may require more fields (a template states
its `difficulty`). Other files and the bot's commands refer to entries by id; players may type the
id or the name, in any letter case.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from rules.difficulty import DIFFICULTY_GOLD, supported_difficulties


class CatalogueError(ValueError):
    """A catalogue file is not valid. The message names the file and the entry."""


@dataclass(frozen=True)
class Entry:
    id: str
    name: str
    details: dict = field(default_factory=dict)  # the extra fields of this kind of entry, by name


# The extra fields each file requires besides id and name, with the type of each value.
# A new field for templates (a timer, a download link) is added here.
TOWN_FIELDS: dict[str, type] = {}
TEMPLATE_FIELDS: dict[str, type] = {"difficulty": int}


class Catalogue:
    def __init__(self, entries: list[Entry]):
        self.entries = tuple(entries)
        self._by_text = {}
        for entry in self.entries:
            self._by_text[entry.id.lower()] = entry
            self._by_text[entry.name.lower()] = entry

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(entry.id for entry in self.entries)

    def __contains__(self, entry_id: str) -> bool:
        return entry_id in self.ids

    def find(self, text: str) -> Entry | None:
        """Find an entry by id or name, ignoring letter case and spaces around the text."""
        return self._by_text.get(text.strip().lower())


_TYPE_WORDS = {int: "whole number", str: "text"}


def _is_a(value, expected: type) -> bool:
    if expected is int:
        return isinstance(value, int) and not isinstance(value, bool)  # True is not a whole number here
    return isinstance(value, expected)


def parse_catalogue(data: object, label: str, extra_fields: dict[str, type] | None = None) -> Catalogue:
    """Build a catalogue from parsed JSON. `label` (the file name) is used in error messages.

    `extra_fields` are the fields every entry must have besides id and name.
    """
    extra_fields = extra_fields or {}
    expected = {"id", "name", *extra_fields}
    expected_text = ", ".join(f'"{name}"' for name in ["id", "name", *extra_fields])

    if not isinstance(data, list) or not data:
        raise CatalogueError(f"{label}: expected a non-empty list of entries")

    entries = []
    first_use = {}  # lowercase id -> number of the entry that used it first
    for number, raw in enumerate(data, start=1):
        if not isinstance(raw, dict) or set(raw) != expected:
            raise CatalogueError(f"{label}: entry {number} must have exactly {expected_text}")
        entry_id, name = raw["id"], raw["name"]
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise CatalogueError(f"{label}: entry {number} has an empty id")
        if not isinstance(name, str) or not name.strip():
            raise CatalogueError(f"{label}: entry {number} ({entry_id}) has an empty name")
        if entry_id.lower() in first_use:
            raise CatalogueError(
                f"{label}: entry {number}: the id {entry_id!r} is already used by entry {first_use[entry_id.lower()]}"
            )
        first_use[entry_id.lower()] = number
        for field_name, field_type in extra_fields.items():
            if not _is_a(raw[field_name], field_type):
                raise CatalogueError(
                    f"{label}: entry {number} ({entry_id}): {field_name!r} must be a "
                    f"{_TYPE_WORDS.get(field_type, field_type.__name__)}, not {raw[field_name]!r}"
                )
        entries.append(Entry(entry_id, name, {key: raw[key] for key in extra_fields}))
    return Catalogue(entries)


def parse_templates(data: object, label: str) -> Catalogue:
    """Build the template catalogue: like any catalogue, and each template's difficulty must be a supported one."""
    catalogue = parse_catalogue(data, label, TEMPLATE_FIELDS)
    for number, entry in enumerate(catalogue.entries, start=1):
        difficulty = entry.details["difficulty"]
        if difficulty not in DIFFICULTY_GOLD:
            raise CatalogueError(
                f"{label}: entry {number} ({entry.id}): difficulty {difficulty} is not supported "
                f"(use one of {supported_difficulties()})"
            )
    return catalogue


def _read_json(path: Path) -> object:
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise CatalogueError(f"{path.name}: not valid JSON ({e})") from e


def load_catalogue(path: Path, extra_fields: dict[str, type] | None = None) -> Catalogue:
    return parse_catalogue(_read_json(path), path.name, extra_fields)


def load_towns(path: Path) -> Catalogue:
    return load_catalogue(path, TOWN_FIELDS)


def load_templates(path: Path) -> Catalogue:
    return parse_templates(_read_json(path), path.name)
