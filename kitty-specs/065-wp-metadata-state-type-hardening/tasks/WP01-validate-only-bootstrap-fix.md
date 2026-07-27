---
work_package_id: WP01
title: Validate-Only Bootstrap Fix (#417)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
planning_base_branch: feature/metadata-state-type-hardening
merge_target_branch: feature/metadata-state-type-hardening
branch_strategy: Planning artifacts for this feature were generated on feature/metadata-state-type-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/metadata-state-type-hardening unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-065-wp-metadata-state-type-hardening
base_commit: 24e13e54a346c3eb2e3747e0a5b2bfe520446e0f
created_at: '2026-04-06T07:01:50.840525+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Bug Fix & Foundation
assignee: ''
agent: "codex"
shell_pid: "347031"
history:
- at: '2026-04-06T05:37:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-implementer
authoritative_surface: src/specify_cli/cli/commands/agent/feature.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/cli/commands/agent/feature.py
task_type: implement
---

# Work Package Prompt: WP01 – Validate-Only Bootstrap Fix (#417)

## IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

- **Review status**: Returned to `planned` during Codex review on `2026-04-06T08:43:29Z`
- **Blocking finding**: `spec-kitty agent tasks finalize-tasks --validate-only --json` still emits a top-level `bootstrap` object, so the dry-run JSON contract is not enforced consistently across the `finalize-tasks` surfaces touched by this WP.
- **Evidence**:
  - `src/specify_cli/cli/commands/agent/tasks.py:1655-1666` always populates `result["bootstrap"]` even when `validate_only=True`.
  - `tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py:153-180` only checks that dry-run passes `dry_run=True`; it does not assert the FR-002 JSON shape.
  - `tests/specify_cli/cli/commands/agent/test_feature_finalize_bootstrap.py:260-305` already enforces the mission-surface contract: no top-level `bootstrap` key in validate-only mode, with dry-run stats under `validation.bootstrap_preview`.
- **Required remediation**:
  1. Align `src/specify_cli/cli/commands/agent/tasks.py` with the validate-only JSON contract already used by `src/specify_cli/cli/commands/agent/feature.py`.
  2. Add a regression test on the `agent tasks finalize-tasks` surface that fails if validate-only JSON includes a top-level `bootstrap` key.
  3. Re-run the targeted finalize-tasks tests after the fix.
- **Downstream note**: `WP02`, `WP03`, and `WP05` depend on `WP01`. If the rework lands in the shared lane branch, notify those agents to rebase.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- **Objective**: Fix the `--validate-only` flag contract violation where `finalize-tasks --validate-only` silently rewrites WP frontmatter before the dry-run fork.
- **SC-001**: `finalize-tasks --validate-only` produces zero bytes of `git diff` output against any mission directory in a clean working tree.
- **SC-002**: A developer documentation artifact accurately lists every frontmatter field that the bootstrap step can write or overwrite (verified by code review against the implementation).
- **FR-002**: When `--validate-only --json` is used, the JSON output must not contain a `bootstrap` key reporting mutations.

## Context & Constraints

- **Upstream issue**: #417 — `finalize-tasks --validate-only` mutates WP frontmatter (flag contract violation)
- **Spec**: `kitty-specs/065-wp-metadata-state-type-hardening/spec.md` (User Story 1, User Story 2)
- **Research**: `kitty-specs/065-wp-metadata-state-type-hardening/research.md` (Finding 1 — Bootstrap Mutation Surface)
- **Plan**: `kitty-specs/065-wp-metadata-state-type-hardening/plan.md` (WP01 section)
- **Root cause**: The frontmatter writing loop (`feature.py:1537–1622`) runs before the `validate_only` branch at line 1676. The flag currently only suppresses `bootstrap_canonical_state()` writes and the final commit — not the frontmatter writes.
- **Constraint**: This is a correctness bug. Zero tolerance for partial fixes.

**Doctrine**:
- `test-first-bug-fixing.procedure.yaml` — understand bug → choose test level → write failing test → verify fails for right reason → fix → full suite → commit together
- `acceptance-test-first.tactic.yaml` — spec acceptance scenarios drive test
- `refactoring.procedure.yaml` — identify smell, apply targeted fix
- `change-apply-smallest-viable-diff.tactic.yaml`

**Cross-cutting**:
- **Self Observation Protocol** (NFR-009): Write observation log to `work/observations/065-wp01-<agent>-<date>.md` at session end.
- **Quality Gate** (DIRECTIVE_030): Tests + type checks must pass before `for_review`.

## Branch Strategy

- **Implementation command**: `spec-kitty implement WP01`
- **Planning base branch**: `feature/metadata-state-type-hardening`
- **Merge target branch**: `feature/metadata-state-type-hardening`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T001 – Write failing test for validate-only frontmatter mutation

- **Purpose**: Prove the bug exists before fixing it (test-first-bug-fixing procedure). The test must fail on current `main` and pass after the fix.
- **Steps**:
  1. Locate the existing finalize-tasks test module. Search for test files covering `finalize_tasks` or `finalize-tasks`:
     ```bash
     rg -l "finalize.tasks" tests/
     ```
  2. Create or extend a test that:
     - Sets up a mission directory with WP files containing manually edited frontmatter (e.g., `dependencies: [WP01, WP02]`)
     - Calls `finalize_tasks()` with `validate_only=True`
     - Asserts that the WP file on disk is byte-for-byte identical after the call (use `pathlib.Path.read_bytes()` before/after comparison)
  3. Also test the `--json` output path:
     - Call with `validate_only=True, json_output=True`
     - Assert the JSON output does NOT contain a `bootstrap` key
  4. Run the test and **verify it fails for the right reason** (frontmatter was modified, or `bootstrap` key present in JSON):
     ```bash
     pytest tests/path/to/test_file.py -x -v -k "validate_only"
     ```
  5. Do NOT fix the bug yet. Commit the failing test separately if the test framework supports marking expected failures, or keep it uncommitted until T002.
- **Files**:
  - `tests/specify_cli/` (locate or create test file for finalize-tasks)
- **Validation**:
  - [ ] Test exists and runs
  - [ ] Test fails on current code (proves the bug)
  - [ ] Test failure message clearly indicates frontmatter was modified

### Subtask T002 – Guard write_frontmatter with not validate_only

- **Purpose**: Apply the minimal fix to the mutation loop so `--validate-only` skips all frontmatter writes.
- **Steps**:
  1. Open `src/specify_cli/cli/commands/agent/feature.py`
  2. Locate the frontmatter writing guard (around line 1620, but verify):
     ```python
     # Current (broken):
     if frontmatter_changed:
         write_frontmatter(wp_file, frontmatter, body)
         updated_count += 1
     ```
  3. Add the `not validate_only` guard:
     ```python
     # Fixed:
     if frontmatter_changed and not validate_only:
         write_frontmatter(wp_file, frontmatter, body)
         updated_count += 1
     ```
  4. Verify `validate_only` is in scope at this location (it should be a parameter of the enclosing function). If the parameter name differs, use the correct name.
  5. Check for any OTHER `write_frontmatter()` calls in the same function that may also need guarding. The mutation surface from research.md lists 8 fields — ensure ALL write paths are guarded.
  6. Run the failing test from T001:
     ```bash
     pytest tests/path/to/test_file.py -x -v -k "validate_only"
     ```
  7. Verify the test now **passes**.
  8. Run the full test suite:
     ```bash
     pytest tests/ -x --timeout=60
     ```
- **Files**:
  - `src/specify_cli/cli/commands/agent/feature.py` (~line 1620)
- **Validation**:
  - [ ] T001 test now passes
  - [ ] Full test suite passes
  - [ ] `git diff` is empty after running finalize-tasks with `--validate-only`

### Subtask T003 – Update JSON output contract for validate-only

- **Purpose**: Ensure the `--validate-only --json` output does not misleadingly report bootstrap mutations that didn't happen.
- **Steps**:
  1. In `feature.py`, find where the JSON output dictionary is constructed for `finalize-tasks`
  2. When `validate_only=True`, ensure the output:
     - Does NOT contain a `bootstrap` key (or contains `bootstrap: null` / `bootstrap: {"skipped": true}`)
     - Contains a `validation` key with the validation report
  3. If bootstrap stats are currently unconditionally added to the JSON, wrap them in `if not validate_only:`
  4. Write or update a test that verifies the JSON output structure for `--validate-only`:
     ```python
     result = finalize_tasks(..., validate_only=True, json_output=True)
     assert "bootstrap" not in result  # or assert result["bootstrap"]["skipped"] == True
     assert "validation" in result
     ```
  5. Run tests:
     ```bash
     pytest tests/ -x -v -k "validate_only and json"
     ```
- **Files**:
  - `src/specify_cli/cli/commands/agent/feature.py`
  - Test file from T001
- **Validation**:
  - [ ] JSON output for `--validate-only` has no `bootstrap` mutations key
  - [ ] JSON output for normal mode still has `bootstrap` key (regression check)

### Subtask T004 – Document bootstrap mutation surface

- **Purpose**: Satisfy FR-003 and SC-002 — provide a developer-facing reference of all frontmatter fields that bootstrap can write.
- **Steps**:
  1. Create or update a developer note documenting the mutation surface. This can be:
     - A code comment block at the top of the `finalize_tasks()` function, OR
     - A section in `kitty-specs/065-wp-metadata-state-type-hardening/research.md` (already has Finding 1)
  2. The document must list all 8 fields with:

     | Field | Source | Condition |
     |-------|--------|-----------|
     | `dependencies` | Parsed from `tasks.md` | Written if absent or differs |
     | `planning_base_branch` | `_resolve_planning_branch()` | Written if differs |
     | `merge_target_branch` | Same as `target_branch` | Written if differs |
     | `branch_strategy` | Computed long-form string | Written if differs |
     | `requirement_refs` | Parsed from WP files and `tasks.md` | Written if absent or differs |
     | `execution_mode` | Inferred by `infer_ownership()` | Written only if absent |
     | `owned_files` | Inferred by `infer_ownership()` | Written only if absent |
     | `authoritative_surface` | Inferred by `infer_ownership()` | Written only if absent |

  3. Verify against the actual code that this list is complete and accurate. If any field is missing, add it.
  4. Add a brief note explaining that `--validate-only` now skips all these writes (referencing the fix in T002).
- **Files**:
  - `src/specify_cli/cli/commands/agent/feature.py` (code comment) OR
  - Developer documentation location (code comment preferred for proximity to the code)
- **Validation**:
  - [ ] All 8 fields listed with source and condition
  - [ ] Verified against actual code
  - [ ] `--validate-only` skip behavior noted

## Definition of Done

- [ ] Failing test written BEFORE fix (T001)
- [ ] `write_frontmatter()` guarded with `not validate_only` (T002)
- [ ] JSON output contract updated for `--validate-only` (T003)
- [ ] Bootstrap mutation surface documented (T004)
- [ ] Full test suite passes with zero regressions
- [ ] `git diff` is empty after `--validate-only` against any mission
- [ ] Type checks pass (`mypy` or project type checker)

## Risks & Mitigations

- **Risk**: Line numbers in research.md may have shifted since the research was done. **Mitigation**: Use `rg` to search for `write_frontmatter` calls rather than relying on line numbers.
- **Risk**: There may be additional `write_frontmatter()` call sites not covered by Finding 1. **Mitigation**: Search all call sites in `feature.py` with `rg "write_frontmatter" src/specify_cli/cli/commands/agent/feature.py`.

## Review Guidance

- Verify that ALL `write_frontmatter()` calls in `finalize_tasks()` are guarded, not just the one at line 1620.
- Check that the JSON output test covers both `--validate-only` (no bootstrap key) and normal mode (bootstrap key present).
- Confirm the mutation surface document matches the current code, not just the research.md snapshot.

## Activity Log

- 2026-04-06T05:37:00Z – system – Prompt created.
- 2026-04-06T07:01:50Z – opencode – shell_pid=152804 – Started implementation via action command
- 2026-04-06T07:15:46Z – opencode – shell_pid=152804 – T001-T004 complete. Tests pass (15 WP01-specific, 3953 fast suite). Type checks clean. Ready for review.
- 2026-04-06T08:20:55Z – codex – shell_pid=226958 – Started review via action command
- 2026-04-06T08:24:13Z – codex – shell_pid=226958 – Moved to planned
- 2026-04-06T08:34:56Z – codex – shell_pid=226958 – Rework complete: in-memory frontmatter snapshots for validate-only ownership validation. Regression tests added. 8090 tests pass, no new type errors.
- 2026-04-06T08:37:08Z – codex – shell_pid=347031 – Started review via action command
- 2026-04-06T08:43:29Z – codex – shell_pid=347031 – Moved to planned
- 2026-04-06T08:43:29Z – codex – shell_pid=347031 – Review feedback recorded: `agent tasks finalize-tasks --validate-only --json` still exposes a top-level `bootstrap` key on the tasks surface; add the matching contract fix and regression test there before returning to review.
- 2026-04-06T08:53:18Z – opencode – shell_pid=152804 – Started implementation via action command
- 2026-04-06T09:00:55Z – opencode – shell_pid=152804 – Third rework: aligned tasks.py validate-only JSON with FR-002 contract (no top-level bootstrap key), added regression test, all 8568 tests pass
- 2026-04-06T09:02:43Z – codex – shell_pid=347031 – Started review via action command
- 2026-04-06T09:03:15Z – codex – shell_pid=347031 – Review passed: validate-only JSON contract aligned across mission/tasks finalize-tasks surfaces; targeted regression tests pass
