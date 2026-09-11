"""DynamoDB access for transaction history and scoring results."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3

from src.shared.config import Config
from src.shared.models.analysis_result import AnalysisResult, TransactionStatus
from src.shared.models.transaction_event import TransactionEvent

_dynamodb = boto3.resource("dynamodb")


class TransactionsRepository:
    def __init__(self, table_name: str = Config.TRANSACTIONS_TABLE) -> None:
        self._table = _dynamodb.Table(table_name)

    def find_recent_by_user(self, user_id: str, window_minutes: int) -> list[TransactionEvent]:
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        response = self._table.query(
            IndexName="userId-occurredAt-index",
            KeyConditionExpression="userId = :uid AND occurredAt >= :since",
            ExpressionAttributeValues={":uid": user_id, ":since": since.isoformat()},
        )
        return [_item_to_transaction_event(item) for item in response.get("Items", [])]

    def find_last_by_user(self, user_id: str) -> TransactionEvent | None:
        response = self._table.query(
            IndexName="userId-occurredAt-index",
            KeyConditionExpression="userId = :uid",
            ExpressionAttributeValues={":uid": user_id},
            ScanIndexForward=False,
            Limit=1,
        )
        items = response.get("Items", [])
        return _item_to_transaction_event(items[0]) if items else None

    def find_by_id(self, transaction_id: str) -> TransactionEvent | None:
        item = self._table.get_item(Key={"transactionId": transaction_id}).get("Item")
        return _item_to_transaction_event(item) if item else None

    def find_result(self, transaction_id: str) -> AnalysisResult | None:
        item = self._table.get_item(Key={"transactionId": transaction_id}).get("Item")
        if not item or "status" not in item:
            return None
        return AnalysisResult(TransactionStatus(item["status"]), list(item.get("reasons", [])))

    def find_all(self) -> list[TransactionEvent]:
        items: list[dict] = []
        scan_kwargs: dict = {}
        while True:
            response = self._table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))
            if not response.get("LastEvaluatedKey"):
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        return [_item_to_transaction_event(item) for item in items]

    def save(self, transaction: TransactionEvent, result: AnalysisResult) -> None:
        self._table.put_item(
            Item={
                "transactionId": transaction.transaction_id,
                "userId": transaction.user_id,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "merchant": transaction.merchant,
                "merchantCategory": transaction.merchant_category,
                "paymentMethod": transaction.payment_method,
                "cardLastFourDigits": transaction.card_last_four_digits,
                "channel": transaction.channel,
                "ipAddress": transaction.ip_address,
                "deviceId": transaction.device_id,
                "billingCountry": transaction.billing_country,
                "occurredAt": transaction.occurred_at.isoformat(),
                "createdAt": transaction.published_at.isoformat(),
                "latitude": _coordinate_to_decimal(transaction.latitude),
                "longitude": _coordinate_to_decimal(transaction.longitude),
                "status": result.status.value,
                "reasons": result.reasons,
                "analyzedAt": datetime.now(timezone.utc).isoformat(),
            },
            ConditionExpression="attribute_not_exists(transactionId)",
        )


def _item_to_transaction_event(item: dict) -> TransactionEvent:
    return TransactionEvent(
        transaction_id=item["transactionId"], user_id=item["userId"],
        amount=Decimal(str(item["amount"])), currency=item["currency"],
        merchant=item["merchant"],
        occurred_at=datetime.fromisoformat(item["occurredAt"]),
        published_at=datetime.fromisoformat(item.get("createdAt", item["occurredAt"])),
        latitude=float(item["latitude"]) if item.get("latitude") is not None else None,
        longitude=float(item["longitude"]) if item.get("longitude") is not None else None,
        merchant_category=item.get("merchantCategory"), payment_method=item.get("paymentMethod"),
        card_last_four_digits=item.get("cardLastFourDigits"), channel=item.get("channel"),
        ip_address=item.get("ipAddress"), device_id=item.get("deviceId"),
        billing_country=item.get("billingCountry"),
    )


def _coordinate_to_decimal(value: float | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None