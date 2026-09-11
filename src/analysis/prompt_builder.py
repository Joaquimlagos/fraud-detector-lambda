"""Builds the bounded context sent to the investigation model."""
from __future__ import annotations

import json

from src.analysis.retrieval.vector_search import SimilarCase
from src.shared.models.analysis_result import AnalysisResult
from src.shared.models.transaction_event import TransactionEvent


def build_prompt(
    transaction: TransactionEvent,
    scoring_result: AnalysisResult | None,
    similar_cases: list[SimilarCase],
) -> str:
    context = {
        "transaction": _transaction_context(transaction),
        "ruleEngine": {
            "status": scoring_result.status.value if scoring_result else "UNKNOWN",
            "triggeredRules": scoring_result.reasons if scoring_result else [],
        },
        "similarCases": [case.to_dict() for case in similar_cases],
    }
    return (
        "Investigate this transaction using only the JSON context below. "
        "Explain objectively why its status is approved, suspicious, or unknown. "
        "Do not invent facts or claim checks that are not present in the context. "
        "Keep the answer concise and in natural language.\n\n"
        f"Context:\n{json.dumps(context, default=str, sort_keys=True)}"
    )


def _transaction_context(transaction: TransactionEvent) -> dict[str, object]:
    return {
        "transactionId": transaction.transaction_id,
        "userId": transaction.user_id,
        "amount": str(transaction.amount),
        "currency": transaction.currency,
        "merchant": transaction.merchant,
        "merchantCategory": transaction.merchant_category,
        "occurredAt": transaction.occurred_at.isoformat(),
        "latitude": transaction.latitude,
        "longitude": transaction.longitude,
        "paymentMethod": transaction.payment_method,
        "channel": transaction.channel,
        "billingCountry": transaction.billing_country,
    }