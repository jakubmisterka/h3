"""A roulette trade played through the commands on a fake thread: the hero bans in turn, the draw the bot makes by
itself, the bid that waits for the heroes, the suggestions, the lobby settings and the undo."""

import asyncio
import random

import pytest

import discord_commands.match as match
import discord_commands.trade as trade_commands
from rules.catalogue import parse_heroes, parse_templates
from rules.formats import parse_format
from rules.registry import Registry
from rules.trade_draw import Draw
from state import parse
from test_selection_command import ANNA, BORIS, BOT, interaction, make_thread, texts, told
from test_trade_command import run


def hero(hero_id, town, **flags):
    return {"id": hero_id, "name": hero_id.capitalize(), "town": town, "link": f"https://example.com/{hero_id}", **flags}


def build_registry(good_format, towns, trade, rolls=0, mirror=False):
    heroes = parse_heroes(
        [hero(f"c{n}", "castle") for n in range(1, 7)] + [hero(f"t{n}", "tower") for n in range(1, 7)] + [hero("cdef", "castle", banned_by_default=True)],
        "heroes.json",
        towns,
    )
    templates = parse_templates(
        [
            {
                "id": "JC",
                "name": "Jebus Cross",
                "difficulty": 160,
                "trade": trade,
                **({"mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}} if mirror else {}),
            },
            {"id": "6lm10a", "name": "6lm10a", "difficulty": 160},
            {"id": "h3dm1", "name": "h3dm1", "difficulty": 160},
        ],
        "templates.json",
        heroes,
    )
    data = dict(
        good_format,
        id="roulette-cup",
        name="Roulette Cup",
        templates=["JC", "6lm10a", "h3dm1"],
        allowed_towns=["castle", "tower"],
        roll_rules={"rolls_per_player": rolls},
    )
    return Registry(towns, templates, {"roulette-cup": parse_format(data, templates, towns, heroes)}, heroes)


@pytest.fixture(autouse=True)
def fixed(monkeypatch):
    """Anna wins the coinflip and is A; the towns are Castle and Tower; the heroes are drawn from a seeded source."""
    monkeypatch.setattr(match, "coinflip", lambda a, b: a)
    monkeypatch.setattr(
        trade_commands,
        "draw_start",
        lambda kind, mirror, allowed, source=None, banned=(), **_: Draw(("castle",) if mirror else ("castle", "tower")),
    )
    monkeypatch.setattr(trade_commands, "random_source", random.Random(4))


@pytest.fixture
def registry(good_format, towns):
    return build_registry(good_format, towns, {"kind": "roulette", "hero_bans": 1})


def started(registry):
    thread = make_thread(980)
    fmt = registry.formats["roulette-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], "JC", ANNA, BORIS))
    return thread


def ban(registry, thread, user, *names):
    return run(trade_commands.ban_heroes, registry, thread, user, *names)


def records_of(thread):
    return [r for r in map(parse, texts(thread)) if r is not None]


def types(thread):
    return [r.type for r in records_of(thread)]


# --- the bans and the draw ------------------------------------------------------------------------------------------------


def test_the_first_player_is_asked_to_ban_when_the_trade_opens(registry):
    thread = started(registry)
    assert texts(thread)[-1].splitlines() == [
        "Next step: hero bans",
        "<@1> may ban up to 1 hero of Castle vs Tower",
        "Ban with /trade ban-heroes; ban nobody by sending it without a hero",
    ]


def test_a_ban_is_recorded_and_the_other_player_is_asked(registry):
    thread = started(registry)
    it = ban(registry, thread, ANNA, "C1")
    assert told(it) == "Banned."
    assert texts(thread)[-2] == "[#4 hb g1] Game 1 - <@1> bans `C1`."
    assert records_of(thread)[-1].data == {"player": 1, "heroes": ("C1",)}
    assert "<@2> may ban up to 1 hero" in texts(thread)[-1]


def test_after_the_second_ban_the_bot_draws_the_heroes_and_the_town_bid_follows(registry):
    thread = started(registry)
    ban(registry, thread, ANNA, "C1")
    it = ban(registry, thread, BORIS)  # Boris bans nobody
    assert told(it) == "You ban nobody."
    assert types(thread)[-2:] == ["hero_bans", "heroes_drawn"]
    drawn = texts(thread)[-2].splitlines()
    assert drawn[0].endswith("The heroes are drawn:") and drawn[1].startswith("`C") and "(Castle) <https://example.com/c" in drawn[1]
    assert drawn[2].startswith("`T") and "(Tower) <https://example.com/t" in drawn[2]
    assert "`C1`" not in texts(thread)[-2]
    assert texts(thread)[-1].startswith("Next step: town bid: Castle vs Tower\n")


def test_the_heroes_are_never_the_banned_ones_or_the_ones_banned_by_default(registry):
    for seed in range(25):
        trade_commands.random_source = random.Random(seed)
        thread = started(registry)
        ban(registry, thread, ANNA, "C1")
        ban(registry, thread, BORIS, "T1")
        heroes = next(r for r in records_of(thread) if r.type == "heroes_drawn").data["heroes"]
        assert "C1" not in heroes and "T1" not in heroes and "Cdef" not in heroes


def test_a_trade_without_hero_bans_draws_at_once(good_format, towns):
    registry = build_registry(good_format, towns, "roulette")
    thread = started(registry)
    assert "heroes_drawn" in types(thread) and "hero_bans" not in types(thread)
    assert texts(thread)[-1].startswith("Next step: town bid: Castle vs Tower")


def test_the_roll_section_comes_before_the_bans(good_format, towns):
    registry = build_registry(good_format, towns, {"kind": "roulette", "hero_bans": 1}, rolls=1)
    thread = started(registry)
    assert texts(thread)[-1].startswith("Next step: town roll")
    run(trade_commands.skip_roll, registry, thread, ANNA)
    run(trade_commands.skip_roll, registry, thread, BORIS)
    assert "<@1> may ban up to 1 hero" in texts(thread)[-1]


# --- refusals -------------------------------------------------------------------------------------------------------------


def test_the_second_player_cannot_ban_first(registry):
    thread = started(registry)
    before = len(texts(thread))
    it = ban(registry, thread, BORIS, "T1")
    assert "other player's turn" in told(it) and len(texts(thread)) == before


def test_a_name_that_is_no_hero_is_refused_in_words(registry):
    thread = started(registry)
    assert "is not a hero" in told(ban(registry, thread, ANNA, "Atlantis"))


def test_too_many_heroes_are_refused_and_the_limit_is_said(registry):
    thread = started(registry)
    assert "At most 1 hero may be banned" in told(ban(registry, thread, ANNA, "C1", "C2"))


def test_a_hero_banned_by_default_cannot_be_banned(registry):
    thread = started(registry)
    assert "Cdef cannot be banned" in told(ban(registry, thread, ANNA, "Cdef"))


def test_the_bid_is_refused_until_the_heroes_are_drawn(registry):
    thread = started(registry)
    it = run(trade_commands.report, registry, thread, ANNA, ANNA, 0, "Castle")
    assert "heroes are banned and drawn before the bid" in told(it)


def test_a_player_cannot_ban_after_the_heroes_are_drawn(registry):
    thread = started(registry)
    ban(registry, thread, ANNA)
    ban(registry, thread, BORIS)
    assert "cannot be banned now" in told(ban(registry, thread, ANNA, "C2"))


# --- the suggestions ------------------------------------------------------------------------------------------------------


def suggestions(registry, thread, current=""):
    it = interaction(registry, thread, ANNA)
    return [(c.name, c.value) for c in asyncio.run(trade_commands._hero_options(it, current))]


def test_the_heroes_that_can_be_banned_are_offered(registry):
    thread = started(registry)
    offered = suggestions(registry, thread)
    assert ("C1 (Castle)", "C1") in offered and ("T6 (Tower)", "T6") in offered
    assert not any(value == "Cdef" for _, value in offered) and len(offered) == 12


def test_what_is_typed_narrows_the_suggestions(registry):
    thread = started(registry)
    assert suggestions(registry, thread, "t3") == [("T3 (Tower)", "T3")]


def test_a_hero_already_banned_is_not_offered_again(registry):
    thread = started(registry)
    ban(registry, thread, ANNA, "C1")
    assert ("C1 (Castle)", "C1") not in suggestions(registry, thread)


def test_nothing_is_offered_when_nobody_is_banning(registry):
    thread = started(registry)
    ban(registry, thread, ANNA)
    ban(registry, thread, BORIS)
    assert suggestions(registry, thread) == []


def test_no_town_is_suggested_for_a_report_while_the_heroes_are_pending(registry):
    thread = started(registry)
    it = interaction(registry, thread, ANNA)
    assert asyncio.run(trade_commands._choice_options(it, "")) == []


# --- the whole trade and the status -----------------------------------------------------------------------------------------


def test_the_lobby_settings_give_each_player_the_hero_of_their_town(registry):
    thread = started(registry)
    ban(registry, thread, ANNA)
    ban(registry, thread, BORIS)
    drawn = next(r for r in records_of(thread) if r.type == "heroes_drawn").data["heroes"]
    run(trade_commands.report, registry, thread, ANNA, ANNA, 2100, "Castle")
    run(trade_commands.report, registry, thread, BORIS, BORIS, 3000, "red")
    summary = texts(thread)[-2].splitlines()
    assert summary[0] == "Game 1 lobby settings - Jebus Cross"
    assert summary[1] == f"<@2>: Tower ({drawn[1]}), red, gold -900"
    assert summary[2] == f"<@1>: Castle ({drawn[0]}), blue, gold +900"


def test_the_status_names_the_hero_step(registry):
    thread = started(registry)
    assert "next: hero bans" in told(run(match.status, registry, thread, ANNA))
    ban(registry, thread, ANNA)
    ban(registry, thread, BORIS)
    assert "next: town bid" in told(run(match.status, registry, thread, ANNA))


# --- undo ------------------------------------------------------------------------------------------------------------------


def test_an_undo_cannot_start_at_the_draw(registry):
    thread = started(registry)
    ban(registry, thread, ANNA)
    ban(registry, thread, BORIS)
    draw = next(r for r in records_of(thread) if r.type == "heroes_drawn")
    last_ban = max(r.n for r in records_of(thread) if r.type == "hero_bans")
    message = told(run(match.undo, registry, thread, ANNA, draw.n))
    assert "cannot start at the draw" in message and f"Undo from record {last_ban}" in message


def test_undoing_the_last_ban_undoes_the_draw_too_and_asks_for_the_ban_again(registry):
    thread = started(registry)
    ban(registry, thread, ANNA)
    ban(registry, thread, BORIS)
    last_ban = max(r.n for r in records_of(thread) if r.type == "hero_bans")
    run(match.undo, registry, thread, ANNA, last_ban)
    run(match.undo, registry, thread, BORIS, last_ban)
    assert "<@2> may ban up to 1 hero" in texts(thread)[-1]
    ban(registry, thread, BORIS)  # the ban is made again, and the heroes are drawn again
    assert types(thread)[-2:] == ["hero_bans", "heroes_drawn"]
    assert texts(thread)[-1].startswith("Next step: town bid")


def test_a_ban_can_be_undone_before_the_draw(registry):
    thread = started(registry)
    ban(registry, thread, ANNA, "C1")
    first = next(r for r in records_of(thread) if r.type == "hero_bans")
    run(match.undo, registry, thread, ANNA, first.n)
    run(match.undo, registry, thread, BORIS, first.n)
    assert "<@1> may ban up to 1 hero" in texts(thread)[-1]
    assert ("C1 (Castle)", "C1") in suggestions(registry, thread)


# --- the mirror roulette ---------------------------------------------------------------------------------------------------


@pytest.fixture
def mirror_registry(good_format, towns):
    return build_registry(good_format, towns, {"kind": "roulette", "hero_bans": 1}, mirror=True)


def to_the_bid(registry):
    thread = started(registry)
    ban(registry, thread, ANNA, "C1")
    ban(registry, thread, BORIS)
    return thread


def test_a_mirror_roulette_asks_for_the_bans_of_the_one_town_then_draws_two_heroes_of_it(mirror_registry):
    thread = started(mirror_registry)
    assert "<@1> may ban up to 1 hero of Castle" in texts(thread)[-1]
    ban(mirror_registry, thread, ANNA, "C1")
    ban(mirror_registry, thread, BORIS)
    drawn = next(t for t in texts(thread) if " hd g1]" in t[:10]).splitlines()
    assert len(drawn) == 3 and all("(" not in line.split("<")[0] for line in drawn[1:])  # no town: both are of Castle
    heroes = next(r for r in records_of(thread) if r.type == "heroes_drawn").data["heroes"]
    assert len(set(heroes)) == 2 and "C1" not in heroes


def test_the_one_bid_is_for_who_chooses_first(mirror_registry):
    thread = to_the_bid(mirror_registry)
    assert texts(thread)[-1].splitlines() == [
        "Next step: bid for the first choice",
        "<@1> bids first, raising by at least 100",
        "Its winner chooses first either the hero or the color, and the other player chooses the other",
        "Report the result with /trade report, choosing hero or color",
    ]


def test_the_report_names_the_amount_and_the_first_choice(mirror_registry):
    thread = to_the_bid(mirror_registry)
    it = run(trade_commands.report, mirror_registry, thread, BORIS, ANNA, 800, "hero")
    assert told(it) == "Reported."
    bid = next(t for t in texts(thread) if " fb g1]" in t[:10])
    assert bid.splitlines()[:3] == [
        "[#7 fb g1] Game 1 - Bid for the first choice, reported by <@2>",
        "<@1> won at `800` gold and chooses the `hero` first",
        "<@2> then chooses the color and plays the other hero",
    ]
    assert next(r for r in records_of(thread) if r.type == "first_choice_bid").data == {"reporter": 2, "winner": 1, "amount": 800, "first": "hero"}


def test_the_lobby_settings_say_who_chooses_what_and_have_no_colors(mirror_registry):
    thread = to_the_bid(mirror_registry)
    heroes = next(r for r in records_of(thread) if r.type == "heroes_drawn").data["heroes"]
    run(trade_commands.report, mirror_registry, thread, ANNA, BORIS, 300, "color")
    assert texts(thread)[-2].splitlines()[-4:] == [
        "Town (both players): Castle",
        f"Heroes: {heroes[0]} and {heroes[1]}",
        "<@1>: chooses the hero first (one of the two), plays the other color, gold +300",
        "<@2>: chooses the color, plays the other hero, gold -300",
    ]


@pytest.mark.parametrize("choice", ["red", "Castle", "blue"])
def test_a_choice_that_is_not_hero_or_color_is_refused(mirror_registry, choice):
    thread = to_the_bid(mirror_registry)
    assert "Choose hero or color" in told(run(trade_commands.report, mirror_registry, thread, ANNA, ANNA, 0, choice))


def test_the_suggestions_for_the_bid_are_hero_and_color(mirror_registry):
    thread = to_the_bid(mirror_registry)
    it = interaction(mirror_registry, thread, ANNA)
    assert [(c.name, c.value) for c in asyncio.run(trade_commands._choice_options(it, ""))] == [("hero", "hero"), ("color", "color")]


def test_the_status_names_the_bid(mirror_registry):
    thread = to_the_bid(mirror_registry)
    assert "next: bid for the first choice" in told(run(match.status, mirror_registry, thread, ANNA))


def test_the_bid_can_be_undone_and_made_again(mirror_registry):
    thread = to_the_bid(mirror_registry)
    run(trade_commands.report, mirror_registry, thread, ANNA, ANNA, 800, "hero")
    bid = next(r for r in records_of(thread) if r.type == "first_choice_bid")
    run(match.undo, mirror_registry, thread, ANNA, bid.n)
    run(match.undo, mirror_registry, thread, BORIS, bid.n)
    assert texts(thread)[-1].startswith("Next step: bid for the first choice")
    run(trade_commands.report, mirror_registry, thread, ANNA, BORIS, 0, "color")
    assert "Town (both players): Castle" in texts(thread)[-2]


def test_a_mirror_roulette_rolls_ban_the_town_before_the_heroes(good_format, towns):
    registry = build_registry(good_format, towns, {"kind": "roulette", "hero_bans": 1}, rolls=1, mirror=True)
    thread = started(registry)
    run(trade_commands.roll, registry, thread, ANNA)
    run(trade_commands.skip_roll, registry, thread, BORIS)
    assert "<@1> may ban up to 1 hero of" in texts(thread)[-1]
