"""What the bot draws for a trade, and what a draw must look like to be believed.

Plain Python: no Discord objects in here, so tests can cover it. A `Draw` is everything the bot drew for a trade at
one moment: the town(s) the players play, for a trade with computer-player packs the six towns of the two packs, and
for a roulette that draws its heroes together with the towns the two heroes. A roll draws again. `draw_shape` says how
many of each a kind draws, so the draws, the checks of a thread's records and the reading of them all use one table.

A town banned in a roll is banned for the players only: it stays out of the town(s) the players play, but it may
come up in a pack of computer-player towns.

The heroes of a roulette are two: for a mirror two different heroes of its town, otherwise one hero of each town of the
pair (the first for the first town). They come from the heroes the template's map offers (`heroes_offered`).
"""

import random
from dataclasses import dataclass

from rules.catalogue import Catalogue, Entry, heroes_offered
from rules.trade_kinds import TradeKind

PACK_SIZE = 3  # towns in a pack
PACK_COUNT = 2  # packs
HERO_COUNT = 2  # heroes drawn for a roulette


class TradeError(ValueError):
    """The trade cannot do what was asked. The message is shown to the player."""


class HeroDrawError(TradeError):
    """The heroes of a roulette cannot be drawn: there are too few that the template's map offers."""


@dataclass(frozen=True)
class Draw:
    """What the bot drew: the town(s) the players play (two, or one for a mirror), the six towns of the packs (pack1
    first) when the trade has packs, and the two heroes (hero ids) when a roulette draws them with the towns."""

    towns: tuple[str, ...]
    packs: tuple[str, ...] = ()
    heroes: tuple[str, ...] = ()

    @property
    def words(self) -> tuple[str, ...]:
        """Every town drawn, in the order the records write them."""
        return self.towns + self.packs

    def pack(self, number: int) -> tuple[str, ...]:
        """The three towns of pack `number` (0 for pack1, 1 for pack2)."""
        return self.packs[number * PACK_SIZE : (number + 1) * PACK_SIZE]


@dataclass(frozen=True)
class DrawShape:
    """How many towns, pack towns and heroes a kind of trade draws."""

    towns: int
    packs: int
    heroes: int = 0

    @property
    def size(self) -> int:
        """The towns and the pack towns: the words a draw has that must all be different."""
        return self.towns + self.packs


def draw_shape(kind: TradeKind, mirror: bool) -> DrawShape:
    with_heroes = kind.draws_heroes and not kind.roll_before_heroes  # otherwise the heroes are drawn after the rolls
    return DrawShape(1 if mirror else 2, PACK_COUNT * PACK_SIZE if kind.has_packs else 0, HERO_COUNT if with_heroes else 0)


# --- the heroes ----------------------------------------------------------------------------------------------------


def hero_pool_of(
    heroes: Catalogue, template: Entry, towns: tuple[str, ...], banned: frozenset[str] | set[str] = frozenset()
) -> dict[str, tuple[str, ...]]:
    """The heroes that can be drawn in each of `towns`, as ids: the ones the template's map offers, less `banned`."""
    return {town: tuple(hero.id for hero in heroes_offered(heroes, template, town) if hero.id not in banned) for town in towns}


def pick_heroes(
    towns: tuple[str, ...], mirror: bool, pool: dict[str, tuple[str, ...]], random_source: random.Random | None = None
) -> tuple[str, ...]:
    """Two different heroes of the town for a mirror, otherwise one hero of each town of the pair, in the order of the
    towns. Raises HeroDrawError when the pool is too small."""
    source = random_source or random
    if mirror:
        ids = pool[towns[0]]
        if len(ids) < HERO_COUNT:
            raise HeroDrawError("Fewer than two heroes can be drawn for this game.")
        return tuple(source.sample(ids, HERO_COUNT))
    if any(not pool[town] for town in towns):
        raise HeroDrawError("No hero can be drawn for one of the towns of this game.")
    return tuple(source.choice(pool[town]) for town in towns)


def check_heroes_fit(towns: tuple[str, ...], mirror: bool, drawn: tuple[str, ...], pool: dict[str, tuple[str, ...]]) -> None:
    """Raise TradeError unless `drawn` is what may be drawn for these towns: two different heroes, from the pool."""
    if len(drawn) != HERO_COUNT or len(set(drawn)) != HERO_COUNT:
        raise TradeError("Two different heroes are drawn.")
    if mirror:
        if not set(drawn) <= set(pool[towns[0]]):
            raise TradeError("A drawn hero is not one of the heroes that can be drawn for this game.")
    else:
        for town, hero in zip(towns, drawn):
            if hero not in pool[town]:
                raise TradeError(f"{hero} cannot be the hero of {town}: it is not one of the heroes that can be drawn.")


# --- checking a draw ---------------------------------------------------------------------------------------------


_PAIR_RULE = "The new pair must be two different allowed towns that are not banned."


def check_draw(
    draw: Draw,
    kind: TradeKind,
    mirror: bool,
    allowed_towns: tuple[str, ...],
    banned: tuple[str, ...],
    heroes: Catalogue | None = None,
    template: Entry | None = None,
) -> None:
    """Raise TradeError unless `draw` is what a trade of this kind draws: the right number of different allowed
    towns, none of the town(s) the players play banned (a banned town may be in a pack) and, when the kind draws its
    heroes with the towns, heroes that the template's map offers (checked when the hero catalogue is given)."""
    plain = not mirror and not kind.has_packs and not kind.draws_heroes
    shape = draw_shape(kind, mirror)
    if len(draw.towns) != shape.towns or len(draw.packs) != shape.packs or len(set(draw.words)) != len(draw.words):
        raise TradeError(_PAIR_RULE if plain else "The new draw has the wrong number of towns, or repeats one.")
    if not set(draw.words) <= set(allowed_towns) or set(draw.towns) & set(banned):
        raise TradeError(_PAIR_RULE if plain else "The new draw must be allowed towns, and the players' town(s) must not be banned.")
    if len(draw.heroes) != shape.heroes:
        raise TradeError(f"A draw of this kind has {shape.heroes} heroes, not {len(draw.heroes)}.")
    if shape.heroes and heroes is not None and template is not None:
        check_heroes_fit(draw.towns, mirror, draw.heroes, hero_pool_of(heroes, template, draw.towns))


def check_start(
    draw: Draw,
    kind: TradeKind,
    mirror: bool,
    allowed_towns: tuple[str, ...],
    heroes: Catalogue | None = None,
    template: Entry | None = None,
) -> None:
    """Raise TradeError unless what a trade started with fits its kind and the phase's towns."""
    shape = draw_shape(kind, mirror)
    if len(draw.towns) != shape.towns or len(draw.packs) != shape.packs or len(set(draw.words)) != len(draw.words):
        raise TradeError(f"a trade of this kind starts with {shape.size} different towns, not {len(draw.words)}")
    if not set(draw.words) <= set(allowed_towns):
        raise TradeError("the trade started with a town that is not allowed in this phase")
    if len(draw.heroes) != shape.heroes:
        raise TradeError(f"a trade of this kind starts with {shape.heroes} heroes, not {len(draw.heroes)}")
    if shape.heroes and heroes is not None and template is not None:
        check_heroes_fit(draw.towns, mirror, draw.heroes, hero_pool_of(heroes, template, draw.towns))


# --- the draws -----------------------------------------------------------------------------------------------


def _available(allowed_towns: tuple[str, ...], banned: tuple[str, ...] = ()) -> list[str]:
    return [town for town in dict.fromkeys(allowed_towns) if town not in banned]


def draw_pair(
    allowed_towns: tuple[str, ...], random_source: random.Random | None = None, banned: tuple[str, ...] = ()
) -> tuple[str, str]:
    """Two different towns at random from the allowed ones that are not banned, each equally likely."""
    available = _available(allowed_towns, banned)
    if len(available) < 2:
        raise TradeError("At least two different towns must be left to draw a pair.")
    first, second = (random_source or random).sample(available, 2)
    return first, second


def draw_town(
    allowed_towns: tuple[str, ...], random_source: random.Random | None = None, banned: tuple[str, ...] = ()
) -> tuple[str]:
    """One town at random from the allowed ones that are not banned, each equally likely (the town of a mirror)."""
    available = _available(allowed_towns, banned)
    if not available:
        raise TradeError("At least one town must be left to draw.")
    return ((random_source or random).choice(available),)


def draw_with_packs(
    allowed_towns: tuple[str, ...], random_source: random.Random | None = None, banned: tuple[str, ...] = ()
) -> Draw:
    """A pair of towns and two packs of three, eight different allowed towns. The pair is drawn from the towns that
    are not banned; the packs from the other allowed towns, so a banned town may come up in a pack."""
    source = random_source or random
    pool = _available(allowed_towns)
    if len(pool) < PACK_COUNT * PACK_SIZE + 2:
        raise TradeError("At least eight different towns must be allowed to draw the pair and the two packs.")
    candidates = _available(allowed_towns, banned)
    if len(candidates) < 2:
        raise TradeError("At least two towns that are not banned must be left to draw the pair.")
    pair = tuple(source.sample(candidates, 2))
    rest = [town for town in pool if town not in pair]
    return Draw(pair, tuple(source.sample(rest, PACK_COUNT * PACK_SIZE)))


def draw_start(
    kind: TradeKind,
    mirror: bool,
    allowed_towns: tuple[str, ...],
    random_source: random.Random | None = None,
    banned: tuple[str, ...] = (),
    heroes: Catalogue | None = None,
    template: Entry | None = None,
) -> Draw:
    """What the bot draws for a trade of this kind. A roll draws the same, with the towns banned so far. A roulette
    that draws its heroes with the towns needs the hero catalogue and the template (HeroDrawError if there are too few)."""
    if kind.has_packs:
        draw = draw_with_packs(allowed_towns, random_source, banned)
    elif mirror:
        draw = Draw(draw_town(allowed_towns, random_source, banned))
    else:
        draw = Draw(draw_pair(allowed_towns, random_source, banned))
    if draw_shape(kind, mirror).heroes:
        if heroes is None or template is None:
            raise HeroDrawError("The heroes of this trade cannot be drawn without the hero catalogue.")
        pool = hero_pool_of(heroes, template, draw.towns)
        draw = Draw(draw.towns, draw.packs, pick_heroes(draw.towns, mirror, pool, random_source))
    return draw
