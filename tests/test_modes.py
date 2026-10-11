import pytest

from rules.formats import parse_format
from rules.registry import ModeError, Registry


@pytest.fixture
def registry(good_format, templates, towns):
    """Two active modes and one archived mode."""
    formats = {}
    for fid, name, status in [("sample-cup", "Sample Cup", "active"), ("second-cup", "Second Cup", "active"), ("old-cup", "Old Cup", "archived")]:
        formats[fid] = parse_format(dict(good_format, id=fid, name=name, status=status), templates, towns)
    return Registry(towns, templates, formats)


# --- the list of modes for new matches -----------------------------------------


def test_archived_modes_are_not_offered_for_new_matches(registry):
    assert [m.id for m in registry.modes_for_new_matches()] == ["sample-cup", "second-cup"]


def test_with_only_archived_modes_nothing_is_offered(registry):
    only_old = Registry(registry.towns, registry.templates, {"old-cup": registry.formats["old-cup"]})
    assert only_old.modes_for_new_matches() == []


# --- choosing a mode to start a match ---------------------------------------------


@pytest.mark.parametrize("text", ["sample-cup", "Sample Cup", "SAMPLE CUP", "  sample cup  ", "SAMPLE-CUP"])
def test_a_mode_is_found_by_id_or_name_in_any_letter_case(registry, text):
    assert registry.choose_mode(text).id == "sample-cup"


def test_an_archived_mode_is_refused_and_says_why(registry):
    with pytest.raises(ModeError, match="Old Cup is archived and cannot start new matches"):
        registry.choose_mode("old-cup")
    with pytest.raises(ModeError, match="Old Cup is archived"):
        registry.choose_mode("Old Cup")


def test_an_unknown_mode_lists_the_available_ones_without_the_archived(registry):
    with pytest.raises(ModeError) as error:
        registry.choose_mode("nope")
    message = str(error.value)
    assert "There is no mode called 'nope'" in message
    assert "Available modes: Sample Cup, Second Cup." in message
    assert "Old Cup" not in message


def test_when_no_mode_is_available_it_says_so(registry):
    only_old = Registry(registry.towns, registry.templates, {"old-cup": registry.formats["old-cup"]})
    with pytest.raises(ModeError, match="There are no modes available"):
        only_old.choose_mode("nope")


# --- looking a mode up (for /info) still finds archived ones -----------------------------


def test_an_archived_mode_can_still_be_looked_up(registry):
    fmt = registry.find_format("Old Cup")
    assert fmt is not None and not fmt.active


def test_looking_up_something_unknown_gives_nothing(registry):
    assert registry.find_format("nope") is None
