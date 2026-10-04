import random

import pytest

from rules import trade as T
from rules.formats import parse_format
from rules.trade import TradeError
from state import fold, make_event

A, B = 10, 20  # A (the coinflip winner) is "P1" in the spec scenarios


class Script:
    """A scripted random source: pairs for sample(), values for randrange()."""

    def __init__(self, pairs=(), tosses=()):
        self.pairs = list(pairs)
        self.tosses = list(tosses)

    def sample(self, pool, k):
        pair = self.pairs.pop(0)
        assert all(f in pool for f in pair), f"{pair} not drawable from {pool}"
        return list(pair)

    def randrange(self, n):
        return self.tosses.pop(0)


class Table:
    """A match in the trade stage, with helpers to play it."""

    def __init__(self, formats, factions, selection_events):
        self.formats = formats
        self.factions = factions
        self.events = [
            make_event(1, "match_started", format="el-classico", phase="Main", p1=A, p2=B),
            make_event(2, "coinflip", a=A, b=B),
            *[make_event(i, t, **d) for i, (t, d) in enumerate(selection_events, start=3)],
        ]

    @property
    def match(self):
        return fold(self.events, self.formats)

    def do(self, action):
        self.events.append(make_event(len(self.events) + 1, action.type, **action.data))
        return action

    def start(self, number=1, pairs=(), tosses=()):
        return self.do(T.start_trade(self.match, number, self.factions, Script(pairs, tosses)))

    def roll(self, user, bans=(), new_pair=("necropolis", "tower"), number=1):
        return self.do(T.roll(self.match, number, user, list(bans), self.factions, Script([new_pair])))

    def decline(self, user, number=1):
        return self.do(T.decline(self.match, number, user, self.factions))

    def report(self, user, choice, winner=None, amount=None, number=1):
        return self.do(T.report(self.match, number, user, choice, winner, amount, self.factions))

    def undo(self, user, number=1):
        return self.do(T.undo(self.match, number, user, self.factions))

    def state(self, number=1):
        return T.trade_state(self.match, number)


def make_formats(el_classico, templates, factions, trade=None, allowed=None, bo3=False):
    phase = el_classico["phases"][0]
    if trade:
        phase["trade"].update(trade)
    if allowed:
        phase["allowed_factions"] = allowed
    if bo3:
        phase["best_of"] = 3
        phase["selection"] = {
            "type": "sequence",
            "steps": [{"who": "A", "do": "pick"}, {"who": "B", "do": "pick"}],
            "game_order": ["pick_1", "pick_2", "decider"],
        }
    return {"el-classico": parse_format(el_classico, templates, factions)}


BO1_BANS = [("ban", {"by": A, "template": "JC"}), ("ban", {"by": B, "template": "h3dm1"})]  # 6lm10a is played
BO3_PICKS = [("pick", {"by": A, "template": "JC"}), ("pick", {"by": B, "template": "h3dm1"})]  # 6lm10a decider


@pytest.fixture
def table(el_classico, templates, factions):
    return Table(make_formats(el_classico, templates, factions), factions, BO1_BANS)


@pytest.fixture
def make_table(el_classico, templates, factions):
    def make(trade=None, allowed=None, bo3=False):
        formats = make_formats(el_classico, templates, factions, trade, allowed, bo3)
        return Table(formats, factions, BO3_PICKS if bo3 else BO1_BANS)

    return make


CASTLE_FACTORY = [("castle", "factory")]


# --- every game has its own trade ------------------------------------------


def test_trade_must_be_started(table):
    with pytest.raises(TradeError, match="has not started"):
        T.roll(table.match, 1, A, [], table.factions)


def test_trade_cannot_start_twice(table):
    table.start(pairs=CASTLE_FACTORY)
    with pytest.raises(TradeError, match="already started"):
        table.start()


def test_commands_target_the_first_unfinished_game(make_table):
    t = make_table(bo3=True)
    assert T.choose_game(t.match, None) == 1
    assert T.choose_game(t.match, 3) == 3


def test_unknown_game_is_refused(table):
    with pytest.raises(TradeError, match="no game 5"):
        T.choose_game(table.match, 5)


def test_finished_game_is_skipped_by_the_default(make_table):
    t = make_table(bo3=True, trade={"rolls_per_player": 0})
    t.start(pairs=CASTLE_FACTORY)
    t.report(A, "castle", A, 2000)
    t.report(A, "red", A, 0)
    assert t.state(1).complete
    assert T.choose_game(t.match, None) == 2
    assert T.following_game(t.match, 1) == 2
    assert T.following_game(t.match, 3) is None


def test_game_two_can_be_traded_while_game_one_waits(make_table):
    t = make_table(bo3=True)
    t.start(1, pairs=CASTLE_FACTORY)
    t.start(2, pairs=[("tower", "cove")])
    assert t.state(1).pair == ("castle", "factory")
    assert t.state(2).pair == ("tower", "cove")
    assert not t.state(1).complete


def test_trades_of_two_games_do_not_mix_gold(make_table):
    t = make_table(bo3=True)
    t.start(1, pairs=CASTLE_FACTORY)
    t.start(2, pairs=[("tower", "cove")])
    t.roll(A, new_pair=("rampart", "inferno"), number=2)
    assert t.state(1).gold == {A: 10000, B: 10000}
    assert t.state(2).gold == {A: 9500, B: 10500}


def test_trade_needs_finished_selection(el_classico, templates, factions):
    formats = make_formats(el_classico, templates, factions)
    t = Table(formats, factions, BO1_BANS[:1])
    with pytest.raises(Exception, match="not finished"):
        T.start_trade(t.match, 1, factions)


# --- prompting and sections ------------------------------------------------


def test_start_announces_template_gold_pair_cost_and_who_may_roll(table):
    action = table.start(pairs=CASTLE_FACTORY)
    assert action.type == "pair_drawn" and action.data == {"game": 1, "pair": ["castle", "factory"]}
    assert "Game 1: 6lm10a" in action.text and "160%" in action.text and "10000 gold each" in action.text
    assert "Castle vs Factory" in action.text
    assert "A roll costs 500 gold" in action.text
    assert "Both players may roll" in action.text
    assert action.ping == (A, B)


def test_color_report_before_the_faction_bid_is_refused(table):
    table.start(pairs=CASTLE_FACTORY)
    with pytest.raises(TradeError, match="faction bid comes first.*Castle vs Factory"):
        table.report(A, "red", A, 1000)


def test_faction_report_after_the_faction_is_settled_is_refused(table):
    table.start(pairs=CASTLE_FACTORY)
    table.report(A, "castle", A, 1000)
    with pytest.raises(TradeError, match="Now report the color"):
        table.report(A, "tower", A, 1000)


def test_nobody_may_roll_when_rolls_per_player_is_zero(make_table):
    t = make_table(trade={"rolls_per_player": 0})
    action = t.start(pairs=CASTLE_FACTORY)
    assert t.state().section == "faction_bid"
    assert "Bid for the faction" in action.text
    assert action.ping == (A,)  # A bids first


def test_nobody_may_roll_when_nobody_can_afford_it(make_table):
    t = make_table(trade={"roll_cost": 10001})
    t.start(pairs=CASTLE_FACTORY)
    assert t.state().section == "faction_bid"


# --- the generated pair ----------------------------------------------------


def test_drawn_pair_has_two_different_allowed_factions():
    allowed = ("castle", "rampart", "tower")
    for seed in range(50):
        first, second = T.draw_pair(allowed, (), random.Random(seed))
        assert first != second and {first, second} <= set(allowed)


def test_every_allowed_faction_appears_equally_often():
    allowed = ("castle", "rampart", "tower", "inferno")
    counts = dict.fromkeys(allowed, 0)
    rng = random.Random(7)
    for _ in range(8000):
        for faction in T.draw_pair(allowed, (), rng):
            counts[faction] += 1
    # each faction is in half of all pairs: expect about 4000
    assert all(3800 < n < 4200 for n in counts.values()), counts


def test_production_random_source_works():
    pair = T.draw_pair(("castle", "rampart", "tower"), ("tower",))
    assert set(pair) == {"castle", "rampart"}


def test_banned_factions_are_never_drawn():
    for seed in range(50):
        pair = T.draw_pair(("castle", "rampart", "tower", "inferno"), ("castle", "rampart"), random.Random(seed))
        assert set(pair) == {"tower", "inferno"}


def test_fewer_than_two_factions_left_is_refused():
    with pytest.raises(TradeError, match="Fewer than two"):
        T.draw_pair(("castle", "rampart", "tower"), ("castle", "rampart"))


def test_start_draws_only_allowed_factions(make_table):
    t = make_table(allowed=["castle", "rampart", "tower"])
    for seed in range(20):
        pair = T.draw_pair(t.match.phase.allowed_factions, (), random.Random(seed))
        assert set(pair) <= {"castle", "rampart", "tower"}


# --- rolling ---------------------------------------------------------------


def test_one_roll_costs_gold_bans_and_draws_a_new_pair(table):
    table.start(pairs=CASTLE_FACTORY)
    action = table.roll(A, bans=["Castle"], new_pair=("necropolis", "tower"))
    st = table.state()
    assert st.pair == ("necropolis", "tower") and st.banned == ("castle",)
    assert st.gold == {A: 9500, B: 10500}
    assert "banning Castle" in action.text and "paid 500 gold" in action.text
    assert "Necropolis vs Tower" in action.text
    assert action.ping == (B,)  # only B may still roll
    assert "may roll" in action.text and "Both" not in action.text


def test_roll_without_bans(table):
    table.start(pairs=CASTLE_FACTORY)
    table.roll(A, bans=[], new_pair=("rampart", "dungeon"))
    assert table.state().banned == () and table.state().gold[A] == 9500


def test_bans_stay_in_force_for_the_next_roll(table):
    table.start(pairs=CASTLE_FACTORY)
    table.roll(A, bans=["castle"], new_pair=("necropolis", "tower"))
    with pytest.raises(AssertionError):  # the scripted draw offers castle, which is banned
        T.roll(table.match, 1, B, [], table.factions, Script([("castle", "tower")]))


def test_too_many_bans_are_refused_and_nobody_pays(table):
    table.start(pairs=CASTLE_FACTORY)
    with pytest.raises(TradeError, match="at most 2"):
        T.roll(table.match, 1, A, ["castle", "factory", "tower"], table.factions)
    assert table.state().gold == {A: 10000, B: 10000}


def test_ban_must_be_in_the_current_pair(table):
    table.start(pairs=CASTLE_FACTORY)
    with pytest.raises(TradeError, match="Tower is not in the current pair"):
        T.roll(table.match, 1, A, ["tower"], table.factions)


def test_unknown_faction_ban_lists_the_allowed_factions(table):
    table.start(pairs=CASTLE_FACTORY)
    with pytest.raises(TradeError, match="not an allowed faction here. Allowed: Castle, Rampart"):
        T.roll(table.match, 1, A, ["atlantis"], table.factions)


def test_faction_not_allowed_in_the_phase_is_refused(make_table):
    t = make_table(allowed=["castle", "rampart", "tower"])
    t.start(pairs=[("castle", "tower")])
    with pytest.raises(TradeError, match="not an allowed faction here. Allowed: Castle, Rampart, Tower"):
        T.roll(t.match, 1, A, ["cove"], t.factions)


def test_player_with_no_roll_left_is_refused(table):
    table.start(pairs=CASTLE_FACTORY)
    table.roll(A, new_pair=("rampart", "dungeon"))
    with pytest.raises(TradeError, match="no roll left"):
        T.roll(table.match, 1, A, [], table.factions, Script([("castle", "tower")]))


def test_player_who_cannot_pay_is_refused(make_table):
    t = make_table(trade={"roll_cost": 6000, "rolls_per_player": 2})
    t.start(pairs=CASTLE_FACTORY)
    t.roll(A, new_pair=("rampart", "dungeon"))  # A has 4000 left
    assert t.state().eligible_rollers() == [B]
    with pytest.raises(TradeError, match="costs 6000 gold and you have 4000"):
        T.roll(t.match, 1, A, [], t.factions, Script([("castle", "tower")]))


def test_roll_that_would_leave_too_few_factions_is_refused(make_table):
    t = make_table(allowed=["castle", "rampart", "tower"], trade={"max_roll_bans": 2})
    t.start(pairs=[("castle", "rampart")])
    with pytest.raises(TradeError, match="Fewer than two"):
        T.roll(t.match, 1, A, ["castle", "rampart"], t.factions)
    assert t.state().gold == {A: 10000, B: 10000}


def test_roll_after_the_section_is_over_is_refused(table):
    table.start(pairs=CASTLE_FACTORY)
    table.report(A, "castle", A, 1000)
    with pytest.raises(TradeError, match="roll is over"):
        T.roll(table.match, 1, B, [], table.factions)


# --- rolling or declining --------------------------------------------------


def test_both_decline_ends_the_section_and_nobody_pays(table):
    table.start(pairs=CASTLE_FACTORY)
    table.decline(A)
    assert table.state().section == "faction_roll"  # B has not answered yet
    action = table.decline(B)
    st = table.state()
    assert st.section == "faction_bid" and st.pair == ("castle", "factory")
    assert st.gold == {A: 10000, B: 10000}
    assert "Bid for the faction" in action.text


def test_waiting_on_the_other_player_names_them(table):
    table.start(pairs=CASTLE_FACTORY)
    action = table.roll(A, new_pair=("rampart", "dungeon"))
    assert table.state().section == "faction_roll"
    assert action.ping == (B,) and f"<@{B}> may roll" in action.text


def test_one_rolls_one_declines_and_the_bid_uses_the_new_pair(table):
    table.start(pairs=CASTLE_FACTORY)
    table.roll(A, new_pair=("rampart", "dungeon"))
    table.decline(B)
    st = table.state()
    assert st.section == "faction_bid" and st.pair == ("rampart", "dungeon")


def test_reporting_the_faction_bid_skips_open_rolls(table):
    table.start(pairs=CASTLE_FACTORY)
    action = table.report(A, "castle", A, 1000)
    assert "open rolls were skipped" in action.text
    assert table.state().rolls_closed and table.state().section == "color_bid"


def test_declining_when_not_eligible_is_refused(table):
    table.start(pairs=CASTLE_FACTORY)
    table.decline(A)
    with pytest.raises(TradeError, match="nothing to decline"):
        T.decline(table.match, 1, A, table.factions)


# --- faction bid -----------------------------------------------------------


def test_winning_faction_bid(table):
    table.start(pairs=[("necropolis", "tower")])
    action = table.report(A, "Necropolis", A, 2100)
    st = table.state()
    assert st.factions == {A: "necropolis", B: "tower"}
    assert st.gold == {A: 7900, B: 12100}
    assert "won the faction bid at 2100" in action.text and "Tower" in action.text


def test_faction_must_be_in_the_pair(table):
    table.start(pairs=[("necropolis", "tower")])
    with pytest.raises(TradeError, match="Castle is not in the pair: Necropolis vs Tower"):
        table.report(A, "castle", A, 2100)


def test_bid_above_the_gold_of_the_winner_is_refused(table):
    table.start(pairs=[("necropolis", "tower")])
    with pytest.raises(TradeError, match="only 10000 gold, not 10001"):
        table.report(A, "tower", A, 10001)


def test_winner_must_be_a_player(table):
    table.start(pairs=[("necropolis", "tower")])
    with pytest.raises(TradeError, match="winner"):
        table.report(A, "tower", 99, 100)
    with pytest.raises(TradeError, match="winner"):
        table.report(A, "tower", None, 100)


def test_amount_is_required_and_not_negative(table):
    table.start(pairs=[("necropolis", "tower")])
    with pytest.raises(TradeError, match="amount"):
        table.report(A, "tower", A, None)
    with pytest.raises(TradeError, match="0 or more"):
        table.report(A, "tower", A, -5)


# --- color bid, gold and summary -------------------------------------------


def test_winning_color_bid(table):
    table.start(pairs=[("necropolis", "tower")])
    table.report(A, "necropolis", A, 2100)
    action = table.report(B, "red", B, 3000)
    st = table.state()
    assert st.colors == {B: "red", A: "blue"}
    assert st.complete
    assert "Red moves first" in action.text


def test_invalid_color_is_refused(table):
    table.start(pairs=[("necropolis", "tower")])
    table.report(A, "necropolis", A, 2100)
    with pytest.raises(TradeError, match="Now report the color"):
        table.report(A, "green", A, 100)


def test_worked_example_and_final_summary(table):
    table.start(pairs=CASTLE_FACTORY)
    table.roll(A, bans=["castle"], new_pair=("necropolis", "tower"))
    table.decline(B)
    table.report(A, "necropolis", A, 2100)
    final = table.report(B, "red", B, 3000)
    st = table.state()
    assert st.gold == {A: 10400, B: 9600}
    assert st.complete and final.ping == ()
    assert "Lobby settings, game 1" in final.text
    assert "Template: **6lm10a**" in final.text
    assert f"<@{A}>: Necropolis, blue, 10400 gold" in final.text
    assert f"<@{B}>: Tower, red, 9600 gold" in final.text
    assert f"Red moves first: <@{B}>" in final.text


def test_gold_is_shown_after_each_section(table):
    table.start(pairs=CASTLE_FACTORY)
    action = table.report(A, "castle", A, 700)
    assert f"Gold: <@{A}> 9300, <@{B}> 10700" in action.text


def test_finished_trade_accepts_no_more_reports(table):
    table.start(pairs=CASTLE_FACTORY)
    table.report(A, "castle", A, 0)
    table.report(A, "red", A, 0)
    with pytest.raises(TradeError, match="is finished"):
        table.report(A, "red", A, 0)


def test_status_shows_the_current_section(table):
    assert "has not started" in T.status_text(table.match, 1, table.factions)
    table.start(pairs=CASTLE_FACTORY)
    text = T.status_text(table.match, 1, table.factions)
    assert "Castle vs Factory" in text and "Gold:" in text


# --- who reports, and undo -------------------------------------------------


def test_the_loser_of_a_bid_may_report_it(table):
    table.start(pairs=CASTLE_FACTORY)
    action = table.report(B, "castle", A, 1000)  # B reports, A won
    assert table.state().factions[A] == "castle"
    assert action.type == "faction_bid" and action.data["by"] == B


def test_undo_returns_to_the_state_before_the_report(table):
    table.start(pairs=CASTLE_FACTORY)
    table.report(A, "castle", A, 1000)
    action = table.undo(B)
    st = table.state()
    assert st.gold == {A: 10000, B: 10000} and st.factions == {}
    assert st.section == "faction_roll"  # skipped rolls are open again
    assert "undid the last report" in action.text and "Castle vs Factory" in action.text


def test_undo_of_a_color_report_reopens_the_color_section(table):
    table.start(pairs=CASTLE_FACTORY)
    table.report(A, "castle", A, 1000)
    table.report(A, "red", A, 500)
    assert table.state().complete
    table.undo(A)
    assert table.state().section == "color_bid"


def test_undo_with_nothing_reported(table):
    table.start(pairs=CASTLE_FACTORY)
    with pytest.raises(TradeError, match="nothing to undo"):
        T.undo(table.match, 1, A, table.factions)


def test_undo_before_the_trade_started(table):
    with pytest.raises(TradeError, match="nothing to undo"):
        T.undo(table.match, 1, A, table.factions)


def test_a_roll_cannot_be_undone(table):
    table.start(pairs=CASTLE_FACTORY)
    table.roll(A, new_pair=("rampart", "dungeon"))
    with pytest.raises(TradeError, match="Random results are final"):
        T.undo(table.match, 1, A, table.factions)


def test_report_after_a_roll_can_be_undone_but_the_roll_stays(table):
    table.start(pairs=CASTLE_FACTORY)
    table.roll(A, bans=["castle"], new_pair=("rampart", "dungeon"))
    table.decline(B)
    table.report(A, "rampart", A, 1000)
    table.undo(A)
    st = table.state()
    assert st.pair == ("rampart", "dungeon") and st.gold == {A: 9500, B: 10500}


def test_a_decline_can_be_undone(table):
    table.start(pairs=CASTLE_FACTORY)
    table.decline(A)
    table.undo(A)
    assert table.state().eligible_rollers() == [A, B]


# --- 200%: only the color toss ---------------------------------------------


@pytest.fixture
def toss_table(make_table):
    return make_table(trade={"difficulty": 200})


def test_200_percent_starts_with_a_toss_and_no_faction_steps(toss_table):
    action = toss_table.start(tosses=[0])
    assert action.type == "color_toss" and action.data["winner"] == A
    assert "Game 1: 6lm10a" in action.text and "200%" in action.text
    assert f"<@{A}> won the toss" in action.text
    assert "roll" not in action.text.lower() and "bid" not in action.text.lower()
    assert action.ping == (A,)
    assert toss_table.state().section == "color_toss"


def test_toss_winner_can_be_either_player(toss_table, make_table):
    toss_table.start(tosses=[1])
    assert toss_table.state().toss_winner == B


def test_toss_winner_chooses_the_color_and_no_gold_moves(toss_table):
    toss_table.start(tosses=[0])
    toss_table.report(A, "red")
    st = toss_table.state()
    assert st.colors == {A: "red", B: "blue"} and st.complete
    assert st.gold == {A: 0, B: 0}


def test_only_the_toss_winner_chooses(toss_table):
    toss_table.start(tosses=[0])
    with pytest.raises(TradeError, match="Only <@10>, who won the toss"):
        toss_table.report(B, "red")


def test_toss_choice_must_be_a_color(toss_table):
    toss_table.start(tosses=[0])
    with pytest.raises(TradeError, match="red or blue"):
        toss_table.report(A, "castle")


def test_200_percent_summary_leaves_out_the_factions(toss_table):
    toss_table.start(tosses=[1])
    final = toss_table.report(B, "blue")
    assert "assigned by the game" in final.text
    assert f"<@{B}>: blue" in final.text and "gold" not in final.text.split("Template")[1]
    assert f"Red moves first: <@{A}>" in final.text


def test_roll_is_not_available_at_200_percent(toss_table):
    toss_table.start(tosses=[0])
    with pytest.raises(TradeError, match="roll is over"):
        T.roll(toss_table.match, 1, A, [], toss_table.factions)


def test_toss_is_fair():
    rng = random.Random(3)
    wins = sum(rng.randrange(2) == 0 for _ in range(10000))
    assert 4700 < wins < 5300


def test_toss_cannot_be_undone(toss_table):
    toss_table.start(tosses=[0])
    with pytest.raises(TradeError, match="nothing to undo"):
        T.undo(toss_table.match, 1, A, toss_table.factions)


def test_color_choice_after_a_toss_can_be_undone(toss_table):
    toss_table.start(tosses=[0])
    toss_table.report(A, "red")
    toss_table.undo(A)
    assert toss_table.state().section == "color_toss" and toss_table.state().toss_winner == A
