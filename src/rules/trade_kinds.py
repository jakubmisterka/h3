"""How a game's trade is run: its kind, and the sections that kind has.

Plain Python: no Discord objects in here, so tests can cover it. A template (in the catalogue) and a tournament (in a
format file) state the kind as the `trade` setting. It is stacked like the other settings, see `template_settings.py`.

A kind is written as a name, or as an object when it has options:

    "standard"                                         the pair of towns, the town bid, the color bid
    "standard_with_ai_packs"                           plus two packs of computer-player towns and a bid for a pack
    "roulette"  or  {"kind": "roulette", "hero_bans": 1, "roll_before_heroes": true}
                                                       the starting heroes are drawn by the bot
    "roulette_with_ai_packs"                           a roulette that also has the two packs and the bid for a pack
                                                       (takes the same options as "roulette")

Whether both players play the same town (a mirror) is a fact of the template, not part of the kind, and the two
combine: see `sections`.
"""

from dataclasses import dataclass

STANDARD_KIND = "standard"
PACKS_KIND = "standard_with_ai_packs"
ROULETTE_KIND = "roulette"
ROULETTE_PACKS_KIND = "roulette_with_ai_packs"
KINDS = (STANDARD_KIND, PACKS_KIND, ROULETTE_KIND, ROULETTE_PACKS_KIND)
MAX_HERO_BANS = 3  # heroes a player may ban before the draw (a command has one option for each)

_OPTIONS = {"kind", "hero_bans", "roll_before_heroes"}


@dataclass(frozen=True)
class Section:
    """One section of a trade. A bid is a section whose result the players report; `choice_field` is where its choice
    is kept in the record."""

    name: str
    bid: bool = False
    choice_field: str | None = None


SECTION_TABLE = {
    section.name: section
    for section in (
        Section("town_roll"),
        Section("hero_bans"),
        Section("town_bid", True, "town"),
        Section("pack_bid", True, "pack"),
        Section("first_choice_bid", True, "first"),
        Section("color_bid", True, "color"),
    )
}


@dataclass(frozen=True)
class TradeKind:
    name: str = STANDARD_KIND
    hero_bans: int = 0  # roulette: heroes each player may ban before the draw
    roll_before_heroes: bool = True  # roulette: True draws the heroes after the rolls, False together with the towns

    @property
    def draws_heroes(self) -> bool:
        return self.name in (ROULETTE_KIND, ROULETTE_PACKS_KIND)

    @property
    def has_packs(self) -> bool:
        return self.name in (PACKS_KIND, ROULETTE_PACKS_KIND)


def check_trade(value: object) -> TradeKind:
    """The kind a `trade` setting states, or ValueError with what is wrong. A name, or an object with the options."""
    known = ", ".join(KINDS)
    if isinstance(value, str):
        value = {"kind": value}
    if not isinstance(value, dict) or "kind" not in value:
        raise ValueError(f'state the kind as a name or as an object with a "kind": one of {known}')
    name = value["kind"]
    if name not in KINDS:
        raise ValueError(f"{name!r} is not a kind of trade. The kinds are: {known}")
    extra = set(value) - _OPTIONS
    if extra:
        raise ValueError(f"unknown option {sorted(extra)[0]!r}. A trade can have: {', '.join(sorted(_OPTIONS))}")
    if name not in (ROULETTE_KIND, ROULETTE_PACKS_KIND) and set(value) != {"kind"}:
        raise ValueError(f"hero_bans and roll_before_heroes are options of {ROULETTE_KIND}, not of {name}")

    hero_bans = value.get("hero_bans", 0)
    if isinstance(hero_bans, bool) or not isinstance(hero_bans, int) or not 0 <= hero_bans <= MAX_HERO_BANS:
        raise ValueError(f"hero_bans is a whole number from 0 to {MAX_HERO_BANS}, not {hero_bans!r}")
    roll_first = value.get("roll_before_heroes", True)
    if not isinstance(roll_first, bool):
        raise ValueError(f"roll_before_heroes is true or false, not {roll_first!r}")
    if hero_bans and not roll_first:
        raise ValueError("heroes cannot be banned before they are drawn: with roll_before_heroes false, hero_bans must be 0")
    return TradeKind(name, hero_bans, roll_first)


def sections(kind: TradeKind, mirror: bool) -> tuple[str, ...]:
    """The sections of a trade, in order. The roll comes first and is a side option until the first bid, but it is
    always the first section; the heroes are drawn by the bot between the roll and the bids, so they are no section."""
    if kind.has_packs and mirror:
        raise ValueError("a mirror template cannot have computer-player packs")
    bans = ("hero_bans",) if kind.draws_heroes and kind.hero_bans and kind.roll_before_heroes else ()
    if kind.has_packs:
        return ("town_roll", *bans, "town_bid", "pack_bid", "color_bid")
    if kind.draws_heroes and mirror:
        bids = ("first_choice_bid",)
    elif mirror:
        bids = ("color_bid",)
    else:
        bids = ("town_bid", "color_bid")
    return ("town_roll", *bans, *bids)


def bid_sections(kind: TradeKind, mirror: bool) -> tuple[str, ...]:
    """The sections of a trade whose result the players report, in order."""
    return tuple(name for name in sections(kind, mirror) if SECTION_TABLE[name].bid)


def trade_rule(kind: TradeKind, mirror: bool) -> str:
    """One message that says how the trade of a game is run, for the rules posted at the start of a match."""
    if kind.name == PACKS_KIND:
        return "Trade: town roll (a pair of towns and two packs of AI towns), then a bid for the town, for a pack and for the color."
    if kind.name == ROULETTE_PACKS_KIND:
        if not kind.roll_before_heroes:
            return (
                "Trade (roulette with AI packs): the pair, two packs of AI towns and the heroes of the pair are drawn together "
                "(a roll redraws all); then a bid for the town, which decides the hero too, for a pack and for the color."
            )
        bans = f"{kind.hero_bans} hero ban{'' if kind.hero_bans == 1 else 's'} each, then " if kind.hero_bans else ""
        return (
            f"Trade (roulette with AI packs): town roll (a pair of towns and two packs of AI towns), {bans}the bot draws a hero for each town of the pair; "
            "then a bid for the town, which decides the hero too, for a pack and for the color."
        )
    if not kind.draws_heroes:
        if mirror:
            return "Trade: one town for both players; town roll, then a bid for the color."
        return "Trade: town roll, then a bid for the town and for the color."
    if not kind.roll_before_heroes:
        if mirror:
            return (
                "Trade (roulette): one town for both players, with two heroes of it drawn together (a roll redraws both); "
                "then one bid: its winner chooses first the hero or the color."
            )
        return (
            "Trade (roulette): the towns and their heroes are drawn together (a roll redraws both); "
            "then a bid for the town, which decides the hero too, and for the color."
        )
    bans = f"{kind.hero_bans} hero ban{'' if kind.hero_bans == 1 else 's'} each, then " if kind.hero_bans else ""
    if mirror:
        return (
            f"Trade (roulette): one town for both players; town roll, {bans}the bot draws two heroes of it; "
            "then one bid: its winner chooses first the hero or the color."
        )
    return (
        f"Trade (roulette): town roll, {bans}the bot draws a hero for each town; "
        "then a bid for the town, which decides the hero too, and for the color."
    )


def kind_words(kind: TradeKind) -> str | None:
    """The kind in a few words for /info, or None for the standard trade (it gets no line)."""
    if kind.name == PACKS_KIND:
        return "computer-player packs"
    if kind.draws_heroes:
        bans = "no hero bans" if kind.hero_bans == 0 else (f"{kind.hero_bans} hero ban each" if kind.hero_bans == 1 else f"{kind.hero_bans} hero bans each")
        when = "heroes drawn after the rolls" if kind.roll_before_heroes else "heroes drawn with the towns"
        return f"roulette{' with computer-player packs' if kind.has_packs else ''}, {bans}, {when}"
    return None
