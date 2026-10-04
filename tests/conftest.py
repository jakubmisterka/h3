import copy
import json
from pathlib import Path

import pytest

from rules.catalogue import load_catalogue, parse_catalogue

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def factions():
    return load_catalogue(ROOT / "data" / "factions.json")


@pytest.fixture(scope="session")
def templates():
    """The shipped templates plus six extra ones, so 7- and 9-template pools can be tested."""
    shipped = load_catalogue(ROOT / "data" / "templates.json")
    extra = ["nostalgia", "mt_nebula", "mt_Jebus", "Sapphire", "Diamond", "Conquest"]
    entries = [{"id": e.id, "name": e.name} for e in shipped.entries]
    entries += [{"id": t, "name": t} for t in extra if t not in shipped]
    return parse_catalogue(entries, "test templates")


@pytest.fixture
def el_classico():
    """A fresh, valid format dict that tests can change."""
    with open(ROOT / "formats" / "el-classico.json", encoding="utf-8") as f:
        return copy.deepcopy(json.load(f))
