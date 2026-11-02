import json

import pytest

from rules.formats import parse_format
from rules.roll_rules import DEFAULT_ROLL_RULES, RollRules, effective_roll_rules



def rules_for(good_format, templates, towns, template="JC", phase=0):
    fmt = parse_format(good_format, templates, towns)
    return effective_roll_rules(fmt, fmt.phases[phase], template)


def test_nothing_written_means_the_built_in_defaults(good_format, templates, towns):
    assert rules_for(good_format, templates, towns) == RollRules(roll_cost=500, rolls_per_player=1, max_roll_bans=2)
    assert DEFAULT_ROLL_RULES == RollRules(500, 1, 2)


def test_the_tournament_rules_apply_to_every_template(good_format, templates, towns):
    good_format["roll_rules"] = {"roll_cost": 300}
    for template in ("JC", "6lm10a", "h3dm1"):
        assert rules_for(good_format, templates, towns, template) == RollRules(300, 1, 2)


def test_a_template_in_the_list_overrides_the_tournament(good_format, templates, towns):
    good_format["roll_rules"] = {"roll_cost": 500}
    good_format["templates"] = [{"template": "JC", "roll_rules": {"roll_cost": 0}}, "6lm10a", "h3dm1"]
    assert rules_for(good_format, templates, towns, "JC").roll_cost == 0
    assert rules_for(good_format, templates, towns, "6lm10a").roll_cost == 500


def test_a_template_in_a_phase_pool_overrides_for_that_phase_only(good_format, templates, towns):
    second = json.loads(json.dumps(good_format["phases"][0]))
    second["name"] = "Final"
    second["pool"] = ["JC", {"template": "6lm10a", "roll_rules": {"rolls_per_player": 2}}, "h3dm1"]
    good_format["phases"][0]["pool"] = ["JC", "6lm10a", "h3dm1"]
    good_format["phases"].append(second)
    assert rules_for(good_format, templates, towns, "6lm10a", phase=0).rolls_per_player == 1
    assert rules_for(good_format, templates, towns, "6lm10a", phase=1).rolls_per_player == 2


def test_the_most_specific_setting_wins(good_format, templates, towns):
    good_format["roll_rules"] = {"roll_cost": 100}
    good_format["templates"] = [{"template": "JC", "roll_rules": {"roll_cost": 200}}, "6lm10a", "h3dm1"]
    good_format["phases"][0]["pool"] = [{"template": "JC", "roll_rules": {"roll_cost": 300}}, "6lm10a", "h3dm1"]
    assert rules_for(good_format, templates, towns, "JC").roll_cost == 300  # pool beats list beats tournament


def test_settings_are_merged_field_by_field(good_format, templates, towns):
    good_format["roll_rules"] = {"roll_cost": 300, "max_roll_bans": 1}
    good_format["templates"] = [{"template": "JC", "roll_rules": {"roll_cost": 0}}, "6lm10a", "h3dm1"]
    good_format["phases"][0]["pool"] = ["JC", "6lm10a", "h3dm1"]
    good_format["phases"][0]["pool"][0] = {"template": "JC", "roll_rules": {"rolls_per_player": 2}}
    # cost from the template, rolls from the pool entry, bans from the tournament
    assert rules_for(good_format, templates, towns, "JC") == RollRules(roll_cost=0, rolls_per_player=2, max_roll_bans=1)


def test_a_rule_set_to_zero_is_not_mistaken_for_missing(good_format, templates, towns):
    good_format["roll_rules"] = {"roll_cost": 0, "rolls_per_player": 0, "max_roll_bans": 0}
    assert rules_for(good_format, templates, towns) == RollRules(0, 0, 0)


def test_a_template_that_is_not_in_the_tournament_is_refused(good_format, templates, towns):
    fmt = parse_format(good_format, templates, towns)
    with pytest.raises(ValueError, match="not one of the templates of Sample Cup"):
        effective_roll_rules(fmt, fmt.phases[0], "Diamond")


def test_a_template_that_the_phase_does_not_use_is_refused(good_format, templates, towns):
    good_format["templates"] = ["JC", "6lm10a", "h3dm1", "Diamond"]
    good_format["phases"][0]["pool"] = ["JC", "6lm10a", "h3dm1"]  # Diamond is in the tournament, not in this phase
    fmt = parse_format(good_format, templates, towns)
    with pytest.raises(ValueError, match="not in the pool of the phase 'Main'"):
        effective_roll_rules(fmt, fmt.phases[0], "Diamond")
