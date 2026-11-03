# ADR-0004 — Python standard library เท่านั้น และใช้ shared CI v1.1.1

- Status: accepted (retro-documented)
- Date: retro-documented 2026-11-03 (shared CI adopted in `7b432a2`, 2026-10-22)

## Context

check ต้องรันได้ทุกที่โดยไม่ติดตั้ง package และ CI ต้องตรงกับมาตรฐาน DevSecOps ของ portfolio

## Decision

- scripts และ tests ใช้ Python 3.11+ standard library (`unittest`, JSON Schema subset ใน `check.py`)
- job `contract` เรียก `platform-ci-workflows/ci-python.yml` pinned SHA `87dc5e1c` (v1.1.1) กับ `install-command: "true"`, matrix 3.11/3.12, `test-command: bash scripts/check.sh`
- job `security` เรียก `security.yml` ที่ SHA เดียวกัน

## Evidence

- `README.md` "Python 3.11+, no third-party packages"; `scripts/check.py` docstring "dependency-free"
- `.github/workflows/check.yml` jobs `contract`, `security`
- `PRODUCT.md` "Operating Context" (GitHub-hosted runners, public repository)

## Consequences

- `format-check: false` และ `typecheck-command: ""` เป็น follow-up ตาม comment ใน workflow
- Ruff ของ shared CI เคยทำ main แดง (EXE001, `d03b020`) แก้ใน `ac5b526`
