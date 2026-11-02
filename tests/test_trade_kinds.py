"""The `trade` setting: the forms it can be written in, its defaults, and the sections each kind and mirror has."""

import pytest

from rules.trade_kinds import MAX_HERO_BANS, STANDARD_KIND, TradeKind, check_trade, kind_words, sections


def test_a_name_is_a_kind_with_default_options():
    assert check_trade("standard") == TradeKind("standard", 0, True)
    assert check_trade("standard_with_ai_packs") == TradeKind("standard_with_ai_packs")


def test_roulette_by_name_has_no_hero_bans_and_rolls_before_the_heroes():
    assert check_trade("roulette") == TradeKind("roulette", 0, True)


def test_an_object_gives_the_options_of_a_roulette():
    assert check_trade({"kind": "roulette", "hero_bans": 1, "roll_before_heroes": True}) == TradeKind("roulette", 1, True)
    assert check_trade({"kind": "roulette", "roll_before_heroes": False}) == TradeKind("roulette", 0, False)


def test_the_default_kind_is_standard():
    assert TradeKind().name == STANDARD_KIND


@pytest.mark.parametrize("value", ["mirror", "Standard", "", {"kind": "nope"}])
def test_a_kind_that_does_not_exist_lists_the_kinds(value):
    with pytest.raises(ValueError, match="standard_with_ai_packs"):
        check_trade(value)


@pytest.mark.parametrize("value", [5, None, ["roulette"], {"hero_bans": 1}])
def test_something_that_is_not_a_kind_is_refused(value):
    with pytest.raises(ValueError, match="state the kind"):
        check_trade(value)


@pytest.mark.parametrize("bans", [-1, MAX_HERO_BANS + 1, True, 1.5, "1"])
def test_hero_bans_is_a_small_whole_number(bans):
    with pytest.raises(ValueError, match="hero_bans is a whole number"):
        check_trade({"kind": "roulette", "hero_bans": bans})


def test_the_most_hero_bans_is_accepted():
    assert check_trade({"kind": "roulette", "hero_bans": MAX_HERO_BANS}).hero_bans == MAX_HERO_BANS


def test_roll_before_heroes_is_true_or_false():
    with pytest.raises(ValueError, match="true or false"):
        check_trade({"kind": "roulette", "roll_before_heroes": "yes"})


def test_heroes_cannot_be_banned_when_they_are_drawn_with_the_towns():
    with pytest.raises(ValueError, match="cannot be banned before they are drawn"):
        check_trade({"kind": "roulette", "hero_bans": 1, "roll_before_heroes": False})


def test_the_options_of_a_roulette_are_refused_on_other_kinds():
    with pytest.raises(ValueError, match="options of roulette"):
        check_trade({"kind": "standard", "hero_bans": 1})


def test_an_unknown_option_is_named():
    with pytest.raises(ValueError, match="unknown option 'bans'"):
        check_trade({"kind": "roulette", "bans": 1})


# --- the sections --------------------------------------------------------------------------------------------------


def test_the_standard_trade_has_the_town_bid_and_the_color_bid():
    assert sections(TradeKind(), mirror=False) == ("town_roll", "town_bid", "color_bid")


def test_a_mirror_has_only_the_color_bid():
    assert sections(TradeKind(), mirror=True) == ("town_roll", "color_bid")


def test_packs_add_a_bid_between_the_town_and_the_color():
    assert sections(check_trade("standard_with_ai_packs"), mirror=False) == ("town_roll", "town_bid", "pack_bid", "color_bid")


def test_packs_on_a_mirror_are_refused():
    with pytest.raises(ValueError, match="mirror"):
        sections(check_trade("standard_with_ai_packs"), mirror=True)


def test_a_roulette_without_bans_has_the_sections_of_its_town_trade():
    kind = check_trade("roulette")
    assert sections(kind, mirror=False) == ("town_roll", "town_bid", "color_bid")
    assert sections(kind, mirror=True) == ("town_roll", "first_choice_bid")


def test_hero_bans_are_a_section_of_a_roulette():
    kind = check_trade({"kind": "roulette", "hero_bans": 2})
    assert sections(kind, mirror=False) == ("town_roll", "hero_bans", "town_bid", "color_bid")
    assert sections(kind, mirror=True) == ("town_roll", "hero_bans", "first_choice_bid")


def test_heroes_drawn_with_the_towns_have_no_ban_section():
    kind = check_trade({"kind": "roulette", "roll_before_heroes": False})
    assert "hero_bans" not in sections(kind, mirror=False)


# --- the words for /info -------------------------------------------------------------------------------------------


def test_a_standard_trade_has_no_words():
    assert kind_words(TradeKind()) is None


def test_packs_are_described():
    assert kind_words(check_trade("standard_with_ai_packs")) == "computer-player packs"


@pytest.mark.parametrize(
    "value, words",
    [
        ({"kind": "roulette", "hero_bans": 1}, "roulette, 1 hero ban each, heroes drawn after the rolls"),
        ({"kind": "roulette", "hero_bans": 2}, "roulette, 2 hero bans each, heroes drawn after the rolls"),
        ("roulette", "roulette, no hero bans, heroes drawn after the rolls"),
        ({"kind": "roulette", "roll_before_heroes": False}, "roulette, no hero bans, heroes drawn with the towns"),
    ],
)
def test_a_roulette_says_its_options(value, words):
    assert kind_words(check_trade(value)) == words
