import pytest

from rules.undo import UndoError, next_undo, plan_undo, request_text, step_words, undone_text
from state import make_record, parse

A, B = 111, 222  # A started the match; B won the coinflip


def start_of_match():
    return [
        make_record(1, "match_started", p1=A, p2=B, mode="sample-cup", phase="Main", template=None),
        make_record(2, "coinflip", winner=B),
    ]


def ban(n, template="JC", player=B):
    return make_record(n, "ban", player=player, template=template)


def pick(n, template="JC", player=B):
    return make_record(n, "pick", player=player, template=template)


def trade_started(n, game=1):
    return make_record(n, "trade_started", game=game, pair=("castle", "tower"))


def roll(n, game=1, player=A):
    return make_record(n, "roll", game=game, player=player, bans=("castle",), pair=("cove", "tower"))


def town_bid(n, game=1, winner=A, amount=2100):
    return make_record(n, "town_bid", game=game, reporter=A, winner=winner, amount=amount, town="tower")


def ask(n, start, player=A):
    return make_record(n, "undo_requested", player=player, start=start)


def agree(n, start, player=B):
    return make_record(n, "undone", player=player, start=start)


def numbers(plan):
    return [record.n for record in plan.removed]


# --- what a request would undo ---------------------------------------------------------------------------------------


def test_a_request_undoes_the_named_record_and_everything_after_it():
    records = start_of_match() + [ban(3), ban(4, "6lm10a", A), pick(5, "h3dm1")]
    plan = plan_undo(records, 4)
    assert plan.start == 4 and numbers(plan) == [4, 5]


def test_without_a_number_only_the_latest_step_is_undone():
    records = start_of_match() + [ban(3), ban(4, "6lm10a", A), pick(5, "h3dm1")]
    plan = plan_undo(records, None)
    assert plan.start == 5 and numbers(plan) == [5]


def test_later_steps_of_other_kinds_go_too():
    records = start_of_match() + [ban(3), ban(4, "6lm10a", A), pick(5, "h3dm1"), trade_started(6), town_bid(7)]
    assert numbers(plan_undo(records, 5)) == [5, 6, 7]


def test_a_roll_can_be_undone():
    records = start_of_match() + [pick(3), trade_started(4), roll(5)]
    assert numbers(plan_undo(records, 5)) == [5]
    assert numbers(plan_undo(records, 4)) == [4, 5]


def test_a_pending_request_is_not_a_step_to_undo():
    records = start_of_match() + [ban(3), ask(4, 3)]
    assert plan_undo(records, None).start == 3


def test_what_an_earlier_undo_cancelled_is_not_offered_again():
    records = start_of_match() + [ban(3), ban(4, "6lm10a", A), ask(5, 4), agree(6, 4)]
    assert numbers(plan_undo(records, None)) == [3]
    with pytest.raises(UndoError, match="Record 4 was already undone. Check /match status"):
        plan_undo(records, 4)


def test_the_start_and_the_coinflip_cannot_be_undone():
    records = start_of_match() + [ban(3)]
    for number in (1, 2):
        with pytest.raises(UndoError, match="start of the match and the coinflip cannot be undone"):
            plan_undo(records, number)


def test_a_record_that_is_not_a_step_is_refused_and_the_status_pointed_to():
    records = start_of_match() + [ban(3), ban(4, "6lm10a", A)]
    with pytest.raises(UndoError, match="Record 9 is not a step of this match. Check /match status"):
        plan_undo(records, 9)


def test_the_records_about_undoing_are_not_steps_either():
    records = start_of_match() + [ban(3), ask(4, 3)]
    with pytest.raises(UndoError, match="Record 4 is not a step of this match"):
        plan_undo(records, 4)


def test_with_no_step_taken_there_is_nothing_to_undo():
    with pytest.raises(UndoError, match="nothing to undo yet"):
        plan_undo(start_of_match(), None)
    with pytest.raises(UndoError, match="nothing to undo yet"):
        plan_undo(start_of_match(), 3)


# --- a request, a repeat, a confirmation -----------------------------------------------------------------------------------


def test_asking_for_the_first_time_is_a_new_request():
    records = start_of_match() + [ban(3)]
    kind, plan = next_undo(records, A, None)
    assert kind == "request" and plan.start == 3


def test_the_other_player_asking_for_the_same_undo_right_after_confirms_it():
    records = start_of_match() + [ban(3), ask(4, 3, player=A)]
    assert next_undo(records, B, 3)[0] == "confirm"
    assert next_undo(records, B, None)[0] == "confirm"  # no number: the latest step, which is the same one


def test_the_other_player_agrees_without_a_number_whatever_the_request_was_for():
    records = start_of_match() + [ban(3), ban(4, "6lm10a", A), ask(5, 3, player=A)]  # asked for 3, not the latest step
    kind, plan = next_undo(records, B, None)
    assert kind == "confirm" and plan.start == 3 and numbers(plan) == [3, 4]


def test_the_player_who_asked_is_told_to_wait():
    records = start_of_match() + [ban(3), ask(4, 3, player=A)]
    kind, plan = next_undo(records, A, 3)
    assert kind == "waiting" and plan.start == 3
    assert next_undo(records, A, None)[0] == "waiting"


def test_another_record_number_is_a_new_request_even_from_the_other_player():
    records = start_of_match() + [ban(3), ban(4, "6lm10a", A), ask(5, 4, player=A)]
    kind, plan = next_undo(records, B, 3)
    assert kind == "request" and plan.start == 3


def test_a_request_that_something_was_posted_after_is_stale():
    records = start_of_match() + [ban(3), ask(4, 3, player=A), ban(5, "6lm10a", A)]
    assert next_undo(records, B, 3)[0] == "request"
    kind, plan = next_undo(records, B, None)
    assert kind == "request" and plan.start == 5  # without a number it is a new request for the latest step


def test_a_request_for_nothing_to_undo_is_refused_even_if_one_is_pending():
    with pytest.raises(UndoError):
        next_undo(start_of_match() + [ask(3, 3)], B, 3)


# --- the words ------------------------------------------------------------------------------------------------------------------


def test_each_kind_of_step_is_described_in_a_few_words(templates, towns):
    words = lambda record: step_words(record, templates, towns)  # noqa: E731
    assert words(ban(3)) == "<@222> banned Jebus Cross"
    assert words(pick(3, "Diamond")) == "<@222> picked Diamond"
    assert words(trade_started(4)) == "game 1: the trade started (Castle vs Tower)"
    assert words(make_record(5, "trade_resumed", game=2)) == "game 2: the trade was reopened"
    assert words(roll(6)) == "game 1: <@111> rolled, banning Castle (new pair Cove vs Tower)"
    assert words(make_record(6, "roll", game=1, player=A, bans=(), pair=("cove", "tower"))) == (
        "game 1: <@111> rolled (new pair Cove vs Tower)"
    )
    assert words(make_record(7, "roll_skipped", game=1, player=B)) == "game 1: <@222> skipped the roll"
    assert words(town_bid(8)) == "game 1: town bid, <@111> won at 2100 and chose Tower"
    assert words(make_record(9, "color_bid", game=1, reporter=A, winner=B, amount=300, color="red")) == (
        "game 1: color bid, <@222> won at 300 and chose red"
    )


def test_a_request_names_the_step_says_the_rest_goes_too_and_asks_the_other_player_to_agree(templates, towns):
    records = start_of_match() + [ban(3), ban(4, "6lm10a", A), pick(5, "h3dm1")]
    text = request_text("<@111>", "<@222>", plan_undo(records, 4), templates, towns)
    assert text == (
        "<@111> asks to undo from record `4` (<@111> banned 6lm10a) and the 1 step after it. "
        "Check /match status to see where the match stands.\n<@222>, to agree, run /match undo"
    )


def test_a_request_for_a_single_step_does_not_mention_later_ones(templates, towns):
    records = start_of_match() + [ban(3)]
    text = request_text("<@111>", "<@222>", plan_undo(records, None), templates, towns)
    assert text.startswith("<@111> asks to undo from record `3` (<@222> banned Jebus Cross). Check /match status")


def test_a_request_with_several_later_steps_counts_them(templates, towns):
    records = start_of_match() + [ban(3), ban(4, "6lm10a", A), pick(5, "h3dm1"), trade_started(6)]
    assert "and the 3 steps after it" in request_text("<@111>", "<@222>", plan_undo(records, 3), templates, towns)


def test_a_request_reads_back_as_the_record_it_came_from(templates, towns):
    records = start_of_match() + [ban(3), trade_started(4)]
    text = request_text("<@111>", "<@222>", plan_undo(records, 3), templates, towns)
    assert parse(f"[#5 ur] {text}") == ask(5, 3, player=A)


def test_the_confirmation_reads_back_as_the_record_it_came_from():
    text = undone_text("<@222>", 4)
    assert text == "<@222> agreed: the match is back to how it was before record `4`."
    assert parse(f"[#6 ud] {text}") == agree(6, 4)
