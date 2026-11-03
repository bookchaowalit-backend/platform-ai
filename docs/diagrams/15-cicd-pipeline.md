# 15 — CI/CD pipeline

workflow เดียว `.github/workflows/check.yml` (name `Check`) ไม่มี CD — ไม่มี deploy job ใด ๆ

```mermaid
flowchart TD
  T1["push (any branch)"] --> W["Check workflow"]
  T2["pull_request"] --> W
  T3["workflow_dispatch"] --> W
  W --> CC{"concurrency check-ref, cancel-in-progress"}
  CC --> J1 & J2 & J3
  subgraph J1["contract (matrix 3.11, 3.12) via ci-python.yml @87dc5e1"]
    A1["Checkout (SHA-pinned)"] --> A2["setup-uv + Python"] --> A3["install-command true"] --> A4["Lint (Ruff)"] --> A5["Test: bash scripts/check.sh"]
  end
  subgraph J2["gateway-parity (ubuntu-latest, 10 min)"]
    B1["checkout repo"] --> B2["checkout gateway @GATEWAY_COMMIT into _gateway"] --> B3["Confirm pin equals fixture"] --> B4["setup-python 3.12"] --> B5["setup-node 22"] --> B6["npm ci --ignore-scripts"] --> B7["check.sh + ai_parity.py --gateway-root (REQUIRE_GATEWAY_PARITY=1)"]
  end
  subgraph J3["security via security.yml @87dc5e1"]
    C1["gitleaks"]; C2["semgrep"]; C3["osv-scanner"]; C4["trivy-fs"]
  end
  J1 & J2 & J3 --> R["Run result (no deploy)"]
```

Sources: `.github/workflows/check.yml`, platform-ci-workflows `.github/workflows/ci-python.yml` and `security.yml` @ `87dc5e1c` (steps Lint `if: inputs.lint-command != ''`, Typecheck skipped because `typecheck-command: ""`, PostgreSQL `if: inputs.postgres` not set, default runner `"ubuntu-24.04"`), `gh run view` of the latest run (7 jobs success, 2026-10-22)

หมายเหตุ: ไม่มี `needs:` ระหว่าง jobs ทั้งสามรันขนาน `format-check: false` และไม่มี typecheck ตาม comment "follow-up" ใน workflow

## Open questions

- ควรเพิ่ม scheduled run เพื่อจับ drift ของ gateway `main` ไหม (gate doc "Not done")
