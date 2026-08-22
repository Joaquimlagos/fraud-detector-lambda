"""
Entry point da Lambda (handler configurado em lambda.tf: "main.handler").

Fluxo por mensagem SQS:
  1. Parseia o body em um TransactionEvent
  2. Busca o histórico recente do usuário no DynamoDB
  3. Roda o AnalysisEngine (todas as regras de fraude)
  4. Persiste a transação com o status resultante (idempotente por
     transactionId — reentregas do SQS não duplicam o registro)
  5. Se suspeita, publica um alerta no SNS

Nenhuma decisão de negócio mora aqui — este módulo só orquestra as chamadas
para os outros, que são os donos da lógica real.
"""
from __future__ import annotations

import json
import logging

from botocore.exceptions import ClientError

from src.config import Config
from src.models.transaction_event import TransactionEvent
from src.notifications.sns_notifier import FraudAlertNotifier
from src.repository.transactions_repository import TransactionsRepository
from src.rules.engine import AnalysisEngine

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_repository = TransactionsRepository()
_notifier = FraudAlertNotifier()
_engine = AnalysisEngine()


def handler(event: dict, context) -> None:
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
        # Sem partial batch failure reporting configurado no event source
        # mapping, uma exceção aqui faz o SQS reentregar o LOTE inteiro
        # (inclusive as mensagens que já processaram com sucesso). Para um
        # lote maior que 1 em produção, vale configurar
        # function_response_types = ["ReportBatchItemFailures"] no
        # aws_lambda_event_source_mapping para reentregar só as que
        # falharam.
        raise RuntimeError(f"Failed to process {len(failures)} message(s): {failures}")


def _process_record(record: dict) -> None:
    body = json.loads(record["body"])
    transaction = TransactionEvent.from_dict(body)

    logger.info("Analyzing transaction %s for user %s", transaction.transaction_id, transaction.user_id)

    recent_history = _repository.find_recent_by_user(
        user_id=transaction.user_id,
        window_minutes=Config.VELOCITY_WINDOW_MINUTES,
    )

    result = _engine.analyze(transaction, recent_history)

    try:
        _repository.save(transaction, result)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # Já processamos esta transactionId antes (reentrega do SQS).
            # Não é um erro — apenas não reprocessa nem notifica de novo.
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
