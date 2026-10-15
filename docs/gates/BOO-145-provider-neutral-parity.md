# BOO-145: provider-neutral parity gate (`ai`)

- Issue: BOO-145. System: `ai` (`repository-catalog/registries/system-repositories.yaml`, solo-empire `63efeeb`, lines 530-553)
- Status: evidence recorded. The owner decision is **proposed, not accepted**. Nothing in this document approves a hosted cutover, a runtime move or a status change.
- Fixture: [`fixtures/gates/provider-neutral-parity.json`](../../fixtures/gates/provider-neutral-parity.json)
- Check: [`scripts/ai_parity.py`](../../scripts/ai_parity.py), tests in [`tests/test_ai_parity.py`](../../tests/test_ai_parity.py), gateway harness [`scripts/ai_parity_gateway_harness.mjs`](../../scripts/ai_parity_gateway_harness.mjs)

## Next gate (verbatim)

> Capture provider-neutral routing, budget, redaction, and evaluation parity before any hosted cutover.

## Contract answered

`bookchaowalit/architecture-docs` @ `9471af5` (origin/main), `systems/ai-data/central-ai-gateway.md`:

| Gate part | Contract section |
|---|---|
| Routing | [`#service-lanes`](https://github.com/bookchaowalit/architecture-docs/blob/9471af55723434fd34c746ad66fa1d4f5ebf6578/systems/ai-data/central-ai-gateway.md#service-lanes) (L18-46), `#provider-presets` (L99-146) |
| Budget | `#contract` (L66-72), `#monthly-budget-guard` (L148-200), `#hosted-service` (L202-214) |
| Redaction | `#contract` (L81-84), `#provider-boundary` (L86-97), `#observability-and-rollout` (L216-222) |
| Evaluation | `#observability-and-rollout` (L233-236) and `systems/ai-data/ai-api-evaluation-plan.md` L25-38 (`ai-api-control-plane-eval-v1`) |

## What "current" means here

The registry entry still lists `source_paths: [systems/ai-data, skills/ai-agents]`; those folders have moved out of the hub
(`systems/ai-data` is in architecture-docs, `skills/ai-agents` in platform-agent-skills and holds only guidance, no routing
or redaction code). The executable current side is:

| Side | Repository @ commit (origin/main) | Files |
|---|---|---|
| Hosted gateway (`api` lane) | `bookchaowalit/platform-ai-gateway-api` @ `723d752` | `api/ai_gateway.ts`, `api/ai_budget.ts`, `api/ai-gateway-service/service.ts`, `database/migrations/025_ai_run_telemetry.sql` |
| Agent routing / context redaction | `bookchaowalit/solo-empire` @ `63efeeb` | `infra/scripts/agent/model_routing.py`, `infra/scripts/agent/context_pack.py` |
| Evaluation plan | `bookchaowalit/architecture-docs` @ `9471af5` | `systems/ai-data/ai-api-evaluation-plan.md` |

The fixture pins the sha256 of every file above; `scripts/ai_parity.py` warns when one changes. The gateway is AGPL-3.0 and
this repository is Apache-2.0, so no gateway code is copied here: the check reads a local checkout instead.

## Routing inventory

Provider-neutral task-class routing (`model_routing.py`):

| Task class (workload / signal) | Requested profile | Lane | Source |
|---|---|---|---|
| `interactive` | `subscription` | subscription | `model_routing.py:112-113` |
| `batch`, `multimodal`, `embedding`, `speech`, `vision`, `tts`, `reranking`, `detection`, `segmentation`, `music`, `image_generation`, `video_generation` | `gpu_worker` | runpod | `model_routing.py:114-118` |
| `agent`/`coding`/`reasoning` with explicit `quality` | that profile | api | `model_routing.py:119-120` |
| quality term (`accuracy`, `quality`, `reasoning`, `deep`, `คุณภาพ`, `แม่น`, `วิเคราะห์ลึก`) or `token_budget > 6000` | `quality` | api | `model_routing.py:121-124` |
| `latency_target_ms <= 1000`, `operation == inspect`, route `health`/`documentation` | `fast` | api | `model_routing.py:125-128` |
| otherwise | `balanced` | api | `model_routing.py:129` |
| `private`/`restricted` data | api/subscription/runpod candidates `excluded` | local | `model_routing.py:132-137` |
| fallback | explicit lanes → `local_reference`; text → requested, `balanced`, `fast`, `local_reference` | | `model_routing.py:209-233` |

Provider-neutral model aliases: `fast-slot`, `balanced-slot`, `quality-slot` (adapter `external`), `solo-empire-local-reference`,
`ai-worker` (runpod) and `gpt-5.6-luna-subscription` (`model_routing.py:73-93`; see G-3).

Gateway profile slots (`ai_gateway.ts`): the provider is always `openai-compatible` (`:274-278`); `AI_GATEWAY_PROVIDER_NAME`
labels telemetry and switching vendor is a configuration change (contract `#provider-presets`). Each profile resolves only
through env aliases (`:289-297`, `:220-227`):

| Profile | Model env | Fallback env | Default output tokens (`:162-166`) |
|---|---|---|---|
| `fast` | `AI_GATEWAY_MODEL_FAST` → `AI_GATEWAY_MODEL` | `AI_GATEWAY_FALLBACK_MODEL_FAST` → `AI_GATEWAY_FALLBACK_MODEL` | 512 |
| `balanced` (default) | `AI_GATEWAY_MODEL_BALANCED` → `AI_GATEWAY_MODEL` | `AI_GATEWAY_FALLBACK_MODEL_BALANCED` → `AI_GATEWAY_FALLBACK_MODEL` | 1024 |
| `quality` | `AI_GATEWAY_MODEL_QUALITY` → `AI_GATEWAY_MODEL` | `AI_GATEWAY_FALLBACK_MODEL_QUALITY` → `AI_GATEWAY_FALLBACK_MODEL` | 2048 |

One fallback attempt on 429, 5xx, timeout or network error (`:536-537`, `:669-685`). The Thai response-language policy is
prepended at the provider boundary (`:172-180`, `:444`).

## Budget inventory

| Limit | Default | Bounds | Source |
|---|---|---|---|
| `AI_GATEWAY_DEFAULT_TOKEN_BUDGET` | 4096 | 256-32768 | `ai_gateway.ts:207-211` |
| `AI_GATEWAY_MAX_TOKEN_BUDGET` | = default budget | 256-131072 | `ai_gateway.ts:209` |
| `AI_GATEWAY_MAX_OUTPUT_TOKENS` | 4096 | 128-16384 | `ai_gateway.ts:323` |
| `AI_GATEWAY_MAX_CONTEXT_CHARS` | 48000 | 1024-200000 | `ai_gateway.ts:322` |
| `AI_GATEWAY_TIMEOUT_MS` / `_REASONING_TIMEOUT_MS` | 30000 | 1000-120000 | `ai_gateway.ts:325-332` |
| Rate cards `AI_GATEWAY_INPUT/OUTPUT_USD_PER_1K` | required | ≥ 0 | `ai_gateway.ts:299-303` |

Fail-closed behaviour:

| Condition | Result | Source |
|---|---|---|
| Monthly cap would be exceeded, unknown provider cost, overdue GPU session, commitments over budget, invalid config | HTTP 429 before the provider call; telemetry `budget_exceeded`, cost 0 | `ai_budget.ts:273-283,303-322`; `ai_gateway.ts:641-650` |
| Hosted service without a monthly budget | 503 `budget_not_configured` | `service.ts:197,266-269` |
| Budget guard cannot be built | 503 `budget_unavailable` | `service.ts:270-279` |
| No provider configured | 503 `not_configured` | `ai_gateway.ts:620-629` |
| Provider usage above `token_budget` | 200 with `status: budget_exceeded`, actual cost recorded | `ai_gateway.ts:704` |
| Error cost policy `unknown` (default) | NULL cost, so the guard denies (`unmetered_api_events`) until reconciled | `ai_gateway.ts:246-254`; `ai_budget.ts:105-122` |

The 18 budget reasons are classified in the fixture (`allow` is only `within_budget`).

## Redaction inventory

| ID | Rule | Enforced by | Source | Parity evidence |
|---|---|---|---|---|
| RD-1 | Telemetry rows are scalar run metadata only | gateway | `ai_gateway.ts:48-63,499-516,705-729`; migration `025` L1-17 | GW-REDACT-SUCCESS, GW-REDACT-PROVIDER-ERROR |
| RD-2 | Provider error bodies are drained, never returned or logged | gateway | `ai_gateway.ts:576-590` | GW-REDACT-PROVIDER-ERROR, GW-RATE-LIMITED |
| RD-3 | Provider URL with credentials/query refused; status shows booleans only | gateway | `ai_gateway.ts:257-272,346-403` | GW-STATUS-NO-KEY, GW-URL-CREDENTIALS |
| RD-4 | `private`/`restricted` fail closed before any hosted call | gateway + routing | `ai_gateway.ts:423-427`; `model_routing.py:132-137` | GW-PRIVACY-*, RT-08, RT-13 |
| RD-5 | One content-free log line with a fixed key set | gateway | `service.ts:200-222` | static key extraction |
| RD-6 | Credential `key=value`, bearer tokens and PEM redacted from agent context | routing | `context_pack.py:33-37,70-93` | RX-01..04, RX-06, RX-07 |
| RD-7 | Routing plans fingerprint the task; raw prompt persistence forbidden | routing | `model_routing.py:96-99,236,257-261` | RT-* (no task echo) |
| RD-8 | Secrets/PII inside messages are **not** scrubbed before the hosted provider | none | `ai_gateway.ts:432-444,552` | GW-REDACT-SUCCESS (`provider_received_canary: true`), RX-05 |

## Evaluation parity

All 10 scenarios of `ai-api-control-plane-eval-v1` are mapped in the fixture. Eight are re-exercised against the real current
code with synthetic canaries; two (missing auth, rate/concurrency limit) are covered only by the gateway's own tests (G-8).

Local run (2026-10-15), current code at the commits above:

```text
python3 scripts/ai_parity.py --gateway-root <platform-ai-gateway-api@723d752> --solo-empire <solo-empire@63efeeb>
ai parity: OK (fixture, oracle, gateway-source, gateway-cases, agent-routing; 0 error(s), 0 warning(s))
```

- 15 gateway cases (real `generateAi`/`getAiGatewayStatus`/`createAiBudgetGuard` against a loopback mock provider), 14 routing
  cases (real `build_routing_plan`) and 8 redaction cases (real `redact_text`) match the fixture.
- No synthetic secret, email, phone or provider-error body reaches telemetry, errors or status output.
- Budget denials make zero provider calls and record cost 0.

The gateway's draft PR #1 (`codex/shared-infrastructure-20261015`, shared workspace AI admission) changes `ai_gateway.ts`
and `service.ts`. The same check run against that branch reports pin warnings only, with no behavioural drift. This
repository has no PR #1.

## Gaps

| ID | Area | Gap |
|---|---|---|
| G-1 | routing | Per-profile output caps disagree: routing plans 1000/3000/6000, the gateway defaults to 512/1024/2048 (max 4096). |
| G-2 | budget | Routing defaults `token_budget` to 6000 and escalates to `quality` above 6000; the gateway rejects anything above `AI_GATEWAY_MAX_TOKEN_BUDGET` (default 4096) with 400 (GW-TOKEN-BUDGET-CEILING). |
| G-3 | routing | The subscription slot names a vendor model (`gpt-5.6-luna-subscription`) rather than a neutral alias. |
| G-4 | redaction | No content redaction before the hosted provider (RD-8). Context-pack redaction misses PII and bare `token:` values (RX-05, RX-08). |
| G-5 | budget | Guard and limiter are process-local (single replica). The in-process gateway enforces a budget only when `LLM_LAB_MONTHLY_BUDGET_USD` is set. |
| G-6 | evaluation | Provider quality, p50/p95 latency and rate-card reconciliation are unevaluated; the plan's recommendation is `restrict`. |
| G-7 | routing | GPU volume routing (`gpu_worker_policy`, platform-ops-cli) is not captured; cases use `volume_units=None`. |
| G-8 | evaluation | Missing-auth and rate/concurrency scenarios are not re-run by this harness. |

## Owner decision — PROPOSED, NOT ACCEPTED

Proposed for the `ai` system owner. It is not accepted until the owner records acceptance in the parent registry.

1. Accept `fixtures/gates/provider-neutral-parity.json` as the parity baseline: any `platform-ai` runtime must reproduce
   its routing aliases, budget fail-closed table, redaction rules RD-1 to RD-7 and evaluation cases before shadow traffic.
2. Keep `platform-ai` at `status: scaffolded`, `shadow_parity: pending`, `cutover: pending`. The hosted gateway
   (`platform-ai-gateway-api`) stays the only serving implementation.
3. Before any hosted cutover, resolve or explicitly accept G-1, G-2 and G-4. Proposed resolution: the gateway's per-profile
   caps become canonical (512/1024/2048, budget ceiling 4096), routing plans clamp to them, and the content policy
   (RD-8) is either "caller-declared privacy class only" (accepted risk) or a pre-provider scrubber with its own cases.
4. Update the registry `source_paths` for `ai` so they name the gateway repository and the routing scripts.

## Not done

- No owner decision, registry update, status change, runtime move, deployment or provider call.
- G-1 to G-8 are recorded, not fixed.
- The source parity tests run only locally (`PLATFORM_AI_PARITY_GATEWAY`, `PLATFORM_AI_PARITY_SOLO_EMPIRE`). CI runs the
  offline fixture, oracle, extractor and document tests.

## Re-run

```bash
bash scripts/check.sh                                   # offline (CI)
(cd <platform-ai-gateway-api> && npm ci)                # once, provides tsx
PLATFORM_AI_PARITY_GATEWAY=<platform-ai-gateway-api> \
PLATFORM_AI_PARITY_SOLO_EMPIRE=<solo-empire> \
  python3 -m unittest tests.test_ai_parity -v           # local parity against current code
```
