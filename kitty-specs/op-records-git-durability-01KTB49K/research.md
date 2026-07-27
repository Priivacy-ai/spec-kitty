# Research: Op Record Git Durability

**Mission**: op-records-git-durability-01KTB49K  
**Phase**: 0 (pre-design research)  
**Date**: 2026-06-05

---

## 1. Current Storage Layout

**Finding**: Op records are written by `InvocationWriter` in `src/specify_cli/invocation/writer.py`.

```python
EVENTS_DIR = ".kittify/events/profile-invocations"   # line 16
INDEX_PATH = ".kittify/events/invocation-index.jsonl" # line 17
```

`InvocationWriter.__init__` sets `self._dir = repo_root / EVENTS_DIR`.

The directory `.kittify/events/` is covered by the project's `.gitignore`, confirmed by issue #1688 (`git:65`). Changing `EVENTS_DIR` to `"kitty-ops"` moves storage out of the gitignored subtree without any `.gitignore` edits.

**Decision**: Change `EVENTS_DIR = "kitty-ops"` in `writer.py`.

---

## 2. Index Path Discrepancy

**Finding**: The `INDEX_PATH` constant is defined at module level but is NOT used inside `_append_to_index`. That method computes the index path independently:

```python
def _append_to_index(self, record: InvocationRecord) -> None:
    index_path = self._dir.parent / "invocation-index.jsonl"   # writer.py:81
```

If `EVENTS_DIR` changes to `"kitty-ops"` without fixing this line:
- `self._dir = repo_root / "kitty-ops"`
- `self._dir.parent = repo_root`
- `index_path = repo_root / "invocation-index.jsonl"` ← wrong location, root-level

**Decision**: Update `_append_to_index` to compute `index_path = self._dir / "ops-index.jsonl"`. Update `INDEX_PATH` constant to `"kitty-ops/ops-index.jsonl"` for documentation/test reference.

---

## 3. Lifecycle Log Path

**Finding**: `src/specify_cli/invocation/lifecycle.py:44`:
```python
LIFECYCLE_LOG_RELATIVE_PATH = Path(".kittify") / "events" / "profile-invocation-lifecycle.jsonl"
```

This path is under `.kittify/events/`, which is gitignored.

**Decision**: Change `LIFECYCLE_LOG_RELATIVE_PATH = Path("kitty-ops") / "lifecycle.jsonl"`.

No structural change to `ProfileInvocationRecord` or `lifecycle.py` logic is needed — only the constant.

---

## 4. Propagation Errors Path

**Finding**: `src/specify_cli/invocation/propagator.py:53`:
```python
PROPAGATION_ERRORS_PATH = ".kittify/events/propagation-errors.jsonl"
```

This path is also under `.kittify/events/`. Moving it to `kitty-ops/` is low-risk since the propagator is NOT deleted in Step 1 (C-003).

**Decision**: Change `PROPAGATION_ERRORS_PATH = "kitty-ops/propagation-errors.jsonl"`. This keeps all Op-related audit files under `kitty-ops/` while leaving propagator logic intact.

---

## 5. Commit Strategy: Direct Git vs `safe_commit`

**Finding**: `safe_commit` (`src/specify_cli/git/commit_helpers.py:788`) requires:
- `worktree_root: Path` — must be a git worktree, not the main checkout
- `destination_ref: str` — the target branch
- Refuses protected branches (including `main`) unless `allow_protected_branch_in_test_mode=True`

Op auto-commits must work from **any** invocation context, including standalone `ask`/`advise`/`do` on `main`. `safe_commit` cannot serve this purpose for main-branch invocations.

**Alternatives considered**:

| Option | Verdict |
|--------|---------|
| `safe_commit` with `allow_protected_branch_in_test_mode=True` | ❌ Test-only escape hatch; semantics are wrong |
| New `allow_protected_branch` flag in `safe_commit` | ❌ Expands `safe_commit` scope beyond its designed purpose (status bookkeeping) |
| Direct subprocess git commit | ✅ Same mechanism used by `specify`, `plan`, `tasks` planning artifact commits |
| Defer commit until next "normal" git op | ❌ Adds complexity; orphan detection becomes ambiguous |

**Decision**: Use direct subprocess git in `complete_invocation()`:
```python
subprocess.run(
    ["git", "-C", str(repo_root), "add", "--", relative_op_path, relative_index_path],
    check=True,
)
subprocess.run(
    ["git", "-C", str(repo_root), "commit", "-m", commit_message],
    check=True,
)
```

Commit errors are logged at WARNING level and do NOT propagate to the caller — a failed commit must not block the invocation response. The Op JSONL file already exists on disk as an untracked file before the commit attempt; a commit failure leaves it in the orphan state.

---

## 6. `InvocationRecord` Model Extension

**Finding**: `InvocationRecord` is a frozen Pydantic v2 model (`model_config = {"frozen": True}`). Adding optional fields is safe — Pydantic v2 handles backward-compatible field additions without breaking existing serialised records.

Current fields include `mode_of_work: str | None = None` as a precedent for additive optional fields.

**Decision**: Add to `InvocationRecord`:
```python
mission_id: str | None = None   # populated when Op runs inside a mission context
wp_id: str | None = None        # populated when Op runs inside a WP context
```

Both default to `None` (excluded from serialisation via `exclude_none=True` on the started event — consistent with existing `mode_of_work` handling).

**Serialisation**: The `write_started` method uses `record.model_dump(exclude_none=True)` — new fields with `None` values produce no on-disk change for legacy callers. Forward compatibility is preserved.

---

## 7. `do_cmd` Zero-Propagation Gap

**Finding**: `do_cmd._build_executor` (line 39):
```python
return ProfileInvocationExecutor(repo_root, router=router)
```

No `propagator=` argument. This means `do` has zero SaaS propagation AND (pre-fix) zero git durability. After this mission, the auto-commit in `complete_invocation()` covers `do` automatically — no call-site changes to `do_cmd.py` are needed.

**Decision**: No change to `do_cmd.py`. The fix is at the executor level.

---

## 8. `MINIMAL_VIABLE_TRAIL_POLICY` Constant

**Finding**: `record.py:87`:
```python
storage_path=".kittify/events/profile-invocations/{invocation_id}.jsonl",
```

This string is used for documentation/policy description only, not for path resolution. Changing it to `"kitty-ops/{invocation_id}.jsonl"` keeps the policy self-documenting and accurate.

**Decision**: Update `MINIMAL_VIABLE_TRAIL_POLICY.tier_1.storage_path` to reflect the new path.

---

## 9. `spec-kitty doctor ops` — Orphan Detection

**Finding**: No existing `doctor ops` subcommand exists. The issue specifies that orphan Ops (started-but-not-completed files in `kitty-ops/`) must be listable via `spec-kitty doctor ops`.

**Decision**: Implement a new `src/specify_cli/doctor/ops.py` module with `list_orphan_ops(repo_root: Path) -> list[Path]`. An orphan is any `.jsonl` file in `kitty-ops/` that does NOT contain a line with `"event": "completed"`. Wire into the `doctor` CLI group.

---

## 10. Existing Test Infrastructure

Relevant existing test files in `tests/specify_cli/invocation/`:

| File | What to add |
|------|-------------|
| `test_writer.py` | `EVENTS_DIR` resolves to `kitty-ops/`; index resolves to `kitty-ops/ops-index.jsonl` |
| `test_executor.py` | `complete_invocation()` triggers git commit; orphan guard (no commit without completed event); `mission_id`/`wp_id` null for standalone |
| `test_record.py` | New fields present; serialise with `exclude_none=True`; no on-disk change for legacy records |

New test file: `tests/specify_cli/invocation/test_doctor_ops.py` — orphan listing.

---

## Summary of Decisions

| Area | Decision |
|------|---------|
| Storage path | `EVENTS_DIR = "kitty-ops"` |
| Index path | `_append_to_index` → `self._dir / "ops-index.jsonl"` |
| Lifecycle log | `LIFECYCLE_LOG_RELATIVE_PATH = Path("kitty-ops") / "lifecycle.jsonl"` |
| Propagation errors | `PROPAGATION_ERRORS_PATH = "kitty-ops/propagation-errors.jsonl"` |
| Commit mechanism | Direct subprocess git; errors are WARNING-logged, not raised |
| New model fields | `mission_id: str \| None = None`, `wp_id: str \| None = None` |
| `do_cmd` fix | No call-site change needed; executor-level commit covers it |
| Orphan detection | New `doctor/ops.py` module + `doctor ops` CLI subcommand |
| `.gitignore` | No changes required |
