---
type: reference
updated: 2026-08-21
---

# Contract: ExecutionMode consolidation (retire · rename · guard)

Authoritative Phase-1 contract for mission `rc3-execution-mode-consolidation-01M0GGX1`.
Every line/file below was verified against `upstream/main` @ `c44b4bcf87` (2026-08-21).
Line numbers are anchors; implementers re-`git grep` before editing (numbers drift).

## Contract A — Retire dead enum #2 (governance-gate)

**Precondition:** `src/mission_runtime/context.py:42` defines
`class ExecutionMode(enum.Enum)` with members `WORKTREE="worktree"`,
`CODE_CHANGE="code_change"`. It has **no member consumers** in `src/`
(`MissionExecutionContext.execution_mode` is `str | None`, context.py:306).

**Postcondition:**
1. The class is deleted from `context.py`.
2. Removed from `context.py` module `__all__` (line 359).
3. Removed from `mission_runtime/__init__.py` import (line 32) and `__all__` (line 82).
4. `tests/architectural/test_mission_runtime_surface.py` `_PUBLIC_SURFACE` no longer
   lists `"ExecutionMode"` (line 53).
5. ADR `docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md` updated:
   `ExecutionMode` removed from the `__all__` code snippet (line 76) and its bullet
   (line 84), plus a dated addendum noting M7 retired the dead symbol.

**Behavior invariant:** no runtime path changes — the symbol was never constructed
or compared. `import mission_runtime` and all its live consumers behave identically.

## Contract B — Rename live enum #1 → `WorkProductKind`

**Precondition:** `src/specify_cli/ownership/models.py:21` defines
`class ExecutionMode(StrEnum)` with `CODE_CHANGE="code_change"`,
`PLANNING_ARTIFACT="planning_artifact"`.

**Postcondition:**
1. Class renamed to `WorkProductKind`. **Member names and string values UNCHANGED**
   (`CODE_CHANGE="code_change"`, `PLANNING_ARTIFACT="planning_artifact"`).
2. The `OwnershipManifest.execution_mode` field name is **unchanged**; its type
   annotation becomes `WorkProductKind`.
3. The `infer_execution_mode` function name is **unchanged**; its return annotation
   becomes `WorkProductKind`.
4. All 9 in-repo src consumers updated (import + references):
   `ownership/{models,__init__,inference,validation}.py`,
   `core/worktree.py`, `lanes/{compute,implement_support}.py`,
   `workspace/context.py`, `cli/commands/agent/mission_parsing.py`.
   `ownership/__init__.py` `__all__` gains `"WorkProductKind"`, drops `"ExecutionMode"`.
5. All test consumers updated (see data-model "Test-side consumers"). **No back-compat
   alias** — the old name must not resolve within this repo.
6. Docstrings referencing the old class name updated for consistency.

**Wire invariant:** WP frontmatter `execution_mode:` values (`code_change` /
`planning_artifact`) still parse — proven by the unchanged member string values and
the existing `test_planning_artifact_wp.py` / `test_inference.py` assertions.

**Untouched (external):** `spec_kitty_events.status.ExecutionMode`
(used at `cli/commands/agent/tasks_transition_core.py:218,229`) — the sole surviving
live `ExecutionMode`.

## Contract C — Re-drift guard test (permits M6)

**New file:** `tests/architectural/test_execution_mode_no_redrift.py`.

**Assertions (absence-of-footgun, NOT an exact member set):**
1. No `class ExecutionMode` under `src/` (grep-style over source; 0 matches).
2. No live enum under `src/` that pairs a `worktree` member with a `code_change`
   member (the specific collision being retired).
3. The retired symbol is absent from the `mission_runtime` package surface
   (`"ExecutionMode" not in mission_runtime.__all__`).

**Must PERMIT (AC-5):** M6 later adding a non-diff completion-mode member to
`WorkProductKind`. Therefore the guard must NOT assert `WorkProductKind`'s exact
member set, and must NOT forbid the string `"code_change"` as a *member value* of
`WorkProductKind` (only forbid the `worktree`+`code_change` *pairing* on one enum).

**Red-first:** the guard is RED on the mission base (enum #2 still present) and GREEN
only after Contracts A + B land.

## Acceptance mapping

| Contract | FRs | ACs |
|----------|-----|-----|
| A (retire) | FR-001 | AC-1 |
| B (rename) | FR-002, FR-003, FR-004, FR-005 | AC-2, AC-3, AC-4 |
| C (guard)  | FR-006 | AC-5 |
| all | — | AC-6 (ruff + mypy --strict clean, no new suppressions) |
