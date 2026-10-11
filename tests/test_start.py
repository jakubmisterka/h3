import random

import pytest

from rules.formats import parse_format
from rules.start import StartError, check_opponent, choose_phase, choose_template, coinflip

PLAYER, OTHER = 1, 2


def test_another_human_is_accepted():
    check_opponent(PLAYER, OTHER, opponent_is_bot=False)  # no error


def test_yourself_is_refused():
    with pytest.raises(StartError, match="yourself"):
        check_opponent(PLAYER, PLAYER, opponent_is_bot=False)


def test_a_bot_is_refused():
    with pytest.raises(StartError, match="bot"):
        check_opponent(PLAYER, OTHER, opponent_is_bot=True)


# --- the phase ---------------------------------------------------------------------------------


@pytest.fixture
def one_phase(good_format, templates, towns):
    return parse_format(good_format, templates, towns)


@pytest.fixture
def three_phases(good_format, templates, towns):
    main = good_format["phases"][0]
    good_format["phases"] = [dict(main, name=name) for name in ("Groups", "Knockout", "Final")]
    return parse_format(good_format, templates, towns)


def test_a_mode_with_one_phase_needs_no_phase(one_phase):
    assert choose_phase(one_phase, None).name == "Main"


def test_a_mode_with_several_phases_asks_for_one(three_phases):
    with pytest.raises(StartError, match="Groups, Knockout, Final"):
        choose_phase(three_phases, None)


def test_a_phase_is_found_by_name_ignoring_case(three_phases):
    assert choose_phase(three_phases, "knockout").name == "Knockout"


def test_an_unknown_phase_lists_the_phases(three_phases):
    with pytest.raises(StartError, match="no phase called 'Semi'.*Groups, Knockout, Final"):
        choose_phase(three_phases, "Semi")


def test_naming_the_only_phase_is_fine_and_naming_another_is_not(one_phase):
    assert choose_phase(one_phase, "Main").name == "Main"
    with pytest.raises(StartError, match="no phase called"):
        choose_phase(one_phase, "Final")


# --- the template of an agreed phase -------------------------------------------------------------


@pytest.fixture
def ranked(good_format, templates, towns):
    good_format["templates"] = ["JC", "6lm10a"]
    good_format["phases"][0]["template_selection"] = {"type": "agreed"}
    return parse_format(good_format, templates, towns).phases[0]


def test_a_phase_with_bans_needs_no_template(one_phase, templates):
    assert choose_template(one_phase.phases[0], None, templates) is None


def test_a_template_is_refused_where_bans_and_picks_choose(one_phase, templates):
    with pytest.raises(StartError, match="bans and picks"):
        choose_template(one_phase.phases[0], "JC", templates)


def test_an_agreed_phase_accepts_an_allowed_template_by_name_or_id(ranked, templates):
    assert choose_template(ranked, "Jebus Cross", templates) == "JC"
    assert choose_template(ranked, "6LM10A", templates) == "6lm10a"


def test_an_agreed_phase_requires_a_template_and_lists_the_allowed_ones(ranked, templates):
    with pytest.raises(StartError, match="Allowed: Jebus Cross, 6lm10a"):
        choose_template(ranked, None, templates)


def test_a_template_outside_the_phase_is_refused_with_the_allowed_ones(ranked, templates):
    with pytest.raises(StartError, match="'Diamond' is not allowed.*Allowed: Jebus Cross, 6lm10a"):
        choose_template(ranked, "Diamond", templates)


def test_a_template_that_does_not_exist_is_refused_too(ranked, templates):
    with pytest.raises(StartError, match="not allowed"):
        choose_template(ranked, "Nowhere", templates)


# --- the coinflip --------------------------------------------------------------------------------


def test_the_same_seed_gives_the_same_winner():
    assert coinflip(PLAYER, OTHER, random.Random(7)) == coinflip(PLAYER, OTHER, random.Random(7))


def test_the_winner_is_always_one_of_the_two_players():
    assert {coinflip(PLAYER, OTHER, random.Random(seed)) for seed in range(50)} == {PLAYER, OTHER}


def test_each_player_wins_about_half_of_many_flips():
    source = random.Random(2024)
    wins = sum(coinflip(PLAYER, OTHER, source) == PLAYER for _ in range(10_000))
    assert 4_700 < wins < 5_300


def test_without_a_random_source_it_still_flips():
    assert coinflip(PLAYER, OTHER) in (PLAYER, OTHER)
