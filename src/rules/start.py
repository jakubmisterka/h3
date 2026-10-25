"""Rules for starting a match. Plain Python: no Discord objects in here, so tests can cover it."""

import random

from rules.catalogue import Catalogue
from rules.formats import Format, Phase
from rules.info import AUTOCOMPLETE_LIMIT, find_phase, template_selection_line
from rules.registry import Registry


###### Wording: what the bot says when a match starts ##########################################################
# The sentences the bot says. To change a wording, change it here; the logic that decides when is further down.

NOT_IN_A_TEXT_CHANNEL = "Start a match in a normal text channel, not inside a thread."


def coinflip_announcement(winner: str, loser: str, phase: Phase, template_named: bool = False) -> str:
    """What the thread says after the coinflip. `winner` and `loser` are mentions. The winner is A.
    With a template named at the start there are no bans or picks, so nobody acts first."""
    if phase.agreed or template_named:
        return f"Coinflip: {winner} wins and is A, {loser} is B."
    first = "bans" if phase.steps[0].do == "ban" else "picks"
    return f"Coinflip: {winner} wins and is A, so {winner} {first} first. {loser} is B."


def rules_announcement(phase: Phase, template_name: str | None, pool_names: list[str]) -> list[str]:
    """The rules of the phase, one short message per rule, posted before the coinflip so both players know what comes."""
    if template_name is not None:  # no bans or picks: one game, straight to the trade
        messages = [f"Best of {phase.best_of}" if phase.agreed else "One game"]
        messages.append(f"The players agreed on the template: {template_name}" if phase.agreed else f"The template: {template_name}")
    else:
        messages = [f"Best of {phase.best_of}"]
        # "AB: A bans, B bans, then decider" is the short notation, then its meaning, each on its own
        notation, _, meaning = template_selection_line(phase.steps).partition(": ")
        messages.append(f"Template Selection: {notation}" if meaning else notation)
        if meaning:
            messages.append(meaning)
    messages.append("The winner of the coinflip will be player A, the other player is B")
    if template_name is None:
        messages.append(f"Templates: {', '.join(pool_names)}")
    return messages


def thread_refused_text(reason: str) -> str:
    """Text for a refusal from Discord that was not predicted. The permission check usually catches the cause first."""
    return f"Discord refused to create the thread ({reason}). Please ask a server admin to check my permissions."


def match_announcement(starter: str, opponent: str) -> str:
    """The message a public thread hangs off. `starter` and `opponent` are mentions."""
    return f"Match: {starter} vs {opponent}"


def private_thread_link(opponent: str, thread: str) -> str:
    """The private reply to the player who started a match in a private thread."""
    return f"Your private match thread with {opponent}: {thread}"


def match_started_text(
    starter: str, opponent: str, mode_name: str, mode_id: str, phase_name: str, template_id: str | None
) -> str:
    """The text of the match started record. The first two mentions are the players and the first `quoted` words the
    mode, the phase and the agreed template, which is how the record is read back."""
    wording = f"Mode: {mode_name} (`{mode_id}`), phase `{phase_name}`"
    if template_id:
        wording += f", template `{template_id}`"
    return f"Match started: {starter} vs {opponent}. {wording}. This is your match thread."


################################################################################################################


class StartError(ValueError):
    """The start command cannot be accepted. The message is shown to the player."""


def check_opponent(starter_id: int, opponent_id: int, opponent_is_bot: bool) -> None:
    """Raise StartError unless the opponent is another human."""
    if opponent_id == starter_id:
        raise StartError("You cannot play a match against yourself.")
    if opponent_is_bot:
        raise StartError("You cannot play a match against a bot.")


def choose_phase(fmt: Format, text: str | None) -> Phase:
    """The phase a match is played in. A mode with one phase needs no answer; with several, the player must name one."""
    if len(fmt.phases) == 1 and not text:
        return fmt.phases[0]
    names = ", ".join(phase.name for phase in fmt.phases)
    if not text:
        raise StartError(f"{fmt.name} has several phases, so say which one this match is in: {names}.")
    phase = find_phase(fmt, text)
    if phase is None:
        raise StartError(f"{fmt.name} has no phase called {text!r}. Its phases: {names}.")
    return phase


def choose_template(phase: Phase, text: str | None, templates: Catalogue) -> str | None:
    """The template id named for the match, or None when none was named (the phase then chooses by bans and picks).

    Any phase accepts a template from its pool, which makes the match one game with no selection. Where the players
    agree on the template, naming one is required."""
    allowed = [templates.find(template_id) for template_id in phase.pool_ids]
    allowed_names = ", ".join(entry.name for entry in allowed)
    if not text:
        if phase.agreed:
            raise StartError(f"In this phase the players agree on the template, so name one. Allowed: {allowed_names}.")
        return None
    entry = templates.find(text)
    if entry is None or entry not in allowed:
        raise StartError(f"{text!r} is not allowed in this phase. Allowed: {allowed_names}.")
    return entry.id


def coinflip(player_1: int, player_2: int, random_source: random.Random | None = None) -> int:
    """The id of the coinflip winner (A). Pass a `random.Random` to make the outcome repeatable."""
    return (random_source or random).choice([player_1, player_2])


# --- what the start command offers while a player is typing ------------------------------------------


def mode_choices(registry: Registry, typed: str) -> list[tuple[str, str]]:
    """(shown name, value) of the modes a match can be started in that match what has been typed."""
    wanted = typed.strip().lower()
    return [
        (fmt.name, fmt.id)
        for fmt in registry.modes_for_new_matches()
        if wanted in fmt.name.lower() or wanted in fmt.id.lower()
    ][:AUTOCOMPLETE_LIMIT]


def template_choices(registry: Registry, mode_text: str, phase_text: str | None, typed: str) -> list[tuple[str, str]]:
    """(display name, template id) of the templates players can agree on, once the mode and phase are chosen."""
    fmt = registry.find_format(mode_text)
    if fmt is None:
        return []
    try:
        phase = choose_phase(fmt, phase_text)
    except StartError:
        return []
    wanted = typed.strip().lower()
    entries = [registry.templates.find(template_id) for template_id in phase.pool_ids]
    return [(e.name, e.id) for e in entries if wanted in e.name.lower() or wanted in e.id.lower()][:AUTOCOMPLETE_LIMIT]
