"""Orchestrates the registered fraud scoring rules."""
from __future__ import annotations

from src.shared.models.analysis_result import AnalysisResult
from src.shared.models.transaction_event import TransactionEvent
from src.scoring.rules.base import FraudRule
from src.scoring.rules.impossible_travel_rule import ImpossibleTravelRule
from src.scoring.rules.time_of_day_rule import TimeOfDayRule
from src.scoring.rules.velocity_rule import VelocityRule

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