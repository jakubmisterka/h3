import pytest

from rules.template_facts import fact_lines, fixed_lines, lobby_lines, setting_line, setting_value
from rules.template_settings import Settings

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
    assert fact_lines(Settings()) == [] and lobby_lines(Settings()) == [] and fixed_lines(Settings()) == []


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
        ({"built_in": True}, "Built into HotA"),
        ({"download": "https://example.com/jc"}, "Download: <https://example.com/jc>"),
    ],
)
def test_each_fact_alone_is_one_short_line(change, line):
    assert fact_lines(Settings(**change)) == [line]


def test_the_timer_is_never_spelled_out():
    [line] = fact_lines(Settings(timer="12:00+06:00+02:00"))
    assert line == "Timer: 12:00+06:00+02:00" and "start" not in line and "turn" not in line


def test_all_the_facts_come_in_a_fixed_order():
    assert fact_lines(ALL) == [
        "Mirror: both players get the same town",
        "Download: <https://example.com/jc>",
        "Timer: 12:00+06:00+02:00",
        "Map: L+U",
        "Roads: slow+mid",
        "AI players: 3",
        "Sim turns until 117",
    ]


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
