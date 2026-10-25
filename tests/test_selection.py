import pytest

from rules.formats import Step
from rules.selection import (
    Action,
    SelectionError,
    after_a_step,
    check_action,
    choose_available,
    games,
    has_decider,
    known_games,
    next_step,
    remaining,
    replay,
)

NINE = ("JC", "6lm10a", "h3dm1", "nostalgia", "mt_nebula", "mt_Jebus", "Sapphire", "Diamond", "Conquest")


def sequence(text: str) -> tuple[Step, ...]:
    """Steps from short words: "A-ban B-pick decider"."""
    steps = []
    for word in text.split():
        if word == "decider":
            steps.append(Step(None, "decider"))
        else:
            who, do = word.split("-")
            steps.append(Step(who, do))
    return tuple(steps)


BO1 = sequence("A-ban B-ban decider")
BO3_NINE = sequence("A-ban B-ban A-pick B-pick A-ban B-ban B-ban A-ban decider")
BO3_SEVEN = sequence("A-ban B-ban B-ban A-ban A-pick B-pick decider")
NO_DECIDER = sequence("A-pick B-pick")


# --- whose step is it --------------------------------------------------------------------------------


def test_the_sequence_is_followed_in_order_with_the_decider_acted_by_nobody():
    actions = []
    seen = []
    while (step := next_step(BO3_NINE, actions)) is not None:
        seen.append(f"{step.who}-{step.do}")
        actions.append(Action(step.who, step.do, NINE[len(actions)]))
    assert seen == ["A-ban", "B-ban", "A-pick", "B-pick", "A-ban", "B-ban", "B-ban", "A-ban"]


def test_b_can_act_twice_in_a_row():
    actions = [Action("A", "ban", "JC"), Action("B", "ban", "6lm10a")]
    assert next_step(BO3_SEVEN, actions).who == "B"
    actions.append(Action("B", "ban", "h3dm1"))
    assert next_step(BO3_SEVEN, actions).who == "A"


def test_when_every_step_is_done_no_step_is_left():
    actions = [Action("A", "ban", "JC"), Action("B", "ban", "6lm10a")]
    assert next_step(BO1, actions) is None


def test_the_decider_is_known():
    assert has_decider(BO1) and not has_decider(NO_DECIDER)


# --- the acting player and the action ----------------------------------------------------------------


def test_the_player_whose_step_it_is_may_act():
    check_action(BO1, [], "A", "ban")  # no error
    check_action(BO1, [Action("A", "ban", "JC")], "B", "ban")


def test_the_wrong_player_is_refused_and_told_whose_step_it_is():
    with pytest.raises(SelectionError, match="player A's step"):
        check_action(BO1, [], "B", "ban")


def test_the_wrong_action_is_refused_and_the_expected_one_named():
    with pytest.raises(SelectionError, match="A ban is expected now, not a pick"):
        check_action(BO1, [], "A", "pick")


def test_after_the_last_step_nothing_more_is_accepted():
    done = [Action("A", "ban", "JC"), Action("B", "ban", "6lm10a")]
    with pytest.raises(SelectionError, match="finished"):
        check_action(BO1, done, "A", "ban")


# --- the pool ---------------------------------------------------------------------------------------------


def test_the_remaining_pool_loses_what_was_banned_or_picked():
    actions = [Action("A", "ban", "mt_nebula"), Action("B", "pick", "JC")]
    left = remaining(NINE, actions)
    assert len(left) == 7 and "mt_nebula" not in left and "JC" not in left
    assert left == tuple(t for t in NINE if t not in ("mt_nebula", "JC"))  # pool order is kept


def test_an_available_template_is_found_by_name_or_id(templates):
    pool = ("JC", "6lm10a", "h3dm1")
    assert choose_available("Jebus Cross", pool, templates) == "JC"
    assert choose_available("6LM10A", pool, templates) == "6lm10a"


def test_a_template_that_is_gone_is_refused_with_the_remaining_ones(templates):
    with pytest.raises(SelectionError, match="'JC' is not available. Remaining templates: 6lm10a, h3dm1"):
        choose_available("JC", ("6lm10a", "h3dm1"), templates)


def test_an_unknown_template_is_refused_too(templates):
    with pytest.raises(SelectionError, match="not available"):
        choose_available("Nowhere", ("JC",), templates)


# --- the games ----------------------------------------------------------------------------------------------


def test_a_bo1_plays_the_template_the_decider_takes():
    actions = [Action("A", "ban", "JC"), Action("B", "ban", "6lm10a")]
    assert games(BO1, ("JC", "6lm10a", "h3dm1"), actions) == ("h3dm1",)


def test_a_bo3_plays_the_picks_in_order_then_the_decider():
    steps = sequence("A-ban B-ban A-pick B-pick decider")
    pool = ("JC", "6lm10a", "h3dm1", "Diamond", "Sapphire")
    actions = [
        Action("A", "ban", "6lm10a"),
        Action("B", "ban", "Sapphire"),
        Action("A", "pick", "JC"),
        Action("B", "pick", "Diamond"),
    ]
    assert games(steps, pool, actions) == ("JC", "Diamond", "h3dm1")


def test_the_nine_template_sequence_ends_in_three_games():
    actions = [Action(step.who, step.do, template) for step, template in zip(BO3_NINE, NINE)]
    actions = actions[:8]
    result = games(BO3_NINE, NINE, actions)
    assert result == ("h3dm1", "nostalgia", "Conquest")  # A's pick, B's pick, the template left over


def test_the_seven_template_sequence_ends_in_three_games():
    pool = NINE[:7]
    actions = [Action(step.who, step.do, template) for step, template in zip(BO3_SEVEN, pool)][:6]
    assert games(BO3_SEVEN, pool, actions) == ("mt_nebula", "mt_Jebus", "Sapphire")


def test_without_a_decider_the_picks_are_the_games():
    actions = [Action("A", "pick", "JC"), Action("B", "pick", "Diamond")]
    assert games(NO_DECIDER, ("JC", "Diamond"), actions) == ("JC", "Diamond")


def test_games_are_not_announced_before_the_end():
    with pytest.raises(SelectionError, match="not finished"):
        games(BO1, ("JC", "6lm10a", "h3dm1"), [Action("A", "ban", "JC")])


# --- replaying a thread's record -------------------------------------------------------------------------

ANNA, BORIS = 111, 222  # A and B


def test_a_clean_record_is_replayed_into_actions():
    taken = ((ANNA, "ban", "JC"), (BORIS, "ban", "6lm10a"))
    assert replay(BO1, ("JC", "6lm10a", "h3dm1"), ANNA, BORIS, taken) == [
        Action("A", "ban", "JC"),
        Action("B", "ban", "6lm10a"),
    ]


def test_no_record_replays_to_no_actions():
    assert replay(BO1, ("JC", "6lm10a", "h3dm1"), ANNA, BORIS, ()) == []


@pytest.mark.parametrize(
    "taken, problem",
    [
        (((BORIS, "ban", "JC"),), "player A's step"),  # out of turn
        (((ANNA, "pick", "JC"),), "ban is expected"),
        (((ANNA, "ban", "JC"), (BORIS, "ban", "JC")), "'JC' was not available"),
        (((ANNA, "ban", "Nowhere"),), "'Nowhere' was not available"),
        (((999, "ban", "JC"),), "not a player"),
        (((ANNA, "ban", "JC"), (BORIS, "ban", "6lm10a"), (ANNA, "ban", "h3dm1")), "finished"),
    ],
)
def test_a_record_that_breaks_the_rules_is_reported_not_trusted(taken, problem):
    with pytest.raises(SelectionError, match=f"number {len(taken)} in this thread does not follow the rules.*{problem}"):
        replay(BO1, ("JC", "6lm10a", "h3dm1"), ANNA, BORIS, taken)


# --- what the thread says after each step ------------------------------------------------------------------

MENTIONS = {"A": "<@1>", "B": "<@2>"}


def say(steps, pool, actions, templates):
    return after_a_step(steps, pool, actions, MENTIONS, templates)


def test_before_the_first_step_the_pool_and_the_first_step_are_announced(templates):
    pool = ("JC", "6lm10a", "h3dm1")
    assert say(BO1, pool, [], templates) == [
        "Remaining (3): Jebus Cross, 6lm10a, h3dm1",
        "Step 1 of 2: <@1> bans a template with /ban",
    ]


def test_after_a_ban_the_pool_shrinks_and_the_next_player_is_named(templates):
    pool = ("JC", "6lm10a", "h3dm1")
    assert say(BO1, pool, [Action("A", "ban", "6lm10a")], templates) == [
        "Remaining (2): Jebus Cross, h3dm1\nBanned: 6lm10a. Picked: none.",
        "Step 2 of 2: <@2> bans a template with /ban",
    ]


def test_a_pick_step_points_to_the_pick_command(templates):
    steps = sequence("A-pick B-pick")
    assert say(steps, ("JC", "Diamond"), [], templates)[-1] == "Step 1 of 2: <@1> picks a template with /pick"


def test_the_games_are_announced_after_the_last_step(templates):
    pool = ("JC", "6lm10a", "h3dm1")
    actions = [Action("A", "ban", "JC"), Action("B", "ban", "6lm10a")]
    assert say(BO1, pool, actions, templates)[-1] == "The bans and picks are done. The games:\nGame 1: h3dm1"


def test_a_best_of_three_lists_every_game_in_order(templates):
    steps = sequence("A-ban B-ban A-pick B-pick decider")
    pool = ("JC", "6lm10a", "h3dm1", "Diamond", "Sapphire")
    actions = [
        Action("A", "ban", "6lm10a"),
        Action("B", "ban", "Sapphire"),
        Action("A", "pick", "JC"),
        Action("B", "pick", "Diamond"),
    ]
    assert say(steps, pool, actions, templates)[-1].splitlines() == [
        "The bans and picks are done. The games:",
        "Game 1: Jebus Cross",
        "Game 2: Diamond",
        "Game 3: h3dm1",
    ]


# --- the games known before the selection is over ------------------------------------------------------------------

BO3 = sequence("A-ban B-ban A-pick B-pick decider")
FIVE = ("JC", "6lm10a", "h3dm1", "Diamond", "Sapphire")


def test_no_game_is_known_before_the_first_pick():
    assert known_games(BO3, FIVE, []) == ()
    assert known_games(BO3, FIVE, [Action("A", "ban", "6lm10a"), Action("B", "ban", "Sapphire")]) == ()


def test_a_game_is_known_as_soon_as_it_is_picked():
    actions = [Action("A", "ban", "6lm10a"), Action("B", "ban", "Sapphire"), Action("A", "pick", "JC")]
    assert known_games(BO3, FIVE, actions) == ("JC",)
    assert known_games(BO3, FIVE, actions + [Action("B", "pick", "Diamond")]) == ("JC", "Diamond", "h3dm1")


def test_the_decider_game_is_known_only_when_the_selection_is_done():
    actions = [Action("A", "ban", "6lm10a"), Action("B", "ban", "Sapphire"), Action("A", "pick", "JC")]
    assert "h3dm1" not in known_games(BO3, FIVE, actions)


def test_known_games_end_up_the_same_as_the_games_of_a_finished_selection():
    actions = [
        Action("A", "ban", "6lm10a"),
        Action("B", "ban", "Sapphire"),
        Action("A", "pick", "JC"),
        Action("B", "pick", "Diamond"),
    ]
    assert known_games(BO3, FIVE, actions) == games(BO3, FIVE, actions)


def test_without_a_decider_the_picks_are_the_known_games():
    assert known_games(NO_DECIDER, ("JC", "Diamond"), [Action("A", "pick", "JC")]) == ("JC",)
