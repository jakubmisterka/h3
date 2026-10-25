"""Tests /trade start and /trade report on a fake thread that keeps its messages, so a whole trade can be played."""

import asyncio
import random

import pytest

import discord_commands.match as match
import discord_commands.selection as selection
import discord_commands.trade as trade_commands
from rules.formats import parse_format
from rules.registry import Registry
from state import parse
from test_selection_command import ANNA, BOT, BORIS, OUTSIDER, interaction, make_thread, texts, told

PAIR = ("necropolis", "tower")


def build_registry(good_format, templates, towns, roll_rules):
    """A best-of-3 where A bans, B bans, A picks, B picks and the decider takes the last template."""
    bo3 = dict(
        good_format,
        id="bo3-cup",
        name="BO3 Cup",
        templates=["JC", "6lm10a", "h3dm1", "Diamond", "Sapphire"],
        allowed_towns=["castle", "necropolis", "tower", "cove"],
        roll_rules=roll_rules,
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


@pytest.fixture
def registry(good_format, templates, towns):
    """The bids are what most tests here are about, so rolling is off in this one (see the rolling tests below)."""
    return build_registry(good_format, templates, towns, {"rolls_per_player": 0})


@pytest.fixture(autouse=True)
def fixed_pair(monkeypatch):
    """The pair the bot draws, made fixed; Anna wins the coinflip and is A."""
    monkeypatch.setattr(trade_commands, "draw_pair", lambda allowed, source=None: PAIR)
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
    assert texts(thread)[-1].startswith("Game 1 town bid: Necropolis vs Tower. <@1> bids first")


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
    assert texts(open_trade)[-1].startswith("Game 2 town bid:")

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
    assert "Game 2: Diamond, trade open, next: town bid Necropolis vs Tower, gold difference <@1> 0 / <@2> 0" in text
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


# --- rolling ------------------------------------------------------------------------------------------------------------------


@pytest.fixture
def rolling_registry(good_format, templates, towns):
    """The built-in roll rules (500 gold, one roll each) with at most one ban per roll."""
    return build_registry(good_format, templates, towns, {"max_roll_bans": 1})


@pytest.fixture
def rolling(rolling_registry, monkeypatch):
    """A thread with game 1 picked and its trade open, in the roll section."""
    monkeypatch.setattr(trade_commands, "random_source", random.Random(7))
    thread = make_thread(901)
    fmt = rolling_registry.formats["bo3-cup"]
    asyncio.run(match.begin_match(thread, BOT, rolling_registry, fmt, fmt.phases[0], None, ANNA, BORIS))
    select(rolling_registry, thread, *FIRST_PICK)
    start(rolling_registry, thread)
    return thread


def roll(registry, thread, user=ANNA, ban_1=None, ban_2=None):
    return run(trade_commands.roll, registry, thread, user, ban_1, ban_2)


def skip(registry, thread, user=ANNA):
    return run(trade_commands.skip_roll, registry, thread, user)


def rolls_in(thread):
    return [r for r in map(parse, texts(thread)) if r is not None and r.type == "roll"]


def test_a_trade_with_rolls_starts_with_the_roll_section(rolling):
    assert texts(rolling)[-1] == (
        "Game 1 town roll: Necropolis vs Tower. A roll costs 500 gold. Both players may roll. "
        "Roll with /trade roll (banning up to 1 town of the pair), or skip with /trade skip-roll."
    )


def test_a_roll_pays_the_opponent_and_announces_the_new_pair_and_who_may_still_roll(rolling_registry, rolling):
    it = roll(rolling_registry, rolling, ANNA, "Necropolis")
    [record] = rolls_in(rolling)
    assert told(it) == "Rolled."
    assert record.game == 1 and record.data["player"] == 1 and record.data["bans"] == ("necropolis",)
    assert "necropolis" not in record.data["pair"] and len(set(record.data["pair"])) == 2
    line = texts(rolling)[-2]
    assert "<@1> rolled, banning Necropolis (`necropolis`), and paid 500 gold to <@2>." in line
    assert line.endswith("Gold difference: <@1> -500, <@2> +500")
    assert "A roll costs 500 gold. <@2> may roll." in texts(rolling)[-1]


def test_a_roll_without_bans_is_possible(rolling_registry, rolling):
    roll(rolling_registry, rolling, BORIS)
    assert "<@2> rolled without banning a town, and paid 500 gold to <@1>." in texts(rolling)[-2]


def test_the_new_pair_is_the_one_the_bid_is_reported_on(rolling_registry, rolling):
    roll(rolling_registry, rolling, ANNA)
    skip(rolling_registry, rolling, BORIS)
    pair = rolls_in(rolling)[0].data["pair"]
    assert texts(rolling)[-1].startswith(f"Game 1 town bid: {rolling_registry.towns.find(pair[0]).name} vs ")
    it = run(trade_commands.report, rolling_registry, rolling, ANNA, ANNA, 2100, pair[1])
    assert told(it) == "Reported."


def test_more_bans_than_allowed_are_refused_and_nobody_pays(rolling_registry, rolling):
    before = texts(rolling)
    it = roll(rolling_registry, rolling, ANNA, "Necropolis", "Tower")
    assert "At most 1 town may be banned" in told(it)
    assert texts(rolling) == before


def test_a_town_outside_the_pair_cannot_be_banned(rolling_registry, rolling):
    before = texts(rolling)
    it = roll(rolling_registry, rolling, ANNA, "Castle")
    assert "Castle is not in the current pair" in told(it)
    assert texts(rolling) == before


def test_a_second_roll_by_the_same_player_is_refused(rolling_registry, rolling):
    roll(rolling_registry, rolling, ANNA)
    before = texts(rolling)
    it = roll(rolling_registry, rolling, ANNA)
    assert "no roll left (1 per player)" in told(it)
    assert texts(rolling) == before


def test_the_roll_section_ends_when_both_players_have_rolled(rolling_registry, rolling):
    roll(rolling_registry, rolling, ANNA)
    roll(rolling_registry, rolling, BORIS)
    assert texts(rolling)[-1].startswith("Game 1 town bid:")


def test_skipping_the_roll_waits_for_the_other_player_and_leaves_the_trade_open(rolling_registry, rolling):
    it = skip(rolling_registry, rolling, ANNA)
    assert told(it) == "You skip the roll."
    assert parse(texts(rolling)[-2]).type == "roll_skipped"
    assert texts(rolling)[-2] == "[#7 rs g1] Game 1 - <@1> skips the roll."
    assert "A roll costs 500 gold. <@2> may roll." in texts(rolling)[-1]


def test_when_both_skip_the_town_bid_starts_with_the_original_pair(rolling_registry, rolling):
    skip(rolling_registry, rolling, ANNA)
    skip(rolling_registry, rolling, BORIS)
    assert texts(rolling)[-1].startswith("Game 1 town bid: Necropolis vs Tower.")
    assert rolls_in(rolling) == []


def test_one_rolls_and_one_skips(rolling_registry, rolling):
    roll(rolling_registry, rolling, ANNA)
    skip(rolling_registry, rolling, BORIS)
    assert texts(rolling)[-1].startswith("Game 1 town bid:")


def test_skipping_with_no_roll_left_is_refused(rolling_registry, rolling):
    roll(rolling_registry, rolling, ANNA)
    it = skip(rolling_registry, rolling, ANNA)
    assert "no roll left" in told(it)


def test_reporting_the_town_bid_records_a_skip_for_every_roll_still_open(rolling_registry, rolling):
    run(trade_commands.report, rolling_registry, rolling, ANNA, ANNA, 2100, "Tower")
    skips = [r for r in records_in_thread(rolling) if r.type == "roll_skipped"]
    assert [(r.n, r.data["player"]) for r in skips] == [(7, 1), (8, 2)]  # one for each player, before the bid
    assert texts(rolling)[-4] == "[#7 rs g1] Game 1 - <@1> skips the roll (the town bid was reported)."
    assert texts(rolling)[-3] == "[#8 rs g1] Game 1 - <@2> skips the roll (the town bid was reported)."
    assert texts(rolling)[-2].startswith("[#9 tb g1]")
    assert texts(rolling)[-1].startswith("Game 1 color bid.")


def test_only_the_rolls_still_open_are_skipped_by_a_report(rolling_registry, rolling):
    roll(rolling_registry, rolling, ANNA)  # Anna used her roll; only Boris's is open
    run(trade_commands.report, rolling_registry, rolling, ANNA, ANNA, 100, rolls_in(rolling)[0].data["pair"][0])
    skips = [r for r in records_in_thread(rolling) if r.type == "roll_skipped"]
    assert [r.data["player"] for r in skips] == [2]


def test_no_skip_is_recorded_when_no_roll_was_open(rolling_registry, rolling):
    skip(rolling_registry, rolling, ANNA)
    skip(rolling_registry, rolling, BORIS)
    run(trade_commands.report, rolling_registry, rolling, ANNA, ANNA, 2100, "Tower")
    assert [r.data["player"] for r in records_in_thread(rolling) if r.type == "roll_skipped"] == [1, 2]  # only the two explicit ones


def records_in_thread(thread):
    return [r for r in map(parse, texts(thread)) if r is not None]


def test_a_roll_after_the_roll_section_is_refused(rolling_registry, rolling):
    run(trade_commands.report, rolling_registry, rolling, ANNA, ANNA, 2100, "Tower")
    it = roll(rolling_registry, rolling, BORIS)
    assert "roll section is over. The color bid is expected now" in told(it)


def test_the_cost_of_the_roll_lowers_what_can_be_bid(rolling_registry, rolling):
    roll(rolling_registry, rolling, ANNA)
    skip(rolling_registry, rolling, BORIS)
    pair = rolls_in(rolling)[0].data["pair"]
    it = run(trade_commands.report, rolling_registry, rolling, ANNA, ANNA, 9600, pair[0])
    assert "9600 gold is more than the 9500" in told(it)


def test_a_whole_trade_with_a_roll_ends_with_the_lobby_settings(rolling_registry, rolling):
    roll(rolling_registry, rolling, ANNA)
    skip(rolling_registry, rolling, BORIS)
    pair = rolls_in(rolling)[0].data["pair"]
    run(trade_commands.report, rolling_registry, rolling, ANNA, BORIS, 1000, pair[0])
    run(trade_commands.report, rolling_registry, rolling, ANNA, ANNA, 0, "red")
    lines = texts(rolling)[-1].splitlines()
    assert lines[0] == "Game 1 lobby settings - Jebus Cross"
    # A paid 500 for the roll and received 1000 for the town: +500; B the opposite
    assert lines[1].endswith("gold +500") and lines[2].endswith("gold -500")


def test_an_outsider_cannot_roll_or_skip(rolling_registry, rolling):
    before = texts(rolling)
    assert "Only the two players" in told(roll(rolling_registry, rolling, OUTSIDER))
    assert "Only the two players" in told(skip(rolling_registry, rolling, OUTSIDER))
    assert texts(rolling) == before


def test_rolling_without_an_open_trade_is_refused(rolling_registry):
    thread = make_thread(902)
    fmt = rolling_registry.formats["bo3-cup"]
    asyncio.run(match.begin_match(thread, BOT, rolling_registry, fmt, fmt.phases[0], None, ANNA, BORIS))
    select(rolling_registry, thread, *FIRST_PICK)
    assert "No trade is open" in told(roll(rolling_registry, thread))
    assert "No trade is open" in told(skip(rolling_registry, thread))


def test_the_towns_of_the_pair_are_offered_as_bans_in_the_roll_section(rolling_registry, rolling):
    names = [(c.name, c.value) for c in asyncio.run(trade_commands._ban_options(interaction(rolling_registry, rolling, ANNA), ""))]
    assert names == [("Necropolis", "necropolis"), ("Tower", "tower")]


def test_no_bans_are_offered_once_the_roll_section_is_over(rolling_registry, rolling):
    skip(rolling_registry, rolling, ANNA)
    skip(rolling_registry, rolling, BORIS)
    assert asyncio.run(trade_commands._ban_options(interaction(rolling_registry, rolling, ANNA), "")) == []


def test_the_overview_shows_the_roll_section_as_next(rolling_registry, rolling):
    it = interaction(rolling_registry, rolling, ANNA)
    asyncio.run(match.status.callback(it))
    assert "trade open, next: town bid Necropolis vs Tower (rolls still open)" in told(it)


def test_the_roll_commands_have_the_expected_options():
    assert {p.name: p.required for p in trade_commands.roll.parameters} == {"ban_1": False, "ban_2": False}
    assert trade_commands.skip_roll.name == "skip-roll" and list(trade_commands.skip_roll.parameters) == []


def report_choices(registry, thread):
    return [(c.name, c.value) for c in asyncio.run(trade_commands._choice_options(interaction(registry, thread, BORIS), ""))]


def test_towns_are_offered_for_the_report_while_the_roll_section_is_still_open(rolling_registry, rolling):
    # nobody has rolled yet, so these are the towns of the first pair
    assert report_choices(rolling_registry, rolling) == [("Necropolis", "necropolis"), ("Tower", "tower")]


def test_the_towns_of_the_new_pair_are_offered_after_a_roll_while_the_other_player_may_still_roll(rolling_registry, rolling):
    roll(rolling_registry, rolling, ANNA)  # Boris has not rolled or skipped, so the roll section is still open
    new_pair = rolls_in(rolling)[0].data["pair"]
    offered = report_choices(rolling_registry, rolling)
    assert [value for _, value in offered] == list(new_pair)
    assert ("red", "red") not in offered


def test_colors_are_offered_once_the_town_bid_is_reported(rolling_registry, rolling):
    run(trade_commands.report, rolling_registry, rolling, ANNA, ANNA, 100, "Tower")
    assert report_choices(rolling_registry, rolling) == [("red", "red"), ("blue", "blue")]


# --- games one after another ----------------------------------------------------------------------------------------------------------


def test_games_are_traded_one_after_another_and_a_finished_trade_stays_finished(registry, thread):
    select(registry, thread, *WHOLE_SELECTION)
    start(registry, thread)  # without a name: game 1
    report(registry, thread, winner=ANNA, amount=2100, choice="Necropolis")
    report(registry, thread, winner=BORIS, amount=3000, choice="red", user=BORIS)
    assert texts(thread)[-1].startswith("Game 1 lobby settings")

    start(registry, thread)  # without a name: the first game not finished, which is game 2
    assert "Game 2 (Diamond): the trade starts." in texts(thread)[-2]
    assert not any("is closed, not finished" in text for text in texts(thread))

    it = interaction(registry, thread, ANNA)
    asyncio.run(match.status.callback(it))
    status = told(it)
    assert "Game 1: Jebus Cross, trade done, gold difference <@1> +900 / <@2> -900" in status
    assert "Game 2: Diamond, trade open, next: town bid" in status
    assert "game 1 is finished" in told(start(registry, thread, "1"))
