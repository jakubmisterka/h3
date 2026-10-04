"""Tournament formats: loading, validation and the settings derived from them.

A format is one JSON file in formats/ (shape: formats/schema.json). This module
checks everything the schema cannot, and answers questions such as "what are the
trade settings for template X in this phase?". It knows nothing about Discord.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from rules.catalogue import Catalogue
from rules.errors import UserError

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "formats" / "schema.json"

# Gold each human player starts with, by in-game difficulty (percent).
# Source: https://heroes.thelazy.net/index.php/Difficulty
DIFFICULTY_GOLD = {80: 30000, 100: 20000, 130: 15000, 160: 10000, 200: 0}

DEFAULT_ROLL_COST = 500
DEFAULT_ROLLS_PER_PLAYER = 1
DEFAULT_MAX_ROLL_BANS = 2

BID_SECTIONS = ("faction_roll", "faction_bid", "color_bid")
# At 200% the lobby is all-random and nobody has gold: only the color is tossed.
ALL_RANDOM_SECTIONS = ("color_toss",)
ALL_RANDOM_DIFFICULTY = 200


class FormatError(ValueError):
    """A format file is not valid. `errors` lists every problem found."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class ModeError(UserError):
    """The requested mode does not exist or cannot be used for a new match."""


@dataclass(frozen=True)
class Step:
    who: str  # "A" (coinflip winner) or "B"
    do: str  # "ban" or "pick"


@dataclass(frozen=True)
class TradeSettings:
    difficulty: int
    starting_gold: int
    roll_cost: int
    rolls_per_player: int
    max_roll_bans: int
    sections: tuple[str, ...]


@dataclass(frozen=True)
class Phase:
    name: str
    best_of: int
    pool: tuple[str, ...]
    agreed: bool  # True: players agree on the template, no bans or picks
    steps: tuple[Step, ...]
    game_order: tuple[str, ...]  # "pick_1", "pick_2", ..., "decider"
    allowed_factions: tuple[str, ...]
    trade: dict  # raw phase defaults
    template_overrides: dict  # raw per-template overrides


@dataclass(frozen=True)
class Format:
    id: str
    name: str
    active: bool
    thread_visibility: str
    phases: tuple[Phase, ...]


def starting_gold(difficulty: int) -> int:
    return DIFFICULTY_GOLD[difficulty]


def default_sections(difficulty: int) -> tuple[str, ...]:
    return ALL_RANDOM_SECTIONS if difficulty == ALL_RANDOM_DIFFICULTY else BID_SECTIONS


def trade_settings(phase: Phase, template_id: str) -> TradeSettings:
    """Phase defaults, updated by the template's overrides, with the standard fallbacks."""
    merged = {**phase.trade, **phase.template_overrides.get(template_id, {})}
    difficulty = merged["difficulty"]
    return TradeSettings(
        difficulty=difficulty,
        starting_gold=starting_gold(difficulty),
        roll_cost=merged.get("roll_cost", DEFAULT_ROLL_COST),
        rolls_per_player=merged.get("rolls_per_player", DEFAULT_ROLLS_PER_PLAYER),
        max_roll_bans=merged.get("max_roll_bans", DEFAULT_MAX_ROLL_BANS),
        sections=tuple(merged["sections"]) if "sections" in merged else default_sections(difficulty),
    )


def _schema_validator() -> Draft202012Validator:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return Draft202012Validator(json.load(f))


def _find_starting_gold(data: object, path: str = "") -> list[str]:
    """Starting gold comes from the difficulty and must never be written in a file."""
    found = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "starting_gold":
                found.append(f"{path or 'format'}: starting gold is not allowed here, it comes from the difficulty")
            found += _find_starting_gold(value, f"{path}.{key}" if path else key)
    elif isinstance(data, list):
        for i, value in enumerate(data):
            found += _find_starting_gold(value, f"{path}[{i}]")
    return found


def _check_difficulty(settings: dict, where: str) -> list[str]:
    difficulty = settings.get("difficulty")
    if difficulty is not None and difficulty not in DIFFICULTY_GOLD:
        allowed = ", ".join(f"{d}%" for d in DIFFICULTY_GOLD)
        return [f"{where}: difficulty {difficulty} is not supported (use one of {allowed})"]
    return []


def _check_phase(phase: dict, templates: Catalogue, factions: Catalogue) -> list[str]:
    where = f'phase "{phase["name"]}"'
    errors: list[str] = []
    pool = phase["pool"]

    if len(set(pool)) != len(pool):
        errors.append(f"{where}: the pool lists a template twice")
    for template_id in pool:
        if template_id not in templates:
            errors.append(f"{where}: unknown template {template_id!r} (not in data/templates.json)")

    for faction_id in phase.get("allowed_factions", []):
        if faction_id not in factions:
            errors.append(f"{where}: unknown faction {faction_id!r} (not in data/factions.json)")

    errors += _check_difficulty(phase["trade"], where)
    for template_id, overrides in phase.get("template_overrides", {}).items():
        if template_id not in pool:
            errors.append(f"{where}: override for {template_id!r}, which is not in the pool")
        errors += _check_difficulty(overrides, f"{where}, override for {template_id}")

    selection = phase["selection"]
    if selection["type"] == "agreed":
        if phase["best_of"] != 1:
            errors.append(f"{where}: an agreed-template phase must be best-of 1")
        return errors

    steps = selection["steps"]
    if len(pool) != len(steps) + 1:
        errors.append(
            f"{where}: the pool must be one larger than the number of steps "
            f"(pool has {len(pool)}, sequence has {len(steps)} steps)"
        )
    picks = sum(1 for s in steps if s["do"] == "pick")
    if picks != phase["best_of"] - 1:
        errors.append(
            f"{where}: a best-of-{phase['best_of']} needs {phase['best_of'] - 1} picks, the sequence has {picks}"
        )
    expected = sorted([f"pick_{i}" for i in range(1, picks + 1)] + ["decider"])
    if sorted(selection["game_order"]) != expected:
        errors.append(
            f"{where}: game_order must name every game exactly once ({', '.join(expected)}), "
            f"got {', '.join(selection['game_order'])}"
        )
    return errors


def validate_format(data: object, templates: Catalogue, factions: Catalogue) -> list[str]:
    """Return every problem found in a parsed format file; an empty list means valid."""
    errors = _find_starting_gold(data)
    errors += [
        f"{'/'.join(str(p) for p in e.absolute_path) or 'format'}: {e.message}"
        for e in sorted(_schema_validator().iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
        if not (e.validator == "additionalProperties" and "starting_gold" in e.message)
    ]
    if errors:
        return errors

    names = [p["name"] for p in data["phases"]]
    if len(set(names)) != len(names):
        errors.append("two phases have the same name")
    for phase in data["phases"]:
        errors += _check_phase(phase, templates, factions)
    return errors


def parse_format(data: dict, templates: Catalogue, factions: Catalogue) -> Format:
    errors = validate_format(data, templates, factions)
    if errors:
        raise FormatError(errors)

    phases = []
    for p in data["phases"]:
        selection = p["selection"]
        agreed = selection["type"] == "agreed"
        phases.append(
            Phase(
                name=p["name"],
                best_of=p["best_of"],
                pool=tuple(p["pool"]),
                agreed=agreed,
                steps=() if agreed else tuple(Step(s["who"], s["do"]) for s in selection["steps"]),
                game_order=() if agreed else tuple(selection["game_order"]),
                allowed_factions=tuple(p.get("allowed_factions", factions.ids)),
                trade=p["trade"],
                template_overrides=p.get("template_overrides", {}),
            )
        )
    return Format(
        id=data["id"],
        name=data["name"],
        active=data.get("status", "active") == "active",
        thread_visibility=data.get("thread_visibility", "public"),
        phases=tuple(phases),
    )


def load_format(path: Path, templates: Catalogue, factions: Catalogue) -> Format:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise FormatError([f"{path.name}: not valid JSON ({e})"]) from e
    try:
        fmt = parse_format(data, templates, factions)
    except FormatError as e:
        raise FormatError([f"{path.name}: {msg}" for msg in e.errors]) from e
    if path.stem != fmt.id:
        raise FormatError([f'{path.name}: the file name must match the id "{fmt.id}"'])
    return fmt


def load_formats(directory: Path, templates: Catalogue, factions: Catalogue) -> dict[str, Format]:
    """Load every format file in a directory (schema.json excluded), keyed by id."""
    formats: dict[str, Format] = {}
    for path in sorted(directory.glob("*.json")):
        if path.name == "schema.json":
            continue
        fmt = load_format(path, templates, factions)
        formats[fmt.id] = fmt
    return formats


def list_modes(formats: dict[str, Format]) -> list[Format]:
    """The modes players can start a match with: active formats only."""
    return [f for f in formats.values() if f.active]


def get_mode(formats: dict[str, Format], mode_id: str) -> Format:
    """Find a mode to start a match in; refuse unknown and archived ones."""
    fmt = formats.get(mode_id)
    if fmt is None:
        raise ModeError(f"There is no mode called {mode_id!r}.")
    if not fmt.active:
        raise ModeError(f"The mode {fmt.name} is archived and cannot start new matches.")
    return fmt
