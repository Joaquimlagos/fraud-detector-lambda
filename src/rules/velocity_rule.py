"""
Regra: muitas transações do mesmo usuário em pouco tempo (velocity check)
são sinalizadas como suspeitas — o exemplo clássico de fraude que só
aparece quando se olha o padrão agregado, não uma transação isolada.

Depende do histórico recente já filtrado pela janela de tempo correta —
essa filtragem é responsabilidade do repository (via query no DynamoDB),
não desta regra. A regra só conta quantas transações vieram nesse
histórico e compara com o limite.
"""
from __future__ import annotations

from src.config import Config
from src.models.transaction_event import TransactionEvent
from src.rules.base import FraudRule


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
        # +1 porque a transação atual ainda não está no histórico
        # (o histórico é buscado antes de esta transação ser persistida).
        count_in_window = len(recent_history) + 1

        if count_in_window > self._max_transactions:
            return (
                f"{count_in_window} transactions from this user within "
                f"{self._window_minutes} minute(s), exceeding the limit of "
                f"{self._max_transactions}"
            )

        return None
