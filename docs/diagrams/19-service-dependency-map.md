# 19 — Service dependency map

ไม่มี runtime dependency (ไม่มี service ที่รัน) dependency ทั้งหมดเป็น check-time ส่วน `depends_on` ใน contract คือ dependency ที่ประกาศไว้สำหรับ runtime อนาคต

```mermaid
flowchart LR
  PAI["platform-ai (checks)"]
  subgraph CT["Check-time dependencies (real)"]
    PY["Python 3.11 / 3.12 stdlib"]
    NODE["Node 22 + tsx from gateway node_modules"]
    GW["platform-ai-gateway-api @723d752"]
    NPM["npm registry"]
    CIWF["platform-ci-workflows @87dc5e1"]
    CORE["platform-backend-core contracts/ (schema source)"]
    ARCH["architecture-docs @9471af5 (pinned docs)"]
    SOLO["solo-empire @63efeeb (local only)"]
  end
  subgraph DECL["Declared for future runtime (contract depends_on)"]
    ID["identity"]; DATA["data"]; SEC["security"]; OBS["observability"]
  end
  subgraph SURF["Consumed by the compatibility surface (current gateway)"]
    PROV["OpenAI-compatible provider"]
    IDB["Identity bearer check"]
  end
  PAI --> PY & NODE & GW & CIWF & CORE & ARCH
  NODE --> NPM
  PAI -.-> SOLO
  PAI -.->|"declared"| ID & DATA & SEC & OBS
  GW --> PROV & IDB
```

Sources: `contract.json` (`depends_on`, `interfaces` consumes), `.github/workflows/check.yml`, `scripts/ai_parity.py`, `scripts/check_schema_pin.py`, `fixtures/gates/provider-neutral-parity.json` (`sources`), `README.md`

หมายเหตุ: ops record: book-platforms-status (2026-11-03) ระบุว่า gateway ใช้ static hashed tokens และ identity client `ai-gateway` ยังไม่ได้สร้าง ดังนั้นเส้น "Identity bearer check" ในวันนี้ไม่ใช่ platform-identity

## Open questions

- runtime ในอนาคตจะใช้ identity JWKS (audience `ai-api`) แทน static tokens หรือไม่ (owner decision ตาม ops record เดียวกัน)
