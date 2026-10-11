"""Shared test setup: the town and template lists, and a good format to break in different ways."""

import copy
from pathlib import Path

import pytest

from rules.catalogue import TEMPLATE_FIELDS, load_towns, parse_catalogue

DATA = Path(__file__).resolve().parent.parent / "data"

# A made-up list of templates for the tests, independent of data/templates.json, big enough for 7- and 9-template pools.
TEST_TEMPLATES = ["JC", "6lm10a", "h3dm1", "nostalgia", "mt_nebula", "mt_Jebus", "Sapphire", "Diamond", "Conquest"]


@pytest.fixture(scope="session")
def towns():
    return load_towns(DATA / "towns.json")


@pytest.fixture(scope="session")
def templates():
    """Nine templates, all 160% difficulty. JC is called Jebus Cross, the others by their ids."""
    entries = [
        {"id": t, "name": "Jebus Cross" if t == "JC" else t, "difficulty": 160} for t in TEST_TEMPLATES
    ]
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
                    "template_selection": {
                        "type": "sequence",
                        "steps": [{"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"do": "decider"}],
                    },
                }
            ],
        }
    )
