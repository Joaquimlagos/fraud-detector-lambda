"""
Regra: transações feitas de madrugada (janela configurável, padrão 2h-7h)
têm risco maior e são sinalizadas como suspeitas.

Nota: esta é uma regra deliberadamente simples, avaliada isoladamente —
não decide sozinha se a transação é bloqueada, apenas contribui um motivo
para o AnalysisEngine considerar junto com as outras regras.
"""
from __future__ import annotations

from src.config import Config
from src.models.transaction_event import TransactionEvent
from src.rules.base import FraudRule


class TimeOfDayRule(FraudRule):
    def __init__(
        self,
        start_hour: int = Config.SUSPICIOUS_HOUR_START,
        end_hour: int = Config.SUSPICIOUS_HOUR_END,
    ) -> None:
        self._start_hour = start_hour
        self._end_hour = end_hour

    def evaluate(
        self,
        transaction: TransactionEvent,
        recent_history: list[TransactionEvent],
    ) -> str | None:
        hour = transaction.occurred_at.hour

        if self._start_hour <= hour < self._end_hour:
            return (
                f"Transaction occurred at {hour:02d}h, "
                f"within the {self._start_hour:02d}h-{self._end_hour:02d}h high-risk window"
            )

        return None
