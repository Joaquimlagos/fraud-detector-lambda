# fraud-detector-lambda

AWS Lambda (Python) responsible for analyzing transactions for potential fraud. Part of the **fraud-detector** system — a portfolio project demonstrating Java + AWS + event-driven architecture + asynchronous processing + NoSQL persistence + decoupled notifications.

## Where this fits

This repository is one of three that together make up the system:

| Repository | Responsibility |
|---|---|
| `fraud-detector-api` | Java/Spring Boot API. Validates transactions and publishes them to SQS. **Never** decides if a transaction is suspicious. |
| **`fraud-detector-lambda`** (this repo) | Runs asynchronous SQS scoring and a direct-invocation RAG investigation flow backed by DynamoDB and 9router. |
| `fraud-detector-infra-aws` | Terraform for the shared infrastructure: DynamoDB tables, SQS queue, SNS topic. |

```
fraud-detector-api ──(SQS)──────────────▶ scoring Lambda ──(DynamoDB)──▶ fraud result
   │                                      │
   │                                      └──(SNS, only if suspicious)──▶ email
   │
   └──(RequestResponse)──▶ analysis Lambda ──▶ cache/retrieval ──▶ 9router/LLM
```

The Lambda's own AWS resources (IAM role, function, SQS trigger) are defined in this repo's `terraform/` folder — they reference the shared resources created by `fraud-detector-infra-aws` by name, via Terraform data sources (no cross-repo state, no cross-repo file paths).

## Project structure

```
src/
├── main.py                          # Backward-compatible scoring import
├── scoring/                          # SQS scoring Lambda
│   ├── handler.py                    # Handler = "src.scoring.handler.handler"
│   ├── rules/                        # Fraud scoring strategies and engine
│   ├── notifications/                # SNS alerts for suspicious transactions
│   └── repository/                   # Scoring-only user access
├── shared/                           # Contracts and persistence used by both flows
│   ├── config.py                     # Environment configuration
│   ├── models/                       # Transaction and scoring result contracts
│   └── repository/                   # Shared transaction history/result access
└── analysis/                         # Direct-invocation RAG investigation flow
   ├── handler.py                     # Handler for {"transactionId": "..."}
   ├── cache.py                        # DynamoDB-backed investigation cache
   ├── llm_client.py                  # OpenAI-compatible 9router client, including SSE responses
   └── retrieval/vector_search.py     # Local-friendly similarity retrieval

tests/                                # pytest + moto (mocked AWS, no real/LocalStack calls needed to run)
terraform/                            # This Lambda's own AWS resources — see its own local_override.tf.example for local dev
```

## Setup

Prerequisites:

- Python 3.11 or later
- Docker Desktop, when using LocalStack
- Terraform, when deploying the Lambda to LocalStack or AWS
- The `fraud-detector-infra-aws` repository cloned next to this repository

Create the virtual environment and install the development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

On PowerShell, activate the environment with:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## Running tests

```bash
pytest -v
```

The tests run against **mocked AWS** (via [moto](https://github.com/getmoto/moto)) — no LocalStack container and no real AWS credentials needed. They cover scoring rules, the scoring handler flow, RAG prompt/cache/handler behavior, and the OpenAI-compatible 9router response contract without making a real LLM call.

## Run locally with LocalStack

There are two local workflows:

- Run `pytest` to test the handlers and rules with mocked AWS services. This is the fastest workflow and does not require Docker or AWS credentials.
- Use LocalStack to package and deploy both Lambda functions, DynamoDB tables, SQS, and SNS. This exercises the deployed handler flow locally.

The LocalStack workflow requires the `fraud-detector-infra-aws` repository because it creates the shared DynamoDB tables, SQS queue, and SNS topic.

### 1. Start LocalStack

From the root of this repository, start the LocalStack container defined in `fraud-detector-infra-aws`:

   ```bash
   docker compose -f ../fraud-detector-infra-aws/docker-compose.localstack.yml up -d
   ```

Adjust the path if the repositories are not siblings. Confirm that the container is running before continuing:

```bash
docker ps
```

### 2. Create the shared LocalStack resources

This repository looks up the SQS queue, DynamoDB tables, and SNS topic by name, so the shared infrastructure must be applied first:

   ```bash
   cd ../fraud-detector-infra-aws/terraform
   cp local_override.tf.example local_override.tf
   cp local.tfvars.example local.tfvars
   terraform init && terraform apply -var-file=local.tfvars
   ```

### 3. Deploy both Lambda functions locally

From this repository, copy the local-only Terraform files and apply them with matching `project_name` and `environment` values:

   ```bash
   cd terraform
   cp local_override.tf.example local_override.tf
   cp local.tfvars.example local.tfvars
   terraform init
   terraform apply -var-file=local.tfvars
   ```

PowerShell equivalents:

```powershell
Copy-Item local_override.tf.example local_override.tf
Copy-Item local.tfvars.example local.tfvars
terraform init
terraform apply -var-file="local.tfvars"
```

`project_name` and `environment` in `local.tfvars` **must match** between both repositories. These values are used by the data sources in `terraform/data.tf` to find the shared resources.

The local `terraform/local.tfvars` file contains only non-sensitive LLM settings:

```hcl
llm_base_url = "http://host.docker.internal:20128/v1"
llm_model    = "fraud-detector-9router"
```

Keep the gateway key in the root `.env` file. The file is ignored by Git; create it manually with this format and replace the placeholder with your local gateway key:

```dotenv
TF_VAR_llm_api_key="your-local-key"
```

Never commit `.env`, `terraform/local.tfvars`, `terraform/local_override.tf`, or any Terraform state file.

PowerShell:

```powershell
Set-Location terraform
$envFile = Get-Content ..\.env | ConvertFrom-StringData
$env:TF_VAR_llm_api_key = $envFile.TF_VAR_llm_api_key.Trim('"')
terraform apply -auto-approve -var-file="local.tfvars"
```

Bash:

```bash
set -a
. ./.env
set +a
cd terraform
terraform apply -auto-approve -var-file=local.tfvars
```

Terraform automatically maps `TF_VAR_llm_api_key` to the `llm_api_key` variable. The API key is passed to the analysis Lambda only through Terraform variables; never print it in logs.

### 4. Invoke the functions

Invoke the analysis Lambda directly through LocalStack from PowerShell:

```powershell
docker exec fraud-detector-localstack awslocal lambda invoke `
   --function-name fraud-detector-analysis-dev `
   --invocation-type RequestResponse `
   --payload '{\"transactionId\":\"abc-123\"}' `
   /tmp/analysis-response.json

docker exec fraud-detector-localstack cat /tmp/analysis-response.json
```

For Bash, use `\` for line continuation instead of PowerShell backticks. The transaction must already exist in the shared DynamoDB table, normally after the scoring flow has processed its SQS event.

To test the scoring Lambda, publish a valid transaction message to the LocalStack SQS queue. The queue name is `fraud-detector-transaction-queue-dev` when using the example values:

```powershell
docker exec fraud-detector-localstack awslocal sqs send-message `
   --queue-url http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/fraud-detector-transaction-queue-dev `
   --message-body '{"userId":"user-123","amount":250.00,"currency":"BRL","merchant":"Amazon BR","merchantCategory":"retail","paymentMethod":"CREDIT_CARD","cardLastFourDigits":"4532","channel":"MOBILE_APP","ipAddress":"192.168.1.100","deviceId":"device-abc-123","latitude":-23.5505,"longitude":-46.6333,"billingCountry":"BR","occurredAt":"2026-09-03T18:30:00Z"}'
```

The SQS event source mapping invokes the scoring Lambda. Inspect the result in DynamoDB or the LocalStack logs:

```powershell
docker logs fraud-detector-localstack --tail 100
```

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
| `ANALYSIS_TABLE` | Dedicated DynamoDB cache table for investigation analyses |
| `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY` | OpenAI-compatible 9router gateway settings |

The investigation Lambda is deployed separately as `src.analysis.handler.handler`.
It receives a direct invocation payload such as `{ "transactionId": "abc-123" }`,
checks the analysis cache, retrieves similar stored transactions, and only then
calls the configured LLM. Scoring lives in `src.scoring.handler.handler` and is still
triggered exclusively by SQS.

The analysis flow is:

1. Validate `transactionId`.
2. Return cached reasoning when an analysis already exists.
3. Load the transaction and scoring result from DynamoDB.
4. Retrieve similar historical transactions from stored DynamoDB records.
5. Build a bounded prompt with transaction data, triggered scoring reasons, and retrieved cases.
6. Call `POST {LLM_BASE_URL}/chat/completions` through 9router.
7. Save reasoning, status, similar cases, and timestamp in the analysis cache table.
8. Return `transactionId`, `status`, `reasoning`, and `cached` to the caller.

Retrieved cases are internal RAG context. They are not included in the public response to the Java API.

The Java API needs permission to invoke the analysis function:

```json
{
   "Effect": "Allow",
   "Action": "lambda:InvokeFunction",
   "Resource": "arn:aws:lambda:<region>:<account>:function:fraud-detector-analysis-<environment>"
}
```

Use the Terraform outputs `analysis_lambda_function_name` or `analysis_lambda_function_arn` when configuring the API.

The RAG Lambda is ready to call an OpenAI-compatible 9router gateway, but a real
LLM call requires `llm_base_url` and `llm_model` to be supplied to Terraform.
The client sends `POST {LLM_BASE_URL}/chat/completions` with a `model` and one
user message. It accepts both standard JSON responses and the 9router streaming
response format (`text/event-stream` with a trailing `data: [DONE]`). After deployment, use the Terraform output
`analysis_lambda_function_name` to configure the Java API and invoke it with
`InvocationType.REQUEST_RESPONSE`.

## Fraud rules

Each rule lives in its own file under `src/scoring/rules/` and implements `FraudRule.evaluate(transaction, recent_history) -> str | None`. `AnalysisEngine` runs the full list and flags the transaction as `SUSPICIOUS` if **any** rule returns a reason; otherwise it's `APPROVED`. Adding a new rule means creating a new class and adding it to `DEFAULT_RULES` in `src/scoring/rules/engine.py` — no other code changes.

Currently implemented:
- **`TimeOfDayRule`** — flags transactions occurring inside a configurable high-risk hour window.
- **`VelocityRule`** — flags a user having more than N transactions within a short time window, based on a DynamoDB query against the `userId-occurredAt-index` GSI.

## Message contract with `fraud-detector-api`

The SQS message body is a JSON object consumed by `TransactionEvent` (`src/shared/models/transaction_event.py`):

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
