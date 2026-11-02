"""A phase where every game is played on one template: the match starts without a template, has as many games as the
best-of, and plays them one after another. Made-up formats only (see conftest.py)."""

import asyncio

import pytest

import discord_commands.match as match
import discord_commands.selection as selection
import discord_commands.trade as trade_commands
from rules.formats import parse_format
from rules.registry import Registry
from rules.start import StartError, choose_template, rules_announcement
from rules.trade_draw import Draw
from state import parse
from test_selection_command import ANNA, BORIS, BOT, make_thread, texts, told
from test_trade_command import report, run, start

PAIR = ("necropolis", "tower")


@pytest.fixture
def registry(good_format, templates, towns):
    data = dict(
        good_format,
        id="one-template-cup",
        name="One Template Cup",
        templates=[{"template": "Sapphire", "settings": {"timer": "16:00+07:30+01:30", "sim_turns": "121"}}],
        allowed_towns=["castle", "necropolis", "tower", "cove"],
        roll_rules={"rolls_per_player": 0},
        settings={},
        phases=[{"name": "Final", "best_of": 3, "template_selection": {"type": "fixed"}}],
    )
    return Registry(towns, templates, {"one-template-cup": parse_format(data, templates, towns)})


@pytest.fixture(autouse=True)
def fixed_draws(monkeypatch):
    monkeypatch.setattr(trade_commands, "draw_start", lambda kind, mirror, allowed, source=None, banned=(), **_: Draw(PAIR))
    monkeypatch.setattr(match, "coinflip", lambda a, b: a)


@pytest.fixture
def thread(registry):
    thread = make_thread(910)
    fmt = registry.formats["one-template-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], None, ANNA, BORIS))
    return thread


def records_of(thread):
    return [r for r in map(parse, texts(thread)) if r is not None]


def play_a_trade(registry, thread):
    report(registry, thread, winner=ANNA, amount=2100, choice="Necropolis")
    report(registry, thread, winner=BORIS, amount=3000, choice="red", user=BORIS)


# --- starting ------------------------------------------------------------------------------------------------------


def test_no_template_is_needed_and_the_record_names_none(thread):
    first = records_of(thread)[0]
    assert first.type == "match_started" and first.data["template"] is None


def test_the_rules_give_the_format_the_template_and_what_is_stated_about_it(thread):
    sent = texts(thread)
    assert sent[1:3] == ["Format: BO3", "Template: `Sapphire`"]
    assert "Timer: `16:00+07:30+01:30`" in sent and "Sim turns: `121`" in sent
    assert not any(text.startswith("Template Selection") or text.startswith("Templates:") for text in sent)


def test_the_coinflip_says_nobody_acts_first_and_the_trade_of_game_1_is_opened(thread):
    assert any(text == "[#2 cf] Coinflip: <@1> wins and is A, <@2> is B." for text in texts(thread))
    opening = next(text for text in texts(thread) if " tr g1]" in text[:10])
    assert opening.startswith("[#3 tr g1] Game 1 (Sapphire)")


def test_the_rules_of_a_fixed_phase_are_the_format_and_the_template_then_the_facts(registry):
    phase = registry.formats["one-template-cup"].phases[0]
    assert rules_announcement(phase, "Sapphire", ["Sapphire"], ["Timer: `16:00+07:30+01:30`"]) == [
        "Format: BO3",
        "Template: `Sapphire`",
        "Timer: `16:00+07:30+01:30`",
    ]


def test_choose_template_takes_none_and_accepts_the_phases_template_but_not_another(registry, templates):
    phase = registry.formats["one-template-cup"].phases[0]
    assert choose_template(phase, None, templates) is None
    assert choose_template(phase, "Sapphire", templates) is None  # the same match: every game is played
    with pytest.raises(StartError, match="Every game is played on Sapphire"):
        choose_template(phase, "JC", templates)


# --- the games -----------------------------------------------------------------------------------------------------


def test_after_a_trade_the_next_game_is_announced_on_the_same_template(registry, thread):
    play_a_trade(registry, thread)
    assert texts(thread)[-1].splitlines()[0] == "Game 2 is Sapphire. Start its trade with /trade start."
    start(registry, thread)
    opening = [text for text in texts(thread) if " tr g2]" in text[:10]]
    assert len(opening) == 1 and opening[0].startswith("[#") and "Game 2 (Sapphire)" in opening[0]


def test_all_three_games_are_traded_and_then_the_match_says_so(registry, thread):
    play_a_trade(registry, thread)
    start(registry, thread)
    play_a_trade(registry, thread)
    assert texts(thread)[-1].splitlines()[0] == "Game 3 is Sapphire. Start its trade with /trade start."
    start(registry, thread)
    play_a_trade(registry, thread)
    assert texts(thread)[-1] == "Every game of this match is traded."
    assert [r.game for r in records_of(thread) if r.type == "trade_started"] == [1, 2, 3]


def test_the_status_shows_three_games_on_the_template_and_no_selection(registry, thread):
    status = told(run(match.status, registry, thread, ANNA))
    assert "Template Selection: none, every game is played on the phase's one template" in status
    for number in (1, 2, 3):
        assert f"Game {number}: Sapphire" in status


def test_ban_and_pick_say_the_phase_has_none(registry, thread):
    for command in (selection.ban, selection.pick):
        assert told(run(command, registry, thread, ANNA, "Sapphire")) == "This phase has no bans or picks: every game is played on its one template."


def test_the_trade_of_a_fourth_game_is_refused(registry, thread):
    assert told(start(registry, thread, game="4")) == "This match has games 1 to 3, not 4."


def test_a_trade_of_a_fixed_phase_can_be_undone_like_any_other(registry, thread):
    play_a_trade(registry, thread)
    first_bid = next(r for r in records_of(thread) if r.type == "town_bid")
    run(match.undo, registry, thread, ANNA, first_bid.n)
    run(match.undo, registry, thread, BORIS, first_bid.n)
    assert texts(thread)[-1].startswith("Next step: town bid")


def test_the_mode_info_says_every_game_is_on_the_template_and_has_no_selection_line(registry, templates):
    from rules.info import mode_info

    text = mode_info(registry.formats["one-template-cup"], templates)
    assert "All 3 games are played on Sapphire." in text and "Template Selection" not in text
