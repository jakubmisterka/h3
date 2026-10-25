"""The short lines that say what is played on a template: the same words in `/info`, in the rules at the start of a
match, in the announcement of a game, and in the lobby settings.

Plain functions from `Settings` (see `template_settings.py`) to text. A fact that is not stated gives no line at all,
and nothing is guessed in its place. The timer is shown only in its compact form, the way it is typed into the lobby.
"""

from rules.template_settings import Settings

# The settings a tournament or a template states, in the order they are shown.
SETTINGS = ("timer", "map_size", "roads", "ai", "sim_turns")
# The ones that are typed into the lobby, which the lobby settings of a game repeat. The recommended length of
# simultaneous turns is guidance, not something typed in.
LOBBY_SETTINGS = ("timer", "map_size", "roads", "ai")


def setting_value(name: str, settings: Settings) -> str | None:
    """The value of one setting as short text, or None if it is not stated. For naming what differs in a phase."""
    value = getattr(settings, name)
    return None if value is None else str(value)


def setting_line(name: str, settings: Settings) -> str | None:
    """The line for one setting, or None if it is not stated."""
    value = getattr(settings, name)
    if value is None:
        return None
    if name == "timer":
        return f"Timer: {value}"
    if name == "map_size":
        return f"Map: {value}"
    if name == "roads":
        return "No roads" if value == "none" else f"Roads: {value}"
    if name == "ai":
        return "No AI players" if value == 0 else f"AI players: {value}"
    if name == "additional_rules":
        return f"Additional rules: {value}"
    return f"Sim turns until {value}"


def fixed_lines(settings: Settings) -> list[str]:
    """The facts of the template itself, which do not change from phase to phase: a mirror, and where to get it."""
    lines = []
    if settings.mirror:
        lines.append("Mirror: both players get the same town")
    if settings.built_in:
        lines.append("Built into HotA")
    elif settings.download:
        lines.append(f"Download: <{settings.download}>")  # the angle brackets keep Discord from unfolding a preview
    return lines


def fact_lines(settings: Settings) -> list[str]:
    """Every stated fact, one short line each, in a fixed order."""
    lines = fixed_lines(settings)
    lines += [line for name in SETTINGS if (line := setting_line(name, settings))]
    return lines


def lobby_lines(settings: Settings) -> list[str]:
    """The stated settings that are typed into the lobby, one line each."""
    return [line for name in LOBBY_SETTINGS if (line := setting_line(name, settings))]
