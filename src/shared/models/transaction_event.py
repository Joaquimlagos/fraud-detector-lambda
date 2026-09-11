"""Transaction contract shared by the SQS and direct-invocation flows."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True)
class TransactionEvent:
    transaction_id: str
    user_id: str
    amount: Decimal
    currency: str
    merchant: str
    occurred_at: datetime
    published_at: datetime
    latitude: float | None = None
    longitude: float | None = None
    merchant_category: str | None = None
    payment_method: str | None = None
    card_last_four_digits: str | None = None
    channel: str | None = None
    ip_address: str | None = None
    device_id: str | None = None
    billing_country: str | None = None

    @staticmethod
    def from_dict(data: dict, fallback_transaction_id: str | None = None) -> "TransactionEvent":
        transaction_id = data.get("transactionId", fallback_transaction_id)
        if transaction_id is None:
            raise KeyError("transactionId")
        return TransactionEvent(
            transaction_id=transaction_id,
            user_id=data["userId"],
            amount=Decimal(str(data["amount"])),
            currency=data["currency"],
            merchant=data["merchant"],
            occurred_at=_parse_instant(data["occurredAt"]),
            published_at=_parse_instant(data.get("publishedAt", data["occurredAt"])),
            latitude=_optional_float(data.get("latitude")),
            longitude=_optional_float(data.get("longitude")),
            merchant_category=data.get("merchantCategory"),
            payment_method=data.get("paymentMethod"),
            card_last_four_digits=data.get("cardLastFourDigits"),
            channel=data.get("channel"),
            ip_address=data.get("ipAddress"),
            device_id=data.get("deviceId"),
            billing_country=data.get("billingCountry"),
        )


def _parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)