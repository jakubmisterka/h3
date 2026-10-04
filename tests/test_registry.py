from pathlib import Path

from rules.registry import load_registry

ROOT = Path(__file__).resolve().parent.parent


def test_repository_data_loads():
    registry = load_registry(ROOT)
    assert "el-classico" in registry.formats
    assert len(registry.factions.entries) == 12


def test_find_format_by_id_or_name_ignoring_case():
    registry = load_registry(ROOT)
    assert registry.find_format("EL CLASSICO").id == "el-classico"
    assert registry.find_format("el-classico").id == "el-classico"
    assert registry.find_format("nope") is None
