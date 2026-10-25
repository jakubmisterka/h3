"""The description and the additional rules: free text of at most 1000 characters, stated by a template in the catalogue
and by a tournament, inherited by a template like its other settings, shown by /info, and posted in the thread when
the trade of a game starts."""

import asyncio
import copy

import pytest

import discord_commands.match as match
from rules.catalogue import CatalogueError, parse_templates
from rules.formats import FormatError, parse_format
from rules.info import info_reply
from rules.lobby_values import MAX_TEXT, check_text
from rules.registry import Registry
from rules.template_settings import effective_settings
from test_selection_command import ANNA, BORIS, BOT, make_thread, texts
from test_trade_command import WHOLE_SELECTION, fixed_pair, select, start  # noqa: F401  (fixed_pair: Anna is A)

CATALOGUE_RULES = "AI picked alternately, blue first"
TEMPLATES = [
    {"id": "JC", "name": "Jebus Cross", "difficulty": 160, "description": "A cross of four islands", "additional_rules": CATALOGUE_RULES},
    {"id": "6lm10a", "name": "6lm10a", "difficulty": 160},
    {"id": "h3dm1", "name": "h3dm1", "difficulty": 160},
    {"id": "Diamond", "name": "Diamond", "difficulty": 160, "additional_rules": "Host picks the AI towns"},
    {"id": "Sapphire", "name": "Sapphire", "difficulty": 160},
]


def catalogue_of(*changes):
    data = copy.deepcopy(TEMPLATES)
    for entry in data:
        for change in changes:
            if entry["id"] == change[0]:
                entry.update(change[1])
    return parse_templates(data, "templates.json")


# --- the check -----------------------------------------------------------------------------------------------------


def test_a_text_is_kept_as_written():
    assert check_text("Blue picks first") == "Blue picks first"


@pytest.mark.parametrize("text", ["", "   ", "\n"])
def test_an_empty_text_asks_to_leave_the_field_out(text):
    with pytest.raises(ValueError, match="leave the field out"):
        check_text(text)


def test_a_text_of_exactly_the_limit_is_accepted_and_one_more_is_not():
    assert check_text("x" * MAX_TEXT)
    with pytest.raises(ValueError, match="limit is 1000"):
        check_text("x" * (MAX_TEXT + 1))


def test_something_that_is_not_text_is_refused():
    with pytest.raises(ValueError, match="not a text"):
        check_text(5)


# --- the catalogue -------------------------------------------------------------------------------------------------


def test_a_template_may_state_a_description_and_rules():
    entry = catalogue_of().find("JC")
    assert entry.details["description"] == "A cross of four islands"
    assert entry.details["additional_rules"] == CATALOGUE_RULES


def test_a_template_may_state_neither():
    assert "additional_rules" not in catalogue_of().find("6lm10a").details


def test_a_long_text_in_the_catalogue_names_the_template_and_the_limit():
    with pytest.raises(CatalogueError, match=r"entry 2 \(6lm10a\): additional_rules: .*limit is 1000"):
        catalogue_of(("6lm10a", {"additional_rules": "x" * 1001}))


def test_an_empty_description_in_the_catalogue_is_refused():
    with pytest.raises(CatalogueError, match=r"entry 3 \(h3dm1\): description: .*leave the field out"):
        catalogue_of(("h3dm1", {"description": " "}))


# --- the format ----------------------------------------------------------------------------------------------------


def make_format(good_format, towns, catalogue=None, **changes):
    data = copy.deepcopy(good_format)
    data.update(changes)
    return parse_format(data, catalogue or catalogue_of(), towns)


def test_a_tournament_may_state_a_description_and_rules(good_format, towns):
    fmt = make_format(good_format, towns, description="Open to all", additional_rules="Agree on the simultaneous turns")
    assert (fmt.description, fmt.additional_rules) == ("Open to all", "Agree on the simultaneous turns")


def test_a_tournament_states_neither_by_default(good_format, towns):
    fmt = make_format(good_format, towns)
    assert fmt.description is None and fmt.additional_rules is None


def test_a_long_tournament_text_says_the_limit(good_format, towns):
    with pytest.raises(FormatError, match="description: .*limit is 1000"):
        make_format(good_format, towns, description="x" * 1001)


def test_tournament_rules_cannot_be_written_in_the_tournaments_settings(good_format, towns):
    with pytest.raises(FormatError, match='written as "additional_rules" next to "name"'):
        make_format(good_format, towns, settings={"additional_rules": "No."})


def test_a_wrong_template_rule_in_the_list_is_found(good_format, towns):
    with pytest.raises(FormatError, match="templates, JC: settings: additional_rules: .*leave the field out"):
        make_format(good_format, towns, templates=[{"template": "JC", "settings": {"additional_rules": ""}}, "6lm10a", "h3dm1"])


# --- the inheritance: catalogue, then the list, then the phase's pool ----------------------------------------------


def settings_in(good_format, towns, template="JC", **changes):
    fmt = make_format(good_format, towns, **changes)
    return effective_settings(fmt, fmt.phases[0], template, catalogue_of())


def test_a_template_has_the_rules_its_catalogue_states(good_format, towns):
    assert settings_in(good_format, towns).additional_rules == CATALOGUE_RULES


def test_a_template_that_states_no_rules_has_none(good_format, towns):
    assert settings_in(good_format, towns, "6lm10a").additional_rules is None


def test_the_tournaments_list_replaces_the_rules_of_the_catalogue(good_format, towns):
    changed = settings_in(
        good_format, towns, templates=[{"template": "JC", "settings": {"additional_rules": "Red first"}}, "6lm10a", "h3dm1"]
    )
    assert changed.additional_rules == "Red first"


def test_the_rules_of_other_templates_are_not_touched(good_format, towns):
    templates = [{"template": "JC", "settings": {"additional_rules": "Red first"}}, "6lm10a", "h3dm1"]
    assert settings_in(good_format, towns, "6lm10a", templates=templates).additional_rules is None


def test_a_phase_replaces_the_rules_of_the_list(good_format, towns):
    phase = copy.deepcopy(good_format["phases"][0])
    phase["pool"] = [{"template": "JC", "settings": {"additional_rules": "Phase rules"}}, "6lm10a", "h3dm1"]
    templates = [{"template": "JC", "settings": {"additional_rules": "List rules"}}, "6lm10a", "h3dm1"]
    assert settings_in(good_format, towns, templates=templates, phases=[phase]).additional_rules == "Phase rules"


def test_the_tournaments_own_rules_are_not_inherited_by_templates(good_format, towns):
    assert settings_in(good_format, towns, "6lm10a", additional_rules="For everyone").additional_rules is None


def test_the_description_comes_from_the_catalogue(good_format, towns):
    assert settings_in(good_format, towns).description == "A cross of four islands"


# --- /info ---------------------------------------------------------------------------------------------------------


def registry_of(good_format, towns, catalogue=None, **changes):
    catalogue = catalogue or catalogue_of()
    fmt = make_format(good_format, towns, catalogue, **changes)
    return Registry(towns, catalogue, {fmt.id: fmt})


def two_phases(good_format):
    groups = copy.deepcopy(good_format["phases"][0])
    final = copy.deepcopy(groups)
    groups["name"], final["name"] = "Groups", "Final"
    return groups, final


def test_the_mode_reply_gives_the_description_and_the_rules(good_format, towns):
    registry = registry_of(good_format, towns, description="Open to all", additional_rules="Agree on the simultaneous turns")
    lines = info_reply(registry, "sample-cup").splitlines()
    assert lines[1] == "Description: Open to all"
    assert lines[-1] == "Additional rules: Agree on the simultaneous turns"


def test_the_mode_reply_is_as_before_without_them(good_format, towns):
    text = info_reply(registry_of(good_format, towns), "sample-cup")
    assert "Description" not in text and "Rules" not in text


def test_the_template_reply_gives_the_description_and_the_rules(good_format, towns):
    lines = info_reply(registry_of(good_format, towns), "sample-cup", "JC").splitlines()
    assert lines[1] == "Description: A cross of four islands"
    assert f"Additional rules: {CATALOGUE_RULES}" in lines


def test_the_template_reply_gives_the_rules_the_tournament_changed(good_format, towns):
    templates = [{"template": "JC", "settings": {"additional_rules": "Red first"}}, "6lm10a", "h3dm1"]
    text = info_reply(registry_of(good_format, towns, templates=templates), "sample-cup", "JC")
    assert "Additional rules: Red first" in text and CATALOGUE_RULES not in text


def test_the_template_reply_names_the_phase_whose_rules_differ(good_format, towns):
    groups, final = two_phases(good_format)
    final["pool"] = [{"template": "JC", "settings": {"additional_rules": "Final rules"}}, "6lm10a", "h3dm1"]
    groups["pool"] = ["JC", "6lm10a", "h3dm1"]
    text = info_reply(registry_of(good_format, towns, phases=[groups, final]), "sample-cup", "JC")
    lines = text.splitlines()
    assert f"Additional rules: {CATALOGUE_RULES}" in lines
    assert "  Final: Final rules" in lines


def test_a_template_without_any_is_as_before(good_format, towns):
    text = info_reply(registry_of(good_format, towns), "sample-cup", "6lm10a")
    assert "Description" not in text and "Rules" not in text


# --- the thread ----------------------------------------------------------------------------------------------------


def started(registry, template=None):
    thread = make_thread(971)
    fmt = registry.formats["sample-cup"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], template, ANNA, BORIS))
    return thread


def bo3_registry(good_format, towns):
    selection = {
        "type": "sequence",
        "steps": [
            {"who": "A", "do": "ban"},
            {"who": "B", "do": "ban"},
            {"who": "A", "do": "pick"},
            {"who": "B", "do": "pick"},
            {"do": "decider"},
        ],
    }
    phase = {"name": "Main", "best_of": 3, "template_selection": selection}
    return registry_of(
        good_format,
        towns,
        templates=["JC", "6lm10a", "h3dm1", "Diamond", "Sapphire"],
        allowed_towns=["castle", "necropolis", "tower", "cove"],
        roll_rules={"rolls_per_player": 0},
        phases=[phase],
        id="sample-cup",
    )


def rule_messages(thread):
    return [t for t in texts(thread) if t.startswith("Additional rules: ")]


def test_a_named_template_posts_its_rules_when_its_trade_starts(good_format, towns):
    thread = started(registry_of(good_format, towns), "JC")
    assert rule_messages(thread) == [f"Additional rules: {CATALOGUE_RULES}"]


def test_the_rules_come_after_the_start_of_the_trade_and_before_what_to_do_next(good_format, towns):
    sent = texts(started(registry_of(good_format, towns), "JC"))
    at = sent.index(f"Additional rules: {CATALOGUE_RULES}")
    assert "trade" in sent[at - 1].lower()  # the opening of the trade
    assert sent[at + 1].startswith("Game 1 town roll")  # the prompt stays the last thing said


def test_the_rules_of_the_phase_are_the_ones_posted(good_format, towns):
    phase = copy.deepcopy(good_format["phases"][0])
    phase["pool"] = [{"template": "JC", "settings": {"additional_rules": "Phase rules"}}, "6lm10a", "h3dm1"]
    registry = registry_of(good_format, towns, phases=[phase])
    assert rule_messages(started(registry, "JC")) == ["Additional rules: Phase rules"]


def test_a_template_without_rules_posts_none(good_format, towns):
    assert rule_messages(started(registry_of(good_format, towns), "6lm10a")) == []


def test_nothing_is_posted_before_a_trade_starts(good_format, towns):
    thread = started(registry_of(good_format, towns))  # the template is not settled yet
    assert rule_messages(thread) == []


def test_the_rules_are_posted_when_each_games_trade_starts_but_not_when_it_is_resumed(good_format, towns):
    registry = bo3_registry(good_format, towns)
    thread = started(registry)
    select(registry, thread, *WHOLE_SELECTION)  # JC is game 1, Diamond game 2, h3dm1 game 3
    assert rule_messages(thread) == []
    start(registry, thread, "1")
    assert rule_messages(thread) == [f"Additional rules: {CATALOGUE_RULES}"]
    start(registry, thread, "2")
    assert rule_messages(thread)[-1] == "Additional rules: Host picks the AI towns"
    start(registry, thread, "1")  # game 1 is resumed
    assert len(rule_messages(thread)) == 2


# --- a version of a template that is not the one built into HotA ---------------------------------------------------

OTHER_VERSION = "https://example.com/other-jc"


def test_a_tournament_can_give_a_download_that_replaces_built_in(good_format, towns):
    catalogue = catalogue_of(("JC", {"built_in": True}))
    fmt = make_format(
        good_format, towns, catalogue, templates=[{"template": "JC", "settings": {"download": OTHER_VERSION}}, "6lm10a", "h3dm1"]
    )
    chosen = effective_settings(fmt, fmt.phases[0], "JC", catalogue)
    assert chosen.download == OTHER_VERSION and not chosen.built_in


def test_without_a_download_the_template_stays_built_in(good_format, towns):
    catalogue = catalogue_of(("JC", {"built_in": True}))
    fmt = make_format(good_format, towns, catalogue)
    assert effective_settings(fmt, fmt.phases[0], "JC", catalogue).built_in


def test_a_download_in_the_tournaments_own_settings_is_refused(good_format, towns):
    with pytest.raises(FormatError, match="can only be given for a template"):
        make_format(good_format, towns, settings={"download": OTHER_VERSION})


def test_a_download_that_is_not_a_link_is_refused(good_format, towns):
    with pytest.raises(FormatError, match="https://"):
        make_format(good_format, towns, templates=[{"template": "JC", "settings": {"download": "ftp://x"}}, "6lm10a", "h3dm1"])
