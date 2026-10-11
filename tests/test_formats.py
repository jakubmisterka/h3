import json

import pytest

from rules.catalogue import parse_catalogue
from rules.formats import FormatError, load_format, load_formats, parse_format, validate_format

NINE = ["JC", "h3dm1", "6lm10a", "nostalgia", "mt_nebula", "mt_Jebus", "Sapphire", "Diamond", "Conquest"]
DECIDER = {"do": "decider"}
# The knockout of the biggest tournament: A ban, B ban, A pick, B pick, A ban, B ban, B ban, A ban, decider
NINE_STEPS = [
    {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"},
    {"who": "A", "do": "pick"}, {"who": "B", "do": "pick"},
    {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "A", "do": "ban"},
    DECIDER,
]
# Another tournament with 7 templates: A ban, B ban, B ban, A ban, A pick, B pick, decider
SEVEN_STEPS = [
    {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "B", "do": "ban"},
    {"who": "A", "do": "ban"}, {"who": "A", "do": "pick"}, {"who": "B", "do": "pick"},
    DECIDER,
]


def phase_of(data):
    return data["phases"][0]


def problems(data, templates, towns):
    return validate_format(data, templates, towns)


def make_phase(data, best_of, template_ids, steps):
    """The tournament lists these templates and its only phase uses all of them."""
    data["templates"] = list(template_ids)
    phase_of(data).pop("pool", None)
    phase_of(data).update(best_of=best_of)
    phase_of(data)["template_selection"]["steps"] = steps


# --- valid formats -----------------------------------------------------------


def test_a_good_format_is_valid(good_format, templates, towns):
    assert problems(good_format, templates, towns) == []


def test_the_nine_template_best_of_3_is_valid(good_format, templates, towns):
    make_phase(good_format, 3, NINE, NINE_STEPS)
    assert problems(good_format, templates, towns) == []


def test_the_seven_template_best_of_3_is_valid(good_format, templates, towns):
    make_phase(good_format, 3, NINE[:7], SEVEN_STEPS)
    assert problems(good_format, templates, towns) == []


def test_a_best_of_7_with_six_picks_and_a_decider_is_valid(good_format, templates, towns):
    steps = [{"who": "AB"[i % 2], "do": "pick"} for i in range(6)] + [DECIDER]
    make_phase(good_format, 7, NINE[:7], steps)
    assert problems(good_format, templates, towns) == []


def test_a_best_of_2_league_phase_is_two_picks_and_no_decider(good_format, templates, towns):
    steps = [{"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "A", "do": "pick"}, {"who": "B", "do": "pick"}]
    make_phase(good_format, 2, NINE[:4], steps)
    assert problems(good_format, templates, towns) == []


def test_an_agreed_template_phase_is_valid(good_format, templates, towns):
    phase_of(good_format)["template_selection"] = {"type": "agreed"}
    assert problems(good_format, templates, towns) == []


# --- the tournament's templates and each phase's pool ------------------------


def test_a_phase_without_a_pool_uses_all_the_templates_of_the_tournament(good_format, templates, towns):
    phase = parse_format(good_format, templates, towns).phases[0]
    assert phase.pool_ids == ("JC", "6lm10a", "h3dm1")


def test_a_phase_can_select_only_some_of_the_templates(good_format, templates, towns):
    good_format["templates"] = NINE
    good_format["phases"].append(
        {"name": "Knockout", "best_of": 3, "pool": NINE, "template_selection": {"type": "sequence", "steps": NINE_STEPS}}
    )
    phase_of(good_format)["pool"] = ["JC", "6lm10a", "h3dm1"]  # the group stage uses three of the nine
    fmt = parse_format(good_format, templates, towns)
    assert fmt.phases[0].pool_ids == ("JC", "6lm10a", "h3dm1")
    assert fmt.phases[1].pool_ids == tuple(NINE)
    assert [entry.template for entry in fmt.templates] == NINE


def test_without_a_pool_the_phase_gets_the_whole_list_and_the_size_rule_applies(good_format, templates, towns):
    good_format["templates"] = NINE  # nine templates, but the phase has only 3 steps and no pool
    messages = problems(good_format, templates, towns)
    assert any("9 templates, 3 steps" in m for m in messages)


def test_a_pool_template_missing_from_the_tournament_list_is_named(good_format, templates, towns):
    phase_of(good_format)["pool"] = ["JC", "6lm10a", "Diamond"]
    messages = problems(good_format, templates, towns)
    assert any(
        "the template 'Diamond' is in the pool but not in the tournament's templates (JC, 6lm10a, h3dm1)" in m
        for m in messages
    )


def test_a_template_twice_in_a_pool_is_reported(good_format, templates, towns):
    phase_of(good_format)["pool"] = ["JC", "JC", "h3dm1"]
    assert any("the template 'JC' is in the pool more than once" in m for m in problems(good_format, templates, towns))


def test_a_template_listed_twice_in_the_tournament_is_reported(good_format, templates, towns):
    good_format["templates"] = ["JC", "JC", "h3dm1"]
    assert any("templates: the template 'JC' is listed more than once" in m for m in problems(good_format, templates, towns))


def test_an_unknown_template_is_named_with_the_known_ones(good_format, templates, towns):
    good_format["templates"] = ["JC", "6lm10a", "nope"]
    [message] = problems(good_format, templates, towns)
    assert message.startswith("templates: unknown template 'nope'") and "Known templates: JC, 6lm10a, h3dm1" in message


def test_template_ids_are_case_sensitive(good_format, templates, towns):
    good_format["templates"] = ["jc", "6lm10a", "h3dm1"]
    assert any("unknown template 'jc'" in m for m in problems(good_format, templates, towns))


def test_an_unknown_template_given_as_an_object_is_named_too(good_format, templates, towns):
    good_format["templates"] = ["JC", "6lm10a", {"template": "nope", "roll_rules": {"roll_cost": 0}}]
    assert any("unknown template 'nope'" in m for m in problems(good_format, templates, towns))


# --- settings written at each level -------------------------------------------


def test_roll_rules_are_kept_at_every_level(good_format, templates, towns):
    good_format["roll_rules"] = {"roll_cost": 300}
    good_format["templates"] = [{"template": "JC", "roll_rules": {"roll_cost": 0}}, "6lm10a", "h3dm1"]
    phase_of(good_format)["pool"] = ["JC", {"template": "6lm10a", "roll_rules": {"rolls_per_player": 2}}, "h3dm1"]
    fmt = parse_format(good_format, templates, towns)
    assert fmt.roll_rules == {"roll_cost": 300}
    assert fmt.templates[0].roll_rules == {"roll_cost": 0} and fmt.templates[1].roll_rules == {}
    pool = fmt.phases[0].pool
    assert pool[0].roll_rules == {} and pool[1].roll_rules == {"rolls_per_player": 2}


def test_without_any_roll_rules_nothing_is_written(good_format, templates, towns):
    fmt = parse_format(good_format, templates, towns)
    assert fmt.roll_rules == {} and all(entry.roll_rules == {} for entry in fmt.templates)


# --- the shape, in plain words -----------------------------------------------


def test_a_missing_field_is_named(good_format, templates, towns):
    del good_format["phases"]
    assert problems(good_format, templates, towns) == ["the file: 'phases' is a required property"]


def test_a_format_without_templates_says_so(good_format, templates, towns):
    del good_format["templates"]
    assert problems(good_format, templates, towns) == ["the file: 'templates' is a required property"]


def test_a_problem_inside_a_phase_names_the_phase_and_the_field(good_format, templates, towns):
    phase_of(good_format)["best_of"] = 4
    [message] = problems(good_format, templates, towns)
    assert message.startswith('phase "Main", best_of: 4 is not one of')


def test_a_wrong_selection_type_gets_a_clear_message(good_format, templates, towns):
    phase_of(good_format)["template_selection"] = {"type": "random"}
    [message] = problems(good_format, templates, towns)
    assert 'phase "Main", template_selection.type' in message and "'random' is not one of ['sequence', 'agreed']" in message


def test_a_ban_without_a_player_says_who_is_missing(good_format, templates, towns):
    phase_of(good_format)["template_selection"]["steps"][0] = {"do": "ban"}
    [message] = problems(good_format, templates, towns)
    assert "'who' is a required property" in message


def test_an_unknown_field_is_named(good_format, templates, towns):
    good_format["colour"] = "red"
    [message] = problems(good_format, templates, towns)
    assert "'colour' was unexpected" in message


def test_a_bad_id_comes_with_a_plain_explanation(good_format, templates, towns):
    good_format["id"] = good_format["name"]  # writing the display name as the id is the likely mistake
    [message] = problems(good_format, templates, towns)
    assert message.startswith("id: 'Sample Cup' does not match")
    assert "Lowercase words joined by dashes" in message


def test_every_shape_problem_is_reported_at_once(good_format, templates, towns):
    good_format["id"] = good_format["name"]
    phase_of(good_format)["best_of"] = 4
    phase_of(good_format)["pool"] = []
    assert len(problems(good_format, templates, towns)) == 3


# --- the rules ---------------------------------------------------------------


def test_the_pool_must_have_as_many_templates_as_there_are_steps(good_format, templates, towns):
    make_phase(good_format, 3, NINE, NINE_STEPS[:7])  # 9 templates but only 7 steps
    messages = problems(good_format, templates, towns)
    assert any("the pool must have as many templates as the sequence has steps" in m and "9 templates, 7 steps" in m for m in messages)


def test_the_number_of_games_must_match_the_best_of(good_format, templates, towns):
    phase_of(good_format)["best_of"] = 3  # but the sequence has no picks, only the decider
    assert 'phase "Main": a best-of-3 needs 3 games, but the sequence gives 1 (0 picks and a decider)' in problems(
        good_format, templates, towns
    )


def test_a_sequence_without_a_decider_needs_enough_picks(good_format, templates, towns):
    steps = [{"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "A", "do": "pick"}]
    make_phase(good_format, 3, ["JC", "6lm10a", "h3dm1"], steps)
    assert 'phase "Main": a best-of-3 needs 3 games, but the sequence gives 1 (1 pick and no decider)' in problems(
        good_format, templates, towns
    )


def test_the_decider_must_be_the_last_step(good_format, templates, towns):
    steps = [{"who": "A", "do": "ban"}, DECIDER, {"who": "B", "do": "ban"}]
    make_phase(good_format, 1, ["JC", "6lm10a", "h3dm1"], steps)
    assert 'phase "Main": the decider must be the last step' in problems(good_format, templates, towns)


def test_there_can_be_only_one_decider(good_format, templates, towns):
    steps = [{"who": "A", "do": "ban"}, DECIDER, DECIDER]
    make_phase(good_format, 2, ["JC", "6lm10a", "h3dm1"], steps)
    assert any("2 decider steps, it can have only one" in m for m in problems(good_format, templates, towns))


def test_the_decider_names_no_player(good_format, templates, towns):
    phase_of(good_format)["template_selection"]["steps"][-1] = {"who": "A", "do": "decider"}
    assert any("the decider names no player" in m for m in problems(good_format, templates, towns))


def test_an_unknown_allowed_town_is_named(good_format, templates, towns):
    phase_of(good_format)["allowed_towns"] = ["castle", "atlantis"]
    [message] = problems(good_format, templates, towns)
    assert "unknown town 'atlantis'" in message and "Known towns:" in message


def test_known_allowed_towns_are_accepted(good_format, templates, towns):
    phase_of(good_format)["allowed_towns"] = ["castle", "rampart", "tower"]
    assert problems(good_format, templates, towns) == []


def test_a_town_named_twice_is_reported(good_format, templates, towns):
    phase_of(good_format)["allowed_towns"] = ["castle", "tower", "castle"]
    [message] = problems(good_format, templates, towns)
    assert "the town 'castle' is in allowed_towns more than once" in message


def test_a_phase_that_names_no_towns_allows_every_town(good_format, templates, towns):
    phase = parse_format(good_format, templates, towns).phases[0]
    assert phase.allowed_towns == towns.ids and len(phase.allowed_towns) == 12


def test_the_tournament_can_restrict_the_towns_for_every_phase(good_format, templates, towns):
    good_format["allowed_towns"] = ["castle", "rampart"]
    fmt = parse_format(good_format, templates, towns)
    assert fmt.allowed_towns == ("castle", "rampart")
    assert fmt.phases[0].allowed_towns == ("castle", "rampart")


def test_a_phase_list_replaces_the_tournament_list(good_format, templates, towns):
    good_format["allowed_towns"] = ["castle", "rampart"]
    second = json.loads(json.dumps(phase_of(good_format)))
    second.update(name="Final", allowed_towns=["tower", "castle", "cove"])  # replaces, so it may also widen
    good_format["phases"].append(second)
    first, last = parse_format(good_format, templates, towns).phases
    assert first.allowed_towns == ("castle", "rampart")
    assert last.allowed_towns == ("tower", "castle", "cove")


def test_an_unknown_town_in_the_tournament_list_is_named(good_format, templates, towns):
    good_format["allowed_towns"] = ["castle", "atlantis"]
    [message] = problems(good_format, templates, towns)
    assert message.startswith("allowed_towns: unknown town 'atlantis'") and "Known towns:" in message


def test_a_town_named_twice_in_the_tournament_list_is_reported(good_format, templates, towns):
    good_format["allowed_towns"] = ["castle", "castle"]
    [message] = problems(good_format, templates, towns)
    assert message == "allowed_towns: the town 'castle' is in allowed_towns more than once"


def test_a_format_that_names_no_towns_allows_every_town_everywhere(good_format, templates, towns):
    fmt = parse_format(good_format, templates, towns)
    assert fmt.allowed_towns == towns.ids and fmt.phases[0].allowed_towns == towns.ids


def test_a_phase_can_restrict_the_towns(good_format, templates, towns):
    phase_of(good_format)["allowed_towns"] = ["castle", "rampart", "tower"]
    phase = parse_format(good_format, templates, towns).phases[0]
    assert phase.allowed_towns == ("castle", "rampart", "tower")


def test_each_phase_has_its_own_towns(good_format, templates, towns):
    second = json.loads(json.dumps(phase_of(good_format)))
    second["name"] = "Final"
    second["allowed_towns"] = ["castle"]
    good_format["phases"].append(second)
    first, last = parse_format(good_format, templates, towns).phases
    assert len(first.allowed_towns) == 12 and last.allowed_towns == ("castle",)


def test_a_town_added_to_the_catalogue_is_allowed_without_other_changes(good_format, templates, towns):
    entries = [{"id": e.id, "name": e.name} for e in towns.entries] + [{"id": "newtown", "name": "New Town"}]
    bigger = parse_catalogue(entries, "towns.json")
    phase = parse_format(good_format, templates, bigger).phases[0]
    assert "newtown" in phase.allowed_towns


def test_two_phases_with_the_same_name_are_reported(good_format, templates, towns):
    good_format["phases"].append(json.loads(json.dumps(phase_of(good_format))))
    assert 'two phases are called "Main"' in problems(good_format, templates, towns)


def test_every_rule_problem_is_reported_at_once(good_format, templates, towns):
    good_format["templates"] = ["JC", "6lm10a", "nope", "h3dm1"]  # an unknown template, and one too many
    phase_of(good_format)["best_of"] = 3  # but there is only a decider
    assert len(problems(good_format, templates, towns)) == 3


# --- building a Format -------------------------------------------------------


def test_parse_builds_the_objects_the_bot_uses(good_format, templates, towns):
    fmt = parse_format(good_format, templates, towns)
    assert (fmt.id, fmt.name, fmt.active, fmt.thread_visibility) == (good_format["id"], good_format["name"], True, "public")
    assert [entry.template for entry in fmt.templates] == ["JC", "6lm10a", "h3dm1"]
    phase = fmt.phases[0]
    assert phase.pool_ids == ("JC", "6lm10a", "h3dm1") and not phase.agreed
    assert [(s.who, s.do) for s in phase.steps] == [("A", "ban"), ("B", "ban"), (None, "decider")]


def test_status_and_visibility_are_read_when_given(good_format, templates, towns):
    good_format.update(status="archived", thread_visibility="private")
    fmt = parse_format(good_format, templates, towns)
    assert (fmt.active, fmt.thread_visibility) == (False, "private")


def test_an_agreed_phase_has_no_steps(good_format, templates, towns):
    phase_of(good_format)["template_selection"] = {"type": "agreed"}
    phase = parse_format(good_format, templates, towns).phases[0]
    assert phase.agreed and phase.steps == ()


def test_parse_refuses_a_bad_format_and_lists_everything(good_format, templates, towns):
    good_format["templates"] = ["JC", "nope", "h3dm1"]
    phase_of(good_format)["best_of"] = 3
    with pytest.raises(FormatError) as error:
        parse_format(good_format, templates, towns)
    assert len(error.value.errors) == 2


# --- files ----------------------------------------------------------------------


def write(folder, name, data):
    path = folder / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_a_file_is_loaded(tmp_path, good_format, templates, towns):
    path = write(tmp_path, f"{good_format['id']}.json", good_format)
    assert load_format(path, templates, towns).name == good_format["name"]


def test_errors_from_a_file_start_with_the_file_name(tmp_path, good_format, templates, towns):
    good_format["templates"] = ["JC", "nope", "h3dm1"]
    file_name = f"{good_format['id']}.json"
    path = write(tmp_path, file_name, good_format)
    with pytest.raises(FormatError) as error:
        load_format(path, templates, towns)
    assert all(message.startswith(f"{file_name}: ") for message in error.value.errors)


def test_the_file_name_must_match_the_id(tmp_path, good_format, templates, towns):
    path = write(tmp_path, "something-else.json", good_format)
    expected = f'something-else.json: the file name must match the format id "{good_format["id"]}"'
    with pytest.raises(FormatError, match=expected):
        load_format(path, templates, towns)


def test_a_file_that_is_not_json_is_reported(tmp_path, templates, towns):
    path = tmp_path / "broken.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(FormatError, match="broken.json: not valid JSON"):
        load_format(path, templates, towns)


def test_a_folder_is_loaded_by_id_and_skips_the_schema(tmp_path, good_format, templates, towns):
    write(tmp_path, f"{good_format['id']}.json", good_format)
    (tmp_path / "schema.json").write_text("{}", encoding="utf-8")
    assert list(load_formats(tmp_path, templates, towns)) == [good_format["id"]]
