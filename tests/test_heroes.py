"""The hero catalogue (`data/heroes.json`), the heroes a template does not offer (`banned_heroes`), and the checks a
format needs the heroes for: a roulette draws heroes, so every town it may draw from must have enough of them."""

import copy
import json
from pathlib import Path

import pytest

from rules.catalogue import Catalogue, CatalogueError, heroes_offered, load_heroes, load_towns, parse_heroes, parse_templates
from rules.formats import FormatError, parse_format
from rules.registry import Registry, RegistryError, load_registry

ROOT = Path(__file__).resolve().parent.parent


def hero(hero_id, town="castle", name=None, link=None):
    return {"id": hero_id, "name": name or hero_id.capitalize(), "town": town, "link": f"https://example.com/{hero_id}" if link is None else link}


def heroes_of(towns_and_counts):
    """A hero catalogue with the given number of heroes in each town: {"castle": 3, "tower": 2}."""
    data = [hero(f"{town}{n}", town) for town, count in towns_and_counts.items() for n in range(count)]
    return parse_heroes(data, "heroes.json", TOWNS)


TOWNS = None  # set by the fixture below, so the module-level helper can use the real town catalogue


@pytest.fixture(autouse=True)
def _towns(towns):
    global TOWNS
    TOWNS = towns


# --- the catalogue ---------------------------------------------------------------------------------------------------


def test_a_valid_hero_catalogue_is_accepted(towns):
    catalogue = parse_heroes([hero("orrin", "castle"), hero("solmyr", "tower")], "heroes.json", towns)
    assert catalogue.find("Orrin").details == {"town": "castle", "link": "https://example.com/orrin"}


def test_a_hero_of_an_unknown_town_names_the_hero_and_the_town(towns):
    with pytest.raises(CatalogueError, match=r"entry 2 \(solmyr\): town: unknown town 'atlantis'"):
        parse_heroes([hero("orrin"), hero("solmyr", "atlantis")], "heroes.json", towns)


def test_a_repeated_id_is_refused(towns):
    with pytest.raises(CatalogueError, match="already used by entry 1"):
        parse_heroes([hero("orrin"), hero("Orrin", name="Another")], "heroes.json", towns)


def test_a_repeated_name_is_refused(towns):
    with pytest.raises(CatalogueError, match=r"entry 2 \(orrin2\): the name 'Orrin' is already used by entry 1"):
        parse_heroes([hero("orrin"), hero("orrin2", name="Orrin")], "heroes.json", towns)


@pytest.mark.parametrize("link", ["http://example.com/orrin", "example.com", "https://", ""])
def test_a_link_that_is_not_an_https_link_is_refused(towns, link):
    with pytest.raises(CatalogueError, match="link: must be a web link starting with https://"):
        parse_heroes([hero("orrin", link=link)], "heroes.json", towns)


def test_a_hero_needs_a_town_and_a_link(towns):
    with pytest.raises(CatalogueError, match='must have "id", "name", "town", "link", and may also have "campaign_hero"'):
        parse_heroes([{"id": "orrin", "name": "Orrin"}], "heroes.json", towns)


def test_a_repository_without_the_file_has_no_heroes(towns, tmp_path):
    assert load_heroes(tmp_path / "heroes.json", towns).entries == ()


# --- banned_heroes -------------------------------------------------------------------------------------------------------


def template(**more):
    return {"id": "JC", "name": "Jebus Cross", "difficulty": 160, **more}


def test_a_template_may_list_the_heroes_its_map_does_not_offer_by_id_or_by_name():
    heroes = parse_heroes([hero("orrin"), hero("solmyr", "tower")], "heroes.json", TOWNS)
    catalogue = parse_templates([template(banned_heroes=["orrin", "Solmyr"])], "templates.json", heroes)
    assert catalogue.find("JC").details["banned_heroes"] == ("orrin", "solmyr")  # kept as ids


def test_an_unknown_banned_hero_names_the_template_and_the_hero():
    heroes = parse_heroes([hero("orrin")], "heroes.json", TOWNS)
    with pytest.raises(CatalogueError, match=r"entry 1 \(JC\): banned_heroes: unknown hero 'nobody'"):
        parse_templates([template(banned_heroes=["orrin", "nobody"])], "templates.json", heroes)


def test_a_hero_listed_twice_by_id_and_by_name_is_refused():
    heroes = parse_heroes([hero("o1", name="Orrin")], "heroes.json", TOWNS)
    with pytest.raises(CatalogueError, match="Orrin is listed twice"):
        parse_templates([template(banned_heroes=["o1", "Orrin"])], "templates.json", heroes)


def test_a_hero_written_twice_in_the_same_way_is_refused():
    with pytest.raises(CatalogueError, match="'ORRIN' is listed twice"):
        parse_templates([template(banned_heroes=["orrin", "ORRIN"])], "templates.json")


def test_an_empty_list_of_banned_heroes_is_refused():
    with pytest.raises(CatalogueError, match="at least one hero"):
        parse_templates([template(banned_heroes=[])], "templates.json")


def test_a_template_without_banned_heroes_states_none():
    assert "banned_heroes" not in parse_templates([template()], "templates.json").find("JC").details


def test_without_a_hero_catalogue_the_list_is_not_checked_and_with_an_empty_one_it_is():
    parse_templates([template(banned_heroes=["orrin"])], "templates.json")  # nothing to check against
    with pytest.raises(CatalogueError, match="unknown hero"):
        parse_templates([template(banned_heroes=["orrin"])], "templates.json", Catalogue([]))


# --- the checks of a format ---------------------------------------------------------------------------------------------

MIRROR = {"mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}}


def roulette_format(good_format, towns_allowed=("castle", "tower", "cove"), trade="roulette", template_id="JC"):
    data = copy.deepcopy(good_format)
    data["allowed_towns"] = list(towns_allowed)
    data["templates"] = [{"template": template_id, "settings": {"trade": trade}}, "6lm10a", "h3dm1"]
    return data


def catalogue_with(**more):
    return parse_templates(
        [template(**more), {"id": "6lm10a", "name": "6lm10a", "difficulty": 160}, {"id": "h3dm1", "name": "h3dm1", "difficulty": 160}],
        "templates.json",
    )


def test_a_roulette_needs_heroes(good_format, towns):
    with pytest.raises(FormatError, match=r'phase "Main", JC: trade: a roulette draws heroes, but data/heroes.json has none'):
        parse_format(roulette_format(good_format), catalogue_with(), towns, Catalogue([]))


def test_a_roulette_with_enough_heroes_is_accepted(good_format, towns):
    heroes = heroes_of({"castle": 2, "tower": 2, "cove": 2})
    parse_format(roulette_format(good_format, trade={"kind": "roulette", "hero_bans": 0}), catalogue_with(), towns, heroes)


def test_a_town_with_too_few_heroes_is_named(good_format, towns):
    heroes = heroes_of({"castle": 5, "tower": 2, "cove": 5})
    data = roulette_format(good_format, trade={"kind": "roulette", "hero_bans": 1})
    with pytest.raises(FormatError, match=r"Tower has 2 heroes left for JC, but a roulette with 1 hero bans each needs at least 3"):
        parse_format(data, catalogue_with(), towns, heroes)


def test_a_mirror_needs_two_heroes_and_the_most_the_players_could_ban(good_format, towns):
    heroes = heroes_of({"castle": 5, "tower": 5, "cove": 5})
    data = roulette_format(good_format, trade={"kind": "roulette", "hero_bans": 2})
    parse_format(data, catalogue_with(), towns, heroes)  # a pair of towns: 1 + 2 * 2 = 5 heroes are enough
    with pytest.raises(FormatError, match="needs at least 6"):
        parse_format(data, catalogue_with(**MIRROR), towns, heroes)  # a mirror draws two: 2 + 2 * 2 = 6


def test_the_heroes_a_template_does_not_offer_do_not_count(good_format, towns):
    heroes = heroes_of({"castle": 3, "tower": 3, "cove": 3})
    banned = ["castle0", "castle1"]
    data = roulette_format(good_format, trade={"kind": "roulette", "hero_bans": 1})
    parse_format(data, catalogue_with(), towns, heroes)
    with pytest.raises(FormatError, match="Castle has 1 heroes left for JC"):
        parse_format(data, catalogue_with(banned_heroes=banned), towns, heroes)


def test_only_the_towns_a_phase_allows_are_checked(good_format, towns):
    heroes = heroes_of({"castle": 5, "tower": 5})  # Cove has none, but the phase does not allow it
    parse_format(roulette_format(good_format, towns_allowed=("castle", "tower"), trade={"kind": "roulette", "hero_bans": 1}), catalogue_with(), towns, heroes)
    with pytest.raises(FormatError, match="Cove has 0 heroes"):
        parse_format(roulette_format(good_format, trade={"kind": "roulette", "hero_bans": 1}), catalogue_with(), towns, heroes)


def test_a_format_without_a_roulette_does_not_need_heroes(good_format, towns):
    data = copy.deepcopy(good_format)
    parse_format(data, catalogue_with(), towns, Catalogue([]))
    parse_format(data, catalogue_with(), towns)


def test_a_roulette_is_not_checked_when_no_heroes_are_given_to_the_check(good_format, towns):
    parse_format(roulette_format(good_format), catalogue_with(), towns)


def test_a_roulette_stated_by_the_catalogue_is_checked_too(good_format, towns):
    data = copy.deepcopy(good_format)
    with pytest.raises(FormatError, match="a roulette draws heroes"):
        parse_format(data, catalogue_with(trade="roulette"), towns, Catalogue([]))


# --- the registry and the shipped data ----------------------------------------------------------------------------------


def write_root(tmp_path, heroes, templates):
    (tmp_path / "data").mkdir()
    (tmp_path / "formats").mkdir()
    (tmp_path / "formats" / "schema.json").write_text((ROOT / "formats" / "schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "data" / "towns.json").write_text((ROOT / "data" / "towns.json").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "data" / "templates.json").write_text(json.dumps(templates), encoding="utf-8")
    if heroes is not None:
        (tmp_path / "data" / "heroes.json").write_text(json.dumps(heroes), encoding="utf-8")
    shipped = (ROOT / "formats" / "mp2026.json").read_text(encoding="utf-8")
    return shipped


def test_the_registry_loads_the_heroes_and_checks_the_banned_ones_against_them(tmp_path):
    write_root(tmp_path, [hero("orrin")], [template(banned_heroes=["Orrin"])])
    registry = load_registry(tmp_path)
    assert registry.heroes.find("orrin") is not None
    assert registry.templates.find("JC").details["banned_heroes"] == ("orrin",)


def test_the_registry_reports_a_banned_hero_that_does_not_exist(tmp_path):
    write_root(tmp_path, [hero("orrin")], [template(banned_heroes=["nobody"])])
    with pytest.raises(RegistryError, match="unknown hero 'nobody'"):
        load_registry(tmp_path)


def test_the_registry_reports_a_bad_hero_file(tmp_path):
    write_root(tmp_path, [hero("orrin", "atlantis")], [template()])
    with pytest.raises(RegistryError, match="unknown town 'atlantis'"):
        load_registry(tmp_path)


def test_a_registry_without_heroes_loads(tmp_path):
    write_root(tmp_path, None, [template()])
    assert load_registry(tmp_path).heroes.entries == ()


def test_a_registry_built_by_hand_has_no_heroes(towns, templates):
    assert Registry(towns, templates, {}).heroes.entries == ()


# --- campaign heroes ---------------------------------------------------------------------------------------------------------


def campaign(hero_id, town="tower"):
    return {**hero(hero_id, town), "campaign_hero": True, "banned_by_default": True}


def test_a_hero_may_be_flagged_as_a_campaign_hero(towns):
    catalogue = parse_heroes([campaign("gelu", "rampart"), hero("orrin")], "heroes.json", towns)
    assert catalogue.find("gelu").details["campaign_hero"] is True
    assert "campaign_hero" not in catalogue.find("orrin").details  # left out means false


def test_the_flag_may_be_stated_as_false(towns):
    catalogue = parse_heroes([{**hero("orrin"), "campaign_hero": False}], "heroes.json", towns)
    assert catalogue.find("orrin").details["campaign_hero"] is False
    assert heroes_offered(catalogue, parse_templates([template()], "t").find("JC"), "castle") == list(catalogue.entries)


@pytest.mark.parametrize("value", ["yes", 1, None])
def test_the_flag_is_true_or_false(towns, value):
    with pytest.raises(CatalogueError, match="campaign_hero must be true or false"):
        parse_heroes([{**hero("gelu"), "campaign_hero": value}], "heroes.json", towns)


def test_a_template_may_allow_campaign_heroes_by_id_or_name():
    heroes = parse_heroes([campaign("gelu", "rampart"), campaign("bora", "stronghold")], "heroes.json", TOWNS)
    catalogue = parse_templates([template(allowed_heroes=["gelu", "Bora"])], "templates.json", heroes)
    assert catalogue.find("JC").details["allowed_heroes"] == ("gelu", "bora")


def test_allowing_a_hero_who_is_not_banned_by_default_is_refused():
    heroes = parse_heroes([hero("orrin")], "heroes.json", TOWNS)
    with pytest.raises(CatalogueError, match=r"entry 1 \(JC\): allowed_heroes: Orrin is not banned by default"):
        parse_templates([template(allowed_heroes=["orrin"])], "templates.json", heroes)


def test_allowing_an_unknown_hero_is_refused():
    heroes = parse_heroes([campaign("gelu", "rampart")], "heroes.json", TOWNS)
    with pytest.raises(CatalogueError, match="allowed_heroes: unknown hero 'nobody'"):
        parse_templates([template(allowed_heroes=["nobody"])], "templates.json", heroes)


def test_a_hero_cannot_be_both_banned_and_allowed():
    heroes = parse_heroes([campaign("gelu", "rampart")], "heroes.json", TOWNS)
    with pytest.raises(CatalogueError, match="Gelu is both in banned_heroes and in allowed_heroes"):
        parse_templates([template(banned_heroes=["gelu"], allowed_heroes=["gelu"])], "templates.json", heroes)


def offered(catalogue, heroes, town):
    return sorted(h.id for h in heroes_offered(heroes, catalogue.find("JC"), town))


def test_a_map_leaves_out_the_campaign_heroes_unless_the_template_allows_them():  # they are banned by default
    heroes = parse_heroes([hero("a1"), hero("a2"), campaign("c1", "castle"), campaign("c2", "castle"), hero("t1", "tower")], "heroes.json", TOWNS)
    plain = parse_templates([template()], "templates.json", heroes)
    assert offered(plain, heroes, "castle") == ["a1", "a2"]
    allowing = parse_templates([template(allowed_heroes=["c1"])], "templates.json", heroes)
    assert offered(allowing, heroes, "castle") == ["a1", "a2", "c1"]
    assert offered(allowing, heroes, "tower") == ["t1"]


def test_the_banned_heroes_are_left_out_of_what_a_map_offers():
    heroes = parse_heroes([hero("a1"), hero("a2"), campaign("c1", "castle")], "heroes.json", TOWNS)
    catalogue = parse_templates([template(banned_heroes=["a1"], allowed_heroes=["c1"])], "templates.json", heroes)
    assert offered(catalogue, heroes, "castle") == ["a2", "c1"]


def test_the_campaign_heroes_count_for_a_roulette_only_when_allowed(good_format, towns):
    data = [hero("t1", "tower"), campaign("t2", "tower"), campaign("t3", "tower"), hero("c1"), hero("c2"), hero("c3"), hero("v1", "cove"), hero("v2", "cove"), hero("v3", "cove")]
    heroes = parse_heroes(data, "heroes.json", TOWNS)
    trade = {"kind": "roulette", "hero_bans": 1}
    fmt = roulette_format(good_format, trade=trade)
    plain = parse_templates([template(), {"id": "6lm10a", "name": "6lm10a", "difficulty": 160}, {"id": "h3dm1", "name": "h3dm1", "difficulty": 160}], "t", heroes)
    with pytest.raises(FormatError, match="Tower has 1 heroes left for JC"):
        parse_format(fmt, plain, towns, heroes)
    allowing = parse_templates(
        [template(allowed_heroes=["t2", "t3"]), {"id": "6lm10a", "name": "6lm10a", "difficulty": 160}, {"id": "h3dm1", "name": "h3dm1", "difficulty": 160}],
        "t",
        heroes,
    )
    parse_format(fmt, allowing, towns, heroes)


# --- the default bans -------------------------------------------------------------------------------------------------------

FLAGS = ("campaign_hero", "banned_by_default", "banned_on_mirrors")


@pytest.mark.parametrize("flag", FLAGS)
def test_every_default_ban_flag_is_true_or_false(towns, flag):
    catalogue = parse_heroes([{**hero("a"), flag: True}, {**hero("b"), flag: False}], "heroes.json", towns)
    assert catalogue.find("a").details[flag] is True and catalogue.find("b").details[flag] is False
    with pytest.raises(CatalogueError, match=f"{flag} must be true or false"):
        parse_heroes([{**hero("c"), flag: "yes"}], "heroes.json", towns)


def test_the_water_flags_and_the_water_content_are_gone(towns):
    with pytest.raises(CatalogueError, match="may also have"):
        parse_heroes([{**hero("a"), "banned_without_water": True}], "heroes.json", towns)
    with pytest.raises(CatalogueError, match="may also have"):
        parse_templates([template(water_content="none")], "templates.json")


DEFAULTS = parse_heroes(
    [
        hero("plain1"),
        hero("plain2"),
        {**hero("campaign"), "campaign_hero": True, "banned_by_default": True},
        {**hero("hota"), "banned_by_default": True},
        {**hero("mirror"), "banned_on_mirrors": True},
    ],
    "heroes.json",
    load_towns(ROOT / "data" / "towns.json"),
)
MIRROR_FACTS = {"mirror": True, "map_size": {"default": "L+U", "allowed": ["L+U"]}}


def offered_by(**facts):
    """The heroes of Castle that a template with these facts offers."""
    catalogue = parse_templates([template(**facts)], "templates.json", DEFAULTS)
    return sorted(h.id for h in heroes_offered(DEFAULTS, catalogue.find("JC"), "castle"))


def test_the_heroes_banned_by_default_are_not_offered_by_a_template_that_says_nothing():
    assert offered_by() == ["mirror", "plain1", "plain2"]


def test_the_flag_that_says_a_hero_is_a_campaign_hero_alone_bans_nobody(towns):
    heroes = parse_heroes([{**hero("c"), "campaign_hero": True}], "heroes.json", towns)
    catalogue = parse_templates([template()], "templates.json", heroes)
    assert [h.id for h in heroes_offered(heroes, catalogue.find("JC"), "castle")] == ["c"]


def test_the_heroes_banned_on_mirrors_are_banned_only_on_a_mirror_template():
    assert "mirror" in offered_by()
    assert "mirror" not in offered_by(**MIRROR_FACTS)


def test_a_template_can_allow_a_hero_the_defaults_ban():
    assert offered_by(allowed_heroes=["campaign", "hota"]) == ["campaign", "hota", "mirror", "plain1", "plain2"]
    assert offered_by(allowed_heroes=["campaign", "mirror"], **MIRROR_FACTS) == ["campaign", "mirror", "plain1", "plain2"]


def test_a_template_can_still_ban_any_hero():
    assert offered_by(banned_heroes=["plain1", "mirror"]) == ["plain2"]


def test_the_defaults_count_for_a_roulette(good_format, towns):
    heroes = parse_heroes(
        [hero("t1", "tower"), {**hero("t2", "tower"), "banned_on_mirrors": True}, {**hero("t3", "tower"), "banned_by_default": True}]
        + [hero(f"c{n}") for n in range(4)]
        + [hero(f"v{n}", "cove") for n in range(4)],
        "heroes.json",
        towns,
    )
    fmt = roulette_format(good_format, trade={"kind": "roulette"})
    with pytest.raises(FormatError, match="Tower has 1 heroes left for JC, but a roulette with 0 hero bans each needs at least 2"):
        parse_format(fmt, catalogue_with(**MIRROR), towns, heroes)  # a mirror draws two, and Tower has one left
    parse_format(fmt, catalogue_with(allowed_heroes=["t3"], **MIRROR), towns, heroes)
    parse_format(fmt, catalogue_with(), towns, heroes)  # not a mirror: it draws one hero per town
