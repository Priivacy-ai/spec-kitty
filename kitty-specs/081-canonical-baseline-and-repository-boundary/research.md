# Research: Canonical Baseline and Repository Boundary

**Mission**: 081-canonical-baseline-and-repository-boundary
**Date**: 2026-04-10

## R1: Current Identity Field Consumer Map

### Decision
The identity fields stored in `.kittify/config.yaml` under `project:` are consumed by 6 major subsystems. Any rename must address all of them in coordinated sequence.

### Findings

**project_uuid (to become repository_uuid):**

| Role | Module | Detail |
|------|--------|--------|
| Writer | `sync/project_identity.py:112-118` | `generate_project_uuid()` mints UUID4 locally |
| Writer | `sync/project_identity.py:217-259` | `atomic_write_config()` persists to config.yaml |
| Writer | `migration/backfill_identity.py:49-88` | `backfill_project_uuid()` for legacy repos |
| Reader | `sync/project_identity.py:262-289` | `load_identity()` from config.yaml |
| Reader | `context/resolver.py:38-53` | `_read_project_uuid()` for context resolution |
| Reader | `sync/namespace.py:67-87` | `from_context()` for body upload namespace — **requires non-empty value** |
| Reader | `sync/namespace.py:37-47` | `__post_init__()` validates non-empty — **hard failure if absent** |
| Reader | `dossier/drift_detector.py:169-198` | `compute_baseline_key()` for drift scope |
| Reader | `sync/queue.py:198-218` | SQLite schema `project_uuid TEXT NOT NULL` — **hard constraint** |
| Reader | `sync/queue.py:27-32` | Coalescence keys scope dedup by `project_uuid` |
| Reader | `core/upstream_contract.json:24` | Listed as required field for body_sync |
| Transmitter | `sync/emitter.py:630-643` | Event envelope: `project_uuid` field |
| Transmitter | `sync/namespace.py:62` | Dedupe key for body uploads |
| Transmitter | `cli/commands/tracker.py:355-361` | `project_identity` dict for bind API |
| Transmitter | `tracker/saas_service.py:228,258` | bind_confirm / bind_resolve payloads |

**project_slug (to become repository_label):**

| Role | Module | Detail |
|------|--------|--------|
| Writer | `sync/project_identity.py:130-173` | `derive_project_slug()` from git remote or dir name |
| Reader | `sync/emitter.py:639` | Event envelope field |
| Transmitter | `sync/emitter.py:630-643` | Transmitted in every event |
| Transmitter | `cli/commands/tracker.py:355-361` | Part of bind API payload |

**repo_slug (unchanged — retains owner/repo meaning):**

| Role | Module | Detail |
|------|--------|--------|
| Writer | `sync/project_identity.py:56-73` | `with_defaults()` — not auto-generated, user override only |
| Reader | `sync/emitter.py:52-65` | Git resolver override |
| Transmitter | `sync/emitter.py:643` | Event envelope field (from git metadata) |

**build_id (unchanged):**

| Role | Module | Detail |
|------|--------|--------|
| Writer | `sync/project_identity.py:121-127` | `generate_build_id()` mints UUID4 |
| Reader | `sync/emitter.py:631` | Event envelope field |
| Transmitter | `sync/emitter.py:631` | Every event envelope |
| Transmitter | `sync/client.py:339-343` | WebSocket pong heartbeat |
| Transmitter | `cli/commands/tracker.py:360` | Bind API payload |

### Rationale
Mapping every consumer is necessary before defining migration sequencing. The event envelope, SaaS bind API, namespace construction, and queue schema are the four surfaces where field renames require careful coordination.

### Alternatives Considered
- Rename only the local config and keep wire/namespace names unchanged: Rejected because it preserves the mislabeling in the most visible contract surfaces and leaves the namespace using a field (`project_uuid`) that is now optional.
- Rename everything atomically in one release: Rejected because SaaS consumers need a deprecation window for wire protocol fields.

---

## R2: Path Resolution Function Impact

### Decision
`locate_project_root` and `get_project_root_or_exit` are called from 47 sites across 28 files. Two duplicate implementations exist. Consolidation should precede the rename.

### Findings

**locate_project_root:**
- Defined in `core/paths.py:28` (primary) and `core/project_resolver.py:16` (legacy wrapper)
- Re-exported from `core/__init__.py:21`
- 36 call sites across 20 files (heaviest: `cli/commands/agent/tasks.py` with 9 calls)
- Result stored inconsistently: `project_root`, `repo_root`, `root`, `resolved_root`, `project_dir`, `main_repo`, `detected_root`

**get_project_root_or_exit:**
- Defined in `cli/helpers.py:133` (thin wrapper around `locate_project_root`)
- 11 call sites across 8 files
- Result always stored as `project_root`

### Rationale
The variable naming inconsistency (some callers already use `repo_root`) means that roughly half the call sites already use the correct canonical name. The rename is primarily a function name change + fixing the other half of variable names.

### Alternatives Considered
- Leave function names as-is and only rename the identity fields: Rejected because the function names are the most visible teaching surface for contributors.
- Create new functions and deprecate old: Preferred approach — add `locate_repository_root` / `get_repository_root_or_exit` as primary, keep old names as deprecated aliases for one release cycle.

---

## R3: SaaS Wire Protocol Migration Strategy

### Decision
SaaS payload field renames must use a versioned dual-write strategy for **both UUID and label fields**: send both old and new field names during the deprecation window, then drop old names after the SaaS server has migrated.

### Findings

Two wire protocols transmit identity fields:

1. **Event envelope** (via WebSocket or offline queue):
   - Fields: `project_uuid`, `project_slug`, `build_id`, `node_id`, `repo_slug`
   - Volume: Every status transition, every sync event
   - Consumer: SaaS event ingestion service
   - **Renames needed**: `project_uuid` → `repository_uuid`, `project_slug` → `repository_label`

2. **Tracker bind API** (via HTTPS):
   - Endpoint: `/api/v1/tracker/bind-resolve/`, `/api/v1/tracker/bind-confirm/`
   - Payload: `project_identity` dict containing `uuid`, `slug`, `node_id`, `repo_slug`, `build_id`
   - Consumer: SaaS tracker binding service
   - **Renames needed**: `uuid` → `repository_uuid`, `slug` → `repository_label`, dict key `project_identity` → `repository_identity`

### Migration Approach
1. **Phase A (CLI dual-write)**: CLI sends both old and new field names for all renamed fields:
   - `project_uuid` AND `repository_uuid` (same value)
   - `project_slug` AND `repository_label` (same value)
   - `repo_slug` unchanged (no dual-write needed)
   - SaaS reads from either field name.
2. **Phase B (SaaS cutover)**: SaaS switches to reading from new field names only. Old field names are ignored but tolerated.
3. **Phase C (CLI cleanup)**: CLI stops sending old field names. Wire protocol contains only canonical names.

### Rationale
Both protocols are consumed by the SaaS backend. The CLI (producer) and SaaS (consumer) are released independently. A hard rename would break any SaaS deployment that hasn't been updated to accept the new field names.

### Alternatives Considered
- API versioning (v1 → v2): Heavyweight for a field rename; dual-write is simpler.
- Rename UUID only, keep `project_slug` as-is: Rejected because leaving a "project_slug" in the wire protocol when the field actually holds a repository label perpetuates the confusion this mission exists to fix.
- Server-side field aliasing only (never rename in CLI): Rejected because the CLI payload code is the most visible teaching surface for contributors.

---

## R4: Config.yaml Migration Strategy

### Decision
The `.kittify/config.yaml` `project:` section must be migrated to `repository:` as the section name with canonical field names. The existing upgrade migration system handles this.

### Findings

Current config.yaml structure:
```yaml
project:
  uuid: "a1b2c3d4-..."       # → becomes repository.repository_uuid
  slug: "my-repo"             # → becomes repository.repository_label
  node_id: "abcdef012345"     # → stays as repository.node_id
  build_id: "e5f6g7h8-..."    # → stays as repository.build_id
  repo_slug: "owner/repo"     # → stays as repository.repo_slug (unchanged meaning)
```

Target config.yaml structure:
```yaml
repository:
  repository_uuid: "a1b2c3d4-..."   # stable local identity
  repository_label: "my-repo"        # mutable display name (was slug/project_slug)
  node_id: "abcdef012345"            # machine identity
  build_id: "e5f6g7h8-..."           # checkout identity
  repo_slug: "owner/repo"            # optional, owner/repo Git provider reference (unchanged)

# project:                            # optional, absent until SaaS binding
#   project_uuid: "x9y0z1-..."       # SaaS-assigned, not locally minted
#   bound_at: "2026-05-01T..."        # ISO timestamp
```

### Rationale
The migration system (`src/specify_cli/upgrade/migrations/`) already handles config.yaml transformations across version upgrades. A new migration can read the old `project:` section, copy values to the new `repository:` section with canonical names.

### Alternatives Considered
- In-place rename within the `project:` section: Rejected because the section name itself is misleading.
- Flat keys (no section nesting): Rejected because the existing config uses sections and mixing patterns would be confusing.

---

## R5: Namespace and Queue Migration Strategy

### Decision
`repository_uuid` replaces `project_uuid` as the required namespace scope key for body sync, queue dedup, and upstream contract validation. This is safe because the UUID value does not change — only the field name.

### Findings

**Affected components:**

1. **NamespaceRef** (`sync/namespace.py:23-87`):
   - `project_uuid` field → `repository_uuid`
   - `__post_init__` validation requires non-empty → unchanged (repository_uuid is always present)
   - `from_context()` reads from `ProjectIdentity.project_uuid` → reads from `RepositoryIdentity.repository_uuid`
   - `to_dict()` serializes as `project_uuid` → serializes as `repository_uuid`
   - `dedupe_key()` uses `project_uuid` as first component → uses `repository_uuid`

2. **Body upload queue** (`sync/queue.py:198-218`):
   - SQLite schema: `project_uuid TEXT NOT NULL` → `repository_uuid TEXT NOT NULL`
   - UNIQUE constraint: first field changes from `project_uuid` to `repository_uuid`
   - Index: `idx_body_queue_namespace` first field changes
   - Coalescence keys: `project_uuid` → `repository_uuid` in key field lists

3. **Upstream contract** (`core/upstream_contract.json:24`):
   - `body_sync.required_fields`: `project_uuid` → `repository_uuid`

### Migration Safety
The UUID value stored in all these locations is the same value that currently lives as `project_uuid` and will become `repository_uuid`. No value changes, no regeneration, no data loss. The SQLite schema migration must rename the column in existing queue databases, or (simpler) recreate the table since queue entries are transient.

### Rationale
Making `project_uuid` optional (absent until SaaS binding) while it remains the required namespace key would break body sync for every repository that hasn't bound to a SaaS project — which is currently all of them. `repository_uuid` is always present (locally minted), so it is the correct required key.

---

## R6: Glossary and Terminology Distribution Strategy

### Decision
The canonical glossary definitions should live in two places: the project glossary system (mission 047+) for machine-readable enforcement, and a human-readable reference document for contributors.

### Findings

- The glossary system in `src/specify_cli/glossary/` supports canonical term definitions with enforcement
- The glossary can flag non-canonical usage during linting/review
- A human-readable terminology reference in `docs/` provides the onboarding surface
- The spec itself (081 spec.md) is the source of truth for the definitions; the glossary and docs are derived views

### Rationale
Two distribution channels serve two audiences: the glossary system enforces consistency for automated checks, while the docs reference serves human contributors who need a prose explanation, not just term → definition mappings.

### Alternatives Considered
- Glossary system only: Rejected because contributors need a prose explanation.
- Docs only: Rejected because automated enforcement prevents drift from recurring.
