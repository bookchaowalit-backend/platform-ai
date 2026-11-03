# 07 — C4 Component

Component ภายใน script หลักสองตัว (`scripts/check.py`, `scripts/ai_parity.py`) ตามชื่อฟังก์ชันจริง

```mermaid
C4Component
  title platform-ai — components of check.py and ai_parity.py
  Container_Boundary(chk, "scripts/check.py") {
    Component(cv, "validate()", "entry", "Required files, read JSON, schema then semantic checks")
    Component(vs, "validate_schema()", "JSON Schema subset", "type, enum, pattern, required, $ref")
    Component(se, "_semantic_errors()", "rules", "status allow-list, implementation repo allow-list, README headings, interface docs, placeholders")
  }
  Container_Boundary(par, "scripts/ai_parity.py") {
    Component(run, "run()", "entry", "Orders fixture, oracle, gateway and routing checks")
    Component(vf, "validate_fixture()", "rules", "Decision state, lane rules, budget classes, canaries")
    Component(or, "check_oracle()", "oracle", "oracle_route and oracle_redact vs fixture cases")
    Component(gf, "gateway_facts() + extract_*()", "regex extractors", "Profile outputs, bounds, error classes, SQL columns, log keys")
    Component(cg, "compare_gateway()", "static parity", "Facts vs fixture, sha256 pin warnings")
    Component(rgc, "run_gateway_cases() + compare_gateway_cases()", "dynamic parity", "Runs harness, checks expectations and canary leaks")
    Component(cr, "compare_routing()", "local only", "Loads model_routing.py and context_pack.py from solo-empire")
  }
  Component_Ext(h, "ai_parity_gateway_harness.mjs", "Node", "Mock provider on 127.0.0.1")
  ComponentDb_Ext(fx, "provider-neutral-parity.json")

  Rel(cv, vs, "calls")
  Rel(cv, se, "calls")
  Rel(run, vf, "calls")
  Rel(run, or, "calls")
  Rel(run, cg, "with --gateway-root")
  Rel(cg, gf, "calls")
  Rel(run, rgc, "when tsx found")
  Rel(rgc, h, "subprocess, PATH and HOME only")
  Rel(run, cr, "with --solo-empire")
  Rel(vf, fx, "reads")
```

Sources: `scripts/check.py`, `scripts/ai_parity.py` (functions L49–L631), `scripts/ai_parity_gateway_harness.mjs`

## Open questions

- ไม่มี
