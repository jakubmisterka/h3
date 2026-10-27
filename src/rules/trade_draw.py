"""What the bot draws for a trade, and what a draw must look like to be believed.

Plain Python: no Discord objects in here, so tests can cover it. A `Draw` is everything the bot drew for a trade at
one moment: the town(s) the players play and, for a trade with computer-player packs, the six towns of the two
packs. A roll draws again. `draw_shape` says how many towns each kind draws, so the draws, the checks of a
thread's records and the reading of them all use one table.

A town banned in a roll is banned for the players only: it stays out of the town(s) the players play, but it may
come up in a pack of computer-player towns.
"""

import random
from dataclasses import dataclass

from rules.trade_kinds import PACKS_KIND, TradeKind

PACK_SIZE = 3  # towns in a pack
PACK_COUNT = 2  # packs


class TradeError(ValueError):
    """The trade cannot do what was asked. The message is shown to the player."""


@dataclass(frozen=True)
class Draw:
    """What the bot drew: the town(s) the players play (two, or one for a mirror), and the six towns of the packs
    (pack1 first) when the trade has packs."""

    towns: tuple[str, ...]
    packs: tuple[str, ...] = ()

    @property
    def words(self) -> tuple[str, ...]:
        """Every town drawn, in the order the records write them."""
        return self.towns + self.packs

    def pack(self, number: int) -> tuple[str, ...]:
        """The three towns of pack `number` (0 for pack1, 1 for pack2)."""
        return self.packs[number * PACK_SIZE : (number + 1) * PACK_SIZE]


@dataclass(frozen=True)
class DrawShape:
    """How many towns a kind of trade draws."""

    towns: int
    packs: int

    @property
    def size(self) -> int:
        return self.towns + self.packs


def draw_shape(kind: TradeKind, mirror: bool) -> DrawShape:
    return DrawShape(1 if mirror else 2, PACK_COUNT * PACK_SIZE if kind.name == PACKS_KIND else 0)


_PAIR_RULE = "The new pair must be two different allowed towns that are not banned."


def check_draw(draw: Draw, kind: TradeKind, mirror: bool, allowed_towns: tuple[str, ...], banned: tuple[str, ...]) -> None:
    """Raise TradeError unless `draw` is what a trade of this kind draws: the right number of different allowed
    towns, and none of the town(s) the players play banned (a banned town may be in a pack)."""
    plain = not mirror and kind.name != PACKS_KIND
    shape = draw_shape(kind, mirror)
    if len(draw.towns) != shape.towns or len(draw.packs) != shape.packs or len(set(draw.words)) != len(draw.words):
        raise TradeError(_PAIR_RULE if plain else "The new draw has the wrong number of towns, or repeats one.")
    if not set(draw.words) <= set(allowed_towns) or set(draw.towns) & set(banned):
        raise TradeError(_PAIR_RULE if plain else "The new draw must be allowed towns, and the players' town(s) must not be banned.")


def check_start(draw: Draw, kind: TradeKind, mirror: bool, allowed_towns: tuple[str, ...]) -> None:
    """Raise TradeError unless what a trade started with fits its kind and the phase's towns."""
    shape = draw_shape(kind, mirror)
    if len(draw.towns) != shape.towns or len(draw.packs) != shape.packs or len(set(draw.words)) != len(draw.words):
        raise TradeError(f"a trade of this kind starts with {shape.size} different towns, not {len(draw.words)}")
    if not set(draw.words) <= set(allowed_towns):
        raise TradeError("the trade started with a town that is not allowed in this phase")


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
) -> Draw:
    """What the bot draws for a trade of this kind. A roll draws the same, with the towns banned so far."""
    if kind.name == PACKS_KIND:
        return draw_with_packs(allowed_towns, random_source, banned)
    if mirror:
        return Draw(draw_town(allowed_towns, random_source, banned))
    return Draw(draw_pair(allowed_towns, random_source, banned))
