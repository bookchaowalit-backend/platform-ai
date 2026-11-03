# 06 — C4 Container

"Container" ของ repo นี้คือ artefact และ CI jobs (ไม่มี process ที่รันถาวร)

```mermaid
C4Container
  title platform-ai — containers (files and CI jobs)
  Person(owner, "Owner / AI agent")
  System_Boundary(repo, "platform-ai repository") {
    ContainerDb(contract, "contract.json", "JSON", "book-platform.contract.v1, 6 interfaces")
    ContainerDb(schema, "schema/", "JSON Schema + sha256 pin", "Vendored copy of the canonical schema")
    ContainerDb(fixture, "fixtures/gates/provider-neutral-parity.json", "JSON", "Routing, budget, redaction, evaluation baseline")
    Container(checks, "scripts/check.py, check_schema_pin.py, check_registry_alignment.py", "Python 3.11+ stdlib", "Offline contract and drift checks")
    Container(parity, "scripts/ai_parity.py", "Python stdlib", "Fixture, oracle, extractors, comparisons")
    Container(harness, "scripts/ai_parity_gateway_harness.mjs", "Node via tsx", "Imports gateway modules, loopback mock provider")
    Container(tests, "tests/", "unittest", "3 test files")
    Container(docs, "docs/", "Markdown", "CONTRACT-SURFACE, UPGRADE-PLAN, gates/BOO-145")
  }
  System_Boundary(ci, "GitHub Actions: Check") {
    Container(jc, "contract job", "ci-python.yml @87dc5e1", "Ruff + scripts/check.sh on 3.11 and 3.12")
    Container(jg, "gateway-parity job", "ubuntu-latest", "Checkout gateway, npm ci, check.sh + ai_parity.py")
    Container(js, "security job", "security.yml @87dc5e1", "gitleaks, semgrep, osv-scanner, trivy-fs")
  }
  System_Ext(gw, "platform-ai-gateway-api @723d752")

  Rel(owner, checks, "runs")
  Rel(checks, contract, "reads")
  Rel(checks, schema, "reads, hashes")
  Rel(checks, docs, "reads README and CONTRACT-SURFACE")
  Rel(parity, fixture, "reads")
  Rel(parity, harness, "spawns with tsx")
  Rel(harness, gw, "imports api/ai_gateway.ts, api/ai_budget.ts")
  Rel(tests, checks, "imports")
  Rel(tests, parity, "imports")
  Rel(jc, tests, "runs via check.sh")
  Rel(jg, parity, "runs with REQUIRE_GATEWAY_PARITY=1")
```

Sources: `contract.json`, `schema/`, `fixtures/gates/provider-neutral-parity.json`, `scripts/*`, `tests/*`, `docs/*`, `.github/workflows/check.yml`, platform-ci-workflows `ci-python.yml` / `security.yml` @ `87dc5e1c`

## Open questions

- ไม่มี
