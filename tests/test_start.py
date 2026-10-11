import pytest

from rules.start import StartError, check_opponent

PLAYER, OTHER = 1, 2


def test_another_human_is_accepted():
    check_opponent(PLAYER, OTHER, opponent_is_bot=False)  # no error


def test_yourself_is_refused():
    with pytest.raises(StartError, match="yourself"):
        check_opponent(PLAYER, PLAYER, opponent_is_bot=False)


def test_a_bot_is_refused():
    with pytest.raises(StartError, match="bot"):
        check_opponent(PLAYER, OTHER, opponent_is_bot=True)
