"""Template Selection: the bans and picks that turn a pool of templates into the games to play.

Plain Python: no Discord objects in here, so tests can cover it. A phase's steps (see `formats.py`)
say who bans or picks and in what order. What has happened so far is a list of `Action`s, oldest
first. Everything else (whose step is next, what is left, the games) is worked out from the steps
and those actions, so the match never needs to store anything but the actions.

Players are the letters "A" (the coinflip winner) and "B"; the command layer knows who is who.
"""

from dataclasses import dataclass

from rules.catalogue import Catalogue
from rules.formats import Step


class SelectionError(ValueError):
    """The ban or pick cannot be accepted. The message is shown to the player."""


@dataclass(frozen=True)
class Action:
    who: str  # "A" or "B"
    do: str  # "ban" or "pick"
    template: str  # template id


def player_steps(steps: tuple[Step, ...]) -> tuple[Step, ...]:
    """The steps a player acts in. The decider is left out: nobody acts in it."""
    return tuple(step for step in steps if step.do != "decider")


def has_decider(steps: tuple[Step, ...]) -> bool:
    return any(step.do == "decider" for step in steps)


def next_step(steps: tuple[Step, ...], actions: list[Action]) -> Step | None:
    """The step a player must act in now, or None when every ban and pick has been made."""
    acting = player_steps(steps)
    return acting[len(actions)] if len(actions) < len(acting) else None


def remaining(pool: tuple[str, ...], actions: list[Action]) -> tuple[str, ...]:
    """The templates of the pool that nobody has banned or picked yet, in pool order."""
    gone = {action.template for action in actions}
    return tuple(template for template in pool if template not in gone)


def check_action(steps: tuple[Step, ...], actions: list[Action], who: str, do: str) -> None:
    """Raise SelectionError unless `who` may do `do` now. Says whose step it is, or which action is expected."""
    step = next_step(steps, actions)
    if step is None:
        raise SelectionError("The bans and picks are finished.")
    if who != step.who:
        raise SelectionError(f"It is player {step.who}'s step, not yours.")
    if do != step.do:
        raise SelectionError(f"A {step.do} is expected now, not a {do}.")


def choose_available(text: str, remaining_ids: tuple[str, ...], templates: Catalogue) -> str:
    """The id of the template a player named, if it is still available. Otherwise the remaining ones are listed."""
    entry = templates.find(text)
    if entry is not None and entry.id in remaining_ids:
        return entry.id
    names = ", ".join(templates.find(template).name for template in remaining_ids)
    raise SelectionError(f"{text!r} is not available. Remaining templates: {names}.")


def games(steps: tuple[Step, ...], pool: tuple[str, ...], actions: list[Action]) -> tuple[str, ...]:
    """The template ids of the games, in play order: the picks as they were made, then the decider's template."""
    if next_step(steps, actions) is not None:
        raise SelectionError("The bans and picks are not finished yet.")
    order = [action.template for action in actions if action.do == "pick"]
    if has_decider(steps):
        order.append(remaining(pool, actions)[0])  # the pool and the steps are the same size, so one is left
    return tuple(order)


def replay(
    steps: tuple[Step, ...], pool: tuple[str, ...], a_id: int, b_id: int, taken: tuple[tuple[int, str, str], ...]
) -> list[Action]:
    """The actions recorded in a thread, checked against the phase's steps one by one.

    `taken` holds (player id, "ban" or "pick", template id) in the order recorded. A record that does not
    fit (wrong player, wrong action, a template that is gone) means the thread cannot be trusted, and is reported.
    """
    letter = {a_id: "A", b_id: "B"}
    actions: list[Action] = []
    for number, (player_id, do, template) in enumerate(taken, start=1):
        try:
            if player_id not in letter:
                raise SelectionError("it was made by somebody who is not a player of this match")
            check_action(steps, actions, letter[player_id], do)
            if template not in remaining(pool, actions):
                raise SelectionError(f"{template!r} was not available")
        except SelectionError as e:
            raise SelectionError(f"Ban or pick number {number} in this thread does not follow the rules: {e}") from e
        actions.append(Action(letter[player_id], do, template))
    return actions


def _names(templates: Catalogue, ids) -> str:
    return ", ".join(templates.find(template).name for template in ids) or "none"


def games_message(order: tuple[str, ...], templates: Catalogue) -> str:
    """The games in play order, one per line."""
    lines = [f"Game {number}: {templates.find(template).name}" for number, template in enumerate(order, start=1)]
    return "\n".join(lines)


def after_a_step(
    steps: tuple[Step, ...], pool: tuple[str, ...], actions: list[Action], mentions: dict[str, str], templates: Catalogue
) -> list[str]:
    """What the thread says after the coinflip and after each ban or pick: the pool, then what comes next.

    `mentions` maps "A" and "B" to the mentions of the two players. Once the bans and picks are done,
    the last message lists the games in play order.
    """
    left = remaining(pool, actions)
    lines = [f"Remaining ({len(left)}): {_names(templates, left)}"]
    banned = [action.template for action in actions if action.do == "ban"]
    picked = [action.template for action in actions if action.do == "pick"]
    if banned or picked:
        lines.append(f"Banned: {_names(templates, banned)}. Picked: {_names(templates, picked)}.")
    messages = ["\n".join(lines)]

    step = next_step(steps, actions)
    if step is not None:
        number = len(actions) + 1
        total = len(player_steps(steps))
        command = "/ban" if step.do == "ban" else "/pick"
        messages.append(f"Step {number} of {total}: {mentions[step.who]} {step.do}s a template with {command}")
    else:
        messages.append("The bans and picks are done. The games:\n" + games_message(games(steps, pool, actions), templates))
    return messages


def known_games(steps: tuple[Step, ...], pool: tuple[str, ...], actions: list[Action]) -> tuple[str, ...]:
    """The games whose template is already decided, in play order.

    The k-th game is known as soon as the k-th pick is made. The decider's game (the last one) is only known
    once every ban and pick is done. So a trade can start while the selection is still going.
    """
    known = [action.template for action in actions if action.do == "pick"]
    if next_step(steps, actions) is None and has_decider(steps):
        known.append(remaining(pool, actions)[0])
    return tuple(known)
