"""
Teste de integração leve do handler, com DynamoDB e SNS simulados via
moto (não bate na AWS real nem no LocalStack). Cobre o fluxo ponta a
ponta: mensagem SQS -> análise -> persistência -> notificação condicional.
"""
from __future__ import annotations

import json

import boto3
import pytest
from moto import mock_aws

from src.config import Config


def _sqs_record(transaction_id: str, occurred_at_iso: str) -> dict:
    body = {
        "transactionId": transaction_id,
        "userId": "user-1",
        "amount": "50.00",
        "currency": "USD",
        "merchant": "Some Store",
        "occurredAt": occurred_at_iso,
        "publishedAt": occurred_at_iso,
    }
    return {"messageId": f"msg-{transaction_id}", "body": json.dumps(body)}


@pytest.fixture
def aws_environment():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName=Config.TRANSACTIONS_TABLE,
            AttributeDefinitions=[
                {"AttributeName": "transactionId", "AttributeType": "S"},
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "occurredAt", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "transactionId", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "userId-occurredAt-index",
                    "KeySchema": [
                        {"AttributeName": "userId", "KeyType": "HASH"},
                        {"AttributeName": "occurredAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        sns = boto3.client("sns", region_name="us-east-1")
        topic = sns.create_topic(Name="test-topic")

        sqs = boto3.client("sqs", region_name="us-east-1")
        queue = sqs.create_queue(QueueName="test-verification-queue")
        queue_arn = sqs.get_queue_attributes(
            QueueUrl=queue["QueueUrl"], AttributeNames=["QueueArn"]
        )["Attributes"]["QueueArn"]
        sns.subscribe(TopicArn=topic["TopicArn"], Protocol="sqs", Endpoint=queue_arn)

        yield {"dynamodb": dynamodb, "sqs": sqs, "queue_url": queue["QueueUrl"]}


def test_should_approve_and_not_notify_when_transaction_is_not_suspicious(aws_environment):
    from src.main import handler  # import após o mock_aws estar ativo

    event = {
        "Records": [_sqs_record("txn-approved", "2026-08-20T14:00:00Z")]
    }

    handler(event, context=None)

    table = aws_environment["dynamodb"].Table(Config.TRANSACTIONS_TABLE)
    item = table.get_item(Key={"transactionId": "txn-approved"})["Item"]
    assert item["status"] == "APPROVED"

    messages = aws_environment["sqs"].receive_message(QueueUrl=aws_environment["queue_url"])
    assert "Messages" not in messages


def test_should_flag_suspicious_and_notify_when_inside_risk_window(aws_environment):
    from src.main import handler

    event = {
        "Records": [_sqs_record("txn-suspicious", "2026-08-20T03:00:00Z")]
    }

    handler(event, context=None)

    table = aws_environment["dynamodb"].Table(Config.TRANSACTIONS_TABLE)
    item = table.get_item(Key={"transactionId": "txn-suspicious"})["Item"]
    assert item["status"] == "SUSPICIOUS"
    assert len(item["reasons"]) > 0

    messages = aws_environment["sqs"].receive_message(QueueUrl=aws_environment["queue_url"])
    assert "Messages" in messages
    assert len(messages["Messages"]) == 1


def test_should_skip_silently_when_transaction_already_processed(aws_environment):
    from src.main import handler

    event = {
        "Records": [_sqs_record("txn-duplicate", "2026-08-20T14:00:00Z")]
    }

    handler(event, context=None)  # primeira entrega
    handler(event, context=None)  # reentrega do SQS — não deve lançar erro

    table = aws_environment["dynamodb"].Table(Config.TRANSACTIONS_TABLE)
    response = table.scan()
    matching = [i for i in response["Items"] if i["transactionId"] == "txn-duplicate"]
    assert len(matching) == 1  # não duplicou o registro
