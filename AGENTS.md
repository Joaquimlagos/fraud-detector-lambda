# AGENTS.md — fraud-detector-lambda

This file gives AI coding agents (OpenCode, via 9router) the context they need to work in this repository without re-explaining the architecture every session. Read this before making changes.

## Role in the system

This repo is **one of three** that make up the `fraud-detector` portfolio project:

| Repository | Responsibility |
|---|---|
| `fraud-detector-api` | Java/Spring Boot. Validates transaction *shape* and publishes to SQS. **Never** decides if a transaction is suspicious. |
| **`fraud-detector-lambda`** (this repo) | Consumes the SQS queue, queries the user's transaction history in DynamoDB, applies fraud rules, persists the result, and publishes an SNS alert when suspicious. |
| `fraud-detector-infra-aws` | Terraform for the shared infrastructure: DynamoDB tables, SQS queue, SNS topic. |

```
fraud-detector-api  —(SQS)→  fraud-detector-lambda  —(DynamoDB)→
                                    |
                                    └—(SNS, only if suspicious)→ email
```

**Hard rule: all fraud/business-logic decisions live here, not in the API.** The API only validates structure (required fields, format). This Lambda is the single source of truth for "is this transaction suspicious."

## Message contract with fraud-detector-api

The SQS message consumed here is produced by `fraud-detector-api`. Any change to this contract must be coordinated across repos — there is no shared code or shared types between them, only this documented contract.

> ⚠️ Confirm the exact field names/types against `models/transaction_event.py` before relying on this table — fill it in as the contract solidifies:

| Field | Type | Notes |
|---|---|---|
| `userId` | string | Confirm format (UUID?) — API validates presence/format, not existence |
| `transactionId` | string | |
| `amount` | number | |
| `timestamp` | string (ISO 8601) | |
| `...` | | Update this table as the schema evolves |

## Project structure

```
src/
  models/
    analysis_result.py        # Output shape: verdict/score produced by the rule engine
    transaction_event.py      # Deserialized shape of the incoming SQS message (the contract above)
  notifications/
    sns_notifier.py           # Publishes to SNS when a transaction is flagged
  repository/
    transactions_repository.py  # DynamoDB access: reads user history, persists analysis_result
  rules/
    base.py                   # Strategy pattern interface — all fraud rules implement this
    engine.py                 # Orchestrates: runs all registered rules, aggregates verdict
    time_of_day_rule.py        # Concrete rule: flags transactions at unusual hours
    velocity_rule.py           # Concrete rule: flags abnormal transaction frequency
  config.py                   # Environment/config loading
  main.py                     # Lambda entry point (handler): SQS trigger → engine → repository/notifier
terraform/
  data.tf, iam.tf, lambda.tf, outputs.tf, providers.tf, variables.tf
  local_override.tf.example, local.tfvars.example, terraform.tfvars.example
tests/
pytest.ini
requirements.txt / requirements-dev.txt
```

## Rules engine (Strategy Pattern)

- `rules/base.py` defines the interface every rule must implement (input: `transaction_event` + user history, output: a partial/contribution to `analysis_result`).
- `rules/engine.py` is the only place that knows about *all* rules — it registers and runs them in sequence and aggregates their outputs into a final verdict.
- Existing rules: `time_of_day_rule.py`, `velocity_rule.py`.

### How to add a new rule
1. Create `rules/<name>_rule.py` implementing the interface in `rules/base.py`.
2. Register it in `rules/engine.py`.
3. Add a focused unit test under `tests/` exercising the rule in isolation (mock history/input, assert verdict contribution).
4. Do not put any AWS/IO calls inside a rule — rules are pure logic; DynamoDB access stays in `repository/`.

## Repository layer

`repository/transactions_repository.py` is the only module allowed to talk to DynamoDB. It's responsible for:
- Fetching the user's transaction history needed by the rules (e.g. for `velocity_rule`).
- Persisting the `analysis_result` after the engine runs.

Do not query DynamoDB directly from `rules/` or `main.py` — always go through this module.

## Notifications

`notifications/sns_notifier.py` publishes an SNS alert **only when the aggregated verdict from the engine is suspicious**. Non-suspicious transactions are persisted but do not trigger a notification.

## Entry point flow (`main.py`)

1. Deserialize the SQS message into `transaction_event`.
2. Validate the `userId` exists (this Lambda's responsibility, not the API's — see architecture decision below). If it doesn't, reject the message (log + route to DLQ) instead of running it through the rule engine.
3. Fetch relevant history via `transactions_repository`.
4. Run `rules/engine.py` to get an `analysis_result`.
5. Persist the result via `transactions_repository`.
6. If suspicious, notify via `sns_notifier`.

## Architecture decisions to respect

- **userId existence validation happens here, not in the API.** The API only validates format/shape at publish time. This Lambda validates existence against DynamoDB before running fraud rules, since it already needs to query user data and the API shouldn't take on a synchronous DynamoDB read just to publish an event.
- **Fraud decisions never leave this repo.** The API and infra repos must never contain rule logic.
- **No cross-repo state or file references.** All shared infrastructure resources are referenced by name via Terraform data sources (see `terraform/data.tf`), not hardcoded IDs.

## Local development

- `terraform/local_override.tf.example` and `terraform/local.tfvars.example` — copy and adapt for local/LocalStack testing, consistent with how `fraud-detector-api` is already wired to LocalStack.
- `terraform/terraform.tfvars.example` — template for real AWS deployment variables.

## Testing

- Test runner config: `pytest.ini`.
- Dev-only dependencies: `requirements-dev.txt`.
- New rules and repository logic should always ship with a corresponding test in `tests/`.
- Run tests with: `pytest`

## Conventions for the agent

- Keep `rules/` free of AWS SDK calls — pure functions/classes only.
- Any change to the SQS message shape must be reflected in `models/transaction_event.py` **and** flagged to the user, since `fraud-detector-api` must be updated in lockstep (no shared types across repos).
- Prefer extending the Strategy pattern (new rule file) over branching logic inside `engine.py`.
- When in doubt about which repo owns a piece of logic, default to: shape validation → API, existence/business validation and fraud decisions → this Lambda, infrastructure → `fraud-detector-infra-aws`.