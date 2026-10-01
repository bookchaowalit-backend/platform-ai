# Contract surface: book-ai-platform

This page documents the API, event, CLI, storage and configuration surface that
`book-ai-platform` owns or consumes. The machine-readable list is `interfaces` in
[`contract.json`](../contract.json); `scripts/check.py` fails when an interface
listed there is missing from this page.

- Platform: `ai` (contract `book-platform.contract.v1`, API `v1`)
- Status: `scaffolded`; source status: `current-implementation-in-solo-empire`
- Current implementation: `solo-empire` at `infra/api/ai_gateway.ts`, `infra/api/ai_budget.ts`
- Depends on: `identity`, `data`, `security`, `observability`

Interfaces marked `current-in-solo-empire` are served by the `solo-empire`
control plane today. This repository does not serve them yet; they are the
compatibility surface a migration must preserve. The `source` column is a path
in the implementing repository.

## Interfaces

| ID | Kind | Direction | Interface | Contract | Auth | Source | Status |
|---|---|---|---|---|---|---|---|
| `ai.http.status` | http | provides | `GET /api/ai/status` | `solo-empire.ai-gateway.v1` | Bearer token with scope api:read | `infra/api/server.ts` | current-in-solo-empire |
| `ai.http.generate` | http | provides | `POST /api/ai/generate` | `solo-empire.ai-gateway.v1` | Bearer token with scope ai:generate | `infra/api/server.ts` | current-in-solo-empire |
| `ai.budget.status` | table | provides | Monthly LLM budget status (embedded in GET /api/ai/status) | `solo-empire.llm-lab-budget.v1` | - | `infra/api/ai_budget.ts` | current-in-solo-empire |
| `ai.event.run-telemetry` | event | provides | AI run telemetry row (ai_run_telemetry, upsert on run_id) | `solo-empire.ai-telemetry.v1` | - | `infra/api/ai_gateway.ts` | current-in-solo-empire |
| `ai.consumes.openai-compatible-provider` | http | consumes | OpenAI-compatible chat completion provider (HTTPS only, no URL credentials) | - | - | `infra/api/ai_gateway.ts` | current-in-solo-empire |
| `ai.consumes.identity-bearer` | http | consumes | Identity bearer-token check (`requireAuth`, scope `ai:generate`) | - | Bearer token with scope ai:generate | `infra/api/auth.ts` | current-in-solo-empire |

## Behaviour notes

Derived from the current source; re-check the source before changing a
consumer.

- `POST /api/ai/generate` request (`AiGenerateRequest`): `route` and `prompt_version`
  (safe identifiers, 1-64 chars of `[A-Za-z0-9_.:/-]`), `messages` (1-40 items,
  roles `system`/`user`/`assistant`, at least one `user`), optional `profile`
  (`fast`/`balanced`/`quality`), `privacy_class`
  (`public`/`internal`/`private`/`restricted`), `token_budget` (256..configured
  maximum), `max_output_tokens`, `temperature` (0..2) and `response_format`
  (`text` or `json_object`; `json_object` requires a message that asks for JSON).
- Response (`AiGenerateResponse`): `contract`, `run_id`, `status`
  (`success`/`budget_exceeded`), `route`, `prompt_version`, `provider`, `model`,
  `fallback_used`, `content`, `output_trust: "untrusted_model_output"`,
  `finish_reason`, `usage` (`source` = `provider`/`estimated`/`unavailable`),
  `token_budget`, `latency_ms`, `estimated_cost_usd`.
- Errors: 400 for validation, 403 when `privacy_class` is `private` or
  `restricted` (hosted generation disabled), 429/503 from the per-subject AI
  rate limiter (with `retry_after_seconds`), 503 when provider configuration or
  the budget guard is unavailable, 502/504 for provider failure or timeout.
- Responses default to Thai (`solo-empire.ai-response-language.th-v1`).
- Telemetry never contains prompt or response bodies; it records run id, route,
  prompt version, provider/model, token counts, budget, latency, cost estimate,
  cache hit and status.

## Migration gates

- provider-neutral parity
- redaction
- budget enforcement
- rollback adapter

## Out of scope

No production provider integration, credential, database writer or customer
payload lives in this repository. Record parity, privacy and rollback evidence
in the parent platform registry before any cutover.
