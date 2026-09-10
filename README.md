# fraud-detector-lambda

AWS Lambda (Python) responsible for analyzing transactions for potential fraud. Part of the **fraud-detector** system — a portfolio project demonstrating Java + AWS + event-driven architecture + asynchronous processing + NoSQL persistence + decoupled notifications.

## Where this fits

This repository is one of three that together make up the system:

| Repository | Responsibility |
|---|---|
| `fraud-detector-api` | Java/Spring Boot API. Validates transactions and publishes them to SQS. **Never** decides if a transaction is suspicious. |
| **`fraud-detector-lambda`** (this repo) | Consumes the SQS queue, queries the user's transaction history in DynamoDB, applies fraud rules, persists the result, and publishes an SNS alert when suspicious. |
| `fraud-detector-infra-aws` | Terraform for the shared infrastructure: DynamoDB tables, SQS queue, SNS topic. |

```
fraud-detector-api  ──(SQS)──▶  fraud-detector-lambda  ──(DynamoDB)──▶  fraud-detector-lambda
                                         │
                                         └──(SNS, only if suspicious)──▶ email
```

The Lambda's own AWS resources (IAM role, function, SQS trigger) are defined in this repo's `terraform/` folder — they reference the shared resources created by `fraud-detector-infra-aws` by name, via Terraform data sources (no cross-repo state, no cross-repo file paths).

## Project structure

```
src/
├── main.py                          # Lambda entry point (handler = "main.handler")
├── config.py                         # Reads environment variables — nothing else should call os.environ directly
├── models/
│   ├── transaction_event.py           # Mirrors the TransactionEvent record from fraud-detector-api — the message contract
│   └── analysis_result.py              # Outcome of the analysis: status + reasons
├── rules/
│   ├── base.py                          # FraudRule interface
│   ├── time_of_day_rule.py               # Flags transactions in a high-risk hour window (default 2h-7h)
│   ├── velocity_rule.py                   # Flags too many transactions from the same user in a short window
│   └── engine.py                           # Runs every rule and aggregates the result
├── repository/
│   └── transactions_repository.py    # DynamoDB access: query history, persist result (idempotent by transactionId)
└── notifications/
    └── sns_notifier.py                # Publishes a fraud alert to SNS

tests/                                # pytest + moto (mocked AWS, no real/LocalStack calls needed to run)
terraform/                            # This Lambda's own AWS resources — see its own local_override.tf.example for local dev
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Running tests

```bash
pytest -v
```

All 12 tests run against **mocked AWS** (via [moto](https://github.com/getmoto/moto)) — no LocalStack container and no real AWS credentials needed. This covers the fraud rules in isolation, the rule engine, and an end-to-end handler flow (SQS message in → DynamoDB write → conditional SNS publish, including the idempotency path for redelivered messages).

## Local development against LocalStack

This is for testing the *deployed* Lambda behavior (via Terraform + a real event source mapping), not for running the tests above — the tests don't need any of this.

1. **Start LocalStack** — it lives in the `fraud-detector-infra-aws` repo, not here:
   ```bash
   docker compose -f ../fraud-detector-infra-aws/docker-compose.localstack.yml up -d
   ```
   (adjust the relative path to wherever you cloned that repo)

2. **Apply the shared infra first** — this Lambda's Terraform looks up the SQS queue/DynamoDB tables/SNS topic by name; they must already exist:
   ```bash
   cd ../fraud-detector-infra-aws/terraform
   cp local_override.tf.example local_override.tf
   cp local.tfvars.example local.tfvars
   terraform init && terraform apply -var-file=local.tfvars
   ```

3. **Then apply this repo's Terraform**, with matching `project_name`/`environment`:
   ```bash
   cd terraform
   cp local_override.tf.example local_override.tf
   cp local.tfvars.example local.tfvars
   terraform init && terraform apply -var-file=local.tfvars
   ```

⚠️ `project_name` and `environment` in `local.tfvars` **must match** between the two repos — that's how the data sources in `terraform/data.tf` find the right resources by name.

## Deploying to real AWS

Same two-step order, without `local_override.tf` present in either repo (so both point to real AWS by default) and using `terraform.tfvars` (your real values) instead of `local.tfvars`. See the "Deploy" section of `fraud-detector-infra-aws`'s README for the full checklist (credentials, IAM permissions needed, reading the plan before applying).

## Environment variables

Set automatically by Terraform (`environment` block in `terraform/lambda.tf`) when deployed — you shouldn't need to set these by hand except for local test runs, where `tests/conftest.py` already provides safe defaults.

| Variable | Purpose |
|---|---|
| `TRANSACTIONS_TABLE` | DynamoDB table name for transaction records |
| `USERS_TABLE` | DynamoDB table name for users |
| `SNS_TOPIC_ARN` | Topic the Lambda publishes fraud alerts to |
| `ENVIRONMENT` | `dev` or `prod` — informational, used in logs |
| `SUSPICIOUS_HOUR_START` / `SUSPICIOUS_HOUR_END` | Time-of-day rule window (default `2` / `7`) |
| `VELOCITY_WINDOW_MINUTES` / `VELOCITY_MAX_TRANSACTIONS` | Velocity rule thresholds (default `2` minutes / `3` transactions) |

## Fraud rules

Each rule lives in its own file under `src/rules/` and implements `FraudRule.evaluate(transaction, recent_history) -> str | None`. `AnalysisEngine` runs the full list and flags the transaction as `SUSPICIOUS` if **any** rule returns a reason; otherwise it's `APPROVED`. Adding a new rule means creating a new class and adding it to `DEFAULT_RULES` in `src/rules/engine.py` — no other code changes.

Currently implemented:
- **`TimeOfDayRule`** — flags transactions occurring inside a configurable high-risk hour window.
- **`VelocityRule`** — flags a user having more than N transactions within a short time window, based on a DynamoDB query against the `userId-occurredAt-index` GSI.

## Message contract with `fraud-detector-api`

The SQS message body is a JSON object consumed by `TransactionEvent` (`src/models/transaction_event.py`):

```json
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
   "occurredAt": "2026-09-03T18:30:00Z"
}
```

Additional fields are accepted and ignored by the fraud engine. If `transactionId` is absent, the Lambda uses the SQS `messageId` as the persistence and idempotency key. For business-level deduplication, the API should eventually include a stable `transactionId` in the message.
