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
            TableName=Config.USERS_TABLE,
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "userId", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        users_table = dynamodb.Table(Config.USERS_TABLE)
        users_table.put_item(Item={"userId": "user-1"})
        users_table.put_item(
            Item={"userId": "ae40fbce-5318-4fbe-9087-a50d18fea769"}
        )

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


def test_should_process_api_payload_without_optional_identifiers(aws_environment):
    from src.main import handler

    event = {
        "Records": [
            {
                "messageId": "sqs-message-1",
                "body": json.dumps(
                    {
                        "userId": "ae40fbce-5318-4fbe-9087-a50d18fea769",
                        "amount": 250.00,
                        "currency": "BRL",
                        "merchant": "Amazon BR",
                        "merchantCategory": "retail",
                        "paymentMethod": "CREDIT_CARD",
                        "cardLastFourDigits": "4532",
                        "channel": "MOBILE_APP",
                        "ipAddress": "192.168.1.100",
                        "deviceId": "device-abc-123",
                        "latitude": -23.5505,
                        "longitude": -46.6333,
                        "billingCountry": "BR",
                        "occurredAt": "2026-09-03T18:30:00Z",
                    }
                ),
            }
        ]
    }

    handler(event, context=None)

    table = aws_environment["dynamodb"].Table(Config.TRANSACTIONS_TABLE)
    item = table.get_item(Key={"transactionId": "sqs-message-1"})["Item"]
    assert item["userId"] == "ae40fbce-5318-4fbe-9087-a50d18fea769"
    assert item["status"] == "APPROVED"
    assert item["merchantCategory"] == "retail"
    assert item["paymentMethod"] == "CREDIT_CARD"
    assert item["cardLastFourDigits"] == "4532"
    assert item["channel"] == "MOBILE_APP"
    assert item["ipAddress"] == "192.168.1.100"
    assert item["deviceId"] == "device-abc-123"
    assert item["billingCountry"] == "BR"
    assert item["createdAt"] == "2026-09-03T18:30:00+00:00"


def test_should_reject_transaction_when_user_does_not_exist(aws_environment):
    from src.main import handler

    event = {
        "Records": [_sqs_record("txn-unknown-user", "2026-08-20T14:00:00Z")]
    }

    result = handler(event, context=None)

    assert result == {
        "batchItemFailures": [{"itemIdentifier": "msg-txn-unknown-user"}]
    }
    table = aws_environment["dynamodb"].Table(Config.TRANSACTIONS_TABLE)
    assert "Item" not in table.get_item(Key={"transactionId": "txn-unknown-user"})
