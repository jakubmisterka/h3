"""The template reply of /info with what is played on the template: facts of the template, the timer, and what the
tournament chose, once, with only the phases that differ named."""

import copy

import pytest

from rules.catalogue import parse_templates
from rules.formats import parse_format
from rules.info import info_reply
from rules.registry import Registry

TEMPLATES = [
    {
        "id": "JC",
        "name": "Jebus Cross",
        "difficulty": 160,
        "roads": {"default": "slow+mid", "allowed": ["none", "mid", "slow+mid", "fast"]},
        "map_size": {"default": "L+U", "allowed": ["L", "L+U", "XL+U"]},
        "ai": {"default": 3, "allowed": [0, 3, 6]},
        "sim_turns": "117",
        "built_in": True,
    },
    {"id": "6lm10a", "name": "6lm10a", "difficulty": 160},
    {
        "id": "h3dm1",
        "name": "h3dm1",
        "difficulty": 160,
        "download": "https://example.com/h3dm1",
        "mirror": True,
        "map_size": {"default": "L+U", "allowed": ["L+U"]},
    },
]


@pytest.fixture(scope="module")
def catalogue():
    return parse_templates(copy.deepcopy(TEMPLATES), "templates.json")


def reply(good_format, towns, catalogue, template="Jebus Cross", mode_changes=None, phases=None, phase=None):
    data = copy.deepcopy(good_format)
    data.update(mode_changes or {})
    if phases:
        data["phases"] = phases
    fmt = parse_format(data, catalogue, towns)
    registry = Registry(towns, catalogue, {fmt.id: fmt})
    return info_reply(registry, "sample-cup", template, phase)


def lines(text):
    return text.splitlines()


def two_phases(good_format, final_pool=None):
    groups = copy.deepcopy(good_format["phases"][0])
    final = copy.deepcopy(groups)
    groups["name"], final["name"] = "Groups", "Final"
    if final_pool:
        final["pool"] = final_pool
    return [groups, final]


def test_what_is_played_from_the_templates_defaults(good_format, towns, catalogue):
    text = reply(good_format, towns, catalogue)
    assert "Built into HotA" in lines(text)
    assert "Map: L+U" in lines(text) and "Roads: slow+mid" in lines(text)
    assert "AI players: 3" in lines(text) and "Sim turns until 117" in lines(text)


def test_the_facts_follow_the_difficulty_and_the_roll_in_a_fixed_order(good_format, towns, catalogue):
    found = lines(reply(good_format, towns, catalogue, mode_changes={"settings": {"timer": "12:00+06:00+02:00"}}))
    assert found[1] == "160% difficulty" and found[2].startswith("Roll: ")
    assert found[3:] == [
        "Built into HotA",
        "Timer: 12:00+06:00+02:00",
        "Map: L+U",
        "Roads: slow+mid",
        "AI players: 3",
        "Sim turns until 117",
    ]


def test_the_timer_is_shown_compactly_and_not_spelled_out(good_format, towns, catalogue):
    text = reply(good_format, towns, catalogue, mode_changes={"settings": {"timer": "12:00+06:00+02:00"}})
    assert "Timer: 12:00+06:00+02:00" in lines(text)
    assert "at the start" not in text and "each turn" not in text


def test_what_the_tournament_chose_replaces_the_default(good_format, towns, catalogue):
    chosen = {"templates": [{"template": "JC", "settings": {"map_size": "XL+U", "ai": 6, "roads": "none", "sim_turns": "121"}}, "6lm10a", "h3dm1"]}
    found = lines(reply(good_format, towns, catalogue, mode_changes=chosen))
    assert "Map: XL+U" in found and "AI players: 6" in found and "No roads" in found and "Sim turns until 121" in found
    assert "Map: L+U" not in found and "Roads: slow+mid" not in found


def test_no_computer_players_is_said_as_such(good_format, towns, catalogue):
    chosen = {"templates": [{"template": "JC", "settings": {"ai": 0}}, "6lm10a", "h3dm1"]}
    assert "No AI players" in lines(reply(good_format, towns, catalogue, mode_changes=chosen))


def test_a_setting_that_differs_between_phases_gives_the_usual_value_and_the_phase_that_differs(good_format, towns, catalogue):
    phases = two_phases(good_format, final_pool=[{"template": "JC", "settings": {"map_size": "XL+U"}}, "6lm10a", "h3dm1"])
    found = lines(reply(good_format, towns, catalogue, phases=phases))
    at = found.index("Map: L+U")
    assert found[at + 1] == "  Final: XL+U"
    assert sum(1 for line in found if line.startswith("Map:")) == 1


def test_a_setting_that_only_a_phase_states_names_that_phase(good_format, towns, catalogue):
    phases = two_phases(good_format, final_pool=[{"template": "JC", "settings": {"timer": "15:00+06:00+02:00"}}, "6lm10a", "h3dm1"])
    found = lines(reply(good_format, towns, catalogue, phases=phases))
    assert "Timer: 15:00+06:00+02:00 (Final)" in found


def test_one_phase_of_a_template_shows_that_phase_only(good_format, towns, catalogue):
    phases = two_phases(good_format, final_pool=[{"template": "JC", "settings": {"map_size": "XL+U"}}, "6lm10a", "h3dm1"])
    final = lines(reply(good_format, towns, catalogue, phases=phases, phase="Final"))
    groups = lines(reply(good_format, towns, catalogue, phases=phases, phase="Groups"))
    assert "Map: XL+U" in final and not any(line.startswith("  ") for line in final)
    assert "Map: L+U" in groups


def test_a_template_to_download_gives_the_link(good_format, towns, catalogue):
    assert "Download: <https://example.com/h3dm1>" in lines(reply(good_format, towns, catalogue, template="h3dm1"))


def test_a_mirror_template_says_both_players_get_the_same_town(good_format, towns, catalogue):
    assert "Mirror: both players get the same town" in lines(reply(good_format, towns, catalogue, template="h3dm1"))


def test_an_ordinary_template_does_not_say_mirror(good_format, towns, catalogue):
    assert not any("Mirror" in line for line in lines(reply(good_format, towns, catalogue)))


def test_a_template_with_nothing_stated_and_no_timer_has_the_reply_it_always_had(good_format, towns, catalogue):
    assert lines(reply(good_format, towns, catalogue, template="6lm10a")) == [
        "**6lm10a** in Sample Cup",
        "160% difficulty",
        "Roll: 500 gold, 1 per player, up to 2 towns banned",
    ]


def test_the_tournaments_timer_is_shown_even_for_a_template_that_states_nothing(good_format, towns, catalogue):
    found = lines(reply(good_format, towns, catalogue, template="6lm10a", mode_changes={"settings": {"timer": "10:00+05:00+01:00"}}))
    assert found[-1] == "Timer: 10:00+05:00+01:00"


def test_a_200_percent_template_shows_its_facts_too(good_format, towns):
    all_random = parse_templates(
        [{"id": "JC", "name": "Jebus Cross", "difficulty": 200, "map_size": {"default": "M", "allowed": ["M"]}}, {"id": "6lm10a", "name": "6lm10a", "difficulty": 160}, {"id": "h3dm1", "name": "h3dm1", "difficulty": 160}],
        "templates.json",
    )
    found = lines(reply(good_format, towns, all_random))
    assert "No roll: the trade is only a toss for color." in found and "Map: M" in found
