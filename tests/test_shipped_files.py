"""Checks the files contributors edit (formats/ and data/), so a bad pull request fails here.

These tests are about *every* format file being correct, not about what any one file says:
formats come and go, and the rules for a valid one are tested in test_formats.py.
"""

from pathlib import Path

import pytest

from rules.catalogue import load_templates, load_towns
from rules.formats import load_format, load_formats

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
