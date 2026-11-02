"""The facts a template may state in the catalogue: roads, map size and computer players with a default and what is
allowed, the recommended simultaneous turns, mirror, and where to get it."""

import pytest

from rules.catalogue import CatalogueError, Choice, parse_catalogue, parse_templates


def template(**facts):
    return {"id": "JC", "name": "Jebus Cross", "difficulty": 160, **facts}


def load(*entries):
    return parse_templates(list(entries), "templates.json")


def details(**facts):
    return load(template(**facts)).find("JC").details


def refused(match, **facts):
    with pytest.raises(CatalogueError, match=match):
        load(template(**facts))


# --- roads, map size and computer players: a default and what is allowed ----------------------------------------


def test_roads_have_a_default_and_what_is_allowed():
    roads = details(roads={"default": "mid", "allowed": ["slow", "mid", "fast", "none"]})["roads"]
    assert roads == Choice("mid", ("slow", "mid", "fast", "none"))


def test_more_than_one_road_type_together_is_a_value_too():
    roads = details(roads={"default": "slow+mid", "allowed": ["slow+mid", "none"]})["roads"]
    assert roads.default == "slow+mid"


def test_a_map_size_with_underground_is_accepted():
    sizes = details(map_size={"default": "L+U", "allowed": ["L", "L+U"]})["map_size"]
    assert sizes == Choice("L+U", ("L", "L+U"))


def test_computer_players_have_a_default_and_a_list_from_zero_to_six():
    ai = details(ai={"default": 3, "allowed": [0, 3, 6]})["ai"]
    assert ai == Choice(3, (0, 3, 6))


def test_a_default_that_is_not_allowed_is_refused():
    refused(
        r"entry 1 \(JC\): map_size: the default 'XL' must be one of the allowed values: M, L",
        map_size={"default": "XL", "allowed": ["M", "L"]},
    )


@pytest.mark.parametrize(
    "field, value, listed",
    [
        ("roads", {"default": "paved", "allowed": ["paved"]}, "none, or slow, mid and fast"),
        ("map_size", {"default": "XXL", "allowed": ["XXL"]}, "use one of S, M, L, XL, H, XH, G"),
        ("map_size", {"default": "L", "allowed": ["L", "L+X"]}, "use one of S, M, L, XL, H, XH, G"),
        ("ai", {"default": 7, "allowed": [7]}, "from 0 to 6"),
        ("ai", {"default": 3, "allowed": [3, -1]}, "from 0 to 6"),
    ],
)
def test_a_value_that_does_not_exist_is_refused_and_the_values_listed(field, value, listed):
    refused(rf"entry 1 \(JC\): {field}: .*{listed}", **{field: value})


def test_a_value_listed_twice_is_refused_and_named():
    refused(
        r"map_size: 'M' is listed twice among the allowed values",
        map_size={"default": "M", "allowed": ["M", "L", "M"]},
    )


@pytest.mark.parametrize("value", ["mid", {"default": "mid"}, {"allowed": ["mid"]}, {"default": "mid", "allowed": []}, {"default": "mid", "allowed": "mid"}, ["mid"]])
def test_a_fact_not_written_as_a_default_and_a_list_is_refused(value):
    refused(r"roads: ", roads=value)


def test_facts_that_are_not_stated_are_unknown():
    assert details() == {"difficulty": 160}


# --- a mirror template is always played with underground ---------------------------------------------------------


def test_a_mirror_template_with_underground_map_sizes_is_accepted():
    found = details(mirror=True, map_size={"default": "L+U", "allowed": ["L+U", "XL+U"]})
    assert found["mirror"] is True


def test_a_mirror_template_with_a_size_without_underground_is_refused():
    refused(
        r"map_size: a mirror template is always played with underground, but 'L' has no \+U",
        mirror=True,
        map_size={"default": "L+U", "allowed": ["L", "L+U"]},
    )


def test_an_ordinary_template_may_have_either_kind_of_map_size():
    found = details(map_size={"default": "L", "allowed": ["L", "L+U"]})
    assert "mirror" not in found
    assert details(mirror=False, map_size={"default": "L", "allowed": ["L"]})["mirror"] is False


def test_a_mirror_without_map_sizes_is_accepted():
    assert details(mirror=True)["mirror"] is True


def test_mirror_must_be_true_or_false():
    refused(r"mirror: mirror must be true or false", mirror="yes")


# --- where to get the template -----------------------------------------------------------------------------------


def test_a_template_built_into_hota():
    assert details(built_in=True)["built_in"] is True


def test_a_template_to_download_with_a_link():
    assert details(download="https://example.com/jc.h3m")["download"] == "https://example.com/jc.h3m"


def test_a_template_stating_neither_says_nothing():
    found = details()
    assert "built_in" not in found and "download" not in found


def test_stating_both_is_refused():
    refused(r"entry 1 \(JC\): state only one of built_in and download", built_in=True, download="https://example.com/jc")


@pytest.mark.parametrize("link", ["ftp://example.com/jc", "example.com/jc", "http://example.com/jc", "https://", "", 5])
def test_a_download_that_is_not_a_web_link_is_refused(link):
    refused(r"download: download must be a link starting with https://", download=link)


@pytest.mark.parametrize("value", [False, "yes", 1])
def test_built_in_stated_as_anything_but_true_is_refused_and_the_download_suggested(value):
    refused(r"built_in: built_in can only be true. To say a template has to be downloaded, give a download link", built_in=value)


# --- the recommended simultaneous turns --------------------------------------------------------------------------


@pytest.mark.parametrize("date", ["117", "121", "1214"])
def test_recommended_simultaneous_turns_are_accepted(date):
    assert details(sim_turns=date)["sim_turns"] == date


@pytest.mark.parametrize("date, problem", [("118", "the day"), ("151", "the week"), ("017", "the month"), ("week 1", "write month, week and day"), ("1-1-7", "write month")])
def test_simultaneous_turns_in_another_form_are_refused(date, problem):
    refused(rf"entry 1 \(JC\): sim_turns: .*{problem}", sim_turns=date)


# --- the loader as a whole ---------------------------------------------------------------------------------------


def test_a_field_that_is_not_known_is_still_refused_and_the_possible_ones_listed():
    refused(r'entry 1 must have "id", "name", "difficulty", and may also have "roads", "map_size", "ai"', timer="12:00+06:00+02:00")


def test_the_entry_number_and_id_are_in_the_message():
    with pytest.raises(CatalogueError, match=r"templates.json: entry 2 \(Diamond\): sim_turns: "):
        load(template(), {"id": "Diamond", "name": "Diamond", "difficulty": 160, "sim_turns": "9"})


def test_a_catalogue_without_optional_fields_still_has_to_match_exactly():
    with pytest.raises(CatalogueError, match='entry 1 must have exactly "id", "name"$'):
        parse_catalogue([{"id": "castle", "name": "Castle", "roads": "mid"}], "towns.json")
