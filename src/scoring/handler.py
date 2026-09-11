"""Entry point for the SQS-driven fraud scoring Lambda."""
from __future__ import annotations

import json
import logging

from botocore.exceptions import ClientError

from src.shared.config import Config
from src.shared.models.transaction_event import TransactionEvent
from src.shared.repository.transactions_repository import TransactionsRepository
from src.scoring.repository.users_repository import UsersRepository
from src.scoring.notifications.sns_notifier import FraudAlertNotifier
from src.scoring.rules.engine import AnalysisEngine

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_repository = TransactionsRepository()
_users_repository = UsersRepository()
_notifier = FraudAlertNotifier()
_engine = AnalysisEngine()


def handler(event: dict, context: object) -> dict[str, list[dict[str, str]]]:
    records = event.get("Records", [])
    logger.info("Processing %d SQS message(s)", len(records))

    failures: list[str] = []

    for record in records:
        message_id = record.get("messageId", "unknown")
        try:
            _process_record(record)
        except Exception:
            logger.exception("Failed to process SQS message %s", message_id)
            failures.append(message_id)

    if failures:
        return {"batchItemFailures": [{"itemIdentifier": message_id} for message_id in failures]}

    return {"batchItemFailures": []}


def _process_record(record: dict) -> None:
    body = json.loads(record["body"])
    transaction = TransactionEvent.from_dict(
        body, fallback_transaction_id=record["messageId"]
    )

    logger.info("Analyzing transaction %s for user %s", transaction.transaction_id, transaction.user_id)

    if not _users_repository.exists(transaction.user_id):
        raise ValueError(f"User {transaction.user_id} does not exist")

    recent_history = _repository.find_recent_by_user(
        user_id=transaction.user_id,
        window_minutes=Config.VELOCITY_WINDOW_MINUTES,
    )
    last_transaction = _repository.find_last_by_user(transaction.user_id)
    history = recent_history
    if last_transaction is not None and all(
        item.transaction_id != last_transaction.transaction_id for item in history
    ):
        history = [*history, last_transaction]

    result = _engine.analyze(transaction, history)

    try:
        _repository.save(transaction, result)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.info("Transaction %s already processed, skipping", transaction.transaction_id)
            return
        raise

    if result.is_suspicious:
        logger.warning(
            "Transaction %s flagged as suspicious: %s",
            transaction.transaction_id,
            result.reasons,
        )
        _notifier.notify(transaction, result)
    else:
        logger.info("Transaction %s approved", transaction.transaction_id)