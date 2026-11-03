# 02 — Use cases

repo นี้ไม่มี auth level ของตัวเอง (ไม่มี runtime) actors จึงเป็นผู้ที่เรียก/รัน artefact ของ repo: owner/agents, GitHub Actions และ repo ข้างเคียง ส่วน actor ของ serving API (scope `api:read`, `ai:generate`) มาจาก contract และถูกบริการโดย gateway ปัจจุบัน

```mermaid
flowchart LR
  OWN(["Owner / AI agent (maintainer)"])
  CI(["GitHub Actions: Check workflow"])
  REG(["solo-empire registry owner"])
  RD(["Caller with scope api:read"])
  GEN(["Caller with scope ai:generate"])

  subgraph REPO["platform-ai (this repo)"]
    UC1["UC1 Validate contract against schema"]
    UC2["UC2 Detect vendored schema drift (sha256 pin)"]
    UC3["UC3 Check README / CONTRACT-SURFACE agree with contract"]
    UC4["UC4 Run parity fixture + oracle offline"]
    UC5["UC5 Run 15 gateway cases against pinned gateway"]
    UC6["UC6 Run agent routing / redaction parity (local only)"]
    UC7["UC7 Compare contract with platform registry (local only)"]
    UC8["UC8 Record gate evidence and owner decision"]
  end

  subgraph SURF["Compatibility surface (served by current gateway, not this repo)"]
    UC9["UC9 Read AI status and monthly budget"]
    UC10["UC10 Generate text through a profile"]
  end

  OWN --> UC1 & UC2 & UC3 & UC4 & UC6 & UC7 & UC8
  CI --> UC1 & UC2 & UC3 & UC4 & UC5
  REG -.->|"registry entry is input"| UC7
  RD --> UC9
  GEN --> UC10
```

Sources: `scripts/check.sh`, `scripts/check.py`, `scripts/check_schema_pin.py`, `scripts/ai_parity.py` (`run`, `main`), `scripts/check_registry_alignment.py`, `.github/workflows/check.yml`, `contract.json` (`interfaces[].auth`), `docs/CONTRACT-SURFACE.md`, `docs/gates/BOO-145-provider-neutral-parity.md`

| Actor | มาจากไหนใน code | Use cases |
|---|---|---|
| Owner / agent | `PRODUCT.md` "Users" | UC1–UC4, UC6–UC8 |
| GitHub Actions | `.github/workflows/check.yml` jobs `contract`, `gateway-parity`, `security` | UC1–UC5 (+ security scan) |
| Registry owner | `scripts/check_registry_alignment.py` อ่าน `repository-catalog/registries/platforms.yaml` | input ของ UC7 |
| `api:read` caller | `contract.json` `ai.http.status.auth` | UC9 |
| `ai:generate` caller | `contract.json` `ai.http.generate.auth`, `ai.consumes.identity-bearer` | UC10 |

## Open questions

- consumer จริงของ `POST /api/ai/generate` คือใครบ้าง (central doc ระบุ "first client: EV3 web on Vercel" ใน architecture-docs `systems/ai-data/central-ai-gateway.md` "Hosted service" แต่ repo นี้ไม่มีรายชื่อ consumer)
