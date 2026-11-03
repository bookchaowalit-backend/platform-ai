# ADR-0002 — Vendor shared contract schema พร้อม sha256 pin

- Status: accepted (retro-documented)
- Date: retro-documented 2026-11-03 (introduced in `3512832`, 2026-09-30)

## Context

contract ทุก platform ใช้ schema `book-platform.contract.v1` ร่วมกัน ต้นฉบับอยู่ที่ backend-core แต่ CI ของ repo นี้ต้องรันแบบ offline ไม่มี package ให้ติดตั้ง

## Decision

copy schema มาไว้ที่ `schema/book-platform.contract.v1.schema.json` และ pin sha256 ใน `.sha256`; `scripts/check_schema_pin.py` fail เมื่อไฟล์ไม่ตรง pin และ (กับ `--canonical`) เมื่อไม่ตรงต้นฉบับ แก้ต้นฉบับก่อนเสมอ

## Evidence

- `scripts/check_schema_pin.py`, `schema/book-platform.contract.v1.schema.json.sha256`
- `scripts/check.sh` เรียก `check_schema_pin.py`
- `README.md`: "the canonical copy lives in `bookchaowalit-backend-core/contracts/`; change it there first"
- `tests/test_drift_checks.py` `SchemaPinTests`
- commit `92e9779` "fix: re-pin vendored contract schema to the platform-* canonical copy"

## Consequences

- drift ระหว่าง repo จะถูกจับใน CI แต่การ sync ต้องทำมือ
- `docs/UPGRADE-PLAN.md` P1: แทนด้วย reusable workflow หรือ tagged package เมื่อ backend-core มี
