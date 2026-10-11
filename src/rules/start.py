"""Rules for starting a match. Plain Python: no Discord objects in here, so tests can cover it."""


class StartError(ValueError):
    """The start command cannot be accepted. The message is shown to the player."""


def check_opponent(starter_id: int, opponent_id: int, opponent_is_bot: bool) -> None:
    """Raise StartError unless the opponent is another human."""
    if opponent_id == starter_id:
        raise StartError("You cannot play a match against yourself.")
    if opponent_is_bot:
        raise StartError("You cannot play a match against a bot.")
