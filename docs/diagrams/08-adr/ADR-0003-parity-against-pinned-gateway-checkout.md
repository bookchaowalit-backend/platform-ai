# ADR-0003 — พิสูจน์ parity กับ gateway จริงที่ commit ที่ pin ไว้ โดยไม่ copy code

- Status: accepted (retro-documented)
- Date: retro-documented 2026-11-03 (introduced in PR #1 `17f0e76`, 2026-10-15)

## Context

migration gate แรกคือ "provider-neutral parity" gateway (`platform-ai-gateway-api`) เป็น AGPL-3.0 แต่ repo นี้เป็น Apache-2.0 (`LICENSE`) จึง copy code มาไม่ได้

## Decision

- fixture `fixtures/gates/provider-neutral-parity.json` คือ parity baseline และ pin sha256 ของทุก source file
- CI job `gateway-parity` checkout gateway public ที่ `GATEWAY_COMMIT` (ต้องตรงกับ fixture), `npm ci --ignore-scripts`, รัน harness ที่ import module จริงกับ mock provider บน loopback
- `REQUIRE_GATEWAY_PARITY=1` ทำให้ checkout/tsx หายหรือ pin เปลี่ยน = fail ไม่ใช่ skip
- agent routing/redaction (solo-empire, private) รัน local เท่านั้น

## Evidence

- `.github/workflows/check.yml` job `gateway-parity` (step "Confirm the pin matches the fixture")
- `scripts/ai_parity_gateway_harness.mjs` header comment
- `tests/test_ai_parity.py` `CurrentGatewayParityTests.setUp`
- `docs/gates/BOO-145-provider-neutral-parity.md` "What current means here", "Where parity is enforced"

## Consequences

- drift บน gateway `main` ไม่ถูกเฝ้า (ไม่มี scheduled job) — gate doc "Not done"
- routing parity ของ solo-empire ไม่ถูกบังคับใน CI
