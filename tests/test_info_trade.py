"""/info says how the trade of a template is run when it is not the standard one, and in which phases it differs."""

import copy

import pytest

from rules.catalogue import parse_templates
from rules.formats import parse_format
from rules.info import info_reply
from rules.registry import Registry

ROULETTE = {"kind": "roulette", "hero_bans": 1}
PACKS = "standard_with_ai_packs"


def templates_with(**more):
    return parse_templates(
        [{"id": "JC", "name": "Jebus Cross", "difficulty": 160, **more}]
        + [{"id": t, "name": t, "difficulty": 160} for t in ("6lm10a", "h3dm1")],
        "templates.json",
    )


def reply(good_format, towns, catalogue, settings=None, phases=None, template="Jebus Cross", heroes=None, **data):
    fmt_data = copy.deepcopy(good_format)
    fmt_data["templates"] = [{"template": "JC", "settings": settings or {}}, "6lm10a", "h3dm1"]
    fmt_data.update(data)
    if phases:
        fmt_data["phases"] = phases
    fmt = parse_format(fmt_data, catalogue, towns, heroes)
    return info_reply(Registry(towns, catalogue, {fmt.id: fmt}), "sample-cup", template)


def two_phases(good_format, final_settings):
    groups = copy.deepcopy(good_format["phases"][0])
    final = copy.deepcopy(groups)
    groups["name"], final["name"] = "Groups", "Final"
    groups["pool"] = ["JC", "6lm10a", "h3dm1"]
    final["pool"] = [{"template": "JC", "settings": final_settings}, "6lm10a", "h3dm1"]
    return [groups, final]


def test_a_standard_trade_gets_no_line(good_format, towns):
    assert "Trade" not in reply(good_format, towns, templates_with())


def test_packs_are_said(good_format, towns):
    assert "Trade: computer-player packs" in reply(good_format, towns, templates_with(), {"trade": PACKS}).splitlines()


def test_a_roulette_says_its_bans_and_when_the_heroes_are_drawn(good_format, towns, heroes_for_info):
    text = reply(good_format, towns, templates_with(), {"trade": ROULETTE}, heroes=heroes_for_info)
    assert "Trade: roulette, 1 hero ban each, heroes drawn after the rolls" in text.splitlines()


def test_a_roulette_drawn_with_the_towns_says_so(good_format, towns, heroes_for_info):
    trade = {"kind": "roulette", "roll_before_heroes": False}
    text = reply(good_format, towns, templates_with(), {"trade": trade}, heroes=heroes_for_info)
    assert "Trade: roulette, no hero bans, heroes drawn with the towns" in text.splitlines()


def test_the_trade_stated_by_the_catalogue_is_said_too(good_format, towns):
    assert "Trade: computer-player packs" in reply(good_format, towns, templates_with(trade=PACKS)).splitlines()


def test_a_trade_that_only_one_phase_has_is_named_with_that_phase(good_format, towns, heroes_for_info):
    phases = two_phases(good_format, {"trade": ROULETTE})  # the groups keep the standard trade
    lines = reply(good_format, towns, templates_with(), phases=phases, heroes=heroes_for_info).splitlines()
    assert "Trade: roulette, 1 hero ban each, heroes drawn after the rolls (Final)" in lines


def test_the_kind_most_phases_use_is_said_once_and_the_phase_that_differs_is_named(good_format, towns):
    phases = two_phases(good_format, {"trade": "standard"})  # the catalogue gives packs; the final plays the standard trade
    lines = reply(good_format, towns, templates_with(trade=PACKS), phases=phases).splitlines()
    assert "Trade: computer-player packs" in lines and "  Final: standard" in lines


def test_a_phase_asked_for_alone_gives_its_own_trade(good_format, towns, heroes_for_info):
    phases = two_phases(good_format, {"trade": ROULETTE})
    fmt_data = copy.deepcopy(good_format)
    fmt_data["templates"] = [{"template": "JC", "settings": {}}, "6lm10a", "h3dm1"]
    fmt_data["phases"] = phases
    fmt = parse_format(fmt_data, templates_with(), towns, heroes_for_info)
    text = info_reply(Registry(towns, templates_with(), {fmt.id: fmt}), "sample-cup", "Jebus Cross", "Final")
    assert "Trade: roulette, 1 hero ban each, heroes drawn after the rolls" in text.splitlines()
    groups = info_reply(Registry(towns, templates_with(), {fmt.id: fmt}), "sample-cup", "Jebus Cross", "Groups")
    assert "Trade" not in groups


def test_a_mirror_is_said_by_the_mirror_line(good_format, towns):
    mirror = {"mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}}
    assert "Mirror: both players get the same town" in reply(good_format, towns, templates_with(**mirror))


@pytest.fixture
def heroes_for_info(towns):
    from rules.catalogue import parse_heroes

    data = [{"id": f"h{n}", "name": f"Hero{n}", "town": town, "link": "https://example.com/x"} for n, town in enumerate(towns.ids * 4)]
    return parse_heroes(data, "heroes.json", towns)
