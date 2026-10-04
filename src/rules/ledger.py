"""The gold of the two players during a trade.

Every payment goes to the opponent, so the total never changes. Amounts are whole
numbers. Undo is not handled here: the trade rebuilds the ledger from its events,
so undoing means leaving the last event out.
"""

from rules.errors import UserError


class LedgerError(UserError):
    pass


class Ledger:
    def __init__(self, players: tuple[int, int], starting_gold: int):
        self.players = players
        self.gold = {p: starting_gold for p in players}

    def other(self, player: int) -> int:
        return self.players[1] if player == self.players[0] else self.players[0]

    def can_pay(self, payer: int, amount: int) -> bool:
        return 0 <= amount <= self.gold[payer]

    def pay(self, payer: int, amount: int) -> None:
        """`payer` pays `amount` gold to the opponent."""
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise LedgerError("The amount must be a whole number of gold, 0 or more.")
        if amount > self.gold[payer]:
            raise LedgerError(f"<@{payer}> has only {self.gold[payer]} gold, not {amount}.")
        self.gold[payer] -= amount
        self.gold[self.other(payer)] += amount
