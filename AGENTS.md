# AGENTS.md — fraud-detector-lambda

This file gives AI coding agents (OpenCode, via 9router) the context they need to work in this repository without re-explaining the architecture every session. Read this before making changes.

## Role in the system

This repo is **one of three** that make up the `fraud-detector` portfolio project:

| Repository | Responsibility |
|---|---|
| `fraud-detector-api` | Java/Spring Boot. Validates transaction *shape* and publishes to SQS. **Never** decides if a transaction is suspicious. |
| **`fraud-detector-lambda`** (this repo) | Runs asynchronous SQS scoring and direct-invocation RAG investigation using DynamoDB and 9router. |
| `fraud-detector-infra-aws` | Terraform for the shared infrastructure: DynamoDB tables, SQS queue, SNS topic. |

```
fraud-detector-api  —(SQS)→ scoring Lambda —(DynamoDB)→ fraud result
  |
  └—(RequestResponse)→ analysis Lambda —(DynamoDB/retrieval)→ 9router/LLM
             |
             └—(SNS from scoring, only if suspicious)→ email
```

**Hard rule: all fraud/business-logic decisions live here, not in the API.** The API only validates structure (required fields, format). This Lambda is the single source of truth for "is this transaction suspicious."

## Scoring message contract with fraud-detector-api

The SQS message consumed here is produced by `fraud-detector-api`. Any change to this contract must be coordinated across repos — there is no shared code or shared types between them, only this documented contract.

The exact field names/types are defined in `src/shared/models/transaction_event.py` and must stay coordinated with the API:

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
  shared/
    config.py                 # Environment configuration for both flows
    models/                   # TransactionEvent and AnalysisResult contracts
    repository/               # Shared DynamoDB transaction/history access
  scoring/
    handler.py                # SQS Lambda entry point
    rules/                    # Pure fraud scoring strategies and engine
    notifications/            # SNS alerts for suspicious scoring results
    repository/               # Scoring-only user existence access
  analysis/
    handler.py                # Direct invocation entry point: {transactionId}
    cache.py                  # Investigation result cache
    retrieval/vector_search.py # Local-friendly similarity retrieval
    prompt_builder.py         # Transaction + rules + similar-case prompt
    llm_client.py             # 9router OpenAI-compatible client
  main.py                     # Backward-compatible import of scoring.handler
terraform/
  data.tf, iam.tf, lambda.tf, outputs.tf, providers.tf, variables.tf
  local_override.tf.example, local.tfvars.example, terraform.tfvars.example
tests/
pytest.ini
requirements.txt / requirements-dev.txt
```

## Scoring rules engine (Strategy Pattern)

- `scoring/rules/base.py` defines the interface every rule must implement (input: `transaction_event` + user history, output: a partial/contribution to `analysis_result`).
- `scoring/rules/engine.py` is the only place that knows about *all* rules — it registers and runs them in sequence and aggregates their outputs into a final verdict.
- Existing rules: `time_of_day_rule.py`, `velocity_rule.py`, and `impossible_travel_rule.py`.

### How to add a new rule
1. Create `scoring/rules/<name>_rule.py` implementing the interface in `scoring/rules/base.py`.
2. Register it in `scoring/rules/engine.py`.
3. Add a focused unit test under `tests/` exercising the rule in isolation (mock history/input, assert verdict contribution).
4. Do not put any AWS/IO calls inside a rule — rules are pure logic; DynamoDB access stays in `shared/repository/`.

## Shared repository layer

`shared/repository/transactions_repository.py` is the only module allowed to talk to the transactions DynamoDB table. It's responsible for:
- Fetching the user's transaction history needed by the rules (e.g. for `velocity_rule`).
- Persisting the `analysis_result` after the engine runs.
- Loading a transaction and its scoring result for the analysis flow.
- Scanning stored transactions for local-friendly similarity retrieval.

Do not query the transactions table directly from `scoring/rules/` or `analysis/` — always go through this module. The RAG cache has its own adapter in `analysis/cache.py`.

## Scoring notifications

`scoring/notifications/sns_notifier.py` publishes an SNS alert **only when the aggregated verdict from the scoring engine is suspicious**. Non-suspicious transactions are persisted but do not trigger a notification. The RAG flow does not publish SNS alerts.

## Scoring entry point flow (`scoring/handler.py`)

1. Deserialize the SQS message into `transaction_event`.
2. Validate the `userId` exists (this Lambda's responsibility, not the API's — see architecture decision below). If it doesn't, reject the message (log + route to DLQ) instead of running it through the rule engine.
3. Fetch relevant history via `transactions_repository`.
4. Run `scoring/rules/engine.py` to get an `analysis_result`.
5. Persist the result via `shared/repository/transactions_repository.py`.
6. If suspicious, notify via `sns_notifier`.

## RAG analysis flow (`analysis/handler.py`)

The Java API invokes this Lambda directly with AWS SDK `InvocationType.REQUEST_RESPONSE`; it does not publish an analysis request to SQS.

Input contract:

```json
{"transactionId":"abc-123"}
```

The handler validates the ID, checks `analysis/cache.py`, loads the transaction and scoring result, retrieves similar cases, builds a prompt, and calls the configured 9router gateway. The prompt contains only transaction fields, triggered scoring reasons, and retrieved-case identifiers/similarities. The model must explain the status using only that context and must not invent facts.

The analysis result is saved with reasoning, status, similar cases, and timestamp. The public response intentionally contains only:

```json
{
  "transactionId": "abc-123",
  "status": "suspicious",
  "reasoning": "...",
  "cached": false
}
```

`similarCases` remains internal to retrieval, prompting, and cache persistence; it is not returned to the Java API.

The LLM client calls `POST {LLM_BASE_URL}/chat/completions` and supports standard JSON responses and the 9router response format that uses `Content-Type: text/event-stream` with a trailing `data: [DONE]` marker. The client is mockable and tests must never call the real gateway.

## Architecture decisions to respect

- **userId existence validation happens here, not in the API.** The API only validates format/shape at publish time. This Lambda validates existence against DynamoDB before running fraud rules, since it already needs to query user data and the API shouldn't take on a synchronous DynamoDB read just to publish an event.
- **Fraud decisions never leave this repo.** The API and infra repos must never contain rule logic.
- **No cross-repo state or file references.** All shared infrastructure resources are referenced by name via Terraform data sources (see `terraform/data.tf`), not hardcoded IDs.

## Local development

- `terraform/local_override.tf.example` and `terraform/local.tfvars.example` — copy and adapt for local/LocalStack testing, consistent with how `fraud-detector-api` is already wired to LocalStack.
- `terraform/terraform.tfvars.example` — template for real AWS deployment variables.
- `llm_base_url`, `llm_model`, and `llm_api_key` configure the analysis Lambda's 9router gateway. Keep secrets in ignored local/secret Terraform variable files.
- Keep `llm_api_key` out of `terraform/local.tfvars`; load it from an ignored root `.env` as `TF_VAR_llm_api_key` before running Terraform.
- Terraform outputs `analysis_lambda_function_name` and `analysis_lambda_function_arn` for the Java API integration.

## Testing

- Test runner config: `pytest.ini`.
- Dev-only dependencies: `requirements-dev.txt`.
- New rules and repository logic should always ship with a corresponding test in `tests/`.
- Run tests with: `pytest`

## Conventions for the agent

- Keep `scoring/rules/` free of AWS SDK calls — pure functions/classes only.
- Any change to the SQS message shape must be reflected in `shared/models/transaction_event.py` **and** flagged to the user, since `fraud-detector-api` must be updated in lockstep (no shared types across repos).
- Prefer extending the Strategy pattern (new rule file) over branching logic inside `engine.py`.
- When in doubt about which repo owns a piece of logic, default to: shape validation → API, existence/business validation and fraud decisions → this Lambda, infrastructure → `fraud-detector-infra-aws`.