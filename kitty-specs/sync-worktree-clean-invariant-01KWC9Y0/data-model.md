# Phase 1 Data Model: Worktree-Clean Sync Invariant

This mission changes *behavior around* existing state; it adds no new persistent schema. The "entities" below are the state objects whose read/write lifecycle the invariant governs.

## Entity: ProjectIdentity

Source: `src/specify_cli/identity/project.py`. Stored in `.kittify/config.yaml` (location/schema unchanged — C-003).

| Field | Type | Source when minted | Deterministic? |
|-------|------|--------------------|----------------|
| `project_uuid` | UUID | `uuid4()` at first `init` (persisted) | no (random, but persisted-once) |
| `project_slug` | str | `derive_project_slug(repo_root)` | yes |
| `node_id` | str | `sha256(hostname:username)[:12]` | yes |
| `build_id` | str | **(changed)** see derivation rule below | **yes (after this mission)** |
| `repo_slug` | str? | user override only | n/a |

**Completeness:** `is_complete == all(project_uuid, project_slug, node_id, build_id)` (`project.py:60`). `repo_slug` is optional.

**States:**
- `incomplete` → on disk but missing ≥1 required field (realistically: `build_id`).
- `complete` → all required fields present.
- `persisted` vs `in-memory` → whether the complete identity is written to `config.yaml`.

**Lifecycle / transitions:**
```
(no config)        --init-->            complete + persisted        (ensure_identity, write-authorized)
incomplete-on-disk --read/emit-->       complete + IN-MEMORY ONLY   (resolve_identity, NO write)   ← the fix
incomplete-on-disk --init/apply-->      complete + persisted        (ensure_identity, write-authorized)
complete-on-disk   --read/emit-->       returned as-is, NO write    (resolve_identity)
```

### Derivation rule (Decision C)

When resolving identity for a read/emit path and `build_id` is missing, derive it deterministically instead of `str(uuid4())`:

```
build_id := uuid5(NAMESPACE, f"{project_uuid}:{node_id}")     # when build_id is absent
```

Invariants of the rule:
- **Stable**: same `(project_uuid, node_id)` → same `build_id` on every call (satisfies NFR-001; SC-003).
- **No write**: derivation happens in memory inside `resolve_identity`/`with_defaults`; never persists on a read path.
- **Backward compatible**: a `build_id` already present on disk is returned unchanged (C-005). `project_uuid` generation is untouched.
- **Seed availability**: requires `project_uuid` present. For the realistic legacy case it is. A truly-uninitialized checkout (no `project_uuid`) is expected to pass through `init` (write-authorized) first; read paths do not invent a random `project_uuid`.

## Entity: TrackerBinding

Source: `src/specify_cli/tracker/` (`saas_service.py`, `config.py`). Stored in `.kittify/config.yaml`.

| Field | Type | Notes |
|-------|------|-------|
| `binding_ref` | str | server-supplied binding reference |

**States:**
- `current` → on-disk `binding_ref` matches the server.
- `pending-upgrade` → server returned a new/changed `binding_ref` not yet persisted.

**Transitions:**
```
read op (status/sync_pull/sync_push/sync_run/map_list)
   server returns changed binding_ref
   --> report pending_binding_upgrade=<ref>   (NO write)        ← the fix
explicit `tracker bind` / apply
   --> save_tracker_config(...)  (persist binding_ref)          (write-authorized)
```

## Entity: Worktree cleanliness state

- Representation: `git status --porcelain` snapshot of the checkout.
- The clean-tree gate (`record-analysis`) allowlist: `meta.json`, `.kittify/encoding-provenance/...` (and coordination residue). **`config.yaml` is NOT allowlisted** and must not be added (C-001).
- Invariant INV-1: covered read/background commands leave this snapshot byte-identical.

## Entity: Write-authorization boundary

- Definition: the set of commands permitted to persist identity / binding config to `config.yaml`.
- Members: `init` (`init.py:99,863`), explicit `tracker bind` / apply-style commands.
- Non-members (must be side-effect-free): status-event emission, `sync status/pull/push/run`, `tracker status`/`map list`, dashboard daemon tick.

## Validation rules (from requirements)

- Any covered read/background command MUST leave `git status --porcelain` and `config.yaml` unchanged (FR-001, INV-1).
- Identity resolved on read paths MUST be identical across N≥2 invocations (NFR-001, SC-003).
- The clean-tree gate MUST still refuse genuine source dirt (FR-007, SC-004).
