import json
import random

import pytest

from rules.formats import parse_format
from rules.start import StartError, check_player, coinflip, plan_start

P1, P2 = 1, 2


@pytest.fixture
def single(el_classico, templates, factions):
    return parse_format(el_classico, templates, factions)


@pytest.fixture
def multi(el_classico, templates, factions):
    second = json.loads(json.dumps(el_classico["phases"][0]))
    second["name"] = "Knockout"
    el_classico["phases"].append(second)
    return parse_format(el_classico, templates, factions)


@pytest.fixture
def ranked(el_classico, templates, factions):
    el_classico["id"] = "ranked"
    el_classico["phases"][0]["selection"] = {"type": "agreed"}
    return parse_format(el_classico, templates, factions)


def start(fmt, templates, phase=None, template=None, opponent=P2, bot=False):
    return plan_start(fmt, phase, template, templates, P1, opponent, bot)


# --- opponent --------------------------------------------------------------


def test_normal_start(single, templates):
    plan = start(single, templates)
    assert plan.phase.name == "Main" and plan.template is None


def test_cannot_play_yourself(single, templates):
    with pytest.raises(StartError, match="yourself"):
        start(single, templates, opponent=P1)


def test_cannot_play_a_bot(single, templates):
    with pytest.raises(StartError, match="bot"):
        start(single, templates, bot=True)


# --- phase -----------------------------------------------------------------


def test_single_phase_mode_needs_no_phase(single, templates):
    assert start(single, templates).phase.name == "Main"


def test_single_phase_mode_accepts_its_own_phase_name(single, templates):
    assert start(single, templates, phase="main").phase.name == "Main"


def test_single_phase_mode_refuses_another_phase(single, templates):
    with pytest.raises(StartError, match="single phase"):
        start(single, templates, phase="Knockout")


def test_multi_phase_mode_asks_for_the_phase(multi, templates):
    with pytest.raises(StartError, match="Which phase.*Main, Knockout"):
        start(multi, templates)


def test_multi_phase_mode_picks_the_named_phase(multi, templates):
    assert start(multi, templates, phase="knockout").phase.name == "Knockout"


def test_multi_phase_mode_refuses_an_unknown_phase(multi, templates):
    with pytest.raises(StartError, match="not a phase"):
        start(multi, templates, phase="Finals")


# --- agreed template -------------------------------------------------------


def test_ranked_start_with_an_allowed_template(ranked, templates):
    plan = start(ranked, templates, template="jc")  # case does not matter
    assert plan.template == "JC"


def test_ranked_start_without_a_template_lists_the_allowed_ones(ranked, templates):
    with pytest.raises(StartError, match="Allowed templates: JC, 6lm10a, h3dm1"):
        start(ranked, templates)


def test_ranked_start_with_a_template_outside_the_pool(ranked, templates):
    with pytest.raises(StartError, match="not allowed here"):
        start(ranked, templates, template="Diamond")


def test_ranked_start_with_an_unknown_template(ranked, templates):
    with pytest.raises(StartError, match="not allowed here"):
        start(ranked, templates, template="nope")


def test_sequence_mode_refuses_a_named_template(single, templates):
    with pytest.raises(StartError, match="bans and picks"):
        start(single, templates, template="JC")


# --- coinflip --------------------------------------------------------------


class Fixed:
    def __init__(self, value):
        self.value = value

    def randrange(self, n):
        return self.value


def test_coinflip_with_a_fixed_source():
    assert coinflip(P1, P2, Fixed(0)) == (P1, P2)
    assert coinflip(P1, P2, Fixed(1)) == (P2, P1)


def test_each_player_can_win():
    winners = {coinflip(P1, P2, random.Random(seed))[0] for seed in range(20)}
    assert winners == {P1, P2}


def test_coinflip_is_fair():
    rng = random.Random(42)
    wins = sum(coinflip(P1, P2, rng)[0] == P1 for _ in range(10000))
    assert 4700 < wins < 5300


def test_production_coinflip_returns_both_players():
    assert sorted(coinflip(P1, P2)) == [P1, P2]


# --- only the players ------------------------------------------------------


def test_players_are_accepted():
    check_player((P1, P2), P1)
    check_player((P1, P2), P2)


def test_outsider_is_refused():
    with pytest.raises(StartError, match="Only the two players"):
        check_player((P1, P2), 99)
