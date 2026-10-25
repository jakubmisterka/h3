"""What is played on one template in one phase of a tournament: the timer, roads, map size, computer players, the
recommended simultaneous turns and the additional rules.

A template states defaults in the catalogue (`data/templates.json`). A format can choose settings in up to three
places, as it can for roll rules: for the whole tournament (only the timer and the simultaneous turns), for a
template in the tournament's list, and for a template in one phase's pool. They are stacked on top of the template's
defaults, the most specific winning, setting by setting:

    template's defaults -> tournament -> template in the list -> template in the phase's pool

The timer is never in the catalogue, so it is unknown unless a tournament sets it. A setting that nobody states is
unknown (`None`), and nothing is guessed in its place.
"""

from dataclasses import dataclass

from rules.catalogue import Catalogue
from rules.formats import Format, Phase

_FROM_CATALOGUE = ("roads", "map_size", "ai")  # facts the template states as a default and what is allowed


@dataclass(frozen=True)
class Settings:
    timer: str | None = None
    roads: str | None = None  # "none", or road types such as "mid" or "slow+mid"
    map_size: str | None = None  # such as "L" or "L+U"
    ai: int | None = None  # computer players
    sim_turns: str | None = None  # the recommended last day of simultaneous turns, such as "117"
    mirror: bool = False  # both players play the same town
    built_in: bool = False  # the template comes with HotA
    download: str | None = None  # where to download the template, if it has to be downloaded
    description: str | None = None  # what the template is, as its catalogue entry says
    additional_rules: str | None = None  # additional rules for this template: the template's own, or what the tournament wrote instead


def effective_settings(fmt: Format, phase: Phase, template: str, catalogue: Catalogue) -> Settings:
    """The settings of `template` when it is played in `phase` of `fmt`."""
    entry = catalogue.find(template)
    if entry is None:
        raise ValueError(f"{template!r} is not a template of the catalogue")
    in_list = next((e for e in fmt.templates if e.template == template), None)
    in_pool = next((e for e in phase.pool if e.template == template), None)
    if in_list is None:
        raise ValueError(f"{template!r} is not one of the templates of {fmt.name}")
    if in_pool is None:
        raise ValueError(f"{template!r} is not in the pool of the phase {phase.name!r}")

    facts = entry.details
    values = {name: facts[name].default for name in _FROM_CATALOGUE if name in facts}
    for name in ("sim_turns", "additional_rules"):
        if name in facts:
            values[name] = facts[name]
    for written in (fmt.settings, in_list.settings, in_pool.settings):  # least to most specific
        values.update(written)
    # A tournament that gives a download link plays another version than the one in HotA, so it is not built in.
    chosen_download = values.pop("download", None)
    return Settings(
        **values,
        mirror=bool(facts.get("mirror")),
        built_in=bool(facts.get("built_in")) and chosen_download is None,
        download=chosen_download or facts.get("download"),
        description=facts.get("description"),
    )
