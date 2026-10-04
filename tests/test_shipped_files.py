"""Checks every file contributors can edit, so a bad pull request fails here."""

from pathlib import Path

from rules.catalogue import load_catalogue
from rules.formats import load_formats, trade_settings

ROOT = Path(__file__).resolve().parent.parent


def test_every_shipped_format_is_valid():
    templates = load_catalogue(ROOT / "data" / "templates.json")
    factions = load_catalogue(ROOT / "data" / "factions.json")
    formats = load_formats(ROOT / "formats", templates, factions)
    assert "el-classico" in formats


def test_el_classico_leaves_one_template_and_ten_thousand_gold():
    templates = load_catalogue(ROOT / "data" / "templates.json")
    factions = load_catalogue(ROOT / "data" / "factions.json")
    phase = load_formats(ROOT / "formats", templates, factions)["el-classico"].phases[0]

    bans = sum(1 for s in phase.steps if s.do == "ban")
    assert (phase.best_of, len(phase.pool) - bans) == (1, 1)
    assert [(s.who, s.do) for s in phase.steps] == [("A", "ban"), ("B", "ban")]
    assert trade_settings(phase, "JC").starting_gold == 10000
    assert len(phase.allowed_factions) == 12
