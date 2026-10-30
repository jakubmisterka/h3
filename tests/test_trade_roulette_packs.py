"""A roulette with computer-player packs played through the commands on a fake thread: the pair and the packs, the hero
bans, the heroes of the pair, the three bids (town, pack, color) and the lobby settings."""

import asyncio
import random

import pytest

import discord_commands.match as match
import discord_commands.trade as trade_commands
from rules.catalogue import parse_heroes, parse_templates
from rules.formats import parse_format
from rules.registry import Registry
from rules.trade_draw import Draw
from rules.trade_kinds import check_trade, sections
from state import parse
from test_selection_command import ANNA, BORIS, BOT, make_thread, texts, told
from test_trade_command import run

PACKS = ("rampart", "inferno", "dungeon", "stronghold", "fortress", "cove")
KIND = {"kind": "roulette_with_ai_packs", "hero_bans": 1}


def build_registry(good_format, towns, trade=KIND, mirror=False, allowed=None):
    heroes = parse_heroes(
        [
            {"id": f"{town}{n}", "name": f"{town.capitalize()}{n}", "town": town, "link": f"https://example.com/{town}{n}"}
            for town in towns.ids
            for n in range(1, 4)
        ],
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
    data = dict(good_format, id="packs-cup", name="Packs Cup", templates=["JC", "6lm10a", "h3dm1"], allowed_towns=allowed or list(towns.ids), roll_rules={"rolls_per_player": 0})
    return Registry(towns, templates, {"packs-cup": parse_format(data, templates, towns, heroes)}, heroes)


@pytest.fixture(autouse=True)
def fixed(monkeypatch):
    monkeypatch.setattr(match, "coinflip", lambda a, b: a)
    monkeypatch.setattr(trade_commands, "random_source", random.Random(4))


@pytest.fixture
def registry(good_format, towns):
    return build_registry(good_format, towns)


def started(registry):
    thread = make_thread(990)
    fmt = registry.formats["packs-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], "JC", ANNA, BORIS))
    return thread


def records_of(thread):
    return [r for r in map(parse, texts(thread)) if r is not None]


def report(registry, thread, winner, amount, choice):
    return run(trade_commands.report, registry, thread, winner, winner, amount, choice)


def test_the_sections_are_the_roll_the_bans_and_the_three_bids():
    assert sections(check_trade(KIND), False) == ("town_roll", "hero_bans", "town_bid", "pack_bid", "color_bid")
    assert sections(check_trade({"kind": "roulette_with_ai_packs"}), False) == ("town_roll", "town_bid", "pack_bid", "color_bid")


def test_a_mirror_cannot_have_packs():
    with pytest.raises(ValueError, match="mirror"):
        sections(check_trade(KIND), True)


def test_a_mirror_template_with_packs_is_refused_when_the_catalogue_is_read(good_format, towns):
    with pytest.raises(Exception, match="mirror template cannot have computer-player packs"):
        build_registry(good_format, towns, mirror=True)


def test_a_match_plays_the_roll_the_bans_the_draw_and_the_three_bids(registry, monkeypatch):
    monkeypatch.setattr(
        trade_commands, "draw_start", lambda kind, mirror, allowed, source=None, banned=(), **_: Draw(("castle", "tower"), PACKS)
    )
    thread = started(registry)
    opening = next(t for t in texts(thread) if " tr g1]" in t[:10]).splitlines()
    assert opening[1:4] == ["Pair: `Castle` vs `Tower`", "Pack1: `Rampart`, `Inferno`, `Dungeon`", "Pack2: `Stronghold`, `Fortress`, `Cove`"]
    assert "<@1> may ban up to 1 hero of Castle vs Tower" in texts(thread)[-1]
    run(trade_commands.ban_heroes, registry, thread, ANNA)
    run(trade_commands.ban_heroes, registry, thread, BORIS)
    drawn = next(r for r in records_of(thread) if r.type == "heroes_drawn")
    assert len(drawn.data["heroes"]) == 2
    assert texts(thread)[-1].startswith("Next step: town bid")
    report(registry, thread, ANNA, 2100, "castle")
    assert "pack bid" in texts(thread)[-1]
    report(registry, thread, ANNA, 1200, "pack2")
    assert "color bid" in texts(thread)[-1]
    report(registry, thread, BORIS, 3000, "red")
    lobby = texts(thread)[-2].splitlines()
    assert lobby[0] == "Game 1 lobby settings - Jebus Cross"
    castle_hero, tower_hero = (registry.heroes.find(name).name for name in drawn.data["heroes"])
    assert lobby[1:] == [
        f"<@2>: Tower ({tower_hero}), pack1 (Rampart, Inferno, Dungeon), red, gold +300",
        f"<@1>: Castle ({castle_hero}), pack2 (Stronghold, Fortress, Cove), blue, gold -300",
    ]


def test_the_trade_rule_and_the_info_line_name_the_packs(registry):
    from rules.trade_kinds import kind_words, trade_rule

    kind = check_trade(KIND)
    assert "roulette with AI packs" in trade_rule(kind, False) and "1 hero ban each" in trade_rule(kind, False)
    assert "drawn together" in trade_rule(check_trade({"kind": "roulette_with_ai_packs", "roll_before_heroes": False}), False)
    assert kind_words(kind) == "roulette with computer-player packs, 1 hero ban each, heroes drawn after the rolls"


def test_with_the_heroes_drawn_together_the_opening_has_the_pair_the_packs_and_the_heroes(good_format, towns):
    registry = build_registry(good_format, towns, {"kind": "roulette_with_ai_packs", "roll_before_heroes": False})
    thread = started(registry)
    opening = next(t for t in texts(thread) if " tr g1]" in t[:10]).splitlines()
    assert [line.split(":")[0] for line in opening[1:6]] == ["Pair", "Pack1", "Pack2", "Hero1", "Hero2"]
    assert texts(thread)[-1].startswith("Next step: town bid")
    assert not any(r.type in ("hero_bans", "heroes_drawn") for r in records_of(thread))


def test_a_phase_with_seven_towns_is_refused_for_this_kind(good_format, towns):
    with pytest.raises(Exception, match="at least eight allowed towns"):
        build_registry(good_format, towns, allowed=list(towns.ids)[:7])
