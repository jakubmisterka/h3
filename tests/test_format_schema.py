"""Checks formats/schema.json: it accepts a good format and rejects each kind of broken one."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "formats" / "schema.json"

# A small format written by hand: a made-up tournament, not a real one.
GOOD = {
    "id": "sample-cup",
    "name": "Sample Cup",
    "templates": ["JC", "6lm10a", "h3dm1"],
    "phases": [
        {
            "name": "Main",
            "best_of": 1,
            "template_selection": {
                "type": "sequence",
                "steps": [{"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"do": "decider"}],
            },
        }
    ],
}


@pytest.fixture(scope="module")
def validator():
    with open(SCHEMA_FILE, encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)  # the schema itself must be valid
    return Draft202012Validator(schema)


def problems(validator, data):
    return [error.message for error in validator.iter_errors(data)]


def changed(modify):
    """A copy of the good format with one thing changed."""
    data = copy.deepcopy(GOOD)
    modify(data)
    return data


def phase(data):
    return data["phases"][0]


# --- what is accepted ----------------------------------------------------------


def test_a_good_format_is_accepted(validator):
    assert problems(validator, GOOD) == []


def test_a_format_with_every_optional_field_is_accepted(validator):
    def fill(data):
        data["status"] = "archived"
        data["thread_visibility"] = "private"
        data["roll_rules"] = {"roll_cost": 300, "rolls_per_player": 2, "max_roll_bans": 1}
        data["templates"] = [{"template": "JC", "roll_rules": {"roll_cost": 0}}, "6lm10a", "h3dm1"]
        phase(data)["pool"] = ["JC", {"template": "6lm10a", "roll_rules": {"rolls_per_player": 0}}, "h3dm1"]
        data["allowed_towns"] = ["castle", "rampart", "tower"]
        phase(data)["allowed_towns"] = ["castle", "rampart"]

    assert problems(validator, changed(fill)) == []


def test_an_agreed_template_phase_is_accepted(validator):
    assert problems(validator, changed(lambda d: phase(d).update(template_selection={"type": "agreed"}))) == []


@pytest.mark.parametrize("best_of", [1, 2, 3, 5, 7, 9])
def test_the_allowed_best_of_values_are_accepted(validator, best_of):
    assert problems(validator, changed(lambda d: phase(d).update(best_of=best_of))) == []


@pytest.mark.parametrize("best_of", [0, 4, 6, 8, 10])
def test_other_best_of_values_are_rejected(validator, best_of):
    assert problems(validator, changed(lambda d: phase(d).update(best_of=best_of)))


# --- the top level ------------------------------------------------------------------


@pytest.mark.parametrize("field", ["id", "name", "templates", "phases"])
def test_a_missing_required_field_is_rejected(validator, field):
    data = copy.deepcopy(GOOD)
    del data[field]
    assert any(f"'{field}' is a required property" in p for p in problems(validator, data))


def test_a_format_with_no_phase_in_the_list_is_rejected(validator):
    assert problems(validator, changed(lambda d: d.update(phases=[])))


def test_an_unknown_field_is_rejected(validator):
    assert problems(validator, changed(lambda d: d.update(colour="red")))
    assert problems(validator, changed(lambda d: phase(d).update(timer=60)))


@pytest.mark.parametrize("bad_id", ["Sample Cup", "sample_cup", "-sample", "sample-", "Sample"])
def test_an_id_must_be_lowercase_words_joined_by_dashes(validator, bad_id):
    assert problems(validator, changed(lambda d: d.update(id=bad_id)))


def test_status_and_visibility_have_fixed_values(validator):
    assert problems(validator, changed(lambda d: d.update(status="deleted")))
    assert problems(validator, changed(lambda d: d.update(thread_visibility="secret")))


# --- the templates of the tournament and the pool of a phase -----------------------------


def test_the_tournament_needs_at_least_one_template(validator):
    assert problems(validator, changed(lambda d: d.update(templates=[])))


def test_a_phase_pool_is_optional_but_cannot_be_empty(validator):
    assert problems(validator, changed(lambda d: phase(d).update(pool=[]))) != []
    assert problems(validator, GOOD) == []  # the good example has no pool


def test_a_template_can_be_a_plain_id_or_an_object_with_settings(validator):
    data = changed(lambda d: d.update(templates=["JC", {"template": "6lm10a"}, {"template": "h3dm1", "roll_rules": {}}]))
    assert problems(validator, data) == []


@pytest.mark.parametrize("entry", [5, ["JC"], "", {"roll_rules": {}}, {"template": ""}, {"template": "JC", "timer": "x"}])
def test_a_template_entry_that_makes_no_sense_is_rejected(validator, entry):
    assert problems(validator, changed(lambda d: d.update(templates=[entry, "6lm10a", "h3dm1"])))
    assert problems(validator, changed(lambda d: phase(d).update(pool=[entry])))


def test_a_template_entry_that_is_not_an_object_says_it_wants_text(validator):
    found = problems(validator, changed(lambda d: d.update(templates=[5, "6lm10a", "h3dm1"])))
    assert any("5 is not of type 'string'" in p for p in found)


def test_a_missing_template_id_in_an_object_entry_is_named(validator):
    found = problems(validator, changed(lambda d: d.update(templates=[{"roll_rules": {}}, "6lm10a", "h3dm1"])))
    assert any("'template' is a required property" in p for p in found)


# --- towns ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("where", ["tournament", "phase"])
def test_a_town_list_cannot_be_empty_or_not_a_list(validator, where):
    def set_list(value):
        def modify(d):
            (d if where == "tournament" else phase(d))["allowed_towns"] = value

        return modify

    assert problems(validator, changed(set_list([])))
    assert problems(validator, changed(set_list(["castle"])))  # a pair needs two different towns
    assert problems(validator, changed(set_list("castle")))
    assert problems(validator, changed(set_list([5])))


# --- roll rules ----------------------------------------------------------------------------


def test_roll_rules_numbers_cannot_be_negative(validator):
    assert problems(validator, changed(lambda d: d.update(roll_rules={"roll_cost": -1})))
    assert problems(validator, changed(lambda d: d.update(roll_rules={"roll_cost": 250})))  # gold moves in hundreds
    assert problems(validator, changed(lambda d: d.update(templates=[{"template": "JC", "roll_rules": {"roll_cost": -1}}])))


def test_roll_rules_cannot_have_unknown_rules(validator):
    assert problems(validator, changed(lambda d: d.update(roll_rules={"roll_price": 300})))


@pytest.mark.parametrize("old_field", ["roll_rules", "template_overrides", "trade"])
def test_settings_that_moved_are_no_longer_accepted_on_a_phase(validator, old_field):
    # Roll rules are written for the tournament, a template in the list, or an entry of a pool.
    assert problems(validator, changed(lambda d: phase(d).update({old_field: {}})))


def test_a_difficulty_does_not_belong_in_a_format(validator):
    # Difficulty is a property of the template (data/templates.json), not of a tournament.
    assert problems(validator, changed(lambda d: d.update(roll_rules={"difficulty": 160})))
    assert problems(validator, changed(lambda d: d.update(templates=[{"template": "JC", "difficulty": 160}])))


# --- template selection -------------------------------------------------------------------------------


def test_a_step_needs_a_known_player_and_action(validator):
    def bad_player(d):
        phase(d)["template_selection"]["steps"][0]["who"] = "C"

    def bad_action(d):
        phase(d)["template_selection"]["steps"][0]["do"] = "skip"

    assert problems(validator, changed(bad_player))
    assert problems(validator, changed(bad_action))


def test_the_selection_type_must_be_known(validator):
    assert problems(validator, changed(lambda d: phase(d).update(template_selection={"type": "random"})))


def test_a_sequence_needs_its_steps(validator):
    def without_steps(d):
        del phase(d)["template_selection"]["steps"]

    assert any("'steps' is a required property" in p for p in problems(validator, changed(without_steps)))


def test_a_sequence_cannot_be_empty(validator):
    assert problems(validator, changed(lambda d: phase(d)["template_selection"].update(steps=[])))


def test_the_old_game_order_field_is_no_longer_accepted(validator):
    # The games are played in the order of the picks, then the decider: nothing to state separately.
    assert problems(validator, changed(lambda d: phase(d)["template_selection"].update(game_order=["decider"])))


def test_the_decider_step_needs_no_player(validator):
    assert problems(validator, changed(lambda d: phase(d)["template_selection"].update(steps=[{"do": "decider"}]))) == []


def test_a_ban_or_pick_without_a_player_is_rejected(validator):
    for action in ("ban", "pick"):
        steps = [{"do": action}, {"do": "decider"}]
        found = problems(validator, changed(lambda d: phase(d)["template_selection"].update(steps=steps)))
        assert any("'who' is a required property" in p for p in found)


def test_a_step_with_an_unknown_action_is_rejected(validator):
    steps = [{"who": "A", "do": "skip"}]
    assert problems(validator, changed(lambda d: phase(d)["template_selection"].update(steps=steps)))
