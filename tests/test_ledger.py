import pytest

from rules.ledger import LedgerError, Payment, check_payment, gold_after, pay

P1, P2 = 111, 222


def test_without_payments_both_players_have_the_starting_gold():
    assert gold_after(10000, (P1, P2), []) == {P1: 10000, P2: 10000}


def test_a_payment_goes_to_the_opponent():
    assert gold_after(10000, (P1, P2), [Payment(P1, 500)]) == {P1: 9500, P2: 10500}
    assert gold_after(10000, (P1, P2), [Payment(P2, 500)]) == {P1: 10500, P2: 9500}


def test_the_worked_example_ends_with_10400_and_9600():
    # 160% difficulty: a 500 roll and the 2100 town bid paid by P1, the 3000 color bid paid by P2
    payments = [Payment(P1, 500), Payment(P1, 2100), Payment(P2, 3000)]
    assert gold_after(10000, (P1, P2), payments) == {P1: 10400, P2: 9600}


def test_the_total_never_changes():
    payments = [Payment(P1, 700), Payment(P2, 1900), Payment(P1, 0), Payment(P2, 300)]
    assert sum(gold_after(10000, (P1, P2), payments).values()) == 20000


def test_a_player_can_pay_everything_they_have():
    assert gold_after(1000, (P1, P2), [Payment(P1, 1000)]) == {P1: 0, P2: 2000}


def test_more_than_the_payer_has_is_refused():
    with pytest.raises(LedgerError, match="2100 gold is more than the 2000 the payer has"):
        gold_after(2000, (P1, P2), [Payment(P1, 2100)])


def test_gold_received_earlier_can_be_spent_later():
    assert gold_after(1000, (P1, P2), [Payment(P2, 1000), Payment(P1, 2000)]) == {P1: 0, P2: 2000}


def test_a_payment_of_zero_is_allowed_and_changes_nothing():
    assert gold_after(500, (P1, P2), [Payment(P1, 0)]) == {P1: 500, P2: 500}


@pytest.mark.parametrize("amount", [-1, 1.5, "100", None, True])
def test_an_amount_that_is_not_a_whole_number_of_gold_is_refused(amount):
    with pytest.raises(LedgerError, match="whole number"):
        check_payment({P1: 1000, P2: 1000}, Payment(P1, amount))


def test_somebody_who_is_not_in_the_game_cannot_pay():
    with pytest.raises(LedgerError, match="one of the two players"):
        pay({P1: 1000, P2: 1000}, Payment(333, 10))


def test_paying_does_not_change_the_gold_it_was_given():
    before = {P1: 1000, P2: 1000}
    pay(before, Payment(P1, 100))
    assert before == {P1: 1000, P2: 1000}


def test_leaving_the_last_payment_out_is_an_undo():
    payments = [Payment(P1, 500), Payment(P1, 2100)]
    assert gold_after(10000, (P1, P2), payments[:-1]) == {P1: 9500, P2: 10500}


def test_a_game_needs_two_different_players():
    with pytest.raises(LedgerError, match="two different players"):
        gold_after(1000, (P1, P1), [])


# --- gold moves in steps of 100 ---------------------------------------------------------------------------


@pytest.mark.parametrize("amount", [0, 100, 2100, 10000])
def test_whole_hundreds_can_be_paid(amount):
    check_payment({P1: 10000, P2: 10000}, Payment(P1, amount))  # no error


@pytest.mark.parametrize("amount", [1, 50, 250, 2150, 9999])
def test_other_amounts_are_refused_with_the_step_named(amount):
    with pytest.raises(LedgerError, match=f"steps of 100, so {amount} is not possible"):
        check_payment({P1: 10000, P2: 10000}, Payment(P1, amount))


def test_a_payment_in_steps_of_100_changes_both_players():
    assert gold_after(10000, (P1, P2), [Payment(P1, 2100)]) == {P1: 7900, P2: 12100}
