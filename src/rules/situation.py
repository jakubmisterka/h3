"""Where a match stands, worked out from the records of its thread, and a summary of it in words.

Plain Python: no Discord objects in here, so tests can cover it. The records are turned into the match
(`state.rebuild`), its bans and picks (`selection.replay`) and its trades (`trade.replay_trades`), each of which
checks what it reads and refuses to guess. Every command that changes or shows a match starts from here.
"""

from dataclasses import dataclass

from rules.catalogue import Catalogue
from rules.formats import Format, Phase
from rules.info import find_phase
from rules.registry import Registry
from rules.roll_rules import RollRules, effective_roll_rules
from rules.selection import Action, after_a_step, known_games, next_step, player_steps, replay
from rules.trade import TradeLog, next_message, pair_names, replay_trades, signed
from state import TRADE_TYPES, Match, MatchError, Record, rebuild, steps_that_count


###### Wording: what the bot says about the thread itself ######################################################
# The sentences the bot says. To change a wording, change it here; the logic that decides when is further down.

NOT_IN_THREAD = "Use this command inside a match thread."


def unreadable(error: Exception) -> str:
    """What the bot says when the records of a thread do not add up. It never guesses."""
    return f"I can't read this thread: {error}"


################################################################################################################


@dataclass(frozen=True)
class Situation:
    match: Match
    fmt: Format
    phase: Phase
    actions: list[Action]  # the bans and picks so far (none when the players agreed on the template)
    games: tuple[str, ...]  # the template ids of the games decided so far, in play order
    log: TradeLog  # the trades
    last_step: Record | None  # the latest step that counts (None: nothing but the start and the coinflip yet)

    def roll_rules(self, template: str) -> RollRules:
        """The roll rules of a template in this match's phase."""
        return effective_roll_rules(self.fmt, self.phase, template)

    @property
    def players(self) -> tuple[int, int]:
        return self.match.a, self.match.b

    @property
    def mentions(self) -> dict[int, str]:
        return {self.match.a: f"<@{self.match.a}>", self.match.b: f"<@{self.match.b}>"}


def situation_of(registry: Registry, records: list[Record]) -> Situation:
    """The situation recorded in a thread. Raises (a ValueError with a message for the player) when it cannot be trusted."""
    match = rebuild(records)
    fmt = registry.find_format(match.mode)
    phase = find_phase(fmt, match.phase) if fmt else None
    if phase is None:
        raise MatchError(f"This match is in {match.mode!r}, phase {match.phase!r}, which I no longer have.")
    if phase.agreed:
        actions: list[Action] = []
        games = (match.template,)
    else:
        actions = replay(phase.steps, phase.pool_ids, match.a, match.b, match.taken)
        games = known_games(phase.steps, phase.pool_ids, actions)
    rules_of = lambda template: effective_roll_rules(fmt, phase, template)  # noqa: E731
    log = replay_trades(match.trade_records, games, (match.a, match.b), registry.templates, phase.allowed_towns, rules_of)
    steps = steps_that_count(records)
    return Situation(match, fmt, phase, actions, games, log, steps[-1] if steps else None)


def _selection_line(s: Situation) -> str:
    if s.phase.agreed:
        return "Template Selection: the players agreed on the template"
    step = next_step(s.phase.steps, s.actions)
    if step is None:
        return "Template Selection: done"
    total = len(player_steps(s.phase.steps))
    return f"Template Selection: step {len(s.actions) + 1} of {total}, {s.mentions[s.match.a if step.who == 'A' else s.match.b]} {step.do}s"


def _game_line(s: Situation, number: int, templates: Catalogue, towns: Catalogue) -> str:
    if number > len(s.games):
        return f"Game {number}: not decided yet"
    name = templates.find(s.games[number - 1]).name
    trade = s.log.trades.get(number)
    if trade is None:
        return f"Game {number}: {name}, trade not started"
    gold = trade.gold
    a, b = trade.players
    state = "trade done" if trade.finished else ("trade open" if s.log.open_game == number else "trade closed, not finished")
    if trade.finished:
        next_section = ""
    elif trade.section == "color_bid":
        next_section = ", next: color bid"
    else:  # the roll is a side option until the town bid is reported, so the town bid is what comes next
        rolls = " (rolls still open)" if trade.section == "town_roll" else ""
        next_section = f", next: town bid {pair_names(towns, trade.pair)}{rolls}"
    difference = f"gold difference {s.mentions[a]} {signed(gold[a] - trade.start_gold)} / {s.mentions[b]} {signed(gold[b] - trade.start_gold)}"
    return f"Game {number}: {name}, {state}{next_section}, {difference}"


def overview(s: Situation, templates: Catalogue, towns: Catalogue) -> str:
    """The match at a glance: the players, the coinflip, the selection, and each game with its trade."""
    m = s.match
    template = f", template {m.template}" if m.template else ""
    lines = [
        f"Match: <@{m.p1}> vs <@{m.p2}>",
        f"Mode {m.mode}, phase {m.phase}{template}",
        f"Coinflip: <@{m.a}> is A (acts first), <@{m.b}> is B",
        _selection_line(s),
    ]
    lines += [_game_line(s, number, templates, towns) for number in range(1, s.phase.best_of + 1)]
    return "\n".join(lines)


def _start_hint(number: int, template: str, templates: Catalogue) -> str:
    return f"Game {number} is {templates.find(template).name}. Start its trade with /trade start."


def next_steps(s: Situation, templates: Catalogue, towns: Catalogue) -> list[str]:
    """What the players can do now, as the messages the thread shows after any step.

    It depends on the latest step that counts. After a step of the open trade it is that trade's next section (or its
    lobby settings, when it is done). After a ban or a pick, or before any step, it is the selection's next step, and
    the games the last step decided can be traded. Where the players agreed on the template there is no selection, so
    it is the trade of the first game that is not finished.
    """
    trade = s.log.open
    if s.last_step is not None and s.last_step.type in TRADE_TYPES and trade is not None:
        return [next_message(trade, s.mentions, towns, templates)]

    messages: list[str] = []
    if s.phase.agreed:
        for number, template in enumerate(s.games, start=1):
            if number not in s.log.trades or not s.log.trades[number].finished:
                messages.append(_start_hint(number, template, templates))
                break
        return messages

    mentions = {"A": s.mentions[s.match.a], "B": s.mentions[s.match.b]}
    messages += after_a_step(s.phase.steps, s.phase.pool_ids, s.actions, mentions, templates)
    known_before = known_games(s.phase.steps, s.phase.pool_ids, s.actions[:-1]) if s.actions else ()
    for number in range(len(known_before) + 1, len(s.games) + 1):  # the games the last step decided
        messages.append(_start_hint(number, s.games[number - 1], templates))
    return messages
