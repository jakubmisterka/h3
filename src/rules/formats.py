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
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from rules.catalogue import Catalogue

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


@dataclass(frozen=True)
class Phase:
    name: str
    best_of: int
    pool: tuple[TemplateEntry, ...]  # the templates this phase uses, with the settings written for this phase
    agreed: bool  # True: the players agree on the template, there are no bans or picks
    steps: tuple[Step, ...]  # the games are played in the order of the picks, then the decider
    allowed_towns: tuple[str, ...]  # town ids players can get in this phase: its own list, else the tournament's

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
    """The message of a schema error. A failed pattern reads like code, so add the field's plain description."""
    description = error.schema.get("description")
    if error.validator == "pattern" and description:
        return f"{error.message}. {description}"
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

    if phase["selection"]["type"] == "sequence":
        problems += _sequence_problems(phase, label, len(pool))
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
    steps = phase["selection"]["steps"]
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


def rule_problems(data: dict, templates: Catalogue, towns: Catalogue) -> list[str]:
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
    return problems


def validate_format(data, templates: Catalogue, towns: Catalogue) -> list[str]:
    """Every problem found in a parsed format file, in words. An empty list means it is valid."""
    problems = shape_problems(data)
    if problems:
        return problems  # the rules cannot be checked on a file with the wrong shape
    return rule_problems(data, templates, towns)


# --- loading --------------------------------------------------------------------------------


def _entry(raw) -> TemplateEntry:
    if isinstance(raw, str):
        return TemplateEntry(raw, {})
    return TemplateEntry(raw["template"], raw.get("roll_rules", {}))


def parse_format(data, templates: Catalogue, towns: Catalogue) -> Format:
    """Check a parsed format file and turn it into a Format. Raises FormatError listing every problem."""
    problems = validate_format(data, templates, towns)
    if problems:
        raise FormatError(problems)

    tournament_templates = tuple(_entry(e) for e in data["templates"])
    tournament_towns = tuple(data.get("allowed_towns", towns.ids))
    phases = []
    for raw in data["phases"]:
        agreed = raw["selection"]["type"] == "agreed"
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
                steps=() if agreed else tuple(Step(s.get("who"), s["do"]) for s in raw["selection"]["steps"]),
                allowed_towns=tuple(raw["allowed_towns"]) if "allowed_towns" in raw else tournament_towns,
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
    )


def load_format(path: Path, templates: Catalogue, towns: Catalogue) -> Format:
    """Read, check and build one format file. Every error message starts with the file name."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise FormatError([f"{path.name}: not valid JSON ({e})"]) from e
    try:
        fmt = parse_format(data, templates, towns)
    except FormatError as e:
        raise FormatError([f"{path.name}: {problem}" for problem in e.errors]) from e
    if path.stem != fmt.id:
        raise FormatError([f'{path.name}: the file name must match the format id "{fmt.id}"'])
    return fmt


def load_formats(directory: Path, templates: Catalogue, towns: Catalogue) -> dict[str, Format]:
    """Every format file in a folder (`schema.json` excluded), by id.

    If some files are not valid, one FormatError lists the problems of all of them.
    """
    formats = {}
    problems = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "schema.json":
            continue
        try:
            fmt = load_format(path, templates, towns)
        except FormatError as e:
            problems += e.errors
        else:
            formats[fmt.id] = fmt
    if problems:
        raise FormatError(problems)
    return formats
