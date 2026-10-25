import pytest

from rules.lobby_values import (
    check_computer_players,
    check_game_date,
    check_map_size,
    check_roads,
    check_timer,
    has_underground,
)

# --- the timer ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["12:00+06:00+02:00", "00:30+00:10+00:05", "99:59+59:59+59:59"])
def test_a_timer_in_the_form_is_accepted_and_kept_as_written(text):
    assert check_timer(text) == text


@pytest.mark.parametrize(
    "text", ["12 minutes", "12:00+06:00", "12:00+6:00+02:00", "12:00+06:00+02", "12:00 + 06:00 + 02:00", "1:00+06:00+02:00", "", "12:00+06:00+02:00+01:00", "120:00+10:00+05:30"]
)
def test_a_timer_in_another_form_is_refused_and_the_form_is_shown(text):
    with pytest.raises(ValueError, match=r"is not a timer: a timer is written like 12:00\+06:00\+02:00"):
        check_timer(text)


def test_seconds_must_be_below_sixty():
    with pytest.raises(ValueError, match="seconds must be below 60"):
        check_timer("12:75+06:00+02:00")
    with pytest.raises(ValueError, match="seconds must be below 60"):
        check_timer("12:00+06:00+02:60")


def test_a_timer_that_is_not_text_is_refused():
    with pytest.raises(ValueError, match="is not a timer"):
        check_timer(1200)


# --- the game date ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["117", "121", "111", "447", "1214", "2427", "10147"])
def test_a_date_in_the_form_is_accepted(text):
    assert check_game_date(text) == text


@pytest.mark.parametrize("text, problem", [("118", "day"), ("110", "day"), ("151", "week"), ("101", "week"), ("017", "month"), ("007", "week")])
def test_a_day_week_or_month_out_of_range_names_which_one(text, problem):
    with pytest.raises(ValueError, match=f"the {problem}"):
        check_game_date(text)


@pytest.mark.parametrize("text", ["week 1", "1-1-7", "17", "", "11 7", "abc", 117])
def test_a_date_not_in_digits_shows_the_form(text):
    with pytest.raises(ValueError, match="write month, week and day in digits, like 117"):
        check_game_date(text)


# --- the roads -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["none", "slow", "mid", "fast", "slow+mid", "mid+fast", "slow+fast", "slow+mid+fast"])
def test_a_road_setting_is_none_or_road_types_in_order(text):
    assert check_roads(text) == text


@pytest.mark.parametrize("text", ["paved", "mid+slow", "mid+mid", "none+mid", "dirt", "slow+", "+mid", "", "Mid", None])
def test_another_road_setting_is_refused_with_the_form(text):
    with pytest.raises(ValueError, match="use none, or slow, mid and fast joined by"):
        check_roads(text)


# --- the map size --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["S", "M", "L", "XL", "H", "XH", "G", "L+U", "XH+U", "G+U", "S+U"])
def test_a_map_size_with_or_without_underground_is_accepted(text):
    assert check_map_size(text) == text


@pytest.mark.parametrize("text", ["XXL", "L+X", "l", "L+u", "L +U", "U", "+U", "", "L+U+U", 5])
def test_another_map_size_is_refused_and_the_sizes_listed(text):
    with pytest.raises(ValueError, match="use one of S, M, L, XL, H, XH, G"):
        check_map_size(text)


def test_underground_is_told_from_the_plus_u():
    assert has_underground("L+U") and not has_underground("L")


# --- computer players ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", [0, 1, 3, 6])
def test_from_zero_to_six_computer_players_are_accepted(value):
    assert check_computer_players(value) == value


@pytest.mark.parametrize("value", [-1, 7, 8, 2.5, "3", None, True])
def test_other_numbers_of_computer_players_are_refused_and_the_limit_explained(value):
    with pytest.raises(ValueError, match="a whole number from 0 to 6.*at most 8 players, two of them human"):
        check_computer_players(value)
