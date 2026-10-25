from pathlib import Path

import pytest

from rules.catalogue import (
    CatalogueError,
    load_catalogue,
    load_templates,
    load_towns,
    parse_catalogue,
    parse_templates,
)

DATA = Path(__file__).resolve().parent.parent / "data"


def entries(*pairs):
    return [{"id": i, "name": n} for i, n in pairs]


# --- the shipped files -------------------------------------------------------


def test_towns_file_has_the_twelve_towns_of_the_wiki():
    towns = load_towns(DATA / "towns.json")
    assert set(towns.ids) == {
        "castle", "rampart", "tower", "inferno", "necropolis", "dungeon",
        "stronghold", "fortress", "conflux", "cove", "factory", "bulwark",
    }


def test_the_templates_file_loads_and_every_template_has_a_difficulty():
    templates = load_templates(DATA / "templates.json")
    assert templates.entries and all("difficulty" in entry.details for entry in templates.entries)


# --- looking things up -----------------------------------------------------


def test_an_entry_is_found_by_id_or_by_name():
    catalogue = parse_catalogue(entries(("necropolis", "Necropolis Town")), "t.json")
    assert catalogue.find("necropolis").name == "Necropolis Town"
    assert catalogue.find("Necropolis Town").id == "necropolis"


def test_letter_case_and_surrounding_spaces_do_not_matter():
    catalogue = parse_catalogue(entries(("JC", "JC")), "t.json")
    assert catalogue.find("jc").id == "JC"
    assert catalogue.find("  Jc ").id == "JC"


def test_something_unknown_is_not_found():
    assert parse_catalogue(entries(("castle", "Castle")), "t.json").find("atlantis") is None


def test_membership_uses_the_id():
    catalogue = parse_catalogue(entries(("castle", "Castle")), "t.json")
    assert "castle" in catalogue
    assert "Castle" not in catalogue  # a name, not an id


# --- extra fields (a template's difficulty) --------------------------------------------


def with_difficulty(*rows):
    return [{"id": i, "name": n, "difficulty": d} for i, n, d in rows]


def test_extra_fields_are_kept_with_the_entry():
    catalogue = parse_catalogue(with_difficulty(("JC", "Jebus Cross", 160)), "t.json", {"difficulty": int})
    assert catalogue.find("JC").details == {"difficulty": 160}


def test_an_entry_without_a_required_extra_field_is_refused():
    with pytest.raises(CatalogueError, match='entry 1 must have exactly "id", "name", "difficulty"'):
        parse_catalogue(entries(("JC", "Jebus Cross")), "templates.json", {"difficulty": int})


def test_an_extra_field_nobody_asked_for_is_refused():
    # Towns have no difficulty: a typo or a field in the wrong file is caught.
    with pytest.raises(CatalogueError, match='entry 1 must have exactly "id", "name"$'):
        parse_catalogue(with_difficulty(("castle", "Castle", 160)), "towns.json")


@pytest.mark.parametrize("bad", ["160%", "160", 160.5, True, None])
def test_an_extra_field_of_the_wrong_kind_is_refused(bad):
    with pytest.raises(CatalogueError, match=r"entry 1 \(JC\): 'difficulty' must be a whole number"):
        parse_catalogue(with_difficulty(("JC", "Jebus Cross", bad)), "templates.json", {"difficulty": int})


# --- a template's difficulty must be a supported one ------------------------------------------------


@pytest.mark.parametrize("difficulty", [80, 100, 130, 160, 200])
def test_every_supported_difficulty_is_accepted(difficulty):
    catalogue = parse_templates(with_difficulty(("JC", "Jebus Cross", difficulty)), "templates.json")
    assert catalogue.find("JC").details["difficulty"] == difficulty


@pytest.mark.parametrize("difficulty", [0, 50, 150, 170, 250, -160])
def test_an_unsupported_difficulty_is_refused_and_the_template_named(difficulty):
    rows = with_difficulty(("JC", "Jebus Cross", 160), ("6lm10a", "6lm10a", difficulty))
    with pytest.raises(CatalogueError) as error:
        parse_templates(rows, "templates.json")
    message = str(error.value)
    assert message.startswith(f"templates.json: entry 2 (6lm10a): difficulty {difficulty} is not supported")
    assert "use one of 80%, 100%, 130%, 160%, 200%" in message


def test_the_templates_file_is_checked_when_it_is_loaded(tmp_path):
    path = tmp_path / "templates.json"
    path.write_text('[{"id": "JC", "name": "Jebus Cross", "difficulty": 150}]', encoding="utf-8")
    with pytest.raises(CatalogueError, match="templates.json: entry 1 \\(JC\\): difficulty 150 is not supported"):
        load_templates(path)


# --- bad files -------------------------------------------------------------


def test_a_repeated_id_is_refused_and_both_entries_are_located():
    with pytest.raises(CatalogueError, match="towns.json: entry 2: the id 'Castle' is already used by entry 1"):
        parse_catalogue(entries(("castle", "Castle"), ("Castle", "Other")), "towns.json")


def test_an_empty_name_is_refused_and_located():
    with pytest.raises(CatalogueError, match=r"towns.json: entry 2 \(tower\) has an empty name"):
        parse_catalogue(entries(("castle", "Castle"), ("tower", "  ")), "towns.json")


def test_an_empty_id_is_refused():
    with pytest.raises(CatalogueError, match="entry 1 has an empty id"):
        parse_catalogue(entries(("", "Castle")), "towns.json")


def test_an_entry_must_have_exactly_the_expected_fields():
    with pytest.raises(CatalogueError, match='entry 1 must have exactly "id", "name"'):
        parse_catalogue([{"id": "castle"}], "towns.json")
    with pytest.raises(CatalogueError, match="entry 1 must have exactly"):
        parse_catalogue([{"id": "castle", "name": "Castle", "extra": 1}], "towns.json")


def test_the_file_must_be_a_list_with_something_in_it():
    with pytest.raises(CatalogueError, match="non-empty list"):
        parse_catalogue({"id": "castle"}, "towns.json")
    with pytest.raises(CatalogueError, match="non-empty list"):
        parse_catalogue([], "towns.json")


def test_a_file_that_is_not_json_is_reported(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("[ not json", encoding="utf-8")
    with pytest.raises(CatalogueError, match="broken.json: not valid JSON"):
        load_catalogue(broken)
