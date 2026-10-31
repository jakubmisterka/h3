"""The short lines that say what is played on a template: the same words in `/info`, in the rules at the start of a
match, in the announcement of a game, and in the lobby settings.

Plain functions from `Settings` (see `template_settings.py`) to text. A fact that is not stated gives no line at all,
and nothing is guessed in its place. The timer is shown only in its compact form, the way it is typed into the lobby.
"""

from rules.catalogue import Catalogue
from rules.template_settings import Settings
from rules.trade_kinds import trade_rule

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


ALTERNATIVES_START = "By agreement the template can be changed to "


def alternatives_line(settings: Settings, templates: Catalogue | None) -> str | None:
    """"By agreement the template can be changed to `h3dm1` ([download](<link>))": each alternative by its name, with
    a link where it is not built into HotA. None when there are none."""
    if not settings.alternatives or templates is None:
        return None
    named = []
    for alternative in settings.alternatives:
        entry = templates.find(alternative)
        link = entry.details.get("download")
        named.append(f"`{entry.name}`" + (f" ([download](<{link}>))" if link and not entry.details.get("built_in") else ""))
    return ALTERNATIVES_START + " or ".join(named)


def announcement_lines(settings: Settings, info_hint: str | None = None, templates: Catalogue | None = None) -> list[str]:
    """What players need when a template is announced, one short message each: where to get it if it is not built into
    HotA, the timer, the recommended simultaneous turns, how its trade is run, the alternatives players may agree on
    (which needs the `templates` catalogue to name them), and how to find out more (`info_hint`).
    The map size, roads and computer players are left out: `/info` and the lobby settings give them."""
    lines = []
    if settings.download and not settings.built_in:
        lines.append(f"Not built into HotA: [download](<{settings.download}>)")  # the angle brackets keep Discord from unfolding a preview
    if settings.timer:
        lines.append(f"Timer: `{settings.timer}`")
    if settings.sim_turns:
        lines.append(f"Sim turns: `{settings.sim_turns}`")
    lines.append(trade_rule(settings.trade, settings.mirror))
    if alternatives := alternatives_line(settings, templates):
        lines.append(alternatives)
    if info_hint:
        lines.append(info_hint)
    return lines


def info_hint(mode_id: str, template_id: str) -> str:
    """How to find out more about a template in a mode."""
    return f"More about this template: /info with mode `{mode_id}` and template `{template_id}`"


def lobby_lines(settings: Settings) -> list[str]:
    """The stated settings that are typed into the lobby, one line each."""
    return [line for name in LOBBY_SETTINGS if (line := setting_line(name, settings))]
