---
work_package_id: WP05
title: Body Sync Migration
dependencies: [WP01]
requirement_refs:
- FR-010
- FR-011
- FR-012
- FR-014
- FR-020
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
- T032
- T033
phase: Phase C - Contract Cleanup
assignee: ''
agent: "opencode:gpt-5.4:python-reviewer:reviewer"
shell_pid: "85052"
history:
- timestamp: '2026-04-06T05:39:39Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/sync/namespace.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/namespace.py
- src/specify_cli/sync/body_queue.py
- src/specify_cli/sync/body_transport.py
- src/specify_cli/sync/queue.py
- src/specify_cli/upgrade/migration_064*.py
- tests/specify_cli/sync/test_body_*
- tests/specify_cli/sync/test_namespace*
---

# Work Package Prompt: WP05 – Body Sync Migration

## Objective

Rename `NamespaceRef` and `BodyUploadTask` dataclass fields from feature-era to canonical terms. Migrate the SQLite queue schema. Update the body transport request payload. Insert compatibility gate at body sync chokepoints.

## Context

The body sync subsystem handles artifact upload to SaaS. Three components need changes:
- **NamespaceRef** (`namespace.py`): 5-field tuple identifying an artifact's namespace. Fields `feature_slug` and `mission_key` must become `mission_slug` and `mission_type`.
- **BodyUploadTask** (`body_queue.py`): Dataclass for queued uploads. Same field renames.
- **body_transport.py**: Builds the HTTP request body. Currently sends `feature_slug`, `mission_key`, and `mission_slug` (as compatibility alias). Must send only `mission_slug` and `mission_type`.

The SQLite `body_upload_queue` table has columns matching the old field names. These must be renamed via ALTER TABLE. Pending uploads must survive the migration (FR-020).

**Evidence**: The `body_upload_queue has no column named feature_slug` error observed during feature creation shows the partial cutover is already causing runtime failures.

See `kitty-specs/064-complete-mission-identity-cutover/contracts/body-sync.md` for the post-cutover contract.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`

## Implementation

### T026: Rename NamespaceRef Fields

**Purpose**: Canonical namespace identifier for all body sync operations.

**Steps**:
1. In `src/specify_cli/sync/namespace.py`, `NamespaceRef` dataclass (line ~24):
   - `feature_slug: str` → `mission_slug: str`
   - `mission_key: str` → `mission_type: str`
2. Update `__post_init__` validation (line ~37) — it validates field names in a tuple, update the tuple
3. Update `resolve_manifest_version()` if it references old field names
4. Update ALL code that constructs `NamespaceRef(...)` — search for `NamespaceRef(` across the codebase
5. Update ALL code that reads `.feature_slug` or `.mission_key` from a `NamespaceRef` instance

### T027: Rename BodyUploadTask Fields

**Purpose**: Queue task dataclass must match the new schema.

**Steps**:
1. In `src/specify_cli/sync/body_queue.py`, `BodyUploadTask` dataclass (line ~33):
   - `feature_slug: str` → `mission_slug: str`
   - `mission_key: str` → `mission_type: str`
2. Update all code that reads `.feature_slug` or `.mission_key` from a `BodyUploadTask`
3. Update the `enqueue()` method that maps NamespaceRef fields to queue columns
4. Update the `_row_to_task()` or similar deserialization that reads from SQLite rows

### T028: Update body_transport Request Payload

**Purpose**: The HTTP payload must use canonical field names only.

**Steps**:
1. In `src/specify_cli/sync/body_transport.py`, `_build_request_body()` (line ~65):
   - Remove `"feature_slug": task.feature_slug` line
   - Remove `"mission_key": task.mission_key` line
   - Remove `"mission_slug": task.mission_key` (the compatibility alias) and the TODO comment
   - Add `"mission_slug": task.mission_slug`
   - Add `"mission_type": task.mission_type`
2. Final payload shape must match `contracts/body-sync.md`:
   ```python
   {
       "project_uuid": task.project_uuid,
       "mission_slug": task.mission_slug,
       "target_branch": task.target_branch,
       "mission_type": task.mission_type,
       "manifest_version": task.manifest_version,
       "artifact_path": task.artifact_path,
       "content_hash": task.content_hash,
       "hash_algorithm": task.hash_algorithm,
       "content_body": task.content_body,
   }
   ```

### T029: Insert Compatibility Gate

**Purpose**: Validate payloads before queue write and HTTP send.

**Steps**:
1. In `body_queue.py`, before the SQLite INSERT in `enqueue()`:
   ```python
   from specify_cli.core.contract_gate import validate_outbound_payload
   validate_outbound_payload(namespace_dict, "body_sync")
   ```
2. In `body_transport.py`, before the HTTP POST in `push_content()`:
   ```python
   validate_outbound_payload(body, "body_sync")
   ```

### T030: Create SQLite Queue Schema Migration

**Purpose**: Rename columns in the existing `body_upload_queue` table.

**Steps**:
1. Create `src/specify_cli/upgrade/migration_064_body_queue.py` (or similar)
2. Implement migration:
   ```python
   def apply(conn):
       conn.execute("ALTER TABLE body_upload_queue RENAME COLUMN feature_slug TO mission_slug")
       conn.execute("ALTER TABLE body_upload_queue RENAME COLUMN mission_key TO mission_type")
   ```
3. Wrap in a transaction for atomicity
4. Handle the case where columns are already renamed (idempotent migration)
5. Handle the case where the table doesn't exist yet (skip migration)

### T031: Register Migration in Upgrade Chain

**Purpose**: Migration runs automatically during `spec-kitty upgrade`.

**Steps**:
1. Find the migration registry (likely in `src/specify_cli/upgrade/` or `src/specify_cli/sync/queue.py`)
2. Register the new migration with an appropriate version/order

### T032: Test Queue Migration with Populated Queue

**Purpose**: FR-020 acceptance criterion — zero task loss after migration.

**Steps**:
1. Write a test that:
   - Creates a SQLite database with the OLD schema (feature_slug, mission_key columns)
   - Inserts 3+ rows with sample data
   - Runs the migration
   - Reads back all rows
   - Asserts: same number of rows, all data preserved, columns now named mission_slug and mission_type
2. Write a test for idempotent migration (running twice doesn't error)
3. Write a test for empty table (migration succeeds on empty queue)

### T033: Update Fresh-Install Schema in queue.py

**Purpose**: Fresh installs must create the body_upload_queue table with canonical column names, not legacy ones.

**Steps**:
1. In `src/specify_cli/sync/queue.py` (line ~198), the `_BODY_QUEUE_SCHEMA` string contains:
   ```sql
   feature_slug TEXT NOT NULL,
   mission_key TEXT NOT NULL,
   ```
2. Change to:
   ```sql
   mission_slug TEXT NOT NULL,
   mission_type TEXT NOT NULL,
   ```
3. Search `queue.py` for any other references to `feature_slug` or `mission_key` in SQL strings or column name constants
4. Update `ensure_body_queue_schema()` or any function that uses `_BODY_QUEUE_SCHEMA` if it references column names
5. Test: on a fresh temp directory (no existing DB), verify the table is created with `mission_slug` and `mission_type` columns

**Files**: `src/specify_cli/sync/queue.py`

## Definition of Done

- [ ] `NamespaceRef` fields: `mission_slug`, `mission_type` (no `feature_slug`, `mission_key`)
- [ ] `BodyUploadTask` fields: `mission_slug`, `mission_type`
- [ ] Transport payload matches `contracts/body-sync.md`
- [ ] Gate validates at enqueue and push chokepoints
- [ ] SQLite migration renames columns preserving data
- [ ] Populated queue test demonstrates zero task loss
- [ ] Fresh install creates tables with new column names
- [ ] Full test suite passes

## Risks

- SQLite column rename requires 3.25.0+ — Python 3.11+ bundles 3.39+, so this is safe
- Existing code may reference old field names in SQL strings — grep for `feature_slug` and `mission_key` in SQL literals

## Activity Log

- 2026-04-06T07:35:32Z – claude:sonnet-4.6:python-implementer:implementer – shell_pid=80435 – Started implementation via action command
- 2026-04-06T07:44:02Z – claude:sonnet-4.6:python-implementer:implementer – shell_pid=80435 – Ready for review: renamed NamespaceRef/BodyUploadTask fields, updated transport payload, added contract gate, SQLite column migration, fresh schema, 217 tests passing
- 2026-04-06T07:44:39Z – opencode:gpt-5.4:python-reviewer:reviewer – shell_pid=84377 – Started review via action command
- 2026-04-06T07:46:03Z – opencode:gpt-5.4:python-reviewer:reviewer – shell_pid=84377 – Re-queuing: previous review was incomplete (no verdict issued)
- 2026-04-06T07:46:11Z – opencode:gpt-5.4:python-reviewer:reviewer – shell_pid=85052 – Started review via action command
