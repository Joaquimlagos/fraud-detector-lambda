"""
Orquestra a lista de regras. Adicionar uma nova regra de fraude no futuro
significa criar uma nova classe FraudRule e adicioná-la à lista abaixo —
nenhum outro código precisa mudar (Open/Closed Principle).
"""
from __future__ import annotations

from src.models.analysis_result import AnalysisResult
from src.models.transaction_event import TransactionEvent
from src.rules.base import FraudRule
from src.rules.impossible_travel_rule import ImpossibleTravelRule
from src.rules.time_of_day_rule import TimeOfDayRule
from src.rules.velocity_rule import VelocityRule

DEFAULT_RULES: list[FraudRule] = [
    ImpossibleTravelRule(),
    TimeOfDayRule(),
    VelocityRule(),
]


class AnalysisEngine:
    def __init__(self, rules: list[FraudRule] | None = None) -> None:
        self._rules = rules if rules is not None else DEFAULT_RULES

    def analyze(
        self,
        transaction: TransactionEvent,
        recent_history: list[TransactionEvent],
    ) -> AnalysisResult:
        reasons = [
            reason
            for rule in self._rules
            if (reason := rule.evaluate(transaction, recent_history)) is not None
        ]

        if reasons:
            return AnalysisResult.suspicious(reasons)

        return AnalysisResult.approved()
