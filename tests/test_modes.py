import pytest

from rules.formats import ModeError, get_mode, list_modes, parse_format


@pytest.fixture
def formats(el_classico, templates, factions):
    old = dict(el_classico, id="old-cup", name="Old Cup", status="archived")
    return {
        "el-classico": parse_format(el_classico, templates, factions),
        "old-cup": parse_format(old, templates, factions),
    }


def test_archived_modes_are_not_listed(formats):
    assert [m.id for m in list_modes(formats)] == ["el-classico"]


def test_el_classico_is_listed(formats):
    assert "El Classico" in [m.name for m in list_modes(formats)]


def test_active_mode_can_be_started(formats):
    assert get_mode(formats, "el-classico").name == "El Classico"


def test_archived_mode_is_refused_and_says_so(formats):
    with pytest.raises(ModeError, match="archived"):
        get_mode(formats, "old-cup")


def test_unknown_mode_is_refused(formats):
    with pytest.raises(ModeError, match="no mode"):
        get_mode(formats, "nope")
