import pytest

from rules.template_facts import announcement_lines, fixed_lines, info_hint, lobby_lines, setting_line, setting_value
from rules.template_settings import Settings
from rules.trade_kinds import check_trade

STANDARD = "Trade: town roll, then a bid for the town and for the color."

ALL = Settings(
    timer="12:00+06:00+02:00",
    roads="slow+mid",
    map_size="L+U",
    ai=3,
    sim_turns="117",
    mirror=True,
    download="https://example.com/jc",
)


def test_a_template_with_nothing_stated_has_no_lines():
    assert lobby_lines(Settings()) == [] and fixed_lines(Settings()) == []
    assert announcement_lines(Settings()) == [STANDARD]  # only how the trade is run is always said


@pytest.mark.parametrize(
    "change, line",
    [
        ({"timer": "12:00+06:00+02:00"}, "Timer: 12:00+06:00+02:00"),
        ({"map_size": "XL+U"}, "Map: XL+U"),
        ({"map_size": "M"}, "Map: M"),
        ({"roads": "mid"}, "Roads: mid"),
        ({"roads": "slow+mid"}, "Roads: slow+mid"),
        ({"roads": "none"}, "No roads"),
        ({"ai": 6}, "AI players: 6"),
        ({"ai": 0}, "No AI players"),
        ({"sim_turns": "117"}, "Sim turns until 117"),
        ({"sim_turns": "121"}, "Sim turns until 121"),
        ({"mirror": True}, "Mirror: both players get the same town"),
    ],
)
def test_each_setting_line_is_short(change, line):
    name = next(iter(change))
    assert setting_line(name, Settings(**change)) == line if name != "mirror" else fixed_lines(Settings(**change)) == [line]


def test_what_is_announced_is_only_what_players_need():
    assert announcement_lines(ALL, "More: /info") == [
        "Not built into HotA: [download](<https://example.com/jc>)",
        "Timer: `12:00+06:00+02:00`",
        "Sim turns: `117`",
        "Trade: one town for both players; town roll, then a bid for the color.",
        "More: /info",
    ]


def test_the_map_the_roads_the_computer_players_and_the_mirror_are_not_announced():
    text = " ".join(announcement_lines(Settings(map_size="XL+U", roads="mid", ai=6, mirror=True)))
    assert "XL+U" not in text and "Roads" not in text and "AI" not in text and "Mirror" not in text


def test_a_template_built_into_hota_has_no_line_about_where_to_get_it():
    assert not any("HotA" in line for line in announcement_lines(Settings(built_in=True)))
    assert not any("HotA" in line for line in announcement_lines(Settings()))  # unknown is not said either


def test_a_download_link_is_a_hyperlink_without_a_preview():
    assert announcement_lines(Settings(download="https://example.com/x"))[0] == "Not built into HotA: [download](<https://example.com/x>)"


def test_the_timer_is_in_code_and_never_spelled_out():
    [line] = [line for line in announcement_lines(Settings(timer="12:00+06:00+02:00")) if line.startswith("Timer")]
    assert line == "Timer: `12:00+06:00+02:00`" and "start" not in line and "turn" not in line


def test_the_trade_rule_follows_the_kind():
    lines = announcement_lines(Settings(trade=check_trade("standard_with_ai_packs")))
    assert lines == ["Trade: town roll (a pair of towns and two packs of AI towns), then a bid for the town, for a pack and for the color."]


def test_how_to_find_out_more_is_said_last_when_asked_for():
    assert announcement_lines(Settings(timer="12:00+06:00+02:00"), info_hint("cup", "JC"))[-1] == (
        "More about this template: /info with mode `cup` and template `JC`"
    )


def test_built_in_and_a_download_are_never_both_said():
    assert fixed_lines(Settings(built_in=True, download="https://example.com/x")) == ["Built into HotA"]


def test_the_lobby_lines_are_only_what_is_typed_into_the_lobby():
    assert lobby_lines(ALL) == ["Timer: 12:00+06:00+02:00", "Map: L+U", "Roads: slow+mid", "AI players: 3"]
    assert lobby_lines(Settings(sim_turns="117", mirror=True, built_in=True)) == []


def test_the_lobby_lines_skip_what_is_not_stated():
    assert lobby_lines(Settings(map_size="M", ai=0)) == ["Map: M", "No AI players"]


def test_the_value_of_a_setting_is_short_text_or_nothing():
    assert setting_value("ai", Settings(ai=6)) == "6"
    assert setting_value("map_size", Settings(map_size="XL+U")) == "XL+U"
    assert setting_value("timer", Settings()) is None
    assert setting_line("timer", Settings()) is None
