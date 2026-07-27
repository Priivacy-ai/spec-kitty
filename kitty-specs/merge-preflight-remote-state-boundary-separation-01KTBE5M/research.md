# Research: Merge Preflight Remote-State Boundary Separation

## Change Surface Analysis

### Decision: Exact defect site

**Chosen**: `TargetBranchSyncStatus.is_safe` at `src/specify_cli/merge/preflight.py:31-32`

**Finding**: `is_safe` returns `True` only for `{"in_sync", "no_tracking_branch"}`. The `"ahead"` state (local has commits origin lacks) is incorrectly classified as unsafe. For a local merge, all origin states are safe — local merge depends only on the local git graph.

**Rationale**: The predicate was authored to protect against merging on top of a stale local base. This protection is valid for `"behind"` and `"diverged"` states (origin has commits local lacks). For `"ahead"`, the protection inverts: local is a strict superset of origin, so there is nothing stale about the merge base.

**Alternatives considered**: Remove `is_safe` entirely. Rejected — the push-safety check needs it. Rename it. Rejected — a second predicate is the correct split; the name can clarify scope.

---

### Decision: Call-site placement

**Chosen**: Gate `_enforce_target_branch_sync_preflight` with `if push:` at `src/specify_cli/cli/commands/merge.py:1508`

**Finding**: The call site fires unconditionally before any local mutation, 395 lines before the actual push at `merge.py:1903`. The push call is already correctly gated on `if push and has_remote(main_repo)`. The preflight call is not.

**Rationale**: Push-safety invariants must be evaluated at push time, not at local-merge time. The `if push:` guard aligns the preflight with the operation it protects.

**Alternatives considered**: Move the entire check inside `_run_lane_based_merge_locked`. Rejected — the call site position (before lock acquisition) is correct; only the push condition is missing.

---

### Decision: New push-preflight module

**Chosen**: Create `src/specify_cli/merge/push_preflight.py`

**Finding**: `refresh_target_branch_tracking_ref` (performs `git fetch`) and `inspect_target_branch_sync` are currently in `preflight.py` — the domain-layer preflight module. They perform secondary-adapter operations (network I/O against origin) and belong in the publish layer.

**Rationale**: The domain layer (`preflight.py`) must not perform network I/O. Extracting to `push_preflight.py` makes the boundary explicit. `preflight.py` retains only local-graph checks.

**Alternatives considered**: Leave the functions in `preflight.py` and import them from `push_preflight.py`. Rejected — the goal is domain/publish layer separation; importing the network function back into domain-layer callers defeats the boundary.

**Interface design**: `push_preflight.py` exports:
- `check_push_safety(repo_root, target_branch, remote_name)` → `TargetBranchPushSafetyResult`
- `TargetBranchPushSafetyResult` — wraps fetch status + sync status + push-safety verdict

The existing `TargetBranchSyncStatus`, `TargetBranchRefreshStatus`, and their helper functions (`refresh_target_branch_tracking_ref`, `inspect_target_branch_sync`) move to `push_preflight.py`. `preflight.py` retains only `run_preflight()` (WP-level local-graph checks) and the `PreflightResult`/`WPStatus` types.

---

### Decision: TargetBranchSyncStatus predicate split

**Chosen**: Add `is_safe_to_push` property; update `is_safe` to be an alias returning `True` always (for local merge safety)

**Finding**: `is_safe` is called in one place — `_enforce_target_branch_sync_preflight` at `merge.py:1256`. The entire predicate will be replaced by the push-safety check in `push_preflight.py`.

**Rationale**: After the refactor, `TargetBranchSyncStatus` moves to `push_preflight.py`. `is_safe_to_push` returns `False` for `"behind"` and `"diverged"` because remote commits are missing locally. Letting those states through would mutate local merge/bookkeeping state before a known non-fast-forward push rejection. `"ahead"`, `"in_sync"`, and `"no_tracking_branch"` are safe to push.

**Push-safety decision matrix**:
| State | Local has | Origin has | Push result | Push-safe? |
|---|---|---|---|---|
| `in_sync` | — | — | Fast-forward (no-op) | ✅ |
| `ahead` | commits + | — | Fast-forward | ✅ |
| `behind` | — | commits + | Rejected by git (non-FF) after local mutation | ❌ block |
| `diverged` | commits + | commits + | Force push required | ❌ block |
| `no_tracking_branch` | — | no remote | No push possible | ✅ (N/A) |

**Rationale for `"behind"` as block**: If local is behind origin, the final push will be rejected by git anyway. Blocking before lane/target merge and bookkeeping avoids leaving local mutation behind a guaranteed publish failure.

---

### Decision: MergeState.push_requested field

**Chosen**: Add `push_requested: bool = False` to `MergeState` dataclass

**Finding**: `MergeState.from_dict` already filters to known fields:
```python
known_fields = {f.name for f in cls.__dataclass_fields__.values()}
filtered = {k: v for k, v in data.items() if k in known_fields}
return cls(**filtered)
```
Adding a new field with a default value (`= False`) is automatically backwards-compatible: old state files that lack `push_requested` will load without the key, and the dataclass default (`False`) fills it in.

**Rationale**: Resume correctness requires knowing whether the original invocation requested a push. Without this field, a resumed merge must either always skip the push step (incorrect for `--push` invocations) or always perform it (incorrect for local-only invocations).

**Storage impact**: Field is serialized as `"push_requested": true|false` in `state.json`. Existing files without this key load with `push_requested=False` (correct default — old merges predating `--push` support, or non-push merges).

---

### Decision: ADR delivery

**Chosen**: Inline with the structural boundary WP (authored and committed in the same work package as `push_preflight.py` creation)

**Rationale**: The ADR documents the same decision being implemented in that WP. Reviewing them together reduces context-switching and allows reviewers to validate the ADR's claims against the code directly.

**ADR location**: `architecture/3.x/adr/2026-06-05-1-merge-publish-layer-boundary.md`

---

## Code Inspection Findings

### preflight.py full surface

- Lines 1-17: Type imports, `TargetBranchSyncState` literal union
- Lines 21-32: `TargetBranchSyncStatus` dataclass — `is_safe` defect here
- Lines 35-43: `TargetBranchRefreshStatus` dataclass
- Lines 46-185: `_git`, `_branch_commit_exists`, `_resolve_tracking_branch`, `refresh_target_branch_tracking_ref`, `inspect_target_branch_sync` — all network/fetch infrastructure → moves to `push_preflight.py`
- Lines 188+: `run_preflight()`, `PreflightResult`, `WPStatus` — WP-level local-graph checks → stays in `preflight.py`

### merge.py call-site map

| Line | Call | Action |
|------|------|--------|
| 1508 | `_enforce_target_branch_sync_preflight(...)` | Wrap with `if push:` |
| 1225 | `_enforce_target_branch_sync_preflight` definition | Update to call `push_preflight.check_push_safety` |
| 1903 | `git push origin` | No change |

### Test surface (test_target_branch_preflight.py)

- `test_merge_preflight_blocks_unsafe_target_with_non_destructive_guidance` — currently uses `"ahead"` as the blocked-state fixture → must be inverted or replaced with `"diverged"` fixture
- `test_merge_preflight_blocks_remote_main_behind_before_mutation` — tests `"behind"` is blocked before merge/bookkeeping mutation
- New tests needed: `push=False + ahead`, `push=False + behind`, `push=False + diverged` (all pass), `push=True + diverged` (blocked), `push=True + ahead` (passes), `#1706 regression` (local-ahead + behind, merge completes)

---

## Unresolved Items

None. All NEEDS CLARIFICATION markers from spec.md resolved. All technical unknowns resolved through code inspection and prior five-paradigm / five-scout analysis.
