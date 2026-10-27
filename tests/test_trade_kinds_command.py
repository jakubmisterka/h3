"""A mirror trade and a trade with computer-player packs, played through the commands on a fake thread: the opening,
the roll, the bids, the suggestions, the match status, the undo and the lobby settings."""

import asyncio
import random

import pytest

import discord_commands.match as match
import discord_commands.trade as trade_commands
from rules.catalogue import parse_templates
from rules.formats import parse_format
from rules.registry import Registry
from rules.trade_draw import Draw
from state import parse
from test_selection_command import ANNA, BORIS, BOT, interaction, make_thread, texts, told
from test_trade_command import run

PACKS = ("rampart", "inferno", "dungeon", "stronghold", "fortress", "cove")


@pytest.fixture
def registry(good_format, towns):
    templates = parse_templates(
        [
            {"id": "JC", "name": "Jebus Cross", "difficulty": 160},
            {"id": "h3dm1", "name": "h3dm1", "difficulty": 160, "mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}},
            {"id": "Sapphire", "name": "Sapphire", "difficulty": 160, "trade": "standard_with_ai_packs"},
        ],
        "templates.json",
    )
    data = dict(
        good_format,
        id="kinds-cup",
        name="Kinds Cup",
        templates=["JC", "h3dm1", "Sapphire"],
        allowed_towns=list(towns.ids),
        roll_rules={"rolls_per_player": 1},
    )
    return Registry(towns, templates, {"kinds-cup": parse_format(data, templates, towns)})


@pytest.fixture(autouse=True)
def fixed_draws(monkeypatch):
    """Anna wins the coinflip and is A; the bot draws the same towns every time, and rolls from a seeded source."""

    def draw(kind, mirror, allowed, source=None, banned=()):
        if kind.name == "standard_with_ai_packs":
            return Draw(("castle", "tower"), PACKS)
        return Draw(("necropolis",) if mirror else ("castle", "tower"))

    monkeypatch.setattr(match, "coinflip", lambda a, b: a)
    monkeypatch.setattr(trade_commands, "draw_start", draw)
    monkeypatch.setattr(trade_commands, "random_source", random.Random(11))


def started(registry, template):
    thread = make_thread(950)
    fmt = registry.formats["kinds-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], template, ANNA, BORIS))
    return thread


def report(registry, thread, winner, amount, choice, user=None):
    return run(trade_commands.report, registry, thread, user or winner, winner, amount, choice)


def records_of(thread):
    return [r for r in map(parse, texts(thread)) if r is not None]


def choices(registry, thread, command_option, current=""):
    it = interaction(registry, thread, ANNA)
    return [(c.name, c.value) for c in asyncio.run(command_option(it, current))]


# --- the mirror trade ---------------------------------------------------------------------------------------------


def test_a_mirror_match_opens_with_the_one_town_and_the_roll(registry):
    thread = started(registry, "h3dm1")
    trade_start = next(t for t in texts(thread) if " tr g1]" in t[:10])
    assert "mirror: both players play the same town" in trade_start and "Town: `Necropolis`" in trade_start
    assert "Pair:" not in trade_start
    assert texts(thread)[-1].splitlines() == [  # what was drawn is in the message above, so it is not said again
        "A roll costs 500 gold. Both players may roll.",
        "Roll with /trade roll (it bans this town), or skip with /trade skip-roll.",
    ]


def test_a_mirror_roll_bans_the_town_and_pays(registry):
    thread = started(registry, "h3dm1")
    it = run(trade_commands.roll, registry, thread, ANNA)
    assert told(it) == "Rolled."
    roll = records_of(thread)[-1]
    assert roll.type == "roll" and roll.data["bans"] == ("Necropolis",) and len(roll.data["towns"]) == 1
    assert roll.data["towns"] != ("Necropolis",)
    assert "paid 500 gold to <@2>" in texts(thread)[-2] and "New town:" in texts(thread)[-2]


def test_a_mirror_roll_that_names_a_town_is_refused(registry):
    thread = started(registry, "h3dm1")
    before = len(texts(thread))
    it = run(trade_commands.roll, registry, thread, ANNA, "Castle")
    assert "names no town" in told(it) and len(texts(thread)) == before


def test_reporting_a_town_in_a_mirror_is_refused_with_the_reason(registry):
    thread = started(registry, "h3dm1")
    it = report(registry, thread, ANNA, 0, "necropolis")
    assert "only the color is bid" in told(it)


def test_the_color_bid_finishes_a_mirror_and_the_lobby_settings_give_the_town(registry):
    thread = started(registry, "h3dm1")
    report(registry, thread, BORIS, 3000, "red")
    assert [r.type for r in records_of(thread)][-3:] == ["roll_skipped", "roll_skipped", "color_bid"]  # the open rolls are skipped
    assert texts(thread)[-2].splitlines() == [  # the last message says it was the only game
        "Game 1 lobby settings - h3dm1",
        "Map: L+U",
        "Town (both players): Necropolis",
        "<@1>: blue, gold +3000",
        "<@2>: red, gold -3000",
    ]


def test_the_suggestions_in_a_mirror_are_colors_and_no_ban(registry):
    thread = started(registry, "h3dm1")
    assert choices(registry, thread, trade_commands._choice_options) == [("red", "red"), ("blue", "blue")]
    assert choices(registry, thread, trade_commands._ban_options) == []


def test_the_status_of_a_mirror_names_the_color_bid(registry):
    thread = started(registry, "h3dm1")
    it = run(match.status, registry, thread, ANNA)
    assert "trade open, next: color bid (rolls still open)" in told(it)


def test_a_mirror_roll_can_be_undone(registry):
    thread = started(registry, "h3dm1")
    run(trade_commands.roll, registry, thread, ANNA)
    roll_number = records_of(thread)[-1].n
    run(match.undo, registry, thread, ANNA, roll_number)
    run(match.undo, registry, thread, BORIS, roll_number)
    assert "Town: `Necropolis`" in " ".join(texts(thread)) and "Necropolis, played by both" in texts(thread)[-1]


# --- the trade with computer-player packs ------------------------------------------------------------------------------


def test_a_packs_match_announces_the_pair_and_the_packs(registry):
    thread = started(registry, "Sapphire")
    opening = next(t for t in texts(thread) if " tr g1]" in t[:10])
    assert "with computer-player packs" in opening
    assert opening.splitlines()[1:6] == [
        "Pair: `Castle` vs `Tower`",
        "Pack1: `Rampart`, `Inferno`, `Dungeon`",
        "Pack2: `Stronghold`, `Fortress`, `Cove`",
        "Starting gold: <@1> 10000, <@2> 10000",
    ]
    assert texts(thread)[-1].startswith("A roll costs 500 gold.") and "Pack" not in texts(thread)[-1]


def test_a_packs_roll_redraws_everything_and_bans_only_the_pair(registry):
    thread = started(registry, "Sapphire")
    it = run(trade_commands.roll, registry, thread, ANNA, "Rampart")
    assert "not in the current pair" in told(it)
    run(trade_commands.roll, registry, thread, ANNA, "Castle")
    roll = records_of(thread)[-1]
    drawn = roll.data["towns"] + roll.data["packs"]
    assert roll.data["bans"] == ("Castle",) and len(roll.data["towns"]) == 2 and len(roll.data["packs"]) == 6
    assert len(set(drawn)) == 8 and "Castle" not in roll.data["towns"]
    lines = texts(thread)[-2].splitlines()  # the roll, then the gold difference
    assert lines[1].startswith("New pair: ") and lines[2].startswith("Pack1: ") and lines[3].startswith("Pack2: ")
    assert lines[4].startswith("Gold difference")


def test_the_bids_of_a_packs_match_go_town_pack_color(registry):
    thread = started(registry, "Sapphire")
    report(registry, thread, ANNA, 2100, "castle")
    assert "pack bid" in texts(thread)[-1]
    report(registry, thread, ANNA, 1200, "pack2")
    assert "color bid" in texts(thread)[-1]
    report(registry, thread, BORIS, 3000, "red")
    assert texts(thread)[-2].splitlines() == [
        "Game 1 lobby settings - Sapphire",
        "<@1>: Castle, pack2 (Stronghold, Fortress, Cove), blue, gold -300",
        "<@2>: Tower, pack1 (Rampart, Inferno, Dungeon), red, gold +300",
    ]


def test_a_pack_that_does_not_exist_is_refused_through_the_command(registry):
    thread = started(registry, "Sapphire")
    report(registry, thread, ANNA, 0, "castle")
    it = report(registry, thread, ANNA, 0, "pack3")
    assert "Choose pack1 or pack2" in told(it)


def test_the_suggestions_for_the_pack_bid_name_the_towns_of_each_pack(registry):
    thread = started(registry, "Sapphire")
    assert choices(registry, thread, trade_commands._choice_options) == [("Castle", "castle"), ("Tower", "tower")]
    report(registry, thread, ANNA, 0, "castle")
    assert choices(registry, thread, trade_commands._choice_options) == [
        ("pack1: Rampart, Inferno, Dungeon", "pack1"),
        ("pack2: Stronghold, Fortress, Cove", "pack2"),
    ]
    assert choices(registry, thread, trade_commands._choice_options, "pack2") == [("pack2: Stronghold, Fortress, Cove", "pack2")]


def test_the_status_of_a_packs_match_names_the_pack_bid(registry):
    thread = started(registry, "Sapphire")
    report(registry, thread, ANNA, 0, "castle")
    assert "next: pack bid" in told(run(match.status, registry, thread, ANNA))


def test_the_pack_bid_can_be_undone_and_is_asked_for_again(registry):
    thread = started(registry, "Sapphire")
    report(registry, thread, ANNA, 2100, "castle")
    report(registry, thread, ANNA, 1200, "pack2")
    pack_bid = next(r for r in records_of(thread) if r.type == "pack_bid")
    run(match.undo, registry, thread, ANNA, pack_bid.n)
    run(match.undo, registry, thread, BORIS, pack_bid.n)
    last = texts(thread)[-1]
    assert "pack bid" in last and "Pack1: Rampart" in last
    report(registry, thread, BORIS, 0, "pack1")  # the pack bid can be reported again
    assert "color bid" in texts(thread)[-1]


def test_the_ask_to_undo_the_pack_bid_names_it(registry):
    thread = started(registry, "Sapphire")
    report(registry, thread, ANNA, 2100, "castle")
    report(registry, thread, ANNA, 1200, "pack2")
    pack_bid = next(r for r in records_of(thread) if r.type == "pack_bid")
    run(match.undo, registry, thread, ANNA, pack_bid.n)
    assert "pack bid, <@1> won at 1200 and chose pack2" in texts(thread)[-1]


# --- a standard template in the same tournament is not touched ------------------------------------------------------


def test_a_standard_template_still_gets_a_pair_and_a_town_bid(registry):
    thread = started(registry, "JC")
    opening = next(t for t in texts(thread) if " tr g1]" in t[:10])
    assert "\nPair: `Castle` vs `Tower`\n" in opening and "Packs" not in opening and "mirror" not in opening


# --- the roll prompt does not say again what was just drawn ---------------------------------------------------------


def test_the_prompt_after_a_roll_does_not_repeat_the_new_draw(registry):
    thread = started(registry, "Sapphire")
    run(trade_commands.roll, registry, thread, ANNA, "Castle")
    prompt = texts(thread)[-1]
    assert "\nPack1: " in texts(thread)[-2] and "Pack" not in prompt and "Pair" not in prompt
    assert "<@2> may roll" in prompt


def test_after_an_undo_the_roll_prompt_says_what_stands(registry):
    thread = started(registry, "Sapphire")
    run(trade_commands.roll, registry, thread, ANNA, "Castle")
    roll_number = records_of(thread)[-1].n
    run(match.undo, registry, thread, ANNA, roll_number)
    run(match.undo, registry, thread, BORIS, roll_number)
    prompt = texts(thread)[-1].splitlines()
    assert prompt[:4] == ["Game 1 town roll", "Pair: Castle vs Tower", "Pack1: Rampart, Inferno, Dungeon", "Pack2: Stronghold, Fortress, Cove"]
    assert prompt[4] == "A roll costs 500 gold. Both players may roll."


def test_after_an_undo_the_mirror_prompt_says_the_town_that_stands(registry):
    thread = started(registry, "h3dm1")
    run(trade_commands.roll, registry, thread, ANNA)
    roll_number = records_of(thread)[-1].n
    run(match.undo, registry, thread, ANNA, roll_number)
    run(match.undo, registry, thread, BORIS, roll_number)
    assert texts(thread)[-1].splitlines()[0] == "Game 1 town roll: Necropolis, played by both"


def test_in_a_mirror_a_skip_does_not_stop_a_player_banning_the_next_town(registry):
    thread = started(registry, "h3dm1")
    run(trade_commands.skip_roll, registry, thread, BORIS)
    run(trade_commands.roll, registry, thread, ANNA)  # a new town is drawn
    assert texts(thread)[-1].startswith("A roll costs 500 gold. <@2> may roll.")
    it = run(trade_commands.roll, registry, thread, BORIS)  # Boris may ban the new town after all
    assert told(it) == "Rolled." and [r.type for r in records_of(thread)].count("roll") == 2
