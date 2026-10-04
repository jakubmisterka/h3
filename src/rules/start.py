"""Starting a match: checking the start command and doing the coinflip."""

import random
from dataclasses import dataclass

from rules.catalogue import Catalogue
from rules.errors import UserError
from rules.formats import Format, Phase


class StartError(UserError):
    """The start command cannot be accepted. The message is shown to the player."""


@dataclass(frozen=True)
class StartPlan:
    phase: Phase
    template: str | None  # only for phases where players agree on the template


def plan_start(
    fmt: Format,
    phase_name: str | None,
    template_text: str | None,
    templates: Catalogue,
    starter_id: int,
    opponent_id: int,
    opponent_is_bot: bool,
) -> StartPlan:
    """Check a start command and decide which phase and template the match uses."""
    if opponent_id == starter_id:
        raise StartError("You cannot play a match against yourself.")
    if opponent_is_bot:
        raise StartError("You cannot play a match against a bot.")

    phase = _choose_phase(fmt, phase_name)

    if not phase.agreed:
        if template_text:
            raise StartError(f"{fmt.name} chooses the template with bans and picks, so do not name one.")
        return StartPlan(phase, None)

    allowed = ", ".join(phase.pool)
    if not template_text:
        raise StartError(f"This mode needs an agreed template. Allowed templates: {allowed}.")
    entry = templates.find(template_text)
    if entry is None or entry.id not in phase.pool:
        raise StartError(f"{template_text!r} is not allowed here. Allowed templates: {allowed}.")
    return StartPlan(phase, entry.id)


def _choose_phase(fmt: Format, phase_name: str | None) -> Phase:
    if len(fmt.phases) == 1:
        only = fmt.phases[0]
        if phase_name and phase_name.strip().lower() != only.name.lower():
            raise StartError(f"{fmt.name} has a single phase, {only.name!r}, so no phase is needed.")
        return only

    names = ", ".join(p.name for p in fmt.phases)
    if not phase_name:
        raise StartError(f"Which phase is this match in? Choose one of: {names}.")
    for phase in fmt.phases:
        if phase.name.lower() == phase_name.strip().lower():
            return phase
    raise StartError(f"{phase_name!r} is not a phase of {fmt.name}. Choose one of: {names}.")


_SYSTEM_RANDOM = random.SystemRandom()


def coinflip(player_1: int, player_2: int, rng: random.Random = _SYSTEM_RANDOM) -> tuple[int, int]:
    """Return (A, B): A is the coinflip winner. Each player has an equal chance."""
    return (player_1, player_2) if rng.randrange(2) == 0 else (player_2, player_1)


def check_player(players: tuple[int, int], user_id: int) -> None:
    """Only the two players of a match may change it."""
    if user_id not in players:
        raise StartError("Only the two players of this match can use this command.")
