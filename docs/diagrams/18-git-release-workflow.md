# 18 — Git and release workflow

ไม่มี tag หรือ release (`git tag` ว่าง) "production" ของ repo นี้คือ `main` ที่ผ่าน `Check` ไม่มี deploy trigger ประวัติแสดงสองแบบ: direct push ไป `main` (ส่วนใหญ่) และ PR แบบ squash (PR #1, #2 สำหรับ BOO-145)

```mermaid
gitGraph
  commit id: "8d72509 init scaffold"
  branch claude/untitled-session-bhlj06
  commit id: "1415d55 schema check"
  commit id: "3512832 schema pin"
  checkout main
  merge claude/untitled-session-bhlj06 id: "d73696d merge"
  commit id: "d1983d3 impl moved (CI red)"
  commit id: "3a72759 rename platform-ai"
  commit id: "dbb5a72 fix BOO-144 (CI green)"
  branch boo-145-provider-neutral-parity
  commit id: "7c892e1"
  commit id: "5e2a743"
  checkout main
  commit id: "17f0e76 PR 1 squash"
  branch boo-145-owner-decision
  commit id: "6ec72e1"
  checkout main
  commit id: "d87072d PR 2 squash"
  commit id: "7b432a2 shared CI v1.1.1"
  commit id: "d03b020 PRODUCT.md (CI red)"
  commit id: "ac5b526 fix EXE001"
```

```mermaid
flowchart LR
  A["Work on branch or main"] --> B{"PR?"}
  B -->|"yes: BOO-145 work"| C["PR: Check runs on push + pull_request"] --> D["Squash merge"]
  B -->|"no: chores, docs, CI"| E["Direct push to main"]
  D --> F["Check on main push"]
  E --> F
  F --> G["No deploy; main is the release"]
```

Sources: `git log --format='%h %ad %s' origin/main` (21 commits, 2026-09-17 → 2026-10-22), `gh pr list -R bookchaowalit-backend/platform-ai --state all` (PR #1, #2 merged), `gh run list` (head SHAs of branch runs), `gh api .../branches/main/protection` (not protected), `.github/workflows/check.yml`

หมายเหตุ: gitGraph ย่อ commit chore บางตัว (f96a543, a98eca8, c0f3c32, 5a2506c, 92e9779, cba1df2, 1d67e13, 4d30ac4) เพื่อให้อ่านง่าย ตำแหน่งของ branch commits ของ PR เป็นการวาดเชิงตรรกะ

## Open questions

- ต้องการให้งานทุกชิ้นผ่าน PR (และ Codex/owner review) หรือ direct push ยังยอมรับได้สำหรับ scaffold
