"""Fixtures compartilhadas entre os testes."""
from __future__ import annotations

import os

# Precisa ser definido ANTES de qualquer import de src.shared.config/src.main,
# já que Config lê os.environ no momento da importação da classe.
os.environ.setdefault("TRANSACTIONS_TABLE", "test-transactions")
os.environ.setdefault("USERS_TABLE", "test-users")
os.environ.setdefault("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:test-topic")
os.environ.setdefault("ENVIRONMENT", "test")

# Em produção, o runtime da Lambda já define isso automaticamente.
# Localmente (testes, LocalStack), precisa ser explícito.
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.shared.models.transaction_event import TransactionEvent


@pytest.fixture
def make_transaction():
    """Factory de TransactionEvent com valores padrão sensatos —
    testes sobrescrevem só o campo que importa para o cenário."""

    def _make(
        transaction_id: str = "txn-1",
        user_id: str = "user-1",
        amount: Decimal = Decimal("100.00"),
        currency: str = "USD",
        merchant: str = "Some Store",
        occurred_at: datetime = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
        published_at: datetime = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> TransactionEvent:
        return TransactionEvent(
            transaction_id=transaction_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            merchant=merchant,
            occurred_at=occurred_at,
            published_at=published_at,
            latitude=latitude,
            longitude=longitude,
        )

    return _make
