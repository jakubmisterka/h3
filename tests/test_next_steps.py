"""What the bot says to do next depends on the latest step that counts: a step of the open trade means the trade, a ban
or a pick (or nothing yet) means the selection. These tests play a match and ask for it after each kind of step."""

import discord_commands.selection as selection
import discord_commands.trade as trade_commands
from rules.situation import next_steps, situation_of
from state import parse
from test_selection_command import ANNA, BORIS, texts
from test_trade_command import (  # noqa: F401  (fixtures are used by name)
    FIRST_PICK,
    WHOLE_SELECTION,
    fixed_pair,
    registry,
    run,
    select,
    start,
    thread,
)


def next_after(registry, thread):
    records = [r for r in map(parse, texts(thread)) if r is not None]
    return next_steps(situation_of(registry, records), registry.templates, registry.towns)


def test_before_any_step_it_is_the_first_step_of_the_selection(registry, thread):
    assert next_after(registry, thread)[-1] == "Step 1 of 4: <@1> bans a template with /ban"


def test_after_a_ban_it_is_the_next_step_of_the_selection(registry, thread):
    select(registry, thread, FIRST_PICK[0])
    assert next_after(registry, thread) == [
        "Remaining (4): Jebus Cross, h3dm1, Diamond, Sapphire\nBanned: 6lm10a. Picked: none.",
        "Step 2 of 4: <@2> bans a template with /ban",
    ]


def test_after_a_pick_the_game_it_decided_can_be_traded(registry, thread):
    select(registry, thread, *FIRST_PICK)
    assert next_after(registry, thread)[-1] == "Game 1 is Jebus Cross. Start its trade with /trade start."
    assert "Step 4 of 4: <@2> picks a template with /pick" in next_after(registry, thread)


def test_after_a_trade_step_it_is_only_the_trade_even_if_the_selection_is_not_finished(registry, thread):
    select(registry, thread, *FIRST_PICK)
    start(registry, thread)
    assert next_after(registry, thread) == [
        "Game 1 town bid: Necropolis vs Tower. <@1> bids first, raising by at least 100. Report the result with /trade report."
    ]


def test_a_selection_step_taken_while_a_trade_is_open_brings_the_selection_back(registry, thread):
    select(registry, thread, *FIRST_PICK)
    start(registry, thread)
    run(selection.pick, registry, thread, BORIS, "Diamond")  # the latest step is a pick again
    messages = next_after(registry, thread)
    assert messages[0].startswith("Remaining (")
    assert messages[-2:] == [
        "Game 2 is Diamond. Start its trade with /trade start.",
        "Game 3 is h3dm1. Start its trade with /trade start.",
    ]
    assert not any("town bid" in message for message in messages)


def test_after_the_last_report_it_is_the_lobby_settings(registry, thread):
    select(registry, thread, *WHOLE_SELECTION)
    start(registry, thread)
    run(trade_commands.report, registry, thread, ANNA, ANNA, 2100, "Necropolis")
    run(trade_commands.report, registry, thread, BORIS, BORIS, 3000, "red")
    [summary] = next_after(registry, thread)
    assert summary.startswith("Game 1 lobby settings - Jebus Cross")
