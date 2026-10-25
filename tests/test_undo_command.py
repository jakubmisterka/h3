"""Tests /match undo on a fake thread that keeps its messages, so a whole match can be played and then rewound."""

import asyncio

import pytest

import discord_commands.match as match
import discord_commands.selection as selection
import discord_commands.trade as trade_commands
from state import parse
from test_selection_command import ANNA, BORIS, OUTSIDER, interaction, make_thread, texts, told
from test_trade_command import (  # noqa: F401  (fixtures are used by name)
    FIRST_PICK,
    PAIR,
    WHOLE_SELECTION,
    build_registry,
    fixed_pair,
    registry,
    rolling,
    rolling_registry,
    run,
    select,
    start,
    thread,
)

# Anna won the coinflip and is A. Records: 1 match started, 2 coinflip, then 3 Anna bans, 4 Boris bans, 5 Anna picks.


def undo(registry, thread, user=ANNA, from_=None):
    return run(match.undo, registry, thread, user, from_)


def records_of(thread):
    return [r for r in map(parse, texts(thread)) if r is not None]


def types(thread):
    return [r.type for r in records_of(thread)]


def agreement(thread):
    """The text of the last record that agreed to an undo."""
    return next(text for text in reversed(texts(thread)) if " ud]" in text[:10])


def after_undo(thread):
    """The messages the bot posted after the last agreement: where the match stands, then what to do next."""
    all_texts = texts(thread)
    return all_texts[all_texts.index(agreement(thread)) + 1 :]


# --- asking ----------------------------------------------------------------------------------------------------------------


def test_asking_names_the_step_points_to_the_status_and_asks_the_other_player_to_agree(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    it = undo(registry, thread, ANNA)
    assert told(it) == "Asked. <@2> has to agree."
    assert texts(thread)[-1].splitlines() == [
        "[#5 ur] <@1> asks to undo from record `4` (<@2> banned Sapphire). Check /match status to see where the match stands.",
        "<@2>, to agree, run /match undo",
    ]


def test_a_number_undoes_that_record_and_says_everything_after_it_goes_too(registry, thread):
    select(registry, thread, *FIRST_PICK)
    undo(registry, thread, ANNA, 4)
    assert "from record `4` (<@2> banned Sapphire) and the 1 step after it" in texts(thread)[-1]


def test_asking_changes_nothing_in_the_match_until_the_other_player_agrees(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA)
    assert "Template Selection: step 3 of 4" in _status(registry, thread)  # Boris's ban still counts
    it = run(selection.pick, registry, thread, ANNA, "JC")  # and the match carries on as usual
    assert told(it) == "You picked Jebus Cross."


# --- agreeing ----------------------------------------------------------------------------------------------------------------


def test_the_other_player_asking_for_the_same_undo_confirms_it(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA)
    it = undo(registry, thread, BORIS)
    assert told(it) == "Undone."
    assert [r for r in types(thread) if r in ("undo_requested", "undone")] == ["undo_requested", "undone"]
    assert "[#6 ud] <@2> agreed: the match is back to how it was before record `4`." in texts(thread)


def test_after_an_undo_the_bot_shows_where_the_match_stands(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA)
    undo(registry, thread, BORIS)
    posted = after_undo(thread)
    assert "Template Selection: step 2 of 4, <@2> bans" in posted[0] and "Game 1: not decided yet" in posted[0]


def test_after_an_undo_the_bot_says_what_to_do_next(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA)
    undo(registry, thread, BORIS)
    posted = after_undo(thread)
    assert posted[1].startswith("Remaining (4):")
    assert posted[-1] == "Step 2 of 4: <@2> bans a template with /ban"


def test_the_undone_step_can_be_taken_again_and_the_numbering_carries_on(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA)
    undo(registry, thread, BORIS)
    it = run(selection.ban, registry, thread, BORIS, "Diamond")
    assert told(it) == "You banned Diamond."
    assert "[#7 bn] <@2> banned **Diamond** (`Diamond`)" in texts(thread)
    assert "Remaining (3):" in "".join(texts(thread)[-3:])


def test_the_player_who_asked_cannot_confirm_their_own_request(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA)
    before = texts(thread)
    it = undo(registry, thread, ANNA)
    assert "Waiting for <@2> to run /match undo." in told(it)
    assert texts(thread) == before


def test_a_request_that_something_was_posted_after_is_not_confirmed(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA)
    run(selection.pick, registry, thread, ANNA, "JC")  # the match moved on after the request
    it = undo(registry, thread, BORIS, 4)
    assert told(it) == "Asked. <@1> has to agree."
    assert "undone" not in types(thread)


def test_another_record_number_is_a_new_request(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA, 4)
    it = undo(registry, thread, BORIS, 3)
    assert told(it) == "Asked. <@1> has to agree."
    assert "undone" not in types(thread)


# --- everything after the record goes -------------------------------------------------------------------------------------------


def test_a_trade_started_after_a_pick_goes_with_the_pick(registry, thread):
    select(registry, thread, *FIRST_PICK)
    start(registry, thread)
    run(trade_commands.report, registry, thread, ANNA, ANNA, 2100, "Necropolis")
    undo(registry, thread, ANNA, 5)
    undo(registry, thread, BORIS, 5)

    posted = after_undo(thread)
    assert "Template Selection: step 3 of 4, <@1> picks" in posted[0] and "Game 1: not decided yet" in posted[0]
    assert posted[-1] == "Step 3 of 4: <@1> picks a template with /pick"
    assert "No trade is open" in told(run(trade_commands.report, registry, thread, ANNA, ANNA, 100, "Tower"))


def test_the_request_counts_the_trade_steps_that_go_with_a_pick(registry, thread):
    select(registry, thread, *FIRST_PICK)
    start(registry, thread)
    run(trade_commands.report, registry, thread, ANNA, ANNA, 2100, "Necropolis")
    undo(registry, thread, ANNA, 5)
    assert "from record `5` (<@1> picked Jebus Cross) and the 2 steps after it" in texts(thread)[-1]


def test_undoing_a_bid_returns_the_trade_to_before_it(registry, thread):
    select(registry, thread, *FIRST_PICK)
    start(registry, thread)
    run(trade_commands.report, registry, thread, ANNA, ANNA, 2100, "Necropolis")
    undo(registry, thread, ANNA)  # the latest step is the bid
    undo(registry, thread, BORIS)
    posted = after_undo(thread)
    assert "Game 1: Jebus Cross, trade open, next: town bid Necropolis vs Tower, gold difference <@1> 0 / <@2> 0" in posted[0]
    assert len(posted) == 2  # the last step that counts is a step of the trade, so only the trade is asked about
    assert posted[-1].startswith("Game 1 town bid: Necropolis vs Tower.")  # and it asks for the result again
    it = run(trade_commands.report, registry, thread, BORIS, BORIS, 300, "Tower")
    assert told(it) == "Reported."


def test_a_roll_can_be_undone_and_made_again(rolling_registry, rolling):
    run(trade_commands.roll, rolling_registry, rolling, ANNA, "Necropolis", None)
    assert "gold difference <@1> -500 / <@2> +500" in _status(rolling_registry, rolling)
    undo(rolling_registry, rolling, ANNA)
    undo(rolling_registry, rolling, BORIS)
    assert "gold difference <@1> 0 / <@2> 0" in _status(rolling_registry, rolling)
    it = run(trade_commands.roll, rolling_registry, rolling, ANNA, None, None)
    assert told(it) == "Rolled."


def _status(registry, thread):
    it = interaction(registry, thread, ANNA)
    asyncio.run(match.status.callback(it))
    return told(it)


def test_the_status_ignores_what_was_undone(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA)
    undo(registry, thread, BORIS)
    assert "Template Selection: step 2 of 4" in _status(registry, thread)


# --- refusals ------------------------------------------------------------------------------------------------------------------------


def test_nothing_to_undo_at_the_start(registry, thread):
    before = texts(thread)
    it = undo(registry, thread, ANNA)
    assert "nothing to undo yet" in told(it)
    assert texts(thread) == before


def test_the_start_and_the_coinflip_cannot_be_undone(registry, thread):
    select(registry, thread, *FIRST_PICK[:1])
    for number in (1, 2):
        assert "cannot be undone" in told(undo(registry, thread, ANNA, number))


def test_a_record_that_is_not_a_step_is_refused_and_the_status_pointed_to(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    it = undo(registry, thread, ANNA, 9)
    assert "Record 9 is not a step of this match. Check /match status" in told(it)


def test_an_undone_record_cannot_be_undone_again_and_the_status_is_pointed_to(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA)
    undo(registry, thread, BORIS)
    assert "Record 4 was already undone. Check /match status" in told(undo(registry, thread, ANNA, 4))


def test_the_status_marks_the_records_that_were_undone(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA)
    undo(registry, thread, BORIS)
    status = _status(registry, thread)
    assert "4. <@2> bans Sapphire (undone)" in status
    assert "3. <@1> bans 6lm10a\n" in status  # still counts, so no mark
    assert "(undone)" not in status.split("5.")[1]  # the request and the agreement are not marked


def test_an_outsider_cannot_ask_or_agree(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    before = texts(thread)
    assert "Only the two players" in told(undo(registry, thread, OUTSIDER))
    assert texts(thread) == before


def test_outside_a_match_thread_the_player_is_sent_there(registry):
    it = interaction(registry, None, ANNA, in_thread=False)
    asyncio.run(match.undo.callback(it, None))
    assert "inside a match thread" in told(it)


def test_the_command_is_called_undo_and_takes_an_optional_record_number_called_from():
    assert match.undo.name == "undo"
    [parameter] = match.undo.parameters
    assert (parameter.display_name, parameter.required, parameter.type.name) == ("from", False, "integer")
    assert "ecord number" in parameter.description and "agree" in parameter.description
    assert len(parameter.description) <= 100  # Discord allows no more in the description of an option


# --- agreeing without a number --------------------------------------------------------------------------------------------


def test_the_other_player_agrees_without_a_number_even_if_the_request_was_for_an_older_record(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA, 3)  # asks to go back before the first ban, not just the latest step
    it = undo(registry, thread, BORIS)
    assert told(it) == "Undone."
    assert "before record `3`" in agreement(thread)
    posted = after_undo(thread)
    assert "Template Selection: step 1 of 4, <@1> bans" in posted[0]
    assert posted[-1] == "Step 1 of 4: <@1> bans a template with /ban"


def test_agreeing_with_the_same_number_works_too(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA, 3)
    assert told(undo(registry, thread, BORIS, 3)) == "Undone."


# --- a new request replaces the one that is waiting ---------------------------------------------------------------------------------------------------


def test_the_same_player_asking_for_another_record_replaces_their_request(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA, 4)
    undo(registry, thread, ANNA, 3)
    assert "from record `3`" in texts(thread)[-1] and "This replaces the earlier request." in texts(thread)[-1]
    # only the new request can be agreed to
    assert told(undo(registry, thread, BORIS)) == "Undone."
    assert "before record `3`" in agreement(thread)


def test_the_other_player_asking_for_another_record_replaces_the_request_too(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA, 4)
    undo(registry, thread, BORIS, 3)
    assert "<@2> asks to undo from record `3`" in texts(thread)[-1] and "This replaces" in texts(thread)[-1]
    assert "Waiting for <@1>" in told(undo(registry, thread, BORIS))  # the old request is gone: Anna has to agree now
    assert told(undo(registry, thread, ANNA)) == "Undone."


def test_a_request_that_replaces_nothing_does_not_say_so(registry, thread):
    select(registry, thread, *FIRST_PICK[:2])
    undo(registry, thread, ANNA, 4)
    assert "replaces" not in texts(thread)[-1]


# --- what is said to do next --------------------------------------------------------------------------------------------------------------------


def test_after_undoing_the_last_step_of_the_selection_the_bot_says_what_the_games_are_and_to_start_a_trade(registry, thread):
    select(registry, thread, *WHOLE_SELECTION)
    undo(registry, thread, ANNA, 6)  # B's pick, which decided the last game
    undo(registry, thread, BORIS)
    posted = after_undo(thread)
    assert posted[-2] == "Step 4 of 4: <@2> picks a template with /pick"
    assert posted[-1] == "Game 1 is Jebus Cross. Start its trade with /trade start."


def test_after_undoing_a_roll_the_open_trade_asks_for_a_roll_or_a_skip_again(rolling_registry, rolling):
    run(trade_commands.roll, rolling_registry, rolling, ANNA, None, None)
    undo(rolling_registry, rolling, ANNA)
    undo(rolling_registry, rolling, BORIS)
    assert after_undo(rolling)[-1].startswith("Game 1 town roll: Necropolis vs Tower. A roll costs 500 gold. Both players may roll.")


# --- undoing a bid does not reopen a roll that the bid had settled ----------------------------------------------------------------------------------


def bid_after_a_roll(rolling_registry, rolling):
    run(trade_commands.roll, rolling_registry, rolling, ANNA, None, None)  # Anna rolls; Boris has not decided
    pair = rolls_in(rolling)[0].data["pair"]
    run(trade_commands.report, rolling_registry, rolling, ANNA, ANNA, 100, pair[0])  # the bid settles Boris's roll


def rolls_in(thread):
    return [r for r in records_of(thread) if r.type == "roll"]


def test_undoing_the_bid_after_a_roll_goes_back_to_the_town_bid_not_to_the_roll(rolling_registry, rolling):
    bid_after_a_roll(rolling_registry, rolling)
    undo(rolling_registry, rolling, ANNA)  # the latest step: the bid
    undo(rolling_registry, rolling, BORIS)
    posted = after_undo(rolling)
    assert posted[-1].startswith("Game 1 town bid:")
    assert "next: town bid" in posted[0]


def test_the_roll_section_opens_again_only_when_the_skip_itself_is_undone(rolling_registry, rolling):
    bid_after_a_roll(rolling_registry, rolling)
    skip_number = next(r.n for r in records_of(rolling) if r.type == "roll_skipped")
    undo(rolling_registry, rolling, ANNA, skip_number)
    undo(rolling_registry, rolling, BORIS)
    posted = after_undo(rolling)
    assert "A roll costs 500 gold. <@2> may roll." in posted[-1]


def test_the_overview_after_an_undo_names_the_town_bid_and_its_pair(rolling_registry, rolling):
    run(trade_commands.roll, rolling_registry, rolling, ANNA, None, None)
    undo(rolling_registry, rolling, ANNA)
    undo(rolling_registry, rolling, BORIS)
    line = [l for l in after_undo(rolling)[0].splitlines() if l.startswith("Game 1")][0]
    assert "next: town bid Necropolis vs Tower (rolls still open)" in line
    assert "gold difference <@1> 0 / <@2> 0" in line
