import pytest

from rules.formats import parse_format
from rules.selection import (
    SelectionError,
    check_step,
    games,
    is_complete,
    next_actor,
    pool_text,
    progress,
    prompt,
    start_text,
    step_text,
)
from state import fold, make_event

A, B = 10, 20  # A won the coinflip

NINE = ["JC", "h3dm1", "6lm10a", "nostalgia", "mt_nebula", "mt_Jebus", "Sapphire", "Diamond", "Conquest"]
NINE_SEQUENCE = "A:ban B:ban A:pick B:pick A:ban B:ban B:ban A:ban"
SEVEN_SEQUENCE = "A:ban B:ban B:ban A:ban A:pick B:pick"


def steps_of(text):
    return [{"who": s.split(":")[0], "do": s.split(":")[1]} for s in text.split()]


class Scenario:
    """A match whose format is changed to a sequence, with helpers to play it."""

    def __init__(self, el_classico, templates, factions, pool, sequence, best_of, game_order):
        phase = el_classico["phases"][0]
        phase.update(best_of=best_of, pool=pool)
        phase["selection"] = {"type": "sequence", "steps": steps_of(sequence), "game_order": game_order}
        self.formats = {"el-classico": parse_format(el_classico, templates, factions)}
        self.templates = templates
        self.events = [
            make_event(1, "match_started", format="el-classico", phase="Main", p1=A, p2=B),
            make_event(2, "coinflip", a=A, b=B),
        ]

    @property
    def match(self):
        return fold(self.events, self.formats)

    def play(self, user, action, template):
        checked = check_step(self.match, user, action, template, self.templates)
        self.events.append(make_event(len(self.events) + 1, action, by=user, template=checked))


@pytest.fixture
def nine(el_classico, templates, factions):
    return Scenario(el_classico, templates, factions, NINE, NINE_SEQUENCE, 3, ["pick_1", "pick_2", "decider"])


@pytest.fixture
def seven(el_classico, templates, factions):
    return Scenario(
        el_classico, templates, factions, NINE[:7], SEVEN_SEQUENCE, 3, ["pick_1", "pick_2", "decider"]
    )


@pytest.fixture
def bo1(el_classico, templates, factions):
    return Scenario(el_classico, templates, factions, ["JC", "6lm10a", "h3dm1"], "A:ban B:ban", 1, ["decider"])


# --- steps follow the sequence --------------------------------------------


def test_nine_template_sequence_runs_in_order(nine):
    expected = [(A, "ban"), (B, "ban"), (A, "pick"), (B, "pick"), (A, "ban"), (B, "ban"), (B, "ban"), (A, "ban")]
    choices = ["mt_nebula", "6lm10a", "JC", "Diamond", "mt_Jebus", "nostalgia", "Sapphire", "Conquest"]
    for (user, action), template in zip(expected, choices):
        step = progress(nine.match).next_step
        assert (nine.match.user_of(step.who), step.do) == (user, action)
        assert next_actor(nine.match) == user
        nine.play(user, action, template)
    assert next_actor(nine.match) is None
    assert is_complete(nine.match)


def test_seven_template_sequence_lets_b_act_twice_in_a_row(seven):
    seven.play(A, "ban", "nostalgia")
    seven.play(B, "ban", "6lm10a")
    assert next_actor(seven.match) == B
    seven.play(B, "ban", "Sapphire")
    assert next_actor(seven.match) == A


def test_prompt_names_the_acting_player(nine):
    assert f"<@{A}> (A)" in prompt(nine.match)
    assert "ban" in prompt(nine.match)


# --- who and what ----------------------------------------------------------


def test_wrong_player_is_refused_and_told_whose_turn_it_is(nine):
    with pytest.raises(SelectionError, match=f"not your turn.*<@{A}>"):
        check_step(nine.match, B, "ban", "JC", nine.templates)
    assert progress(nine.match).banned == ()


def test_wrong_action_is_refused(nine):
    with pytest.raises(SelectionError, match="A ban is expected now, not a pick"):
        check_step(nine.match, A, "pick", "JC", nine.templates)


def test_banned_template_is_refused_with_the_remaining_ones(nine):
    nine.play(A, "ban", "mt_nebula")
    with pytest.raises(SelectionError, match="not available.*JC"):
        check_step(nine.match, B, "ban", "mt_nebula", nine.templates)


def test_unknown_template_is_refused(nine):
    with pytest.raises(SelectionError, match="not available"):
        check_step(nine.match, A, "ban", "nope", nine.templates)


def test_template_names_ignore_case(nine):
    assert check_step(nine.match, A, "ban", "mt_JEBUS", nine.templates) == "mt_Jebus"


def test_selection_that_is_finished_accepts_nothing(bo1):
    bo1.play(A, "ban", "JC")
    bo1.play(B, "ban", "h3dm1")
    with pytest.raises(SelectionError, match="finished"):
        check_step(bo1.match, A, "ban", "6lm10a", bo1.templates)


# --- remaining pool --------------------------------------------------------


def test_pool_shrinks_and_ban_is_listed(nine):
    nine.play(A, "ban", "mt_nebula")
    state = progress(nine.match)
    assert len(state.remaining) == 8 and "mt_nebula" not in state.remaining
    assert "Remaining (8)" in pool_text(nine.match)
    assert "Banned: mt_nebula" in pool_text(nine.match)


def test_picks_are_listed_separately(nine):
    for user, action, template in [(A, "ban", "mt_nebula"), (B, "ban", "6lm10a"), (A, "pick", "JC")]:
        nine.play(user, action, template)
    assert "Picked: JC" in pool_text(nine.match)


# --- ordered games ---------------------------------------------------------


def test_bo3_result_is_picks_then_decider(nine):
    for user, action, template in [
        (A, "ban", "mt_nebula"), (B, "ban", "6lm10a"), (A, "pick", "JC"), (B, "pick", "Diamond"),
        (A, "ban", "mt_Jebus"), (B, "ban", "nostalgia"), (B, "ban", "Sapphire"), (A, "ban", "Conquest"),
    ]:
        nine.play(user, action, template)
    assert [(g.number, g.template) for g in games(nine.match)] == [(1, "JC"), (2, "Diamond"), (3, "h3dm1")]


def test_game_order_from_the_format_is_respected(el_classico, templates, factions):
    reordered = Scenario(el_classico, templates, factions, NINE, NINE_SEQUENCE, 3, ["decider", "pick_2", "pick_1"])
    for user, action, template in [
        (A, "ban", "mt_nebula"), (B, "ban", "6lm10a"), (A, "pick", "JC"), (B, "pick", "Diamond"),
        (A, "ban", "mt_Jebus"), (B, "ban", "nostalgia"), (B, "ban", "Sapphire"), (A, "ban", "Conquest"),
    ]:
        reordered.play(user, action, template)
    assert [g.template for g in games(reordered.match)] == ["h3dm1", "Diamond", "JC"]


def test_bo1_result_is_the_only_template_left(bo1):
    bo1.play(A, "ban", "JC")
    bo1.play(B, "ban", "h3dm1")
    assert [(g.number, g.template) for g in games(bo1.match)] == [(1, "6lm10a")]


def test_games_before_selection_ends_are_refused(bo1):
    with pytest.raises(SelectionError, match="not finished"):
        games(bo1.match)


def test_last_step_text_announces_the_games(bo1):
    bo1.play(A, "ban", "JC")
    bo1.play(B, "ban", "h3dm1")
    text = step_text(bo1.match, B, "ban", "h3dm1")
    assert f"<@{B}> banned **h3dm1**" in text
    assert "Game 1: **6lm10a**" in text


def test_middle_step_text_shows_pool_and_next_prompt(bo1):
    bo1.play(A, "ban", "JC")
    text = step_text(bo1.match, A, "ban", "JC")
    assert "Remaining (2)" in text and f"<@{B}>" in text


def test_start_text_names_the_first_actor(nine):
    assert f"<@{A}> (A)" in start_text(nine.match)


# --- agreed templates ------------------------------------------------------


@pytest.fixture
def ranked(el_classico, templates, factions):
    el_classico["phases"][0]["selection"] = {"type": "agreed"}
    formats = {"el-classico": parse_format(el_classico, templates, factions)}
    events = [
        make_event(1, "match_started", format="el-classico", phase="Main", p1=A, p2=B, template="JC"),
        make_event(2, "coinflip", a=A, b=B),
    ]
    return fold(events, formats), templates


def test_agreed_phase_skips_selection(ranked):
    match, _ = ranked
    assert is_complete(match)
    assert [(g.number, g.template) for g in games(match)] == [(1, "JC")]
    assert "Game 1: **JC**" in start_text(match)


def test_agreed_phase_refuses_bans(ranked):
    match, templates = ranked
    with pytest.raises(SelectionError, match="no bans or picks"):
        check_step(match, A, "ban", "h3dm1", templates)
