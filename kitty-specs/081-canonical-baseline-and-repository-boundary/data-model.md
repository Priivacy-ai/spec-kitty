# Data Model: Canonical Baseline and Repository Boundary

**Mission**: 081-canonical-baseline-and-repository-boundary
**Date**: 2026-04-10

## Identity Layer — Before and After

### Current Model (pre-081)

All identity fields are bundled under `ProjectIdentity` and stored in the `project:` config section. The naming implies SaaS project scope, but every value is locally minted and repository/build-scoped. The same `project_uuid` value doubles as both a "project identity" label and the required namespace scope key for body sync, queue dedup, and upstream contract validation.

```
ProjectIdentity
├── project_uuid   : UUID4    # locally minted, actually repository identity
│                              # also used as required namespace key for body sync
├── project_slug   : str      # derived from git remote/dir, actually repo display name
├── node_id        : str      # 12-char hex machine ID
├── repo_slug      : str?     # optional owner/repo Git provider reference
└── build_id       : str      # UUID4, per checkout/worktree
```

**Config representation** (`.kittify/config.yaml`):
```yaml
project:
  uuid: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  slug: "spec-kitty"
  node_id: "abcdef012345"
  build_id: "f1e2d3c4-b5a6-7890-1234-567890abcdef"
  # repo_slug: "Priivacy-ai/spec-kitty"  # optional
```

**Wire protocol** (event envelope):
```json
{
  "project_uuid": "a1b2c3d4-...",
  "project_slug": "spec-kitty",
  "build_id": "f1e2d3c4-...",
  "node_id": "abcdef012345",
  "repo_slug": "Priivacy-ai/spec-kitty"
}
```

**Namespace/dedup** (body sync):
```python
NamespaceRef(
    project_uuid="a1b2c3d4-...",   # required, non-empty
    mission_slug="081-...",
    target_branch="main",
    mission_type="software-dev",
    manifest_version="1",
)
```

### Canonical Model (post-081)

Identity is split into scoped layers. `RepositoryIdentity` holds the local stable identity. `ProjectBinding` holds the optional SaaS collaboration identity. Each field name reflects its actual scope. `repository_uuid` replaces `project_uuid` as the required namespace key for all local operations.

```
RepositoryIdentity
├── repository_uuid    : UUID4    # stable local identity (was project_uuid)
│                                  # required namespace key for body sync/dedup
├── repository_label   : str      # human-readable display name (was project_slug)
├── node_id            : str      # 12-char hex machine ID (unchanged)
├── repo_slug          : str?     # optional owner/repo Git provider reference (unchanged)
└── build_id           : str      # UUID4, per checkout/worktree (unchanged)

ProjectBinding (optional, absent until SaaS binding)
├── project_uuid       : UUID4    # SaaS-assigned collaboration identity
└── bound_at           : datetime # when binding was established
```

**Config representation** (`.kittify/config.yaml`):
```yaml
repository:
  repository_uuid: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  repository_label: "spec-kitty"
  node_id: "abcdef012345"
  build_id: "f1e2d3c4-b5a6-7890-1234-567890abcdef"
  # repo_slug: "Priivacy-ai/spec-kitty"  # optional, unchanged meaning

# project:                # absent until SaaS binding
#   project_uuid: "..."   # assigned by SaaS, not locally minted
#   bound_at: "..."       # ISO timestamp of binding
```

**Wire protocol** (event envelope, post-migration):
```json
{
  "repository_uuid": "a1b2c3d4-...",
  "repository_label": "spec-kitty",
  "repo_slug": "Priivacy-ai/spec-kitty",
  "build_id": "f1e2d3c4-...",
  "node_id": "abcdef012345",
  "project_uuid": null
}
```

**Namespace/dedup** (body sync, post-migration):
```python
NamespaceRef(
    repository_uuid="a1b2c3d4-...",   # required, non-empty (was project_uuid)
    mission_slug="081-...",
    target_branch="main",
    mission_type="software-dev",
    manifest_version="1",
)
```

## Field Mapping

| Current Name | Current Section | Canonical Name | Canonical Section | Migration | Semantic Change |
|-------------|----------------|---------------|-------------------|-----------|-----------------|
| `uuid` | `project:` | `repository_uuid` | `repository:` | Copy value, rename key and section | Name only; value and scope unchanged |
| `slug` | `project:` | `repository_label` | `repository:` | Copy value, rename key and section | Name only; value and derivation unchanged |
| `node_id` | `project:` | `node_id` | `repository:` | Move to new section, no key rename | None |
| `build_id` | `project:` | `build_id` | `repository:` | Move to new section, no key rename | None |
| `repo_slug` | `project:` | `repo_slug` | `repository:` | Move to new section, no key rename | None; retains `owner/repo` meaning |
| (new) | — | `project_uuid` | `project:` | New field, absent until SaaS binding | New; SaaS-assigned only |
| (new) | — | `bound_at` | `project:` | New field, absent until SaaS binding | New |

## Class Rename Mapping

| Current | Canonical | Notes |
|---------|-----------|-------|
| `ProjectIdentity` | `RepositoryIdentity` | Primary identity class |
| `generate_project_uuid()` | `generate_repository_uuid()` | UUID4 minting function |
| `derive_project_slug()` | `derive_repository_label()` | Git remote/dir name derivation |
| `backfill_project_uuid()` | `backfill_repository_uuid()` | Legacy migration function |
| `ensure_identity()` | `ensure_identity()` | Name is scope-neutral, no change needed |
| `load_identity()` | `load_identity()` | Name is scope-neutral, no change needed |

## Wire Protocol Field Mapping

Both UUID and label fields require dual-write during migration:

| Current Wire Field | Canonical Wire Field | Dual-Write Required | Notes |
|-------------------|---------------------|-------------------|-------|
| `project_uuid` | `repository_uuid` | Yes | Same value; both sent during transition |
| `project_slug` | `repository_label` | Yes | Same value; both sent during transition |
| `repo_slug` | `repo_slug` | No | Unchanged name and meaning |
| `build_id` | `build_id` | No | Unchanged |
| `node_id` | `node_id` | No | Unchanged |
| (absent) | `project_uuid` (when bound) | N/A | New field, only present after SaaS binding |

## Namespace/Dedup Key Migration

| Component | Current Key Field | Canonical Key Field | Migration |
|-----------|------------------|--------------------|-----------| 
| `NamespaceRef` dataclass | `project_uuid` (required non-empty) | `repository_uuid` (required non-empty) | Rename field; same value flows through |
| `body_upload_queue` SQLite | `project_uuid TEXT NOT NULL` | `repository_uuid TEXT NOT NULL` | Schema migration; existing rows carry same value |
| UNIQUE constraint | `project_uuid, mission_slug, ...` | `repository_uuid, mission_slug, ...` | Schema migration |
| Queue coalescence keys | `project_uuid` scopes dedup | `repository_uuid` scopes dedup | Update key lists |
| `upstream_contract.json` | `project_uuid` in required_fields | `repository_uuid` in required_fields | Config file update |

**Key invariant**: The UUID value itself does not change. Only the field name changes. Existing offline queue entries remain valid because the value stored in the column is the same — the column is just renamed.

## Function Rename Mapping (Path Resolution)

| Current | Canonical | Call Sites | Notes |
|---------|-----------|------------|-------|
| `locate_project_root()` | `locate_repository_root()` | 36 across 20 files | Two implementations exist (paths.py, project_resolver.py); consolidate first |
| `get_project_root_or_exit()` | `get_repository_root_or_exit()` | 11 across 8 files | Thin wrapper; rename follows |

## Variable Standardization

Result variables from path resolution are currently inconsistent:

| Current Names (mixed) | Canonical Name |
|-----------------------|----------------|
| `project_root` | `repo_root` |
| `project_dir` | `repo_root` |
| `main_repo` | `repo_root` |
| `resolved_root` | `repo_root` |
| `detected_root` | `repo_root` |
| `repo_root` | `repo_root` (already correct) |
| `root` | `repo_root` (when holding repository root) |

## State Transitions

The `ProjectBinding` entity has a simple lifecycle:

```
[absent] --bind--> [bound]
[bound]  --unbind--> [absent]
```

- **absent**: No SaaS project claims this repository. `project:` section is absent from config.yaml. All CLI operations work normally. `repository_uuid` is the namespace key.
- **bound**: A SaaS project has been assigned. `project:` section appears in config.yaml with `project_uuid` and `bound_at`. CLI operations continue to work identically; the `project_uuid` is included in wire protocol payloads alongside `repository_uuid`.

No intermediate states. Binding is atomic (either the SaaS assigned a UUID or it didn't).

## Consumer Impact Summary

| Consumer | Fields Used | Migration Complexity |
|----------|------------|---------------------|
| `sync/project_identity.py` | All fields | High — core class rename + all field renames |
| `sync/emitter.py` | `project_uuid`, `project_slug`, `build_id`, `node_id`, `repo_slug` | High — event envelope field renames (wire protocol dual-write for UUID and label) |
| `sync/namespace.py` | `project_uuid` (required namespace key) | High — rename required field + update all callers |
| `sync/queue.py` | `project_uuid` (SQLite schema, coalescence keys) | High — schema migration + key rename |
| `sync/client.py` | `build_id` | Low — field name unchanged |
| `cli/commands/tracker.py` | All fields | Medium — `project_identity` dict construction |
| `tracker/saas_service.py` | `project_identity` dict | Medium — payload rename |
| `tracker/saas_client.py` | `project_identity` dict | Medium — HTTP payload rename |
| `context/resolver.py` | `project_uuid` | Low — single read site; rename to `repository_uuid` |
| `dossier/drift_detector.py` | `project_uuid`, `node_id` | Low — baseline key rename |
| `migration/backfill_identity.py` | `project_uuid` | Low — function rename |
| `core/paths.py` | N/A (function names only) | Medium — 36 call sites |
| `cli/helpers.py` | N/A (function names only) | Low — wrapper rename + 11 call sites |
| `core/upstream_contract.json` | `project_uuid` in required_fields | Low — config file update |
