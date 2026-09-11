---
applyTo: "**/*.py"
---

# Python / AWS Lambda Best Practices

Applies to all code in this repository. Written in English — this is the primary language for code, comments, docstrings, commit messages, and identifiers in this project, regardless of the language used in conversation with the agent.

## Language & style

- All code, comments, docstrings, variable/function names, log messages, and commit messages: **English**.
- Follow PEP 8. Use type hints on every function signature (parameters and return type).
- Prefer explicit over clever. Fraud rules and Lambda handlers are read far more often than written — optimize for the next reader.
- Use `black` / `ruff` (or whatever formatter/linter is in `requirements-dev.txt`) before committing; don't hand-format.

## Lambda handler design

- `main.py`'s handler should stay thin: parse event → delegate to domain code (`rules/`, `repository/`, `notifications/`) → return. No business logic inline in the handler.
- One Lambda invocation = one SQS message. Never assume batch size unless the trigger is explicitly configured for batching, and if it is, handle partial batch failures correctly (return `batchItemFailures`, don't let one bad record fail the whole batch).
- Fail loudly on malformed input (bad SQS message shape) — log the error with enough context to debug, then let it go to the DLQ rather than swallowing it silently.
- Keep cold start light: avoid heavy imports or client initialization inside the handler function body — initialize AWS clients (boto3, etc.) at module level so they're reused across warm invocations.

## AWS SDK (boto3) usage

- Reuse boto3 clients/resources across invocations (module-level, not per-call).
- Never hardcode region, table names, queue URLs, or ARNs — read from environment variables via `config.py`.
- Wrap AWS calls with explicit error handling for the exceptions that matter (e.g. `ClientError`, throttling) rather than a bare `except Exception`.
- Use DynamoDB conditional expressions instead of read-then-write when checking existence/uniqueness, to avoid race conditions.

## Rules engine (Strategy Pattern)

- Every class in `rules/` must be pure: no AWS SDK calls, no I/O. Input is the transaction event + whatever history data `repository/` already fetched; output is a contribution to `analysis_result`.
- New rules go through `rules/base.py`'s interface and get registered in `rules/engine.py` — never add conditional branches for a new rule type inside `main.py` or `engine.py`.

## Testing

- Every new rule or repository method needs a test in `tests/`.
- Mock AWS calls (e.g. with `moto` or manual stubs) — tests must not hit real AWS or LocalStack by default.
- Test names and assertions in English, describing behavior (`test_velocity_rule_flags_more_than_five_transactions_per_minute`), not implementation details.

## Logging & observability

- Use structured logging (key-value or JSON), not free-form string concatenation — this matters for CloudWatch Insights queries later.
- Always log the `transactionId` (and `userId` when relevant) so a single transaction can be traced across log lines.
- Never log full transaction payloads with sensitive data at INFO level; keep PII out of logs.

## Dependencies

- Keep `requirements.txt` limited to what actually ships in the deployed Lambda package. Dev/test-only tools go in `requirements-dev.txt`.
- Pin versions in `requirements.txt` to keep Lambda builds reproducible.