# 11 — State machines

entity ที่มี status/lifecycle ใน repo: `contract.status` (enum ใน schema), `migration.*`, `owner_decision` ใน fixture และ `status` ของ `AiGenerateResponse` (compatibility surface)

## A. Contract lifecycle (`status`)

```mermaid
stateDiagram-v2
  [*] --> scaffolded
  scaffolded --> pilot : "not allowed here yet (ALLOWED_STATUS)"
  pilot --> active
  active --> retired
  scaffolded --> retired
  note right of scaffolded
    Current state. check.py allows only scaffolded,
    so any transition needs a code change first.
  end note
```

Sources: `schema/book-platform.contract.v1.schema.json` (`status.enum`: scaffolded, pilot, active, retired), `scripts/check.py` (`ALLOWED_STATUS`), `contract.json`. การเปลี่ยนจาก state ใดไป state ใดเป็นได้บ้าง schema **ไม่ได้กำหนด** ลูกศรนอกจาก scaffolded คือลำดับตามชื่อ enum เท่านั้น

## B. Migration progression (`migration` + gate doc)

```mermaid
stateDiagram-v2
  [*] --> ParityPending
  ParityPending --> ParityEvidenceAccepted : "BOO-145 owner decision 2026-10-16"
  ParityEvidenceAccepted --> ShadowParity : "after G-1, G-2, G-4 resolved or accepted"
  ShadowParity --> CutoverApproved : "owner approval + rollback rehearsal"
  CutoverApproved --> [*]
  note right of ParityEvidenceAccepted
    Current: shadow_parity pending, cutover pending,
    cutover_approved false in the fixture.
  end note
```

Sources: `contract.json` (`migration`), `fixtures/gates/provider-neutral-parity.json` (`owner_decision.cutover_approved`), `docs/gates/BOO-145-provider-neutral-parity.md`, `README.md` "Migration gate"

## C. Generate run outcome (compatibility surface)

```mermaid
stateDiagram-v2
  [*] --> Validating
  Validating --> Rejected400 : "validation error"
  Validating --> Blocked403 : "privacy_class private or restricted"
  Validating --> BudgetCheck
  BudgetCheck --> BudgetDenied429 : "deny reason, cost 0"
  BudgetCheck --> NotConfigured503 : "no provider or budget guard"
  BudgetCheck --> Calling
  Calling --> Fallback : "429, 5xx, timeout, network error"
  Fallback --> Success
  Fallback --> ProviderFailed : "502 or 504"
  Calling --> Success
  Calling --> ProviderFailed
  Success --> BudgetExceededPostHoc : "usage above token_budget, 200"
  Success --> [*]
  BudgetExceededPostHoc --> [*]
  ProviderFailed --> [*]
```

Sources: `docs/CONTRACT-SURFACE.md` (Errors, Response `status`), `docs/gates/BOO-145-provider-neutral-parity.md` (fail-closed table), `fixtures/gates/provider-neutral-parity.json` (`GW-*` expectations, `routing.gateway.fallback_retryable`, `fallback_attempts_max: 1`)

## Open questions

- transition ที่อนุญาตของ `status` (pilot/active/retired) ยังไม่มีกฎใน schema หรือเอกสาร
