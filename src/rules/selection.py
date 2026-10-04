"""Template selection: the bans and picks that turn the pool into the games to play.

Everything here works on a `Match` (see state.py) and is plain Python. A and B are
the coinflip winner and the other player; the format says who acts in each step.
"""

from dataclasses import dataclass

from rules.catalogue import Catalogue
from rules.errors import UserError
from rules.formats import Step
from state import Match


class SelectionError(UserError):
    """A ban or pick cannot be accepted. The message is shown to the player."""


@dataclass(frozen=True)
class Progress:
    remaining: tuple[str, ...]  # templates still in the pool
    banned: tuple[str, ...]
    picked: tuple[str, ...]
    next_step: Step | None  # None when every step is done


@dataclass(frozen=True)
class Game:
    number: int  # 1-based, in play order
    template: str
    source: str  # "pick_1", "pick_2", ..., "decider" or "agreed"


def progress(match: Match) -> Progress:
    banned = [e.data["template"] for e in match.selection if e.type == "ban"]
    picked = [e.data["template"] for e in match.selection if e.type == "pick"]
    taken = set(banned) | set(picked)
    steps = match.phase.steps
    done = len(match.selection)
    return Progress(
        remaining=tuple(t for t in match.phase.pool if t not in taken),
        banned=tuple(banned),
        picked=tuple(picked),
        next_step=steps[done] if done < len(steps) else None,
    )


def is_complete(match: Match) -> bool:
    """True when there is nothing left to ban or pick (also for agreed-template phases)."""
    return match.phase.agreed or progress(match).next_step is None


def next_actor(match: Match) -> int | None:
    """The user whose step it is, or None when selection is complete."""
    step = progress(match).next_step
    return None if step is None else match.user_of(step.who)


def check_step(match: Match, user_id: int, action: str, template_text: str, templates: Catalogue) -> str:
    """Check a ban or pick and return the template id. Raises SelectionError with the reason."""
    if match.phase.agreed:
        raise SelectionError("This mode has no bans or picks: the template was agreed when the match started.")
    state = progress(match)
    step = state.next_step
    if step is None:
        raise SelectionError("Selection is finished, there is nothing left to ban or pick.")

    expected_user = match.user_of(step.who)
    if user_id != expected_user:
        raise SelectionError(f"It is not your turn. <@{expected_user}> ({step.who}) must {step.do} now.")
    if action != step.do:
        raise SelectionError(f"A {step.do} is expected now, not a {action}. Use `/{step.do}`.")

    entry = templates.find(template_text)
    if entry is None or entry.id not in state.remaining:
        raise SelectionError(f"{template_text!r} is not available. Remaining: {', '.join(state.remaining)}.")
    return entry.id


def games(match: Match) -> list[Game]:
    """The games to play, in the order the format states. Needs selection to be complete."""
    if match.phase.agreed:
        return [Game(1, match.agreed_template, "agreed")]
    state = progress(match)
    if state.next_step is not None:
        raise SelectionError("Selection is not finished yet.")
    by_source = {f"pick_{i}": template for i, template in enumerate(state.picked, start=1)}
    by_source["decider"] = state.remaining[0]
    return [Game(number, by_source[source], source) for number, source in enumerate(match.phase.game_order, start=1)]


def games_text(match: Match) -> str:
    lines = [f"Game {g.number}: **{g.template}**" for g in games(match)]
    return "Games to play:\n" + "\n".join(lines)


def prompt(match: Match) -> str:
    """Say whose step it is."""
    step = progress(match).next_step
    user = match.user_of(step.who)
    return f"<@{user}> ({step.who}), it is your turn to **{step.do}**. Use `/{step.do}` and choose a template."


def pool_text(match: Match) -> str:
    state = progress(match)
    lines = [f"Remaining ({len(state.remaining)}): {', '.join(state.remaining)}"]
    if state.banned:
        lines.append(f"Banned: {', '.join(state.banned)}")
    if state.picked:
        lines.append(f"Picked: {', '.join(state.picked)}")
    return "\n".join(lines)


def step_text(match: Match, user_id: int, action: str, template: str) -> str:
    """The message for a step that was just accepted; `match` already includes the step."""
    verb = "banned" if action == "ban" else "picked"
    lines = [f"<@{user_id}> {verb} **{template}**."]
    if is_complete(match):
        lines.append(games_text(match))
    else:
        lines += [pool_text(match), prompt(match)]
    return "\n".join(lines)


def start_text(match: Match) -> str:
    """What the bot says right after the coinflip."""
    if match.phase.agreed:
        return games_text(match)
    return "\n".join([pool_text(match), prompt(match)])
