---
work_package_id: WP06
title: doctor.py mission_state multiplexer refactor + typing
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-010
- FR-013
planning_base_branch: fix/quality-check-updates
merge_target_branch: fix/quality-check-updates
branch_strategy: Planning artifacts for this mission were generated on fix/quality-check-updates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/quality-check-updates unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
- T033
- T034
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1147001"
history:
- at: '2026-05-14'
  actor: planner
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/doctor.py
execution_mode: code_change
mission_id: 01KRJGKH4DJCSF277K9QV3WBE7
mission_slug: quality-devex-hardening-3-2-01KRJGKH
owned_files:
- src/specify_cli/cli/commands/doctor.py
- tests/cli/commands/test_doctor_mission_state.py
- tests/regressions/test_doctor_missionrepairresult_findings.py
- kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP06.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Close mypy strict on `src/specify_cli/cli/commands/doctor.py` (WP01's carve-out) AND refactor the `mission_state` CLI command (cognitive complexity 57) into a thin orchestrator + per-mode runners + shared `_emit` helper. The function is classified as **debt** in `work/findings/refactor-audit.md` — three independent dispatch arms (`--audit`, `--fix`, `--teamspace-dry-run`) plus triplicated JSON-vs-pretty logic. Per the refactor classification rubric, this is debt, not deliberate linearity.

Characterization tests precede the refactor commit per `tdd-red-green-refactor` (NFR-003). The typing fix at line 1092 (`RepairReport` vs `RepoAuditReport` mismatch) lands FIRST with a regression test, because the mypy error likely masks a real branch bug. WP01's T003 captured pre-refactor behavior; this WP updates that test to reflect the fixed behavior.

## Context

### Pre-refactor shape

`src/specify_cli/cli/commands/doctor.py:903` defines `mission_state` — ~200 lines, cognitive complexity 57 per Sonar. Body structure:

1. ~70 lines of CLI option validation (`--audit` / `--fix` / `--teamspace-dry-run` mutually exclusive; `--fail-on` parse; fixture-dir resolution).
2. ~60 lines of `--fix` branch (calls `repair_repo`, emits JSON or pretty output).
3. ~30 lines of `--teamspace-dry-run` branch (calls `teamspace_dry_run`, emits JSON or pretty output).
4. ~40 lines of `--audit` branch (calls `run_audit`, emits JSON or pretty output).

The JSON-vs-pretty pattern repeats three times — logical duplication.

### Typing errors in this file (from WP01's residual)

- `doctor.py:631` — unused `type: ignore` + `"object" has no attribute "entries"` (`attr-defined`)
- `doctor.py:1092` — `RepairReport` assigned where `RepoAuditReport` expected (`assignment`)
- `doctor.py:1111` — `RepairReport` passed where `RepoAuditReport` expected (`arg-type`)
- `doctor.py:1119, 1125` — `MissionRepairResult` has no attribute `findings` (`attr-defined`)

The `1092..1125` cluster strongly suggests a real bug — the code returns the wrong report type on one branch, and the downstream consumer (`.findings` access) doesn't exist on the returned type. WP01's T003 added a regression test capturing today's broken behavior; this WP fixes the bug and updates the test.

### Refactor target shape (per `work/findings/refactor-audit.md`)

```python
def mission_state(...) -> None:
    mode = _validate_modes(audit, fix, teamspace_dry_run)
    fail_on_severity, fail_on_teamspace_blocker = _resolve_fail_on(fail_on)
    audit_root = _resolve_audit_root(repo_root, fixture_dir, include_fixtures)

    if mode == Mode.FIX:
        return _run_repair(audit_root, mission, manifest_path, allow_dirty, json_output)
    if mode == Mode.TEAMSPACE_DRY_RUN:
        return _run_teamspace_dry_run(audit_root, mission, json_output)
    return _run_audit(audit_root, mission, fail_on_severity, fail_on_teamspace_blocker, json_output)
```

Each `_run_*` helper takes its required inputs and emits via the shared `_emit(report_like, json_output, pretty_renderer)`.

## Doctrine Citations

This WP applies:

- [`tdd-red-green-refactor`](../../../src/doctrine/tactics/shipped/testing/tdd-red-green-refactor.tactic.yaml) — characterization tests precede refactor (NFR-003).
- [`refactoring-extract-first-order-concept`](../../../src/doctrine/tactics/shipped/refactoring/refactoring-extract-first-order-concept.tactic.yaml) — per-mode runner + shared `_emit` extraction.
- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — tests assert exit codes + emitted artifacts, not internal calls.

## Branch Strategy

- Planning / base branch: `fix/quality-check-updates`.
- Final merge target: `fix/quality-check-updates`.

## Subtasks

### T029 — Characterization tests for the three modes (commit BEFORE refactor)

**Purpose**: Capture today's observable behavior across all three dispatch arms. Tests must remain green through the typing fix AND the refactor.

**Steps**:

1. Create `tests/cli/commands/test_doctor_mission_state.py`.
2. For each mode (`--audit`, `--fix`, `--teamspace-dry-run`), author a Typer `CliRunner`-driven test:
   - Set up a `tmp_path` project with realistic `kitty-specs/` content (use the `tests/_factories/charters/` fixtures or build minimal mission state).
   - Invoke `spec-kitty doctor mission-state <mode-flag> --json`.
   - Snapshot the JSON output and exit code.
3. Cover error cases: invalid `--fail-on` value, conflicting mode flags, missing repo root.
4. **Commit T029 alone** before T030/T031.

**Files**: `tests/cli/commands/test_doctor_mission_state.py` (new, ~250 lines).

**Validation**:

- All characterization tests pass against unchanged `doctor.py`.
- Commit is isolated; the typing fix and refactor land in subsequent commits.

### T030 — Author regression test FIRST, then fix typing errors at 631 + 1092..1125

**Purpose**: Capture the `MissionRepairResult.findings` real-branch bug in a regression test BEFORE fixing it. Then close the residual mypy errors in `doctor.py` (red → green workflow per `tdd-red-green-refactor`).

**Steps**:

1. Read `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/research/doctor-mission-state-1092-bug-evidence.md` (authored by WP01's T003 handoff). It documents the offending branch in `doctor.py:1080..1130` and the observable broken behavior.
2. Author `tests/regressions/test_doctor_missionrepairresult_findings.py`:
   - Reproduce the offending branch via `CliRunner.invoke(... mission_state ...)`.
   - First assertion captures today's broken behavior (crash / wrong output). Test should FAIL after the fix lands — and that failure is the proof the bug is fixed.
   - Mark with a clear docstring: "Bug was: `repair_repo` returned `RepairReport` where `RepoAuditReport` (with `.findings`) was expected. Fix is in this same commit; assertions reflect post-fix behavior."
3. Determine the correct fix:
   - If `repair_repo`'s return type should be `RepoAuditReport` (with `.findings`), update the call site to use the right type.
   - If the callsite should branch on the report type and access different attributes, refactor the callsite.
   - If the access path is wrong (e.g. should access `.changes` not `.findings`), correct the access.
4. Update the regression test's assertions to reflect post-fix behavior. The test now passes against the fixed code.
5. Fix `doctor.py:631` — remove the unused `type: ignore` and address the `attr-defined` on `.entries`.
6. Confirm `uv run mypy --strict src/specify_cli/cli/commands/doctor.py` exits 0.

**Files**:

- `src/specify_cli/cli/commands/doctor.py` (modified, focused on lines 631 + 1080..1130).
- `tests/regressions/test_doctor_missionrepairresult_findings.py` (new — authored as part of this WP).

**Validation**:

- mypy strict on doctor.py exits 0.
- T029 characterization tests still pass.
- The regression test asserts the post-fix behavior; its docstring records the pre-fix / post-fix delta.

### T031 — Extract `_validate_modes`, `_resolve_fail_on`, `_resolve_audit_root` helpers

**Purpose**: Apply `refactoring-extract-first-order-concept` to the option-validation block at the top of `mission_state`.

**Steps**:

1. Author `_validate_modes(audit, fix, teamspace_dry_run) -> Mode`:
   - Returns an `enum.Enum` (`Mode.AUDIT`, `Mode.FIX`, `Mode.TEAMSPACE_DRY_RUN`).
   - Raises `typer.Exit(2)` on conflicting / missing modes; preserves current error messages.
2. Author `_resolve_fail_on(fail_on: str | None) -> tuple[Severity | None, bool]`:
   - Returns `(severity, teamspace_blocker_flag)`.
   - Preserves current `Invalid --fail-on value` error message.
3. Author `_resolve_audit_root(repo_root, fixture_dir, include_fixtures) -> Path`:
   - Returns the resolved audit root, handling `--include-fixtures` and `--fixture-dir` interplay.
   - Preserves current error messages.
4. Update `mission_state` body to call these helpers.
5. Re-run T029 characterization tests — must remain green.

**Files**: `src/specify_cli/cli/commands/doctor.py` (modified).

**Validation**:

- Each helper has cognitive complexity ≤ 5.
- T029 tests still pass.

### T032 — Extract per-mode runners (`_run_repair`, `_run_teamspace_dry_run`, `_run_audit`)

**Purpose**: Apply `refactoring-extract-first-order-concept` to the three dispatch arms.

**Steps**:

1. Extract each dispatch arm into a standalone function:
   - `_run_repair(audit_root, mission, manifest_path, allow_dirty, json_output) -> int` — returns exit code; calls `repair_repo`; emits via `_emit` (T033).
   - `_run_teamspace_dry_run(audit_root, mission, json_output) -> int`.
   - `_run_audit(audit_root, mission, fail_on_severity, fail_on_teamspace_blocker, json_output) -> int`.
2. Each runner ≤ 30 lines, cognitive complexity ≤ 10.
3. Update `mission_state` body to call the runner matching the resolved Mode.
4. Re-run T029 — must remain green.

**Files**: `src/specify_cli/cli/commands/doctor.py` (modified).

**Validation**:

- Each runner has cognitive complexity ≤ 10.
- T029 tests still pass.

### T033 — Extract shared `_emit` helper for JSON-vs-pretty pattern

**Purpose**: Address the logical duplication of the `if json_output: dump JSON else: pretty-print` pattern across the three runners.

**Steps**:

1. Author `_emit(report, *, json_output, pretty_renderer)`:
   - If `json_output`, calls `report.to_json()` (or equivalent) and writes to stdout.
   - Else, calls `pretty_renderer(report)` which renders to the global `console`.
2. Update each `_run_*` runner to call `_emit` with the appropriate `pretty_renderer` callable.
3. The `pretty_renderer` is a small closure or local function per runner; do not over-generalize.
4. Re-run T029 — must remain green.

**Files**: `src/specify_cli/cli/commands/doctor.py` (modified).

**Validation**:

- Three call sites of the JSON-vs-pretty pattern collapse to three `_emit(...)` calls with distinct renderers.
- T029 tests still pass.

### T034 — Slim `mission_state` to ~30-line orchestrator + glossary fragment

**Purpose**: Final shape of the refactor — `mission_state` becomes a thin orchestrator.

**Steps**:

1. Confirm `mission_state` is now:
   ```python
   def mission_state(...) -> None:
       mode = _validate_modes(audit, fix, teamspace_dry_run)
       fail_on_severity, fail_on_teamspace_blocker = _resolve_fail_on(fail_on)
       audit_root = _resolve_audit_root(repo_root, fixture_dir, include_fixtures)
       runner = {
           Mode.FIX: _run_repair,
           Mode.TEAMSPACE_DRY_RUN: _run_teamspace_dry_run,
           Mode.AUDIT: _run_audit,
       }[mode]
       runner(audit_root, mission, json_output, ...)  # args per runner
   ```
2. Confirm cognitive complexity of `mission_state` ≤ 10 per Sonar.
3. Author `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP06.md`:
   - **`structural debt`**: "A function's cognitive complexity has accumulated beyond reviewable bounds AND the responsibilities mixed inside the body are independent. Refactor candidate per the `refactoring-extract-first-order-concept` and `refactoring-extract-class-by-responsibility-split` tactics. Distinguished from deliberate linearity by the absence of a documented design intent." Confidence 0.9. Status active.
   - **`deliberate linearity`**: "A function whose body is intentionally kept long-and-linear (rather than extracted into helpers) for traceability against a documented contract, code-review map, or output-section sequence. Such functions are NOT refactor candidates regardless of Sonar S3776 score. Identified by an explicit code comment justifying the structure. Example: `src/specify_cli/cli/commands/_auth_doctor.py::render_report`." Confidence 0.95. Status active.
4. Stage and commit.

**Files**:

- `src/specify_cli/cli/commands/doctor.py` (final form).
- `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP06.md` (new).

**Validation**:

- `mission_state` cognitive complexity ≤ 10.
- Every extracted helper has complexity ≤ 10.
- T029 tests still pass.
- mypy strict on doctor.py exits 0.
- Glossary fragment exists.

## Test Strategy

- **Characterization tests (T029)** anchor every subsequent commit's behavior preservation.
- **Updated regression test (T030)** locks the post-fix behavior of the `MissionRepairResult.findings` bug.
- **No new behavior tests beyond the characterization corpus** — the refactor is behavior-preserving by design.

## Definition of Done

- [ ] T029 characterization-tests commit precedes all subsequent commits in this WP (`git log --oneline -- src/specify_cli/cli/commands/doctor.py tests/cli/commands/test_doctor_mission_state.py`).
- [ ] T030 regression-test commit lands FIRST in the typing-fix sequence (test fails on pre-fix code; passes on post-fix code).
- [ ] mypy strict on `doctor.py` exits 0.
- [ ] `mission_state` cognitive complexity ≤ 10 per Sonar.
- [ ] Every extracted helper (`_validate_modes`, `_resolve_fail_on`, `_resolve_audit_root`, `_run_repair`, `_run_teamspace_dry_run`, `_run_audit`, `_emit`) has cognitive complexity ≤ 10.
- [ ] T029 characterization tests pass after every commit.
- [ ] `tests/regressions/test_doctor_missionrepairresult_findings.py` asserts post-fix behavior with a docstring recording the pre-fix / post-fix delta.
- [ ] `glossary-fragments/WP06.md` carries "structural debt" and "deliberate linearity" entries.

## Risks

- **The `MissionRepairResult.findings` bug fix has a non-trivial blast radius** (e.g. `repair_repo` returns the wrong type because of an upstream contract issue). If the fix crosses owned_files, escalate to the operator; do not let scope expand.
- **The characterization corpus misses an edge case**. The refactor passes T029 but the user hits a regression. Mitigation: include at least one fixture per error path (`--fail-on` invalid, conflicting modes, fixture-dir-not-found, etc.).
- **Sonar S3776 score on `mission_state` stays > 15.** The decomposition should bring it well below 15; if not, revisit the helper boundaries.

## Reviewer Guidance

When reviewing this WP, check:

1. T029 commit precedes the typing-fix and refactor commits in `git log`. Reject if order is wrong (NFR-003).
2. The `MissionRepairResult.findings` bug fix is minimal and local; if it cascades to multiple files, push back on scope.
3. The extracted helpers have descriptive names and single responsibilities.
4. The `_emit` helper is small and does not over-generalize.
5. No other `doctor.py` subcommands were modified — locality of change.
6. Updated regression test docstring records the pre-fix / post-fix delta.

## Implementation command

```bash
spec-kitty agent action implement WP06 --agent claude
```

## Activity Log

- 2026-05-14T10:02:00Z – claude:sonnet:python-pedro:implementer – shell_pid=1141012 – Started implementation via action command
- 2026-05-14T10:14:50Z – claude:sonnet:python-pedro:implementer – shell_pid=1141012 – Ready: doctor.py mission_state refactored from CC57 to CC3 thin orchestrator + per-mode runners + shared _emit helper. _print_overdue_details type annotation fixed (ShimRegistryReport, no type:ignore). mypy strict on doctor.py = 0 errors (closes WP01 carve-out). T029 characterization tests (17) pass through all refactor commits. T030 regression (5 tests) locks post-fix behavior. Cites tdd-red-green-refactor, refactoring-extract-first-order-concept, function-over-form-testing. Glossary: structural debt + deliberate linearity on planning branch.
- 2026-05-14T10:16:23Z – claude:opus:reviewer-renata:reviewer – shell_pid=1147001 – Started review via action command
- 2026-05-14T10:20:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=1147001 – Approved: doctor.py mission_state CC57→3 (radon verified); 10 extracted helpers all CC≤9 (radon: _audit_fail_gate=9, _validate_modes=7, _resolve_audit_root=7, _run_audit_mode=6, _run_mission_repair=5, _resolve_fail_on=5, _print_overdue_details=4, _run_teamspace_dry_run_mode=4, _emit_mission_state=2, _emit_json_error=1); mypy strict on doctor.py 0 errors + full repo mypy strict 0 errors across 764 source files → FR-001 (mission-wide) now satisfied; T029 characterization-tests commit (75aad0b98, 502 insertions tests-only) precedes T030 bug-fix commit (fecc5ce5a) and T031-T033 refactor commit (cf9d5eb9c) — NFR-003 verified; T030 fixed _print_overdue_details line 631 (one of TWO bugs WP01's evidence documented — the other being the report=RepairReport|RepoAuditReport variable-aliasing at lines 1080-1130, resolved via T031-T033 Option-B extract per WP01's own recommendation); 22 tests green (17 characterization + 5 regression); function-over-form audit clean (zero mock-internal asserts, one tolerable call_count>=1 smoke assertion in regression test); locality respected — no _auth_doctor.render_report changes per C-003 (WP06 scope: only doctor.py + 2 new test files, 942 insertions); doctrine citations correct on every commit; glossary fragment with 'structural debt' (conf 0.9) + 'deliberate linearity' (conf 0.95), both active, both citing canonical _auth_doctor example and the refactoring tactics.
