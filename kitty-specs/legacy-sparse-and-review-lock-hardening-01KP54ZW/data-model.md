# Data Model: Legacy Sparse-Checkout Cleanup and Review-Lock Hardening

**Mission**: `legacy-sparse-and-review-lock-hardening-01KP54ZW`
**Phase**: 1 (Design)
**Date**: 2026-04-14

This mission is a bugfix / hardening mission against existing subsystems, not a new data product. The "data model" section therefore enumerates the structured types and on-disk artifacts introduced or modified by the mission.

---

## New in-memory types

### `SparseCheckoutState`

Module: `src/specify_cli/git/sparse_checkout.py`

Immutable result of the detection primitive (FR-001). All fields populated by inspecting the target path, its git config, and its worktree-local state.

```python
@dataclass(frozen=True)
class SparseCheckoutState:
    """Result of probing a repository or worktree for sparse-checkout state."""
    path: Path                      # Probed path (repo root or worktree root)
    config_enabled: bool            # True iff `core.sparseCheckout` == "true" at that path
    pattern_file_path: Path | None  # Resolved path to sparse-checkout pattern file, if present
    pattern_file_present: bool      # True iff pattern_file_path exists on disk
    pattern_line_count: int         # Count of non-empty, non-comment lines in the pattern file (0 when absent)
    is_worktree: bool               # True iff the probed path is a linked worktree (not the primary)

    @property
    def is_active(self) -> bool:
        """Canonical "do I need to worry about this repo" signal."""
        return self.config_enabled
```

Invariants:
- `is_active == config_enabled` (R6)
- `pattern_file_present` can be true even when `config_enabled` is false (abandoned pattern files are not themselves active sparse-checkout).
- `pattern_line_count >= 0` always.

### `SparseCheckoutScanReport`

Module: `src/specify_cli/git/sparse_checkout.py`

Aggregate result of scanning the primary repo plus all lane worktrees beneath it.

```python
@dataclass(frozen=True)
class SparseCheckoutScanReport:
    primary: SparseCheckoutState
    worktrees: tuple[SparseCheckoutState, ...]   # Ordered by worktree path; empty tuple if no .worktrees/*

    @property
    def any_active(self) -> bool:
        return self.primary.is_active or any(w.is_active for w in self.worktrees)

    @property
    def affected_paths(self) -> tuple[Path, ...]:
        hits = []
        if self.primary.is_active:
            hits.append(self.primary.path)
        hits.extend(w.path for w in self.worktrees if w.is_active)
        return tuple(hits)
```

### `SparseCheckoutRemediationResult`

Module: `src/specify_cli/git/sparse_checkout_remediation.py`

Per-path outcome of the remediation action.

```python
@dataclass(frozen=True)
class SparseCheckoutRemediationResult:
    path: Path
    success: bool
    steps_completed: tuple[str, ...]   # Ordered list of steps that succeeded, e.g. ("disable", "unset_config", "refresh", "verify_clean")
    error_step: str | None             # Name of the step that failed, if any
    error_detail: str | None           # Human-readable error from that step
    dirty_before_remediation: bool     # True iff the path had uncommitted tracked changes when remediation started
```

Aggregate:

```python
@dataclass(frozen=True)
class SparseCheckoutRemediationReport:
    primary_result: SparseCheckoutRemediationResult
    worktree_results: tuple[SparseCheckoutRemediationResult, ...]

    @property
    def overall_success(self) -> bool:
        return self.primary_result.success and all(w.success for w in self.worktree_results)
```

### Staging-area diff types for the commit-layer backstop

Module: `src/specify_cli/git/commit_helpers.py`

```python
@dataclass(frozen=True)
class UnexpectedStagedPath:
    path: str                     # Path as reported by git (POSIX separators)
    status_code: str              # e.g. "D " (deleted), "A " (added), "M " (modified) — first 2 chars of porcelain
```

```python
class SafeCommitBackstopError(RuntimeError):
    """Raised by safe_commit when the staging area contains paths outside files_to_commit."""
    unexpected: tuple[UnexpectedStagedPath, ...]
    requested: tuple[str, ...]
```

The backstop runs inside `safe_commit` after staging but before the commit invocation. On mismatch it raises, aborting the commit. The raised error surfaces to the caller (`_run_lane_based_merge_locked`, `move-task`, etc.) which already handles `RuntimeError` by printing and exiting.

---

## Modified on-disk state

### User-repo state the mission removes (via remediation)

| Artifact | Location | Action |
|---|---|---|
| `core.sparseCheckout` config key | repo-local git config | Unset |
| `core.sparseCheckout` config key | per-worktree git config (`.git/worktrees/<lane>/config.worktree`) | Unset (if present) |
| Primary sparse pattern file | `.git/info/sparse-checkout` | Removed |
| Per-worktree sparse pattern file | `.git/worktrees/<lane>/info/sparse-checkout` | Removed (per worktree, if present) |
| Working tree lag | primary + each worktree | Refreshed via `git checkout HEAD -- .` |

### User-repo state the mission writes

| Artifact | Location | Written when |
|---|---|---|
| Per-worktree ignore for spec-kitty runtime state | `.git/worktrees/<lane>/info/exclude` — line `.spec-kitty/` appended if absent | On `agent action implement` worktree creation (FR-016) |
| Structured log line | stderr / logging backend | On every `--allow-sparse-checkout` use (FR-008) |

### Spec-kitty repository artifacts (this mission ships code)

| Artifact | Path | Kind |
|---|---|---|
| Detection primitive | `src/specify_cli/git/sparse_checkout.py` | New module |
| Remediation logic | `src/specify_cli/git/sparse_checkout_remediation.py` | New module |
| Commit-layer backstop | `src/specify_cli/git/commit_helpers.py` (modified) | Inline in existing `safe_commit` |
| Doctor finding + remediation action | `src/specify_cli/status/doctor.py` (modified) | New finding class, new action handler |
| Merge preflight | `src/specify_cli/cli/commands/merge.py` (modified) | Preflight block at entry of `_run_lane_based_merge` |
| Merge post-merge refresh + invariant | `src/specify_cli/cli/commands/merge.py` (modified) | Between merge and housekeeping `safe_commit` |
| Implement preflight | `src/specify_cli/cli/commands/agent/workflow.py` or the implement entry point (modified) | Preflight block before `git worktree add` |
| Session warning hook | `src/specify_cli/cli/commands/agent/tasks.py`, and anywhere else state-mutating CLI commands converge | New call-site invoking the session-warning emitter |
| Guard runtime-state filter | `src/specify_cli/cli/commands/agent/tasks.py` `_validate_ready_for_review` (modified) | New deny-list |
| Guidance target-lane fix | `src/specify_cli/cli/commands/agent/tasks.py:823` (modified) | Parameterization |
| Review-lock release on approve/reject | `src/specify_cli/cli/commands/agent/tasks.py` (modified) | New call into `ReviewLock.release()` with empty-dir cleanup |
| `ReviewLock.release()` empty-dir cleanup | `src/specify_cli/review/lock.py` (modified) | Enhance existing `release` staticmethod |
| Per-worktree exclude writer | `src/specify_cli/core/worktree.py` or the VCS create path (modified) | New post-creation step |
| ADR | `architecture/1.x/adr/2026-04-14-sparse-checkout-defense-in-depth.md` | New |
| CHANGELOG entry | `CHANGELOG.md` (modified) | Describes all fixes + recovery recipe |

---

## Contracts

This mission is internal CLI hardening; it does not add HTTP / API contracts. The following function-level contracts are canonical for the new surfaces:

### Detection primitive

```python
def scan_repo(repo_root: Path) -> SparseCheckoutScanReport: ...
def scan_path(path: Path, *, is_worktree: bool) -> SparseCheckoutState: ...
```

- `scan_repo` runs `scan_path` on `repo_root` and on every entry in `repo_root / ".worktrees"` that exists and looks like a git worktree directory.
- Both functions are pure: they read from disk and run git-config lookups but make no mutations.

### Remediation

```python
def remediate(
    report: SparseCheckoutScanReport,
    *,
    interactive: bool,
    confirm: Callable[[str], bool] | None = None,
) -> SparseCheckoutRemediationReport: ...
```

- Refuses if any `SparseCheckoutState` in the report has a dirty tree (FR-005).
- `interactive=False` forces non-interactive behaviour; confirm callback is ignored. In interactive mode, `confirm` is called once per affected path with a plain-language prompt; a false return aborts remediation for that path.
- Always operates on primary first, then worktrees.
- Always writes a full audit to stderr describing every step taken.

### Preflight

```python
def require_no_sparse_checkout(
    repo_root: Path,
    *,
    command: str,
    allow_override: bool,
    override_flag: bool,
    actor: str | None,
    mission_slug: str | None,
    mission_id: str | None,
) -> None: ...
```

- Raises `SparseCheckoutPreflightError` when the scan reports `any_active` and `override_flag` is false.
- If `override_flag` is true, emits the structured log record (`spec_kitty.override.sparse_checkout`) and returns normally.
- `allow_override=False` on callers that must never allow the override (none in this mission; parameter kept for future use).

### Backstop

```python
def assert_staging_area_matches_expected(
    repo_root: Path,
    expected_paths: Sequence[str],
) -> None: ...
```

- Reads `git diff --cached --name-status` and compares the staged path set to `expected_paths` (normalized to POSIX).
- Raises `SafeCommitBackstopError` on mismatch.
- Called by `safe_commit` after its stage step and before its commit step.

### Session warning

```python
def warn_if_sparse_once(repo_root: Path, *, command: str) -> None: ...
def _reset_session_warning_state() -> None: ...   # Test-only helper
```

- First call with an active-sparse repo emits a `WARNING` log line and sets the module-level flag.
- Subsequent calls in the same process do nothing.
- Test fixture resets the flag between tests.

### Review-lock release

Existing method signature preserved; behaviour extended:

```python
class ReviewLock:
    @staticmethod
    def release(worktree: Path) -> None:
        """Remove the lock file and, if the containing directory is now empty, remove the directory."""
```

---

## State transitions this mission touches

No change to the 9-lane state machine. The mission changes the guard that evaluates FOR_REVIEW → {APPROVED, DONE} and FOR_REVIEW → PLANNED (rejection) transitions (FR-015, FR-017, FR-018, FR-019); it also removes the `.spec-kitty/` directory when a review terminates (FR-018). Event-log schema, reducer, and validation rules remain unchanged.

---

## Out of scope for the data model

- No new `status.events.jsonl` event variants (see R3).
- No changes to `MergeState`, `PreflightResult`, or `WPStatus` beyond consumption of the new types.
- No new external APIs, HTTP contracts, or dashboard data.
- No migration for the existing StatusEvent schema.
