"""Tests /trade start and /trade report on a fake thread that keeps its messages, so a whole trade can be played."""

import asyncio

import pytest

import discord_commands.match as match
import discord_commands.selection as selection
import discord_commands.trade as trade_commands
from rules.formats import parse_format
from rules.registry import Registry
from state import parse
from test_selection_command import ANNA, BOT, BORIS, OUTSIDER, interaction, make_thread, texts, told

PAIR = ("necropolis", "tower")


@pytest.fixture
def registry(good_format, templates, towns):
    """A best-of-3 where A bans, B bans, A picks, B picks and the decider takes the last template."""
    bo3 = dict(
        good_format,
        id="bo3-cup",
        name="BO3 Cup",
        templates=["JC", "6lm10a", "h3dm1", "Diamond", "Sapphire"],
        allowed_towns=["castle", "necropolis", "tower", "cove"],
        phases=[
            {
                "name": "Main",
                "best_of": 3,
                "template_selection": {
                    "type": "sequence",
                    "steps": [
                        {"who": "A", "do": "ban"},
                        {"who": "B", "do": "ban"},
                        {"who": "A", "do": "pick"},
                        {"who": "B", "do": "pick"},
                        {"do": "decider"},
                    ],
                },
            }
        ],
    )
    return Registry(towns, templates, {"bo3-cup": parse_format(bo3, templates, towns)})


@pytest.fixture(autouse=True)
def fixed_pair(monkeypatch):
    """The pair the bot draws, made fixed; Anna wins the coinflip and is A."""
    monkeypatch.setattr(trade_commands, "draw_pair", lambda allowed: PAIR)
    monkeypatch.setattr(match, "coinflip", lambda a, b: a)


@pytest.fixture
def thread(registry):
    thread = make_thread(900)
    fmt = registry.formats["bo3-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], None, ANNA, BORIS))
    return thread


def run(command, registry, thread, user, *args):
    it = interaction(registry, thread, user)
    asyncio.run(command.callback(it, *args))
    return it


def select(registry, thread, *steps):
    """Play bans and picks: ("ban", "6lm10a", ANNA) ..."""
    for do, template, user in steps:
        run(selection.ban if do == "ban" else selection.pick, registry, thread, user, template)


FIRST_PICK = [("ban", "6lm10a", ANNA), ("ban", "Sapphire", BORIS), ("pick", "JC", ANNA)]
WHOLE_SELECTION = FIRST_PICK + [("pick", "Diamond", BORIS)]  # the decider takes h3dm1


def start(registry, thread, game=None, user=ANNA):
    return run(trade_commands.start, registry, thread, user, game)


def report(registry, thread, winner=ANNA, amount=2100, choice="Necropolis", user=ANNA):
    return run(trade_commands.report, registry, thread, user, winner, amount, choice)


def record_types(thread):
    return [r.type for r in map(parse, texts(thread)) if r is not None]


# --- the hint that a game can be traded --------------------------------------------------------------------------


def test_a_pick_says_the_game_can_be_traded(registry, thread):
    select(registry, thread, *FIRST_PICK)
    assert texts(thread)[-1] == "Game 1 is Jebus Cross. Start its trade with /trade start."


def test_the_decider_game_is_announced_when_the_last_pick_is_made(registry, thread):
    select(registry, thread, *WHOLE_SELECTION)
    assert texts(thread)[-2:] == [
        "Game 2 is Diamond. Start its trade with /trade start.",
        "Game 3 is h3dm1. Start its trade with /trade start.",
    ]


# --- starting a trade ------------------------------------------------------------------------------------------------


def test_a_trade_can_start_while_the_selection_goes_on(registry, thread):
    select(registry, thread, *FIRST_PICK)
    it = start(registry, thread)

    record = [r for r in map(parse, texts(thread)) if r is not None and r.type == "trade_started"][0]
    assert (record.game, record.data["pair"]) == (1, PAIR)
    assert told(it) == "Game 1's trade is open."
    assert texts(thread)[-2].startswith("[#6 tr g1] Game 1 (Jebus Cross): the trade starts. Pair: Necropolis")
    assert "Starting gold: <@1> 10000, <@2> 10000" in texts(thread)[-2]
    assert texts(thread)[-1].startswith("Game 1 town bid. <@1> bids first")


def test_a_game_that_is_not_decided_yet_is_refused(registry, thread):
    select(registry, thread, *FIRST_PICK)
    before = texts(thread)
    it = start(registry, thread, "3")
    assert "template of game 3 is not decided yet" in told(it)
    assert texts(thread) == before


def test_a_trade_is_started_by_template_name(registry, thread):
    select(registry, thread, *WHOLE_SELECTION)
    start(registry, thread, "Diamond")
    assert "[#7 tr g2]" in texts(thread)[-2]


def test_without_a_name_the_first_game_is_taken(registry, thread):
    select(registry, thread, *FIRST_PICK)
    start(registry, thread)
    assert "tr g1" in texts(thread)[-2]


def test_before_any_pick_there_is_no_game_to_trade(registry, thread):
    it = start(registry, thread)
    assert "No game is decided yet" in told(it)


def test_starting_the_open_trade_again_is_refused(registry, thread):
    select(registry, thread, *FIRST_PICK)
    start(registry, thread)
    it = start(registry, thread)
    assert "already open" in told(it)


def test_an_outsider_cannot_start_a_trade(registry, thread):
    select(registry, thread, *FIRST_PICK)
    before = texts(thread)
    it = start(registry, thread, user=OUTSIDER)
    assert "Only the two players" in told(it)
    assert texts(thread) == before


def test_outside_a_match_thread_the_player_is_sent_there(registry):
    it = interaction(registry, None, ANNA, in_thread=False)
    asyncio.run(trade_commands.start.callback(it, None))
    assert "inside a match thread" in told(it)


# --- reporting the bids ----------------------------------------------------------------------------------------------------


@pytest.fixture
def open_trade(registry, thread):
    select(registry, thread, *WHOLE_SELECTION)
    start(registry, thread)
    return thread


def test_a_town_bid_is_recorded_with_the_result_and_the_gold(registry, open_trade):
    it = report(registry, open_trade, winner=ANNA, amount=2100, choice="Necropolis")
    assert told(it) == "Reported."
    line = texts(open_trade)[-2]
    assert line.startswith("[#8 tb g1] Game 1 - Town bid, reported by <@1>: <@1> won at `2100` gold and plays Necropolis")
    assert line.endswith("Gold difference: <@1> -2100, <@2> +2100")
    assert texts(open_trade)[-1].startswith("Game 1 color bid.")


def test_either_player_may_report(registry, open_trade):
    report(registry, open_trade, winner=ANNA, user=BORIS)
    assert "reported by <@2>" in texts(open_trade)[-2]


def test_a_whole_trade_is_played_and_the_gold_is_right(registry, open_trade):
    report(registry, open_trade, winner=ANNA, amount=2100, choice="Necropolis")
    report(registry, open_trade, winner=BORIS, amount=3000, choice="red", user=BORIS)
    assert "Color bid, reported by <@2>: <@2> won at `3000` gold and plays `red`, <@1> plays blue." in texts(open_trade)[-2]
    assert texts(open_trade)[-2].endswith("Gold difference: <@1> +900, <@2> -900")
    assert texts(open_trade)[-1].splitlines() == [
        "Game 1 lobby settings - Jebus Cross",
        "<@1>: Necropolis, blue, gold +900",
        "<@2>: Tower, red, gold -900",
    ]


def test_a_color_before_the_town_is_refused_and_nothing_changes(registry, open_trade):
    before = texts(open_trade)
    it = report(registry, open_trade, choice="red")
    assert "town bid comes first" in told(it)
    assert texts(open_trade) == before


def test_a_town_outside_the_pair_is_refused_and_the_pair_repeated(registry, open_trade):
    before = texts(open_trade)
    it = report(registry, open_trade, choice="Castle")
    assert "Castle is not in the pair. The pair is Necropolis, Tower" in told(it)
    assert texts(open_trade) == before


def test_a_town_the_phase_does_not_allow_lists_the_allowed_ones(registry, open_trade):
    it = report(registry, open_trade, choice="Factory")
    assert "not an allowed town. Allowed towns: Castle, Necropolis, Tower, Cove" in told(it)


def test_a_bid_above_the_winners_gold_is_refused(registry, open_trade):
    before = texts(open_trade)
    it = report(registry, open_trade, amount=10100)
    assert "10100 gold is more than the 10000" in told(it)
    assert texts(open_trade) == before


def test_a_bid_that_is_not_a_whole_hundred_is_refused(registry, open_trade):
    it = report(registry, open_trade, amount=2150)
    assert "steps of 100" in told(it)


def test_reporting_without_an_open_trade_is_refused(registry, thread):
    select(registry, thread, *FIRST_PICK)
    it = report(registry, thread)
    assert "No trade is open. Start one with /trade start" in told(it)


def test_an_outsider_cannot_report(registry, open_trade):
    before = texts(open_trade)
    it = report(registry, open_trade, user=OUTSIDER)
    assert "Only the two players" in told(it)
    assert texts(open_trade) == before


def test_the_winner_must_be_a_player(registry, open_trade):
    it = report(registry, open_trade, winner=OUTSIDER)
    assert "one of the two players" in told(it)


def test_a_finished_trade_cannot_be_started_again(registry, open_trade):
    report(registry, open_trade)
    report(registry, open_trade, choice="red", amount=0)
    it = start(registry, open_trade, "1")
    assert "game 1 is finished" in told(it)


# --- one trade open at a time ------------------------------------------------------------------------------------------------


def test_starting_another_trade_closes_the_open_one_and_reopening_continues_it(registry, open_trade):
    report(registry, open_trade, winner=ANNA, amount=2100)  # game 1: town bid done, color bid next
    start(registry, open_trade, "2")
    assert "The trade of game 1 is closed, not finished. Start it again to continue." in texts(open_trade)
    assert texts(open_trade)[-1].startswith("Game 2 town bid.")

    start(registry, open_trade, "1")
    assert record_types(open_trade)[-1] == "trade_resumed"
    assert "Game 1 (Jebus Cross): the trade continues." in texts(open_trade)[-3]
    assert "Gold difference: <@1> -2100, <@2> +2100" in texts(open_trade)[-3]  # game 1 as it was
    assert texts(open_trade)[-1].startswith("Game 1 color bid.")  # and the section it stopped in


def test_reports_go_to_the_open_trade_only(registry, open_trade):
    start(registry, open_trade, "2")
    report(registry, open_trade, winner=BORIS, amount=500, choice="Tower", user=BORIS)
    assert "tb g2]" in texts(open_trade)[-2]
    assert "Gold difference: <@1> +500, <@2> -500" in texts(open_trade)[-2]  # game 2 has its own gold


def test_a_finished_trade_is_not_called_incomplete_when_another_opens(registry, open_trade):
    report(registry, open_trade)
    report(registry, open_trade, choice="blue", amount=0)
    start(registry, open_trade, "2")
    assert not any("is closed, not finished" in text for text in texts(open_trade))


# --- two commands at once ------------------------------------------------------------------------------------------------------


def test_two_reports_at_once_are_taken_one_after_the_other(registry, open_trade):
    async def both():
        first = interaction(registry, open_trade, ANNA)
        second = interaction(registry, open_trade, BORIS)
        await asyncio.gather(
            trade_commands.report.callback(first, ANNA, 2100, "Necropolis"),
            trade_commands.report.callback(second, ANNA, 2100, "Necropolis"),
        )
        return first, second

    first, second = asyncio.run(both())
    assert record_types(open_trade).count("town_bid") == 1
    assert "Now the color bid" in told(second)


# --- the overview ---------------------------------------------------------------------------------------------------------------


def test_status_lists_every_game_with_its_trade(registry, open_trade):
    report(registry, open_trade, winner=ANNA, amount=2100)
    start(registry, open_trade, "2")
    it = interaction(registry, open_trade, ANNA)
    asyncio.run(match.status.callback(it))
    text = told(it)
    assert "Template Selection: done" in text
    assert "Game 1: Jebus Cross, trade closed, not finished, next: color bid, gold difference <@1> -2100 / <@2> +2100" in text
    assert "Game 2: Diamond, trade open, next: town bid, gold difference <@1> 0 / <@2> 0" in text
    assert "Game 3: h3dm1, trade not started" in text


# --- what is offered while typing ----------------------------------------------------------------------------------------------------


def choices(callback, registry, thread, current=""):
    return [(c.name, c.value) for c in asyncio.run(callback(interaction(registry, thread, ANNA), current))]


def test_the_towns_of_the_pair_are_offered_in_the_town_section(registry, open_trade):
    assert choices(trade_commands._choice_options, registry, open_trade) == [("Necropolis", "necropolis"), ("Tower", "tower")]
    assert choices(trade_commands._choice_options, registry, open_trade, "tow") == [("Tower", "tower")]


def test_the_colors_are_offered_in_the_color_section(registry, open_trade):
    report(registry, open_trade)
    assert choices(trade_commands._choice_options, registry, open_trade) == [("red", "red"), ("blue", "blue")]


def test_nothing_is_offered_without_an_open_trade(registry, thread):
    assert choices(trade_commands._choice_options, registry, thread) == []


def test_the_games_not_finished_are_offered_for_a_trade_start(registry, thread):
    select(registry, thread, *WHOLE_SELECTION)
    assert choices(trade_commands._game_options, registry, thread) == [
        ("Game 1: Jebus Cross", "1"),
        ("Game 2: Diamond", "2"),
        ("Game 3: h3dm1", "3"),
    ]
    assert choices(trade_commands._game_options, registry, thread, "dia") == [("Game 2: Diamond", "2")]


def test_the_commands_have_the_expected_options():
    assert {p.name: p.required for p in trade_commands.start.parameters} == {"game": False}
    assert {p.name: p.required for p in trade_commands.report.parameters} == {
        "winner": True,
        "amount": True,
        "choice": True,
    }
