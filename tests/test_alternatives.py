"""Alternatives of a template: a tournament says that, by agreement, another template can be played instead. Made-up
catalogue and formats only (see conftest.py)."""

import asyncio
import copy

import pytest

import discord_commands.match as match
from rules.catalogue import parse_templates
from rules.formats import FormatError, parse_format, validate_format
from rules.info import info_reply
from rules.registry import Registry
from rules.template_facts import announcement_lines, info_hint
from rules.template_settings import Settings, effective_settings
from test_selection_command import ANNA, BORIS, BOT, make_thread, texts

LINK = "https://example.com/base-nc"

TEMPLATES = [
    {"id": "Base", "name": "Base", "difficulty": 160, "built_in": True},
    {"id": "Base_nc", "name": "Base nc", "difficulty": 160, "download": LINK},
    {"id": "Base_alt", "name": "Base alt", "difficulty": 160, "built_in": True},
    {"id": "Locked", "name": "Locked", "difficulty": 160},
    {"id": "Other", "name": "Other", "difficulty": 160, "built_in": True},
]


@pytest.fixture
def catalogue():
    return parse_templates(copy.deepcopy(TEMPLATES), "templates.json")


def format_with(good_format, settings_of_base=None, pool_settings=None):
    """One phase where the players agree, listing Base (with the given settings) and Other."""
    base = {"template": "Base", "settings": settings_of_base} if settings_of_base is not None else "Base"
    pool = [{"template": "Base", "settings": pool_settings}, "Other"] if pool_settings is not None else None
    phase = {"name": "Main", "best_of": 1, "template_selection": {"type": "agreed"}, **({"pool": pool} if pool else {})}
    return dict(good_format, id="alt-cup", name="Alt Cup", templates=[base, "Other"], phases=[phase], settings={}, roll_rules={})


def problems(data, catalogue, towns):
    return validate_format(data, catalogue, towns)


# --- the setting ---------------------------------------------------------------------------------------------------


def test_an_alternative_that_can_be_obtained_is_accepted_and_read(good_format, catalogue, towns):
    data = format_with(good_format, {"alternatives": ["Base_nc", "Base_alt"]})
    assert problems(data, catalogue, towns) == []
    fmt = parse_format(data, catalogue, towns)
    assert effective_settings(fmt, fmt.phases[0], "Base", catalogue).alternatives == ("Base_nc", "Base_alt")
    assert effective_settings(fmt, fmt.phases[0], "Other", catalogue).alternatives == ()


def test_the_phases_alternatives_replace_the_tournaments(good_format, catalogue, towns):
    data = format_with(good_format, {"alternatives": ["Base_nc"]}, pool_settings={"alternatives": ["Base_alt"]})
    fmt = parse_format(data, catalogue, towns)
    assert effective_settings(fmt, fmt.phases[0], "Base", catalogue).alternatives == ("Base_alt",)


@pytest.mark.parametrize(
    "alternatives, words",
    [
        (["Nowhere"], "'Nowhere' is not a template of the catalogue"),
        (["Base"], "'Base' cannot be its own alternative"),
        (["Locked"], "neither built into HotA nor has a download link"),
        (["Base_nc", "Base_nc"], "'Base_nc' is listed more than once"),
        ([], "should be non-empty"),
        ("Base_nc", "is not of type 'array'"),
    ],
)
def test_a_bad_alternative_is_refused_naming_the_template(good_format, catalogue, towns, alternatives, words):
    messages = problems(format_with(good_format, {"alternatives": alternatives}), catalogue, towns)
    assert any(words in message for message in messages), messages


def test_parse_refuses_a_format_with_a_bad_alternative(good_format, catalogue, towns):
    with pytest.raises(FormatError, match="Locked"):
        parse_format(format_with(good_format, {"alternatives": ["Locked"]}), catalogue, towns)


# --- the line ------------------------------------------------------------------------------------------------------


def line_for(*alternatives, catalogue):
    return [line for line in announcement_lines(Settings(alternatives=alternatives), None, catalogue) if "By agreement" in line]


def test_an_alternative_that_has_to_be_downloaded_has_its_link(catalogue):
    assert line_for("Base_nc", catalogue=catalogue) == [f"By agreement the template can be changed to `Base nc` ([download](<{LINK}>))"]


def test_an_alternative_built_into_hota_has_no_link(catalogue):
    assert line_for("Base_alt", catalogue=catalogue) == ["By agreement the template can be changed to `Base alt`"]


def test_several_alternatives_are_one_line(catalogue):
    assert line_for("Base_nc", "Base_alt", catalogue=catalogue) == [
        f"By agreement the template can be changed to `Base nc` ([download](<{LINK}>)) or `Base alt`"
    ]


def test_without_alternatives_there_is_no_line(catalogue):
    assert line_for(catalogue=catalogue) == []


def test_the_line_comes_after_the_trade_rule_and_before_the_hint_to_info(catalogue):
    lines = announcement_lines(Settings(alternatives=("Base_alt",), timer="12:00+06:00+01:15"), info_hint("alt-cup", "Base"), catalogue)
    assert lines[0] == "Timer: `12:00+06:00+01:15`" and lines[1].startswith("Trade:")
    assert lines[2].startswith("By agreement") and lines[3].startswith("More about this template")


# --- in the thread and in /info ------------------------------------------------------------------------------------


@pytest.fixture
def registry(good_format, catalogue, towns):
    fmt = parse_format(format_with(good_format, {"alternatives": ["Base_nc"]}), catalogue, towns)
    return Registry(towns, catalogue, {fmt.id: fmt})


def test_a_match_started_with_a_template_names_its_alternatives(registry):
    thread = make_thread(920)
    fmt = registry.formats["alt-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], "Base", ANNA, BORIS))
    sent = texts(thread)
    assert f"By agreement the template can be changed to `Base nc` ([download](<{LINK}>))" in sent
    assert sent.index("Format: BO1") < sent.index(f"By agreement the template can be changed to `Base nc` ([download](<{LINK}>))")


def test_a_template_without_alternatives_has_no_line_in_its_match(registry):
    thread = make_thread(921)
    fmt = registry.formats["alt-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], "Other", ANNA, BORIS))
    assert not any("By agreement" in text for text in texts(thread))


def test_info_names_the_alternatives_of_a_template(registry):
    reply = info_reply(registry, "alt-cup", "Base")
    assert f"By agreement the template can be changed to `Base nc` ([download](<{LINK}>))" in reply
    assert "By agreement" not in info_reply(registry, "alt-cup", "Other")


def test_info_names_the_phases_that_differ(good_format, catalogue, towns):
    data = format_with(good_format, {"alternatives": ["Base_nc"]})
    data["phases"] = [
        {"name": "One", "best_of": 1, "template_selection": {"type": "agreed"}},
        {"name": "Two", "best_of": 1, "template_selection": {"type": "agreed"}, "pool": [{"template": "Base", "settings": {"alternatives": ["Base_alt"]}}, "Other"]},
        {"name": "Three", "best_of": 1, "template_selection": {"type": "agreed"}},
    ]
    fmt = parse_format(data, catalogue, towns)
    reply = info_reply(Registry(towns, catalogue, {fmt.id: fmt}), "alt-cup", "Base")
    assert f"By agreement the template can be changed to `Base nc` ([download](<{LINK}>))\n  Two: `Base alt`" in reply


# --- looking an alternative up -------------------------------------------------------------------------------------


def test_info_can_look_up_an_alternative_of_the_mode(registry):
    reply = info_reply(registry, "alt-cup", "Base_nc")
    assert reply.splitlines()[0] == "**Base nc** in Alt Cup"
    assert "An alternative to Base: the players may play it instead, if they agree." in reply
    assert f"Download: <{LINK}>" in reply


def test_info_still_refuses_a_template_that_is_neither_played_nor_an_alternative(registry):
    assert info_reply(registry, "alt-cup", "Locked").startswith("'Locked' is not in Alt Cup")


def test_the_alternatives_are_offered_while_typing_the_template(registry):
    from rules.info import template_choices

    assert template_choices(registry, "alt-cup", "") == [("Base", "Base"), ("Other", "Other"), ("Base nc (alternative)", "Base_nc")]
    assert template_choices(registry, "alt-cup", "nc") == [("Base nc (alternative)", "Base_nc")]
