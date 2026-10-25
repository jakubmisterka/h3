"""What the thread says about the template of a game: in the rules at the start of a match with a named template, in
the announcement of a game once a pick or the last ban settles it, and in the lobby settings that close its trade."""

import asyncio
import copy

import pytest

import discord_commands.match as match
import discord_commands.trade as trade_commands
from rules.catalogue import parse_templates
from rules.formats import parse_format
from rules.registry import Registry
from test_selection_command import ANNA, BORIS, BOT, make_thread, texts
from test_trade_command import FIRST_PICK, WHOLE_SELECTION, fixed_pair, report, run, select, start  # noqa: F401

TEMPLATES = [
    {
        "id": "JC",
        "name": "Jebus Cross",
        "difficulty": 160,
        "map_size": {"default": "L+U", "allowed": ["L+U", "XL+U"]},
        "roads": {"default": "mid", "allowed": ["none", "mid", "slow+mid"]},
        "ai": {"default": 6, "allowed": [0, 6]},
        "sim_turns": "117",
        "download": "https://example.com/jc",
    },
    {"id": "6lm10a", "name": "6lm10a", "difficulty": 160},
    {"id": "h3dm1", "name": "h3dm1", "difficulty": 160, "built_in": True},
    {"id": "Diamond", "name": "Diamond", "difficulty": 160, "map_size": {"default": "M", "allowed": ["M"]}},
    {"id": "Sapphire", "name": "Sapphire", "difficulty": 160},
]
JC_FACTS = [
    "Download: <https://example.com/jc>",
    "Timer: 12:00+06:00+02:00",
    "Map: L+U",
    "Roads: mid",
    "AI players: 6",
    "Sim turns until 117",
]


def bo3(good_format, **more):
    selection = {
        "type": "sequence",
        "steps": [
            {"who": "A", "do": "ban"},
            {"who": "B", "do": "ban"},
            {"who": "A", "do": "pick"},
            {"who": "B", "do": "pick"},
            {"do": "decider"},
        ],
    }
    data = dict(
        good_format,
        id="bo3-cup",
        name="BO3 Cup",
        templates=["JC", "6lm10a", "h3dm1", "Diamond", "Sapphire"],
        allowed_towns=["castle", "necropolis", "tower", "cove"],
        roll_rules={"rolls_per_player": 0},
        phases=[{"name": "Main", "best_of": 3, "template_selection": selection}],
    )
    data.update(more)  # what a test changes: the tournament's settings, or its list of templates
    return data


def registry_of(good_format, towns, **more):
    catalogue = parse_templates(copy.deepcopy(TEMPLATES), "templates.json")
    fmt = parse_format(bo3(good_format, **more), catalogue, towns)
    return Registry(towns, catalogue, {fmt.id: fmt})


def started(registry, template=None):
    thread = make_thread(970)
    fmt = registry.formats["bo3-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], template, ANNA, BORIS))
    return thread


@pytest.fixture
def registry(good_format, towns):
    return registry_of(good_format, towns, settings={"timer": "12:00+06:00+02:00"})


@pytest.fixture
def thread(registry):
    return started(registry)


# --- the rules at the start of a match with a named template -------------------------------------------------------


def test_the_rules_of_a_named_template_include_what_is_stated_about_it(registry):
    thread = started(registry, "JC")
    sent = texts(thread)
    assert sent[1:3] == ["One game", "The template: Jebus Cross"]
    assert sent[3 : 3 + len(JC_FACTS)] == JC_FACTS
    assert sent[3 + len(JC_FACTS)] == "The winner of the coinflip will be player A, the other player is B"


def test_what_the_phase_chose_is_what_the_rules_say(good_format, towns):
    chosen = registry_of(
        good_format,
        towns,
        templates=[{"template": "JC", "settings": {"map_size": "XL+U", "ai": 0}}, "6lm10a", "h3dm1", "Diamond", "Sapphire"],
    )
    sent = texts(started(chosen, "JC"))
    assert "Map: XL+U" in sent and "No AI players" in sent
    assert "Map: L+U" not in sent and "AI players: 6" not in sent


def test_a_named_template_that_states_nothing_gets_only_the_tournaments_timer(registry):
    sent = texts(started(registry, "6lm10a"))
    assert sent[1:4] == ["One game", "The template: 6lm10a", "Timer: 12:00+06:00+02:00"]


def test_a_named_template_that_states_nothing_in_a_mode_without_a_timer_is_as_before(good_format, towns):
    sent = texts(started(registry_of(good_format, towns), "6lm10a"))
    assert sent[1:4] == ["One game", "The template: 6lm10a", "The winner of the coinflip will be player A, the other player is B"]


def test_the_rules_without_a_named_template_are_not_changed(registry):
    assert "Timer" not in " ".join(texts(started(registry)))  # the templates are not settled yet


# --- the announcement of a decided game ----------------------------------------------------------------------------


def test_a_game_decided_by_a_pick_is_announced_with_what_is_stated(registry, thread):
    select(registry, thread, *FIRST_PICK)  # A picks Jebus Cross: game 1
    assert texts(thread)[-1].splitlines() == [
        *JC_FACTS,
        "Game 1 is Jebus Cross. Start its trade with /trade start.",
    ]


def test_the_decider_game_is_announced_in_the_same_way(registry, thread):
    select(registry, thread, *WHOLE_SELECTION)  # B picks Diamond (game 2), the decider takes h3dm1 (game 3)
    second, third = texts(thread)[-2:]
    assert second.splitlines() == [
        "Timer: 12:00+06:00+02:00",
        "Map: M",
        "Game 2 is Diamond. Start its trade with /trade start.",
    ]
    assert third.splitlines() == [
        "Built into HotA",
        "Timer: 12:00+06:00+02:00",
        "Game 3 is h3dm1. Start its trade with /trade start.",
    ]


def test_a_game_whose_template_states_nothing_in_a_mode_without_a_timer_is_announced_as_before(good_format, towns):
    plain = registry_of(good_format, towns)
    thread = started(plain)
    select(plain, thread, ("ban", "Diamond", ANNA), ("ban", "h3dm1", BORIS), ("pick", "6lm10a", ANNA))
    assert texts(thread)[-1] == "Game 1 is 6lm10a. Start its trade with /trade start."


# --- the lobby settings -------------------------------------------------------------------------------------------


def finish_trade(registry, thread):
    start(registry, thread)
    report(registry, thread, winner=ANNA, amount=2100, choice="Necropolis")
    report(registry, thread, winner=BORIS, amount=3000, choice="red", user=BORIS)


def test_the_lobby_settings_include_what_is_typed_into_the_lobby(registry, thread):
    select(registry, thread, *FIRST_PICK)
    finish_trade(registry, thread)
    assert texts(thread)[-1].splitlines() == [
        "Game 1 lobby settings - Jebus Cross",
        "Timer: 12:00+06:00+02:00",
        "Map: L+U",
        "Roads: mid",
        "AI players: 6",
        "<@1>: Necropolis, blue, gold +900",
        "<@2>: Tower, red, gold -900",
    ]


def test_the_lobby_settings_leave_out_the_recommended_simultaneous_turns_and_where_to_get_it(registry, thread):
    select(registry, thread, *FIRST_PICK)
    finish_trade(registry, thread)
    summary = texts(thread)[-1]
    assert "Sim turns" not in summary and "Download" not in summary


def test_the_lobby_settings_of_a_game_with_nothing_stated_have_only_the_tournaments_timer(registry):
    thread = started(registry, "6lm10a")
    finish_trade(registry, thread)
    assert texts(thread)[-2].splitlines() == [
        "Game 1 lobby settings - 6lm10a",
        "Timer: 12:00+06:00+02:00",
        "<@1>: Necropolis, blue, gold +900",
        "<@2>: Tower, red, gold -900",
    ]


def test_the_lobby_settings_without_anything_stated_are_as_before(good_format, towns):
    plain = registry_of(good_format, towns)
    thread = started(plain, "6lm10a")
    finish_trade(plain, thread)
    assert texts(thread)[-2].splitlines()[0] == "Game 1 lobby settings - 6lm10a"
    assert texts(thread)[-2].splitlines()[1].startswith("<@1>: ")
