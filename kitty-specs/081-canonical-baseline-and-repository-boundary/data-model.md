# Data Model: Canonical Baseline and Repository Boundary

**Mission**: 081-canonical-baseline-and-repository-boundary
**Date**: 2026-04-10

## Identity Layer — Before and After

### Current Model (pre-081)

All identity fields are bundled under `ProjectIdentity` and stored in the `project:` config section. The naming implies SaaS project scope, but every value is locally minted and repository/build-scoped.

```
ProjectIdentity
├── project_uuid   : UUID4    # locally minted, actually repository identity
├── project_slug   : str      # derived from git remote/dir, actually repo locator
├── node_id        : str      # 12-char hex machine ID
├── repo_slug      : str?     # optional user override (owner/repo)
└── build_id       : str      # UUID4, per checkout/worktree
```

**Config representation** (`.kittify/config.yaml`):
```yaml
project:
  uuid: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  slug: "spec-kitty"
  node_id: "abcdef012345"
  build_id: "f1e2d3c4-b5a6-7890-1234-567890abcdef"
  # repo_slug: "owner/repo"  # optional, only if user sets it
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

### Canonical Model (post-081)

Identity is split into three scoped layers. `RepositoryIdentity` holds the local stable identity. `ProjectBinding` holds the optional SaaS collaboration identity. Each field name reflects its actual scope.

```
RepositoryIdentity
├── repository_uuid      : UUID4    # stable local identity (was project_uuid)
├── repo_slug            : str      # mutable locator (was project_slug)
├── node_id              : str      # 12-char hex machine ID (unchanged)
├── repo_slug_override   : str?     # optional user override (was repo_slug)
└── build_id             : str      # UUID4, per checkout/worktree (unchanged)

ProjectBinding (optional, absent until SaaS binding)
├── project_uuid         : UUID4    # SaaS-assigned collaboration identity
└── bound_at             : datetime # when binding was established
```

**Config representation** (`.kittify/config.yaml`):
```yaml
repository:
  repository_uuid: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  repo_slug: "spec-kitty"
  node_id: "abcdef012345"
  build_id: "f1e2d3c4-b5a6-7890-1234-567890abcdef"
  # repo_slug_override: "owner/repo"  # optional

# project:                # absent until SaaS binding
#   project_uuid: "..."   # assigned by SaaS, not locally minted
#   bound_at: "..."       # ISO timestamp of binding
```

**Wire protocol** (event envelope, post-migration):
```json
{
  "repository_uuid": "a1b2c3d4-...",
  "repo_slug": "spec-kitty",
  "build_id": "f1e2d3c4-...",
  "node_id": "abcdef012345",
  "project_uuid": null
}
```

## Field Mapping

| Current Name | Current Section | Canonical Name | Canonical Section | Migration |
|-------------|----------------|---------------|-------------------|-----------|
| `uuid` | `project:` | `repository_uuid` | `repository:` | Copy value, rename key and section |
| `slug` | `project:` | `repo_slug` | `repository:` | Copy value, rename key and section |
| `node_id` | `project:` | `node_id` | `repository:` | Move to new section, no key rename |
| `build_id` | `project:` | `build_id` | `repository:` | Move to new section, no key rename |
| `repo_slug` | `project:` | `repo_slug_override` | `repository:` | Rename key to disambiguate from `repo_slug` (the locator) |
| (new) | — | `project_uuid` | `project:` | New field, absent until SaaS binding |
| (new) | — | `bound_at` | `project:` | New field, absent until SaaS binding |

## Class Rename Mapping

| Current | Canonical | Notes |
|---------|-----------|-------|
| `ProjectIdentity` | `RepositoryIdentity` | Primary identity class |
| `generate_project_uuid()` | `generate_repository_uuid()` | UUID4 minting function |
| `derive_project_slug()` | `derive_repo_slug()` | Git remote/dir name derivation |
| `backfill_project_uuid()` | `backfill_repository_uuid()` | Legacy migration function |
| `ensure_identity()` | `ensure_identity()` | Name is scope-neutral, no change needed |
| `load_identity()` | `load_identity()` | Name is scope-neutral, no change needed |

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

- **absent**: No SaaS project claims this repository. `project:` section is absent from config.yaml. All CLI operations work normally.
- **bound**: A SaaS project has been assigned. `project:` section appears in config.yaml with `project_uuid` and `bound_at`. CLI operations continue to work identically; the `project_uuid` is included in wire protocol payloads.

No intermediate states. Binding is atomic (either the SaaS assigned a UUID or it didn't).

## Consumer Impact Summary

| Consumer | Fields Used | Migration Complexity |
|----------|------------|---------------------|
| `sync/project_identity.py` | All fields | High — core class rename + all field renames |
| `sync/emitter.py` | `project_uuid`, `project_slug`, `build_id`, `node_id`, `repo_slug` | High — event envelope field renames (wire protocol) |
| `sync/client.py` | `build_id` | Low — field name unchanged |
| `sync/namespace.py` | `project_uuid` | Medium — rename in namespace construction |
| `cli/commands/tracker.py` | All fields | Medium — `project_identity` dict construction |
| `tracker/saas_service.py` | `project_identity` dict | Medium — payload rename |
| `tracker/saas_client.py` | `project_identity` dict | Medium — HTTP payload rename |
| `context/resolver.py` | `project_uuid` | Low — single read site |
| `dossier/drift_detector.py` | `project_uuid`, `node_id` | Low — baseline key rename |
| `migration/backfill_identity.py` | `project_uuid` | Low — function rename |
| `core/paths.py` | N/A (function names only) | Medium — 36 call sites |
| `cli/helpers.py` | N/A (function names only) | Low — wrapper rename + 11 call sites |
