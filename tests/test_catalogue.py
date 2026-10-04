from pathlib import Path

import pytest

from rules.catalogue import CatalogueError, load_catalogue, parse_catalogue

DATA = Path(__file__).resolve().parent.parent / "data"


def test_shipped_factions_are_the_twelve_wiki_towns():
    factions = load_catalogue(DATA / "factions.json")
    assert set(factions.ids) == {
        "castle", "rampart", "tower", "inferno", "necropolis", "dungeon",
        "stronghold", "fortress", "conflux", "cove", "factory", "bulwark",
    }


def test_shipped_templates_start_with_the_el_classico_pool():
    templates = load_catalogue(DATA / "templates.json")
    assert {"JC", "6lm10a", "h3dm1"} <= set(templates.ids)


def test_find_by_id_or_name_ignores_case():
    cat = parse_catalogue([{"id": "castle", "name": "Castle"}], "t")
    assert cat.find("CASTLE").id == "castle"
    assert cat.find(" castle ").id == "castle"
    assert cat.find("rampart") is None


def test_duplicate_ids_are_rejected():
    with pytest.raises(CatalogueError, match="duplicate"):
        parse_catalogue([{"id": "a", "name": "A"}, {"id": "A", "name": "Again"}], "t")


def test_empty_name_is_rejected():
    with pytest.raises(CatalogueError, match="empty name"):
        parse_catalogue([{"id": "a", "name": " "}], "t")


def test_empty_id_is_rejected():
    with pytest.raises(CatalogueError, match="empty id"):
        parse_catalogue([{"id": "", "name": "A"}], "t")


def test_wrong_shape_is_rejected():
    with pytest.raises(CatalogueError):
        parse_catalogue({"id": "a"}, "t")
    with pytest.raises(CatalogueError):
        parse_catalogue([{"id": "a"}], "t")
