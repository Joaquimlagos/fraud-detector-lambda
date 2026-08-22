"""
Acesso à tabela de transações no DynamoDB. É o único módulo que fala
diretamente com boto3 para essa tabela — todo o resto do código manipula
apenas TransactionEvent/AnalysisResult.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3

from src.config import Config
from src.models.analysis_result import AnalysisResult
from src.models.transaction_event import TransactionEvent

_dynamodb = boto3.resource("dynamodb")


class TransactionsRepository:
    def __init__(self, table_name: str = Config.TRANSACTIONS_TABLE) -> None:
        self._table = _dynamodb.Table(table_name)

    def find_recent_by_user(
        self, user_id: str, window_minutes: int
    ) -> list[TransactionEvent]:
        """Busca transações do usuário nos últimos `window_minutes`,
        usando o GSI userId-occurredAt-index (ver dynamodb.tf no repo
        fraud-detector-infra-aws)."""
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        response = self._table.query(
            IndexName="userId-occurredAt-index",
            KeyConditionExpression=(
                "userId = :uid AND occurredAt >= :since"
            ),
            ExpressionAttributeValues={
                ":uid": user_id,
                ":since": since.isoformat(),
            },
        )

        return [_item_to_transaction_event(item) for item in response.get("Items", [])]

    def save(self, transaction: TransactionEvent, result: AnalysisResult) -> None:
        self._table.put_item(
            Item={
                "transactionId": transaction.transaction_id,
                "userId": transaction.user_id,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "merchant": transaction.merchant,
                "occurredAt": transaction.occurred_at.isoformat(),
                "status": result.status.value,
                "reasons": result.reasons,
                "analyzedAt": datetime.now(timezone.utc).isoformat(),
            },
            # Idempotência: se esta transactionId já foi persistida (ex.
            # reentrega da mesma mensagem SQS), não sobrescreve nem lança
            # erro — apenas ignora silenciosamente a segunda tentativa.
            ConditionExpression="attribute_not_exists(transactionId)",
        )


def _item_to_transaction_event(item: dict) -> TransactionEvent:
    return TransactionEvent(
        transaction_id=item["transactionId"],
        user_id=item["userId"],
        amount=Decimal(str(item["amount"])),
        currency=item["currency"],
        merchant=item["merchant"],
        occurred_at=datetime.fromisoformat(item["occurredAt"]),
        published_at=datetime.fromisoformat(item["occurredAt"]),  # não persistido, valor placeholder
    )
