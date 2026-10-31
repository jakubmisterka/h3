"""Tournament formats: loading a format file, checking it, and the objects the rest of the bot uses.

A format is one JSON file in `formats/`. It lists the templates of the tournament once, and each
phase selects its pool from that list (all of it, when the phase states no pool). Settings such as
roll rules can be written for the whole tournament, for a template in the list, or for a template in
one phase's pool; the most specific one wins.

Checking a file happens in two stages:

1. its shape, against `formats/schema.json` (which fields exist, which values are allowed);
2. the rules that compare values, which a schema cannot say: that the templates and towns it names
   exist, that each phase pool is part of the tournament's list, the size of the pool against the
   number of steps, the number of games, and the place of the decider.

Every problem found is reported at once, in plain words, so a contributor can fix them in one go.
"""

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from rules.catalogue import Catalogue, heroes_offered
from rules.trade_kinds import TradeKind, check_trade
from rules.lobby_values import (
    check_alternatives,
    check_computer_players,
    check_download,
    check_game_date,
    check_map_size,
    check_roads,
    check_text,
    check_timer,
)

SCHEMA_FILE = Path(__file__).resolve().parents[2] / "formats" / "schema.json"


class FormatError(ValueError):
    """A format file is not valid. `errors` lists every problem found."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class Step:
    who: str | None  # "A" (the coinflip winner) or "B"; None for the decider
    do: str  # "ban", "pick" or "decider" (the template that is left)


@dataclass(frozen=True)
class TemplateEntry:
    """A template in the tournament's list or in a phase's pool, with the settings written for it there."""

    template: str  # template id
    roll_rules: dict  # roll rules written for this template here (empty: nothing special)
    settings: dict = field(default_factory=dict)  # timer, roads, map size, computer players and sim turns written for it here


@dataclass(frozen=True)
class Phase:
    name: str
    best_of: int
    pool: tuple[TemplateEntry, ...]  # the templates this phase uses, with the settings written for this phase
    agreed: bool  # True: the players agree on the template, there are no bans or picks
    steps: tuple[Step, ...]  # the games are played in the order of the picks, then the decider
    allowed_towns: tuple[str, ...]  # town ids players can get in this phase: its own list, else the tournament's
    fixed: bool = False  # True: the phase has one template and every game is played on it, there are no bans or picks

    @property
    def pool_ids(self) -> tuple[str, ...]:
        return tuple(entry.template for entry in self.pool)


@dataclass(frozen=True)
class Format:
    id: str
    name: str
    active: bool
    thread_visibility: str
    roll_rules: dict  # roll rules for every template of the tournament (empty: the defaults apply)
    allowed_towns: tuple[str, ...]  # towns players can get unless a phase has its own list (all towns by default)
    templates: tuple[TemplateEntry, ...]  # every template of the tournament, once
    phases: tuple[Phase, ...]
    settings: dict = field(default_factory=dict)  # timer and sim turns written for the whole tournament
    description: str | None = None  # what the tournament is, for /info
    additional_rules: str | None = None  # additional rules of the tournament as a whole, for /info


# --- stage 1: the shape ---------------------------------------------------------------------


@lru_cache(maxsize=1)
def _schema_validator() -> Draft202012Validator:
    with open(SCHEMA_FILE, encoding="utf-8") as f:
        return Draft202012Validator(json.load(f))


def _where(path, data) -> str:
    """Where a problem is, in words: the phase by name, then the field."""
    parts = list(path)
    if len(parts) >= 2 and parts[0] == "phases" and isinstance(parts[1], int):
        phases = data.get("phases") if isinstance(data, dict) else None
        phase = phases[parts[1]] if isinstance(phases, list) and parts[1] < len(phases) else None
        name = phase.get("name") if isinstance(phase, dict) else None
        head = f'phase "{name}"' if name else f"phase {parts[1] + 1}"
        rest = ".".join(str(p) for p in parts[2:])
        return f"{head}, {rest}" if rest else head
    return ".".join(str(p) for p in parts) or "the file"


def _explain(error) -> str:
    """The message of a schema error. A failed pattern reads like code, so add the field's plain description,
    and a field that is not allowed here just says why with its own description."""
    description = error.schema.get("description")
    if error.validator == "pattern" and description:
        return f"{error.message}. {description}"
    if error.validator == "not" and description:
        return description
    return error.message


def shape_problems(data) -> list[str]:
    """Problems with the shape of a format, in words. Empty means the shape is right."""
    errors = sorted(_schema_validator().iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path])
    return [f"{_where(e.absolute_path, data)}: {_explain(e)}" for e in errors]


# --- stage 2: the rules ---------------------------------------------------------------------


def _template_id(raw) -> str:
    """The template id of an entry written either as a plain id or as an object."""
    return raw if isinstance(raw, str) else raw["template"]


def _repeated(ids: list[str]) -> list[str]:
    return sorted({i for i in ids if ids.count(i) > 1})


def _phase_problems(phase: dict, listed: list[str], towns: Catalogue) -> list[str]:
    label = f'phase "{phase["name"]}"'
    problems = []

    # A phase without a pool uses every template of the tournament.
    pool = [_template_id(e) for e in phase["pool"]] if "pool" in phase else listed
    for template in _repeated(pool):
        problems.append(f"{label}: the template {template!r} is in the pool more than once")
    for template in pool:
        if template not in listed:
            problems.append(
                f"{label}: the template {template!r} is in the pool but not in the tournament's templates "
                f"({', '.join(listed)})"
            )
    problems += _town_problems(label, phase.get("allowed_towns", []), towns)

    kind = phase["template_selection"]["type"]
    if kind == "sequence":
        problems += _sequence_problems(phase, label, len(pool))
    if kind == "fixed" and len(set(pool)) != 1:
        problems.append(f"{label}: a fixed phase needs exactly one template, but it has {len(set(pool))} ({', '.join(pool)})")
    return problems


def _town_problems(label: str, allowed: list[str], towns: Catalogue) -> list[str]:
    problems = []
    for town in _repeated(allowed):
        problems.append(f"{label}: the town {town!r} is in allowed_towns more than once")
    for town in dict.fromkeys(allowed):
        if town not in towns:
            problems.append(f"{label}: unknown town {town!r}. Known towns: {', '.join(towns.ids)}")
    return problems


def _sequence_problems(phase: dict, label: str, pool_size: int) -> list[str]:
    problems = []
    steps = phase["template_selection"]["steps"]
    best_of = phase["best_of"]

    # Every template in the pool is used by exactly one step: banned, picked, or taken by the decider.
    if pool_size != len(steps):
        problems.append(
            f"{label}: the pool must have as many templates as the sequence has steps, because each template "
            f"is banned, picked or taken by the decider ({pool_size} templates, {len(steps)} steps)"
        )

    deciders = [i for i, step in enumerate(steps) if step["do"] == "decider"]
    if len(deciders) > 1:
        problems.append(f"{label}: the sequence has {len(deciders)} decider steps, it can have only one")
    elif deciders and deciders[0] != len(steps) - 1:
        problems.append(f"{label}: the decider must be the last step")
    if any("who" in steps[i] for i in deciders):
        problems.append(f"{label}: the decider names no player, it takes the template that is left")

    # The games are the picks, in order, plus the decider if there is one.
    picks = sum(1 for step in steps if step["do"] == "pick")
    games = picks + (1 if deciders else 0)
    if games != best_of:
        pick_text = f"{picks} pick" if picks == 1 else f"{picks} picks"
        decider_text = "a decider" if deciders else "no decider"
        problems.append(
            f"{label}: a best-of-{best_of} needs {best_of} games, but the sequence gives {games} "
            f"({pick_text} and {decider_text})"
        )
    return problems


# How each setting is read, and for the three that a template lists the allowed values of, the name of that list.
_SETTING_CHECKS = {
    "timer": check_timer,
    "sim_turns": check_game_date,
    "roads": check_roads,
    "map_size": check_map_size,
    "ai": check_computer_players,
    "additional_rules": check_text,
    "download": check_download,
    "trade": check_trade,
    "alternatives": check_alternatives,
}
_CHOSEN_FROM_ALLOWED = ("roads", "map_size", "ai")


def _settings_problems(where: str, settings: dict, template: str | None, templates: Catalogue) -> list[str]:
    """Problems with the settings written in one place: each value has the right form, and what is chosen for a
    template is among the values that template allows. `template` is None for the whole tournament."""
    problems = []
    for name, value in settings.items():
        try:
            _SETTING_CHECKS[name](value)
        except ValueError as e:
            problems.append(f"{where}: {name}: {e}")
            continue
        entry = templates.find(template) if template else None
        if name == "trade" and entry is not None and check_trade(value).has_packs and entry.details.get("mirror"):
            problems.append(f"{where}: trade: a mirror template cannot have computer-player packs ({template!r} is a mirror)")
        if name == "alternatives" and entry is not None:
            problems += _alternative_problems(where, template, value, templates)
        if name in _CHOSEN_FROM_ALLOWED and entry is not None:  # an unknown template is reported elsewhere
            choice = entry.details.get(name)
            if choice is None:
                problems.append(
                    f"{where}: {name} cannot be chosen, because the template {template!r} states no allowed {name} "
                    f"in the template catalogue"
                )
            elif value not in choice.allowed:
                problems.append(
                    f"{where}: {name}: {value!r} is not allowed for {template!r}. "
                    f"Allowed: {', '.join(str(v) for v in choice.allowed)}"
                )
    return problems


def _alternative_problems(where: str, template: str, alternatives: list[str], templates: Catalogue) -> list[str]:
    """An alternative is another template of the catalogue that players can get: built into HotA or with a download link."""
    problems = []
    for alternative in alternatives:
        entry = templates.find(alternative)
        if entry is None:
            problems.append(f"{where}: alternatives: {alternative!r} is not a template of the catalogue")
        elif entry.id == template:
            problems.append(f"{where}: alternatives: {template!r} cannot be its own alternative")
        elif not (entry.details.get("built_in") or entry.details.get("download")):
            problems.append(
                f"{where}: alternatives: {alternative!r} is neither built into HotA nor has a download link in the "
                f"catalogue, so players could not get it"
            )
    return problems


def _stacked(name: str, catalogue_value, *written_in):
    """The value of a setting for a template as it is written, the most specific place winning: the catalogue, then
    the template's entry in the tournament's list, then its entry in the phase's pool (`written_in`, least specific
    first). The same order as `effective_settings`, on the raw data a format file is validated from."""
    value = catalogue_value
    for raw in written_in:
        if isinstance(raw, dict) and name in raw.get("settings", {}):
            value = raw["settings"][name]
    return value


def _trade_kind(template: str, listed_entry, pool_entry, templates: Catalogue) -> TradeKind | None:
    """The kind of trade a template has in a phase, as written, or None if none is stated (or it is not a kind,
    which is reported with the setting itself)."""
    entry = templates.find(template)
    stated = _stacked("trade", entry.details.get("trade") if entry else None, listed_entry, pool_entry)
    if stated is None or isinstance(stated, TradeKind):  # the catalogue's value is already read
        return stated
    try:
        return check_trade(stated)
    except ValueError:
        return None


def _trade_name(template: str, listed_entry, pool_entry, templates: Catalogue) -> str | None:
    kind = _trade_kind(template, listed_entry, pool_entry, templates)
    return kind.name if kind else None


def _packs_problems(data: dict, templates: Catalogue, towns: Catalogue) -> list[str]:
    """Computer-player packs need eight different towns to draw from, in every phase that uses the template."""
    listed = {_template_id(raw): raw for raw in data["templates"]}
    problems = []
    for phase in data["phases"]:
        allowed = phase.get("allowed_towns", data.get("allowed_towns", towns.ids))
        pool = phase.get("pool") or data["templates"]
        for raw in pool:
            template = _template_id(raw)
            if template not in listed or len(set(allowed)) >= 8:
                continue
            kind = _trade_kind(template, listed[template], raw, templates)
            if kind is not None and kind.has_packs:
                problems.append(
                    f'phase "{phase["name"]}", {template}: trade: computer-player packs need at least eight allowed towns '
                    f"(two for the players and six for the computer players), but this phase allows {len(set(allowed))}"
                )
    return problems


def _roulette_problems(data: dict, templates: Catalogue, towns: Catalogue, heroes: Catalogue) -> list[str]:
    """A roulette draws heroes of the towns of the phase, so there must be heroes, and enough of them left in every
    allowed town after the heroes the template does not offer and the most the players could ban."""
    listed = {_template_id(raw): raw for raw in data["templates"]}
    problems = []
    for phase in data["phases"]:
        allowed = list(dict.fromkeys(phase.get("allowed_towns", data.get("allowed_towns", towns.ids))))
        for raw in phase.get("pool") or data["templates"]:
            template = _template_id(raw)
            kind = _trade_kind(template, listed.get(template), raw, templates) if template in listed else None
            if kind is None or not kind.draws_heroes:
                continue
            where = f'phase "{phase["name"]}", {template}: trade'
            if not heroes.entries:
                problems.append(f"{where}: a roulette draws heroes, but data/heroes.json has none")
                continue
            entry = templates.find(template)
            needed = (2 if entry and entry.details.get("mirror") else 1) + 2 * kind.hero_bans
            for town in allowed:
                left = len(heroes_offered(heroes, entry, town))
                if left < needed:
                    problems.append(
                        f"{where}: {towns.find(town).name} has {left} heroes left for {template}, but a roulette with "
                        f"{kind.hero_bans} hero bans each needs at least {needed}"
                    )
    return problems


def _all_settings_problems(data: dict, templates: Catalogue) -> list[str]:
    problems = _settings_problems("settings", data.get("settings", {}), None, templates)
    for raw in data["templates"]:
        if isinstance(raw, dict):
            problems += _settings_problems(f"templates, {raw['template']}: settings", raw.get("settings", {}), raw["template"], templates)
    for phase in data["phases"]:
        for raw in phase.get("pool", []):
            if isinstance(raw, dict):
                where = f'phase "{phase["name"]}", {raw["template"]}: settings'
                problems += _settings_problems(where, raw.get("settings", {}), raw["template"], templates)
    return problems


def rule_problems(data: dict, templates: Catalogue, towns: Catalogue, heroes: Catalogue | None = None) -> list[str]:
    """Problems with the rules of a format whose shape is right, in words."""
    problems = []

    listed = [_template_id(e) for e in data["templates"]]
    for template in _repeated(listed):
        problems.append(f"templates: the template {template!r} is listed more than once")
    for template in dict.fromkeys(listed):
        if template not in templates:
            problems.append(f"templates: unknown template {template!r}. Known templates: {', '.join(templates.ids)}")

    problems += _town_problems("allowed_towns", data.get("allowed_towns", []), towns)

    names = [phase["name"] for phase in data["phases"]]
    for name in _repeated(names):
        problems.append(f'two phases are called "{name}"')
    for phase in data["phases"]:
        problems += _phase_problems(phase, listed, towns)
    problems += _all_settings_problems(data, templates)
    problems += _packs_problems(data, templates, towns)
    if heroes is not None:
        problems += _roulette_problems(data, templates, towns, heroes)
    for name in ("description", "additional_rules"):
        if name in data:
            try:
                check_text(data[name])
            except ValueError as e:
                problems.append(f"{name}: {e}")
    return problems


def validate_format(data, templates: Catalogue, towns: Catalogue, heroes: Catalogue | None = None) -> list[str]:
    """Every problem found in a parsed format file, in words. An empty list means it is valid."""
    problems = shape_problems(data)
    if problems:
        return problems  # the rules cannot be checked on a file with the wrong shape
    return rule_problems(data, templates, towns, heroes)


# --- loading --------------------------------------------------------------------------------


def _entry(raw) -> TemplateEntry:
    if isinstance(raw, str):
        return TemplateEntry(raw, {})
    return TemplateEntry(raw["template"], raw.get("roll_rules", {}), raw.get("settings", {}))


def parse_format(data, templates: Catalogue, towns: Catalogue, heroes: Catalogue | None = None) -> Format:
    """Check a parsed format file and turn it into a Format. Raises FormatError listing every problem."""
    problems = validate_format(data, templates, towns, heroes)
    if problems:
        raise FormatError(problems)

    tournament_templates = tuple(_entry(e) for e in data["templates"])
    tournament_towns = tuple(data.get("allowed_towns", towns.ids))
    phases = []
    for raw in data["phases"]:
        agreed = raw["template_selection"]["type"] == "agreed"
        fixed = raw["template_selection"]["type"] == "fixed"
        if "pool" in raw:
            pool = tuple(_entry(e) for e in raw["pool"])
        else:  # no pool written: the phase uses every template of the tournament
            pool = tuple(TemplateEntry(t.template, {}) for t in tournament_templates)
        phases.append(
            Phase(
                name=raw["name"],
                best_of=raw["best_of"],
                pool=pool,
                agreed=agreed,
                steps=() if agreed or fixed else tuple(Step(s.get("who"), s["do"]) for s in raw["template_selection"]["steps"]),
                allowed_towns=tuple(raw["allowed_towns"]) if "allowed_towns" in raw else tournament_towns,
                fixed=fixed,
            )
        )
    return Format(
        id=data["id"],
        name=data["name"],
        active=data.get("status", "active") == "active",
        thread_visibility=data.get("thread_visibility", "public"),
        roll_rules=data.get("roll_rules", {}),
        allowed_towns=tournament_towns,
        templates=tournament_templates,
        phases=tuple(phases),
        settings=data.get("settings", {}),
        description=data.get("description"),
        additional_rules=data.get("additional_rules"),
    )


def load_format(path: Path, templates: Catalogue, towns: Catalogue, heroes: Catalogue | None = None) -> Format:
    """Read, check and build one format file. Every error message starts with the file name."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise FormatError([f"{path.name}: not valid JSON ({e})"]) from e
    try:
        fmt = parse_format(data, templates, towns, heroes)
    except FormatError as e:
        raise FormatError([f"{path.name}: {problem}" for problem in e.errors]) from e
    if path.stem != fmt.id:
        raise FormatError([f'{path.name}: the file name must match the format id "{fmt.id}"'])
    return fmt


def load_formats(directory: Path, templates: Catalogue, towns: Catalogue, heroes: Catalogue | None = None) -> dict[str, Format]:
    """Every format file in a folder (`schema.json` excluded), by id.

    If some files are not valid, one FormatError lists the problems of all of them.
    """
    formats = {}
    problems = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "schema.json":
            continue
        try:
            fmt = load_format(path, templates, towns, heroes)
        except FormatError as e:
            problems += e.errors
        else:
            formats[fmt.id] = fmt
    if problems:
        raise FormatError(problems)
    return formats
