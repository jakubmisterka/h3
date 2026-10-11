import pytest

from state import (
    MatchError,
    Record,
    RecordError,
    check_player,
    describe,
    describe_records,
    make_record,
    parse,
    players_of,
    tag,
)

# Discord user ids are 64-bit numbers
ANNA, BORIS = 111111111111111111, 222222222222222222


def test_tag_shows_the_number_and_the_code():
    assert tag(make_record(1, "match_started", p1=1, p2=2)) == "[#1 ms]"
    assert tag(make_record(12, "match_started", p1=1, p2=2)) == "[#12 ms]"


def test_match_started_reads_both_players_from_the_mentions():
    record = parse("[#1 ms] Match started: <@111> vs <@222>. This is your match thread.")
    assert record == make_record(1, "match_started", p1=111, p2=222)


def test_big_discord_ids_are_not_changed():
    record = parse(f"[#1 ms] <@{ANNA}> vs <@{BORIS}>")
    assert record.data == {"p1": ANNA, "p2": BORIS}


def test_wording_around_the_data_is_free():
    assert parse("[#2 ms] <@1> and <@2> are playing").data == {"p1": 1, "p2": 2}
    assert parse("[#2 ms] <@1><@2>").data == {"p1": 1, "p2": 2}


def test_message_over_several_lines_is_read_the_same():
    text = "[#3 ms] Match started!\n<@1> vs <@2>\nGood luck."
    assert parse(text).data == {"p1": 1, "p2": 2}


def test_mentions_after_the_data_are_not_read():
    # Only the first two mentions are the players; prose may mention anyone else.
    assert parse("[#1 ms] <@1> vs <@2>. Ask <@999> if you need help.").data == {"p1": 1, "p2": 2}


def test_nickname_style_mentions_are_read():
    assert parse("[#1 ms] <@!1> vs <@!2>").data == {"p1": 1, "p2": 2}


def test_record_number_is_read():
    assert parse("[#27 ms] <@1> vs <@2>").n == 27


def test_ordinary_text_is_not_a_record():
    assert parse("Anna and Boris, this is your match thread.") is None
    assert parse("") is None


def test_a_tag_that_is_not_at_the_start_is_not_a_record():
    assert parse("Look at [#1 ms] <@1> vs <@2>") is None


def test_text_that_only_looks_a_little_like_a_tag_is_not_a_record():
    assert parse("[#x ms] <@1> vs <@2>") is None
    assert parse("[1 ms] <@1> vs <@2>") is None
    assert parse("#1 ms <@1> vs <@2>") is None


def test_unknown_code_is_reported():
    with pytest.raises(RecordError, match="unknown record code 'zz'"):
        parse("[#1 zz] something")


def test_match_started_without_two_players_is_reported():
    with pytest.raises(RecordError, match="both players"):
        parse("[#1 ms] Match started: <@1> only")
    with pytest.raises(RecordError, match="both players"):
        parse("[#1 ms] Match started")


def test_missing_or_extra_data_is_reported():
    with pytest.raises(RecordError, match="needs exactly"):
        make_record(1, "match_started", p1=1)
    with pytest.raises(RecordError, match="needs exactly"):
        make_record(1, "match_started", p1=1, p2=2, p3=3)


def test_unknown_record_type_is_reported():
    with pytest.raises(RecordError, match="unknown record type"):
        make_record(1, "teleport")


def test_records_with_the_same_content_are_equal():
    assert make_record(1, "match_started", p1=1, p2=2) == Record(1, "match_started", {"p1": 1, "p2": 2})


def test_match_started_is_described_with_both_players():
    assert describe(make_record(1, "match_started", p1=111, p2=222)) == "match started: <@111> vs <@222>"


def test_unknown_types_are_still_described():
    assert describe(Record(2, "something_new", {"x": 1})) == "something_new {'x': 1}"


def test_records_are_listed_in_order_with_their_numbers():
    text = describe_records([make_record(1, "match_started", p1=111, p2=222), Record(2, "something_new", {})])
    assert text.splitlines() == [
        "I read 2 record(s) in this thread:",
        "1. match started: <@111> vs <@222>",
        "2. something_new {}",
    ]


def test_no_records_is_explained():
    assert describe_records([]) == "I found no match records in this thread."


def match_records():
    return [make_record(1, "match_started", p1=111, p2=222)]


def test_players_are_the_two_in_the_start_record():
    assert players_of(match_records()) == (111, 222)


def test_both_players_pass_the_check():
    check_player(match_records(), 111)
    check_player(match_records(), 222)


def test_somebody_else_is_refused():
    with pytest.raises(MatchError, match="Only the two players"):
        check_player(match_records(), 333)


def test_thread_without_a_start_record_is_not_a_match():
    with pytest.raises(MatchError, match="not a match thread"):
        players_of([])
    with pytest.raises(MatchError, match="not a match thread"):
        check_player([], 111)
