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
    effective_records,
    make_record,
    parse,
    pending_undo,
    players_of,
    rebuild,
    steps_that_count,
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


# --- the game marker in the tag ----------------------------------------------------------------------------


def test_a_record_of_a_game_shows_the_game_in_its_tag():
    assert tag(make_record(7, "coinflip", game=1, winner=1)) == "[#7 cf g1]"
    assert tag(make_record(7, "coinflip", winner=1)) == "[#7 cf]"


def test_the_game_marker_is_read_back():
    record = parse("[#7 cf g2] Coinflip: <@1> wins")
    assert (record.n, record.game, record.data) == (7, 2, {"winner": 1})


def test_a_record_without_a_marker_belongs_to_no_game():
    assert parse("[#7 cf] Coinflip: <@1> wins").game is None


def test_the_same_data_in_another_game_is_another_record():
    assert make_record(1, "coinflip", game=1, winner=1) != make_record(1, "coinflip", game=2, winner=1)


def test_a_malformed_game_marker_is_not_a_record():
    assert parse("[#7 cf g] Coinflip: <@1> wins") is None
    assert parse("[#7 cf gx] Coinflip: <@1> wins") is None
    assert parse("[#7 cf g1 g2] Coinflip: <@1> wins") is None


# --- the trade records --------------------------------------------------------------------------------------------


def test_the_trade_started_record_reads_the_pair():
    record = parse("[#5 tr g1] Game 1: the trade starts. Pair: Necropolis (`necropolis`) vs Tower (`tower`)")
    assert record == make_record(5, "trade_started", game=1, pair=("necropolis", "tower"))


def test_a_trade_started_record_without_two_towns_is_reported():
    with pytest.raises(RecordError, match="two towns"):
        parse("[#5 tr g1] the trade starts with `necropolis`")


def test_a_reopened_trade_needs_no_data():
    assert parse("[#6 tu g1] Game 1 continues") == make_record(6, "trade_resumed", game=1)


def test_a_town_bid_record_reads_reporter_winner_amount_and_town():
    record = parse("[#7 tb g2] <@1> reports: <@2> won the town bid at `2100` gold and chose Tower (`tower`)")
    assert record == make_record(7, "town_bid", game=2, reporter=1, winner=2, amount=2100, town="tower")


def test_a_color_bid_record_reads_the_color():
    record = parse("[#8 cb g2] <@1> reports: <@1> won the color bid at `0` gold and chose `red`")
    assert record == make_record(8, "color_bid", game=2, reporter=1, winner=1, amount=0, color="red")


def test_a_bid_record_with_a_damaged_amount_is_reported():
    with pytest.raises(RecordError, match="whole number"):
        parse("[#7 tb g2] <@1> reports: <@2> won at `lots` and chose `tower`")
    with pytest.raises(RecordError, match="reporter and the winner"):
        parse("[#7 tb g2] <@1> reports at `2100` and chose `tower`")


def test_a_trade_record_is_described_with_its_game():
    assert describe(make_record(5, "trade_started", game=1, pair=("necropolis", "tower"))) == "game 1: trade started, necropolis vs tower"
    assert describe(make_record(7, "town_bid", game=2, reporter=1, winner=2, amount=2100, town="tower")) == (
        "game 2: <@2> won the town bid at 2100, chose tower"
    )


def test_the_trade_records_are_kept_in_order_by_the_rebuilt_match():
    trade = [
        make_record(3, "trade_started", game=1, pair=("castle", "tower")),
        make_record(4, "town_bid", game=1, reporter=111, winner=111, amount=100, town="castle"),
    ]
    assert rebuild(clean_run() + trade).trade_records == tuple(trade)


def test_a_trade_record_without_a_game_is_reported():
    with pytest.raises(RecordError, match="does not say which game"):
        rebuild(clean_run() + [make_record(3, "trade_started", pair=("castle", "tower"))])


def test_a_trade_before_the_coinflip_is_reported():
    records = [started(111, 222), make_record(2, "trade_started", game=1, pair=("castle", "tower")), make_record(3, "coinflip", winner=222)]
    with pytest.raises(RecordError, match="before the coinflip"):
        rebuild(records)


# --- the roll records ---------------------------------------------------------------------------------------------


def test_a_roll_record_reads_the_roller_the_bans_and_the_new_pair():
    text = "[#6 rl g1] Game 1 - <@1> rolled, banning Castle (`castle`), and paid 500 gold. New pair: Cove (`cove`) vs Tower (`tower`)."
    assert parse(text) == make_record(6, "roll", game=1, player=1, bans=("castle",), pair=("cove", "tower"))


def test_a_roll_without_bans_has_none():
    text = "[#6 rl g1] Game 1 - <@1> rolled without banning a town. New pair: Cove (`cove`) vs Tower (`tower`)."
    assert parse(text).data["bans"] == ()


def test_a_roll_with_two_bans_reads_both():
    text = "[#6 rl g2] <@2> rolled, banning Castle (`castle`), Tower (`tower`). New pair: `cove` vs `fortress`"
    assert parse(text).data == {"player": 2, "bans": ("castle", "tower"), "pair": ("cove", "fortress")}


def test_a_roll_record_that_cannot_be_read_is_reported():
    with pytest.raises(RecordError, match="new pair"):
        parse("[#6 rl g1] <@1> rolled and `castle`")
    with pytest.raises(RecordError, match="mention the player"):
        parse("[#6 rl g1] rolled. New pair: `cove` vs `tower`")


def test_a_skipped_roll_record_reads_the_player():
    assert parse("[#7 rs g1] Game 1 - <@2> skips the rolls.") == make_record(7, "roll_skipped", game=1, player=2)
    with pytest.raises(RecordError, match="mention the player"):
        parse("[#7 rs g1] skips")


def test_roll_records_are_described():
    assert describe(make_record(6, "roll", game=1, player=1, bans=("castle",), pair=("cove", "tower"))) == (
        "game 1: <@1> rolled, banning castle, new pair cove vs tower"
    )
    assert describe(make_record(6, "roll", game=1, player=1, bans=(), pair=("cove", "tower"))) == (
        "game 1: <@1> rolled, new pair cove vs tower"
    )
    assert describe(make_record(7, "roll_skipped", game=1, player=2)) == "game 1: <@2> skipped the roll"


def test_the_roll_records_are_kept_by_the_rebuilt_match():
    rolls = [make_record(3, "roll", game=1, player=111, bans=(), pair=("cove", "tower"))]
    assert rebuild(clean_run() + rolls).trade_records == tuple(rolls)


# --- the undo records -----------------------------------------------------------------------------------------------


def test_an_undo_request_reads_the_player_and_the_record_number():
    text = "[#9 ur] <@1> asks to undo from record `8`. <@2> confirms with /match undo."
    assert parse(text) == make_record(9, "undo_requested", player=1, start=8)


def test_an_undo_confirmation_reads_the_player_and_the_record_number():
    text = "[#10 ud] <@2> agreed: the match is back to how it was before record `8`."
    assert parse(text) == make_record(10, "undone", player=2, start=8)


def test_an_undo_record_that_cannot_be_read_is_reported():
    with pytest.raises(RecordError, match="record number"):
        parse("[#9 ur] <@1> asks to undo from record `eight`")
    with pytest.raises(RecordError, match="record number"):
        parse("[#9 ur] asks to undo from record `8`")
    with pytest.raises(RecordError, match="record number"):
        parse("[#9 ud] <@1> agreed")


def test_undo_records_are_described():
    assert describe(make_record(9, "undo_requested", player=1, start=8)) == "<@1> asks to undo everything from record 8"
    assert describe(make_record(10, "undone", player=2, start=8)) == "<@2> agreed to undo everything from record 8"


# --- which records still count --------------------------------------------------------------------------------------------


def ban(n, template="JC", player=111):
    return make_record(n, "ban", player=player, template=template)


def ask(n, start, player=111):
    return make_record(n, "undo_requested", player=player, start=start)


def agree(n, start, player=222):
    return make_record(n, "undone", player=player, start=start)


def numbers(records):
    return [r.n for r in records]


def test_without_undos_every_record_counts():
    records = clean_run() + [ban(3), ban(4, "6lm10a", 222)]
    assert effective_records(records) == records


def test_a_request_alone_changes_nothing_and_is_not_a_step_itself():
    records = clean_run() + [ban(3), ban(4, "6lm10a", 222), ask(5, 4)]
    assert numbers(effective_records(records)) == [1, 2, 3, 4]


def test_an_agreed_undo_drops_that_record_and_everything_after_it():
    records = clean_run() + [ban(3), ban(4, "6lm10a", 222), ban(5, "h3dm1"), ask(6, 4), agree(7, 4)]
    assert numbers(effective_records(records)) == [1, 2, 3]


def test_the_latest_step_can_be_undone_alone():
    records = clean_run() + [ban(3), ban(4, "6lm10a", 222), ask(5, 4), agree(6, 4)]
    assert numbers(effective_records(records)) == [1, 2, 3]


def test_records_posted_after_an_undo_count_again():
    records = clean_run() + [ban(3), ask(4, 3), agree(5, 3), ban(6, "Diamond")]
    assert numbers(effective_records(records)) == [1, 2, 6]


def test_a_second_undo_can_go_back_further():
    records = clean_run() + [ban(3), ban(4, "6lm10a", 222), ask(5, 4), agree(6, 4), ask(7, 3, 222), agree(8, 3, 111)]
    assert numbers(effective_records(records)) == [1, 2]


def test_the_start_and_the_coinflip_cannot_be_undone():
    for start in (1, 2):
        records = clean_run() + [ban(3), ask(4, start), agree(5, start)]
        with pytest.raises(RecordError, match=f"from record {start}, which is not a step that counts"):
            effective_records(records)


def test_a_record_that_does_not_exist_or_was_already_undone_cannot_be_undone():
    with pytest.raises(RecordError, match="from record 9, which is not a step that counts"):
        effective_records(clean_run() + [ban(3), ask(4, 9), agree(5, 9)])
    already = clean_run() + [ban(3), ask(4, 3), agree(5, 3), ask(6, 3, 222), agree(7, 3, 111)]
    with pytest.raises(RecordError, match="from record 3, which is not a step that counts"):
        effective_records(already)


@pytest.mark.parametrize(
    "records",
    [
        [ban(3), agree(4, 3)],  # nobody asked
        [ban(3), ask(4, 3), ban(5, "6lm10a", 222), agree(6, 3)],  # something was posted in between
        [ban(3), ask(4, 3), agree(5, 3, player=111)],  # the same player cannot confirm their own request
        [ban(3), ask(4, 3), agree(5, 2)],  # another record number than the request
    ],
)
def test_an_undo_that_was_not_asked_for_by_the_other_player_is_reported(records):
    with pytest.raises(RecordError, match="did not just ask to undo"):
        effective_records(clean_run() + records)


def test_the_pending_request_is_the_last_record_if_it_is_a_request():
    records = clean_run() + [ban(3), ask(4, 3)]
    assert pending_undo(records) == ask(4, 3)
    assert pending_undo(records + [ban(5, "6lm10a", 222)]) is None
    assert pending_undo(clean_run() + [ban(3), ask(4, 3), agree(5, 3)]) is None
    assert pending_undo([]) is None


def test_the_steps_that_count_leave_out_the_start_the_coinflip_and_the_undo_records():
    records = clean_run() + [ban(3), ban(4, "6lm10a", 222), ask(5, 4), agree(6, 4), ban(7, "h3dm1", 222)]
    assert numbers(steps_that_count(records)) == [3, 7]


# --- the match after undos ------------------------------------------------------------------------------------------------


def test_an_undone_ban_is_no_longer_taken():
    records = clean_run() + [ban(3), ban(4, "6lm10a", 222), ask(5, 4), agree(6, 4)]
    assert rebuild(records).taken == ((111, "ban", "JC"),)


def test_trades_after_an_undone_step_no_longer_count_either():
    trade = [
        make_record(4, "trade_started", game=1, pair=("castle", "tower")),
        make_record(5, "town_bid", game=1, reporter=111, winner=111, amount=100, town="castle"),
    ]
    records = clean_run() + [make_record(3, "pick", player=111, template="JC")] + trade + [ask(6, 3, 222), agree(7, 3, 111)]
    match = rebuild(records)
    assert match.taken == () and match.trade_records == ()


def test_a_pending_request_changes_nothing_in_the_match():
    with_request = clean_run() + [ban(3), ask(4, 3)]
    assert rebuild(with_request) == rebuild(clean_run() + [ban(3)])


def test_the_numbering_is_still_checked_over_every_record_including_the_undo_ones():
    records = clean_run() + [ban(3), ask(4, 3), agree(6, 3)]  # record 5 is missing
    with pytest.raises(RecordError, match="message #5 of this match is missing"):
        rebuild(records)


def test_a_thread_with_an_undo_that_cannot_be_trusted_is_refused():
    with pytest.raises(RecordError, match="did not just ask to undo"):
        rebuild(clean_run() + [ban(3), agree(4, 3)])
