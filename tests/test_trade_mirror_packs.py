"""The mirror trade (one town for both players, only a color bid) and the trade with computer-player packs (a pair and
two packs of three towns, a pack bid between the town bid and the color bid): the draws, the rolls, the bids, the
records the wording writes and the replay that reads them back."""

import random
from pathlib import Path
from collections import Counter
from dataclasses import replace

import pytest

from rules.catalogue import load_towns, parse_templates
from rules.roll_rules import RollRules
from rules.trade import (
    Report,
    Roll,
    TradeError,
    check_roll,
    make_report,
    make_roll,
    new_trade,
    next_message,
    next_words,
    opening_line,
    prompt,
    replay_trades,
    report_line,
    roll_line,
    summary,
)
from rules.trade_draw import Draw, check_start, draw_start, draw_town, draw_with_packs
from rules.trade_kinds import TradeKind, check_trade
from state import make_record, parse

A, B = 111, 222
PLAYERS = (A, B)
MENTIONS = {A: "<@111>", B: "<@222>"}
ROLLS = RollRules(roll_cost=500, rolls_per_player=1, max_roll_bans=2)
NO_ROLLS = RollRules(roll_cost=500, rolls_per_player=0, max_roll_bans=2)
PACKS_KIND = check_trade("standard_with_ai_packs")
GAMES = ("h3dm1", "Sapphire", "JC")  # a mirror, a template with packs, a standard one


@pytest.fixture(scope="module")
def catalogue():
    return parse_templates(
        [
            {"id": "h3dm1", "name": "h3dm1", "difficulty": 160, "mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}},
            {"id": "Sapphire", "name": "Sapphire", "difficulty": 160, "trade": "standard_with_ai_packs"},
            {"id": "JC", "name": "Jebus Cross", "difficulty": 160},
        ],
        "templates.json",
    )


@pytest.fixture
def allowed(towns):
    return tuple(towns.ids[:9])


def mirror_trade(catalogue, rules=ROLLS, town="necropolis", game=1):
    return new_trade(game, GAMES, Draw((town,)), PLAYERS, catalogue, rules, TradeKind(), True)


def packs_trade(catalogue, rules=ROLLS, pair=("castle", "tower"), packs=("rampart", "inferno", "dungeon", "stronghold", "fortress", "cove")):
    return new_trade(2, GAMES, Draw(pair, packs), PLAYERS, catalogue, rules, PACKS_KIND, False)


def kind_of(catalogue):
    return lambda template: catalogue.find(template).details.get("trade", TradeKind())


TOWNS = load_towns(Path(__file__).resolve().parent.parent / "data" / "towns.json")


def named(*ids):
    """Town ids as the thread quotes them: by name."""
    return tuple(TOWNS.find(i).name for i in ids)


def replay(catalogue, allowed, *records, rules=ROLLS):
    return replay_trades(tuple(records), GAMES, PLAYERS, catalogue, allowed, lambda template: rules, kind_of(catalogue), TOWNS)


# --- the draws -----------------------------------------------------------------------------------------------------


def test_one_town_is_drawn_from_the_allowed_ones(allowed):
    (town,) = draw_town(allowed, random.Random(1))
    assert town in allowed


def test_a_banned_town_is_not_drawn(allowed):
    seen = {draw_town(allowed, random.Random(seed), banned=(allowed[0],))[0] for seed in range(80)}
    assert allowed[0] not in seen and len(seen) == len(allowed) - 1


def test_every_allowed_town_is_drawn_equally_often(allowed):
    rng = random.Random(5)
    counts = Counter(draw_town(allowed, rng)[0] for _ in range(4500))
    assert set(counts) == set(allowed) and all(400 < n < 600 for n in counts.values())


def test_no_town_left_to_draw_is_refused():
    with pytest.raises(TradeError, match="At least one town"):
        draw_town(("castle",), banned=("castle",))


def test_the_pair_and_the_packs_are_eight_different_allowed_towns(allowed):
    draw = draw_with_packs(allowed, random.Random(2))
    assert len(draw.towns) == 2 and len(draw.packs) == 6
    assert len(set(draw.words)) == 8 and set(draw.words) <= set(allowed)


def test_a_banned_town_is_never_in_the_pair_but_may_be_in_a_pack(towns):
    banned = (towns.ids[0], towns.ids[1])
    in_a_pack = set()
    for seed in range(300):
        draw = draw_with_packs(towns.ids, random.Random(seed), banned)
        assert not set(draw.towns) & set(banned)
        in_a_pack |= set(draw.packs) & set(banned)
    assert in_a_pack == set(banned)


def test_with_exactly_eight_towns_a_ban_still_leaves_a_draw(allowed):
    eight = allowed[:8]
    for seed in range(100):
        draw = draw_with_packs(eight, random.Random(seed), banned=(eight[0],))
        assert eight[0] not in draw.towns and set(draw.words) == set(eight)


def test_every_town_can_be_in_the_pair_or_a_pack_equally_often(allowed):
    rng = random.Random(9)
    counts = Counter(town for _ in range(3000) for town in draw_with_packs(allowed, rng).words)
    assert set(counts) == set(allowed)
    assert max(counts.values()) - min(counts.values()) < 0.1 * max(counts.values())


def test_every_town_not_banned_can_be_in_the_pair_equally_often(allowed):
    rng = random.Random(10)
    counts = Counter(town for _ in range(4000) for town in draw_with_packs(allowed, rng, banned=(allowed[0],)).towns)
    assert allowed[0] not in counts and set(counts) == set(allowed[1:])
    assert max(counts.values()) - min(counts.values()) < 0.2 * max(counts.values())


def test_fewer_than_eight_allowed_towns_is_refused(allowed):
    with pytest.raises(TradeError, match="At least eight"):
        draw_with_packs(allowed[:7])


def test_fewer_than_two_towns_that_are_not_banned_is_refused(allowed):
    with pytest.raises(TradeError, match="At least two towns that are not banned"):
        draw_with_packs(allowed[:8], banned=allowed[:7])


def test_draw_start_gives_what_the_kind_needs(allowed):
    rng = random.Random(3)
    assert len(draw_start(TradeKind(), False, allowed, rng).towns) == 2
    assert len(draw_start(TradeKind(), True, allowed, rng).towns) == 1
    draw = draw_start(PACKS_KIND, False, allowed, rng)
    assert len(draw.towns) == 2 and len(draw.packs) == 6
    assert draw_start(TradeKind(), False, allowed, rng).packs == ()


# --- the mirror trade ----------------------------------------------------------------------------------------------


def test_a_mirror_trade_has_the_roll_and_then_only_the_color_bid(catalogue):
    trade = mirror_trade(catalogue)
    assert trade.bids == ("color_bid",) and trade.section == "town_roll"
    assert mirror_trade(catalogue, NO_ROLLS).section == "color_bid"


def test_a_mirror_roll_bans_the_town_that_stands_and_draws_another(catalogue, towns, allowed):
    trade = mirror_trade(catalogue)
    roll = make_roll(trade, towns, allowed, A, [], random.Random(1))
    assert roll.bans == ("necropolis",) and len(roll.towns) == 1 and roll.towns != ("necropolis",)
    after = trade.with_roll(roll)
    assert after.towns == roll.towns and after.gold == {A: 9500, B: 10500}


def test_a_banned_town_never_comes_back_in_the_same_roll_section(catalogue, towns, allowed):
    trade = mirror_trade(catalogue, RollRules(500, 5, 2))
    seen = ["necropolis"]
    for seed in range(5):
        roll = make_roll(trade, towns, allowed, A if seed % 2 == 0 else B, [], random.Random(seed))
        assert roll.towns[0] not in seen
        seen.append(roll.towns[0])
        trade = trade.with_roll(roll)


def test_a_mirror_roll_that_names_a_town_is_refused(catalogue, towns, allowed):
    with pytest.raises(TradeError, match="names no town"):
        make_roll(mirror_trade(catalogue), towns, allowed, A, ["Castle"])


def test_a_mirror_roll_with_no_town_left_is_refused_and_nobody_pays(catalogue, towns):
    with pytest.raises(TradeError, match="No allowed town would be left"):
        make_roll(mirror_trade(catalogue, town="castle"), towns, ("castle",), A, [])


def test_a_mirror_roll_that_does_not_ban_the_town_that_stands_does_not_fit(catalogue, allowed):
    with pytest.raises(TradeError, match="bans the town that stands"):
        check_roll(mirror_trade(catalogue), Roll(A, (), Draw(("tower",))), allowed)


def test_reporting_a_town_in_a_mirror_says_the_color_is_bid(catalogue, towns, allowed):
    with pytest.raises(TradeError, match="only the color is bid"):
        make_report(mirror_trade(catalogue), towns, allowed, A, A, 0, "necropolis")


def test_the_color_bid_finishes_a_mirror_trade(catalogue, towns, allowed):
    trade = mirror_trade(catalogue)
    report = make_report(trade, towns, allowed, B, B, 3000, "red")
    after = trade.with_report(report)
    assert after.finished and after.gold == {A: 13000, B: 7000}


def test_a_town_chosen_in_the_color_bid_of_a_mirror_is_not_a_town_of_a_pair(catalogue, towns, allowed):
    with pytest.raises(TradeError):
        make_report(mirror_trade(catalogue), towns, allowed, A, A, 0, "pack1")


def test_the_mirror_summary_gives_the_one_town_and_the_colors(catalogue, towns):
    trade = mirror_trade(catalogue)
    trade = trade.with_report(Report("color_bid", B, B, 3000, "red"))
    lines = summary(trade, MENTIONS, towns, catalogue).splitlines()
    assert lines == [
        "Game 1 lobby settings - h3dm1",
        "Town (both players): Necropolis",
        "<@222>: red, gold -3 000",
        "<@111>: blue, gold +3 000",
    ]


def test_the_mirror_wording_says_one_town_and_how_to_roll(catalogue, towns):
    trade = mirror_trade(catalogue)
    text = prompt(trade, MENTIONS, towns)
    assert "Town: Necropolis" in text and "it bans this town" in text
    assert opening_line(trade, False, MENTIONS, towns, catalogue).splitlines() == [
        "Game 1 (h3dm1)",
        "Town: `Necropolis`",
        "Starting gold: 10 000",
    ]


def test_the_status_of_a_mirror_names_the_color_bid(catalogue, towns):
    assert next_words(mirror_trade(catalogue), towns) == ", next: color bid (rolls still open)"
    assert next_words(mirror_trade(catalogue, NO_ROLLS), towns) == ", next: color bid"


def test_what_the_mirror_wording_writes_is_read_back(catalogue, towns, allowed):
    trade = mirror_trade(catalogue)
    start = parse("[#3 tr g1] " + opening_line(trade, False, MENTIONS, towns, catalogue))
    assert start == make_record(3, "trade_started", 1, towns=("Necropolis",))
    roll = make_roll(trade, towns, allowed, A, [], random.Random(4))
    text = roll_line(trade.with_roll(roll), roll, MENTIONS, towns)
    assert parse("[#4 rl g1] " + text) == make_record(4, "roll", 1, player=A, bans=("Necropolis",), towns=named(*roll.towns))


def test_a_mirror_trade_is_replayed_from_its_records(catalogue, allowed, towns):
    trade = mirror_trade(catalogue)
    roll = make_roll(trade, towns, allowed, A, [], random.Random(4))
    log = replay(
        catalogue,
        allowed,
        make_record(3, "trade_started", 1, towns=("necropolis",)),
        make_record(4, "roll", 1, player=A, bans=("necropolis",), towns=roll.towns),
        make_record(5, "roll_skipped", 1, player=B),
        make_record(6, "color_bid", 1, reporter=B, winner=B, amount=3000, color="red"),
    )
    assert log.trades[1].finished and log.trades[1].towns == roll.towns


def test_a_mirror_start_with_two_towns_is_reported(catalogue, allowed):
    with pytest.raises(TradeError, match="starts with 1 different towns, not 2"):
        replay(catalogue, allowed, make_record(3, "trade_started", 1, towns=("castle", "tower")))


# --- the trade with computer-player packs --------------------------------------------------------------------------


def test_a_packs_trade_has_the_pack_bid_between_the_town_and_the_color(catalogue):
    trade = packs_trade(catalogue)
    assert trade.bids == ("town_bid", "pack_bid", "color_bid")
    assert trade.pack("pack1") == ("rampart", "inferno", "dungeon") and trade.pack("pack2") == ("stronghold", "fortress", "cove")


def test_a_roll_redraws_the_pair_and_both_packs_and_the_banned_town_stays_out_of_the_pair(catalogue, towns, allowed):
    trade = packs_trade(catalogue)
    roll = make_roll(trade, towns, allowed, A, ["Castle"], random.Random(1))
    assert roll.bans == ("castle",) and len(roll.towns) == 2 and len(roll.packs) == 6
    assert len(set(roll.draw.words)) == 8 and "castle" not in roll.towns
    after = trade.with_roll(roll)
    assert after.pack("pack1") == roll.packs[:3] and after.gold == {A: 9500, B: 10500}


def test_only_the_towns_of_the_pair_can_be_banned(catalogue, towns, allowed):
    with pytest.raises(TradeError, match="not in the current pair"):
        make_roll(packs_trade(catalogue), towns, allowed, A, ["Rampart"])  # a town of pack1


def test_a_banned_town_may_come_up_in_a_pack_of_the_next_draw(catalogue, towns, allowed):
    trade = packs_trade(catalogue)
    seen_in_a_pack = False
    for seed in range(200):
        roll = make_roll(trade, towns, allowed, A, ["Castle"], random.Random(seed))
        assert "castle" not in roll.towns
        seen_in_a_pack |= "castle" in roll.packs
    assert seen_in_a_pack


def test_with_exactly_eight_allowed_towns_a_roll_with_a_ban_works(catalogue, towns, allowed):
    eight = allowed[:8]
    trade = packs_trade(catalogue, pair=(eight[0], eight[1]), packs=eight[2:])
    roll = make_roll(trade, towns, eight, A, [towns.find(eight[0]).name], random.Random(3))
    assert eight[0] not in roll.towns and set(roll.draw.words) == set(eight)


def test_a_roll_that_leaves_fewer_than_two_towns_for_the_pair_is_refused(catalogue, towns, allowed):
    eight = allowed[:8]
    trade = packs_trade(catalogue, RollRules(500, 2, 2), pair=(eight[0], eight[1]), packs=eight[2:])
    banned_already = trade.with_roll(Roll(A, tuple(eight[2:7]), Draw((eight[0], eight[1]), eight[2:])))
    with pytest.raises(TradeError, match="Fewer than two allowed towns would be left to play"):
        make_roll(banned_already, towns, eight, B, [towns.find(eight[0]).name, towns.find(eight[1]).name])


def test_the_pack_bid_pays_and_gives_the_other_pack_to_the_other_player(catalogue, towns, allowed):
    trade = packs_trade(catalogue, NO_ROLLS)
    trade = trade.with_report(make_report(trade, towns, allowed, A, A, 2100, "castle"))
    assert trade.section == "pack_bid"
    report = make_report(trade, towns, allowed, A, A, 1200, "pack2")
    after = trade.with_report(report)
    assert after.gold == {A: 10000 - 2100 - 1200, B: 10000 + 2100 + 1200} and after.section == "color_bid"


@pytest.mark.parametrize("choice", ["pack3", "castle", "red", "Pack"])
def test_a_pack_that_does_not_exist_is_refused(catalogue, towns, allowed, choice):
    trade = packs_trade(catalogue, NO_ROLLS)
    trade = trade.with_report(make_report(trade, towns, allowed, A, A, 0, "castle"))
    with pytest.raises(TradeError, match="Choose pack1 or pack2"):
        make_report(trade, towns, allowed, A, A, 0, choice)


def test_the_pack_choice_is_not_case_sensitive(catalogue, towns, allowed):
    trade = packs_trade(catalogue, NO_ROLLS)
    trade = trade.with_report(make_report(trade, towns, allowed, A, A, 0, "castle"))
    assert make_report(trade, towns, allowed, A, A, 0, "PACK1").choice == "pack1"


def test_reporting_the_pack_before_the_town_is_refused(catalogue, towns, allowed):
    with pytest.raises(TradeError):
        make_report(packs_trade(catalogue, NO_ROLLS), towns, allowed, A, A, 0, "pack1")


def test_the_status_of_a_packs_trade_names_the_pack_bid(catalogue, towns, allowed):
    trade = packs_trade(catalogue, NO_ROLLS)
    trade = trade.with_report(make_report(trade, towns, allowed, A, A, 0, "castle"))
    assert next_words(trade, towns) == ", next: pack bid"


def full_packs_trade(catalogue, towns, allowed):
    """A wins the town (Castle, 2100) and the pack (pack2, 1200); B wins the color (red, 3000)."""
    trade = packs_trade(catalogue, NO_ROLLS)
    for winner, amount, choice in ((A, 2100, "castle"), (A, 1200, "pack2"), (B, 3000, "red")):
        trade = trade.with_report(make_report(trade, towns, allowed, winner, winner, amount, choice))
    return trade


def test_the_summary_of_a_packs_trade_gives_each_players_pack(catalogue, towns, allowed):
    trade = full_packs_trade(catalogue, towns, allowed)
    assert trade.finished
    lines = summary(trade, MENTIONS, towns, catalogue).splitlines()
    assert lines[1:] == [
        "<@222>: Tower, pack1 (Rampart, Inferno, Dungeon), red, gold +300",
        "<@111>: Castle, pack2 (Stronghold, Fortress, Cove), blue, gold -300",
    ]


def test_what_the_packs_wording_writes_is_read_back(catalogue, towns):
    allowed = tuple(towns.ids)  # the bans leave at least eight towns
    trade = packs_trade(catalogue)
    start = parse("[#3 tr g2] " + opening_line(trade, False, MENTIONS, towns, catalogue))
    assert start == make_record(3, "trade_started", 2, towns=("Castle", "Tower"), packs=named(*trade.packs))
    roll = make_roll(trade, towns, allowed, A, ["Castle", "Tower"], random.Random(8))
    parsed = parse("[#4 rl g2] " + roll_line(trade.with_roll(roll), roll, MENTIONS, towns))
    assert parsed == make_record(4, "roll", 2, player=A, bans=("Castle", "Tower"), towns=named(*roll.towns), packs=named(*roll.packs))


def test_the_pack_bid_wording_is_read_back(catalogue, towns, allowed):
    trade = packs_trade(catalogue, NO_ROLLS)
    trade = trade.with_report(make_report(trade, towns, allowed, A, A, 0, "castle"))
    report = make_report(trade, towns, allowed, B, A, 1200, "pack2")
    parsed = parse("[#5 pb g2] " + report_line(trade.with_report(report), report, MENTIONS, towns))
    assert parsed == make_record(5, "pack_bid", 2, reporter=B, winner=A, amount=1200, pack="pack2")


def test_the_prompts_of_a_packs_trade_name_the_packs(catalogue, towns, allowed):
    trade = packs_trade(catalogue)
    assert "Pack1: Rampart, Inferno, Dungeon\nPack2: Stronghold, Fortress, Cove" in prompt(trade, MENTIONS, towns)
    done = packs_trade(catalogue, NO_ROLLS)
    done = done.with_report(make_report(done, towns, allowed, A, A, 0, "castle"))
    assert "pack bid" in prompt(done, MENTIONS, towns) and "choosing pack1 or pack2" in prompt(done, MENTIONS, towns)
    assert "\nPack1: " in opening_line(trade, False, MENTIONS, towns, catalogue)


def test_a_packs_trade_is_replayed_from_its_records(catalogue, towns):
    allowed = tuple(towns.ids)
    pair, packs = ("castle", "tower"), ("rampart", "inferno", "dungeon", "stronghold", "fortress", "cove")
    log = replay(
        catalogue,
        allowed,
        make_record(3, "trade_started", 2, towns=pair, packs=packs),
        make_record(4, "town_bid", 2, reporter=A, winner=A, amount=2100, town="castle"),
        make_record(5, "pack_bid", 2, reporter=A, winner=B, amount=300, pack="pack1"),
        make_record(6, "color_bid", 2, reporter=B, winner=B, amount=0, color="red"),
        rules=NO_ROLLS,
    )
    assert log.trades[2].finished


def test_a_packs_start_without_packs_is_reported(catalogue, allowed):
    with pytest.raises(TradeError, match="starts with 8 different towns, not 2"):
        replay(catalogue, allowed, make_record(3, "trade_started", 2, towns=("castle", "tower")))


def test_a_packs_start_that_repeats_a_town_is_reported(catalogue, allowed):
    packs = ("castle", "inferno", "dungeon", "stronghold", "fortress", "cove")
    with pytest.raises(TradeError, match="different towns"):
        replay(catalogue, allowed, make_record(3, "trade_started", 2, towns=("castle", "tower"), packs=packs))


def test_a_standard_start_is_unchanged(catalogue, allowed):
    log = replay(catalogue, allowed, make_record(3, "trade_started", 3, towns=("castle", "tower")))
    assert log.trades[3].towns == ("castle", "tower") and not log.trades[3].mirror


def test_check_start_names_how_many_towns_a_kind_needs():
    with pytest.raises(TradeError, match="starts with 1"):
        check_start(Draw(("castle", "tower")), TradeKind(), True, ("castle", "tower"))


def test_check_start_refuses_a_town_that_is_not_allowed():
    with pytest.raises(TradeError, match="not allowed in this phase"):
        check_start(Draw(("castle", "tower")), TradeKind(), False, ("castle", "cove"))


# --- the wording after the pack bid, and a banned town in the next draw ----------------------------------------------


def test_after_the_pack_bid_a_wrong_choice_says_the_color_is_next(catalogue, towns, allowed):
    trade = packs_trade(catalogue, NO_ROLLS)
    for choice in ("castle", "pack1"):
        trade = trade.with_report(make_report(trade, towns, allowed, A, A, 0, choice))
    with pytest.raises(TradeError, match="The color bid is next. Choose red or blue."):
        make_report(trade, towns, allowed, A, A, 0, "pack2")


# --- messages stay within Discord's limit -----------------------------------------------------------------------------

BIG_MENTIONS = {A: "<@123456789012345678>", B: "<@876543210987654321>"}


def test_the_longest_messages_of_a_packs_trade_fit_in_a_discord_message(catalogue, towns):
    allowed = tuple(towns.ids)
    trade = packs_trade(catalogue, RollRules(500, 2, 2))
    roll = make_roll(trade, towns, allowed, A, ["Castle", "Tower"], random.Random(5))
    rolled = trade.with_roll(roll)
    done = rolled.with_report(Report("town_bid", A, A, 2100, rolled.towns[0]))
    done = done.with_report(Report("pack_bid", A, A, 1200, "pack2")).with_report(Report("color_bid", B, B, 3000, "red"))
    messages = [
        opening_line(trade, False, BIG_MENTIONS, towns, catalogue),
        opening_line(rolled, True, BIG_MENTIONS, towns, catalogue),
        roll_line(rolled, roll, BIG_MENTIONS, towns),
        prompt(rolled, BIG_MENTIONS, towns),
        summary(done, BIG_MENTIONS, towns, catalogue, lobby=["Timer: 16:00+07:00+01:30", "Map: XL+U", "Roads: mid", "AI players: 6"]),
        report_line(done, done.reports[1], BIG_MENTIONS, towns),
    ]
    assert all(len(message) < 1000 for message in messages)  # far under the 2000 characters Discord allows


# --- old threads, and several rolls through the thread's own text ---------------------------------------------------


def test_the_old_standard_wording_is_still_read():
    start = "[#3 tr g1] Game 1 (Jebus Cross) Pair: Necropolis (`necropolis`) vs Tower (`tower`). Starting gold: 10 000"
    roll = (
        "[#4 rl g1] Game 1 - <@1> rolled, banning Necropolis (`necropolis`), and paid 500 gold to <@2>. "
        "New pair: Cove (`cove`) vs Castle (`castle`).\nGold difference: <@1> -500, <@2> +500"
    )
    assert parse(start) == make_record(3, "trade_started", 1, towns=("necropolis", "tower"))
    assert parse(roll) == make_record(4, "roll", 1, player=1, bans=("necropolis",), towns=("cove", "castle"))


def play_rolls(catalogue, towns, allowed, rolls):
    """Play a packs trade through the thread's own text: every roll is written, parsed back and replayed."""
    trade = packs_trade(catalogue, RollRules(500, 2, 2), pair=("castle", "tower"))
    records = [parse("[#3 tr g2] " + opening_line(trade, False, MENTIONS, towns, catalogue))]
    for number, (player, bans) in enumerate(rolls, start=4):
        roll = make_roll(trade, towns, allowed, player, bans, random.Random(number))
        trade = trade.with_roll(roll)
        records.append(parse(f"[#{number} rl g2] " + roll_line(trade, roll, MENTIONS, towns)))
    return trade, records


def test_several_packs_rolls_survive_the_trip_through_the_thread(catalogue, towns):
    allowed = tuple(towns.ids)
    trade, records = play_rolls(catalogue, towns, allowed, [(A, ["Castle"]), (B, [])])
    replayed = replay(catalogue, allowed, *records, rules=RollRules(500, 2, 2)).trades[2]
    assert replayed.rolls == trade.rolls and replayed.draw == trade.draw
    assert "castle" in trade.banned and "castle" not in replayed.rolls[0].towns


def test_a_second_ban_adds_to_the_first_for_the_pair_only(catalogue, towns):
    allowed = tuple(towns.ids)
    first = packs_trade(catalogue, RollRules(500, 2, 2))
    roll = make_roll(first, towns, allowed, A, ["Castle"], random.Random(2))
    second = first.with_roll(roll)
    ban = towns.find(second.towns[0]).name
    again = make_roll(second, towns, allowed, B, [ban], random.Random(3))
    assert not set(again.towns) & {"castle", second.towns[0]}


def test_a_resumed_packs_trade_shows_the_packs_that_stand(catalogue, towns):
    allowed = tuple(towns.ids)
    trade = packs_trade(catalogue, RollRules(500, 2, 2))
    roll = make_roll(trade, towns, allowed, A, [], random.Random(6))
    rolled = trade.with_roll(roll)
    text = opening_line(rolled, True, MENTIONS, towns, catalogue)
    assert "the trade continues" in text and _pack_names(rolled, towns) in text
    assert parse("[#9 tu g2] " + text).type == "trade_resumed"


def _pack_names(trade, towns):
    return "\n".join(
        f"Pack{n}: " + ", ".join(f"`{towns.find(t).name}`" for t in trade.draw.pack(n - 1)) for n in (1, 2)
    )


def test_a_thread_that_quotes_town_ids_is_still_replayed(catalogue, towns):
    allowed = tuple(towns.ids)
    ids = replay(catalogue, allowed, make_record(3, "trade_started", 3, towns=("castle", "tower"))).trades[3]
    names = replay(catalogue, allowed, make_record(3, "trade_started", 3, towns=("Castle", "Tower"))).trades[3]
    assert ids.towns == names.towns == ("castle", "tower")


def test_a_quoted_name_that_is_no_town_fails_the_checks(catalogue, towns):
    with pytest.raises(TradeError, match="not allowed in this phase"):
        replay(catalogue, tuple(towns.ids), make_record(3, "trade_started", 3, towns=("Castle", "Atlantis")))


def test_a_roll_prompt_without_the_draw_has_only_the_roll_and_the_next_step(catalogue, towns):
    for trade in (mirror_trade(catalogue), packs_trade(catalogue)):
        lines = prompt(trade, MENTIONS, towns, show_draw=False).splitlines()
        assert lines[0] == "Next step: town roll" and lines[1] == "Cost: 500 gold"
        assert lines[2:4] == ["<@111>: 1 roll left", "<@222>: 1 roll left"] and lines[4].startswith("Roll with /trade roll (")
        assert len(lines) == 5


def test_the_packs_are_read_from_the_pack1_line_and_from_an_older_packs_line():
    new = "[#3 tr g2] Game 2 (Sapphire)\nPair: `Castle` vs `Tower`\nPack1: `A`, `B`, `C`\nPack2: `D`, `E`, `F`\nStarting gold: <@1> 1, <@2> 1"
    old = new.replace("\nPack1:", "\nPacks:\n  Pack1:")
    expected = make_record(3, "trade_started", 2, towns=("Castle", "Tower"), packs=("A", "B", "C", "D", "E", "F"))
    assert parse(new) == expected and parse(old) == expected
