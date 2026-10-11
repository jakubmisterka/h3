"""Shared test setup: the town and template lists, and a good format to break in different ways."""

import copy
from pathlib import Path

import pytest

from rules.catalogue import TEMPLATE_FIELDS, load_templates, load_towns, parse_catalogue

DATA = Path(__file__).resolve().parent.parent / "data"

# Templates used by tournaments in the explore session, so 7- and 9-template pools can be tested.
EXTRA_TEMPLATES = ["nostalgia", "mt_nebula", "mt_Jebus", "Sapphire", "Diamond", "Conquest"]


@pytest.fixture(scope="session")
def towns():
    return load_towns(DATA / "towns.json")


@pytest.fixture(scope="session")
def templates():
    """The shipped templates plus six more."""
    shipped = load_templates(DATA / "templates.json")
    entries = [{"id": e.id, "name": e.name, **e.details} for e in shipped.entries]
    entries += [{"id": t, "name": t, "difficulty": 160} for t in EXTRA_TEMPLATES]
    return parse_catalogue(entries, "test templates", TEMPLATE_FIELDS)


@pytest.fixture
def good_format():
    """A valid format as a fresh dict, for tests to change. It is a made-up tournament, not a real one."""
    return copy.deepcopy(
        {
            "id": "sample-cup",
            "name": "Sample Cup",
            "templates": ["JC", "6lm10a", "h3dm1"],
            "phases": [
                {
                    "name": "Main",
                    "best_of": 1,
                    "selection": {
                        "type": "sequence",
                        "steps": [{"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"do": "decider"}],
                    },
                }
            ],
        }
    )
