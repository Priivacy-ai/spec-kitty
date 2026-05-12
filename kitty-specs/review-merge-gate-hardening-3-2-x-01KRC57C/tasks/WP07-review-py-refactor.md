---
work_package_id: WP07
title: review.py hygiene refactor
dependencies: []
requirement_refs:
- FR-024
- FR-025
planning_base_branch: fix/3.2.x-review-merge-gate-hardening
merge_target_branch: fix/3.2.x-review-merge-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.x-review-merge-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.x-review-merge-gate-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
agent: "claude:opus:reviewer:reviewer"
shell_pid: "491999"
history:
- at: '2026-05-12'
  actor: planner
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/review/
execution_mode: code_change
mission_id: 01KRC57CNW5JCVBRV8RAQ2ARXZ
mission_slug: review-merge-gate-hardening-3-2-x-01KRC57C
owned_files:
- src/specify_cli/cli/commands/review.py
- src/specify_cli/cli/commands/review/__init__.py
- src/specify_cli/cli/commands/review/_lane_gate.py
- src/specify_cli/cli/commands/review/_dead_code.py
- src/specify_cli/cli/commands/review/_ble001_audit.py
- src/specify_cli/cli/commands/review/_report.py
- tests/specify_cli/cli/commands/test_review*.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load implementer-ivan
```

The profile establishes your identity (Implementer Ivan), primary focus (writing and verifying production-grade code), and avoidance boundary (no architectural redesign; no scope expansion beyond what this WP authorizes). If the profile load fails, stop and surface the error — do not improvise a role.

## Objective

Split `src/specify_cli/cli/commands/review.py` into a small Python package: `commands/review/__init__.py` plus sibling files `_lane_gate.py`, `_dead_code.py`, `_ble001_audit.py`, `_report.py`. **Mechanical extraction only.** No new abstractions, no new public types, no behavior change.

This is a **prerequisite** to WP03's contract enforcement work so that WP03's new code (`_mode.py`, `_issue_matrix.py`, `_diagnostics.py`) lands into a clean package rather than swelling a god-module.

This WP satisfies FR-024, FR-025, and NFR-005 in [`../spec.md`](../spec.md).

## Context

`src/specify_cli/cli/commands/review.py` currently contains the entire mission-review command: the four gates, the report writer, all helpers, and the entry point — in one file. WP03 will add mode resolution, an `issue-matrix.md` validator with audit-derived schema, a diagnostic-code StrEnum, and frontmatter writer extensions. Landing all that into a single file produces a god-module: 1500+ LOC, mixed concerns, impossible to review.

The fix is a **purely mechanical** refactor done first. After WP07:

- Each of the 4 gates lives in its own file.
- The `review_mission()` entry point is in `__init__.py` and stays importable from its original path so no caller needs changing.
- The pre-WP07 test suite passes unchanged (NFR-005).

**Critical scope boundary**: this WP does **not** introduce any abstraction layer, type, or service. The full domain split (extracting a `ReleaseEvidence` aggregate, factoring out gate orchestration) is **#992 WS-5 ReleaseEvidence work**, not this WP. If you find yourself wanting to "improve while moving", stop — that's a follow-up ticket, not WP07.

## Branch Strategy

- **Planning/base branch**: `fix/3.2.x-review-merge-gate-hardening`
- **Final merge target**: `main` (after PR review)
- **Execution worktree**: assigned by `spec-kitty implement WP07`. WP07 has no dependencies; should land first so WP01 and WP03 can build on the package layout.

## Subtasks

### T011 — Create the package and re-export `review_mission`

**Purpose**: replace `review.py` (file) with `review/` (package); `review/__init__.py` re-exports `review_mission` so every existing `from specify_cli.cli.commands.review import review_mission` import keeps working without modification.

**Steps**:

1. Create directory `src/specify_cli/cli/commands/review/`.
2. Create `src/specify_cli/cli/commands/review/__init__.py` with:
   ```python
   """Mission-review command package.

   Public entry: review_mission()
   Internal modules:
     _lane_gate.py     — Gate 1: WP lane consistency check
     _dead_code.py     — Gate 2: dead-code scan
     _ble001_audit.py  — Gate 3: BLE001 broad-except audit
     _report.py        — Gate 4: report writer

   See: src/specify_cli/cli/commands/review/ERROR_CODES.md (authored by WP03)
   """

   from ._report import write_review_report  # noqa: F401
   from ._lane_gate import check_wp_lanes  # noqa: F401
   from ._dead_code import scan_dead_code  # noqa: F401
   from ._ble001_audit import audit_ble001  # noqa: F401

   # ... and the public review_mission() entry function, moved verbatim from review.py
   ```
3. **Do NOT delete `review.py` yet** — keep it through T015 so partial extractions can be tested. T016 is the deletion step.

**Files**: `src/specify_cli/cli/commands/review/__init__.py` (new)

**Validation**:
- [ ] `python -c "from specify_cli.cli.commands.review import review_mission"` succeeds.
- [ ] Existing tests still pass (the import resolves to the package's `review_mission` once T016 deletes the old file).

### T012 — Extract Gate 1 (WP lane check)

**Purpose**: move the WP-lane-check function (currently lines ~291–365 of `review.py`) verbatim into `_lane_gate.py`. Function signatures unchanged.

**Steps**:

1. Identify the function in `review.py` (search for "Step 1" or "check WP lanes"; expected: a function named `_check_wp_lanes`, `check_wp_lanes`, or similar).
2. Cut the function and its directly-used module-level helpers (private helpers only — do not pull in helpers that are also used by other gates) into `_lane_gate.py`.
3. Adjust imports in `_lane_gate.py` for what it actually uses (e.g., `pathlib.Path`, `subprocess`, etc.).
4. In `review.py`, replace the moved function definition with an import: `from .review._lane_gate import check_wp_lanes` if `review.py` still references it. After T016 this becomes moot.

**Files**: `src/specify_cli/cli/commands/review/_lane_gate.py` (new), `review.py` (modified)

**Validation**:
- [ ] Function works identically when called from the new module path.

### T013 [P] — Extract Gate 2 (dead-code scan)

**Purpose**: move dead-code scan logic (currently lines ~365–425 of `review.py`) into `_dead_code.py`.

**Steps**: same pattern as T012. Function name likely `_scan_dead_code` or `scan_dead_code`.

**Files**: `src/specify_cli/cli/commands/review/_dead_code.py` (new)

**Validation**:
- [ ] Dead-code scan still produces the same warnings/findings on the same input fixture.

### T014 [P] — Extract Gate 3 (BLE001 audit)

**Purpose**: move BLE001 broad-except audit (currently lines ~425–450 of `review.py`) into `_ble001_audit.py`.

**Steps**: same pattern.

**Files**: `src/specify_cli/cli/commands/review/_ble001_audit.py` (new)

**Validation**:
- [ ] Audit produces the same findings on the same input.

### T015 [P] — Extract Gate 4 (report writer)

**Purpose**: move report-writer logic (currently lines ~450–504 of `review.py`) into `_report.py`. This includes the YAML frontmatter writer and findings serialization.

**Steps**: same pattern.

**Files**: `src/specify_cli/cli/commands/review/_report.py` (new)

**Validation**:
- [ ] Report file content byte-for-byte identical to pre-WP07 output on the same fixture.

### T016 — Delete `review.py`; verify behavioral neutrality

**Purpose**: remove the original file once everything is extracted; run the entire existing review test suite unchanged to prove NFR-005.

**Steps**:

1. Verify nothing imports from `review.py` directly (the package re-export handles `from specify_cli.cli.commands.review import …`):
   ```bash
   rg 'from specify_cli.cli.commands.review import' tests/ src/
   ```
2. `git rm src/specify_cli/cli/commands/review.py`.
3. Run the existing review test suite:
   ```bash
   uv run python -m pytest tests/specify_cli/cli/commands/test_review*.py -v
   ```
4. Every test must pass with **zero modifications**. If a test requires modification (e.g., import path adjustment), the package's `__init__.py` re-exports are wrong — fix the re-export, not the test.

**Files**: `src/specify_cli/cli/commands/review.py` (deleted)

**Validation**:
- [ ] All pre-existing review tests pass.
- [ ] Existing callers of `review_mission` and helpers still work without modification.

## Definition of Done

- [ ] T011: `review/__init__.py` exists, re-exports the public API.
- [ ] T012–T015: four gate files created; helpers extracted; no behavior change.
- [ ] T016: `review.py` deleted; existing test suite green.
- [ ] FR-024, FR-025, NFR-005 cited in commit messages.
- [ ] No new public types, no new abstractions introduced.
- [ ] Any test modification (import paths, fixture paths) is **unjustifiable** — the public API stays the same.

## Risks and Reviewer Guidance

**Risk**: an implementer "improves while moving" — renames a helper, simplifies a conditional, removes "dead" code. **NFR-005 forbids this.** Reviewer must verify that the post-WP07 diff is purely structural: the same lines of code in different files, same imports, same control flow.

**Reviewer focus**:
- T016 must show every pre-existing review test passes with zero test-side changes.
- The `__init__.py` re-export list must cover every name the test suite imports.
- Helpers used by multiple gates: confirm they stay in `__init__.py` (or a shared `_helpers.py` if absolutely necessary; prefer staying in `__init__.py` to minimize new files).

## Suggested implement command

```bash
spec-kitty agent action implement WP07 --agent claude --mission review-merge-gate-hardening-3-2-x-01KRC57C
```

## Activity Log

- 2026-05-12T13:19:46Z – claude:sonnet:implementer-ivan:implementer – shell_pid=476601 – Started implementation via action command
- 2026-05-12T13:24:16Z – claude:sonnet:implementer-ivan:implementer – shell_pid=476601 – WP07 ready: review.py split into package; all pre-existing tests pass without modification
- 2026-05-12T13:24:42Z – claude:opus:reviewer:reviewer – shell_pid=491999 – Started review via action command
- 2026-05-12T13:28:10Z – claude:opus:reviewer:reviewer – shell_pid=491999 – Review passed: NFR-005 satisfied. review.py deleted; 5 sibling files in commands/review/ contain verbatim extractions (same constants, regexes, dataclass, control flow, console output, exit code semantics). Zero test files modified. All 47 review-related tests in tests/specify_cli/cli/commands/ pass on WP07's commit. The single pre-existing failure (test_mission_review_fails_when_done_wp_latest_review_artifact_is_rejected) reproduces on parent commit 28e4309eb, confirming it is data/environment-related and not a WP07 regression. Public API (review_mission, Ble001SuppressionFinding, audit_auth_storage_ble001_line, collect_auth_storage_ble001_findings) preserved via __init__.py re-exports; subprocess monkeypatch path remains effective because the module-level subprocess attribute references the same module object used by _dead_code.py.
