# ADR-0001 — Boundary เป็น contract-only scaffold ไม่มี runtime

- Status: accepted (retro-documented)
- Date: retro-documented 2026-11-03 (decision visible since `8d72509`, 2026-09-17)

## Context

capability `ai` (LLM gateway, routing, budget, prompt policy, RAG) ให้บริการอยู่แล้วโดย implementation อื่น การย้ายออกจาก control plane ต้องไม่ทำให้ consumer รู้สึกถึงการเปลี่ยน

## Decision

repo นี้ถือเฉพาะ contract ที่ตรวจได้ (`contract.json`, `status: scaffolded`) ไม่มี provider integration, database writer, credential หรือ customer payload; serving อยู่ที่ `platform-ai-gateway-api` จนกว่าจะมี parity + rollback evidence และ owner อนุมัติ cutover

## Evidence

- `README.md` "Scope": "This checkout is a local scaffold; it contains no production provider integration, database writer, credential, or customer payload."
- `contract.json`: `status: scaffolded`, `migration.cutover: pending`, `current_implementation.repository: platform-ai-gateway-api`
- `scripts/check.py`: `ALLOWED_STATUS = frozenset({"scaffolded"})`
- `PRODUCT.md` "Positioning": "A boundary contract with offline evidence, not a running service."
- `docs/gates/BOO-145-provider-neutral-parity.md`: owner decision 2026-10-16 "accept parity evidence; no cutover"

## Consequences

- ไม่มี deploy, Sentry, backup ใน repo นี้ (`PRODUCT.md`: "Sentry does not apply")
- การเปลี่ยน status เป็นอย่างอื่นต้องแก้ `ALLOWED_STATUS` ก่อน ซึ่ง check จะ fail โดยตั้งใจ
