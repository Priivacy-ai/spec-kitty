---
work_package_id: WP02
title: Sparse-Checkout Detection Primitive, Session Warning, and Preflight API
dependencies: []
requirement_refs:
- FR-001
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T019
phase: Phase 0 — Sparse-checkout foundation
history:
- timestamp: '2026-04-14T05:26:49Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/git/sparse_checkout.py
execution_mode: code_change
mission_id: 01KP54ZWEEPCC2VC3YKRX1HT8W
owned_files:
- src/specify_cli/git/sparse_checkout.py
- tests/unit/git/test_sparse_checkout_detection.py
- tests/integration/sparse_checkout/test_detection.py
tags: []
wp_code: WP02
---

# Work Package Prompt: WP02 — Sparse-Checkout Detection Primitive, Session Warning, and Preflight API

## Implementation Command

```bash
spec-kitty agent action implement WP02 --agent <your-agent-name> --mission 01KP54ZW
```

No `--base` flag needed — this WP has no dependencies.

---

## Branch Strategy

- **Planning branch**: `main`
- **Final merge target**: `main`
- The execution worktree is allocated per lane by `finalize-tasks`. Resolve from `lanes.json` at runtime.

---

## Objective

Create the single canonical surface that every other WP in the mission depends on for sparse-checkout handling: pure detection types, scan functions, a once-per-process session warning, and the preflight API used by merge and implement. Keep detection side-effect-free; keep the warning mechanism simple; keep the preflight contract narrow.

---

## Context

- This module is the "detection primitive" in layer 1–4 terminology from the spec's Decision Log. WP03 (remediation), WP04 (doctor), WP05 (preflight callers), WP06/WP07 (session-warning call sites) all depend on the surface this WP delivers.
- Constraints: FR-001 (pure primitive), FR-010 (once-per-process warning), NFR-001 (≤20 ms overhead), NFR-005 (exactly-once emission), C-006 (single source of truth).
- Research references: R4 (module layout), R5 (session-flag mechanism), R6 (detection precision — `core.sparseCheckout=true` is definitive).

---

## Subtask Guidance

### T009 — `SparseCheckoutState` and `SparseCheckoutScanReport` types

**Files**: `src/specify_cli/git/sparse_checkout.py` (new file)

**What**: Create the module with its dataclasses exactly matching the shapes in `data-model.md`.

```python
"""Sparse-checkout detection, session warning, and preflight API.

This module is the single source of truth for sparse-checkout state handling in
spec-kitty 3.x. v3.0.0 removed sparse-checkout support but did not ship a
migration for existing user repos; this module surfaces the lingering state so
doctor and preflights can act on it, and provides the once-per-process warning
that other CLI surfaces hook into.

See Priivacy-ai/spec-kitty#588 for the data-loss regression that motivated this
surface and the four-layer hybrid architecture recorded in ADR
2026-04-14-sparse-checkout-defense-in-depth.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SparseCheckoutState:
    """Result of probing a repository or worktree for sparse-checkout state."""
    path: Path
    config_enabled: bool
    pattern_file_path: Path | None
    pattern_file_present: bool
    pattern_line_count: int
    is_worktree: bool

    @property
    def is_active(self) -> bool:
        """Canonical signal used by preflights and doctor. See R6 in research.md."""
        return self.config_enabled


@dataclass(frozen=True)
class SparseCheckoutScanReport:
    """Aggregate scan of a primary repo and its lane worktrees."""
    primary: SparseCheckoutState
    worktrees: tuple[SparseCheckoutState, ...]

    @property
    def any_active(self) -> bool:
        return self.primary.is_active or any(w.is_active for w in self.worktrees)

    @property
    def affected_paths(self) -> tuple[Path, ...]:
        hits: list[Path] = []
        if self.primary.is_active:
            hits.append(self.primary.path)
        hits.extend(w.path for w in self.worktrees if w.is_active)
        return tuple(hits)
```

**Validation**:
- Frozen dataclasses.
- `is_active` derives only from `config_enabled` per R6. Do not mix in pattern-file presence.
- Include the module-level docstring referencing the regression issue — this is a load-bearing module and future readers need the rationale.

---

### T010 — `scan_path()` and `scan_repo()` pure detection functions

**Files**: `src/specify_cli/git/sparse_checkout.py`

**What**: Two pure functions with no side effects beyond reading disk and spawning `git config` subprocesses.

```python
def scan_path(path: Path, *, is_worktree: bool) -> SparseCheckoutState:
    """Probe a single repo or worktree for sparse-checkout state.

    Reads `git config --get core.sparseCheckout` at the path and inspects the
    sparse-checkout pattern file. Never mutates anything.
    """
    config_enabled = _read_sparse_config_flag(path)
    pattern_file_path = _resolve_sparse_pattern_file(path, is_worktree=is_worktree)
    pattern_file_present = pattern_file_path is not None and pattern_file_path.exists()
    pattern_line_count = (
        _count_nonempty_noncomment_lines(pattern_file_path)
        if pattern_file_present and pattern_file_path is not None
        else 0
    )
    return SparseCheckoutState(
        path=path,
        config_enabled=config_enabled,
        pattern_file_path=pattern_file_path,
        pattern_file_present=pattern_file_present,
        pattern_line_count=pattern_line_count,
        is_worktree=is_worktree,
    )


def scan_repo(repo_root: Path) -> SparseCheckoutScanReport:
    """Probe the primary repo and every lane worktree beneath `.worktrees/`."""
    primary = scan_path(repo_root, is_worktree=False)
    worktrees_dir = repo_root / ".worktrees"
    worktree_states: list[SparseCheckoutState] = []
    if worktrees_dir.exists() and worktrees_dir.is_dir():
        for child in sorted(worktrees_dir.iterdir()):
            if not child.is_dir() or not (child / ".git").exists():
                continue
            worktree_states.append(scan_path(child, is_worktree=True))
    return SparseCheckoutScanReport(primary=primary, worktrees=tuple(worktree_states))
```

Implement the three helpers (`_read_sparse_config_flag`, `_resolve_sparse_pattern_file`, `_count_nonempty_noncomment_lines`) as module-private functions:
- `_read_sparse_config_flag(path)` runs `git config --get core.sparseCheckout` inside `path`; returns `True` iff stdout strips to `"true"`.
- `_resolve_sparse_pattern_file(path, is_worktree)` returns `path / ".git" / "info" / "sparse-checkout"` for the primary, and the per-worktree path `<git-common-dir>/worktrees/<name>/info/sparse-checkout` for worktrees (use `git rev-parse --git-dir` to resolve).
- `_count_nonempty_noncomment_lines(p)` opens the file, counts lines that are non-empty after strip and do not start with `#`.

**Validation**:
- Functions never write to disk or modify config.
- Functions handle non-existent paths gracefully (return a `SparseCheckoutState` with all false/None/zero).
- NFR-001: add a quick microbenchmark to the unit tests asserting a single `scan_path` completes in <20 ms on a typical repo (mock the subprocess and assert negligible overhead).

---

### T011 — `warn_if_sparse_once()` session-warning emitter

**Files**: `src/specify_cli/git/sparse_checkout.py`

**What**: Module-level flag + session-warning function.

```python
_SPARSE_WARNING_EMITTED: bool = False


def warn_if_sparse_once(repo_root: Path, *, command: str) -> None:
    """Emit a WARNING log line once per process if sparse-checkout state is active.

    Subsequent calls in the same process are no-ops. The stable marker
    `spec_kitty.sparse_checkout.detected` is searchable in log aggregators.
    """
    global _SPARSE_WARNING_EMITTED
    if _SPARSE_WARNING_EMITTED:
        return
    try:
        report = scan_repo(repo_root)
    except Exception:  # noqa: BLE001 — never let detection block the command
        return
    if not report.any_active:
        return
    affected = ", ".join(str(p) for p in report.affected_paths)
    logger.warning(
        "spec_kitty.sparse_checkout.detected command=%s repo=%s affected=%s "
        "fix='spec-kitty doctor --fix sparse-checkout'",
        command,
        repo_root,
        affected,
    )
    _SPARSE_WARNING_EMITTED = True


def _reset_session_warning_state() -> None:
    """Test helper — resets the session-warning flag. Not for production use."""
    global _SPARSE_WARNING_EMITTED
    _SPARSE_WARNING_EMITTED = False
```

**Validation**:
- The flag is a module global — simplest possible mechanism per R5.
- `warn_if_sparse_once` is truly once-per-process; second call is a no-op.
- The warning line contains the stable marker `spec_kitty.sparse_checkout.detected` so log collectors can pin it.
- Detection errors are swallowed. A broken detection must never break the CLI command that invoked the warning hook.
- `_reset_session_warning_state` is exported for pytest fixtures.

---

### T012 — Unit tests for detection primitive [P]

**Files**: `tests/unit/git/test_sparse_checkout_detection.py` (new)

**What**: Unit tests covering:
- `SparseCheckoutState.is_active` mirrors `config_enabled`, not pattern presence (R6).
- `scan_path` on a non-sparse repo returns `config_enabled=False` and `pattern_file_present=False`.
- `scan_path` on a sparse repo with no pattern file returns `config_enabled=True`, `pattern_file_present=False`, `pattern_line_count=0`.
- `scan_path` on a sparse repo with patterns returns the correct line count.
- `scan_repo` walks `.worktrees/*` and returns one `SparseCheckoutState` per worktree directory.
- `scan_repo` on a repo without `.worktrees/` returns an empty `worktrees` tuple.
- `warn_if_sparse_once` emits exactly one log line across N consecutive calls on an active-sparse repo (use `caplog`).
- `warn_if_sparse_once` swallows detection errors gracefully.
- `_reset_session_warning_state` re-arms the emitter.

**Validation**:
- Every test uses `tmp_path` for its own isolated repo fixture.
- `caplog` is used to assert log output, not stdout capture.
- Tests reset the session-warning state between runs via a `pytest` fixture.

---

### T019 — `SparseCheckoutPreflightError` + `require_no_sparse_checkout()` API

**Files**: `src/specify_cli/git/sparse_checkout.py`

**What**: The preflight contract used by WP05's merge and implement wiring.

```python
class SparseCheckoutPreflightError(RuntimeError):
    """Raised when a hard-block preflight detects active sparse-checkout state."""

    def __init__(self, command: str, report: SparseCheckoutScanReport) -> None:
        self.command = command
        self.report = report
        affected = "\n".join(f"  {p}" for p in report.affected_paths)
        super().__init__(
            f"{command} aborted: legacy sparse-checkout state detected.\n"
            f"\nAffected paths:\n{affected}\n"
            "\nThis repository has core.sparseCheckout=true configured, which\n"
            "v3.x spec-kitty does not handle correctly and which has caused\n"
            "silent data loss in prior mission merges (see\n"
            "Priivacy-ai/spec-kitty#588).\n"
            "\nFix:\n"
            "  spec-kitty doctor --fix sparse-checkout\n"
            "\nIf you have an intentional sparse configuration and understand\n"
            "the risk, you may pass --allow-sparse-checkout to proceed. Use of\n"
            "this override is logged at WARNING level."
        )


def require_no_sparse_checkout(
    repo_root: Path,
    *,
    command: str,
    override_flag: bool,
    actor: str | None,
    mission_slug: str | None,
    mission_id: str | None,
) -> None:
    """Preflight for commands that must not operate under sparse-checkout.

    If `override_flag` is True and sparse-checkout is active, emits the
    structured override log record (FR-008) and returns. Otherwise raises
    `SparseCheckoutPreflightError` when sparse-checkout is active.
    """
    report = scan_repo(repo_root)
    if not report.any_active:
        return
    if override_flag:
        logger.warning(
            "spec_kitty.override.sparse_checkout command=%s "
            "mission_slug=%s mission_id=%s actor=%s repo=%s affected=%s",
            command,
            mission_slug or "<none>",
            mission_id or "<none>",
            actor or "<unknown>",
            repo_root,
            ",".join(str(p) for p in report.affected_paths),
        )
        return
    raise SparseCheckoutPreflightError(command=command, report=report)
```

**Validation**:
- The error message structure matches `spec.md` FR-008 / quickstart Flow 2.
- The override log record uses the stable marker `spec_kitty.override.sparse_checkout`.
- `--force` is NOT a parameter of this function. Callers that want to bypass must pass `override_flag=True` from their own `--allow-sparse-checkout` flag.
- Both the block path and the override path emit a WARNING log record (though with different markers).

---

## Definition of Done

- [ ] New module `src/specify_cli/git/sparse_checkout.py` exists with module-level docstring referencing #588 and the ADR.
- [ ] `SparseCheckoutState`, `SparseCheckoutScanReport`, `SparseCheckoutPreflightError` are exported from the module (either directly or via `__all__`).
- [ ] `scan_path`, `scan_repo`, `warn_if_sparse_once`, `require_no_sparse_checkout`, `_reset_session_warning_state` are exported.
- [ ] No side effects in `scan_path` or `scan_repo`.
- [ ] `mypy --strict src/specify_cli/git/sparse_checkout.py` passes.
- [ ] `ruff check src/specify_cli/git/sparse_checkout.py` passes.
- [ ] Unit tests in `tests/unit/git/test_sparse_checkout_detection.py` cover every listed case and pass.
- [ ] Coverage on the new module is ≥90%.
- [ ] `pytest tests/unit/git/test_sparse_checkout_detection.py` passes.
- [ ] The module is independently importable and its API is documented in the docstrings.

## Risks

- **Per-worktree git-config layering**: git's config resolution at a worktree layers the worktree-local config on top of the repo-local config. Reading `core.sparseCheckout` from inside a worktree must return the effective value. Tests must include a case where primary has config unset but worktree has it set, and vice versa.
- **`git rev-parse --git-dir` depends on cwd**: when resolving per-worktree pattern paths, the helper must invoke git at the worktree's path, not at the caller's cwd.
- **False "already active" on abandoned pattern files**: if a user left a pattern file behind but has `core.sparseCheckout=false`, detection returns `is_active=False` per R6. Doctor may still want to mention abandoned pattern files as a separate, lower-severity observation — but that is WP04's concern, not this WP's.

## Reviewer Guidance

- Verify that `is_active` depends only on `config_enabled`, not on pattern presence.
- Verify that `warn_if_sparse_once` is truly once-per-process (run the test against a single-process invocation of N calls).
- Verify no code path mutates git state. Grep for `git config --set`, `git sparse-checkout`, `subprocess.run(..., "add", ...)` — none should appear in this module. Mutation is WP03's job.
- Verify the structured-log stable markers match the names used in WP05's override wiring and in quickstart Flow 2 / Flow 3.
