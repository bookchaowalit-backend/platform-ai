# 10 — Sequences

สาม path ที่สำคัญที่สุดของ repo นี้ (CI parity gate, harness case, local check) และหนึ่ง path ของ compatibility surface ที่ gateway ให้บริการ

## A. CI job `gateway-parity`

```mermaid
sequenceDiagram
  participant GH as GitHub Actions
  participant R as platform-ai checkout
  participant G as _gateway checkout (platform-ai-gateway-api)
  participant P as ai_parity.py
  participant H as harness (tsx)
  GH->>R: actions/checkout@v4
  GH->>G: checkout ref GATEWAY_COMMIT, persist-credentials false
  GH->>R: python3 -c compare fixture sources.gateway.commit to GATEWAY_COMMIT
  alt pins differ
    R-->>GH: exit non-zero, job fails
  end
  GH->>G: npm ci --ignore-scripts --no-audit --no-fund
  GH->>R: bash scripts/check.sh (REQUIRE_GATEWAY_PARITY=1)
  GH->>P: ai_parity.py --gateway-root _gateway
  P->>P: validate_fixture, check_oracle
  P->>G: read pinned files, extract facts, sha256 compare
  P->>H: spawn tsx harness with PATH and HOME only
  H->>G: import api/ai_gateway.ts and api/ai_budget.ts
  H-->>P: observed outcomes JSON (last stdout line)
  P->>P: compare_gateway_cases, canary leak check
  P-->>GH: "ai parity: OK" or FAIL with errors
```

Sources: `.github/workflows/check.yml`, `scripts/ai_parity.py` (`run`, `run_gateway_cases`, `compare_gateway_cases`), `tests/test_ai_parity.py` (`CurrentGatewayParityTests`)

## B. One harness case (e.g. GW-FALLBACK)

```mermaid
sequenceDiagram
  participant H as harness
  participant GW as generateAi (gateway module)
  participant M as mock provider 127.0.0.1
  H->>H: mode = http_503_then_ok, synthetic key, baseEnv
  H->>GW: generate request with synthetic messages
  GW->>M: POST chat completion (primary model)
  M-->>GW: 503 with canary error body
  GW->>M: POST chat completion (fallback model)
  M-->>GW: 200 synthetic answer, usage
  GW-->>H: success, fallback_used true, 2 telemetry rows
  H->>H: record provider_calls, telemetry fields, canary presence
```

Sources: `scripts/ai_parity_gateway_harness.mjs` (mock provider modes), `fixtures/gates/provider-neutral-parity.json` (`GW-FALLBACK` expect: `provider_calls: 2`, `telemetry_rows: 2`)

## C. Local `bash scripts/check.sh`

```mermaid
sequenceDiagram
  participant D as Developer
  participant C as check.py
  participant S as check_schema_pin.py
  participant U as unittest discover
  D->>C: python3 scripts/check.py
  C->>C: required files, schema validate, semantic rules
  C-->>D: "OK: platform-ai (ai) scaffolded contract, 6 documented interface(s)"
  D->>S: python3 scripts/check_schema_pin.py
  S-->>D: OK or drift
  D->>U: python3 -m unittest discover -s tests -v
  U-->>D: results (gateway / solo-empire tests skip unless env set)
```

Sources: `scripts/check.sh`, `scripts/check.py` (`main`), `tests/test_ai_parity.py` (skip conditions)

## D. Compatibility surface: `POST /api/ai/generate` (served by the current gateway)

```mermaid
sequenceDiagram
  participant A as Caller (scope ai:generate)
  participant GW as Current gateway
  participant B as Budget guard
  participant P as OpenAI-compatible provider
  participant T as ai_run_telemetry
  A->>GW: POST /api/ai/generate (route, prompt_version, messages, profile, privacy_class)
  GW->>GW: validate (400 on error)
  alt privacy_class private or restricted
    GW-->>A: 403, no provider call
  end
  GW->>B: reserve against monthly cap
  alt deny
    B-->>GW: budget reason
    GW->>T: status budget_exceeded, cost 0
    GW-->>A: 429
  end
  GW->>P: chat completion with Thai response-language policy prepended
  P-->>GW: content and usage (or 429/5xx/timeout then one fallback)
  GW->>T: upsert on run_id (no prompt, no response)
  GW-->>A: AiGenerateResponse, output_trust untrusted_model_output
```

Sources: `docs/CONTRACT-SURFACE.md` "Behaviour notes", `docs/gates/BOO-145-provider-neutral-parity.md` (Budget fail-closed table, Routing inventory, RD-1..RD-4)

## Open questions

- ลำดับจริงระหว่าง rate limiter กับ budget guard ใน gateway ไม่ได้ระบุใน repo นี้ (CONTRACT-SURFACE ระบุเพียงว่ามี 429/503 จาก rate limiter)
