"""The lists of towns and templates, loaded from the JSON files in `data/`.

Every entry has an `id` and a `name`; a kind of entry may require more fields (a template states
its `difficulty`). Other files and the bot's commands refer to entries by id; players may type the
id or the name, in any letter case.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from rules.trade_kinds import check_trade
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
HERO_FIELDS: dict[str, type] = {"town": str, "link": str}  # the id of the hero's town, and the page that describes the hero


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


def _flag(name: str) -> Callable[[object], bool]:
    def read(value: object) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be true or false")
        return value

    return read


_mirror = _flag("mirror")


def _hero_list(value: object) -> tuple[str, ...]:
    """A list of heroes (as written: an id or a name), each once. Whether they exist is checked with the heroes."""
    if not isinstance(value, list) or not value:
        raise ValueError("state it as a list with at least one hero")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError("every hero is written as text, the id or the name of a hero of data/heroes.json")
    for position, item in enumerate(value):
        if item.strip().lower() in [other.strip().lower() for other in value[:position]]:
            raise ValueError(f"{item!r} is listed twice")
    return tuple(value)


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
    "trade": check_trade,
    "banned_heroes": _hero_list,
    "allowed_heroes": _hero_list,
}

# The facts a hero may state besides id, name, town and link; left out, each means false. The shipped file states
# campaign_hero and banned_by_default for every hero, and banned_on_mirrors where it is true.
DEFAULT_BAN_FLAGS = (
    "campaign_hero",  # comes with a campaign and is not playable unless a map enables them (information; they are also banned)
    "banned_by_default",  # banned in every template pack, as HotA's template editor bans them
    "banned_on_mirrors",  # banned on a mirror template
)
HERO_OPTIONAL: dict[str, Callable[[object], object]] = {flag: _flag(flag) for flag in DEFAULT_BAN_FLAGS}


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


def parse_templates(data: object, label: str, heroes: Catalogue | None = None) -> Catalogue:
    """Build the template catalogue: like any catalogue, and each template's difficulty must be a supported one.

    With the hero catalogue (`heroes`), the heroes a template lists as banned must exist; they are kept as ids."""
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
        if heroes is not None and "banned_heroes" in entry.details:
            entry.details["banned_heroes"] = _hero_ids(where, "banned_heroes", entry.details["banned_heroes"], heroes)
        if heroes is not None and "allowed_heroes" in entry.details:
            allowed = _hero_ids(where, "allowed_heroes", entry.details["allowed_heroes"], heroes)
            for hero_id in allowed:
                hero = heroes.find(hero_id)
                if not (hero.details.get("banned_by_default") or hero.details.get("banned_on_mirrors")):
                    raise CatalogueError(
                        f"{where}: allowed_heroes: {hero.name} is not banned by default, "
                        f"so it needs no permission (leave it out of the list)"
                    )
                if hero_id in entry.details.get("banned_heroes", ()):
                    raise CatalogueError(f"{where}: {hero.name} is both in banned_heroes and in allowed_heroes")
            entry.details["allowed_heroes"] = allowed
        trade = entry.details.get("trade")
        if trade is not None and trade.has_packs and entry.details.get("mirror"):
            raise CatalogueError(f"{where}: trade: a mirror template cannot have computer-player packs")
        if entry.details.get("mirror"):
            sizes = entry.details.get("map_size")
            for size in (sizes.allowed if sizes else ()):
                if not has_underground(size):
                    raise CatalogueError(
                        f"{where}: map_size: a mirror template is always played with underground, "
                        f"but {size!r} has no +U"
                    )
    return catalogue


def _hero_ids(where: str, field_name: str, listed: tuple[str, ...], heroes: Catalogue) -> tuple[str, ...]:
    """The ids of the heroes a template lists, whether it wrote ids or names. Raises CatalogueError for an unknown hero."""
    ids = []
    for text in listed:
        hero = heroes.find(text)
        if hero is None:
            raise CatalogueError(f"{where}: {field_name}: unknown hero {text!r}. The heroes are in data/heroes.json")
        if hero.id in ids:
            raise CatalogueError(f"{where}: {field_name}: {hero.name} is listed twice")
        ids.append(hero.id)
    return tuple(ids)


def parse_heroes(data: object, label: str, towns: Catalogue) -> Catalogue:
    """Build the hero catalogue: each hero has a town of the town catalogue and a link starting with https://, and no
    two heroes share a name (players name a hero by typing it)."""
    catalogue = parse_catalogue(data, label, HERO_FIELDS, HERO_OPTIONAL)
    first_use: dict[str, int] = {}
    for number, entry in enumerate(catalogue.entries, start=1):
        where = f"{label}: entry {number} ({entry.id})"
        if entry.details["town"] not in towns:
            raise CatalogueError(f"{where}: town: unknown town {entry.details['town']!r}. Known towns: {', '.join(towns.ids)}")
        link = entry.details["link"]
        if not link.startswith("https://") or len(link) <= len("https://"):
            raise CatalogueError(f"{where}: link: must be a web link starting with https://, not {link!r}")
        name = entry.name.strip().lower()
        if name in first_use:
            raise CatalogueError(f"{where}: the name {entry.name!r} is already used by entry {first_use[name]}")
        first_use[name] = number
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


def banned_by_default(hero: Entry, template: Entry) -> bool:
    """Whether HotA's defaults ban a hero on a template: the heroes banned by default always, and the heroes banned on
    mirror templates when the template is a mirror."""
    return bool(hero.details.get("banned_by_default") or (hero.details.get("banned_on_mirrors") and template.details.get("mirror")))


def heroes_offered(heroes: Catalogue, template: Entry, town: str) -> list[Entry]:
    """The heroes of a town that a template's map offers. The template's own lists win over the defaults: a hero it
    bans is out, and one the defaults ban is in only if the template allows it (`allowed_heroes`)."""
    banned = set(template.details.get("banned_heroes", ()))
    allowed = set(template.details.get("allowed_heroes", ()))
    return [
        hero
        for hero in heroes.entries
        if hero.details["town"] == town
        and hero.id not in banned
        and (hero.id in allowed or not banned_by_default(hero, template))
    ]


def load_templates(path: Path, heroes: Catalogue | None = None) -> Catalogue:
    return parse_templates(_read_json(path), path.name, heroes)


def load_heroes(path: Path, towns: Catalogue) -> Catalogue:
    """The hero catalogue. A repository without the file has no heroes, which only matters to a roulette."""
    if not path.exists():
        return Catalogue([])
    return parse_heroes(_read_json(path), path.name, towns)
