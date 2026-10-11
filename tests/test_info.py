import copy

import pytest

from rules.catalogue import TEMPLATE_FIELDS, parse_catalogue
from rules.formats import Step, parse_format
from rules.info import (
    MAX_REPLY,
    _fit,
    info_reply,
    mode_choices,
    mode_info,
    phase_choices,
    roll_line,
    template_choices,
    template_info,
    template_selection_line,
)
from rules.registry import Registry
from rules.roll_rules import RollRules

BAN_BAN = {"type": "sequence", "steps": [{"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"do": "decider"}]}
THREE = ["JC", "6lm10a", "h3dm1"]


def steps(text):
    """Steps from a short text: 'A ban, B ban, decider'."""
    result = []
    for word in text.split(","):
        parts = word.split()
        result.append(Step(None, "decider") if parts == ["decider"] else Step(parts[0], parts[1]))
    return tuple(result)


def phase(name, pool=None, best_of=1, selection=None):
    """A phase of a made-up tournament: best of 1, ban, ban, decider (so the pool must hold 3 templates)."""
    data = {"name": name, "best_of": best_of, "template_selection": copy.deepcopy(selection or BAN_BAN)}
    if pool is not None:
        data["pool"] = pool
    return data


def registry_with(good_format, templates, towns, phases, listed=None, **top):
    """A registry with one made-up tournament, "Sample Cup", with these phases."""
    data = dict(good_format, templates=listed or THREE, phases=phases, **top)
    fmt = parse_format(data, templates, towns)
    return Registry(towns, templates, {fmt.id: fmt})


@pytest.fixture
def registry(good_format, templates, towns):
    """One active single-phase mode (Sample Cup) and one archived mode (Old Cup)."""
    sample = parse_format(good_format, templates, towns)
    old = parse_format(dict(good_format, id="old-cup", name="Old Cup", status="archived"), templates, towns)
    return Registry(towns, templates, {sample.id: sample, old.id: old})


# --- the template selection line -------------------------------------------------------------


@pytest.mark.parametrize(
    "sequence, expected",
    [
        ("A ban, B ban, decider", "AB: A bans, B bans, then decider"),
        (
            "A ban, B ban, A pick, B pick, A ban, B ban, B ban, A ban, decider",
            "ABABABBA: A bans, B bans, A picks, B picks, A bans, B bans, B bans, A bans, then decider",
        ),
        (
            "A ban, B ban, B ban, A ban, A pick, B pick, decider",
            "ABBAAB: A bans, B bans, B bans, A bans, A picks, B picks, then decider",
        ),
        ("A ban, B ban, A pick, B pick", "ABAB: A bans, B bans, A picks, B picks"),
        ("decider", "No bans or picks: the only template is the decider"),
    ],
)
def test_the_template_selection_line(sequence, expected):
    assert template_selection_line(steps(sequence)) == expected


# --- the roll rules line -----------------------------------------------------------------------


def test_the_default_roll_rules_in_words():
    assert roll_line(RollRules(500, 1, 2)) == "500 gold, 1 per player, up to 2 towns banned"


def test_free_rolls_and_several_rolls():
    assert roll_line(RollRules(0, 2, 1)) == "free, 2 per player, up to 1 town banned"


def test_no_rolls_and_no_bans():
    assert roll_line(RollRules(500, 0, 2)) == "no rolls"
    assert roll_line(RollRules(500, 1, 0)) == "500 gold, 1 per player, no bans"


# --- a mode with one phase never mentions its phase -----------------------------------------------


def test_a_single_phase_mode(registry):
    assert info_reply(registry, "Sample Cup") == "\n".join(
        [
            "**Sample Cup**",
            "Templates: Jebus Cross, 6lm10a, h3dm1",
            "Best of 1",
            "Template Selection: AB: A bans, B bans, then decider",
        ]
    )


def test_a_single_phase_mode_does_not_name_its_phase_anywhere(registry):
    assert "Phase" not in info_reply(registry, "Sample Cup")
    assert "Main" not in info_reply(registry, "Sample Cup", "JC")


def test_templates_are_never_shown_by_their_short_id(registry):
    assert "JC" not in info_reply(registry, "Sample Cup")
    assert "JC" not in info_reply(registry, "Sample Cup", "JC")


def test_a_mode_is_found_by_id_or_name_in_any_letter_case(registry):
    assert info_reply(registry, "SAMPLE-CUP") == info_reply(registry, "sample cup") == info_reply(registry, "Sample Cup")


def test_a_single_phase_that_uses_only_some_templates_says_which(good_format, templates, towns):
    # the tournament lists four templates, its only phase uses three of them
    reg = registry_with(good_format, templates, towns, [phase("Main", pool=THREE)], listed=THREE + ["Diamond"])
    text = info_reply(reg, "Sample Cup")
    assert "Templates: Jebus Cross, 6lm10a, h3dm1, Diamond\nBest of 1\nPool: Jebus Cross, 6lm10a, h3dm1" in text


def test_an_agreed_template_phase_says_so_without_repeating_the_templates(good_format, templates, towns):
    good_format["phases"][0]["template_selection"] = {"type": "agreed"}
    fmt = parse_format(good_format, templates, towns)
    text = info_reply(Registry(towns, templates, {fmt.id: fmt}), "Sample Cup")
    assert "The players agree on the template." in text
    assert "Template Selection:" not in text and "Templates allowed" not in text


def test_an_archived_mode_is_shown_and_says_it_is_archived(registry):
    text = info_reply(registry, "Old Cup")
    assert text.startswith("**Old Cup** (archived: it cannot start new matches)")
    assert "Templates: Jebus Cross, 6lm10a, h3dm1" in text


# --- a mode with several phases ---------------------------------------------------------------------------


def test_each_phase_has_its_own_heading_and_a_phase_that_uses_everything_says_all(good_format, templates, towns):
    nine = ["JC", "h3dm1", "6lm10a", "nostalgia", "mt_nebula", "mt_Jebus", "Sapphire", "Diamond", "Conquest"]
    knockout = phase("Knockout", pool=nine[:7], best_of=3, selection={"type": "sequence", "steps": [
        {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "A", "do": "ban"},
        {"who": "A", "do": "pick"}, {"who": "B", "do": "pick"}, {"do": "decider"}]})
    final = phase("Final", best_of=3, selection={"type": "sequence", "steps": [
        {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "A", "do": "pick"}, {"who": "B", "do": "pick"},
        {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "B", "do": "ban"}, {"who": "A", "do": "ban"},
        {"do": "decider"}]})
    reg = registry_with(good_format, templates, towns, [phase("Group", pool=nine[:3]), knockout, final], listed=nine)
    text = info_reply(reg, "Sample Cup")

    assert text.count("Templates: Jebus Cross, h3dm1, 6lm10a, nostalgia, mt_nebula, mt_Jebus, Sapphire, Diamond, Conquest") == 1
    assert '**Phase "Group"** - best of 1\nTemplates: Jebus Cross, h3dm1, 6lm10a\nTemplate Selection: AB:' in text
    assert '**Phase "Knockout"** - best of 3\nTemplates: Jebus Cross, h3dm1, 6lm10a, nostalgia, mt_nebula, mt_Jebus, Sapphire\n' in text
    assert "Template Selection: ABBAAB: A bans, B bans, B bans, A bans, A picks, B picks, then decider" in text
    assert '**Phase "Final"** - best of 3\nTemplates: all\nTemplate Selection: ABABABBA:' in text


def test_an_agreed_phase_among_several_lists_the_allowed_templates(good_format, templates, towns):
    agreed = {"name": "Ranked", "best_of": 1, "pool": ["JC", "6lm10a"], "template_selection": {"type": "agreed"}}
    reg = registry_with(good_format, templates, towns, [phase("Cup"), agreed])
    text = info_reply(reg, "Sample Cup")
    assert '**Phase "Ranked"** - best of 1\nTemplates allowed: Jebus Cross, 6lm10a\nThe players agree on the template.' in text


# --- limiting a reply to one phase ------------------------------------------------------------------------


def three_phases(good_format, templates, towns):
    return registry_with(good_format, templates, towns, [phase("Group"), phase("Semi"), phase("Final")])


def test_a_mode_can_be_limited_to_one_phase(good_format, templates, towns):
    text = info_reply(three_phases(good_format, templates, towns), "Sample Cup", None, "Semi")
    assert text.startswith("**Sample Cup**\nTemplates: Jebus Cross, 6lm10a, h3dm1")
    assert '**Phase "Semi"**' in text and "Group" not in text and "Final" not in text


def test_a_phase_is_found_by_name_in_any_letter_case(good_format, templates, towns):
    reg = three_phases(good_format, templates, towns)
    assert info_reply(reg, "Sample Cup", None, "semi") == info_reply(reg, "Sample Cup", None, " SEMI ")


def test_an_unknown_phase_lists_the_phases_of_the_mode(good_format, templates, towns):
    text = info_reply(three_phases(good_format, templates, towns), "Sample Cup", None, "Quarter")
    assert text == "Sample Cup has no phase called 'Quarter'. Its phases: Group, Semi, Final."


def test_a_single_phase_mode_accepts_its_own_phase_name_and_explains_others(registry):
    assert info_reply(registry, "Sample Cup", None, "Main") == info_reply(registry, "Sample Cup")
    assert info_reply(registry, "Sample Cup", None, "Final") == "Sample Cup has no phase called 'Final'. Its phases: Main."


# --- a template in a mode ----------------------------------------------------------------------------


def test_a_template_in_a_single_phase_mode(registry):
    assert info_reply(registry, "Sample Cup", "JC") == "\n".join(
        [
            "**Jebus Cross** in Sample Cup",
            "160% difficulty",
            "Roll: 500 gold, 1 per player, up to 2 towns banned",
        ]
    )


def test_a_template_is_found_by_id_or_display_name(registry):
    assert info_reply(registry, "Sample Cup", "JC") == info_reply(registry, "Sample Cup", "jebus cross")


def test_a_template_that_is_the_same_in_every_phase_says_it_once_without_phases(good_format, templates, towns):
    text = info_reply(three_phases(good_format, templates, towns), "Sample Cup", "JC")
    assert text == "\n".join(
        [
            "**Jebus Cross** in Sample Cup",
            "160% difficulty",
            "Roll: 500 gold, 1 per player, up to 2 towns banned",
        ]
    )


def test_a_tournament_wide_override_is_still_said_once(good_format, templates, towns):
    good_format["roll_rules"] = {"roll_cost": 500}
    listed = [{"template": "JC", "roll_rules": {"roll_cost": 0}}, "6lm10a", "h3dm1"]
    reg = registry_with(good_format, templates, towns, [phase("A"), phase("B")], listed=listed)
    text = info_reply(reg, "Sample Cup", "JC")
    assert "Roll: free, 1 per player, up to 2 towns banned" in text and "A:" not in text
    assert "Roll: 500 gold," in info_reply(reg, "Sample Cup", "6lm10a")


def entry(template, **rules):
    return {"template": template, "roll_rules": rules}


def test_only_the_rule_that_differs_is_listed_under_the_phase(good_format, templates, towns):
    phases = [phase("Group"), phase("Final", pool=["JC", entry("6lm10a", rolls_per_player=2), "h3dm1"])]
    text = info_reply(registry_with(good_format, templates, towns, phases), "Sample Cup", "6lm10a")
    assert text == "\n".join(
        [
            "**6lm10a** in Sample Cup",
            "160% difficulty",
            "Roll: 500 gold, 1 per player, up to 2 towns banned",
            "  Final: 2 per player",
        ]
    )


def test_several_differing_rules_in_one_phase_are_listed_together(good_format, templates, towns):
    phases = [phase("Group"), phase("Final", pool=["JC", entry("6lm10a", roll_cost=0, max_roll_bans=0), "h3dm1"])]
    text = info_reply(registry_with(good_format, templates, towns, phases), "Sample Cup", "6lm10a")
    assert "  Final: free, no bans" in text


def test_each_deviating_phase_gets_its_own_line(good_format, templates, towns):
    phases = [phase("One"), phase("Two", pool=["JC", entry("6lm10a", rolls_per_player=2), "h3dm1"]),
              phase("Three", pool=["JC", entry("6lm10a", roll_cost=100), "h3dm1"])]
    text = info_reply(registry_with(good_format, templates, towns, phases), "Sample Cup", "6lm10a")
    assert "  Two: 2 per player\n  Three: 100 gold" in text


def test_the_base_is_the_value_most_phases_use(good_format, templates, towns):
    two_rolls = ["JC", entry("6lm10a", rolls_per_player=2), "h3dm1"]
    phases = [phase("One"), phase("Two", pool=two_rolls), phase("Three", pool=two_rolls)]
    text = info_reply(registry_with(good_format, templates, towns, phases), "Sample Cup", "6lm10a")
    assert "Roll: 500 gold, 2 per player, up to 2 towns banned" in text
    assert "  One: 1 per player" in text and "Two:" not in text and "Three:" not in text


def test_on_a_tie_the_first_phase_is_the_base(good_format, templates, towns):
    phases = [phase("One"), phase("Two", pool=["JC", entry("6lm10a", rolls_per_player=3), "h3dm1"])]
    text = info_reply(registry_with(good_format, templates, towns, phases), "Sample Cup", "6lm10a")
    assert "Roll: 500 gold, 1 per player" in text and "  Two: 3 per player" in text


def test_a_template_that_is_not_in_every_phase_says_where_it_is_played(good_format, templates, towns):
    phases = [phase("Group", pool=["JC", "6lm10a", "h3dm1"]), phase("Final", pool=["6lm10a", "h3dm1", "Diamond"])]
    reg = registry_with(good_format, templates, towns, phases, listed=THREE + ["Diamond"])
    assert "Played in: Group\n" in info_reply(reg, "Sample Cup", "JC")
    assert "Played in: Final\n" in info_reply(reg, "Sample Cup", "Diamond")
    assert "Played in" not in info_reply(reg, "Sample Cup", "6lm10a")


def test_a_template_limited_to_one_phase_shows_only_that_phase(good_format, templates, towns):
    phases = [phase("Group"), phase("Final", pool=["JC", entry("6lm10a", rolls_per_player=2), "h3dm1"])]
    reg = registry_with(good_format, templates, towns, phases)
    assert info_reply(reg, "Sample Cup", "6lm10a", "Final") == "\n".join(
        [
            "**6lm10a** in Sample Cup - Final",
            "160% difficulty",
            "Roll: 500 gold, 2 per player, up to 2 towns banned",
        ]
    )


def test_a_template_limited_to_a_phase_that_does_not_use_it_says_where_it_is_played(good_format, templates, towns):
    phases = [phase("Group", pool=["JC", "6lm10a", "h3dm1"]), phase("Final", pool=["6lm10a", "h3dm1", "Diamond"])]
    reg = registry_with(good_format, templates, towns, phases, listed=THREE + ["Diamond"])
    assert info_reply(reg, "Sample Cup", "Diamond", "Group") == "Diamond is not played in Group. It is played in: Final."


def test_a_200_percent_template_has_no_roll_to_describe(good_format, templates, towns):
    entries = [{"id": t, "name": t, "difficulty": 200 if t == "JC" else 160} for t in THREE]
    all_random = parse_catalogue(entries, "t", TEMPLATE_FIELDS)
    fmt = parse_format(good_format, all_random, towns)
    text = info_reply(Registry(towns, all_random, {fmt.id: fmt}), "Sample Cup", "JC")
    assert text == "**JC** in Sample Cup\n200% difficulty\nNo roll: the trade is only a toss for color."


def test_a_template_that_no_phase_uses_says_so(good_format, templates, towns):
    reg = registry_with(good_format, templates, towns, [phase("Main", pool=THREE)], listed=THREE + ["Diamond"])
    assert info_reply(reg, "Sample Cup", "Diamond") == "Diamond is listed for Sample Cup but no phase uses it."


# --- unknown names ---------------------------------------------------------------------------------------


def test_an_unknown_mode_lists_the_modes_that_can_be_looked_up(registry):
    assert info_reply(registry, "nope") == (
        "There is no mode called 'nope'. Modes you can look up: Sample Cup, Old Cup (archived)."
    )


def test_a_template_that_is_not_in_the_mode_lists_the_templates_of_the_mode(registry):
    assert info_reply(registry, "Sample Cup", "Diamond") == (
        "'Diamond' is not in Sample Cup. Its templates: Jebus Cross, 6lm10a, h3dm1."
    )


def test_a_template_that_does_not_exist_at_all_is_answered_the_same_way(registry):
    assert info_reply(registry, "Sample Cup", "nope").startswith("'nope' is not in Sample Cup.")


# --- autocomplete --------------------------------------------------------------------------------------------


def test_modes_are_offered_by_name_with_the_id_as_value(registry):
    assert mode_choices(registry, "") == [("Sample Cup", "sample-cup"), ("Old Cup (archived)", "old-cup")]
    assert mode_choices(registry, "sam") == [("Sample Cup", "sample-cup")]
    assert mode_choices(registry, "OLD-C") == [("Old Cup (archived)", "old-cup")]
    assert mode_choices(registry, "zzz") == []


def test_templates_of_the_chosen_mode_are_offered_by_display_name_with_the_id_as_value(registry):
    assert template_choices(registry, "sample-cup", "") == [("Jebus Cross", "JC"), ("6lm10a", "6lm10a"), ("h3dm1", "h3dm1")]
    assert template_choices(registry, "Sample Cup", "jeb") == [("Jebus Cross", "JC")]
    assert template_choices(registry, "Sample Cup", "jc") == [("Jebus Cross", "JC")]


def test_no_templates_are_offered_for_an_unknown_mode(registry):
    assert template_choices(registry, "nope", "") == []


def test_the_phases_of_the_chosen_mode_are_offered(good_format, templates, towns):
    reg = three_phases(good_format, templates, towns)
    assert phase_choices(reg, "Sample Cup", "") == [("Group", "Group"), ("Semi", "Semi"), ("Final", "Final")]
    assert phase_choices(reg, "sample-cup", "fi") == [("Final", "Final")]
    assert phase_choices(reg, "nope", "") == []


def test_a_mode_with_one_phase_offers_no_phase_to_choose(registry):
    assert phase_choices(registry, "Sample Cup", "") == []


def test_at_most_25_choices_are_offered(good_format, templates, towns):
    many = {f"cup-{i}": parse_format(dict(good_format, id=f"cup-{i}", name=f"Cup {i}"), templates, towns) for i in range(40)}
    assert len(mode_choices(Registry(towns, templates, many), "")) == 25


# --- the length of a reply ------------------------------------------------------------------------------------


def test_a_short_reply_is_unchanged():
    assert _fit("hello\nworld") == "hello\nworld"


def test_a_reply_that_is_too_long_is_cut_at_a_line_and_says_so():
    long_text = "\n".join(f"line {i} " + "x" * 50 for i in range(100))
    fitted = _fit(long_text)
    assert len(fitted) <= MAX_REPLY + 50
    assert fitted.endswith("(The rest is too long to show.)")
    assert "\nline 0 " in "\n" + fitted


def test_a_realistic_big_tournament_fits(good_format, templates, towns):
    nine = ["JC", "h3dm1", "6lm10a", "nostalgia", "mt_nebula", "mt_Jebus", "Sapphire", "Diamond", "Conquest"]
    nine_bans = {"type": "sequence", "steps": [{"who": "AB"[i % 2], "do": "ban"} for i in range(8)] + [{"do": "decider"}]}
    phases = [phase(f"Stage {i + 1}", pool=nine, selection=nine_bans) for i in range(3)]
    reg = registry_with(good_format, templates, towns, phases, listed=nine)
    fmt = reg.formats[good_format["id"]]
    assert len(mode_info(fmt, templates)) < 2000
    assert len(template_info(fmt, "JC", templates)) < 2000
