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
from rules.selection import Action, known_games, next_step, player_steps, replay
from rules.trade import TradeLog, signed, replay_trades
from state import Match, MatchError, Record, rebuild


@dataclass(frozen=True)
class Situation:
    match: Match
    fmt: Format
    phase: Phase
    actions: list[Action]  # the bans and picks so far (none when the players agreed on the template)
    games: tuple[str, ...]  # the template ids of the games decided so far, in play order
    log: TradeLog  # the trades

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
    log = replay_trades(match.trade_records, games, (match.a, match.b), registry.templates)
    return Situation(match, fmt, phase, actions, games, log)


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
    next_section = "" if trade.finished else f", next: {trade.section.replace('_', ' ')}"
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
