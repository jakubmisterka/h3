import pytest

from rules.formats import DIFFICULTY_GOLD, parse_format, starting_gold, trade_settings


def settings_for(data, templates, factions, template_id="JC"):
    phase = parse_format(data, templates, factions).phases[0]
    return trade_settings(phase, template_id)


@pytest.mark.parametrize("difficulty, gold", [(80, 30000), (100, 20000), (130, 15000), (160, 10000), (200, 0)])
def test_starting_gold_follows_the_difficulty(difficulty, gold):
    assert starting_gold(difficulty) == gold


def test_gold_table_has_exactly_the_supported_difficulties():
    assert set(DIFFICULTY_GOLD) == {80, 100, 130, 160, 200}


def test_roll_defaults_apply_when_nothing_is_set(el_classico, templates, factions):
    s = settings_for(el_classico, templates, factions)
    assert (s.roll_cost, s.rolls_per_player, s.max_roll_bans) == (500, 1, 2)
    assert s.starting_gold == 10000


def test_phase_defaults_apply_to_a_template_without_overrides(el_classico, templates, factions):
    el_classico["phases"][0]["trade"].update(roll_cost=300, rolls_per_player=2)
    s = settings_for(el_classico, templates, factions, "h3dm1")
    assert (s.roll_cost, s.rolls_per_player) == (300, 2)


def test_template_override_changes_only_that_template(el_classico, templates, factions):
    el_classico["phases"][0]["template_overrides"] = {"JC": {"difficulty": 130, "roll_cost": 0}}
    jc = settings_for(el_classico, templates, factions, "JC")
    other = settings_for(el_classico, templates, factions, "6lm10a")
    assert (jc.difficulty, jc.starting_gold, jc.roll_cost) == (130, 15000, 0)
    assert (other.difficulty, other.starting_gold, other.roll_cost) == (160, 10000, 500)


def test_default_sections_below_200_are_roll_and_two_bids(el_classico, templates, factions):
    s = settings_for(el_classico, templates, factions)
    assert s.sections == ("faction_roll", "faction_bid", "color_bid")


def test_default_sections_at_200_are_only_the_color_toss(el_classico, templates, factions):
    el_classico["phases"][0]["trade"]["difficulty"] = 200
    s = settings_for(el_classico, templates, factions)
    assert s.sections == ("color_toss",)
    assert s.starting_gold == 0


def test_override_to_200_switches_the_sections_for_that_template(el_classico, templates, factions):
    el_classico["phases"][0]["template_overrides"] = {"JC": {"difficulty": 200}}
    assert settings_for(el_classico, templates, factions, "JC").sections == ("color_toss",)
    assert settings_for(el_classico, templates, factions, "h3dm1").sections[0] == "faction_roll"


def test_explicit_sections_win_over_the_default(el_classico, templates, factions):
    el_classico["phases"][0]["trade"]["sections"] = ["faction_bid", "color_bid"]
    s = settings_for(el_classico, templates, factions)
    assert s.sections == ("faction_bid", "color_bid")
