import json
import shutil
from pathlib import Path

import pytest

from bot import load_data_or_exit
from rules.registry import RegistryError, load_registry

REPO = Path(__file__).resolve().parent.parent


def write_format(root, data):
    """Write a format file named after its id, as the repository expects."""
    (root / "formats" / f"{data['id']}.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def root(tmp_path, good_format):
    """A copy of the repository's data with one valid format, in a temporary folder to break."""
    shutil.copytree(REPO / "data", tmp_path / "data")
    (tmp_path / "formats").mkdir()
    write_format(tmp_path, good_format)
    return tmp_path


# --- the repository itself ----------------------------------------------------------------


def test_the_repository_data_loads():
    registry = load_registry(REPO)
    assert registry.towns.ids and registry.templates.ids and registry.formats


# --- a valid set of files -----------------------------------------------------------------------


def test_valid_files_are_loaded(root, good_format):
    registry = load_registry(root)
    assert list(registry.formats) == [good_format["id"]]
    assert registry.formats[good_format["id"]].phases[0].pool_ids == tuple(good_format["templates"])


# --- problems are reported in words, with the file name, all at once ------------------------------


def test_a_bad_format_is_reported_with_its_file_name(root, good_format):
    good_format["templates"] = ["JC", "nope", "h3dm1"]
    write_format(root, good_format)
    with pytest.raises(RegistryError) as error:
        load_registry(root)
    assert error.value.problems[0].startswith(f"{good_format['id']}.json: templates: unknown template 'nope'")


def test_every_bad_format_file_is_reported_not_only_the_first(root, good_format):
    broken_a = dict(good_format, id="aaa-cup", templates=["JC", "nope", "h3dm1"])
    broken_b = dict(good_format, id="bbb-cup")
    broken_b["phases"] = [dict(good_format["phases"][0], best_of=4)]
    write_format(root, broken_a)
    write_format(root, broken_b)
    with pytest.raises(RegistryError) as error:
        load_registry(root)
    files = {problem.split(":")[0] for problem in error.value.problems}
    assert files == {"aaa-cup.json", "bbb-cup.json"}


def test_a_broken_towns_file_is_reported(root):
    (root / "data" / "towns.json").write_text('[{"id": "castle"}]', encoding="utf-8")
    with pytest.raises(RegistryError) as error:
        load_registry(root)
    assert error.value.problems == ['towns.json: entry 1 must have exactly "id", "name"']


def test_both_broken_lists_are_reported_together(root):
    (root / "data" / "towns.json").write_text("[ not json", encoding="utf-8")
    (root / "data" / "templates.json").write_text("[]", encoding="utf-8")
    with pytest.raises(RegistryError) as error:
        load_registry(root)
    assert len(error.value.problems) == 2
    assert error.value.problems[0].startswith("towns.json") and error.value.problems[1].startswith("templates.json")


def test_formats_are_not_checked_when_a_list_they_need_is_broken(root):
    (root / "data" / "templates.json").write_text("[]", encoding="utf-8")
    with pytest.raises(RegistryError) as error:
        load_registry(root)
    assert all(problem.startswith("templates.json") for problem in error.value.problems)


# --- the summary line for the log ---------------------------------------------------------------


def test_the_summary_says_what_was_loaded(root, good_format):
    summary = load_registry(root).summary()
    assert summary == f"12 towns, 3 templates, 1 format ({good_format['id']})"


def test_the_summary_marks_archived_formats(root, good_format):
    old = dict(good_format, id="old-cup", status="archived")
    write_format(root, old)
    summary = load_registry(root).summary()
    assert summary.startswith("12 towns, 3 templates, 2 formats (")
    assert "old-cup (archived)" in summary and good_format["id"] in summary


# --- what the bot does when it starts ----------------------------------------------------------------


def test_the_bot_loads_valid_data_and_logs_what_it_loaded(root, good_format, caplog):
    with caplog.at_level("INFO", logger="h3bot"):
        registry = load_data_or_exit(root)
    assert registry.formats
    assert f"Data loaded: 12 towns, 3 templates, 1 format ({good_format['id']})" in caplog.text


def test_the_bot_refuses_to_start_and_says_what_is_wrong(root, good_format):
    good_format["templates"] = ["JC", "nope", "h3dm1"]
    write_format(root, good_format)
    with pytest.raises(SystemExit) as stop:
        load_data_or_exit(root)
    message = str(stop.value)
    assert message.startswith(f"Cannot start: a data file is not valid.\n  - {good_format['id']}.json:")
    assert "unknown template 'nope'" in message
