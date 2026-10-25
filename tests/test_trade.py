import random
from collections import Counter

import pytest

from rules.catalogue import TEMPLATE_FIELDS, parse_catalogue
from rules.ledger import LedgerError
from rules.trade import (
    Report,
    TradeError,
    TradeLog,
    check_startable,
    choose_game,
    draw_pair,
    make_report,
    new_trade,
    next_message,
    opening_line,
    prompt,
    replay_trades,
    report_line,
    summary,
)
from state import make_record, parse

A, B = 111, 222
PLAYERS = (A, B)
GAMES = ("JC", "Diamond", "h3dm1")  # three games of a best-of-3, all 160%: 10000 gold each
PAIR = ("necropolis", "tower")
ALLOWED = ("castle", "necropolis", "tower", "cove")
MENTIONS = {A: "<@111>", B: "<@222>"}


def started(n, game, pair=PAIR):
    return make_record(n, "trade_started", game, pair=pair)


def resumed(n, game):
    return make_record(n, "trade_resumed", game)


def town_bid(n, game, winner=A, amount=2100, town="necropolis", reporter=A):
    return make_record(n, "town_bid", game, reporter=reporter, winner=winner, amount=amount, town=town)


def color_bid(n, game, winner=B, amount=3000, color="red", reporter=B):
    return make_record(n, "color_bid", game, reporter=reporter, winner=winner, amount=amount, color=color)


def replay(*records, templates, games=GAMES):
    return replay_trades(tuple(records), games, PLAYERS, templates)


@pytest.fixture
def trade(templates):
    return new_trade(1, GAMES, PAIR, PLAYERS, templates)


# --- the pair the bot draws ---------------------------------------------------------------------------------


def test_the_pair_is_two_different_allowed_towns():
    for seed in range(100):
        first, second = draw_pair(ALLOWED, random.Random(seed))
        assert first != second and {first, second} <= set(ALLOWED)


def test_the_same_seed_draws_the_same_pair():
    assert draw_pair(ALLOWED, random.Random(5)) == draw_pair(ALLOWED, random.Random(5))


def test_every_allowed_town_is_equally_likely():
    source = random.Random(1234)
    counts = Counter(town for _ in range(8000) for town in draw_pair(ALLOWED, source))
    # 8000 pairs of 2 towns from 4: each town appears in about half the pairs
    assert all(3700 < counts[town] < 4300 for town in ALLOWED)


def test_a_pair_needs_two_different_towns():
    with pytest.raises(TradeError, match="two different towns"):
        draw_pair(("castle",))
    with pytest.raises(TradeError, match="two different towns"):
        draw_pair(("castle", "castle"))


# --- a new trade --------------------------------------------------------------------------------------------


def test_a_new_trade_starts_with_the_gold_of_the_difficulty_and_the_town_bid(trade):
    assert trade.gold == {A: 10000, B: 10000}
    assert trade.section == "town_bid" and not trade.finished


def test_a_200_percent_game_has_no_trade_yet(towns):
    all_random = parse_catalogue([{"id": "X", "name": "X", "difficulty": 200}], "templates", TEMPLATE_FIELDS)
    with pytest.raises(TradeError, match="200%"):
        new_trade(1, ("X",), PAIR, PLAYERS, all_random)


# --- reporting ------------------------------------------------------------------------------------------------


def report(trade, towns, winner=A, amount=2100, choice="Necropolis", allowed=ALLOWED, reporter=A):
    return make_report(trade, towns, allowed, reporter, winner, amount, choice)


def test_a_town_bid_is_reported_by_name_or_id(trade, towns):
    assert report(trade, towns, choice="Necropolis") == Report("town_bid", A, A, 2100, "necropolis")
    assert report(trade, towns, choice="TOWER").choice == "tower"


def test_either_player_may_report_the_result(trade, towns):
    assert report(trade, towns, winner=A, reporter=B).reporter == B


def test_a_color_before_the_town_is_refused_and_the_town_bid_is_named(trade, towns):
    with pytest.raises(TradeError, match="town bid comes first.*Necropolis, Tower"):
        report(trade, towns, choice="red")


def test_a_town_outside_the_pair_is_refused_and_the_pair_repeated(trade, towns):
    with pytest.raises(TradeError, match="Castle is not in the pair. The pair is Necropolis, Tower"):
        report(trade, towns, choice="Castle")


def test_an_unknown_town_is_refused_and_the_allowed_towns_listed(trade, towns):
    with pytest.raises(TradeError, match="'Atlantis' is not an allowed town. Allowed towns: Castle, Necropolis, Tower, Cove"):
        report(trade, towns, choice="Atlantis")


def test_a_town_the_phase_does_not_allow_is_refused_and_the_allowed_towns_listed(trade, towns):
    with pytest.raises(TradeError, match="not an allowed town. Allowed towns: Castle, Rampart, Tower"):
        report(trade, towns, choice="Cove", allowed=("castle", "rampart", "tower"))


def test_more_than_the_winner_has_is_refused(trade, towns):
    with pytest.raises(LedgerError, match="10100 gold is more than the 10000"):
        report(trade, towns, amount=10100)


def test_an_amount_that_is_not_a_whole_hundred_is_refused(trade, towns):
    with pytest.raises(LedgerError, match="steps of 100"):
        report(trade, towns, amount=2150)


def test_the_winner_must_be_a_player(trade, towns):
    with pytest.raises(TradeError, match="one of the two players"):
        report(trade, towns, winner=333)


def test_a_town_after_the_town_bid_is_refused_for_the_color_section(templates, towns):
    after_town = replay(started(1, 1), town_bid(2, 1), templates=templates).open
    with pytest.raises(TradeError, match="Now the color bid: choose red or blue"):
        make_report(after_town, towns, ALLOWED, A, B, 3000, "Tower")


def test_a_finished_trade_takes_no_more_reports(templates, towns):
    done = replay(started(1, 1), town_bid(2, 1), color_bid(3, 1), templates=templates).open
    with pytest.raises(TradeError, match="game 1 is finished"):
        make_report(done, towns, ALLOWED, A, A, 100, "red")


# --- the trades of a match from its records ----------------------------------------------------------------------


def test_the_gold_follows_the_reports(templates):
    log = replay(started(1, 1), town_bid(2, 1, winner=A, amount=2100), color_bid(3, 1, winner=B, amount=3000), templates=templates)
    trade = log.open
    assert trade.gold == {A: 10900, B: 9100}  # A paid 2100 and received 3000; B paid 3000 and received 2100
    assert trade.finished and log.open_game == 1


def test_the_section_moves_from_the_town_bid_to_the_color_bid(templates):
    log = replay(started(1, 1), templates=templates)
    assert log.open.section == "town_bid"
    log = replay(started(1, 1), town_bid(2, 1), templates=templates)
    assert log.open.section == "color_bid"


def test_nothing_is_open_before_a_trade_starts(templates):
    log = replay(templates=templates)
    assert log.open is None and log.trades == {}


def test_starting_another_trade_closes_the_open_one_as_incomplete(templates):
    log = replay(started(1, 1), town_bid(2, 1), started(3, 2), templates=templates)
    assert log.open_game == 2
    assert log.trades[1].section == "color_bid" and not log.trades[1].finished  # kept as it was


def test_a_closed_trade_is_reopened_where_it_stopped(templates):
    log = replay(started(1, 1), town_bid(2, 1), started(3, 2), resumed(4, 1), templates=templates)
    assert log.open_game == 1
    assert log.open.section == "color_bid" and log.open.pair == PAIR and log.open.gold == {A: 7900, B: 12100}


def test_each_game_has_its_own_gold(templates):
    log = replay(started(1, 1), town_bid(2, 1), started(3, 2), templates=templates)
    assert log.trades[2].gold == {A: 10000, B: 10000}


@pytest.mark.parametrize(
    "records, problem",
    [
        ([started(1, 4)], "game 4 is not decided"),
        ([started(1, 1), started(2, 1)], "started twice"),
        ([town_bid(1, 1)], "never started"),
        ([resumed(1, 1)], "never started"),
        ([started(1, 1), started(2, 2), town_bid(3, 1)], "game 1 was not open"),
        ([started(1, 1), color_bid(2, 1)], "town bid is expected"),
        ([started(1, 1), town_bid(2, 1, town="castle")], "one of the pair"),
        ([started(1, 1), town_bid(2, 1, winner=333)], "two players"),
        ([started(1, 1), town_bid(2, 1, amount=10100)], "10100 gold is more than"),
        ([started(1, 1), town_bid(2, 1), color_bid(3, 1), color_bid(4, 1)], "finished"),
    ],
)
def test_a_record_that_does_not_fit_is_reported_not_trusted(templates, records, problem):
    with pytest.raises(TradeError, match=f"Message #{records[-1].n} .*does not fit the trade.*{problem}"):
        replay(*records, templates=templates)


# --- which game a player means --------------------------------------------------------------------------------------


@pytest.fixture
def log(templates):
    return replay(started(1, 1), town_bid(2, 1), color_bid(3, 1), started(4, 2), templates=templates)


def choose(text, log, templates, games=GAMES):
    return choose_game(text, games, 3, log, templates)


def test_without_a_name_the_first_unfinished_game_is_taken(log, templates):
    assert choose(None, log, templates) == 2  # game 1 is finished, game 2 is open and unfinished
    assert choose("", log, templates) == 2


def test_without_a_name_and_nothing_started_it_is_game_1(templates):
    assert choose(None, TradeLog({}), templates) == 1


def test_a_game_is_named_by_number_or_by_template(log, templates):
    assert choose("3", log, templates) == 3
    assert choose("game 3", log, templates) == 3
    assert choose("Diamond", log, templates) == 2
    assert choose("jc", log, templates) == 1


def test_a_game_whose_template_is_not_decided_yet_is_refused(templates):
    with pytest.raises(TradeError, match="template of game 3 is not decided yet"):
        choose("3", TradeLog({}), templates, games=("JC", "Diamond"))


def test_without_a_name_and_no_game_known_the_bot_says_so(templates):
    with pytest.raises(TradeError, match="No game is decided yet"):
        choose(None, TradeLog({}), templates, games=())


def test_a_number_outside_the_match_is_refused(log, templates):
    with pytest.raises(TradeError, match="games 1 to 3, not 4"):
        choose("4", log, templates)
    with pytest.raises(TradeError, match="games 1 to 3, not 0"):
        choose("0", log, templates)


def test_a_template_that_is_not_a_game_of_the_match_is_refused(log, templates):
    with pytest.raises(TradeError, match="'Conquest' is not a game of this match"):
        choose("Conquest", log, templates)
    with pytest.raises(TradeError, match="not a game of this match"):
        choose("nonsense", log, templates)


def test_when_every_known_game_is_finished_the_bot_says_so(templates):
    done = replay(started(1, 1), town_bid(2, 1), color_bid(3, 1), templates=templates)
    with pytest.raises(TradeError, match="all the games decided so far are finished"):
        choose(None, done, templates, games=("JC",))


# --- starting, reopening --------------------------------------------------------------------------------------------


def test_a_game_never_started_is_started(log):
    assert check_startable(log, 3) == "start"


def test_a_closed_game_is_resumed(templates):
    log = replay(started(1, 1), started(2, 2), templates=templates)
    assert check_startable(log, 1) == "resume"


def test_the_open_game_cannot_be_started_again(log):
    with pytest.raises(TradeError, match="game 2 is already open"):
        check_startable(log, 2)


def test_a_finished_game_cannot_be_started_again(log):
    with pytest.raises(TradeError, match="game 1 is finished"):
        check_startable(log, 1)


# --- what the thread says ---------------------------------------------------------------------------------------------


def test_a_trade_start_gives_the_template_the_pair_and_the_starting_gold(trade, towns, templates):
    assert opening_line(trade, False, MENTIONS, towns, templates) == (
        "Game 1 (Jebus Cross): the trade starts. Pair: Necropolis (`necropolis`) vs Tower (`tower`). "
        "Starting gold: <@111> 10000, <@222> 10000"
    )


def test_the_opening_line_reads_back_as_the_record_it_came_from(trade, towns, templates):
    text = opening_line(trade, False, MENTIONS, towns, templates)
    assert parse(f"[#3 tr g1] {text}") == make_record(3, "trade_started", game=1, pair=PAIR)


def test_a_reopened_trade_says_it_continues_and_shows_the_difference_so_far(templates, towns):
    reopened = replay(started(1, 1), town_bid(2, 1), templates=templates).open
    text = opening_line(reopened, True, MENTIONS, towns, templates)
    assert text.startswith("Game 1 (Jebus Cross): the trade continues.")
    assert text.endswith("Gold difference: <@111> -2100, <@222> +2100")


def test_the_prompt_names_the_section_and_who_bids_first(trade):
    assert prompt(trade, MENTIONS) == (
        "Game 1 town bid. <@111> bids first, raising by at least 100. "
        "Report the result with /trade report, choosing a town of the pair."
    )
    after_town = trade.with_report(Report("town_bid", A, A, 2100, "necropolis"))
    assert prompt(after_town, MENTIONS).startswith("Game 1 color bid.")


def test_an_unfinished_trade_is_followed_by_its_prompt_and_a_finished_one_by_the_lobby_settings(templates, towns):
    half = replay(started(1, 1), town_bid(2, 1), templates=templates).open
    assert next_message(half, MENTIONS, towns, templates) == prompt(half, MENTIONS)
    done = replay(started(1, 1), town_bid(2, 1), color_bid(3, 1), templates=templates).open
    assert next_message(done, MENTIONS, towns, templates) == summary(done, MENTIONS, towns, templates)


def test_the_lobby_settings_give_each_players_town_color_and_gold_difference(templates, towns):
    done = replay(started(1, 1), town_bid(2, 1), color_bid(3, 1), templates=templates).open
    assert summary(done, MENTIONS, towns, templates).splitlines() == [
        "Game 1 lobby settings - Jebus Cross",
        "<@111>: Necropolis, blue, gold +900",
        "<@222>: Tower, red, gold -900",
    ]


def test_the_lobby_settings_when_the_same_player_wins_both_bids(templates, towns):
    done = replay(
        started(1, 1), town_bid(2, 1, winner=A, amount=1000, town="tower"), color_bid(3, 1, winner=A, amount=500, color="red"),
        templates=templates,
    ).open
    assert summary(done, MENTIONS, towns, templates).splitlines() == [
        "Game 1 lobby settings - Jebus Cross",
        "<@111>: Tower, red, gold -1500",
        "<@222>: Necropolis, blue, gold +1500",
    ]


def test_a_difference_of_nothing_is_written_as_zero(templates, towns):
    done = replay(
        started(1, 1), town_bid(2, 1, amount=0), color_bid(3, 1, amount=0), templates=templates
    ).open
    assert "gold 0" in summary(done, MENTIONS, towns, templates)


def test_a_town_bid_line_gives_the_result_and_the_gold_difference(templates, towns):
    trade = replay(started(1, 1), town_bid(2, 1), templates=templates).open
    assert report_line(trade, trade.reports[0], MENTIONS, towns) == (
        "Game 1 - Town bid, reported by <@111>: <@111> won at `2100` gold and plays Necropolis (`necropolis`), "
        "<@222> plays Tower.\nGold difference: <@111> -2100, <@222> +2100"
    )


def test_a_color_bid_line_gives_the_result_and_the_gold_difference(templates, towns):
    trade = replay(started(1, 1), town_bid(2, 1), color_bid(3, 1), templates=templates).open
    assert report_line(trade, trade.reports[1], MENTIONS, towns) == (
        "Game 1 - Color bid, reported by <@222>: <@222> won at `3000` gold and plays `red`, <@111> plays blue.\n"
        "Gold difference: <@111> +900, <@222> -900"
    )


def test_the_report_lines_read_back_as_the_records_they_came_from(templates, towns):
    trade = replay(started(1, 1), town_bid(2, 1, reporter=B), color_bid(3, 1, reporter=A), templates=templates).open
    town_line, color_line = (report_line(trade, r, MENTIONS, towns) for r in trade.reports)
    assert parse(f"[#2 tb g1] {town_line}") == town_bid(2, 1, reporter=B)
    assert parse(f"[#3 cb g1] {color_line}") == color_bid(3, 1, reporter=A)
