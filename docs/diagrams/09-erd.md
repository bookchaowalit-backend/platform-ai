# 09 — ERD

repo นี้ **ไม่มี database** ข้อมูลที่ persist คือไฟล์ JSON ใน Git ภาพแรกจึงเป็น document model ของ `contract.json` ตาม schema ภาพที่สองคือตาราง `ai_run_telemetry` ซึ่งเป็น **compatibility surface** (interface `ai.event.run-telemetry`) ที่ gateway ปัจจุบันเป็นเจ้าของ คอลัมน์มาจาก fixture (`redaction.telemetry_columns`, ที่ extract จาก migration `025_ai_run_telemetry.sql` @ `723d752`) ไม่ใช่ migration ใน repo นี้

## A. Contract document (`contract.json` / `book-platform.contract.v1`)

```mermaid
erDiagram
  CONTRACT ||--|| CURRENT_IMPLEMENTATION : has
  CONTRACT ||--|| MIGRATION : has
  CONTRACT ||--o{ INTERFACE : declares
  CONTRACT ||--o{ CAPABILITY : lists
  CONTRACT ||--o{ DEPENDENCY : depends_on
  CONTRACT ||--o{ MIGRATION_GATE : lists
  CONTRACT {
    string schema_version "book-platform.contract.v1"
    string platform_id "enum, here ai"
    string repository "platform-ai"
    string status "scaffolded, pilot, active, retired"
    string api_version "v1"
    string data_owner "repository or none"
    string surface_doc "docs/CONTRACT-SURFACE.md"
  }
  CURRENT_IMPLEMENTATION {
    string repository "platform-ai-gateway-api"
    string source_path "first of source_paths"
    string source_status "adjacent-domain-repository"
  }
  MIGRATION {
    string compatibility_adapter "required"
    string shadow_parity "pending"
    string cutover "pending"
    string rollback "required"
  }
  INTERFACE {
    string id PK "e.g. ai.http.generate"
    string kind "http, event, cli, object-store, table, config, workflow"
    string direction "provides or consumes"
    string name
    string status "current-in-solo-empire, implemented, pilot, planned"
    string source
    string contract
    string auth
  }
  CAPABILITY { string slug "llm-gateway, model-routing, budget, prompt-policy, rag" }
  DEPENDENCY { string platform_id "identity, data, security, observability" }
  MIGRATION_GATE { string name "4 gates" }
```

Sources: `contract.json`, `schema/book-platform.contract.v1.schema.json` (`properties`, `$defs.interface`)

## B. `ai_run_telemetry` (compatibility surface, owned by the current gateway)

```mermaid
erDiagram
  AI_RUN_TELEMETRY {
    string id PK
    string run_id "upsert key"
    string route
    string prompt_version
    string provider
    string model
    int input_tokens
    int output_tokens
    int total_tokens
    int token_budget
    int latency_ms
    float estimated_cost_usd
    bool cache_hit
    string status
    string metadata_json "allow-listed keys only"
    string created_at
  }
```

Sources: `fixtures/gates/provider-neutral-parity.json` (`redaction.telemetry_columns`, `redaction.telemetry_metadata_keys`), `contract.json` (`ai.event.run-telemetry`: "upsert on run_id"), `docs/CONTRACT-SURFACE.md` (telemetry never contains prompt or response bodies). ชนิดคอลัมน์เป็นการอนุมานจากชื่อ ไม่ได้อ่าน SQL จริง

## C. Parity fixture (top-level keys)

```mermaid
erDiagram
  FIXTURE ||--|| OWNER_DECISION : records
  FIXTURE ||--o{ SOURCE_PIN : pins
  FIXTURE ||--|| ROUTING : defines
  FIXTURE ||--|| BUDGET : defines
  FIXTURE ||--|| REDACTION : defines
  FIXTURE ||--|| EVALUATION : defines
  FIXTURE ||--o{ GAP : lists
  EVALUATION ||--o{ CASE : contains
  SOURCE_PIN {
    string repository
    string commit
    string file_sha256
  }
  OWNER_DECISION {
    string status
    string date
    bool cutover_approved
  }
  CASE {
    string id "GW-*, RT-*, RX-*"
    string expect
  }
  GAP {
    string id "G-1..G-8"
  }
```

Sources: `fixtures/gates/provider-neutral-parity.json`, `scripts/ai_parity.py` (`validate_fixture`)

## Open questions

- ชนิดคอลัมน์จริงของ `ai_run_telemetry` (SQLite บน gateway) ต้องยืนยันจาก `database/migrations/025_ai_run_telemetry.sql` ใน `platform-ai-gateway-api`
- เมื่อ `data_owner: platform-ai` เริ่มมี runtime จะเก็บข้อมูลที่ไหน (Neon แยก project ตาม pattern ของ platform อื่น หรือ SQLite แบบ gateway)
