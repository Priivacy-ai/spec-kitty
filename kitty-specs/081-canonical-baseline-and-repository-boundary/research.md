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
| Reader | `sync/namespace.py:67-87` | `from_context()` for body upload namespace |
| Reader | `dossier/drift_detector.py:169-198` | `compute_baseline_key()` for drift scope |
| Transmitter | `sync/emitter.py:630-643` | Event envelope: `project_uuid` field |
| Transmitter | `sync/namespace.py:62` | Dedupe key for body uploads |
| Transmitter | `cli/commands/tracker.py:355-361` | `project_identity` dict for bind API |
| Transmitter | `tracker/saas_service.py:228,258` | bind_confirm / bind_resolve payloads |

**project_slug (to become repo_slug locator or similar):**

| Role | Module | Detail |
|------|--------|--------|
| Writer | `sync/project_identity.py:130-173` | `derive_project_slug()` from git remote or dir name |
| Reader | `sync/emitter.py:639` | Event envelope field |
| Transmitter | `sync/emitter.py:630-643` | Transmitted in every event |
| Transmitter | `cli/commands/tracker.py:355-361` | Part of bind API payload |

**repo_slug (currently optional override):**

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
Mapping every consumer is necessary before defining migration sequencing. The event envelope and SaaS bind API are the two wire-protocol surfaces where field renames are breaking changes requiring versioned migration.

### Alternatives Considered
- Rename only the local config and keep wire names unchanged: Rejected because it preserves the mislabeling in the most visible contract surface.
- Rename everything atomically in one release: Rejected because SaaS consumers need a deprecation window.

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
SaaS payload field renames must use a versioned dual-write strategy: send both old and new field names during the deprecation window, then drop old names after the SaaS server has migrated.

### Findings

Two wire protocols transmit identity fields:

1. **Event envelope** (via WebSocket or offline queue):
   - Fields: `project_uuid`, `project_slug`, `build_id`, `node_id`, `repo_slug`
   - Volume: Every status transition, every sync event
   - Consumer: SaaS event ingestion service

2. **Tracker bind API** (via HTTPS):
   - Endpoint: `/api/v1/tracker/bind-resolve/`, `/api/v1/tracker/bind-confirm/`
   - Payload: `project_identity` dict containing `uuid`, `slug`, `node_id`, `repo_slug`, `build_id`
   - Consumer: SaaS tracker binding service

### Rationale
Both protocols are consumed by the SaaS backend. The CLI (producer) and SaaS (consumer) are released independently. A hard rename would break any SaaS deployment that hasn't been updated to accept the new field names.

### Migration Approach
1. **Phase A (CLI dual-write)**: CLI sends both `project_uuid` and `repository_uuid` (same value), both `project_slug` and `repo_slug_display` (same value). SaaS reads from either.
2. **Phase B (SaaS cutover)**: SaaS switches to reading from new field names only. Old field names are ignored but tolerated.
3. **Phase C (CLI cleanup)**: CLI stops sending old field names. Wire protocol contains only canonical names.

### Alternatives Considered
- API versioning (v1 → v2): Heavyweight for a field rename; dual-write is simpler.
- Server-side field aliasing only (never rename in CLI): Rejected because the CLI payload code is the most visible teaching surface for contributors.

---

## R4: Config.yaml Migration Strategy

### Decision
The `.kittify/config.yaml` `project:` section must be migrated to use `repository:` as the section name and `repository_uuid` as the key. The existing upgrade migration system handles this.

### Findings

Current config.yaml structure:
```yaml
project:
  uuid: "a1b2c3d4-..."     # → becomes repository.repository_uuid
  slug: "my-repo"           # → becomes repository.repo_slug (locator)
  node_id: "abcdef012345"   # → stays (machine identity, scope-neutral)
  build_id: "e5f6g7h8-..."  # → stays (already correct)
  repo_slug: "owner/repo"   # → stays as optional override
```

Target config.yaml structure:
```yaml
repository:
  repository_uuid: "a1b2c3d4-..."  # stable local identity
  repo_slug: "my-repo"             # mutable locator (was project_slug)
  node_id: "abcdef012345"          # machine identity
  build_id: "e5f6g7h8-..."         # checkout identity
  repo_slug_override: "owner/repo" # optional user override (was repo_slug)
project:                            # optional, absent until SaaS binding
  project_uuid: "x9y0z1-..."       # SaaS-assigned, not locally minted
```

### Rationale
The migration system (`src/specify_cli/upgrade/migrations/`) already handles config.yaml transformations across version upgrades. A new migration can read the old `project:` section, copy `uuid` → `repository_uuid`, and create the new `repository:` section.

### Alternatives Considered
- In-place rename within the `project:` section: Rejected because the section name itself is misleading.
- Flat keys (no section nesting): Rejected because the existing config uses sections and mixing patterns would be confusing.

---

## R5: Glossary and Terminology Distribution Strategy

### Decision
The canonical glossary definitions should live in two places: the project glossary system (mission 047+) for machine-readable enforcement, and a human-readable reference document for contributors.

### Findings

- The glossary system in `src/specify_cli/glossary/` supports canonical term definitions with enforcement
- The glossary can flag non-canonical usage during linting/review
- A human-readable terminology reference in `docs/` provides the onboarding surface
- The spec itself (081 spec.md) is the source of truth for the definitions; the glossary and docs are derived views

### Rationale
Two distribution channels serve two audiences: the glossary system enforces consistency for automated checks, while the docs reference serves human contributors who need to look up the canonical term for what they're writing.

### Alternatives Considered
- Glossary system only: Rejected because contributors need a prose explanation, not just term → definition mappings.
- Docs only: Rejected because automated enforcement prevents drift from recurring.
