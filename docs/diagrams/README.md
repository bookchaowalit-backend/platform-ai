# Core 22 SDLC diagram pack — platform-ai

ชุด diagram 22 รายการตาม SDLC Diagram Catalog v2 (knowledge-base `knowledge/tech/core-cs/sdlc-diagram-catalog.md`) วาดจาก code / config ของ repo นี้ที่ `origin/main` `ac5b526` (2026-11-03)

repo นี้เป็น **contract-only scaffold** ของ platform `ai` (`contract.json` `status: scaffolded`): มี contract, vendored schema, parity fixture และ offline checks เท่านั้น ไม่มี runtime, database, deploy หรือ instrumentation ส่วน serving จริงอยู่ที่ `bookchaowalit/platform-ai-gateway-api` (current implementation) ภาพของ API ที่ให้บริการจึงวาดในฐานะ "compatibility surface" ตาม `docs/CONTRACT-SURFACE.md` และ gate doc BOO-145 ทุก diagram มี `Sources:` และ "Open questions" แยกไว้ hosting facts ที่ไม่อยู่ใน repo อ้าง `ops record: book-platforms-status (2026-11-03)`

| # | Item | Status | File | Sources read |
|---|---|---|---|---|
| 01 | Business process (As-Is / To-Be) | done | [01-business-process.md](01-business-process.md) | README.md, PRODUCT.md, contract.json, check.sh, check.yml, UPGRADE-PLAN.md, gates/BOO-145 |
| 02 | Use cases | done | [02-use-cases.md](02-use-cases.md) | scripts/*, check.yml, contract.json interfaces auth |
| 03 | User flows (maintainer flows; no UI) | done | [03-user-flows.md](03-user-flows.md) | README.md, check.py, check_schema_pin.py, check_registry_alignment.py, BOO-145 "Re-run" |
| 04 | Traceability (RTM) | done | [04-traceability.md](04-traceability.md) | PRODUCT.md, README.md, contract.json, UPGRADE-PLAN.md, scripts/, tests/, check.yml |
| 05 | C4 Context | done | [05-c4-context.md](05-c4-context.md) | contract.json, check.yml, fixture `sources`, README.md |
| 06 | C4 Container | done | [06-c4-container.md](06-c4-container.md) | repo tree, check.yml, ci-workflows @87dc5e1 |
| 07 | C4 Component | done | [07-c4-component.md](07-c4-component.md) | check.py, ai_parity.py, harness |
| 08 | ADRs (4) | done | [08-adr/](08-adr/) | README.md, PRODUCT.md, contract.json, check.py, check_schema_pin.py, check.yml, LICENSE, git log |
| 09 | ERD | done (document model + compatibility table) | [09-erd.md](09-erd.md) | contract.json, contract schema, fixture `redaction.telemetry_columns` |
| 10 | Sequences | done | [10-sequences.md](10-sequences.md) | check.yml, ai_parity.py, harness, CONTRACT-SURFACE.md, BOO-145 |
| 11 | State machines | done | [11-state-machines.md](11-state-machines.md) | schema `status.enum`, check.py, contract.json `migration`, fixture, CONTRACT-SURFACE.md |
| 12 | API and integrations | reused + extended | [12-api-integration.md](12-api-integration.md) → [`docs/CONTRACT-SURFACE.md`](../CONTRACT-SURFACE.md) | contract.json, CONTRACT-SURFACE.md, check.yml, scripts |
| 13 | Threat model (DFD + STRIDE) | done | [13-threat-model.md](13-threat-model.md) | check.yml, harness, ai_parity.py, security.yml, BOO-145, gh branch protection API |
| 14 | Backup / DR | not_applicable (no runtime data; Git only) | [14-backup-dr.md](14-backup-dr.md) | README.md, PRODUCT.md, fixture `sources`, central-ai-gateway.md |
| 15 | CI/CD pipeline | done (CI only, no CD) | [15-cicd-pipeline.md](15-cicd-pipeline.md) | check.yml, ci-workflows @87dc5e1 ci-python.yml / security.yml, gh run view |
| 16 | Deployment | not_applicable (no hosted runtime) | [16-deployment.md](16-deployment.md) | PRODUCT.md, README.md, DOCPACK card, central-ai-gateway.md, ops record |
| 17 | Test coverage matrix | done | [17-test-coverage-matrix.md](17-test-coverage-matrix.md) | tests/*.py, check.yml, BOO-145 |
| 18 | Git / release workflow | done | [18-git-release-workflow.md](18-git-release-workflow.md) | git log, gh pr list, gh run list, gh branch protection API |
| 19 | Service dependency map | done (check-time + declared) | [19-service-dependency-map.md](19-service-dependency-map.md) | contract.json, check.yml, scripts, fixture, ops record |
| 20 | Observability | done (CI signals only; runtime not_applicable) | [20-observability.md](20-observability.md) | PRODUCT.md, check.yml, scripts `main()`, security.yml, BOO-145 RD-5 |
| 21 | Incident response | not_applicable (no production runtime, no alert channel) | [21-incident-response.md](21-incident-response.md) | gh run list, gh run view --log-failed, git log |
| 22 | DORA | done (proxies; no deploys exist) | [22-dora.md](22-dora.md) | git log, gh pr list, gh run list |

## ADRs

- [ADR-0001](08-adr/ADR-0001-contract-only-boundary-no-runtime.md) Boundary เป็น contract-only scaffold ไม่มี runtime
- [ADR-0002](08-adr/ADR-0002-vendored-schema-with-sha256-pin.md) Vendor shared schema พร้อม sha256 pin
- [ADR-0003](08-adr/ADR-0003-parity-against-pinned-gateway-checkout.md) Parity กับ gateway จริงที่ commit ที่ pin โดยไม่ copy code
- [ADR-0004](08-adr/ADR-0004-stdlib-python-and-shared-ci.md) Python stdlib เท่านั้น + shared CI v1.1.1

## Related docs (reused, not copied)

- [`docs/CONTRACT-SURFACE.md`](../CONTRACT-SURFACE.md), [`docs/UPGRADE-PLAN.md`](../UPGRADE-PLAN.md), [`docs/gates/BOO-145-provider-neutral-parity.md`](../gates/BOO-145-provider-neutral-parity.md)
- Central: [central-ai-gateway.md](https://github.com/bookchaowalit/architecture-docs/blob/main/systems/ai-data/central-ai-gateway.md), [ai-api-evaluation-plan.md](https://github.com/bookchaowalit/architecture-docs/blob/main/systems/ai-data/ai-api-evaluation-plan.md)

## Drift found while drawing

- `docs/CONTRACT-SURFACE.md` ยังเขียน source status `current-implementation-in-solo-empire` และ path `infra/api/*.ts` ขณะที่ `contract.json` ชี้ไป `platform-ai-gateway-api` (`adjacent-domain-repository`)
- `DOCPACK/00-product-card.md` (2026-10-08) ยังบอก test 2 ไฟล์และ implementation ใน `solo-empire`; `docs/UPGRADE-PLAN.md` บอก "19 tests" (ปัจจุบัน 21 ใน `test_contract_check.py`)
