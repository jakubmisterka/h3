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
        "Game 1 town bid: Necropolis vs Tower\n<@1> bids first, raising by at least 100.\nReport the result with /trade report."
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
    summary, *after = next_after(registry, thread)
    assert summary.startswith("Game 1 lobby settings - Jebus Cross")
    assert after == ["Game 2 is Diamond. Start its trade with /trade start."]  # and what comes after it


# --- after the trade of a game ------------------------------------------------------------------------------------------


def trade_game(registry, thread, game):
    start(registry, thread, str(game))
    run(trade_commands.report, registry, thread, ANNA, ANNA, 2100, "Necropolis")
    run(trade_commands.report, registry, thread, BORIS, BORIS, 3000, "red")


def test_after_a_trade_the_selection_that_is_not_done_goes_on(registry, thread):
    select(registry, thread, *FIRST_PICK)
    trade_game(registry, thread, 1)
    assert texts(thread)[-1] == "Step 4 of 4: <@2> picks a template with /pick"


def test_after_the_last_trade_the_thread_says_every_game_is_traded(registry, thread):
    select(registry, thread, *WHOLE_SELECTION)
    for game in (1, 2):
        trade_game(registry, thread, game)
    assert next_after(registry, thread)[-1].startswith("Game 3 is h3dm1")  # the decider is still to be traded
    trade_game(registry, thread, 3)
    assert texts(thread)[-1] == "Every game of this match is traded."


def test_the_next_step_comes_first_and_the_trade_to_start_last(good_format, templates, towns, monkeypatch):
    import asyncio

    import discord_commands.match as match
    from rules.formats import parse_format
    from rules.registry import Registry
    from test_selection_command import BOT, make_thread

    pool = ["JC", "6lm10a", "h3dm1", "nostalgia", "mt_nebula", "mt_Jebus", "Sapphire"]
    steps = [{"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "A", "do": "pick"}, {"who": "B", "do": "pick"}]
    steps += [{"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"do": "decider"}]
    data = dict(
        good_format, id="long-cup", name="Long Cup", templates=pool, allowed_towns=["castle", "necropolis", "tower", "cove"],
        roll_rules={"rolls_per_player": 0},
        phases=[{"name": "Main", "best_of": 3, "template_selection": {"type": "sequence", "steps": steps}}],
    )
    registry = Registry(towns, templates, {"long-cup": parse_format(data, templates, towns)})
    thread = make_thread(970)
    fmt = registry.formats["long-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], None, ANNA, BORIS))
    select(registry, thread, ("ban", "6lm10a", ANNA), ("ban", "Sapphire", BORIS), ("pick", "JC", ANNA), ("pick", "h3dm1", BORIS))
    trade_game(registry, thread, 1)
    assert texts(thread)[-2] == "Step 5 of 6: <@1> bans a template with /ban"
    assert texts(thread)[-1] == "Game 2 is h3dm1. Start its trade with /trade start."
