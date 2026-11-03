# 03 — User flows

ไม่มี routes หรือ pages (ไม่มี UI, ไม่มี HTTP server ใน repo) user flow จึงเป็น journey ของ maintainer ตามคำสั่งที่ README และ gate doc เขียนไว้

## Flow A — แก้ contract หรือ interface

```mermaid
flowchart TD
  A1["Edit contract.json interfaces"] --> A2["Document the same interface id in docs/CONTRACT-SURFACE.md"]
  A2 --> A3["python3 scripts/check.py"]
  A3 -->|"FAIL: interface not documented / README status mismatch / placeholder"| A1
  A3 -->|"OK"| A4["bash scripts/check.sh"]
  A4 --> A5["Optional: check_registry_alignment.py --solo-empire ../solo-empire"]
  A5 -->|"error: field drift"| A6["Change registry first, then this contract"]
  A5 -->|"warning: interface source outside source_paths"| A6
  A5 -->|"aligned"| A7["Commit and push"]
```

Sources: `scripts/check.py` (`_semantic_errors`), `scripts/check_registry_alignment.py` (`compare`), `README.md` "Local verification", `docs/UPGRADE-PLAN.md` P1

## Flow B — เปลี่ยน shared schema

```mermaid
flowchart LR
  B1["Change canonical schema in backend-core contracts/"] --> B2["Copy schema + sha256 pin into schema/"]
  B2 --> B3["python3 scripts/check_schema_pin.py --canonical ../platform-backend-core"]
  B3 -->|"drift or stale pin"| B2
  B3 -->|"OK"| B4["bash scripts/check.sh"]
```

Sources: `README.md` (schema pin paragraph), `scripts/check_schema_pin.py`

## Flow C — Re-run parity gate (BOO-145)

```mermaid
flowchart TD
  C1["bash scripts/check.sh (offline: fixture + oracle + extractors)"] --> C2["npm ci --ignore-scripts in a platform-ai-gateway-api checkout"]
  C2 --> C3["REQUIRE_GATEWAY_PARITY=1 PLATFORM_AI_PARITY_GATEWAY=... bash scripts/check.sh"]
  C3 --> C4["python3 scripts/ai_parity.py --gateway-root ..."]
  C4 --> C5{"ai parity OK?"}
  C5 -->|"pin warning"| C6["Re-review fixture against changed gateway file"]
  C5 -->|"OK"| C7["Optional local: PLATFORM_AI_PARITY_SOLO_EMPIRE=... unittest tests.test_ai_parity"]
  C7 --> C8["Update docs/gates/BOO-145 evidence"]
```

Sources: `docs/gates/BOO-145-provider-neutral-parity.md` "Re-run", `scripts/ai_parity.py`, `tests/test_ai_parity.py`

## Open questions

- ไม่มี flow สำหรับ caller ของ AI API ใน repo นี้ ถ้าต้องการ user flow ของ app ที่เรียก gateway ต้องดูที่ `platform-ai-gateway-api` (ไม่ได้อ่านในรอบนี้)
