---
work_package_id: WP08
title: Stale-lane auto-rebase classifier + orchestrator + ADR
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-013
planning_base_branch: fix/quality-check-updates
merge_target_branch: fix/quality-check-updates
branch_strategy: Planning artifacts for this mission were generated on fix/quality-check-updates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/quality-check-updates unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
- T044
- T045
- T046
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "26556"
history:
- at: '2026-05-14'
  actor: planner
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
execution_mode: code_change
mission_id: 01KRJGKH4DJCSF277K9QV3WBE7
mission_slug: quality-devex-hardening-3-2-01KRJGKH
owned_files:
- architecture/2.x/adr/2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md
- src/specify_cli/merge/conflict_classifier.py
- src/specify_cli/merge/conflict_resolver.py
- src/specify_cli/lanes/auto_rebase.py
- src/specify_cli/lanes/merge.py
- tests/integration/merge/test_conflict_classifier.py
- tests/integration/lanes/test_auto_rebase_additive.py
- kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP08.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Implement the stale-lane auto-rebase classifier and orchestrator per the ADR draft in `contracts/stale-lane-auto-rebase-classifier-policy.md`. The mission's constraint C-007 requires the ADR to be promoted to canonical status (`architecture/2.x/adr/2026-05-14-1-...`) with operator approval BEFORE implementation begins.

The classifier defaults to **fail-safe** (`Manual` for any unmatched file pattern; NFR-005). The orchestrator integrates into `spec-kitty merge` to attempt `git merge <mission-branch>` inside a stale lane worktree before halting; it auto-resolves additive-only conflicts (pyproject deps, `__init__.py` import-block additions, `urls.py` URL lists), regenerates `uv.lock` under a global file lock, and reports auto-resolved vs manual lanes.

## Context

### Current code (read before designing)

`src/specify_cli/lanes/merge.py:108-118`:

```python
stale = check_lane_staleness(lane, branch, mission_branch, repo_root)
if stale.is_stale:
    return LaneMergeResult(
        success=False, lane_id=lane_id, merged_into=mission_branch,
        errors=[
            f"Lane {lane_id} is stale: overlapping files {stale.stale_files}. "
            f"{stale.remediation}"
        ],
        stale_check=stale,
    )
```

Fails fast. No auto-rebase, no union-merge driver. Tests at `tests/lanes/test_merge.py`, `tests/lanes/test_stale_check.py` assert this contract.

### ADR draft (already authored)

`contracts/stale-lane-auto-rebase-classifier-policy.md` enumerates five rules:

1. **R-PYPROJECT-DEPS-UNION** — pyproject dependency-array union merge.
2. **R-INIT-IMPORTS-UNION** — `__init__.py` import-block union + ruff fix.
3. **R-URLS-LIST-UNION** — list-of-strings constants union.
4. **R-UVLOCK-REGENERATE** — special-cased; regenerate `uv.lock` under file lock.
5. **R-DEFAULT-MANUAL** — fail-safe default; always last.

### Data model (already authored)

`data-model.md` §3 defines `ConflictClassification`, `Resolution = Auto(merged_text, rule_id) | Manual(reason)`, `AutoRebaseReport`.

## Doctrine Citations

This WP applies:

- ADR-led design — architectural decision recorded before implementation.
- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — every test.
- [`secure-design-checklist`](../../../src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml) — for the `uv lock` regeneration boundary (operates on the lockfile under a global mutex).

## Branch Strategy

- Planning / base branch: `fix/quality-check-updates`.
- Final merge target: `fix/quality-check-updates`.

## Subtasks

### T040 — Promote ADR draft to canonical status (operator approval gate — HALT)

**Purpose**: Constraint C-007 — the ADR MUST land before implementation begins. The three open questions in the draft require operator decisions; the implementer cannot resolve them unilaterally.

**Steps**:

1. Read `contracts/stale-lane-auto-rebase-classifier-policy.md`. The bottom of that file lists three open questions for the operator:
   - Auto-rebase commit message format (proposed: include `lane=<id>`).
   - `ruff --fix --select I001` scope (proposed: keep minimal; add more rules only on operator request).
   - `R-URLS-LIST-UNION` sort-convention detection (proposed: sample unmodified prefix).
2. **HALT** the WP and surface these three questions to the operator via the implement-review review cycle. Each question has a Pedro recommendation in the draft — the operator either accepts the recommendation or directs a different resolution.
3. Once the operator has resolved all three questions (recorded as decision moments or as direct chat answers captured in the WP review record), create `architecture/2.x/adr/2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md` with:
   - Frontmatter status `ACCEPTED`.
   - Body lifted from the contracts draft, with the resolved questions inlined.
   - Cross-link back to the contracts draft for historical traceability.
4. Only then proceed to T041.

**Halt behavior**: if the operator approval has not been recorded, the implement-review loop should reject the WP for review and surface the three questions. **Do NOT improvise resolutions** — the ADR is the governance artifact for a behavior change in `spec-kitty merge`; unilateral resolution would violate the locality-of-change directive.

**Files**: `architecture/2.x/adr/2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md` (new, ~250 lines, written only after operator approval).

**Validation**:

- ADR exists at the canonical path with status ACCEPTED.
- The three open questions are resolved inline with operator-confirmed answers.
- Contracts draft is updated to cite the ADR as the canonical reference.

### T041 — Implement `src/specify_cli/merge/conflict_classifier.py`

**Purpose**: Encode the ADR's five rules as pure functions returning `ConflictClassification`.

**Steps**:

1. Create `src/specify_cli/merge/conflict_classifier.py` per `data-model.md` §3:
   - Define `Auto` and `Manual` dataclasses; `Resolution` union.
   - Define `ConflictClassification` dataclass.
   - Define each rule as a pure function `(file_path, hunk_text) -> ConflictClassification | None` where `None` means "rule doesn't match, try next".
     - `r_pyproject_deps_union(file_path, hunk_text)` — match on `pyproject.toml` AND `[project.dependencies]` array shape; emit `Auto(union_text, rule_id="R-PYPROJECT-DEPS-UNION")`.
     - `r_init_imports_union(...)` — match on `__init__.py` import-block additions.
     - `r_urls_list_union(...)` — match on `urls.py` list-of-strings additions.
     - `r_uvlock_regenerate(...)` — match on `uv.lock`; emit a special sentinel that the orchestrator treats as "regenerate, not merge".
     - `r_default_manual(...)` — always returns `Manual("no classifier rule matched <file_path>")`.
   - Wrap each rule body in `try/except: return Manual(reason="rule raised: <exc>")` per NFR-005 fail-safe.
2. Define `classify(file_path, hunk_text) -> ConflictClassification`:
   - Iterate rules in declared order.
   - Return the first non-`None` result.
3. Add post-resolution validation hook (`Auto` outputs are validated by `tomllib.loads` for TOML files; `ast.parse` for Python files; revert to `Manual` on failure).

**Files**: `src/specify_cli/merge/conflict_classifier.py` (new, ~250 lines).

**Validation**:

- Module imports cleanly.
- `mypy --strict` passes.
- Every rule's body is wrapped in `try/except`.

### T042 — [P] Per-rule unit tests in `tests/integration/merge/test_conflict_classifier.py`

**Purpose**: Lock each rule's behavior with parametrized happy + counter-example cases per ADR §Examples.

**Steps**:

1. Create `tests/integration/merge/test_conflict_classifier.py`.
2. For each rule, author parametrized tests with `(file_path, hunk_text, expected_resolution)` triples:
   - **R-PYPROJECT-DEPS-UNION** happy: two sides add distinct deps → `Auto(merged_with_both_deps_sorted)`.
   - **R-PYPROJECT-DEPS-UNION** counter: same-package version-specifier conflict → falls through to `R-DEFAULT-MANUAL`.
   - **R-INIT-IMPORTS-UNION** happy: two sides add distinct imports → `Auto(merged_imports, ruff-sorted)`.
   - **R-INIT-IMPORTS-UNION** counter: one side renames an existing import → `Manual`.
   - **R-URLS-LIST-UNION** happy: distinct entries → `Auto(union)`.
   - **R-URLS-LIST-UNION** counter: same-entry modification → `Manual`.
   - **R-DEFAULT-MANUAL** smoke: a path no rule covers → `Manual`.
3. Add validation tests: an `Auto` output whose `merged_text` fails `tomllib.loads` triggers fallback to `Manual`.

**Files**: `tests/integration/merge/test_conflict_classifier.py` (new, ~300 lines).

**Validation**:

- All tests pass.
- Each rule has ≥ 1 happy + ≥ 1 counter-example case.

### T043 — Implement `src/specify_cli/lanes/auto_rebase.py` orchestrator

**Purpose**: Drive the auto-rebase pipeline — attempt `git merge`, classify conflicts, apply auto-resolutions, regenerate `uv.lock` under file lock, report.

**Steps**:

1. Create `src/specify_cli/lanes/auto_rebase.py` with `attempt_auto_rebase(lane, branch, mission_branch, repo_root, worktree_path) -> AutoRebaseReport`:
   - Step 1: Run `git merge <mission-branch>` inside `worktree_path` via `subprocess.run`.
   - Step 2: If clean (exit 0, no conflicts), return `AutoRebaseReport(succeeded=True, classifications=())`.
   - Step 3: If conflicts, parse each conflicted file:
     - Read the file; split by `<<<<<<<` / `=======` / `>>>>>>>` markers; classify each conflict region with `conflict_classifier.classify(...)`.
     - If all classifications are `Auto`, apply them (write merged_text); stage the file.
     - If any classification is `Manual`, run `git merge --abort` and return `AutoRebaseReport(succeeded=False, halt_reason=<first manual.reason>)`.
   - Step 4: If `uv.lock` was conflicted, hold `specify_cli.core.file_lock` and run `uv lock --no-upgrade`. On non-zero exit, abort and report.
   - Step 5: If any `__init__.py` was modified, run `ruff --fix --select I001 <file>`. Treat ruff failure as fallback to `Manual`.
   - Step 6: Create the merge commit with message `auto-rebase: <N> conflicts resolved by classifier rules [<rule_ids>]` (per ADR §Operator-visible-behavior).

**Files**: `src/specify_cli/lanes/auto_rebase.py` (new, ~300 lines).

**Validation**:

- Module imports cleanly.
- `mypy --strict` passes.

### T044 — Integration test for two-lane additive merge

**Purpose**: End-to-end test of the happy path (per quickstart §5).

**Steps**:

1. Create `tests/integration/lanes/test_auto_rebase_additive.py`.
2. Set up `tmp_path` with a minimal repo, two lane worktrees, and a mission branch.
3. Each lane adds a distinct dependency to `pyproject.toml`. Lane A merges into the mission branch first.
4. Lane B is now stale. Invoke `auto_rebase.attempt_auto_rebase(...)`.
5. Assert:
   - The returned `AutoRebaseReport.succeeded` is `True`.
   - `pyproject.toml` in the lane B worktree contains both dependencies.
   - `uv.lock` was regenerated.
   - The lane branch carries a merge commit with the expected message format.

**Files**: `tests/integration/lanes/test_auto_rebase_additive.py` (new, ~200 lines).

**Validation**:

- Test passes.
- No partial state leaks if any assertion fails.

### T045 — Negative integration test for semantic conflict

**Purpose**: Verify the fail-safe halt path.

**Steps**:

1. Extend the test file with a scenario where lane A and lane B both modify the same function body in `flags.py` (or similar).
2. Invoke `auto_rebase.attempt_auto_rebase(...)`.
3. Assert:
   - `AutoRebaseReport.succeeded` is `False`.
   - `halt_reason` cites `R-DEFAULT-MANUAL` (the classifier did not match any auto-resolve rule).
   - The lane B worktree state is reverted (no partial auto-resolution leaks).
   - The original `lanes/merge.py` actionable error message is preserved at the caller boundary.

**Files**: same test file (extend, ~80 additional lines).

**Validation**:

- Test passes.
- Lane B worktree is clean after the failed attempt (`git status` shows no conflicts in flight).

### T046 — Update `lanes/merge.py` to delegate; glossary fragment

**Purpose**: Wire the orchestrator into the existing merge path.

**Steps**:

1. Update `src/specify_cli/lanes/merge.py:108-118`:
   ```python
   if stale.is_stale:
       from specify_cli.lanes.auto_rebase import attempt_auto_rebase
       report = attempt_auto_rebase(lane, branch, mission_branch, repo_root, worktree_path)
       if report.succeeded:
           # continue outer merge pipeline as if lane had been merged cleanly
           ...
       else:
           # preserve current actionable error message
           return LaneMergeResult(
               success=False, lane_id=lane_id, merged_into=mission_branch,
               errors=[
                   f"Lane {lane_id} is stale: overlapping files {stale.stale_files}. "
                   f"{stale.remediation}"
               ],
               stale_check=stale,
           )
   ```
2. Ensure existing tests at `tests/lanes/test_merge.py` and `tests/lanes/test_stale_check.py` still pass — they assert the halt path, which remains intact when auto-rebase fails.
3. Author `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP08.md`:
   - WP08 reinforces "fail-safe default" via the ADR; document as: `# WP08 introduces no new canonical terms; reinforces fail-safe-default behavior in the auto-rebase classifier per ADR 2026-05-14-1.`

**Files**:

- `src/specify_cli/lanes/merge.py` (modified).
- `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP08.md` (new).

**Validation**:

- Existing `tests/lanes/*` tests pass.
- New T044/T045 tests pass.

## Test Strategy

- **Per-rule unit tests (T042)** lock each classifier rule.
- **Two-lane additive integration test (T044)** is the happy-path smoke per quickstart §5.
- **Semantic-conflict negative test (T045)** verifies the fail-safe halt.
- **Existing `tests/lanes/*` tests** must remain green — the halt-on-Manual path is the existing contract.

## Definition of Done

- [ ] ADR exists at `architecture/2.x/adr/2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md` with status ACCEPTED.
- [ ] `src/specify_cli/merge/conflict_classifier.py` implements the five rules.
- [ ] `src/specify_cli/lanes/auto_rebase.py` orchestrates the auto-rebase pipeline.
- [ ] `src/specify_cli/lanes/merge.py` delegates to `auto_rebase` before halting.
- [ ] All four test files (T042 + T044 + T045 + existing) pass.
- [ ] `mypy --strict` passes on the new modules.
- [ ] `glossary-fragments/WP08.md` exists.

## Risks

- **Operator approval delay on T040** blocks the WP. If the ADR cannot be approved within the WP's window, document the blocker and defer WP08 to a follow-up mission.
- **`git merge` behavior varies across versions**. Test the orchestrator against the supported git versions; pin the version in CI if drift surfaces.
- **`uv lock` regeneration is slow on large lockfiles**. The integration test should use a minimal `pyproject.toml` to keep the test fast.
- **A wrongly-classified semantic conflict silently combines incompatible code**. NFR-005 mitigation: `R-DEFAULT-MANUAL` is always last; classifier `try/except` defaults to `Manual` on rule-evaluation exceptions; post-resolution AST/TOML validation reverts to `Manual` on syntax failure.

## Reviewer Guidance

When reviewing this WP, check:

1. T040 ADR is `ACCEPTED` and the operator approval is recorded in evidence.
2. Every classifier rule is wrapped in `try/except` defaulting to `Manual` (NFR-005).
3. Post-resolution validation (TOML parse + AST parse) is implemented and tested.
4. The orchestrator runs `git merge --abort` on any `Manual` result; no partial state leaks (verified by T045).
5. `uv lock` regeneration holds `specify_cli.core.file_lock` (do not introduce a parallel mutex).
6. Existing `tests/lanes/*` tests still pass — the halt path is preserved when auto-rebase fails.

## Implementation command

```bash
spec-kitty agent action implement WP08 --agent claude
```

## Activity Log

- 2026-05-14T13:15:45Z – claude:sonnet:python-pedro:implementer – shell_pid=18125 – Started implementation via action command
- 2026-05-14T13:28:36Z – claude:sonnet:python-pedro:implementer – shell_pid=18125 – Ready for review: ADR promoted to ACCEPTED with 3 open questions resolved; classifier (5 rules + NFR-005 fail-safe + TOML/AST validation), orchestrator (git merge/classify/splice/uv lock under MachineFileLock/ruff fix/audit commit), lanes/merge.py delegation. 23 classifier unit tests + 2 integration tests (additive + semantic-conflict negative). All 181 existing lane tests pass. mypy --strict clean; ruff clean.
- 2026-05-14T13:29:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=26556 – Started review via action command
- 2026-05-14T13:31:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=26556 – Review passed: ADR ACCEPTED with 3 open questions resolved inline; classifier (5 rules + NFR-005 try/except + TOML/AST validation) and orchestrator (git merge, classify, splice, validate, uv.lock regen under MachineFileLock, ruff fix, commit with lane=<id>) wired live from lanes/merge.py. 25 tests pass (per-rule happy/counter/dispatcher/validation/fail-safe-on-exception + additive happy path + semantic-conflict negative); 181 existing lane tests still pass; mypy --strict clean. Files in lane write_scope; glossary fragment present on planning branch.
