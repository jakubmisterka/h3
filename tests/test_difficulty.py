import pytest

from rules.difficulty import (
    ALL_RANDOM_SECTIONS,
    DIFFICULTY_GOLD,
    TRADE_SECTIONS,
    default_sections,
    starting_gold,
    supported_difficulties,
)


@pytest.mark.parametrize("difficulty, gold", [(80, 30000), (100, 20000), (130, 15000), (160, 10000), (200, 0)])
def test_starting_gold_follows_from_the_difficulty(difficulty, gold):
    assert starting_gold(difficulty) == gold


def test_there_are_exactly_these_difficulties():
    assert set(DIFFICULTY_GOLD) == {80, 100, 130, 160, 200}
    assert supported_difficulties() == "80%, 100%, 130%, 160%, 200%"


@pytest.mark.parametrize("difficulty", [0, 150, 170, 300])
def test_an_unsupported_difficulty_is_refused_with_the_supported_ones(difficulty):
    with pytest.raises(ValueError, match="not supported \\(use one of 80%, 100%, 130%, 160%, 200%\\)"):
        starting_gold(difficulty)
    with pytest.raises(ValueError, match="not supported"):
        default_sections(difficulty)


@pytest.mark.parametrize("difficulty", [80, 100, 130, 160])
def test_below_200_the_trade_is_roll_town_bid_and_color_bid(difficulty):
    assert default_sections(difficulty) == ("town_roll", "town_bid", "color_bid") == TRADE_SECTIONS


def test_at_200_only_the_color_is_tossed():
    assert default_sections(200) == ("color_toss",) == ALL_RANDOM_SECTIONS
