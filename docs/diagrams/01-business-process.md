# 01 — Business process (As-Is / To-Be)

repo นี้เป็น **contract-only scaffold** ของ capability `ai` (LLM gateway, model routing, budget, prompt policy, RAG) ไม่มี runtime, ไม่มี provider integration, ไม่มี database writer (README "Scope", `contract.json` `status: scaffolded`) งานจริงที่ repo นี้ทำคือ "เขียนและตรวจ contract + เก็บหลักฐาน parity" ส่วนการให้บริการ AI จริงอยู่ที่ `bookchaowalit/platform-ai-gateway-api` (`contract.json` `current_implementation`)

## As-Is (จาก code วันนี้)

```mermaid
flowchart TD
  A["Owner or agent changes the ai boundary"] --> B["Edit contract.json / docs / fixture"]
  B --> C["bash scripts/check.sh (local)"]
  C --> C1["check.py: contract vs vendored schema, README and CONTRACT-SURFACE agreement"]
  C --> C2["check_schema_pin.py: schema sha256 vs pin"]
  C --> C3["unittest: contract, drift, parity fixture and oracle"]
  C1 & C2 & C3 --> D{"All green?"}
  D -->|"no"| B
  D -->|"yes"| E["Push or open PR on GitHub"]
  E --> F["Check workflow: contract job, gateway-parity job, security job"]
  F --> G{"CI green?"}
  G -->|"no"| B
  G -->|"yes"| H["main updated (no deploy step)"]
  H --> I["Evidence recorded: docs/gates/BOO-145, owner decision"]
  L["Optional, local only: check_registry_alignment.py vs solo-empire registry"] -.-> B
  M["Optional, local only: ai_parity.py --solo-empire (agent routing and redaction)"] -.-> I
```

Sources: `README.md`, `PRODUCT.md`, `contract.json`, `scripts/check.sh`, `scripts/check.py`, `scripts/check_schema_pin.py`, `scripts/check_registry_alignment.py`, `scripts/ai_parity.py`, `.github/workflows/check.yml`, `docs/gates/BOO-145-provider-neutral-parity.md`

## Serving process ที่ boundary นี้ "ครอบ" (ทำงานที่ repo อื่น)

ภาพนี้คือ process ที่ contract บรรยายไว้ ไม่ได้รันใน repo นี้ (interfaces ทั้งหมด `status: current-in-solo-empire`)

```mermaid
flowchart LR
  APP["Calling app or agent"] -->|"POST /api/ai/generate, scope ai:generate"| GW["Current gateway (platform-ai-gateway-api)"]
  GW --> V{"Validate request, privacy_class"}
  V -->|"private / restricted"| X403["403 hosted generation disabled"]
  V -->|"ok"| BG{"Monthly budget guard"}
  BG -->|"deny"| X429["429 budget_exceeded, no provider call"]
  BG -->|"allow"| P["OpenAI-compatible provider"]
  P -->|"429 / 5xx / timeout"| FB["One fallback model attempt"]
  P --> T["ai_run_telemetry row (no prompt or response)"]
  FB --> T
  T --> R["AiGenerateResponse, output_trust untrusted_model_output"]
```

Sources: `docs/CONTRACT-SURFACE.md` (Behaviour notes), `docs/gates/BOO-145-provider-neutral-parity.md` (Routing / Budget / Redaction inventory)

## To-Be (จากเอกสารใน repo เท่านั้น)

```mermaid
flowchart LR
  S0["Now: scaffolded, shadow_parity pending, cutover pending"] --> S1["P0: request/response schemas + sanitized fixtures (400, 403, 429, 504)"]
  S1 --> S2["P1: fixtures for duplicate delivery, timeout, provider failure; registry source_paths fixed"]
  S2 --> S3["Resolve or accept gaps G-1, G-2, G-4 (open item 3)"]
  S3 --> S4["Shadow traffic must reproduce the parity baseline"]
  S4 --> S5["Cutover only with owner approval + rollback rehearsal"]
  S5 --> S6["P2: health endpoint and rollback instructions once a runtime exists"]
```

Sources: `docs/UPGRADE-PLAN.md` (Backlog P0–P2), `docs/gates/BOO-145-provider-neutral-parity.md` ("Owner decision", "Still open"), `README.md` ("Migration gate"), `contract.json` (`migration`)

หมายเหตุ: ops record: book-platforms-status (2026-11-03) บันทึกทางเลือกอื่นที่แนะนำ (ให้ gateway กลายเป็น ai service แล้ว archive scaffold นี้) แต่ยังเป็น **owner decision ที่เปิดอยู่** จึงไม่วาดเป็น To-Be

## Open questions

- เกณฑ์ cutover สำหรับเปิด runtime (`PRODUCT.md` Measures: "[ต้องยืนยัน]")
- จะย้าย implementation มาที่ repo นี้ หรือให้ `platform-ai-gateway-api` เป็น ai service แล้ว archive scaffold (ops record: book-platforms-status (2026-11-03), owner decision เปิดอยู่)
- RAG และ prompt policy อยู่ใน `capabilities` แต่ไม่มี interface ใดใน `contract.json` ครอบไว้ จะนิยามเมื่อไร
