# Data Model: Mission & Build Identity Contract Cutover

**Mission**: 075-mission-build-identity-contract-cutover
**Date**: 2026-04-08

## Entities Modified

### ProjectIdentity (revised)

**Before**: `build_id` stored in `.kittify/config.yaml` under `project.build_id` (committed to git, shared across worktrees).

**After**: `build_id` stored in `{git-dir}/spec-kitty-build-id` (non-committed, per-worktree).

```
ProjectIdentity
├── project_uuid: str       # .kittify/config.yaml → project.uuid (unchanged)
├── project_slug: str       # .kittify/config.yaml → project.slug (unchanged)
├── node_id: str            # .kittify/config.yaml → project.node_id (unchanged)
├── repo_slug: str | None   # .kittify/config.yaml → project.repo_slug (optional user override,
│                           # e.g., "priivacy-ai/spec-kitty"; NOT derived from project_slug;
│                           # omitted from serialized config if None — unchanged)
└── build_id: str           # {git-dir}/spec-kitty-build-id  ← MOVED (was project.build_id)
```

**Load sequence** (executed inside `ensure_identity(repo_root)`):
1. `git rev-parse --git-dir` → `BuildIdentityError` if subprocess fails (no `.git`)
2. `_migrate_build_id_from_config(config_path, git_dir)` — copy-then-remove from config (idempotent noop if absent)
3. `load_build_id(git_dir)`:
   - Read `{git-dir}/spec-kitty-build-id` → return if present
   - Generate `uuid4()`, write to `{git-dir}/spec-kitty-build-id`, return

**Migration (FR-016, runs once at load time)**:
```
if "build_id" in config.yaml[project]:
    copy build_id → {git-dir}/spec-kitty-build-id   (if not already present there)
    remove build_id from config.yaml[project]
    write config.yaml
```
Idempotent: if `build_id` absent from config, noop.

**Invariants**:
- `config.yaml` never contains `build_id` after first load post-upgrade
- Distinct worktrees always yield distinct `build_id` (different `git-dir` paths → different files)
- Same worktree: identical `build_id` across all invocations

---

### StatusEvent (revised inbound deserialization)

**Before** (`status/models.py:221`):
```python
mission_slug=data.get("mission_slug") or data.get("feature_slug", ""),
```

**After**:
```python
mission_slug=data["mission_slug"],   # KeyError if absent
```

**Invariant**: any inbound event dict without `mission_slug` raises `KeyError("mission_slug")`. No fallback normalization outside migration code.

---

### StatusSnapshot (revised inbound deserialization)

**Before** (`status/models.py:264-268`):
```python
feature_slug = data.get("mission_slug") or data.get("feature_slug")
if feature_slug is None:
    raise KeyError("mission_slug")
return cls(mission_slug=feature_slug, ...)
```

**After**:
```python
mission_slug = data["mission_slug"]  # KeyError if absent
return cls(mission_slug=mission_slug, ...)
```

---

### StatusEvent validation (revised — `status/validate.py`)

**Before** (`validate.py:72`):
```python
if "mission_slug" not in event and "feature_slug" not in event:
    findings.append("Missing required field: mission_slug (or legacy mission_slug)")
```

**After**:
```python
if "mission_slug" not in event:
    findings.append("Missing required field: mission_slug")
```

---

### WPMetadata (revised — `status/wp_metadata.py`)

**Before** (line 74):
```python
feature_slug: str | None = None
```

**After**: field removed entirely. `WPMetadata.model_dump()` never emits `feature_slug`.

---

### IdentityAliases (removed — `core/identity_aliases.py`)

**Before**: module provided `with_tracked_mission_slug_aliases()` which backfilled `mission_slug` from `feature_slug`.

**After**: module deleted or function body replaced with identity/noop. Callers that relied on the backfill must be audited — if any exist outside migration paths, they fail (which surfaces the remaining legacy dependency).

---

### TrackerBindPayload (extended — SaaS call)

**Before** (`tracker/origin.py` → `SaaSTrackerClient.bind_mission_origin`):
```
provider, project_slug, mission_slug, external_issue_id,
external_issue_key, external_issue_url, title, external_status
```

**After**:
```
provider, project_slug, mission_slug, build_id,   ← ADDED
external_issue_id, external_issue_key,
external_issue_url, title, external_status
```

---

## State Transitions

No new state machine. Existing mission/WP lane transitions are unchanged.

The only behavioral state change is `build_id` lifetime:
- **Before**: shared across all worktrees (committed config lifetime)
- **After**: per-worktree, generated once, lives for the lifetime of the `.git/worktrees/<name>/` directory

## Files Deleted or Emptied

| File | Action | Reason |
|------|--------|--------|
| `core/identity_aliases.py` | Delete or empty | Module's only purpose was the removed feature_slug backfill |
| `config.yaml` `project.build_id` key | Removed at migration | Replaced by per-worktree file |
