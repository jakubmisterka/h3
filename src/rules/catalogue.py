"""The lists of towns and templates, loaded from the JSON files in `data/`.

Every entry has an `id` and a `name`; a kind of entry may require more fields (a template states
its `difficulty`). Other files and the bot's commands refer to entries by id; players may type the
id or the name, in any letter case.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from rules.difficulty import DIFFICULTY_GOLD, supported_difficulties
from rules.lobby_values import (
    check_computer_players,
    check_download,
    check_game_date,
    check_map_size,
    check_roads,
    check_text,
    has_underground,
)


class CatalogueError(ValueError):
    """A catalogue file is not valid. The message names the file and the entry."""


@dataclass(frozen=True)
class Entry:
    id: str
    name: str
    details: dict = field(default_factory=dict)  # the extra fields of this kind of entry, by name


# The extra fields each file requires besides id and name, with the type of each value.
TOWN_FIELDS: dict[str, type] = {}
TEMPLATE_FIELDS: dict[str, type] = {"difficulty": int}


@dataclass(frozen=True)
class Choice:
    """A fact with a default and the values a tournament may choose instead (roads, map size, computer players)."""

    default: object
    allowed: tuple


def _choice_of(check: Callable[[object], object]) -> Callable[[object], Choice]:
    """A reader for a fact written as {"default": ..., "allowed": [...]}, whose values `check` accepts."""

    def read(value: object) -> Choice:
        if not isinstance(value, dict) or set(value) != {"default", "allowed"}:
            raise ValueError('state it as {"default": ..., "allowed": [...]}')
        if not isinstance(value["allowed"], list) or not value["allowed"]:
            raise ValueError('"allowed" must be a list with at least one value')
        allowed = [check(item) for item in value["allowed"]]
        for position, item in enumerate(allowed):
            if item in allowed[:position]:
                raise ValueError(f"{item!r} is listed twice among the allowed values")
        default = check(value["default"])
        if default not in allowed:
            raise ValueError(f"the default {default!r} must be one of the allowed values: {', '.join(map(str, allowed))}")
        return Choice(default, tuple(allowed))

    return read


def _true(name: str, advice: str) -> Callable[[object], bool]:
    def read(value: object) -> bool:
        if value is not True:
            raise ValueError(f"{name} can only be true. {advice}")
        return True

    return read


def _mirror(value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError("mirror must be true or false")
    return value


# The facts a template may state besides id, name and difficulty. Each reader returns the value to keep, or raises
# ValueError with what is wrong. A fact that is not stated is unknown, and nothing is guessed in its place.
TEMPLATE_OPTIONAL: dict[str, Callable[[object], object]] = {
    "roads": _choice_of(check_roads),
    "map_size": _choice_of(check_map_size),
    "ai": _choice_of(check_computer_players),
    "sim_turns": check_game_date,
    "mirror": _mirror,
    "built_in": _true("built_in", "To say a template has to be downloaded, give a download link instead."),
    "download": check_download,
    "description": check_text,
    "additional_rules": check_text,
}


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


def parse_catalogue(
    data: object,
    label: str,
    extra_fields: dict[str, type] | None = None,
    optional_fields: dict[str, Callable[[object], object]] | None = None,
) -> Catalogue:
    """Build a catalogue from parsed JSON. `label` (the file name) is used in error messages.

    `extra_fields` are the fields every entry must have besides id and name. `optional_fields` are the fields an
    entry may have, each with a reader that returns the value to keep or raises ValueError; an entry has nothing
    else.
    """
    extra_fields = extra_fields or {}
    optional_fields = optional_fields or {}
    expected = {"id", "name", *extra_fields}
    expected_text = ", ".join(f'"{name}"' for name in ["id", "name", *extra_fields])
    may_have = ", ".join(f'"{name}"' for name in optional_fields)

    if not isinstance(data, list) or not data:
        raise CatalogueError(f"{label}: expected a non-empty list of entries")

    entries = []
    first_use = {}  # lowercase id -> number of the entry that used it first
    for number, raw in enumerate(data, start=1):
        if not isinstance(raw, dict) or not expected <= set(raw) <= expected | set(optional_fields):
            if optional_fields:
                raise CatalogueError(f"{label}: entry {number} must have {expected_text}, and may also have {may_have}")
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
        details = {key: raw[key] for key in extra_fields}
        for field_name, read in optional_fields.items():
            if field_name in raw:
                try:
                    details[field_name] = read(raw[field_name])
                except ValueError as e:
                    raise CatalogueError(f"{label}: entry {number} ({entry_id}): {field_name}: {e}") from e
        entries.append(Entry(entry_id, name, details))
    return Catalogue(entries)


def parse_templates(data: object, label: str) -> Catalogue:
    """Build the template catalogue: like any catalogue, and each template's difficulty must be a supported one."""
    catalogue = parse_catalogue(data, label, TEMPLATE_FIELDS, TEMPLATE_OPTIONAL)
    for number, entry in enumerate(catalogue.entries, start=1):
        where = f"{label}: entry {number} ({entry.id})"
        difficulty = entry.details["difficulty"]
        if difficulty not in DIFFICULTY_GOLD:
            raise CatalogueError(
                f"{where}: difficulty {difficulty} is not supported (use one of {supported_difficulties()})"
            )
        if "built_in" in entry.details and "download" in entry.details:
            raise CatalogueError(f"{where}: state only one of built_in and download")
        if entry.details.get("mirror"):
            sizes = entry.details.get("map_size")
            for size in (sizes.allowed if sizes else ()):
                if not has_underground(size):
                    raise CatalogueError(
                        f"{where}: map_size: a mirror template is always played with underground, "
                        f"but {size!r} has no +U"
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
