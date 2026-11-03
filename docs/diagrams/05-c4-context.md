# 05 — C4 Context

System ในภาพคือ repo `platform-ai` (contract + evidence) ไม่ใช่ service ที่รันอยู่ ความสัมพันธ์ทั้งหมดเป็น build-time/check-time ยกเว้นเส้นประที่แสดง serving path ของ gateway ปัจจุบัน (ไม่ผ่าน repo นี้)

```mermaid
C4Context
  title platform-ai — system context (contract-only boundary)
  Person(owner, "Owner / AI agent", "Maintains the ai boundary contract")
  System(pai, "platform-ai", "Contract, vendored schema, parity fixture, offline checks")
  System_Ext(gh, "GitHub Actions", "Check workflow on push / PR / dispatch")
  System_Ext(ciwf, "platform-ci-workflows", "Reusable ci-python and security workflows @87dc5e1")
  System_Ext(gw, "platform-ai-gateway-api", "Current serving implementation, public, pinned @723d752")
  System_Ext(solo, "solo-empire", "Private control plane: platform registry, model_routing.py, context_pack.py")
  System_Ext(core, "platform-backend-core", "Canonical contract schema in contracts/")
  System_Ext(arch, "architecture-docs", "central-ai-gateway.md and ai-api-evaluation-plan.md @9471af5")
  System_Ext(prov, "OpenAI-compatible provider", "Called by the gateway only")

  Rel(owner, pai, "edits, runs scripts/check.sh")
  Rel(gh, pai, "runs contract, gateway-parity, security jobs")
  Rel(gh, ciwf, "calls reusable workflows")
  Rel(gh, gw, "checks out at pinned commit, runs 15 cases")
  Rel(owner, solo, "local only: registry alignment, routing parity")
  Rel(pai, core, "pins schema sha256")
  Rel(pai, arch, "fixture pins doc sha256")
  Rel(gw, prov, "chat completions (serving path, not via this repo)")
```

Sources: `contract.json`, `README.md`, `.github/workflows/check.yml`, `fixtures/gates/provider-neutral-parity.json` (`sources`), `scripts/check_schema_pin.py`, `scripts/check_registry_alignment.py`, `docs/gates/BOO-145-provider-neutral-parity.md`

ขอบเขต dependency ที่ contract ประกาศ (`depends_on`: `identity`, `data`, `security`, `observability`) เป็นเป้าหมายของ runtime ในอนาคต ยังไม่มีการเรียกจริงจาก repo นี้ จึงไม่วาดเป็น Rel

## Open questions

- เมื่อมี runtime จะเรียก `data` และ `observability` ผ่าน interface ใด (ไม่มี interface `consumes` ของสอง platform นี้ใน `contract.json`)
