import json

import pytest

from rules.formats import FormatError, load_format, load_formats, parse_format, validate_format

NINE = ["JC", "h3dm1", "6lm10a", "nostalgia", "mt_nebula", "mt_Jebus", "Sapphire", "Diamond", "Conquest"]
NINE_STEPS = [
    {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"},
    {"who": "A", "do": "pick"}, {"who": "B", "do": "pick"},
    {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "A", "do": "ban"},
]


def phase_of(data):
    return data["phases"][0]


def problems(data, templates, factions):
    return validate_format(data, templates, factions)


def test_shipped_el_classico_is_valid(el_classico, templates, factions):
    assert problems(el_classico, templates, factions) == []


def test_missing_phases_is_rejected(el_classico, templates, factions):
    del el_classico["phases"]
    assert any("phases" in p for p in problems(el_classico, templates, factions))


def test_unknown_field_is_rejected(el_classico, templates, factions):
    el_classico["colour"] = "red"
    assert problems(el_classico, templates, factions)


def test_pool_must_be_one_larger_than_the_sequence(el_classico, templates, factions):
    phase = phase_of(el_classico)
    phase["best_of"] = 3
    phase["pool"] = NINE
    phase["selection"]["steps"] = NINE_STEPS[:7]
    phase["selection"]["game_order"] = ["pick_1", "pick_2", "decider"]
    found = problems(el_classico, templates, factions)
    assert any("one larger than the number of steps" in p for p in found)


def test_biggest_tournament_nine_template_bo3_is_valid(el_classico, templates, factions):
    phase = phase_of(el_classico)
    phase["best_of"] = 3
    phase["pool"] = NINE
    phase["selection"]["steps"] = NINE_STEPS
    phase["selection"]["game_order"] = ["pick_1", "pick_2", "decider"]
    assert problems(el_classico, templates, factions) == []


def test_seven_template_bo3_is_valid(el_classico, templates, factions):
    phase = phase_of(el_classico)
    phase["best_of"] = 3
    phase["pool"] = NINE[:7]
    phase["selection"]["steps"] = [
        {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "B", "do": "ban"},
        {"who": "A", "do": "ban"}, {"who": "A", "do": "pick"}, {"who": "B", "do": "pick"},
    ]
    phase["selection"]["game_order"] = ["pick_1", "pick_2", "decider"]
    assert problems(el_classico, templates, factions) == []


def test_picks_must_be_one_fewer_than_best_of(el_classico, templates, factions):
    phase = phase_of(el_classico)
    phase["best_of"] = 3  # but the sequence has no picks
    phase["selection"]["game_order"] = ["pick_1", "pick_2", "decider"]
    found = problems(el_classico, templates, factions)
    assert any("needs 2 picks" in p for p in found)


def test_game_order_must_name_every_game_once(el_classico, templates, factions):
    phase_of(el_classico)["selection"]["game_order"] = ["decider", "decider"]
    found = problems(el_classico, templates, factions)
    assert any("game_order" in p for p in found)


def test_unknown_template_is_named(el_classico, templates, factions):
    phase_of(el_classico)["pool"] = ["JC", "6lm10a", "nope"]
    found = problems(el_classico, templates, factions)
    assert any("unknown template 'nope'" in p for p in found)


def test_duplicate_template_in_pool_is_rejected(el_classico, templates, factions):
    phase_of(el_classico)["pool"] = ["JC", "JC", "h3dm1"]
    assert any("twice" in p for p in problems(el_classico, templates, factions))


def test_unknown_faction_is_named(el_classico, templates, factions):
    phase_of(el_classico)["allowed_factions"] = ["castle", "atlantis"]
    found = problems(el_classico, templates, factions)
    assert any("unknown faction 'atlantis'" in p for p in found)


def test_override_for_template_outside_pool_is_rejected(el_classico, templates, factions):
    phase_of(el_classico)["template_overrides"] = {"Diamond": {"difficulty": 130}}
    assert any("not in the pool" in p for p in problems(el_classico, templates, factions))


def test_starting_gold_in_a_file_is_rejected(el_classico, templates, factions):
    phase_of(el_classico)["trade"]["starting_gold"] = 15000
    found = problems(el_classico, templates, factions)
    assert any("comes from the difficulty" in p for p in found)


def test_starting_gold_in_an_override_is_rejected(el_classico, templates, factions):
    phase_of(el_classico)["template_overrides"] = {"JC": {"starting_gold": 1}}
    found = problems(el_classico, templates, factions)
    assert any("comes from the difficulty" in p for p in found)


def test_unsupported_difficulty_is_rejected(el_classico, templates, factions):
    phase_of(el_classico)["trade"]["difficulty"] = 150
    assert any("difficulty 150 is not supported" in p for p in problems(el_classico, templates, factions))


def test_difficulty_is_required(el_classico, templates, factions):
    del phase_of(el_classico)["trade"]["difficulty"]
    assert problems(el_classico, templates, factions)


def test_agreed_phase_is_valid_for_best_of_one(el_classico, templates, factions):
    phase = phase_of(el_classico)
    phase["selection"] = {"type": "agreed"}
    assert problems(el_classico, templates, factions) == []
    assert parse_format(el_classico, templates, factions).phases[0].agreed


def test_agreed_phase_must_be_best_of_one(el_classico, templates, factions):
    phase = phase_of(el_classico)
    phase["selection"] = {"type": "agreed"}
    phase["best_of"] = 3
    assert any("best-of 1" in p for p in problems(el_classico, templates, factions))


def test_phase_names_must_differ(el_classico, templates, factions):
    el_classico["phases"].append(json.loads(json.dumps(phase_of(el_classico))))
    assert any("same name" in p for p in problems(el_classico, templates, factions))


def test_parse_raises_with_every_problem(el_classico, templates, factions):
    phase_of(el_classico)["pool"] = ["JC", "6lm10a", "nope"]
    phase_of(el_classico)["trade"]["difficulty"] = 150
    with pytest.raises(FormatError) as exc:
        parse_format(el_classico, templates, factions)
    assert len(exc.value.errors) >= 2


def test_defaults_for_visibility_and_status(el_classico, templates, factions):
    del el_classico["thread_visibility"]
    del el_classico["status"]
    fmt = parse_format(el_classico, templates, factions)
    assert fmt.thread_visibility == "public"
    assert fmt.active


def test_private_visibility_is_kept(el_classico, templates, factions):
    el_classico["thread_visibility"] = "private"
    assert parse_format(el_classico, templates, factions).thread_visibility == "private"


def test_phase_without_allowed_factions_allows_the_whole_catalogue(el_classico, templates, factions):
    fmt = parse_format(el_classico, templates, factions)
    assert set(fmt.phases[0].allowed_factions) == set(factions.ids)


def test_restricted_phase_allows_only_the_listed_factions(el_classico, templates, factions):
    phase_of(el_classico)["allowed_factions"] = ["castle", "rampart", "tower"]
    fmt = parse_format(el_classico, templates, factions)
    assert fmt.phases[0].allowed_factions == ("castle", "rampart", "tower")


def test_new_faction_is_allowed_without_other_changes(el_classico, templates, factions):
    from rules.catalogue import parse_catalogue

    bigger = parse_catalogue(
        [{"id": e.id, "name": e.name} for e in factions.entries] + [{"id": "newtown", "name": "New Town"}], "f"
    )
    fmt = parse_format(el_classico, templates, bigger)
    assert "newtown" in fmt.phases[0].allowed_factions


def test_file_name_must_match_the_id(tmp_path, el_classico, templates, factions):
    path = tmp_path / "other-name.json"
    path.write_text(json.dumps(el_classico), encoding="utf-8")
    with pytest.raises(FormatError, match="must match the id"):
        load_format(path, templates, factions)


def test_invalid_json_is_reported(tmp_path, templates, factions):
    path = tmp_path / "broken.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(FormatError, match="not valid JSON"):
        load_format(path, templates, factions)


def test_load_formats_skips_the_schema_and_keys_by_id(tmp_path, el_classico, templates, factions):
    (tmp_path / "schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "el-classico.json").write_text(json.dumps(el_classico), encoding="utf-8")
    assert list(load_formats(tmp_path, templates, factions)) == ["el-classico"]
