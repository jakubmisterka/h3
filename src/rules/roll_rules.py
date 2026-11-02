"""The roll rules that apply to one template in one phase.

A format may write roll rules in up to three places: for the whole tournament, on a template in the
tournament's list, and on a template in one phase's pool. They are stacked, the most specific
winning field by field, on top of the built-in defaults:

    built-in defaults -> tournament -> template in the list -> template in the phase's pool
"""

from dataclasses import dataclass

from rules.formats import Format, Phase


@dataclass(frozen=True)
class RollRules:
    roll_cost: int  # gold a player pays to roll the town pair
    rolls_per_player: int
    max_roll_bans: int  # towns a player may ban when rolling, 0 up to this


DEFAULT_ROLL_RULES = RollRules(roll_cost=500, rolls_per_player=1, max_roll_bans=2)


def effective_roll_rules(fmt: Format, phase: Phase, template: str) -> RollRules:
    """The roll rules for `template` when it is played in `phase` of `fmt`."""
    in_list = next((entry for entry in fmt.templates if entry.template == template), None)
    in_pool = next((entry for entry in phase.pool if entry.template == template), None)
    if in_list is None:
        raise ValueError(f"{template!r} is not one of the templates of {fmt.name}")
    if in_pool is None:
        raise ValueError(f"{template!r} is not in the pool of the phase {phase.name!r}")

    rules = {
        "roll_cost": DEFAULT_ROLL_RULES.roll_cost,
        "rolls_per_player": DEFAULT_ROLL_RULES.rolls_per_player,
        "max_roll_bans": DEFAULT_ROLL_RULES.max_roll_bans,
    }
    for written in (fmt.roll_rules, in_list.roll_rules, in_pool.roll_rules):  # least to most specific
        rules.update(written)
    return RollRules(**rules)
