---
work_package_id: WP04
title: Track 3 — Mission Identity Phase 1
dependencies: []
requirement_refs:
- FR-201
- FR-202
- FR-203
- FR-204
- FR-205
- FR-206
planning_base_branch: main
merge_target_branch: main
branch_strategy: WP04 runs in an execution lane allocated by finalize-tasks. Implementation happens in the lane worktree. Merge target is main.
subtasks:
- T016
- T017
- T018
- T019
history:
- at: '2026-04-09T07:30:50Z'
  event: created
authoritative_surface: src/specify_cli/core/mission_creation.py
execution_mode: code_change
mission_slug: 079-post-555-release-hardening
owned_files:
- src/specify_cli/core/mission_creation.py
- src/specify_cli/mission_metadata.py
- src/specify_cli/sync/events.py
- src/specify_cli/sync/emitter.py
- kitty-specs/079-post-555-release-hardening/meta.json
- tests/core/test_mission_creation*.py
- tests/sync/test_emit_mission_created*.py
- tests/mission_metadata/**
tags: []
---

# WP04 — Track 3: Mission Identity Phase 1

**Spec FRs**: FR-201, FR-202, FR-203, FR-204, FR-205, FR-206
**Priority**: P1 — every new mission created after this lands has a canonical, collision-free identity.
**Estimated size**: ~320 lines

## Objective

Mint a ULID `mission_id` at mission-creation time. Persist it to `meta.json`. Expose it through `MissionIdentity`. Include it in `emit_mission_created()` payloads. Mint mission 079's own `mission_id` as the first dogfood action.

**Phase 1 only**: backfill of historical missions is OUT OF SCOPE (NG-2, C-002). The only code that changes is the CREATE path and the read surface — no migration runners.

## Context

**ADR**: `architecture/adrs/2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md` — ULID is the canonical identity format, numeric prefix is display-only.

**ULID library**: `python-ulid >= 3.0` is already in `pyproject.toml:72`. Import: `from ulid import ULID; str(ULID())`.

**Current `create_mission_core()` field set** (lines 289-309):
```python
meta.setdefault("mission_number", ...)
meta.setdefault("slug", ...)
meta.setdefault("mission_slug", ...)
meta.setdefault("friendly_name", ...)
meta.setdefault("mission_type", ...)
meta.setdefault("target_branch", ...)
meta.setdefault("created_at", ...)
```
`mission_id` is NOT currently written.

**Existing locking**: `status/locking.py:feature_status_lock_path()` provides a `filelock.FileLock` pattern. Adapt it for the `meta.json` write to prevent partial writes under concurrent creation.

**Mission 079 itself**: `kitty-specs/079-post-555-release-hardening/meta.json` currently has no `mission_id`. T016 must add one directly.

## Branch Strategy

Plan in `main`, implement in the lane worktree. Merge back to `main` on completion.

## Subtask Guidance

### T016 — Mint ULID `mission_id` in `mission_creation.py`; persist to `meta.json`; mint 079's own

**File**: `src/specify_cli/core/mission_creation.py` (primary), `kitty-specs/079-post-555-release-hardening/meta.json` (dogfood edit)

**Steps — part A (code change)**:

1. At the top of `create_mission_core()`, add:
   ```python
   from ulid import ULID
   
   # Mint canonical machine-facing identity. The ULID is immutable after creation.
   # mission_number (the numeric prefix) is display-only; see ADR b85116ed.
   mission_id = str(ULID())
   ```

2. Add `meta.setdefault("mission_id", mission_id)` alongside the other `setdefault` calls.

3. Wrap the `meta.json` write in a lock:
   ```python
   from specify_cli.status.locking import feature_status_lock_path
   import filelock

   lock_path = feature_status_lock_path(repo_root, mission_slug_formatted)
   with filelock.FileLock(str(lock_path), timeout=10):
       # Write meta.json atomically
       meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
   ```
   Alternatively, use the existing atomic write pattern already in the repo (temp file + rename). Prefer that if it exists.

4. Add `mission_id` to the JSON output of `spec-kitty agent mission create --json`. Find where the output JSON is constructed and add `"mission_id": meta["mission_id"]`.

5. `get_next_feature_number()` at `worktree.py:163-207` continues to work as a display-number helper. Do NOT remove it. The `mission_id` mint is independent of the numeric prefix — both are computed and written to `meta.json`.

**Steps — part B (mission 079 dogfood edit)**:

6. Edit `kitty-specs/079-post-555-release-hardening/meta.json` directly. Generate a ULID (any standard ULID generator; use Python: `python3 -c "from ulid import ULID; print(str(ULID()))"`) and add it to meta.json:
   ```json
   {
     "mission_id": "01<your-generated-ulid>",
     ...
   }
   ```
   This is the first concrete dogfood action of Track 3 — mission 079 shows that the field exists and has the right format.

**Validation**:
- Call `create_mission_core()` for a fresh test mission. Read `meta.json`. Assert `"mission_id"` key exists, value is a 26-character string, parses as valid ULID.
- `spec-kitty agent mission create test-id-123 --json` output includes `"mission_id"` key.
- `kitty-specs/079-post-555-release-hardening/meta.json` has `"mission_id"` with a non-empty ULID value.

---

### T017 — `MissionIdentity.mission_id` field + `resolve_mission_identity()`

**File**: `src/specify_cli/mission_metadata.py`

**Steps**:

1. Find the `MissionIdentity` dataclass (lines 79-84). Add a field:
   ```python
   @dataclass
   class MissionIdentity:
       mission_slug: str
       mission_number: str
       mission_type: str
       mission_id: str | None = None  # Canonical identity per ADR b85116ed. None only for pre-3.1.1 missions.
   ```
   The `None` default is the ONLY legacy-tolerance hook (per spec A-1 / NG-2).

2. In `resolve_mission_identity(feature_dir: Path)` (lines 121-129), read the new field:
   ```python
   meta = json.loads((feature_dir / "meta.json").read_text())
   return MissionIdentity(
       mission_slug=meta["mission_slug"],
       mission_number=meta.get("mission_number", "000"),
       mission_type=meta.get("mission_type", "software-dev"),
       mission_id=meta.get("mission_id"),  # None if not present (legacy mission)
   )
   ```

3. In any call site that destructures `MissionIdentity` without the new field, update them to handle the new `mission_id` attribute. If the call site uses `dataclasses.astuple()` or similar, check for breakage.

4. For NEW flows in 3.1.1 that depend on `mission_id`: treat `None` as a hard error. For example:
   ```python
   identity = resolve_mission_identity(feature_dir)
   if identity.mission_id is None:
       raise ValueError(
           f"Mission {identity.mission_slug!r} has no mission_id. "
           f"This mission was created before spec-kitty 3.1.1. "
           f"Machine-facing flows require mission_id. See FR-202."
       )
   ```
   This guard applies ONLY to new flows added in 3.1.1. Existing flows that use `mission_slug` continue to work.

**Validation**:
- `resolve_mission_identity()` called on a 3.1.1-created mission → `MissionIdentity.mission_id` is a non-empty ULID string.
- `resolve_mission_identity()` called on a legacy mission (no `mission_id` in meta.json) → `MissionIdentity.mission_id is None` (no exception).
- Any new code that uses `mission_id` with a `None` tolerance handles it correctly.

---

### T018 — `mission_id` in `emit_mission_created()` payload

**Files**: `src/specify_cli/sync/events.py`, `src/specify_cli/sync/emitter.py`

**Steps**:

1. In `sync/events.py`, find `emit_mission_created()` (lines 235-245). Current signature:
   ```python
   def emit_mission_created(
       mission_slug: str,
       mission_number: str,
       target_branch: str,
       wp_count: int,
       created_at: str | None = None,
       causation_id: str | None = None,
   ) -> dict[str, Any] | None:
   ```
   Add `mission_id: str | None = None` as a parameter.

2. In `sync/emitter.py`, find where the event payload dict is built (lines 425-449). Add `"mission_id": mission_id` to the payload dict when `mission_id is not None`:
   ```python
   payload: dict[str, Any] = {
       "mission_slug": mission_slug,
       "mission_number": mission_number,
       "target_branch": target_branch,
       "wp_count": wp_count,
   }
   if mission_id is not None:
       payload["mission_id"] = mission_id
   ```

3. Update the call site in `mission_creation.py` (or wherever `emit_mission_created()` is called) to pass `mission_id=meta["mission_id"]`.

4. This is an **additive** change. The event payload schema gains a new optional field. Existing consumers that don't look for `mission_id` are unaffected.

**Validation**:
- Call `emit_mission_created(mission_slug=..., mission_id="01TEST...")`. Assert the emitted payload JSON contains `"mission_id": "01TEST..."`.
- Call `emit_mission_created()` WITHOUT `mission_id` (legacy call). Assert the emitted payload does NOT contain a `"mission_id"` key.

---

### T019 — Regression tests for Track 3

**Files**: `tests/core/test_mission_creation_identity.py` (new), `tests/core/test_mission_creation_concurrent.py` (new), `tests/sync/test_emit_mission_created_includes_mission_id.py` (new), `tests/mission_metadata/test_mission_identity.py` (new or extend)

**Test T3.1 — `mission_id` minted at creation, ULID-shaped**:
```python
# tests/core/test_mission_creation_identity.py
def test_mission_id_minted_at_creation(tmp_path):
    from ulid import ULID
    create_mission_core(tmp_path, "test-identity", ...)
    meta = json.loads((tmp_path / "kitty-specs" / "..." / "meta.json").read_text())
    assert "mission_id" in meta
    assert len(meta["mission_id"]) == 26  # ULID is 26 chars
    ULID.from_str(meta["mission_id"])  # Parses without exception
```

**Test T3.2 — `mission_id` is NOT derived from prefix scan**:
```python
def test_mission_id_is_not_derived_from_prefix_scan(tmp_path):
    # Create two missions with different numeric prefix spaces
    # Assert: their mission_ids are different ULIDs
    # Assert: changing the kitty-specs/ directory contents does not change the mission_id
    ...
```

**Test T3.3 — Concurrent creates do not collide**:
```python
# tests/core/test_mission_creation_concurrent.py
def test_concurrent_create_no_mission_id_collision(tmp_path):
    import threading
    results = []
    def create_and_capture(slug):
        create_mission_core(tmp_path, slug, ...)
        meta = json.loads(...)
        results.append(meta["mission_id"])
    
    t1 = threading.Thread(target=create_and_capture, args=("concurrent-1",))
    t2 = threading.Thread(target=create_and_capture, args=("concurrent-2",))
    t1.start(); t2.start(); t1.join(); t2.join()
    
    assert len(results) == 2
    assert results[0] != results[1]  # No collision
```

**Test T3.4 — `MissionIdentity` exposes `mission_id`**:
```python
# tests/mission_metadata/test_mission_identity.py
def test_resolve_mission_identity_includes_mission_id(tmp_path):
    # Create a meta.json with mission_id
    identity = resolve_mission_identity(tmp_path)
    assert identity.mission_id is not None
    assert len(identity.mission_id) == 26
```

**Test T3.5 — Legacy mission (no `mission_id`) is tolerated**:
```python
def test_resolve_mission_identity_tolerates_legacy_mission(tmp_path):
    # Create a meta.json WITHOUT mission_id
    identity = resolve_mission_identity(tmp_path)
    assert identity.mission_id is None  # No exception, just None
```

**Test T3.6 — `emit_mission_created` includes `mission_id` in payload**:
```python
# tests/sync/test_emit_mission_created_includes_mission_id.py
def test_emit_mission_created_includes_mission_id():
    # Mock the emitter transport
    # Call emit_mission_created(..., mission_id="01TESTULID")
    # Assert: captured payload dict contains "mission_id": "01TESTULID"
```

## Definition of Done

- [ ] `spec-kitty agent mission create <slug> --json` output includes `mission_id`.
- [ ] `meta.json` for every new mission contains a non-empty ULID `mission_id`.
- [ ] `kitty-specs/079-post-555-release-hardening/meta.json` has `mission_id` (dogfood).
- [ ] `MissionIdentity.mission_id` is populated for new missions; `None` for legacy.
- [ ] `emit_mission_created()` payload includes `mission_id` when provided.
- [ ] All 6 regression tests (T3.1–T3.6) pass.
- [ ] Concurrent creation of 2 missions produces 2 different `mission_id` values (T3.3).
- [ ] `mypy --strict` clean on all modified files.
- [ ] No backfill code or migration scripts added (NG-2).

## Risks

| Risk | Mitigation |
|------|-----------|
| `MissionIdentity` destructuring breaks existing callers | Make `mission_id` an optional field with `None` default. Existing callers that don't access it are unaffected. |
| ULID collision concern | ULIDs are 128-bit with a 80-bit random tail. Collision probability is negligible for any realistic workload. No lock needed for identity uniqueness — the FileLock is for write atomicity only. |
| T016 dogfood edit: wrong ULID format | Use `python3 -c "from ulid import ULID; print(str(ULID()))"` to generate. Validate the length is 26 chars, all characters are Crockford base32. |

## Reviewer Guidance

1. Confirm `meta.json` for mission 079 has a valid ULID `mission_id`.
2. Confirm no backfill code exists: search for `for mission in`, `walk(kitty-specs)`, etc. in the changes.
3. Run T3.3 (concurrent test) 5 times in CI to verify it does not flake.
4. Confirm `mypy --strict` on `mission_metadata.py` handles the `str | None` annotation correctly.
