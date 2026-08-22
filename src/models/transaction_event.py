"""
Espelha o record TransactionEvent do repositório fraud-detector-api
(messaging/TransactionEvent.java). Este é o contrato de mensagem entre os
dois repositórios — mudar um nome ou tipo de campo aqui sem mudar lá (ou
vice-versa) quebra a integração silenciosamente. Trate como uma mudança
deliberada, nunca incidental.
"""
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

    @staticmethod
    def from_dict(data: dict) -> "TransactionEvent":
        return TransactionEvent(
            transaction_id=data["transactionId"],
            user_id=data["userId"],
            amount=Decimal(str(data["amount"])),
            currency=data["currency"],
            merchant=data["merchant"],
            occurred_at=_parse_instant(data["occurredAt"]),
            published_at=_parse_instant(data["publishedAt"]),
        )


def _parse_instant(value: str) -> datetime:
    """Converte um Instant serializado pelo Jackson (ISO-8601, ex:
    '2026-08-20T05:12:33.123Z') para datetime timezone-aware em UTC."""
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
