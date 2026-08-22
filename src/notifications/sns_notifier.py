"""Publica um alerta no SNS quando uma transação é considerada suspeita.
Único módulo que fala com o cliente SNS."""
from __future__ import annotations

import json

import boto3

from src.config import Config
from src.models.analysis_result import AnalysisResult
from src.models.transaction_event import TransactionEvent

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
            Subject=subject[:100],  # SNS limita Subject a 100 caracteres
            Message=json.dumps(message, indent=2),
        )
