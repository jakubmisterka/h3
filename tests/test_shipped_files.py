"""Checks the files contributors edit (formats/ and data/), so a bad pull request fails here.

These tests are about *every* format file being correct, not about what any one file says:
formats come and go, and the rules for a valid one are tested in test_formats.py.
"""

import json
import re
from pathlib import Path

import pytest

from rules.catalogue import heroes_offered, load_heroes, load_templates, load_towns, parse_templates
from rules.formats import load_format, load_formats, validate_format

ROOT = Path(__file__).resolve().parent.parent
FORMAT_FILES = sorted(p for p in (ROOT / "formats").glob("*.json") if p.name != "schema.json")


@pytest.fixture(scope="module")
def towns():
    return load_towns(ROOT / "data" / "towns.json")


@pytest.fixture(scope="module")
def heroes(towns):
    return load_heroes(ROOT / "data" / "heroes.json", towns)


@pytest.fixture(scope="module")
def templates(heroes):
    return load_templates(ROOT / "data" / "templates.json", heroes)


def test_there_are_format_files_to_check():
    assert FORMAT_FILES, "formats/ has no format file, so these tests would check nothing"


@pytest.mark.parametrize("path", FORMAT_FILES, ids=lambda p: p.name)
def test_a_format_file_is_valid(path, templates, towns, heroes):
    # Raises with every problem found: wrong shape (including fields that do not belong), unknown
    # templates or towns, a pool that does not fit its sequence, or a file name that is not the format id.
    load_format(path, templates, towns, heroes)


def test_the_whole_folder_loads_together(templates, towns, heroes):
    assert len(load_formats(ROOT / "formats", templates, towns, heroes)) == len(FORMAT_FILES)


def test_the_example_in_the_formats_readme_is_a_valid_format(templates, towns):
    # The guide for contributors must not teach a file the bot would refuse.
    text = (ROOT / "formats" / "README.md").read_text(encoding="utf-8")
    found = re.search(r"<!-- full example -->\s*```json\n(.*?)```", text, re.DOTALL)
    assert found, "formats/README.md has no example marked with <!-- full example -->"
    assert validate_format(json.loads(found.group(1)), templates, towns) == []


def _readme_block(path, marker):
    text = (ROOT / path).read_text(encoding="utf-8")
    found = re.search(rf"<!-- {marker} -->\s*```json\n(.*?)```", text, re.DOTALL)
    assert found, f"{path} has no example marked with <!-- {marker} -->"
    return json.loads(found.group(1))


def test_the_templates_example_in_the_data_readme_is_valid():
    # The guide must not teach an entry the bot would refuse.
    parse_templates(_readme_block("data/README.md", "templates example"), "the example in data/README.md")


def test_the_settings_example_in_the_formats_readme_is_valid_for_the_templates_of_the_data_readme(towns):
    # The two guides refer to each other: the format example is checked against the templates of the data example.
    catalogue = parse_templates(_readme_block("data/README.md", "templates example"), "the example in data/README.md")
    assert validate_format(_readme_block("formats/README.md", "settings example"), catalogue, towns) == []


def test_town_names_are_single_capitalised_words(towns):
    # The thread quotes a town by its name (`Castle`), so a name is one word starting with a capital letter.
    for entry in towns.entries:
        assert re.fullmatch(r"[A-Z][A-Za-z]*", entry.name), f"town {entry.id!r} is called {entry.name!r}"


def test_every_town_has_enough_heroes_for_a_roulette(towns, heroes):
    # A mirror roulette draws two heroes of one town and each player may ban up to three of them, so every town needs
    # at least eight heroes, whatever the template leaves out.
    # What a map offers by default: not the heroes HotA bans, and on a mirror not the ones banned there either.
    plain = parse_templates([{"id": "T", "name": "T", "difficulty": 160}], "t").find("T")
    mirror = parse_templates(
        [{"id": "M", "name": "M", "difficulty": 160, "mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}}], "t"
    ).find("M")
    for town in towns.entries:
        for template, what in ((plain, "a template"), (mirror, "a mirror template")):
            count = len(heroes_offered(heroes, template, town.id))
            assert count >= 8, f"{town.name} has {count} heroes for {what} in data/heroes.json"


def test_every_hero_states_whether_it_is_a_campaign_hero_and_whether_it_is_banned_by_default(heroes):
    for hero in heroes.entries:
        assert isinstance(hero.details.get("campaign_hero"), bool) and isinstance(hero.details.get("banned_by_default"), bool), hero.id


def test_the_campaign_heroes_a_map_can_enable_are_flagged(heroes):
    flagged = {hero.id for hero in heroes.entries if hero.details.get("campaign_hero")}
    assert {"gelu", "boragus", "kilgor", "catherine", "roland", "frederick"} <= flagged
    assert "orrin" not in flagged and "sir_mullich" not in flagged


def test_heroes_link_to_the_community_wiki(heroes):
    for hero in heroes.entries:
        assert hero.details["link"].startswith("https://heroes.thelazy.net/index.php/"), hero.id


def flagged(heroes, flag):
    return {hero.name for hero in heroes.entries if hero.details.get(flag)}


def test_the_default_bans_are_those_of_the_hota_template_editor(heroes):
    # https://h3hota.com/en/template-format, section Heroes (the editor spells Kilgor "Kilgore"). Nobody plays with
    # water, so the heroes the editor bans for the water content are banned by default as well.
    campaign = {
        "Adrienne", "Catherine", "Dracon", "Gelu", "Kilgor", "Haart Lich", "Mutare", "Roland", "Mutare Drake",
        "Boragus", "Xeron", "Bidley", "Tark", "Frederick", "Tavin", "Murdoch",
    }
    others = {"Galthran", "Sir Mullich", "Thorgrim"}
    water = {"Sylvia", "Voy", "Elmore", "Haugir", "Beatrice", "Kinkeria", "Derek", "Biarma"}
    assert flagged(heroes, "campaign_hero") == campaign
    assert flagged(heroes, "banned_by_default") == campaign | others | water


def test_the_heroes_banned_on_mirror_templates_are_flagged(heroes):
    assert flagged(heroes, "banned_on_mirrors") == {
        "Grindan", "Labetha", "Luna", "Dessa", "Gunnar", "Kyrre", "Aislinn", "Deemer", "Solmyr", "Alamar", "Jeddite", "Loynis",
    }


def test_the_trade_example_in_the_formats_readme_is_valid_for_the_templates_of_the_data_readme(towns, heroes):
    catalogue = parse_templates(_readme_block("data/README.md", "templates example"), "the example in data/README.md")
    assert validate_format(_readme_block("formats/README.md", "trade example"), catalogue, towns, heroes) == []
