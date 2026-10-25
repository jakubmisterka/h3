"""Discord refuses a command or an option whose description is longer than 100 characters, and only says so when the
commands are synced. This checks them all here, so it is found by the tests instead."""

from discord import app_commands

from discord_commands import match
from discord_commands.info import info
from discord_commands.selection import ban, pick
from discord_commands.trade import group as trade_group

LIMIT = 100


def commands_in(command):
    """A command, or every command of a group, however deep."""
    if isinstance(command, app_commands.Group):
        for child in command.commands:
            yield from commands_in(child)
    else:
        yield command


def all_commands():
    for top in (match.group, info, ban, pick, trade_group):
        yield from commands_in(top)


def test_there_are_commands_to_check():
    names = {command.qualified_name for command in all_commands()}
    assert {"match start", "match status", "match undo", "info", "ban", "pick"} <= names
    assert {"trade start", "trade report", "trade roll", "trade skip-roll"} <= names


def test_every_command_description_fits_in_discord():
    for command in all_commands():
        assert len(command.description) <= LIMIT, f"/{command.qualified_name}: {command.description!r}"


def test_every_option_description_fits_in_discord():
    for command in all_commands():
        for parameter in command.parameters:
            assert len(parameter.description) <= LIMIT, f"/{command.qualified_name} {parameter.display_name}: {parameter.description!r}"


def test_every_option_has_a_description():
    for command in all_commands():
        for parameter in command.parameters:
            assert parameter.description not in ("", "…"), f"/{command.qualified_name} {parameter.display_name} has no description"
