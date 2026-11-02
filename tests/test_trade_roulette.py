"""The heroes of a roulette trade: the bans (each player in turn, the first player first), the draw the bot makes, the
sections that follow from them, the records they are written as and the replay that reads them back."""

import random
from collections import Counter

import pytest

from rules.catalogue import parse_heroes, parse_templates
from rules.roll_rules import RollRules
from rules.trade import (
    HeroBan,
    Report,
    TradeError,
    check_hero_ban,
    check_heroes_drawn,
    draw_heroes,
    hero_bans_line,
    hero_pool,
    heroes_drawn_line,
    make_hero_ban,
    make_heroes_drawn,
    make_report,
    new_trade,
    next_words,
    opening_line,
    prompt,
    replay_trades,
    report_line,
    summary,
)
from rules.trade_draw import Draw
from rules.trade_kinds import check_trade
from state import describe, make_record, parse

A, B = 111, 222
PLAYERS = (A, B)
MENTIONS = {A: "<@111>", B: "<@222>"}
GAMES = ("JC", "Diamond", "h3dm1")
NO_ROLLS = RollRules(roll_cost=500, rolls_per_player=0, max_roll_bans=2)
ROLLS = RollRules(roll_cost=500, rolls_per_player=1, max_roll_bans=2)
ONE_BAN = check_trade({"kind": "roulette", "hero_bans": 1})
TWO_BANS = check_trade({"kind": "roulette", "hero_bans": 2})
NO_BANS = check_trade("roulette")
ALLOWED = ("castle", "tower", "cove")


def hero(hero_id, town, **flags):
    return {"id": hero_id, "name": hero_id.capitalize(), "town": town, "link": f"https://example.com/{hero_id}", **flags}


@pytest.fixture(scope="module")
def heroes(towns):
    data = [hero(f"c{n}", "castle") for n in range(1, 7)] + [hero(f"t{n}", "tower") for n in range(1, 7)]
    data += [hero("cdef", "castle", banned_by_default=True), hero("tmir", "tower", banned_on_mirrors=True)]
    return parse_heroes(data, "heroes.json", towns)


def trade_of(templates, kind=ONE_BAN, mirror=False, rules=NO_ROLLS, towns=("castle", "tower")):
    return new_trade(1, GAMES, Draw(towns if not mirror else towns[:1]), PLAYERS, templates, rules, kind, mirror)


def ban(trade, heroes, templates, player, *names):
    made = make_hero_ban(trade, heroes, templates, player, list(names))
    return trade.with_hero_ban(made)


def drawn(trade, heroes, templates, seed=1):
    return trade.with_heroes(make_heroes_drawn(trade, heroes, templates, random.Random(seed)))


# --- the order of the sections --------------------------------------------------------------------------------------------


def test_after_the_rolls_the_heroes_are_banned_before_the_bid(templates):
    trade = trade_of(templates)
    assert trade.section == "hero_bans" and trade.ban_turn == A


def test_while_a_player_can_still_roll_the_roll_section_comes_first(templates):
    assert trade_of(templates, rules=ROLLS).section == "town_roll"
    after = trade_of(templates, rules=ROLLS).with_skip(A).with_skip(B)
    assert after.section == "hero_bans"


def test_without_hero_bans_the_heroes_are_drawn_as_soon_as_the_rolls_are_over(templates):
    trade = trade_of(templates, kind=NO_BANS)
    assert trade.section == "hero_draw" and trade.ban_turn is None


def test_the_first_player_bans_first_and_then_the_second(templates, heroes):
    trade = trade_of(templates)
    trade = ban(trade, heroes, templates, A, "C1")
    assert trade.section == "hero_bans" and trade.ban_turn == B
    trade = ban(trade, heroes, templates, B, "T1")
    assert trade.section == "hero_draw"


def test_after_the_draw_the_bids_follow(templates, heroes):
    trade = drawn(ban(ban(trade_of(templates), heroes, templates, A), heroes, templates, B), heroes, templates)
    assert trade.section == "town_bid" and trade.bids == ("town_bid", "color_bid")


def test_a_trade_of_another_kind_has_no_hero_steps(templates):
    standard = new_trade(1, GAMES, Draw(("castle", "tower")), PLAYERS, templates, NO_ROLLS)
    assert standard.section == "town_bid" and not standard.heroes_after_rolls


# --- the bans -------------------------------------------------------------------------------------------------------------


def test_a_player_may_ban_nobody(templates, heroes):
    made = make_hero_ban(trade_of(templates), heroes, templates, A, [])
    assert made == HeroBan(A, ())


def test_a_hero_is_banned_by_name_or_id_in_any_letter_case(templates, heroes):
    trade = trade_of(templates, kind=TWO_BANS)
    assert make_hero_ban(trade, heroes, templates, A, ["c1", "C2"]).heroes == ("c1", "c2")


def test_naming_a_hero_twice_bans_it_once(templates, heroes):
    assert make_hero_ban(trade_of(templates, kind=TWO_BANS), heroes, templates, A, ["C1", "c1"]).heroes == ("c1",)


def test_the_second_player_cannot_ban_first(templates, heroes):
    with pytest.raises(TradeError, match="other player's turn"):
        make_hero_ban(trade_of(templates), heroes, templates, B, ["T1"])


def test_a_stranger_cannot_ban(templates, heroes):
    with pytest.raises(TradeError, match="Only one of the two players"):
        make_hero_ban(trade_of(templates), heroes, templates, 333, [])


def test_more_heroes_than_the_tournament_allows_are_refused_and_the_limit_stated(templates, heroes):
    with pytest.raises(TradeError, match="At most 1 hero may be banned"):
        make_hero_ban(trade_of(templates), heroes, templates, A, ["C1", "T1"])
    with pytest.raises(TradeError, match="At most 2 heroes may be banned"):
        make_hero_ban(trade_of(templates, kind=TWO_BANS), heroes, templates, A, ["C1", "C2", "C3"])


@pytest.mark.parametrize("name", ["nobody", ""])
def test_a_name_that_is_no_hero_is_refused(templates, heroes, name):
    with pytest.raises(TradeError, match="is not a hero"):
        make_hero_ban(trade_of(templates), heroes, templates, A, [name])


def test_a_hero_of_another_town_cannot_be_banned(templates, heroes):
    trade = trade_of(templates, towns=("castle", "cove"))
    with pytest.raises(TradeError, match="T1 cannot be banned"):
        make_hero_ban(trade, heroes, templates, A, ["T1"])


def test_a_hero_the_map_does_not_offer_cannot_be_banned(templates, heroes):
    with pytest.raises(TradeError, match="Cdef cannot be banned"):  # banned by default
        make_hero_ban(trade_of(templates), heroes, templates, A, ["Cdef"])


def test_a_hero_banned_already_cannot_be_banned_again(templates, heroes):
    trade = ban(trade_of(templates), heroes, templates, A, "C1")
    with pytest.raises(TradeError, match="C1 cannot be banned"):
        make_hero_ban(trade, heroes, templates, B, ["C1"])


def test_a_ban_after_the_bans_are_over_is_refused(templates, heroes):
    trade = ban(ban(trade_of(templates), heroes, templates, A), heroes, templates, B)
    with pytest.raises(TradeError, match="cannot be banned now"):
        make_hero_ban(trade, heroes, templates, A, [])


def test_a_ban_that_would_leave_too_few_heroes_is_refused(templates, towns):
    few = parse_heroes([hero("c1", "castle"), hero("c2", "castle"), hero("c3", "castle")], "heroes.json", towns)
    mirror = trade_of(templates, mirror=True, towns=("castle",)).with_hero_ban(HeroBan(A, ("c1",)))  # c2 and c3 are left
    with pytest.raises(TradeError, match="Too few heroes"):
        check_hero_ban(mirror, HeroBan(B, ("c2",)), few, templates)  # a mirror draws two


# --- the draw -------------------------------------------------------------------------------------------------------------


def test_a_pair_gets_one_hero_of_each_town_in_the_order_of_the_towns(templates, heroes):
    for seed in range(40):
        first, second = draw_heroes(trade_of(templates), heroes, templates, random.Random(seed))
        assert heroes.find(first).details["town"] == "castle" and heroes.find(second).details["town"] == "tower"


def test_a_mirror_gets_two_different_heroes_of_its_town(templates, heroes):
    mirror = trade_of(templates, mirror=True, towns=("castle",))
    for seed in range(40):
        a, b = draw_heroes(mirror, heroes, templates, random.Random(seed))
        assert a != b and heroes.find(a).details["town"] == heroes.find(b).details["town"] == "castle"


def test_the_heroes_that_are_banned_by_a_player_or_by_default_are_never_drawn(templates, heroes):
    trade = ban(trade_of(templates), heroes, templates, A, "C1")
    trade = ban(trade, heroes, templates, B, "T1")
    seen = set()
    for seed in range(300):
        seen |= set(draw_heroes(trade, heroes, templates, random.Random(seed)))
    assert not seen & {"c1", "t1", "cdef"}
    assert seen == {"c2", "c3", "c4", "c5", "c6", "t2", "t3", "t4", "t5", "t6", "tmir"}


def test_the_hero_banned_on_mirrors_is_drawn_for_a_pair_but_not_for_a_mirror(templates, heroes):
    mirror = new_trade(1, GAMES, Draw(("tower",)), PLAYERS, templates, NO_ROLLS, ONE_BAN, True)
    mirror_templates = parse_templates(
        [{"id": "JC", "name": "JC", "difficulty": 160, "mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}},
         {"id": "Diamond", "name": "Diamond", "difficulty": 160}, {"id": "h3dm1", "name": "h3dm1", "difficulty": 160}],
        "t",
    )
    seen = set()
    for seed in range(200):
        seen |= set(draw_heroes(mirror, heroes, mirror_templates, random.Random(seed)))
    assert "tmir" not in seen and seen == {"t1", "t2", "t3", "t4", "t5", "t6"}


def test_every_hero_that_can_be_drawn_is_drawn_equally_often(templates, heroes):
    counts = Counter(draw_heroes(trade_of(templates), heroes, templates, random.Random(seed))[0] for seed in range(3000))
    assert set(counts) == {"c1", "c2", "c3", "c4", "c5", "c6"} and max(counts.values()) - min(counts.values()) < 250


def test_a_mirror_without_two_heroes_left_is_refused(templates, towns):
    one = parse_heroes([hero("c1", "castle")], "heroes.json", towns)
    with pytest.raises(TradeError, match="Fewer than two heroes"):
        draw_heroes(trade_of(templates, mirror=True, towns=("castle",)), one, templates)


def test_a_town_without_heroes_is_refused(templates, towns):
    only_castle = parse_heroes([hero("c1", "castle")], "heroes.json", towns)
    with pytest.raises(TradeError, match="No hero can be drawn"):
        draw_heroes(trade_of(templates), only_castle, templates)


def test_the_pool_is_what_the_map_offers_less_the_bans(templates, heroes):
    trade = ban(trade_of(templates), heroes, templates, A, "C1")
    assert "c1" not in hero_pool(trade, heroes, templates)["castle"] and "cdef" not in hero_pool(trade, heroes, templates)["castle"]


def test_a_draw_that_is_not_allowed_is_refused_by_the_check(templates, heroes):
    trade = ban(ban(trade_of(templates), heroes, templates, A, "C1"), heroes, templates, B)
    for wrong in (("c1", "t2"), ("c2", "c3"), ("c2", "c2"), ("c2",), ("cdef", "t2")):
        with pytest.raises(TradeError):
            check_heroes_drawn(trade, wrong, heroes, templates)
    check_heroes_drawn(trade, ("c2", "t2"), heroes, templates)


def test_the_heroes_cannot_be_drawn_before_their_time_or_twice(templates, heroes):
    with pytest.raises(TradeError, match="cannot be drawn now"):
        make_heroes_drawn(trade_of(templates), heroes, templates)
    done = drawn(ban(ban(trade_of(templates), heroes, templates, A), heroes, templates, B), heroes, templates)
    with pytest.raises(TradeError, match="cannot be drawn now"):
        make_heroes_drawn(done, heroes, templates)


# --- the bid waits for the heroes ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("rules", [NO_ROLLS, ROLLS])
def test_a_bid_before_the_heroes_are_drawn_is_refused(templates, towns, rules):
    trade = trade_of(templates, rules=rules)
    with pytest.raises(TradeError, match="heroes are banned and drawn before the bid"):
        make_report(trade, towns, ALLOWED, A, A, 0, "Castle")


def test_the_refusal_says_what_comes_first(templates, towns, heroes):
    with pytest.raises(TradeError, match="Finish the roll section first"):
        make_report(trade_of(templates, rules=ROLLS), towns, ALLOWED, A, A, 0, "Castle")
    with pytest.raises(TradeError, match=r"ban them with /trade ban-heroes"):
        make_report(trade_of(templates), towns, ALLOWED, A, A, 0, "Castle")
    with pytest.raises(TradeError, match="are being drawn"):
        make_report(trade_of(templates, kind=NO_BANS), towns, ALLOWED, A, A, 0, "Castle")


def test_after_the_draw_the_town_bid_is_accepted_as_in_any_trade(templates, towns, heroes):
    trade = drawn(trade_of(templates, kind=NO_BANS), heroes, templates)
    report = make_report(trade, towns, ALLOWED, A, A, 2100, "Castle")
    assert trade.with_report(report).gold == {A: 7900, B: 12100}


# --- the wording and the records -------------------------------------------------------------------------------------------


def test_the_hero_bans_line_names_the_player_and_the_heroes(templates, heroes):
    trade = trade_of(templates, kind=TWO_BANS)
    assert hero_bans_line(trade, HeroBan(A, ("c1", "c2")), MENTIONS, heroes) == "Game 1 - <@111> bans `C1`, `C2`."
    assert hero_bans_line(trade, HeroBan(A, ()), MENTIONS, heroes) == "Game 1 - <@111> bans no hero."


def test_the_hero_bans_line_reads_back_as_the_record_it_came_from(templates, heroes):
    trade = trade_of(templates, kind=TWO_BANS)
    text = hero_bans_line(trade, HeroBan(A, ("c1", "c2")), MENTIONS, heroes)
    assert parse(f"[#5 hb g1] {text}") == make_record(5, "hero_bans", 1, player=A, heroes=("C1", "C2"))
    empty = hero_bans_line(trade, HeroBan(B, ()), MENTIONS, heroes)
    assert parse(f"[#6 hb g1] {empty}") == make_record(6, "hero_bans", 1, player=B, heroes=())


def test_the_drawn_heroes_are_listed_with_their_town_and_a_link(templates, heroes, towns):
    trade = trade_of(templates)
    assert heroes_drawn_line(trade, ("c2", "t3"), towns, heroes).splitlines() == [
        "Game 1 - The heroes are drawn:",
        "`C2` (Castle) <https://example.com/c2>",
        "`T3` (Tower) <https://example.com/t3>",
    ]


def test_a_mirror_lists_its_heroes_without_the_town(templates, heroes, towns):
    mirror = trade_of(templates, mirror=True, towns=("castle",))
    assert heroes_drawn_line(mirror, ("c2", "c3"), towns, heroes).splitlines()[1:] == [
        "`C2` <https://example.com/c2>",
        "`C3` <https://example.com/c3>",
    ]


def test_the_drawn_heroes_line_reads_back_as_the_record_it_came_from(templates, heroes, towns):
    text = heroes_drawn_line(trade_of(templates), ("c2", "t3"), towns, heroes)
    assert parse(f"[#7 hd g1] {text}") == make_record(7, "heroes_drawn", 1, heroes=("C2", "T3"))


def test_the_prompt_says_whose_turn_it_is_and_how_many_heroes_may_be_banned(templates, towns):
    text = prompt(trade_of(templates), MENTIONS, towns)
    assert text.splitlines() == [
        "Next step: hero bans",
        "<@111> may ban up to 1 hero of Castle vs Tower",
        "Ban with /trade ban-heroes; ban nobody by sending it without a hero",
    ]
    assert "<@111> may ban up to 2 heroes of" in prompt(trade_of(templates, kind=TWO_BANS), MENTIONS, towns)


def test_the_status_names_the_hero_sections(templates, towns):
    assert next_words(trade_of(templates), towns) == ", next: hero bans"
    assert next_words(trade_of(templates, kind=NO_BANS), towns) == ", next: hero draw"


def test_the_opening_of_a_roulette_says_so(templates, towns):
    assert opening_line(trade_of(templates), False, MENTIONS, towns, templates).splitlines()[0] == "Game 1 (Jebus Cross)"


def test_a_reopened_roulette_shows_the_heroes_that_were_drawn(templates, heroes, towns):
    trade = drawn(ban(ban(trade_of(templates), heroes, templates, A), heroes, templates, B), heroes, templates)
    text = opening_line(trade, True, MENTIONS, towns, templates, heroes)
    assert all(f"`{heroes.find(hero_id).name}`" in text for hero_id in trade.drawn_heroes)


def test_the_lobby_settings_give_each_player_the_hero_of_their_town(templates, heroes, towns):
    trade = trade_of(templates, kind=NO_BANS)
    trade = trade.with_heroes(("c2", "t3"))
    trade = trade.with_report(Report("town_bid", A, A, 0, "castle")).with_report(Report("color_bid", B, B, 0, "red"))
    lines = summary(trade, MENTIONS, towns, templates, heroes=heroes).splitlines()
    assert lines[1:] == ["<@222>: Tower (T3), red, gold 0", "<@111>: Castle (C2), blue, gold 0"]


def test_the_records_are_described(templates):
    assert describe(make_record(5, "hero_bans", 1, player=A, heroes=("C1",))) == "game 1: <@111> banned C1"
    assert describe(make_record(5, "hero_bans", 1, player=A, heroes=())) == "game 1: <@111> banned no hero"
    assert describe(make_record(6, "heroes_drawn", 1, heroes=("C2", "T3"))) == "game 1: heroes drawn: C2, T3"


# --- the replay ------------------------------------------------------------------------------------------------------------


def replay(records, templates, towns, heroes, kind=ONE_BAN, rules=NO_ROLLS):
    return replay_trades(tuple(records), GAMES, PLAYERS, templates, ALLOWED, lambda t: rules, lambda t: kind, towns, heroes)


START = make_record(3, "trade_started", 1, towns=("Castle", "Tower"))


def full_records():
    return [
        START,
        make_record(4, "hero_bans", 1, player=A, heroes=("C1",)),
        make_record(5, "hero_bans", 1, player=B, heroes=()),
        make_record(6, "heroes_drawn", 1, heroes=("C2", "T3")),
        make_record(7, "town_bid", 1, reporter=A, winner=A, amount=0, town="Castle"),
        make_record(8, "color_bid", 1, reporter=B, winner=B, amount=0, color="red"),
    ]


def test_a_roulette_is_replayed_from_its_records(templates, heroes, towns):
    trade = replay(full_records(), templates, towns, heroes).trades[1]
    assert trade.finished and trade.banned_heroes == ("c1",) and trade.drawn_heroes == ("c2", "t3")


def test_a_roulette_without_hero_bans_is_replayed(templates, heroes, towns):
    records = [START, make_record(4, "heroes_drawn", 1, heroes=("C2", "T3"))]
    assert replay(records, templates, towns, heroes, kind=NO_BANS).trades[1].section == "town_bid"


@pytest.mark.parametrize(
    "records, message",
    [
        ([START, make_record(4, "hero_bans", 1, player=B, heroes=())], "other player's turn"),
        ([START, make_record(4, "hero_bans", 1, player=A, heroes=("C1", "C2"))], "At most 1 hero may be banned"),
        ([START, make_record(4, "hero_bans", 1, player=A, heroes=("Atlantis",))], "cannot be banned"),
        ([START, make_record(4, "heroes_drawn", 1, heroes=("C2", "T3"))], "cannot be drawn now"),
        (full_records()[:3] + [make_record(6, "heroes_drawn", 1, heroes=("C1", "T3"))], "cannot be the hero of castle|not one of the heroes"),
        (full_records()[:3] + [make_record(6, "heroes_drawn", 1, heroes=("C2", "C3"))], "cannot be the hero of tower|not one of the heroes"),
        ([START, make_record(4, "town_bid", 1, reporter=A, winner=A, amount=0, town="Castle")], "heroes are banned and drawn before the bid"),
    ],
)
def test_a_record_that_does_not_fit_is_reported(templates, heroes, towns, records, message):
    with pytest.raises(TradeError, match=message):
        replay(records, templates, towns, heroes)


def test_hero_records_in_a_trade_that_is_not_a_roulette_are_reported(templates, heroes, towns):
    standard = check_trade("standard")
    records = [START, make_record(4, "hero_bans", 1, player=A, heroes=())]
    with pytest.raises(TradeError, match="cannot be banned now"):
        replay(records, templates, towns, heroes, kind=standard)


def test_a_thread_without_a_hero_catalogue_reports_a_hero_record(templates, towns):
    with pytest.raises(TradeError, match="cannot be banned"):
        replay([START, make_record(4, "hero_bans", 1, player=A, heroes=("C1",))], templates, towns, None)


# --- the mirror roulette: one bid, for who chooses first -------------------------------------------------------------------


def mirror_roulette(templates, heroes, kind=ONE_BAN, rules=NO_ROLLS):
    """A mirror roulette whose bans are made and whose heroes are drawn: only the bid is left."""
    trade = new_trade(1, GAMES, Draw(("castle",)), PLAYERS, templates, rules, kind, True)
    if kind.hero_bans:
        trade = ban(ban(trade, heroes, templates, A), heroes, templates, B)
    return drawn(trade, heroes, templates)


def test_a_mirror_roulette_has_one_bid_after_the_heroes(templates, heroes):
    trade = new_trade(1, GAMES, Draw(("castle",)), PLAYERS, templates, NO_ROLLS, ONE_BAN, True)
    assert trade.bids == ("first_choice_bid",) and trade.section == "hero_bans"
    assert mirror_roulette(templates, heroes).section == "first_choice_bid"


def test_the_winner_reports_the_amount_and_what_they_choose_first(templates, towns, heroes):
    trade = mirror_roulette(templates, heroes)
    report = make_report(trade, towns, ALLOWED, B, A, 800, "Hero")
    assert (report.section, report.winner, report.amount, report.choice) == ("first_choice_bid", A, 800, "hero")
    after = trade.with_report(report)
    assert after.finished and after.gold == {A: 9200, B: 10800}


@pytest.mark.parametrize("choice", ["red", "Castle", "pack1", ""])
def test_a_choice_that_is_not_hero_or_color_is_refused(templates, towns, heroes, choice):
    with pytest.raises(TradeError, match="Choose hero or color"):
        make_report(mirror_roulette(templates, heroes), towns, ALLOWED, A, A, 0, choice)


def test_the_bid_cannot_be_more_than_the_winner_has(templates, towns, heroes):
    with pytest.raises(Exception, match="more than"):
        make_report(mirror_roulette(templates, heroes), towns, ALLOWED, A, A, 10100, "hero")


def test_the_bid_waits_for_the_heroes(templates, towns):
    trade = new_trade(1, GAMES, Draw(("castle",)), PLAYERS, templates, NO_ROLLS, ONE_BAN, True)
    with pytest.raises(TradeError, match="heroes are banned and drawn before the bid"):
        make_report(trade, towns, ALLOWED, A, A, 0, "hero")


def test_the_prompt_says_who_bids_first_and_what_the_winner_chooses(templates, towns, heroes):
    assert prompt(mirror_roulette(templates, heroes), MENTIONS, towns).splitlines() == [
        "Next step: bid for the first choice",
        "<@111> bids first, raising by at least 100",
        "Its winner chooses first either the hero or the color, and the other player chooses the other",
        "Report the result with /trade report, choosing hero or color",
    ]


@pytest.mark.parametrize(
    "choice, lines",
    [
        ("hero", ["<@111> won at `800` gold and chooses the `hero` first", "<@222> then chooses the color and plays the other hero"]),
        ("color", ["<@111> won at `800` gold and chooses the `color` first", "<@222> then chooses a hero and plays the other color"]),
    ],
)
def test_the_result_says_who_chooses_what(templates, towns, heroes, choice, lines):
    trade = mirror_roulette(templates, heroes)
    after = trade.with_report(make_report(trade, towns, ALLOWED, B, A, 800, choice))
    text = report_line(after, after.reports[0], MENTIONS, towns)
    assert text.splitlines() == [
        "Game 1 - Bid for the first choice, reported by <@222>",
        *lines,
        "Gold difference: <@111> -800, <@222> +800",
    ]
    assert parse(f"[#9 fb g1] {text}") == make_record(9, "first_choice_bid", 1, reporter=B, winner=A, amount=800, first=choice)


def test_the_lobby_settings_give_the_town_the_heroes_and_who_chooses_what_without_colors(templates, towns, heroes):
    trade = mirror_roulette(templates, heroes)
    after = trade.with_report(make_report(trade, towns, ALLOWED, A, A, 800, "hero"))
    first, second = (heroes.find(hero).name for hero in after.drawn_heroes)
    assert summary(after, MENTIONS, towns, templates, heroes=heroes).splitlines() == [
        "Game 1 lobby settings - Jebus Cross",
        "Town (both players): Castle",
        f"Heroes: {first} and {second}",
        "<@111>: chooses the hero first (one of the two), gets the other color, gold -800",
        "<@222>: chooses the color, plays the other hero, gold +800",
    ]


def test_choosing_the_color_first_is_worded_the_other_way_round(templates, towns, heroes):
    trade = mirror_roulette(templates, heroes)
    after = trade.with_report(make_report(trade, towns, ALLOWED, A, B, 300, "color"))
    lines = summary(after, MENTIONS, towns, templates, heroes=heroes).splitlines()
    assert lines[-2:] == [
        "<@111>: chooses the hero first (one of the two), plays the other color, gold +300",
        "<@222>: chooses the color, plays the other hero, gold -300",
    ]


def test_the_status_names_the_bid(templates, heroes, towns):
    assert next_words(mirror_roulette(templates, heroes), towns) == ", next: bid for the first choice"


def test_the_records_of_a_mirror_roulette_are_replayed(templates, heroes, towns):
    records = [
        make_record(3, "trade_started", 1, towns=("Castle",)),
        make_record(4, "hero_bans", 1, player=A, heroes=("C1",)),
        make_record(5, "hero_bans", 1, player=B, heroes=()),
        make_record(6, "heroes_drawn", 1, heroes=("C2", "C3")),
        make_record(7, "first_choice_bid", 1, reporter=A, winner=B, amount=500, first="color"),
    ]
    mirror_templates = parse_templates(
        [
            {"id": "JC", "name": "Jebus Cross", "difficulty": 160, "mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}},
            {"id": "Diamond", "name": "Diamond", "difficulty": 160},
            {"id": "h3dm1", "name": "h3dm1", "difficulty": 160},
        ],
        "templates.json",
    )
    trade = replay(records, mirror_templates, towns, heroes).trades[1]
    assert trade.finished and trade.mirror and trade.drawn_heroes == ("c2", "c3")


def test_a_choice_that_is_not_hero_or_color_in_a_record_is_reported(templates, heroes, towns):
    records = [
        make_record(3, "trade_started", 1, towns=("Castle",)),
        make_record(4, "hero_bans", 1, player=A, heroes=()),
        make_record(5, "hero_bans", 1, player=B, heroes=()),
        make_record(6, "heroes_drawn", 1, heroes=("C2", "C3")),
        make_record(7, "first_choice_bid", 1, reporter=A, winner=B, amount=500, first="red"),
    ]
    mirror_templates = parse_templates(
        [
            {"id": "JC", "name": "Jebus Cross", "difficulty": 160, "mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}},
            {"id": "Diamond", "name": "Diamond", "difficulty": 160},
            {"id": "h3dm1", "name": "h3dm1", "difficulty": 160},
        ],
        "templates.json",
    )
    with pytest.raises(TradeError, match="first choice is the hero or the color"):
        replay(records, mirror_templates, towns, heroes)
