# 20 — Observability

**Runtime: not_applicable** — `PRODUCT.md`: "Sentry does not apply: nothing runs in production. Add it in the change that activates a runtime." ไม่มี Sentry, PostHog, uptime target หรือ heartbeat ใน repo สัญญาณที่มีจริงคือผลของ CI และ warnings จาก scripts

```mermaid
flowchart LR
  subgraph SIG["Signals that exist"]
    S1["Check workflow run status (contract, gateway-parity, security)"]
    S2["ai_parity.py: 'ai parity: OK/FAIL (n errors, n warnings)'"]
    S3["check.py: 'OK: platform-ai (ai) scaffolded contract, 6 documented interface(s)'"]
    S4["security SARIF artifacts (gitleaks, semgrep, osv, trivy)"]
    S5["check_registry_alignment.py warnings (local)"]
  end
  S1 --> V["GitHub Actions UI / gh run list"]
  S2 --> S1
  S3 --> S1
  S4 --> V
  S5 --> DEV["Developer terminal"]
  subgraph SURF["Compatibility surface telemetry (current gateway, not here)"]
    T1["ai_run_telemetry rows"]
    T2["One content-free JSON log line per request (RD-5)"]
  end
```

Sources: `PRODUCT.md`, `.github/workflows/check.yml`, `scripts/ai_parity.py` (`main`), `scripts/check.py` (`main`), platform-ci-workflows `security.yml` @ `87dc5e1c` (upload-artifact `*-sarif`), `docs/CONTRACT-SURFACE.md`, `docs/gates/BOO-145-provider-neutral-parity.md` (RD-5)

## What is watched

| Watched | By | Alert channel |
|---|---|---|
| contract / parity / security on push | GitHub Actions | none configured in repo (GitHub default notifications only) |
| gateway drift on `main` | nobody | — (gate doc "Not done") |
| solo-empire routing drift | nobody in CI | — |

## Open questions

- ต้องการ alert (เช่น Telegram แบบ repo อื่น) เมื่อ `Check` บน `main` แดงหรือไม่
- G-6: provider quality, p50/p95 latency, rate-card reconciliation ยังไม่มีการวัด
