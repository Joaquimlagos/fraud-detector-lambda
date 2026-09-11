"""Flags excessive transaction velocity for one user."""
from __future__ import annotations

from src.shared.config import Config
from src.shared.models.transaction_event import TransactionEvent
from src.scoring.rules.base import FraudRule


class VelocityRule(FraudRule):
    def __init__(
        self,
        max_transactions: int = Config.VELOCITY_MAX_TRANSACTIONS,
        window_minutes: int = Config.VELOCITY_WINDOW_MINUTES,
    ) -> None:
        self._max_transactions = max_transactions
        self._window_minutes = window_minutes

    def evaluate(
        self,
        transaction: TransactionEvent,
        recent_history: list[TransactionEvent],
    ) -> str | None:
        count_in_window = len(recent_history) + 1

        if count_in_window > self._max_transactions:
            return (
                f"{count_in_window} transactions from this user within "
                f"{self._window_minutes} minute(s), exceeding the limit of "
                f"{self._max_transactions}"
            )

        return None