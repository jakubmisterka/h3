"""Settings in format files: where they can be written, what is checked, and how they stack on a template's defaults."""

import copy

import pytest

from rules.catalogue import parse_templates
from rules.formats import FormatError, parse_format, shape_problems, validate_format
from rules.template_settings import Settings, effective_settings

TEMPLATES = [
    {
        "id": "JC",
        "name": "Jebus Cross",
        "difficulty": 160,
        "roads": {"default": "mid", "allowed": ["slow", "mid", "fast", "none"]},
        "map_size": {"default": "L", "allowed": ["M", "L", "XL"]},
        "ai": {"default": 3, "allowed": [0, 3, 6]},
        "sim_turns": "117",
        "built_in": True,
    },
    {"id": "6lm10a", "name": "6lm10a", "difficulty": 160},
    {"id": "Diamond", "name": "Diamond", "difficulty": 160},
    {"id": "h3dm1", "name": "h3dm1", "difficulty": 160, "download": "https://example.com/h3dm1", "mirror": True,
     "map_size": {"default": "L+U", "allowed": ["L+U", "XL+U"]}},
]


@pytest.fixture(scope="module")
def catalogue():
    return parse_templates(copy.deepcopy(TEMPLATES), "templates.json")


def make(good_format, **changes):
    data = copy.deepcopy(good_format)
    for key, value in changes.items():
        data[key] = value
    return data


def problems(good_format, towns, catalogue, **changes):
    return validate_format(make(good_format, **changes), catalogue, towns)


def listed(*entries):
    return list(entries)


def two_phases(good_format):
    """A format with a group phase and a final, both using JC, 6lm10a and h3dm1."""
    first = copy.deepcopy(good_format["phases"][0])
    second = copy.deepcopy(first)
    first["name"], second["name"] = "Groups", "Final"
    return [first, second]


# --- where settings can be written and what is checked ----------------------------------------------------------


def test_a_format_without_settings_is_unchanged(good_format, towns, catalogue):
    assert problems(good_format, towns, catalogue) == []
    fmt = parse_format(good_format, catalogue, towns)
    assert fmt.settings == {} and fmt.templates[0].settings == {}


def test_a_timer_and_simultaneous_turns_can_be_set_for_the_whole_tournament(good_format, towns, catalogue):
    data = make(good_format, settings={"timer": "12:00+06:00+02:00", "sim_turns": "121"})
    assert validate_format(data, catalogue, towns) == []
    assert parse_format(data, catalogue, towns).settings == {"timer": "12:00+06:00+02:00", "sim_turns": "121"}


@pytest.mark.parametrize("setting", [{"map_size": "L"}, {"roads": "mid"}, {"ai": 3}])
def test_roads_map_size_and_computer_players_cannot_be_set_for_the_whole_tournament(good_format, towns, catalogue, setting):
    messages = problems(good_format, towns, catalogue, settings=setting)
    assert len(messages) == 1
    assert "can only be chosen for a template" in messages[0]


def test_a_template_in_the_list_can_have_all_five_settings(good_format, towns, catalogue):
    templates = listed(
        {"template": "JC", "settings": {"timer": "15:00+06:00+02:00", "sim_turns": "121", "roads": "fast", "map_size": "XL", "ai": 6}},
        "6lm10a",
        "h3dm1",
    )
    data = make(good_format, templates=templates)
    assert validate_format(data, catalogue, towns) == []
    assert parse_format(data, catalogue, towns).templates[0].settings["map_size"] == "XL"


def test_a_template_in_a_phase_pool_can_have_settings_too(good_format, towns, catalogue):
    phase = good_format["phases"][0]
    phase["pool"] = [{"template": "JC", "settings": {"ai": 0}}, "6lm10a", "h3dm1"]
    assert problems(good_format, towns, catalogue) == []
    assert parse_format(good_format, catalogue, towns).phases[0].pool[0].settings == {"ai": 0}


def test_an_unknown_setting_is_refused_by_the_schema(good_format, towns, catalogue):
    messages = problems(good_format, towns, catalogue, settings={"colour": "red"})
    assert any("colour" in message for message in messages)
    templates = listed({"template": "JC", "settings": {"weather": "rain"}}, "6lm10a", "h3dm1")
    assert any("weather" in message for message in problems(good_format, towns, catalogue, templates=templates))


def test_computer_players_must_be_a_whole_number_from_zero_to_six_in_the_shape(good_format, towns, catalogue):
    for bad in (7, -1, 2.5, "3"):
        data = make(good_format, templates=listed({"template": "JC", "settings": {"ai": bad}}, "6lm10a", "h3dm1"))
        assert shape_problems(data), bad


@pytest.mark.parametrize(
    "setting, where_text, problem",
    [
        ({"timer": "12 minutes"}, "settings: timer: ", "a timer is written like 12:00+06:00+02:00"),
        ({"timer": "12:00+6:00+02:00"}, "settings: timer: ", "two digits everywhere"),
        ({"timer": "12:75+06:00+02:00"}, "settings: timer: ", "seconds must be below 60"),
        ({"sim_turns": "118"}, "settings: sim_turns: ", "the day"),
        ({"sim_turns": "1-1-7"}, "settings: sim_turns: ", "write month, week and day in digits"),
    ],
)
def test_a_value_in_the_wrong_form_is_reported_with_where_it_is_and_what_to_write(good_format, towns, catalogue, setting, where_text, problem):
    messages = problems(good_format, towns, catalogue, settings=setting)
    assert len(messages) == 1 and messages[0].startswith(where_text) and problem in messages[0]


def test_the_place_of_a_bad_value_names_the_template_or_the_phase(good_format, towns, catalogue):
    in_list = listed({"template": "JC", "settings": {"timer": "bad"}}, "6lm10a", "h3dm1")
    assert problems(good_format, towns, catalogue, templates=in_list)[0].startswith("templates, JC: settings: timer: ")
    good_format["phases"][0]["pool"] = [{"template": "JC", "settings": {"sim_turns": "bad"}}, "6lm10a", "h3dm1"]
    assert problems(good_format, towns, catalogue)[0].startswith('phase "Main", JC: settings: sim_turns: ')


# --- what a tournament may choose ---------------------------------------------------------------------------------


def test_an_allowed_choice_passes(good_format, towns, catalogue):
    templates = listed({"template": "JC", "settings": {"map_size": "XL", "roads": "none", "ai": 6}}, "6lm10a", "h3dm1")
    assert problems(good_format, towns, catalogue, templates=templates) == []


def test_a_choice_that_is_not_allowed_names_the_template_the_setting_and_what_is_allowed(good_format, towns, catalogue):
    templates = listed({"template": "JC", "settings": {"map_size": "H"}}, "6lm10a", "h3dm1")
    [message] = problems(good_format, towns, catalogue, templates=templates)
    assert message == "templates, JC: settings: map_size: 'H' is not allowed for 'JC'. Allowed: M, L, XL"


def test_computer_players_not_among_the_allowed_numbers_are_refused(good_format, towns, catalogue):
    templates = listed({"template": "JC", "settings": {"ai": 4}}, "6lm10a", "h3dm1")
    [message] = problems(good_format, towns, catalogue, templates=templates)
    assert "'JC'. Allowed: 0, 3, 6" in message


def test_roads_not_among_the_allowed_ones_are_refused(good_format, towns, catalogue):
    templates = listed({"template": "JC", "settings": {"roads": "slow+mid"}}, "6lm10a", "h3dm1")
    [message] = problems(good_format, towns, catalogue, templates=templates)
    assert "roads: 'slow+mid' is not allowed for 'JC'. Allowed: slow, mid, fast, none" in message


def test_a_template_that_states_nothing_allowed_cannot_have_that_chosen(good_format, towns, catalogue):
    templates = listed("JC", {"template": "6lm10a", "settings": {"roads": "mid"}}, "h3dm1")
    [message] = problems(good_format, towns, catalogue, templates=templates)
    assert message == (
        "templates, 6lm10a: settings: roads cannot be chosen, because the template '6lm10a' states no allowed roads "
        "in the template catalogue"
    )


def test_any_valid_date_can_be_chosen_for_simultaneous_turns_and_any_valid_timer(good_format, towns, catalogue):
    templates = listed({"template": "6lm10a", "settings": {"sim_turns": "121", "timer": "10:00+05:00+01:00"}}, "JC", "h3dm1")
    assert problems(good_format, towns, catalogue, templates=templates) == []


def test_every_problem_is_reported_at_once(good_format, towns, catalogue):
    templates = listed({"template": "JC", "settings": {"map_size": "H", "roads": "paved"}}, "6lm10a", "h3dm1")
    assert len(problems(good_format, towns, catalogue, templates=templates, settings={"timer": "x"})) == 3


def test_a_format_with_a_bad_setting_does_not_load(good_format, towns, catalogue):
    with pytest.raises(FormatError, match="map_size: 'H' is not allowed"):
        parse_format(make(good_format, templates=listed({"template": "JC", "settings": {"map_size": "H"}}, "6lm10a", "h3dm1")), catalogue, towns)


# --- stacking on the template's defaults ---------------------------------------------------------------------------


def settings_of(good_format, towns, catalogue, template="JC", phase=0, **changes):
    fmt = parse_format(make(good_format, **changes), catalogue, towns)
    return effective_settings(fmt, fmt.phases[phase], template, catalogue)


def test_the_templates_defaults_are_used_when_nothing_is_chosen(good_format, towns, catalogue):
    assert settings_of(good_format, towns, catalogue) == Settings(
        roads="mid", map_size="L", ai=3, sim_turns="117", built_in=True
    )


def test_a_template_that_states_nothing_has_nothing_known(good_format, towns, catalogue):
    assert settings_of(good_format, towns, catalogue, template="6lm10a") == Settings()


def test_the_tournaments_timer_applies_to_every_template(good_format, towns, catalogue):
    for template in ("JC", "6lm10a", "h3dm1"):
        found = settings_of(good_format, towns, catalogue, template=template, settings={"timer": "12:00+06:00+02:00"})
        assert found.timer == "12:00+06:00+02:00"


def test_the_tournaments_sim_turns_replace_the_templates(good_format, towns, catalogue):
    found = settings_of(good_format, towns, catalogue, settings={"sim_turns": "121"})
    assert found.sim_turns == "121"


def test_a_choice_in_the_list_replaces_the_default_only_for_that_template(good_format, towns, catalogue):
    templates = listed({"template": "JC", "settings": {"roads": "fast"}}, "6lm10a", "h3dm1")
    assert settings_of(good_format, towns, catalogue, templates=templates).roads == "fast"
    assert settings_of(good_format, towns, catalogue, templates=templates, template="h3dm1").roads is None


def test_a_choice_in_a_phase_pool_wins_over_the_list_and_applies_to_that_phase_only(good_format, towns, catalogue):
    good_format["phases"] = two_phases(good_format)
    good_format["phases"][1]["pool"] = [{"template": "JC", "settings": {"ai": 6, "map_size": "XL"}}, "6lm10a", "h3dm1"]
    templates = listed({"template": "JC", "settings": {"map_size": "M"}}, "6lm10a", "h3dm1")
    groups = settings_of(good_format, towns, catalogue, templates=templates, phase=0)
    final = settings_of(good_format, towns, catalogue, templates=templates, phase=1)
    assert (groups.ai, groups.map_size) == (3, "M")  # the default number of players, the list's map size
    assert (final.ai, final.map_size) == (6, "XL")  # the pool wins


def test_another_timer_in_a_phase_wins_over_the_tournaments(good_format, towns, catalogue):
    good_format["phases"] = two_phases(good_format)
    good_format["phases"][1]["pool"] = [{"template": "JC", "settings": {"timer": "15:00+06:00+02:00"}}, "6lm10a", "h3dm1"]
    groups = settings_of(good_format, towns, catalogue, phase=0, settings={"timer": "12:00+06:00+02:00"})
    final = settings_of(good_format, towns, catalogue, phase=1, settings={"timer": "12:00+06:00+02:00"})
    assert groups.timer == "12:00+06:00+02:00" and final.timer == "15:00+06:00+02:00"


def test_the_facts_of_the_template_come_along(good_format, towns, catalogue):
    found = settings_of(good_format, towns, catalogue, template="h3dm1")
    assert found.mirror and found.download == "https://example.com/h3dm1" and not found.built_in
    assert found.map_size == "L+U"


def test_a_template_the_catalogue_does_not_have_has_no_settings(good_format, towns, catalogue):
    fmt = parse_format(make(good_format), catalogue, towns)
    with pytest.raises(ValueError, match="'Atlantis' is not a template of the catalogue"):
        effective_settings(fmt, fmt.phases[0], "Atlantis", catalogue)


def test_a_template_the_format_does_not_use_has_no_settings_in_it(good_format, towns, catalogue):
    fmt = parse_format(make(good_format), catalogue, towns)
    with pytest.raises(ValueError, match="'Diamond' is not one of the templates of Sample Cup"):
        effective_settings(fmt, fmt.phases[0], "Diamond", catalogue)
