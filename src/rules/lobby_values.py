"""The values a template or a tournament states about the game that is played, and the checks that read them.

Plain Python: no Discord objects in here, so tests can cover it. Each `check_*` returns the value if it is valid
and otherwise raises `ValueError` with a message that says what the value should look like. Values are kept as
they were written (a timer is shown as `12:00+06:00+02:00`, exactly what is typed into the lobby).
"""

import re

ROAD_TYPES = ("slow", "mid", "fast")  # the game's dirt, gravel and cobblestone roads
MAP_SIZES = ("S", "M", "L", "XL", "H", "XH", "G")
MAX_COMPUTER_PLAYERS = 6  # a game has at most 8 players, and two of them are the humans
MAX_TEXT = 1000  # characters in a description or in additional rules

_TIMER_SHAPE = re.compile(r"^\d{2}:\d{2}\+\d{2}:\d{2}\+\d{2}:\d{2}$")
_MAP_SIZE = re.compile(r"^(" + "|".join(MAP_SIZES) + r")(\+U)?$")


def check_timer(text: object) -> str:
    """A chess timer: `mm:ss+mm:ss+mm:ss`, every part two digits, seconds below 60.

    The first part is the time each player has at the start, the second is added at the beginning of each of their
    turns, the third is added when each fight starts."""
    form = "a timer is written like 12:00+06:00+02:00 (minutes:seconds three times, joined by +, two digits everywhere)"
    if not isinstance(text, str) or not _TIMER_SHAPE.match(text):
        raise ValueError(f"{text!r} is not a timer: {form}")
    for part in text.split("+"):
        if int(part.split(":")[1]) >= 60:
            raise ValueError(f"{text!r} is not a timer: seconds must be below 60 ({part} has too many)")
    return text


def check_game_date(text: object) -> str:
    """A date in the game's calendar as digits: month, week, day. `117` is month 1, week 1, day 7."""
    form = "write month, week and day in digits, like 117 (month 1, week 1, day 7) or 121 (month 1, week 2, day 1)"
    if not isinstance(text, str) or not text.isdigit() or len(text) < 3 or not text.isascii():
        raise ValueError(f"{text!r} is not a date: {form}")
    month, week, day = int(text[:-2]), int(text[-2]), int(text[-1])
    if not 1 <= day <= 7:
        raise ValueError(f"{text!r} is not a date: the day (last digit) is 1 to 7, not {day}")
    if not 1 <= week <= 4:
        raise ValueError(f"{text!r} is not a date: the week (second to last digit) is 1 to 4, not {week}")
    if month < 1:
        raise ValueError(f"{text!r} is not a date: the month (the digits before the week) is 1 or more")
    return text


def check_roads(text: object) -> str:
    """A road setting: `none`, or the road types `slow`, `mid`, `fast` joined by `+`, in that order, each once."""
    form = "use none, or slow, mid and fast joined by + in that order (for example mid or slow+mid)"
    if not isinstance(text, str):
        raise ValueError(f"{text!r} is not a road setting: {form}")
    if text == "none":
        return text
    parts = text.split("+")
    if not all(part in ROAD_TYPES for part in parts):
        raise ValueError(f"{text!r} is not a road setting: {form}")
    if [ROAD_TYPES.index(part) for part in parts] != sorted(set(ROAD_TYPES.index(part) for part in parts)):
        raise ValueError(f"{text!r} is not a road setting: {form}")
    return text


def check_map_size(text: object) -> str:
    """A map size: S, M, L, XL, H, XH or G, with `+U` when it is played with underground."""
    if not isinstance(text, str) or not _MAP_SIZE.match(text):
        raise ValueError(f"{text!r} is not a map size: use one of {', '.join(MAP_SIZES)}, optionally followed by +U (for example L+U)")
    return text


def check_computer_players(value: object) -> int:
    """The number of computer players: a whole number from 0 to 6."""
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_COMPUTER_PLAYERS:
        raise ValueError(
            f"{value!r} is not a number of computer players: use a whole number from 0 to {MAX_COMPUTER_PLAYERS} "
            f"(a game has at most 8 players, two of them human)"
        )
    return value


def check_download(value: object) -> str:
    """A link where a template can be downloaded: it starts with https://."""
    if not isinstance(value, str) or not value.startswith("https://") or len(value) <= len("https://"):
        raise ValueError(f"download must be a link starting with https://, not {value!r}")
    return value


def check_text(text: object) -> str:
    """A free text for players to read (a description, additional rules): not empty, at most `MAX_TEXT` characters."""
    if not isinstance(text, str):
        raise ValueError(f"{text!r} is not a text: write it between quotes")
    if not text.strip():
        raise ValueError("the text is empty: leave the field out, or give a text")
    if len(text) > MAX_TEXT:
        raise ValueError(f"the text has {len(text)} characters, but the limit is {MAX_TEXT}")
    return text


def has_underground(map_size: str) -> bool:
    """True for a map size played with underground, such as `L+U`."""
    return map_size.endswith("+U")
