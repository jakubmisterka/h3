"""The `trade` setting in the template catalogue and in a format file: where it can be written, how it stacks, and the
checks that a kind can work."""

import copy

import pytest

from rules.catalogue import CatalogueError, parse_templates
from rules.formats import FormatError, parse_format
from rules.template_settings import effective_settings
from rules.trade_kinds import TradeKind, check_trade

PACKS = "standard_with_ai_packs"
ROULETTE = {"kind": "roulette", "hero_bans": 1}


def catalogue_of(**trade_by_template):
    """JC, 6lm10a and h3dm1, with the trade (and the mirror fact) the test gives them."""
    entries = [{"id": t, "name": t, "difficulty": 160} for t in ("JC", "6lm10a", "h3dm1")]
    for entry in entries:
        entry.update(trade_by_template.get(entry["id"], {}))
    return parse_templates(entries, "templates.json")


def format_of(good_format, templates=None, phases=None, **more):
    data = copy.deepcopy(good_format)
    if templates is not None:
        data["templates"] = templates
    if phases is not None:
        data["phases"] = phases
    data.update(more)
    return data


def kind_in(fmt, catalogue, template="JC", phase=0):
    return effective_settings(fmt, fmt.phases[phase], template, catalogue).trade


# --- the catalogue -------------------------------------------------------------------------------------------------


def test_a_template_may_state_its_trade():
    assert catalogue_of(JC={"trade": PACKS}).find("JC").details["trade"] == check_trade(PACKS)


def test_a_template_may_state_a_roulette_with_options():
    assert catalogue_of(JC={"trade": ROULETTE}).find("JC").details["trade"] == TradeKind("roulette", 1, True)


def test_a_template_without_a_trade_states_none():
    assert "trade" not in catalogue_of().find("JC").details


def test_a_bad_kind_in_the_catalogue_names_the_template_and_lists_the_kinds():
    with pytest.raises(CatalogueError, match=r"entry 1 \(JC\): trade: 'dance' is not a kind of trade.*roulette"):
        catalogue_of(JC={"trade": "dance"})


def test_a_mirror_template_cannot_have_packs():
    with pytest.raises(CatalogueError, match=r"entry 3 \(h3dm1\): trade: a mirror template cannot have computer-player packs"):
        catalogue_of(h3dm1={"mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}, "trade": PACKS})


def test_a_mirror_template_can_be_a_roulette():
    entry = catalogue_of(h3dm1={"mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}, "trade": ROULETTE}).find("h3dm1")
    assert entry.details["trade"].name == "roulette"


# --- the format file ----------------------------------------------------------------------------------------------


def test_nothing_stated_is_the_standard_trade(good_format, towns):
    fmt = parse_format(format_of(good_format), catalogue_of(), towns)
    assert kind_in(fmt, catalogue_of()) == TradeKind()


def test_a_template_states_its_kind_and_a_format_leaves_it(good_format, towns):
    catalogue = catalogue_of(JC={"trade": PACKS})
    fmt = parse_format(format_of(good_format), catalogue, towns)
    assert kind_in(fmt, catalogue).name == PACKS


def test_a_template_in_the_list_replaces_the_kind_of_the_catalogue(good_format, towns):
    catalogue = catalogue_of(JC={"trade": PACKS})
    data = format_of(good_format, templates=[{"template": "JC", "settings": {"trade": ROULETTE}}, "6lm10a", "h3dm1"])
    assert kind_in(parse_format(data, catalogue, towns), catalogue) == TradeKind("roulette", 1, True)


def test_the_kind_can_differ_in_one_phase(good_format, towns):
    groups = copy.deepcopy(good_format["phases"][0])
    final = copy.deepcopy(groups)
    groups["name"], final["name"] = "Groups", "Final"
    final["pool"] = [{"template": "JC", "settings": {"trade": ROULETTE}}, "6lm10a", "h3dm1"]
    groups["pool"] = ["JC", "6lm10a", "h3dm1"]
    catalogue = catalogue_of()
    fmt = parse_format(format_of(good_format, phases=[groups, final]), catalogue, towns)
    assert kind_in(fmt, catalogue, phase=0).name == "standard"
    assert kind_in(fmt, catalogue, phase=1).name == "roulette"


def test_a_roulette_written_as_an_object_has_the_defaults(good_format, towns):
    catalogue = catalogue_of()
    data = format_of(good_format, templates=[{"template": "JC", "settings": {"trade": {"kind": "roulette"}}}, "6lm10a", "h3dm1"])
    assert kind_in(parse_format(data, catalogue, towns), catalogue) == TradeKind("roulette", 0, True)


def test_a_kind_that_does_not_exist_in_a_format_lists_the_kinds(good_format, towns):
    data = format_of(good_format, templates=[{"template": "JC", "settings": {"trade": "dance"}}, "6lm10a", "h3dm1"])
    with pytest.raises(FormatError, match="not a kind of trade"):
        parse_format(data, catalogue_of(), towns)


def test_the_trade_cannot_be_chosen_for_the_whole_tournament(good_format, towns):
    with pytest.raises(FormatError, match="can only be chosen for a template"):
        parse_format(format_of(good_format, settings={"trade": "roulette"}), catalogue_of(), towns)


def test_a_shape_that_is_not_a_kind_is_refused(good_format, towns):
    data = format_of(good_format, templates=[{"template": "JC", "settings": {"trade": {"kind": "roulette", "hero_bans": 4}}}, "6lm10a", "h3dm1"])
    with pytest.raises(FormatError):
        parse_format(data, catalogue_of(), towns)


# --- the checks that a kind can work ------------------------------------------------------------------------------


def test_packs_on_a_mirror_template_are_refused_in_a_format(good_format, towns):
    catalogue = catalogue_of(h3dm1={"mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}})
    data = format_of(good_format, templates=["JC", "6lm10a", {"template": "h3dm1", "settings": {"trade": PACKS}}])
    with pytest.raises(FormatError, match=r"h3dm1.*trade: a mirror template cannot have computer-player packs"):
        parse_format(data, catalogue, towns)


def test_hero_bans_without_the_rolls_first_are_refused(good_format, towns):
    trade = {"kind": "roulette", "hero_bans": 1, "roll_before_heroes": False}
    data = format_of(good_format, templates=[{"template": "JC", "settings": {"trade": trade}}, "6lm10a", "h3dm1"])
    with pytest.raises(FormatError, match="cannot be banned before they are drawn"):
        parse_format(data, catalogue_of(), towns)


def test_packs_need_eight_allowed_towns(good_format, towns):
    data = format_of(good_format, allowed_towns=list(towns.ids[:7]))
    data["templates"] = [{"template": "JC", "settings": {"trade": PACKS}}, "6lm10a", "h3dm1"]
    with pytest.raises(FormatError, match=r'phase "Main", JC: trade: computer-player packs need at least eight allowed towns.*allows 7'):
        parse_format(data, catalogue_of(), towns)


def test_packs_with_eight_allowed_towns_are_accepted(good_format, towns):
    data = format_of(good_format, allowed_towns=list(towns.ids[:8]))
    data["templates"] = [{"template": "JC", "settings": {"trade": PACKS}}, "6lm10a", "h3dm1"]
    parse_format(data, catalogue_of(), towns)


def test_packs_stated_by_the_catalogue_also_need_eight_towns(good_format, towns):
    data = format_of(good_format, allowed_towns=list(towns.ids[:5]))
    with pytest.raises(FormatError, match="at least eight allowed towns"):
        parse_format(data, catalogue_of(JC={"trade": PACKS}), towns)


def test_a_phase_with_its_own_towns_is_checked_on_its_own(good_format, towns):
    data = format_of(good_format)
    data["phases"][0]["allowed_towns"] = list(towns.ids[:4])
    data["templates"] = [{"template": "JC", "settings": {"trade": PACKS}}, "6lm10a", "h3dm1"]
    with pytest.raises(FormatError, match="allows 4"):
        parse_format(data, catalogue_of(), towns)
