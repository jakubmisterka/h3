import random
from collections import Counter

import pytest

from rules.catalogue import TEMPLATE_FIELDS, parse_catalogue
from rules.ledger import LedgerError
from rules.roll_rules import RollRules
from rules.trade import (
    Report,
    Roll,
    TradeError,
    TradeLog,
    check_startable,
    choose_game,
    draw_pair,
    make_report,
    make_roll,
    make_skip,
    new_trade,
    next_message,
    opening_line,
    prompt,
    replay_trades,
    report_line,
    roll_line,
    skip_line,
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


NO_ROLLS = RollRules(roll_cost=500, rolls_per_player=0, max_roll_bans=2)  # trades that start at the town bid
ROLLS = RollRules(roll_cost=500, rolls_per_player=1, max_roll_bans=2)  # the built-in defaults


def replay(*records, templates, games=GAMES, rules=NO_ROLLS, allowed=ALLOWED):
    return replay_trades(tuple(records), games, PLAYERS, templates, allowed, lambda template: rules)


@pytest.fixture
def trade(templates):
    return new_trade(1, GAMES, PAIR, PLAYERS, templates, NO_ROLLS)


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


def test_the_prompt_names_the_section_and_who_bids_first(trade, towns):
    assert prompt(trade, MENTIONS, towns) == (
        "Game 1 town bid: Necropolis vs Tower. <@111> bids first, raising by at least 100. "
        "Report the result with /trade report."
    )
    after_town = trade.with_report(Report("town_bid", A, A, 2100, "necropolis"))
    assert prompt(after_town, MENTIONS, towns).startswith("Game 1 color bid.")


def test_an_unfinished_trade_is_followed_by_its_prompt_and_a_finished_one_by_the_lobby_settings(templates, towns):
    half = replay(started(1, 1), town_bid(2, 1), templates=templates).open
    assert next_message(half, MENTIONS, towns, templates) == prompt(half, MENTIONS, towns)
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


# --- rolling ----------------------------------------------------------------------------------------------------------


def roll_record(n, game=1, player=A, bans=(), pair=("castle", "cove")):
    return make_record(n, "roll", game, player=player, bans=bans, pair=pair)


def skip_record(n, game=1, player=A):
    return make_record(n, "roll_skipped", game, player=player)


@pytest.fixture
def rolling(templates):
    """A trade of game 1 on the built-in roll rules: 500 gold, one roll each, up to two bans."""
    return new_trade(1, GAMES, PAIR, PLAYERS, templates, ROLLS)


def roll(trade, towns, player=A, bans=(), allowed=ALLOWED, seed=1):
    return make_roll(trade, towns, allowed, player, list(bans), random.Random(seed))


def test_a_trade_with_rolls_starts_in_the_roll_section_and_both_players_may_roll(rolling):
    assert rolling.section == "town_roll" and rolling.rollers == (A, B)


def test_a_trade_nobody_can_roll_in_starts_at_the_town_bid(trade):
    assert trade.rollers == () and trade.section == "town_bid"


def test_the_roll_section_announces_the_cost_and_who_may_roll(rolling, towns):
    assert prompt(rolling, MENTIONS, towns) == (
        "Game 1 town roll: Necropolis vs Tower. A roll costs 500 gold. Both players may roll. "
        "Roll with /trade roll (banning up to 2 towns of the pair), or skip with /trade skip-roll."
    )


def test_a_roll_pays_the_opponent_and_draws_a_new_pair_without_the_banned_town(rolling, towns):
    made = roll(rolling, towns, player=A, bans=["Necropolis"])
    after = rolling.with_roll(made)
    assert made.bans == ("necropolis",) and "necropolis" not in made.pair
    assert made.pair[0] != made.pair[1] and set(made.pair) <= set(ALLOWED)
    assert after.gold == {A: 9500, B: 10500} and after.pair == made.pair


def test_a_roll_without_bans_still_costs_and_draws_a_new_pair(rolling, towns):
    made = roll(rolling, towns, player=B)
    assert made.bans == () and rolling.with_roll(made).gold == {A: 10500, B: 9500}


def test_a_town_named_twice_is_banned_once(rolling, towns):
    assert roll(rolling, towns, bans=["Tower", "tower"]).bans == ("tower",)


def test_after_a_roll_the_other_player_may_still_roll_and_the_roller_may_not(rolling, towns):
    after = rolling.with_roll(roll(rolling, towns, player=A))
    assert after.rollers == (B,) and after.section == "town_roll"
    assert "A roll costs 500 gold. <@222> may roll." in prompt(after, MENTIONS, towns)


def test_only_the_player_who_can_pay_may_roll(templates, towns):
    expensive = RollRules(roll_cost=9800, rolls_per_player=2, max_roll_bans=2)
    trade = new_trade(1, GAMES, PAIR, PLAYERS, templates, expensive)
    after = trade.with_roll(roll(trade, towns, player=A))  # A is left with 200 and cannot roll again
    assert after.rollers == (B,)


def test_a_player_who_cannot_pay_is_refused_and_told_why(templates, towns):
    expensive = RollRules(roll_cost=9800, rolls_per_player=2, max_roll_bans=2)
    trade = new_trade(1, GAMES, PAIR, PLAYERS, templates, expensive)
    after = trade.with_roll(roll(trade, towns, player=A))
    with pytest.raises(TradeError, match="A roll costs 9800 gold and you have 200"):
        roll(after, towns, player=A)


def test_a_player_without_a_roll_left_is_refused(rolling, towns):
    after = rolling.with_roll(roll(rolling, towns, player=A))
    with pytest.raises(TradeError, match=r"no roll left \(1 per player\)"):
        roll(after, towns, player=A)


def test_a_player_who_skipped_is_refused(rolling, towns):
    with pytest.raises(TradeError, match="skipped your rolls"):
        roll(rolling.with_skip(A), towns, player=A)


def test_more_bans_than_allowed_are_refused_and_the_limit_stated(templates, towns):
    one_ban = new_trade(1, GAMES, PAIR, PLAYERS, templates, RollRules(500, 1, 1))
    with pytest.raises(TradeError, match="At most 1 town may be banned"):
        roll(one_ban, towns, bans=["Necropolis", "Tower"])


def test_a_town_outside_the_current_pair_cannot_be_banned(rolling, towns):
    with pytest.raises(TradeError, match="Castle is not in the current pair.*The pair is Necropolis, Tower"):
        roll(rolling, towns, bans=["Castle"])
    with pytest.raises(TradeError, match="'Atlantis' is not a town"):
        roll(rolling, towns, bans=["Atlantis"])


def test_a_roll_that_would_leave_fewer_than_two_towns_is_refused_and_nobody_pays(templates, towns):
    three = ("castle", "necropolis", "tower")
    trade = new_trade(1, GAMES, ("necropolis", "tower"), PLAYERS, templates, ROLLS)
    with pytest.raises(TradeError, match="Fewer than two allowed towns.*nobody paid"):
        roll(trade, towns, bans=["Necropolis", "Tower"], allowed=three)
    assert trade.gold == {A: 10000, B: 10000}


def test_banned_towns_stay_out_of_every_later_draw(templates, towns):
    trade = new_trade(1, GAMES, PAIR, PLAYERS, templates, RollRules(500, 2, 2))
    for seed in range(40):
        first = roll(trade, towns, player=A, bans=[towns.find(trade.pair[0]).name], seed=seed)
        again = trade.with_roll(first)
        second = roll(again, towns, player=A, bans=[towns.find(again.pair[0]).name], seed=seed + 100)
        assert set(second.pair) & set(again.banned + second.bans) == set()


def test_an_unbanned_town_of_the_old_pair_may_come_back(rolling, towns):
    seen = {town for seed in range(60) for town in roll(rolling, towns, bans=["Tower"], seed=seed).pair}
    assert "necropolis" in seen and "tower" not in seen


def test_every_allowed_town_that_is_not_banned_is_equally_likely_in_a_new_pair(rolling, towns):
    counts = Counter(town for seed in range(3000) for town in roll(rolling, towns, bans=["Tower"], seed=seed).pair)
    assert set(counts) == {"castle", "necropolis", "cove"}
    assert all(1700 < count < 2300 for count in counts.values())  # 3000 pairs of 2 from 3: about 2000 each


def test_a_roll_cannot_be_made_after_the_roll_section(trade, towns):
    with pytest.raises(TradeError, match="roll section is over. The town bid is expected now"):
        roll(trade, towns)


# --- skipping the roll ---------------------------------------------------------------------------------------------------


def test_a_player_can_skip_their_roll_and_then_the_section_waits_for_the_other(rolling):
    make_skip(rolling, A)  # no error
    after = rolling.with_skip(A)
    assert after.section == "town_roll" and after.rollers == (B,)


def test_when_both_players_skip_the_town_bid_starts_with_the_pair_unchanged(rolling):
    after = rolling.with_skip(A).with_skip(B)
    assert after.section == "town_bid" and after.pair == PAIR and after.gold == {A: 10000, B: 10000}


def test_when_one_rolls_and_the_other_skips_the_town_bid_starts_with_the_new_pair(rolling, towns):
    made = roll(rolling, towns, player=A)
    after = rolling.with_roll(made).with_skip(B)
    assert after.section == "town_bid" and after.pair == made.pair


def test_a_player_with_no_roll_to_skip_is_told_why(rolling, towns):
    after = rolling.with_roll(roll(rolling, towns, player=A))
    with pytest.raises(TradeError, match="no roll left"):
        make_skip(after, A)
    with pytest.raises(TradeError, match="one of the two players"):
        make_skip(rolling, 333)


def test_a_roll_cannot_be_skipped_after_the_roll_section(trade):
    with pytest.raises(TradeError, match="roll section is over"):
        make_skip(trade, A)


# --- reporting the town bid ends the roll section -------------------------------------------------------------------------


def test_reporting_the_town_bid_while_rolls_are_open_skips_them(rolling, towns):
    after = rolling.with_report(make_report(rolling, towns, ALLOWED, A, A, 2100, "Necropolis"))
    assert after.section == "color_bid"


def test_the_cost_of_a_roll_lowers_what_can_be_bid(rolling, towns):
    after = rolling.with_roll(roll(rolling, towns, player=A))  # A paid 500 and has 9500
    with pytest.raises(LedgerError, match="9600 gold is more than the 9500"):
        make_report(after, towns, ALLOWED, A, A, 9600, after.pair[0])


def test_a_color_cannot_be_reported_during_the_roll_section(rolling, towns):
    with pytest.raises(TradeError, match="town bid comes first"):
        make_report(rolling, towns, ALLOWED, A, A, 100, "red")


# --- rolls in the records of a thread -------------------------------------------------------------------------------------


def test_rolls_and_skips_are_replayed_in_order(templates):
    log = replay(
        started(1, 1), roll_record(2, bans=("necropolis",), pair=("castle", "cove")), skip_record(3, player=B),
        templates=templates, rules=ROLLS,
    )
    trade = log.open
    assert trade.pair == ("castle", "cove") and trade.section == "town_bid" and trade.gold == {A: 9500, B: 10500}


def test_the_new_pair_is_the_one_a_town_bid_is_reported_on(templates):
    log = replay(
        started(1, 1), roll_record(2, pair=("castle", "cove")), skip_record(3, player=B), town_bid(4, 1, town="cove"),
        templates=templates, rules=ROLLS,
    )
    assert log.open.reports[0].choice == "cove"


def test_a_town_bid_during_the_roll_section_is_accepted_as_a_skip(templates):
    log = replay(started(1, 1), town_bid(2, 1), templates=templates, rules=ROLLS)
    assert log.open.section == "color_bid"


def test_a_trade_reopened_after_a_roll_keeps_the_new_pair_and_the_gold(templates):
    log = replay(
        started(1, 1), roll_record(2, pair=("castle", "cove")), started(3, 2), resumed(4, 1), templates=templates, rules=ROLLS
    )
    assert log.open.pair == ("castle", "cove") and log.open.gold == {A: 9500, B: 10500}


@pytest.mark.parametrize(
    "records, problem",
    [
        ([started(1, 1), roll_record(2, player=333)], "one of the two players"),
        ([started(1, 1), roll_record(2), roll_record(3)], "no roll left"),
        ([started(1, 1), skip_record(2), roll_record(3)], "skipped your rolls"),
        ([started(1, 1), roll_record(2, bans=("castle",))], "Only towns of the current pair"),
        ([started(1, 1), roll_record(2, bans=("necropolis", "tower", "castle"))], "At most 2 towns"),
        ([started(1, 1), roll_record(2, bans=("necropolis",), pair=("necropolis", "cove"))], "must be two different allowed towns"),
        ([started(1, 1), roll_record(2, pair=("cove", "cove"))], "must be two different allowed towns"),
        ([started(1, 1), roll_record(2, pair=("cove", "atlantis"))], "must be two different allowed towns"),
        ([started(1, 1), town_bid(2, 1), roll_record(3)], "roll section is over"),
        ([started(1, 1), skip_record(2), skip_record(3)], "skipped your rolls"),
        ([roll_record(1)], "never started"),
        ([started(1, 1), started(2, 2), roll_record(3, game=1)], "was not open"),
    ],
)
def test_a_roll_record_that_does_not_fit_is_reported_not_trusted(templates, records, problem):
    with pytest.raises(TradeError, match=f"Message #{records[-1].n} .*does not fit the trade.*{problem}"):
        replay(*records, templates=templates, rules=ROLLS)


# --- what the thread says about rolls ------------------------------------------------------------------------------------


def test_a_roll_line_gives_the_roller_the_bans_the_new_pair_and_the_gold_difference(rolling, towns):
    made = Roll(A, ("necropolis",), ("castle", "cove"))
    assert roll_line(rolling.with_roll(made), made, MENTIONS, towns) == (
        "Game 1 - <@111> rolled, banning Necropolis (`necropolis`), and paid 500 gold to <@222>. "
        "New pair: Castle (`castle`) vs Cove (`cove`).\nGold difference: <@111> -500, <@222> +500"
    )


def test_a_roll_line_without_bans_says_so(rolling, towns):
    made = Roll(B, (), ("castle", "cove"))
    assert "<@222> rolled without banning a town, and paid 500 gold to <@111>." in roll_line(
        rolling.with_roll(made), made, MENTIONS, towns
    )


def test_the_roll_lines_read_back_as_the_records_they_came_from(rolling, towns):
    first = Roll(A, ("necropolis", "tower"), ("castle", "cove"))
    second = Roll(B, (), ("castle", "tower"))
    assert parse("[#2 rl g1] " + roll_line(rolling.with_roll(first), first, MENTIONS, towns)) == roll_record(
        2, player=A, bans=("necropolis", "tower"), pair=("castle", "cove")
    )
    assert parse("[#3 rl g1] " + roll_line(rolling.with_roll(second), second, MENTIONS, towns)) == roll_record(
        3, player=B, bans=(), pair=("castle", "tower")
    )


def test_a_skip_line_reads_back_as_the_record_it_came_from(rolling):
    assert skip_line(rolling, B, MENTIONS) == "Game 1 - <@222> skips the roll."
    assert parse("[#4 rs g1] " + skip_line(rolling, B, MENTIONS)) == skip_record(4, player=B)


def test_a_reopened_trade_names_the_pair_that_stands(templates, towns):
    trade = replay(started(1, 1), roll_record(2, pair=("castle", "cove")), templates=templates, rules=ROLLS).open
    assert "Pair: Castle (`castle`) vs Cove (`cove`)" in opening_line(trade, True, MENTIONS, towns, templates)
    assert "Pair: Necropolis (`necropolis`) vs Tower (`tower`)" in opening_line(trade, False, MENTIONS, towns, templates)


def test_the_roll_prompt_names_the_pair_that_stands_now(rolling, towns):
    made = Roll(A, ("necropolis",), ("castle", "cove"))
    assert prompt(rolling, MENTIONS, towns).startswith("Game 1 town roll: Necropolis vs Tower. ")
    assert prompt(rolling.with_roll(made), MENTIONS, towns).startswith("Game 1 town roll: Castle vs Cove. ")
