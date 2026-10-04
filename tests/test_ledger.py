import pytest

from rules.ledger import Ledger, LedgerError

P1, P2 = 1, 2


def test_worked_example_from_the_spec():
    ledger = Ledger((P1, P2), 10000)
    ledger.pay(P1, 500)  # P1 rolls
    ledger.pay(P1, 2100)  # P1 wins the faction bid
    ledger.pay(P2, 3000)  # P2 wins the color bid
    assert ledger.gold == {P1: 10400, P2: 9600}


def test_total_gold_never_changes():
    ledger = Ledger((P1, P2), 15000)
    for payer, amount in [(P1, 700), (P2, 1200), (P1, 0), (P2, 14500)]:
        ledger.pay(payer, amount)
    assert sum(ledger.gold.values()) == 30000


def test_cannot_pay_more_than_the_gold_a_player_has():
    ledger = Ledger((P1, P2), 10000)
    with pytest.raises(LedgerError, match="only 10000 gold"):
        ledger.pay(P1, 10001)
    assert ledger.gold == {P1: 10000, P2: 10000}


def test_can_pay_everything():
    ledger = Ledger((P1, P2), 10000)
    ledger.pay(P1, 10000)
    assert ledger.gold == {P1: 0, P2: 20000}


@pytest.mark.parametrize("amount", [-1, 1.5, "100", True])
def test_amount_must_be_a_whole_number_of_gold(amount):
    with pytest.raises(LedgerError, match="whole number"):
        Ledger((P1, P2), 10000).pay(P1, amount)


def test_nobody_has_gold_at_200_percent():
    ledger = Ledger((P1, P2), 0)
    assert not ledger.can_pay(P1, 1)
    ledger.pay(P1, 0)
    assert ledger.gold == {P1: 0, P2: 0}
