"""Interface base para uma regra de fraude."""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.transaction_event import TransactionEvent


class FraudRule(ABC):
    """Cada regra recebe a transação atual e o histórico recente do
    usuário, e decide se aquilo é suspeito. Uma regra nunca lança exceção
    por conta própria de "não suspeito" — retorna None nesse caso."""

    @abstractmethod
    def evaluate(
        self,
        transaction: TransactionEvent,
        recent_history: list[TransactionEvent],
    ) -> str | None:
        """Retorna uma string explicando o motivo se a regra disparar,
        ou None se a transação passar por essa regra sem problema."""
        raise NotImplementedError
