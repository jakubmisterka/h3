"""A roulette whose heroes are drawn together with the towns (`roll_before_heroes` false): the start and every roll
draw the towns and the heroes, so players see the heroes before deciding to roll, and a roll redraws both."""

import asyncio
import random

import pytest

import discord_commands.match as match
import discord_commands.trade as trade_commands
from rules.catalogue import parse_heroes, parse_templates
from rules.roll_rules import RollRules
from rules.trade import (
    Roll,
    TradeError,
    check_roll,
    new_trade,
    opening_line,
    replay_trades,
    roll_data,
    roll_line,
    start_data,
)
from rules.trade_draw import Draw, HeroDrawError, check_draw, check_start, draw_shape, draw_start
from rules.trade_kinds import check_trade
from state import make_record, parse
from test_selection_command import ANNA, BORIS, BOT, interaction, make_thread, texts, told
from test_trade_command import run
from test_trade_roulette_command import build_registry, hero

TOGETHER = check_trade({"kind": "roulette", "roll_before_heroes": False})
ALLOWED = ("castle", "tower")
A, B = 111, 222
MENTIONS = {A: "<@111>", B: "<@222>"}
GAMES = ("JC", "Diamond", "h3dm1")


@pytest.fixture(scope="module")
def heroes(towns):
    data = [hero(f"c{n}", "castle") for n in range(1, 5)] + [hero(f"t{n}", "tower") for n in range(1, 5)]
    data += [hero("cdef", "castle", banned_by_default=True), hero("cban", "castle")]
    return parse_heroes(data, "heroes.json", towns)


@pytest.fixture(scope="module")
def catalogue(heroes):
    return parse_templates(
        [
            {"id": "JC", "name": "Jebus Cross", "difficulty": 160, "banned_heroes": ["cban"]},
            {"id": "Diamond", "name": "Diamond", "difficulty": 160},
            {"id": "h3dm1", "name": "h3dm1", "difficulty": 160},
        ],
        "templates.json",
        heroes,
    )


# --- the draw ---------------------------------------------------------------------------------------------------------------


def test_this_kind_draws_two_heroes_with_the_towns_and_the_other_draws_none():
    assert draw_shape(TOGETHER, False).heroes == 2 and draw_shape(TOGETHER, True).heroes == 2
    assert draw_shape(check_trade("roulette"), False).heroes == 0  # drawn after the rolls instead
    assert draw_shape(check_trade("standard"), False).heroes == 0


def test_a_pair_gets_a_hero_of_each_town_and_a_mirror_two_of_its_town(catalogue, heroes):
    for seed in range(60):
        pair = draw_start(TOGETHER, False, ALLOWED, random.Random(seed), heroes=heroes, template=catalogue.find("JC"))
        for town, hero_id in zip(pair.towns, pair.heroes):
            assert heroes.find(hero_id).details["town"] == town
        mirror = draw_start(TOGETHER, True, ALLOWED, random.Random(seed), heroes=heroes, template=catalogue.find("JC"))
        assert len(set(mirror.heroes)) == 2 and {heroes.find(h).details["town"] for h in mirror.heroes} == set(mirror.towns)


def test_a_hero_the_map_does_not_offer_is_never_drawn(catalogue, heroes):
    seen = set()
    for seed in range(300):
        seen |= set(draw_start(TOGETHER, False, ALLOWED, random.Random(seed), heroes=heroes, template=catalogue.find("JC")).heroes)
    assert not seen & {"cdef", "cban"} and {"c1", "t1"} <= seen


def test_the_draw_needs_the_hero_catalogue_and_the_template(catalogue):
    with pytest.raises(HeroDrawError, match="without the hero catalogue"):
        draw_start(TOGETHER, False, ALLOWED, random.Random(1))


def test_too_few_heroes_refuse_the_draw(catalogue, towns):
    few = parse_heroes([hero("c1", "castle"), hero("t1", "tower")], "heroes.json", towns)
    draw_start(TOGETHER, False, ALLOWED, random.Random(1), heroes=few, template=catalogue.find("Diamond"))
    with pytest.raises(HeroDrawError, match="Fewer than two heroes"):
        draw_start(TOGETHER, True, ALLOWED, random.Random(1), heroes=few, template=catalogue.find("Diamond"))


def test_a_draw_with_the_wrong_heroes_is_refused_by_the_checks(catalogue, heroes):
    template = catalogue.find("JC")
    check_draw(Draw(("castle", "tower"), (), ("c1", "t1")), TOGETHER, False, ALLOWED, (), heroes, template)
    for wrong in (("t1", "c1"), ("c1",), ("c1", "t1", "t2"), ("cdef", "t1"), ("cban", "t1"), ("c1", "c1")):
        with pytest.raises(TradeError):
            check_draw(Draw(("castle", "tower"), (), wrong), TOGETHER, False, ALLOWED, (), heroes, template)


def test_a_start_with_the_wrong_number_of_heroes_is_reported(catalogue, heroes):
    with pytest.raises(TradeError, match="starts with 2 heroes, not 0"):
        check_start(Draw(("castle", "tower")), TOGETHER, False, ALLOWED, heroes, catalogue.find("JC"))
    with pytest.raises(TradeError, match="starts with 0 heroes, not 2"):
        check_start(Draw(("castle", "tower"), (), ("c1", "t1")), check_trade("standard"), False, ALLOWED)


# --- the wording and the records --------------------------------------------------------------------------------------------


def trade_of(templates, draw):
    return new_trade(1, GAMES, draw, (A, B), templates, kind=TOGETHER)


def test_the_opening_says_the_heroes_with_their_towns_and_links(templates, towns, heroes):
    trade = trade_of(templates, Draw(("castle", "tower"), (), ("c2", "t3")))
    assert opening_line(trade, False, MENTIONS, towns, templates, heroes).splitlines() == [
        "Game 1 (Jebus Cross)",
        "Pair: `Castle` vs `Tower`",
        "Hero1: `C2` (Castle) <https://example.com/c2>",
        "Hero2: `T3` (Tower) <https://example.com/t3>",
        "Starting gold: 10 000",
    ]


def test_a_mirror_lists_its_heroes_without_the_town(templates, towns, heroes):
    trade = new_trade(1, GAMES, Draw(("castle",), (), ("c2", "c3")), (A, B), templates, kind=TOGETHER, mirror=True)
    assert opening_line(trade, False, MENTIONS, towns, templates, heroes).splitlines()[1:4] == [
        "Town: `Castle`",
        "Hero1: `C2` <https://example.com/c2>",
        "Hero2: `C3` <https://example.com/c3>",
    ]


def test_the_opening_reads_back_as_the_record_it_came_from(templates, towns, heroes):
    trade = trade_of(templates, Draw(("castle", "tower"), (), ("c2", "t3")))
    text = opening_line(trade, False, MENTIONS, towns, templates, heroes)
    record = parse(f"[#3 tr g1] {text}")
    assert record == make_record(3, "trade_started", 1, towns=("Castle", "Tower"), heroes=("C2", "T3"))
    assert start_data(trade, towns, heroes) == record.data


def test_a_roll_says_the_new_towns_and_the_new_heroes_and_reads_back(templates, towns, heroes):
    trade = trade_of(templates, Draw(("castle", "tower"), (), ("c2", "t3")))
    roll = Roll(A, ("castle",), Draw(("tower", "cove"), (), ("t1", "v1")))
    heroes_with_cove = parse_heroes(
        [hero(f"c{n}", "castle") for n in range(1, 5)] + [hero(f"t{n}", "tower") for n in range(1, 5)] + [hero("v1", "cove")],
        "heroes.json",
        towns,
    )
    rolled = trade.with_roll(roll)
    text = roll_line(rolled, roll, MENTIONS, towns, heroes_with_cove)
    assert text.splitlines()[1:4] == [
        "New pair: `Tower` vs `Cove`",
        "Hero1: `T1` (Tower) <https://example.com/t1>",
        "Hero2: `V1` (Cove) <https://example.com/v1>",
    ]
    record = parse(f"[#4 rl g1] {text}")
    assert record == make_record(4, "roll", 1, player=A, bans=("Castle",), towns=("Tower", "Cove"), heroes=("T1", "V1"))
    assert roll_data(roll, towns, heroes_with_cove) == record.data


def test_the_replay_reads_the_heroes_of_the_start_and_of_a_roll(catalogue, towns, heroes):
    records = (
        make_record(3, "trade_started", 1, towns=("Castle", "Tower"), heroes=("C2", "T3")),
        make_record(4, "roll", 1, player=A, bans=(), towns=("Tower", "Castle"), heroes=("T1", "C3")),
    )
    rolls = lambda t: RollRules(500, 1, 2)  # noqa: E731
    trade = replay_trades(records, GAMES, (A, B), catalogue, ALLOWED, rolls, lambda t: TOGETHER, towns, heroes).trades[1]
    assert trade.heroes == ("t1", "c3") and trade.draw.heroes == ("t1", "c3") and trade.section == "town_roll"


def test_a_roll_with_a_hero_of_the_wrong_town_is_reported(catalogue, towns, heroes):
    records = (
        make_record(3, "trade_started", 1, towns=("Castle", "Tower"), heroes=("C2", "T3")),
        make_record(4, "roll", 1, player=A, bans=(), towns=("Tower", "Castle"), heroes=("C1", "T1")),  # the heroes stay in place
    )
    rolls = lambda t: RollRules(500, 1, 2)  # noqa: E731
    with pytest.raises(TradeError, match="cannot be the hero of tower"):
        replay_trades(records, GAMES, (A, B), catalogue, ALLOWED, rolls, lambda t: TOGETHER, towns, heroes)


# --- played through the commands ----------------------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fixed(monkeypatch):
    monkeypatch.setattr(match, "coinflip", lambda a, b: a)
    monkeypatch.setattr(trade_commands, "random_source", random.Random(6))


def together(good_format, towns, rolls=0, mirror=False):
    return build_registry(good_format, towns, {"kind": "roulette", "roll_before_heroes": False}, rolls=rolls, mirror=mirror)


def started(registry):
    thread = make_thread(990)
    fmt = registry.formats["roulette-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], "JC", ANNA, BORIS))
    return thread


def records_of(thread):
    return [r for r in map(parse, texts(thread)) if r is not None]


def test_the_heroes_come_with_the_towns_and_there_is_no_ban_step(good_format, towns):
    registry = together(good_format, towns)
    thread = started(registry)
    opening = next(t for t in texts(thread) if " tr g1]" in t[:10]).splitlines()
    assert [line.split(":")[0] for line in opening[1:4]] == ["Pair", "Hero1", "Hero2"]
    assert texts(thread)[-1].startswith("Next step: town bid")
    assert not any(r.type in ("hero_bans", "heroes_drawn") for r in records_of(thread))


def test_each_hero_belongs_to_the_town_next_to_it(good_format, towns):
    registry = together(good_format, towns)
    thread = started(registry)
    record = next(r for r in records_of(thread) if r.type == "trade_started")
    for town, hero_name in zip(record.data["towns"], record.data["heroes"]):
        assert registry.heroes.find(hero_name).details["town"] == registry.towns.find(town).id


def test_a_roll_redraws_the_towns_and_the_heroes_together(good_format, towns):
    registry = together(good_format, towns, rolls=1)
    thread = started(registry)
    assert texts(thread)[-1].startswith("Next step: town roll")  # the draw is not said again
    run(trade_commands.roll, registry, thread, ANNA)
    roll = next(r for r in records_of(thread) if r.type == "roll")
    assert len(roll.data["heroes"]) == 2 and set(roll.data["towns"]) == {"Castle", "Tower"}
    for town, hero_name in zip(roll.data["towns"], roll.data["heroes"]):
        assert registry.heroes.find(hero_name).details["town"] == registry.towns.find(town).id
    assert "\nHero1: " in texts(thread)[-2] and "\nHero2: " in texts(thread)[-2]


def test_after_an_undo_of_a_roll_the_prompt_shows_the_heroes_that_stand(good_format, towns):
    registry = together(good_format, towns, rolls=1)
    thread = started(registry)
    run(trade_commands.roll, registry, thread, ANNA)
    roll = next(r for r in records_of(thread) if r.type == "roll")
    run(match.undo, registry, thread, ANNA, roll.n)
    run(match.undo, registry, thread, BORIS, roll.n)
    prompt = texts(thread)[-1].splitlines()
    assert prompt[0] == "Next step: town roll" and prompt[1].startswith("Pair: ")
    assert prompt[2].startswith("Hero1: ") and prompt[3].startswith("Hero2: ") and prompt[4] == "Cost: 500 gold"


def test_the_town_bid_and_the_lobby_settings_show_the_heroes(good_format, towns):
    registry = together(good_format, towns)
    thread = started(registry)
    record = next(r for r in records_of(thread) if r.type == "trade_started")
    first_town = record.data["towns"][0]
    run(trade_commands.report, registry, thread, ANNA, ANNA, 2100, first_town)
    run(trade_commands.report, registry, thread, BORIS, BORIS, 3000, "red")
    summary = texts(thread)[-2].splitlines()
    assert summary[2] == f"<@1>: {first_town} ({record.data['heroes'][0]}), blue, gold +900"


def test_a_mirror_draws_two_heroes_of_its_town_with_it_and_has_the_one_bid(good_format, towns):
    registry = together(good_format, towns, mirror=True)
    thread = started(registry)
    record = next(r for r in records_of(thread) if r.type == "trade_started")
    assert len(record.data["towns"]) == 1 and len(set(record.data["heroes"])) == 2
    assert texts(thread)[-1].startswith("Next step: bid for the first choice")
    run(trade_commands.report, registry, thread, ANNA, BORIS, 300, "hero")
    heroes_line = next(line for line in texts(thread)[-2].splitlines() if line.startswith("Heroes: "))
    assert set(heroes_line.removeprefix("Heroes: ").split(" and ")) == set(record.data["heroes"])


def test_a_mirror_roll_bans_the_town_and_draws_new_heroes(good_format, towns):
    registry = together(good_format, towns, rolls=1, mirror=True)
    thread = started(registry)
    first = next(r for r in records_of(thread) if r.type == "trade_started")
    run(trade_commands.roll, registry, thread, ANNA)
    roll = next(r for r in records_of(thread) if r.type == "roll")
    assert roll.data["bans"] == first.data["towns"] and roll.data["towns"] != first.data["towns"]
    assert len(roll.data["heroes"]) == 2


def test_the_bid_is_not_held_back_by_a_ban_step(good_format, towns):
    registry = together(good_format, towns, rolls=1)
    thread = started(registry)
    record = next(r for r in records_of(thread) if r.type == "trade_started")
    it = run(trade_commands.report, registry, thread, ANNA, ANNA, 0, record.data["towns"][0])
    assert told(it) == "Reported."  # reporting the bid skips the rolls still open, as in a standard trade
