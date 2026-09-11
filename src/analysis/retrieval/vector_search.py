"""Small, local-friendly similarity search over transaction history."""
from __future__ import annotations

from dataclasses import dataclass

from src.shared.models.transaction_event import TransactionEvent
from src.shared.repository.transactions_repository import TransactionsRepository


@dataclass(frozen=True)
class SimilarCase:
    transaction_id: str
    similarity: float

    def to_dict(self) -> dict[str, str | float]:
        return {
            "transactionId": self.transaction_id,
            "similarity": round(self.similarity, 4),
        }


class VectorSearch:
    """Retrieval interface backed by DynamoDB scan for local portability."""

    def __init__(self, repository: TransactionsRepository | None = None) -> None:
        self._repository = repository or TransactionsRepository()

    def find_similar(
        self, transaction: TransactionEvent, limit: int = 5
    ) -> list[SimilarCase]:
        candidates = self._repository.find_all()
        scored = [
            SimilarCase(candidate.transaction_id, _similarity(transaction, candidate))
            for candidate in candidates
            if candidate.transaction_id != transaction.transaction_id
        ]
        return sorted(scored, key=lambda case: case.similarity, reverse=True)[:limit]


def _similarity(left: TransactionEvent, right: TransactionEvent) -> float:
    score = 0.0
    if left.user_id == right.user_id:
        score += 0.35
    if left.currency == right.currency:
        score += 0.15
    if left.merchant_category and left.merchant_category == right.merchant_category:
        score += 0.2
    if left.merchant.casefold() == right.merchant.casefold():
        score += 0.15
    if left.latitude is not None and right.latitude is not None:
        if abs(left.latitude - right.latitude) <= 1:
            score += 0.075
    if left.longitude is not None and right.longitude is not None:
        if abs(left.longitude - right.longitude) <= 1:
            score += 0.075
    largest_amount = max(left.amount, right.amount)
    amount_ratio = min(left.amount, right.amount) / largest_amount if largest_amount else 1
    return min(1.0, score + float(amount_ratio) * 0.1)