"""DynamoDB-backed cache for generated investigation explanations."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3

from src.shared.config import Config

_dynamodb = boto3.resource("dynamodb")


class AnalysisCache:
    def __init__(self, table: Any | None = None, table_name: str = Config.ANALYSIS_TABLE) -> None:
        self._table = table or _dynamodb.Table(table_name)

    def get(self, transaction_id: str) -> dict[str, Any] | None:
        response = self._table.get_item(Key={"transactionId": transaction_id})
        return response.get("Item")

    def save(
        self,
        transaction_id: str,
        status: str,
        reasoning: str,
        similar_cases: list[dict[str, str | float]],
    ) -> dict[str, Any]:
        item = {
            "transactionId": transaction_id,
            "status": status,
            "reasoning": reasoning,
            "similarCases": _dynamodb_similar_cases(similar_cases),
            "analyzedAt": datetime.now(timezone.utc).isoformat(),
        }
        self._table.put_item(Item=item)
        return item


def _dynamodb_similar_cases(
    similar_cases: list[dict[str, str | float]],
) -> list[dict[str, str | Decimal]]:
    return [
        {
            "transactionId": str(case["transactionId"]),
            "similarity": Decimal(str(case["similarity"])),
        }
        for case in similar_cases
    ]