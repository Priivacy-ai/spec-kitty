# Data Model: Op Record Git Durability

**Mission**: op-records-git-durability-01KTB49K  
**Date**: 2026-06-05

---

## 1. Storage Directory Structure

```
<repo_root>/
└── kitty-ops/                           # git-tracked (not gitignored)
    ├── <op_id>.jsonl                    # one file per Op, append-only
    ├── ops-index.jsonl                  # performance index for reverse-scan
    ├── lifecycle.jsonl                  # loop-lifecycle pairing log (moved from .kittify/events/)
    └── propagation-errors.jsonl         # propagation error log (moved from .kittify/events/)
```

**Invariant**: `kitty-ops/` is never added to `.gitignore`. All files under it are git-tracked by default.

---

## 2. Op JSONL Format

Each Op produces one `kitty-ops/<op_id>.jsonl` file with two event lines (append-only):

### Started Event

```json
{
  "event": "started",
  "invocation_id": "01KTB49KJKRJ71YR8KERVDMHHA",
  "profile_id": "debugger-debbie",
  "action": "investigate",
  "request_text": "why is the test slow",
  "governance_context_hash": "a3f2c1d8e5f0b2a9",
  "governance_context_available": true,
  "actor": "claude",
  "router_confidence": null,
  "started_at": "2026-06-05T05:30:00+00:00",
  "mode_of_work": "advisory",
  "mission_id": "01KTB49KJKRJ71YR8KERVDMHHA",
  "wp_id": "WP01"
}
```

### Completed Event

```json
{
  "event": "completed",
  "invocation_id": "01KTB49KJKRJ71YR8KERVDMHHA",
  "profile_id": "debugger-debbie",
  "action": "",
  "completed_at": "2026-06-05T05:30:45+00:00",
  "outcome": "done",
  "evidence_ref": null
}
```

### Standalone Op (null correlation fields)

When dispatched outside a mission context, `mission_id` and `wp_id` are omitted (serialised as `None`, excluded by `model_dump(exclude_none=True)`):

```json
{
  "event": "started",
  "invocation_id": "01KTB49KJKRJ71YR8KERVDMHHA",
  "profile_id": "debugger-debbie",
  "action": "investigate",
  "request_text": "...",
  "governance_context_hash": "a3f2c1d8e5f0b2a9",
  "governance_context_available": true,
  "actor": "operator",
  "started_at": "2026-06-05T05:30:00+00:00"
}
```

---

## 3. `InvocationRecord` Model Changes

**File**: `src/specify_cli/invocation/record.py`

New optional fields added to `InvocationRecord` (after existing optional fields):

| Field | Type | Default | Serialised when |
|-------|------|---------|-----------------|
| `mission_id` | `str \| None` | `None` | Populated from active execution context |
| `wp_id` | `str \| None` | `None` | Populated from active WP context |

Both fields use `exclude_none=True` at serialisation (consistent with `mode_of_work`).

`MINIMAL_VIABLE_TRAIL_POLICY.tier_1.storage_path` updated from  
`.kittify/events/profile-invocations/{invocation_id}.jsonl`  
→ `kitty-ops/{invocation_id}.jsonl`

---

## 4. Constant Changes

| File | Constant | Old Value | New Value |
|------|----------|-----------|-----------|
| `invocation/writer.py:16` | `EVENTS_DIR` | `".kittify/events/profile-invocations"` | `"kitty-ops"` |
| `invocation/writer.py:17` | `INDEX_PATH` | `".kittify/events/invocation-index.jsonl"` | `"kitty-ops/ops-index.jsonl"` |
| `invocation/writer.py:81` | (inline) | `self._dir.parent / "invocation-index.jsonl"` | `self._dir / "ops-index.jsonl"` |
| `invocation/lifecycle.py:44` | `LIFECYCLE_LOG_RELATIVE_PATH` | `Path(".kittify") / "events" / "profile-invocation-lifecycle.jsonl"` | `Path("kitty-ops") / "lifecycle.jsonl"` |
| `invocation/propagator.py:53` | `PROPAGATION_ERRORS_PATH` | `".kittify/events/propagation-errors.jsonl"` | `"kitty-ops/propagation-errors.jsonl"` |

---

## 5. Auto-Commit Behaviour in `complete_invocation()`

**File**: `src/specify_cli/invocation/executor.py`

After Step 3 (`write_completed`) succeeds, `complete_invocation()` runs:

```
Step 3: write_completed(invocation_id, ...) → appends completed event to kitty-ops/<op_id>.jsonl
Step 3a (NEW): git add kitty-ops/<op_id>.jsonl kitty-ops/ops-index.jsonl
Step 3b (NEW): git commit -m "op(<profile_id>): <action> [<op_id[:8]>]"
             → on failure: log WARNING, do not raise
```

Steps 4–7 (evidence promotion, artifact links, commit links, SaaS propagation) are unchanged.

**Orphan invariant**: `write_started` writes the `.jsonl` file with the `started` event; it is NOT committed. Only `complete_invocation()` triggers the git commit. If a session crashes between `write_started` and `complete_invocation()`, the file exists as an untracked working-tree file (orphan) — never in git history.

**Commit failure handling**: The git commit is best-effort. If it fails (e.g. nothing to commit, no git config), the method logs at WARNING and returns normally. This matches the behaviour of `_append_to_index` (silent on error) and prevents Op records from blocking commands.

---

## 6. `doctor ops` — Orphan Detection

**New file**: `src/specify_cli/doctor/ops.py`

```python
def list_orphan_ops(repo_root: Path) -> list[Path]:
    """Return paths of .jsonl files in kitty-ops/ that have no 'completed' event."""
```

An orphan is any `kitty-ops/<something>.jsonl` (excluding `ops-index.jsonl`, `lifecycle.jsonl`, `propagation-errors.jsonl`) that does NOT contain a line with `"event": "completed"`.

Wired to `spec-kitty doctor ops` CLI subcommand.

---

## 7. Test Matrix (FR coverage)

| Test ID | Spec FR | Description |
|---------|---------|-------------|
| T-001 | FR-001 | `EVENTS_DIR` constant resolves to `kitty-ops` (not `.kittify/events/profile-invocations`) |
| T-002 | FR-001, FR-009 | `INDEX_PATH` constant resolves to `kitty-ops/ops-index.jsonl`; `_append_to_index` writes there |
| T-003 | FR-002, FR-003 | After `complete_invocation()`, `git log --oneline kitty-ops/` shows a commit matching `op(...)` pattern |
| T-004 | NFR-001 | `git clean -fdx kitty-ops/ && git checkout kitty-ops/` restores the Op JSONL file |
| T-005 | FR-004 | Op started but `complete_invocation()` never called → file in working tree, NOT in `git log kitty-ops/` |
| T-006 | FR-008 | `do` command (`do_cmd._build_executor`) result: `complete_invocation()` produces a commit in `kitty-ops/` |
| T-007 | FR-006, FR-007 | `mission_id`/`wp_id` are `None` for standalone invocations; populated when passed explicitly |

---

## 8. File Change Summary

| File | Change type | Step |
|------|-------------|------|
| `src/specify_cli/invocation/writer.py` | Modify constants (2 lines) + `_append_to_index` (1 line) | Step 1 |
| `src/specify_cli/invocation/lifecycle.py` | Modify constant (1 line) | Step 1 |
| `src/specify_cli/invocation/record.py` | Add 2 model fields + update MVTP constant | Step 1 |
| `src/specify_cli/invocation/executor.py` | Add git commit in `complete_invocation()` (≈10 lines) | Step 1 |
| `src/specify_cli/invocation/propagator.py` | Modify constant (1 line) | Step 1 |
| `src/specify_cli/doctor/ops.py` | New file (orphan listing) | Step 1 |
| `tests/specify_cli/invocation/test_writer.py` | Add T-001, T-002 | Step 1 |
| `tests/specify_cli/invocation/test_executor.py` | Add T-003, T-004, T-005, T-006, T-007 | Step 1 |
| `tests/specify_cli/invocation/test_record.py` | Add field presence and serialisation tests | Step 1 |
| `tests/specify_cli/invocation/test_doctor_ops.py` | New file (T-005 orphan listing) | Step 1 |
