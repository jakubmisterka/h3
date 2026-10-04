import pytest

from rules.formats import parse_format
from state import Event, StateError, decode, encode, fold, make_event

P1, P2 = 111111111111111111, 222222222222222222  # Discord ids are 64-bit


@pytest.fixture
def formats(el_classico, templates, factions):
    return {"el-classico": parse_format(el_classico, templates, factions)}


def start(n=1, **extra):
    return make_event(n, "match_started", format="el-classico", phase="Main", p1=P1, p2=P2, **extra)


def clean_run():
    return [
        start(),
        make_event(2, "coinflip", a=P2, b=P1),
        make_event(3, "ban", by=P2, template="JC"),
        make_event(4, "ban", by=P1, template="h3dm1"),
        make_event(5, "pair_drawn", game=1, pair=["castle", "factory"]),
    ]


# --- encode / decode -------------------------------------------------------


def test_round_trip_keeps_every_field():
    event = make_event(7, "faction_bid", game=1, by=P1, winner=P2, amount=2100, faction="necropolis")
    assert decode(encode(event)) == event


def test_64_bit_ids_survive_the_round_trip():
    event = make_event(2, "coinflip", a=P1, b=P2)
    assert decode(encode(event)).data == {"a": P1, "b": P2}


def test_encoded_event_is_short_enough_for_an_embed_footer():
    event = make_event(1, "match_started", format="el-classico", phase="Main", p1=P1, p2=P2, template="JC")
    assert len(encode(event)) < 2048


def test_ordinary_text_is_not_an_event():
    assert decode("A banned JC") is None


def test_damaged_event_raises():
    with pytest.raises(StateError, match="damaged"):
        decode("h3:{not json")
    with pytest.raises(StateError, match="damaged"):
        decode('h3:{"t":"ban"}')  # no number


def test_unknown_event_type_raises():
    with pytest.raises(StateError, match="unknown event type"):
        decode('h3:{"n":3,"t":"teleport"}')


def test_event_missing_a_field_raises():
    with pytest.raises(StateError, match="missing template"):
        decode('h3:{"n":3,"t":"ban","by":1}')


# --- fold ------------------------------------------------------------------


def test_clean_run_is_rebuilt(formats):
    match = fold(clean_run(), formats)
    assert match.players == (P1, P2)
    assert (match.a, match.b) == (P2, P1)
    assert [(e.type, e.data["template"]) for e in match.selection] == [("ban", "JC"), ("ban", "h3dm1")]
    assert match.trade[1][0].type == "pair_drawn"
    assert match.last_n == 5
    assert match.phase.name == "Main"


def test_helpers_name_the_sides(formats):
    match = fold(clean_run(), formats)
    assert match.side_of(P2) == "A" and match.side_of(P1) == "B"
    assert match.user_of("A") == P2
    assert match.other(P1) == P2
    assert match.is_player(P1) and not match.is_player(5)


def test_agreed_template_is_kept(formats):
    match = fold([start(template="JC")], formats)
    assert match.agreed_template == "JC"


def test_undo_removes_the_latest_player_report(formats):
    events = clean_run() + [
        make_event(6, "faction_bid", game=1, by=P1, winner=P1, amount=2100, faction="castle"),
        make_event(7, "undo", game=1, by=P2),
    ]
    match = fold(events, formats)
    assert [e.type for e in match.trade[1]] == ["pair_drawn"]


def test_undo_never_removes_a_random_draw(formats):
    events = clean_run() + [make_event(6, "undo", game=1, by=P1)]
    match = fold(events, formats)
    assert [e.type for e in match.trade[1]] == ["pair_drawn"]


def test_undo_never_removes_a_roll(formats):
    events = clean_run() + [
        make_event(6, "roll", game=1, by=P1, bans=["castle"], pair=["tower", "cove"]),
        make_event(7, "undo", game=1, by=P1),
    ]
    match = fold(events, formats)
    assert [e.type for e in match.trade[1]] == ["pair_drawn", "roll"]


def test_trades_of_different_games_stay_apart(formats):
    events = clean_run() + [make_event(6, "pair_drawn", game=2, pair=["tower", "cove"])]
    match = fold(events, formats)
    assert set(match.trade) == {1, 2}


def test_no_events_means_no_match(formats):
    with pytest.raises(StateError, match="no match"):
        fold([], formats)


def test_missing_start_event_cannot_be_rebuilt(formats):
    events = clean_run()[1:]
    events = [Event(i, e.type, e.data) for i, e in enumerate(events, start=1)]
    with pytest.raises(StateError, match="started the match is missing"):
        fold(events, formats)


def test_deleted_message_in_the_middle_is_detected(formats):
    events = clean_run()
    del events[2]  # event 3 is gone
    with pytest.raises(StateError, match="event 3 was expected but event 4"):
        fold(events, formats)


def test_second_match_start_is_rejected(formats):
    with pytest.raises(StateError, match="two match starts"):
        fold([start(), start(n=2)], formats)


def test_format_that_no_longer_exists_is_reported(formats):
    with pytest.raises(StateError, match="no longer exists"):
        fold([start()], {})


def test_phase_that_no_longer_exists_is_reported(formats):
    event = make_event(1, "match_started", format="el-classico", phase="Gone", p1=P1, p2=P2)
    with pytest.raises(StateError, match="no phase"):
        fold([event], formats)
