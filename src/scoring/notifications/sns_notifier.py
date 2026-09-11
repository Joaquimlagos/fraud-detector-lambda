"""Publishes suspicious transaction alerts to SNS."""
from __future__ import annotations

import json

import boto3

from src.shared.config import Config
from src.shared.models.analysis_result import AnalysisResult
from src.shared.models.transaction_event import TransactionEvent

_sns = boto3.client("sns")


class FraudAlertNotifier:
    def __init__(self, topic_arn: str = Config.SNS_TOPIC_ARN) -> None:
        self._topic_arn = topic_arn

    def notify(self, transaction: TransactionEvent, result: AnalysisResult) -> None:
        subject = f"Suspicious transaction detected — {transaction.transaction_id}"
        message = {
            "transactionId": transaction.transaction_id,
            "userId": transaction.user_id,
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "merchant": transaction.merchant,
            "occurredAt": transaction.occurred_at.isoformat(),
            "reasons": result.reasons,
        }
        _sns.publish(
            TopicArn=self._topic_arn,
            Subject=subject[:100],
            Message=json.dumps(message, indent=2),
        )