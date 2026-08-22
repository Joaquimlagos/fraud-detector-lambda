"""Resultado da análise de fraude para uma transação."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TransactionStatus(str, Enum):
    APPROVED = "APPROVED"
    SUSPICIOUS = "SUSPICIOUS"


@dataclass(frozen=True)
class AnalysisResult:
    status: TransactionStatus
    reasons: list[str] = field(default_factory=list)

    @property
    def is_suspicious(self) -> bool:
        return self.status is TransactionStatus.SUSPICIOUS

    @staticmethod
    def approved() -> "AnalysisResult":
        return AnalysisResult(status=TransactionStatus.APPROVED, reasons=[])

    @staticmethod
    def suspicious(reasons: list[str]) -> "AnalysisResult":
        return AnalysisResult(status=TransactionStatus.SUSPICIOUS, reasons=reasons)
