"""The gold of the two players in one game's trade.

Plain Python: no Discord objects in here, so tests can cover it. Gold is never stored. It is worked
out from the starting gold (see `difficulty.py`) and the payments made so far, in order, so undoing
a payment is just leaving it out and working it out again. Every payment goes to the opponent, so the
two players always hold the same total as they started with. Players are identified by any value
(the bot uses Discord user ids).
"""

from dataclasses import dataclass

GOLD_STEP = 100  # gold in a trade moves in steps of 100: bids are raised by at least 100, a roll costs whole hundreds


class LedgerError(ValueError):
    """A payment is not possible. The message is shown to the player."""


@dataclass(frozen=True)
class Payment:
    payer: int  # who pays; the other player receives
    amount: int  # whole gold, 0 or more


def check_payment(gold: dict[int, int], payment: Payment) -> None:
    """Raise LedgerError unless `payment` can be made with the gold as it stands."""
    if payment.payer not in gold:
        raise LedgerError("Only one of the two players of this game can pay.")
    # bool is a kind of int in Python, so True would otherwise pass as a payment of 1
    if not isinstance(payment.amount, int) or isinstance(payment.amount, bool) or payment.amount < 0:
        raise LedgerError("An amount of gold must be a whole number, 0 or more.")
    if payment.amount % GOLD_STEP != 0:
        raise LedgerError(f"Gold moves in steps of {GOLD_STEP}, so {payment.amount} is not possible.")
    if payment.amount > gold[payment.payer]:
        raise LedgerError(f"{payment.amount} gold is more than the {gold[payment.payer]} the payer has.")


def pay(gold: dict[int, int], payment: Payment) -> dict[int, int]:
    """The gold after one payment (the given dict is left as it is). The opponent receives the amount."""
    check_payment(gold, payment)
    receiver = next(player for player in gold if player != payment.payer)
    after = dict(gold)
    after[payment.payer] -= payment.amount
    after[receiver] += payment.amount
    return after


def gold_after(start: int, players: tuple[int, int], payments: list[Payment]) -> dict[int, int]:
    """The gold of both players after the payments, in order. Refuses a payment that could not have been made."""
    if len(set(players)) != 2:
        raise LedgerError("A game has exactly two different players.")
    gold = {player: start for player in players}
    for payment in payments:
        gold = pay(gold, payment)
    return gold

