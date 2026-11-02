"""The link to a tournament's full rules: its form, the rules at the start of a match and /info. Made-up formats only."""

import asyncio

import pytest

import discord_commands.match as match
from rules.formats import FormatError, parse_format, validate_format
from rules.info import info_reply
from rules.registry import Registry
from test_selection_command import ANNA, BORIS, BOT, make_thread, texts

LINK = "https://example.com/rules"


def with_link(good_format, link=LINK):
    return dict(good_format, rules_link=link)


def test_a_link_is_accepted_and_read(good_format, templates, towns):
    data = with_link(good_format)
    assert validate_format(data, templates, towns) == []
    assert parse_format(data, templates, towns).rules_link == LINK


def test_no_link_is_fine(good_format, templates, towns):
    assert validate_format(good_format, templates, towns) == []
    assert parse_format(good_format, templates, towns).rules_link is None


@pytest.mark.parametrize("bad", ["example.com/rules", "http://example.com/rules", "", "https://"])
def test_a_bad_link_is_refused_naming_the_field(good_format, templates, towns, bad):
    messages = validate_format(with_link(good_format, bad), templates, towns)
    assert any("rules_link" in message for message in messages), messages
    with pytest.raises(FormatError, match="rules_link"):
        parse_format(with_link(good_format, bad), templates, towns)


def registry_of(good_format, templates, towns, link):
    data = with_link(good_format, link) if link else good_format
    fmt = parse_format(data, templates, towns)
    return Registry(towns, templates, {fmt.id: fmt})


def started(registry):
    thread = make_thread(930)
    fmt = next(iter(registry.formats.values()))
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], None, ANNA, BORIS))
    return texts(thread)


def test_the_rules_of_a_match_link_to_the_tournament_rules_after_the_number_of_games(good_format, templates, towns):
    sent = started(registry_of(good_format, templates, towns, LINK))
    index = next(i for i, text in enumerate(sent) if text.startswith("Format: "))
    assert sent[index + 1] == f"Rules: [full tournament rules](<{LINK}>)"


def test_a_tournament_without_a_link_has_no_such_message(good_format, templates, towns):
    assert not any(text.startswith("Rules:") for text in started(registry_of(good_format, templates, towns, None)))


def test_info_gives_the_link_after_the_description(good_format, templates, towns):
    registry = registry_of(good_format, templates, towns, LINK)
    fmt = next(iter(registry.formats.values()))
    lines = info_reply(registry, fmt.id).splitlines()
    assert f"Rules: [full tournament rules](<{LINK}>)" in lines
    assert lines.index(f"Rules: [full tournament rules](<{LINK}>)") <= 2


def test_info_without_a_link_has_no_line(good_format, templates, towns):
    registry = registry_of(good_format, templates, towns, None)
    assert "Rules: [" not in info_reply(registry, next(iter(registry.formats.values())).id)
