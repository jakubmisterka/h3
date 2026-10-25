"""Checks the files contributors edit (formats/ and data/), so a bad pull request fails here.

These tests are about *every* format file being correct, not about what any one file says:
formats come and go, and the rules for a valid one are tested in test_formats.py.
"""

import json
import re
from pathlib import Path

import pytest

from rules.catalogue import load_templates, load_towns, parse_templates
from rules.formats import load_format, load_formats, validate_format

ROOT = Path(__file__).resolve().parent.parent
FORMAT_FILES = sorted(p for p in (ROOT / "formats").glob("*.json") if p.name != "schema.json")


@pytest.fixture(scope="module")
def templates():
    return load_templates(ROOT / "data" / "templates.json")


@pytest.fixture(scope="module")
def towns():
    return load_towns(ROOT / "data" / "towns.json")


def test_there_are_format_files_to_check():
    assert FORMAT_FILES, "formats/ has no format file, so these tests would check nothing"


@pytest.mark.parametrize("path", FORMAT_FILES, ids=lambda p: p.name)
def test_a_format_file_is_valid(path, templates, towns):
    # Raises with every problem found: wrong shape (including fields that do not belong), unknown
    # templates or towns, a pool that does not fit its sequence, or a file name that is not the format id.
    load_format(path, templates, towns)


def test_the_whole_folder_loads_together(templates, towns):
    assert len(load_formats(ROOT / "formats", templates, towns)) == len(FORMAT_FILES)


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
