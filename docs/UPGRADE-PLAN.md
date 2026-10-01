# Upgrade plan: book-ai-platform

## Current state

Score: 6/10 (was 5/10 before pass 2). The vendored schema is now pinned
and drift-checked in CI, and the contract can be compared with the parent
registry locally. The boundary now has a precise, schema-validated
contract aligned with the parent registry, a documented contract surface, unit
tests for the check and CI; it still has no runtime implementation, fixtures or
parity evidence.

## Backlog

### P0

- Add `schema/ai-generate-request.v1.json` and `ai-generate-response.v1.json` mirroring `AiGenerateRequest`/`AiGenerateResponse` in `solo-empire/infra/api/ai_gateway.ts`, with sanitized fixtures for success, 400, 403 (private data), 429 and 504.
- Add a fixture-driven test that every fixture validates against those schemas (offline, no provider call).

### P1

- Replace the vendored schema and its pin with a reusable workflow or tagged
  package from `bookchaowalit-backend-core` once one exists.
- Ask the `solo-empire` owner to adopt the new schema and check in
  `infra/scaffolds/platform-repository` and to extend `platform_repository_guard.py`
  to compare `capabilities`, `depends_on` and `source_paths` with this contract
  (`scripts/check_registry_alignment.py` already does this locally).
- Add sanitized fixtures for success, duplicate delivery, timeout and provider
  failure (repository baseline in `systems/architecture/platform-repository-split.md`).

- Ask the registry owner whether `infra/api/server.ts` belongs in the `ai`
  `source_paths`: `ai.http.status` and `ai.http.generate` are routed there, and
  `scripts/check_registry_alignment.py` warns that they sit outside the
  registered paths. Change the registry first, then this contract.

### P2

- Add a health endpoint and rollback instructions once a runtime exists.

## Done in this pass (pass 2)

- `schema/book-platform.contract.v1.schema.json.sha256` pins the canonical
  schema digest; `scripts/check_schema_pin.py` fails on drift (and, with
  `--canonical`, compares with a local backend-core checkout). It runs in
  `scripts/check.sh` and as its own CI step.
- `scripts/check_registry_alignment.py --solo-empire PATH` compares the
  contract with `repository-catalog/registries/platforms.yaml` and warns on
  missing source paths (local, read-only; not in CI).
- `tests/test_drift_checks.py` covers both checks offline.
- Registry alignment verified read-only against `solo-empire` `5b43c85`: fields
  agree; the only finding is the `server.ts` routing warning (new P1 above).

## Done in pass 1

- `contract.json`: registry-aligned `capabilities`, `depends_on`,
  `source_paths`, `source_status`, `migration_gates`, and an `interfaces` list
  derived from the current source.
- `schema/book-platform.contract.v1.schema.json` plus a dependency-free
  validator in `scripts/check.py` (schema, README/contract agreement,
  interface documentation, placeholder and path-traversal checks).
- `tests/test_contract_check.py` (19 tests) and `.github/workflows/check.yml`.
- `docs/CONTRACT-SURFACE.md` documenting the owned and consumed interfaces.
