import pytest

from state import (
    Match,
    MatchError,
    Record,
    RecordError,
    check_player,
    describe,
    describe_match,
    describe_records,
    make_record,
    parse,
    players_of,
    rebuild,
    tag,
)

# Discord user ids are 64-bit numbers
ANNA, BORIS = 111111111111111111, 222222222222222222

# The mode, phase and template a match starts with (no template: bans and picks choose them)
MODE = {"mode": "sample-cup", "phase": "Main", "template": None}
WORDS = "Mode: Sample Cup (`sample-cup`), phase `Main`."


def started(p1, p2, **more):
    return make_record(1, "match_started", p1=p1, p2=p2, **{**MODE, **more})


def test_tag_shows_the_number_and_the_code():
    assert tag(started(1, 2)) == "[#1 ms]"
    assert tag(make_record(12, "coinflip", winner=1)) == "[#12 cf]"


def test_match_started_reads_both_players_the_mode_and_the_phase():
    record = parse(f"[#1 ms] Match started: <@111> vs <@222>. {WORDS} This is your match thread.")
    assert record == started(111, 222)


def test_match_started_reads_the_agreed_template_when_there_is_one():
    record = parse("[#1 ms] <@1> vs <@2>. Mode: Ranked (`ranked`), phase `Main`, template `JC`.")
    assert record.data["template"] == "JC"


def test_big_discord_ids_are_not_changed():
    record = parse(f"[#1 ms] <@{ANNA}> vs <@{BORIS}> `sample-cup` `Main`")
    assert (record.data["p1"], record.data["p2"]) == (ANNA, BORIS)


def test_wording_around_the_data_is_free():
    assert parse("[#2 ms] <@1> and <@2> are playing `sample-cup` in `Main`") == make_record(2, "match_started", p1=1, p2=2, **MODE)
    assert parse("[#2 ms] <@1><@2>`sample-cup``Main`").data["phase"] == "Main"


def test_message_over_several_lines_is_read_the_same():
    text = "[#3 ms] Match started!\n<@1> vs <@2>\n`sample-cup`, `Main`\nGood luck."
    assert parse(text).data == {"p1": 1, "p2": 2, **MODE}


def test_mentions_after_the_data_are_not_read():
    # Only the first two mentions are the players; prose may mention anyone else.
    record = parse("[#1 ms] <@1> vs <@2> `sample-cup` `Main`. Ask <@999> if you need help.")
    assert (record.data["p1"], record.data["p2"]) == (1, 2)


def test_nickname_style_mentions_are_read():
    assert parse("[#1 ms] <@!1> vs <@!2> `sample-cup` `Main`").data["p1"] == 1


def test_record_number_is_read():
    assert parse("[#27 ms] <@1> vs <@2> `sample-cup` `Main`").n == 27


def test_coinflip_reads_the_winner():
    assert parse("[#2 cf] Coinflip: <@222> wins and is A, so <@222> bans first. <@111> is B.") == make_record(
        2, "coinflip", winner=222
    )


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
        parse("[#1 ms] Match started: <@1> only `sample-cup` `Main`")
    with pytest.raises(RecordError, match="both players"):
        parse("[#1 ms] Match started")


def test_match_started_without_mode_and_phase_is_reported():
    with pytest.raises(RecordError, match="mode and the phase"):
        parse("[#1 ms] Match started: <@1> vs <@2>")
    with pytest.raises(RecordError, match="mode and the phase"):
        parse("[#1 ms] Match started: <@1> vs <@2> `sample-cup`")


def test_coinflip_without_a_winner_is_reported():
    with pytest.raises(RecordError, match="mention the winner"):
        parse("[#2 cf] Coinflip: nobody")


def test_missing_or_extra_data_is_reported():
    with pytest.raises(RecordError, match="needs exactly"):
        make_record(1, "match_started", p1=1)
    with pytest.raises(RecordError, match="needs exactly"):
        make_record(1, "coinflip", winner=1, loser=2)


def test_unknown_record_type_is_reported():
    with pytest.raises(RecordError, match="unknown record type"):
        make_record(1, "teleport")


def test_records_with_the_same_content_are_equal():
    assert started(1, 2) == Record(1, "match_started", {"p1": 1, "p2": 2, **MODE})


def test_match_started_is_described_with_players_mode_and_phase():
    assert describe(started(111, 222)) == "match started: <@111> vs <@222>, mode sample-cup, phase Main"
    assert describe(started(111, 222, template="JC")).endswith(", template JC")


def test_coinflip_is_described_with_its_winner():
    assert describe(make_record(2, "coinflip", winner=222)) == "coinflip won by <@222>"


def test_unknown_types_are_still_described():
    assert describe(Record(2, "something_new", {"x": 1})) == "something_new {'x': 1}"


def test_records_are_listed_in_order_with_their_numbers():
    text = describe_records([started(111, 222), Record(2, "something_new", {})])
    assert text.splitlines() == [
        "I read 2 record(s) in this thread:",
        "1. match started: <@111> vs <@222>, mode sample-cup, phase Main",
        "2. something_new {}",
    ]


def test_no_records_is_explained():
    assert describe_records([]) == "I found no match records in this thread."


def match_records():
    return [started(111, 222)]


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


# --- rebuilding the match from its records ---------------------------------------------------------------


def clean_run():
    return [started(111, 222), make_record(2, "coinflip", winner=222)]


def test_a_clean_run_is_rebuilt():
    assert rebuild(clean_run()) == Match(111, 222, "sample-cup", "Main", None, a=222, b=111)


def test_the_loser_of_the_coinflip_is_b_whoever_started_the_match():
    assert rebuild([started(111, 222), make_record(2, "coinflip", winner=111)]).b == 222


def test_the_agreed_template_is_kept():
    match = rebuild([started(1, 2, template="JC"), make_record(2, "coinflip", winner=1)])
    assert match.template == "JC"


def test_a_thread_without_records_is_not_a_match():
    with pytest.raises(MatchError, match="not a match thread"):
        rebuild([])


def test_a_deleted_start_is_reported_as_a_missing_message():
    with pytest.raises(RecordError, match="message #1 of this match is missing"):
        rebuild([make_record(2, "coinflip", winner=1)])


def test_a_deleted_message_in_the_middle_is_reported_by_number():
    records = [started(1, 2), make_record(2, "coinflip", winner=1), make_record(4, "coinflip", winner=1)]
    with pytest.raises(RecordError, match="message #3 of this match is missing"):
        rebuild(records)


def test_a_deleted_coinflip_is_reported():
    with pytest.raises(RecordError, match="coinflip of this match was not recorded"):
        rebuild([started(1, 2)])


def test_a_second_start_is_reported_not_guessed():
    records = [started(1, 2), make_record(2, "match_started", p1=3, p2=4, **MODE), make_record(3, "coinflip", winner=1)]
    with pytest.raises(RecordError, match="2 match start messages"):
        rebuild(records)


def test_a_second_coinflip_is_reported_not_guessed():
    records = [started(1, 2), make_record(2, "coinflip", winner=1), make_record(3, "coinflip", winner=2)]
    with pytest.raises(RecordError, match="2 coinflip messages"):
        rebuild(records)


def test_a_repeated_number_is_reported():
    records = [started(1, 2), make_record(1, "coinflip", winner=1)]
    with pytest.raises(RecordError, match="message #1 appears twice"):
        rebuild(records)


def test_a_coinflip_won_by_a_stranger_is_reported():
    with pytest.raises(RecordError, match="not a player"):
        rebuild([started(1, 2), make_record(2, "coinflip", winner=3)])


def test_the_match_is_described_in_words():
    assert describe_match(rebuild(clean_run())).splitlines() == [
        "Match: <@111> vs <@222>",
        "Mode sample-cup, phase Main",
        "Coinflip: <@222> is A (acts first), <@111> is B",
    ]
