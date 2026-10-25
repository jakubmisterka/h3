"""The text of the /info replies: how a mode works, and how one template is played in it.

Plain functions from the loaded data to text, so every sentence can be tested. Templates are
always shown by the name players read (Jebus Cross), never by their short id (JC).

A reply never repeats itself: a mode with one phase does not mention the phase, and what is the
same in every phase of a template is said once, with only the differences listed per phase.
"""

from rules.catalogue import Catalogue
from rules.difficulty import ALL_RANDOM_DIFFICULTY
from rules.formats import Format, Phase, Step
from rules.registry import Registry
from rules.roll_rules import RollRules, effective_roll_rules
from rules.template_facts import SETTINGS, fixed_lines, setting_line, setting_value
from rules.template_settings import Settings, effective_settings

# Discord refuses a message longer than 2000 characters. Stay safely under it.
MAX_REPLY = 1900
AUTOCOMPLETE_LIMIT = 25  # Discord shows at most 25 choices


# --- small pieces ------------------------------------------------------------------------------


def _names(templates: Catalogue, ids) -> str:
    return ", ".join(templates.find(template).name for template in ids)


def _plural(number: int, word: str) -> str:
    return f"{number} {word}" if number == 1 else f"{number} {word}s"


def template_selection_line(steps: tuple[Step, ...]) -> str:
    """How the template is chosen, the way players write it: "AB: A bans, B bans, then decider"."""
    acting = [step for step in steps if step.do != "decider"]
    has_decider = len(acting) < len(steps)
    words = [f"{step.who} {'bans' if step.do == 'ban' else 'picks'}" for step in acting]
    if has_decider:
        words.append("then decider")
    if not acting:
        return "No bans or picks: the only template is the decider"
    return f"{''.join(step.who for step in acting)}: {', '.join(words)}"


# The roll rules in words, one rule at a time, so that a difference can be named on its own.
def _cost_words(rules: RollRules) -> str:
    return "free" if rules.roll_cost == 0 else f"{rules.roll_cost} gold"


def _rolls_words(rules: RollRules) -> str:
    return "no rolls" if rules.rolls_per_player == 0 else f"{rules.rolls_per_player} per player"


def _bans_words(rules: RollRules) -> str:
    return "no bans" if rules.max_roll_bans == 0 else f"up to {_plural(rules.max_roll_bans, 'town')} banned"


def roll_line(rules: RollRules) -> str:
    """All the roll rules in words, for example "500 gold, 1 per player, up to 2 towns banned"."""
    if rules.rolls_per_player == 0:
        return "no rolls"
    return f"{_cost_words(rules)}, {_rolls_words(rules)}, {_bans_words(rules)}"


def _most_common(values: list):
    """The value that occurs most often; on a tie, the one that comes first."""
    return max(values, key=lambda value: (values.count(value), -values.index(value)))


def _fit(text: str) -> str:
    """Keep a reply under Discord's limit, cutting at a line break and saying so."""
    if len(text) <= MAX_REPLY:
        return text
    cut = text[:MAX_REPLY].rsplit("\n", 1)[0]
    return f"{cut}\n(The rest is too long to show.)"


def find_phase(fmt: Format, text: str) -> Phase | None:
    """A phase of the mode by name, ignoring letter case."""
    wanted = text.strip().lower()
    return next((phase for phase in fmt.phases if phase.name.lower() == wanted), None)


# --- a mode -------------------------------------------------------------------------------------


def _phase_lines(fmt: Format, phase: Phase, templates: Catalogue) -> list[str]:
    several = len(fmt.phases) > 1
    uses_all = set(phase.pool_ids) == {entry.template for entry in fmt.templates}
    lines = [f'**Phase "{phase.name}"** - best of {phase.best_of}'] if several else [f"Best of {phase.best_of}"]

    label = "Templates allowed" if phase.agreed else ("Templates" if several else "Pool")
    if several and uses_all:
        lines.append(f"{label}: all")
    elif not uses_all:
        lines.append(f"{label}: {_names(templates, phase.pool_ids)}")
    # a single phase that uses every template needs no line: the mode's own list says it

    if phase.agreed:
        lines.append("The players agree on the template.")
    else:
        lines.append(f"Template Selection: {template_selection_line(phase.steps)}")
    return lines


def mode_info(fmt: Format, templates: Catalogue, phase: Phase | None = None) -> str:
    """Everything a player may want to know about a mode, or about one of its phases."""
    title = f"**{fmt.name}**" + ("" if fmt.active else " (archived: it cannot start new matches)")
    lines = [title]
    if fmt.description:
        lines.append(f"Description: {fmt.description}")
    lines.append(f"Templates: {_names(templates, (entry.template for entry in fmt.templates))}")
    for shown in [phase] if phase else fmt.phases:
        if len(fmt.phases) > 1:
            lines.append("")
        lines += _phase_lines(fmt, shown, templates)
    if fmt.additional_rules:
        lines += ["", f"Additional rules: {fmt.additional_rules}"] if len(fmt.phases) > 1 else [f"Additional rules: {fmt.additional_rules}"]
    return _fit("\n".join(lines))


# --- a template in a mode ----------------------------------------------------------------------------


def _roll_lines(per_phase: list[tuple[Phase, RollRules]]) -> list[str]:
    """The roll rules once, then the phases that differ and only what differs there, rule by rule."""
    rules = [rule for _, rule in per_phase]
    base = RollRules(
        roll_cost=_most_common([r.roll_cost for r in rules]),
        rolls_per_player=_most_common([r.rolls_per_player for r in rules]),
        max_roll_bans=_most_common([r.max_roll_bans for r in rules]),
    )
    lines = [f"Roll: {roll_line(base)}"]
    for phase, rule in per_phase:
        different = []
        if rule.roll_cost != base.roll_cost:
            different.append(_cost_words(rule))
        if rule.rolls_per_player != base.rolls_per_player:
            different.append(_rolls_words(rule))
        if rule.max_roll_bans != base.max_roll_bans:
            different.append(_bans_words(rule))
        if different:
            lines.append(f"  {phase.name}: {', '.join(different)}")
    return lines


def _setting_lines(per_phase: list[tuple[Phase, Settings]]) -> list[str]:
    """What is played on the template: its own facts once, then each stated setting once, with the phases that differ
    named after it, as the roll rules are."""
    lines = fixed_lines(per_phase[0][1])
    for name in (*SETTINGS, "additional_rules"):
        values = [getattr(settings, name) for _, settings in per_phase]
        base = _most_common(values)
        if base is not None:
            lines.append(setting_line(name, Settings(**{name: base})))
        for phase, settings in per_phase:
            value = getattr(settings, name)
            if value is None or value == base:
                continue
            if base is None:  # only some phases state it
                lines.append(f"{setting_line(name, settings)} ({phase.name})")
            else:
                lines.append(f"  {phase.name}: {setting_value(name, settings)}")
    return lines


def template_info(fmt: Format, template_id: str, templates: Catalogue, phase: Phase | None = None) -> str:
    """How one template is played in a mode: in all the phases that use it, or in just one."""
    entry = templates.find(template_id)
    several = len(fmt.phases) > 1
    title = f"**{entry.name}** in {fmt.name}" + ("" if fmt.active else " (archived)")
    if phase and several:
        title += f" - {phase.name}"
    lines = [title]
    if entry.details.get("description"):
        lines.append(f"Description: {entry.details['description']}")

    using = [p for p in fmt.phases if template_id in p.pool_ids]
    if phase:
        if phase not in using:
            where = ", ".join(p.name for p in using)
            elsewhere = f"It is played in: {where}." if where else "No phase uses it."
            return f"{entry.name} is not played in {phase.name}. {elsewhere}"
        using = [phase]
    if not using:
        return f"{entry.name} is listed for {fmt.name} but no phase uses it."
    if several and not phase and len(using) < len(fmt.phases):
        lines.append(f"Played in: {', '.join(p.name for p in using)}")

    difficulty = entry.details["difficulty"]
    lines.append(f"{difficulty}% difficulty")
    if difficulty == ALL_RANDOM_DIFFICULTY:
        lines.append("No roll: the trade is only a toss for color.")
    else:
        lines += _roll_lines([(p, effective_roll_rules(fmt, p, template_id)) for p in using])
    lines += _setting_lines([(p, effective_settings(fmt, p, template_id, templates)) for p in using])
    return _fit("\n".join(lines))


# --- looking a mode or template up, with every way it can go wrong ---------------------------------------


def _lookup_names(registry: Registry) -> str:
    return ", ".join(fmt.name + ("" if fmt.active else " (archived)") for fmt in registry.formats.values())


def info_reply(registry: Registry, mode_text: str, template_text: str | None = None, phase_text: str | None = None) -> str:
    """The reply to /info for a mode or a template in it, optionally for one phase. Always text, never an error."""
    fmt = registry.find_format(mode_text)
    if fmt is None:
        names = _lookup_names(registry)
        available = f"Modes you can look up: {names}." if names else "There are no modes."
        return f"There is no mode called {mode_text!r}. {available}"

    phase = None
    if phase_text:
        phase = find_phase(fmt, phase_text)
        if phase is None:
            phases = ", ".join(p.name for p in fmt.phases)
            return f"{fmt.name} has no phase called {phase_text!r}. Its phases: {phases}."

    if not template_text:
        return mode_info(fmt, registry.templates, phase)

    found = registry.templates.find(template_text)
    listed = [entry.template for entry in fmt.templates]
    if found is None or found.id not in listed:
        return f"{template_text!r} is not in {fmt.name}. Its templates: {_names(registry.templates, listed)}."
    return template_info(fmt, found.id, registry.templates, phase)


# --- autocomplete ---------------------------------------------------------------------------------------


def mode_choices(registry: Registry, typed: str) -> list[tuple[str, str]]:
    """(shown name, value) for the modes matching what the player has typed so far."""
    wanted = typed.strip().lower()
    return [
        (fmt.name + ("" if fmt.active else " (archived)"), fmt.id)
        for fmt in registry.formats.values()
        if wanted in fmt.name.lower() or wanted in fmt.id.lower()
    ][:AUTOCOMPLETE_LIMIT]


def template_choices(registry: Registry, mode_text: str, typed: str) -> list[tuple[str, str]]:
    """(display name, template id) for the templates of the chosen mode matching what has been typed."""
    fmt = registry.find_format(mode_text)
    if fmt is None:
        return []
    wanted = typed.strip().lower()
    choices = []
    for entry in fmt.templates:
        template = registry.templates.find(entry.template)
        if wanted in template.name.lower() or wanted in template.id.lower():
            choices.append((template.name, template.id))
    return choices[:AUTOCOMPLETE_LIMIT]


def phase_choices(registry: Registry, mode_text: str, typed: str) -> list[tuple[str, str]]:
    """(name, value) for the phases of the chosen mode. A mode with one phase offers nothing to choose."""
    fmt = registry.find_format(mode_text)
    if fmt is None or len(fmt.phases) < 2:
        return []
    wanted = typed.strip().lower()
    return [(phase.name, phase.name) for phase in fmt.phases if wanted in phase.name.lower()][:AUTOCOMPLETE_LIMIT]
