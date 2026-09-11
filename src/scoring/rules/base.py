"""Interface for a fraud scoring rule."""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.shared.models.transaction_event import TransactionEvent


class FraudRule(ABC):
    @abstractmethod
    def evaluate(
        self,
        transaction: TransactionEvent,
        recent_history: list[TransactionEvent],
    ) -> str | None:
        raise NotImplementedError