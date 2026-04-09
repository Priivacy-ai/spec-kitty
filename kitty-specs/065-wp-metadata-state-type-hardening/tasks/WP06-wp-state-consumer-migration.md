---
work_package_id: WP06
title: WPState Consumer Migration — High-Touch Trio (#405)
dependencies: [WP05]
requirement_refs:
- FR-013
- FR-014
- NFR-001
- NFR-006
- C-004
planning_base_branch: feature/metadata-state-type-hardening
merge_target_branch: feature/metadata-state-type-hardening
branch_strategy: Planning artifacts for this feature were generated on feature/metadata-state-type-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/metadata-state-type-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
- T033
phase: Phase 3 - Consumer Migration
assignee: ''
agent: "opencode"
shell_pid: "152804"
history:
- at: '2026-04-06T06:15:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/orchestrator_api/commands.py
execution_mode: code_change
lane: planned
agent_profile: python-implementer
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/next/decision.py
- src/specify_cli/dashboard/scanner.py
- src/specify_cli/tasks_support.py
- src/specify_cli/scripts/tasks/task_helpers.py
task_type: implement
---

# Work Package Prompt: WP06 – WPState Consumer Migration — High-Touch Trio (#405)

## IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- **Objective**: Migrate the three highest-density lane-logic consumers (`orchestrator_api/commands.py`, `next/decision.py`, `dashboard/scanner.py`) to use `WPState` methods. Deduplicate the 3 `LANES` tuple definitions. Preserve old API for non-migrated consumers.
- **SC-006**: `grep -r 'current_lane ==' src/specify_cli/orchestrator_api src/specify_cli/next src/specify_cli/dashboard` returns zero matches.
- **FR-013**: LANES tuple deduplication — `tasks_support.py` and `task_helpers.py` import from canonical `status` package.
- **FR-014**: No direct lane string comparisons remain in the three migrated files.
- **NFR-001**: Full test suite passes after each consumer migration commit.
- **NFR-006**: Dashboard kanban bucketing produces identical results via `WPState.display_category()`.
- **C-004**: Old `validate_transition()` and `ALLOWED_TRANSITIONS` remain accessible for 40+ non-migrated consumers.

## Context & Constraints

- **Upstream issue**: #405 — lane transition logic scattered across 46 files
- **Plan**: `kitty-specs/065-wp-metadata-state-type-hardening/plan.md` (WP06 section)
- **Prerequisite**: WP05 (WPState ABC, concrete classes, and property tests must exist)
- **Rebased baseline note**: `src/specify_cli/orchestrator_api/commands.py` now already carries review-handoff evidence behavior in the baseline (`--review-ref` handling, policy/evidence validation, and corresponding tests). This WP must preserve those semantics while migrating lane logic to `WPState`.

**Key eliminations** (from plan.md):
- `_RUN_AFFECTING_LANES = frozenset(["claimed", "in_progress", "for_review"])` in `orchestrator_api/commands.py` → `state.affects_run` property (if applicable) or `state.progress_bucket() == "in_flight"`, without weakening the current review/policy guard behavior
- `if current_lane == "planned" / elif "claimed"` cascades → `state.allowed_targets()` / `state.progress_bucket()`
- 4-lane `LANES` tuple in `task_helpers.py` → removed
- 3 separate `LANES` definitions → single import from `status` package

**Migration pattern** (Strangler Fig):
```python
# BEFORE (raw string comparison):
if current_lane == "planned":
    ...
elif current_lane in ("claimed", "in_progress"):
    ...
elif current_lane == "for_review":
    ...

# AFTER (WPState method):
state = wp_state_for(current_lane)
if state.progress_bucket() == "not_started":
    ...
elif state.progress_bucket() == "in_flight":
    ...
elif state.progress_bucket() == "review":
    ...
```

**`in_review` Lane Awareness** (FR-012a scope expansion):
- WP05 promotes `in_review` from alias to first-class lane. Consumer migration must account for this:
  - `decision.py`: `_find_first_wp_by_lane("for_review")` logic needs an `in_review` counterpart — WPs in `in_review` are actively being reviewed and should not be picked up by another reviewer.
  - `orchestrator_api/commands.py`: Any `for_review`-specific logic must also handle `in_review` (or use `state.progress_bucket() == "review"` to cover both), while retaining the current `review_ref` and policy/evidence transition requirements already covered by baseline tests.
  - `dashboard/scanner.py`: Kanban bucketing must include `in_review` in the "Review" column alongside `for_review` and `approved`.
- The `display_category()` method from WP05 should handle this correctly (`InReviewState.display_category() == "Review"`), but verify during migration.

**Doctrine**:
- `quality-gate-verification.tactic.yaml` — per-commit verification during consumer migration
- `refactoring-strangler-fig.tactic.yaml` — old API preserved alongside new State Object
- `change-apply-smallest-viable-diff.tactic.yaml` — one consumer per commit
- `001-architectural-integrity-standard.directive.yaml`

**Cross-cutting**:
- **Boy Scout** (DIRECTIVE_025): Handle empty except at `commands.py:135`; extract 3 duplicated help strings to constants.
- **Self Observation Protocol** (NFR-009): Write observation log at session end.
- **Quality Gate** (DIRECTIVE_030): Tests + type checks must pass before `for_review`.

## Branch Strategy

- **Implementation command**: `spec-kitty implement WP06 --base WP05`
- **Planning base branch**: `feature/metadata-state-type-hardening`
- **Merge target branch**: `feature/metadata-state-type-hardening`

## Subtasks & Detailed Guidance

### Subtask T028 – Migrate orchestrator_api/commands.py + Boy Scout

- **Purpose**: Migrate the highest-density consumer (22 lane string occurrences). Apply Boy Scout fixes.
- **Steps**:
  1. Find all lane string comparisons:
     ```bash
     rg "current_lane|lane ==" src/specify_cli/orchestrator_api/commands.py
     rg "_RUN_AFFECTING_LANES" src/specify_cli/orchestrator_api/commands.py
     ```
  2. For each pattern, replace with `WPState` method calls:
     - `_RUN_AFFECTING_LANES` → check `state.progress_bucket() == "in_flight"` or add an `affects_run` convenience property if it simplifies multiple call sites
     - `if lane == "planned"` → `if state.progress_bucket() == "not_started"`
     - `if lane in ("done", "canceled")` → `if state.is_terminal`
     - `if lane == "blocked"` → `if state.is_blocked`
  3. Import `wp_state_for` from `specify_cli.status`:
     ```python
     from specify_cli.status import wp_state_for
     ```
  4. **Boy Scout** (DIRECTIVE_025):
     - Handle empty except clause at line ~135:
       ```bash
       rg "except:" src/specify_cli/orchestrator_api/commands.py
       ```
       Replace bare `except:` with `except Exception:` or a more specific type.
     - Extract 3 duplicated help strings to module-level constants:
       ```bash
       rg "help=" src/specify_cli/orchestrator_api/commands.py | head -10
       ```
  5. Run tests after migration:
     ```bash
     pytest tests/ -x -v -k "orchestrator"
     pytest tests/ -x --timeout=60
     ```
  6. **Commit separately**.
- **Files**: `src/specify_cli/orchestrator_api/commands.py`
- **Parallel?**: Yes — can proceed alongside T029 and T030 (different files).
- **Validation**:
  - [ ] No `current_lane ==` comparisons remain
  - [ ] `_RUN_AFFECTING_LANES` frozenset removed (replaced by WPState method)
  - [ ] Boy Scout: empty except fixed, help strings extracted
  - [ ] Tests pass

### Subtask T029 – Migrate next/decision.py

- **Purpose**: Migrate the next-action decision engine from lane string comparisons to WPState methods.
- **Steps**:
  1. Find lane string patterns:
     ```bash
     rg "current_lane|lane ==|\.lane\b" src/specify_cli/next/decision.py
     ```
  2. Replace each pattern with the appropriate `WPState` method:
     - Lane comparisons → `state.progress_bucket()` or `state.allowed_targets()`
     - Terminal checks → `state.is_terminal`
     - Decision branching → `state.display_category()` where appropriate
  3. Import `wp_state_for`:
     ```python
     from specify_cli.status import wp_state_for
     ```
  4. Run tests:
     ```bash
     pytest tests/ -x -v -k "decision or next"
     pytest tests/ -x --timeout=60
     ```
  5. **Commit separately**.
- **Files**: `src/specify_cli/next/decision.py`
- **Parallel?**: Yes — independent of T028 and T030.
- **Validation**:
  - [ ] No direct lane string comparisons remain
  - [ ] Tests pass
  - [ ] Decision logic produces identical outcomes

### Subtask T030 – Migrate dashboard/scanner.py to WPState

- **Purpose**: Migrate the dashboard scanner's lane bucketing and progress computation.
- **Steps**:
  1. Find lane patterns:
     ```bash
     rg "current_lane|lane ==|\.lane\b|\"planned\"|\"doing\"|\"for_review\"|\"done\"" src/specify_cli/dashboard/scanner.py
     ```
  2. Replace bucketing logic with `WPState` methods:
     - Kanban lane assignment → `state.display_category()`
     - Progress computation → `state.progress_bucket()`
     - Terminal checks → `state.is_terminal`
  3. **Critical**: The dashboard's kanban columns must use the same labels as before. Verify `display_category()` returns the correct column labels:
     - `Planned`, `In Progress`, `Review`, `Done`, `Blocked`, `Canceled`
     - If the dashboard uses different labels, adjust `display_category()` in WP05 or use a mapping here.
  4. Import `wp_state_for`:
     ```python
     from specify_cli.status import wp_state_for
     ```
  5. Run tests:
     ```bash
     pytest tests/ -x -v -k "dashboard or scanner"
     ```
  6. **Commit separately**.
- **Files**: `src/specify_cli/dashboard/scanner.py`
- **Validation**:
  - [ ] No direct lane string comparisons remain
  - [ ] Dashboard kanban columns are identical before/after
  - [ ] Tests pass

### Subtask T031 – Deduplicate LANES tuples

- **Purpose**: Collapse 3 separate `LANES` tuple definitions into a single canonical import from the `status` package.
- **Steps**:
  1. Find all LANES definitions:
     ```bash
     rg "LANES\s*=" src/specify_cli/ --type py
     ```
  2. Verify which `LANES` definition is canonical (likely in `status/models.py` or `status/__init__.py`):
     ```bash
     rg "LANES" src/specify_cli/status/
     ```
  3. In `tasks_support.py` and `scripts/tasks/task_helpers.py`, replace the local `LANES` definition with an import:
     ```python
     from specify_cli.status import LANES  # or from specify_cli.status.models import Lane
     ```
  4. If `LANES` is not already exported from `status/__init__.py`, add the export.
  5. Run tests:
     ```bash
     pytest tests/ -x -v -k "tasks_support or task_helpers"
     pytest tests/ -x --timeout=60
     ```
  6. **Commit separately**.
- **Files**:
  - `src/specify_cli/tasks_support.py`
  - `src/specify_cli/scripts/tasks/task_helpers.py`
  - `src/specify_cli/status/__init__.py` (if export needed)
- **Parallel?**: Yes — independent of consumer migrations.
- **Validation**:
  - [ ] Only one canonical `LANES` definition remains
  - [ ] `tasks_support.py` imports from `status`
  - [ ] `task_helpers.py` imports from `status`
  - [ ] Tests pass

### Subtask T032 – Remove stale 4-lane tuple in task_helpers.py

- **Purpose**: The 4-lane `LANES` tuple in `task_helpers.py` is outdated (only 4 of 8 lanes). Remove it entirely.
- **Steps**:
  1. Find the stale tuple:
     ```bash
     rg "LANES" src/specify_cli/scripts/tasks/task_helpers.py
     ```
  2. Verify it's truly stale:
     - Count elements (should be 4 vs the canonical 8)
     - Check all usages — if any code references this local LANES, it must be updated to use the canonical import from T031
  3. Remove the stale definition.
  4. Run tests:
     ```bash
     pytest tests/ -x --timeout=60
     ```
  5. This can be committed with T031 if both touch the same file.
- **Files**: `src/specify_cli/scripts/tasks/task_helpers.py`
- **Parallel?**: Yes — can be done with T031.
- **Validation**:
  - [ ] Stale 4-lane LANES tuple removed
  - [ ] All references updated to canonical import
  - [ ] Tests pass

### Subtask T033 – Verify dashboard kanban bucketing identity (NFR-006)

- **Purpose**: Final NFR-006 gate — prove dashboard kanban bucketing is identical before and after migration.
- **Steps**:
  1. Run dashboard-related tests:
     ```bash
     pytest tests/ -x -v -k "dashboard or kanban or scanner"
     ```
  2. If there are no specific kanban bucketing tests, create a focused verification:
     ```python
     def test_display_category_matches_kanban_columns():
         """All lanes produce the expected dashboard kanban column labels."""
         expected_mapping = {
             "planned": "Planned",
             "claimed": "In Progress",
             "in_progress": "In Progress",
             "for_review": "Review",
             "approved": "Review",
             "done": "Done",
             "blocked": "Blocked",
             "canceled": "Canceled",
         }
         for lane, expected_label in expected_mapping.items():
             state = wp_state_for(lane)
             assert state.display_category() == expected_label, (
                 f"Lane {lane}: expected {expected_label!r}, got {state.display_category()!r}"
             )
     ```
  3. Verify via grep that no lane string literals remain in the three migrated files:
     ```bash
     grep -r 'current_lane ==' src/specify_cli/orchestrator_api src/specify_cli/next src/specify_cli/dashboard
     ```
     This must return zero matches (SC-006).
  4. Document the verification in the Activity Log.
- **Files**: No files changed — verification only (test may be added to `test_wp_state.py`).
- **Validation**:
  - [ ] `grep` returns zero matches for `current_lane ==` in the three directories
  - [ ] Dashboard kanban tests pass
  - [ ] Bucketing labels verified identical

## Definition of Done

- [ ] `orchestrator_api/commands.py` migrated to WPState (T028)
- [ ] `next/decision.py` migrated to WPState (T029)
- [ ] `dashboard/scanner.py` migrated to WPState (T030)
- [ ] LANES tuples deduplicated (T031)
- [ ] Stale 4-lane tuple removed (T032)
- [ ] Dashboard kanban bucketing identity verified (T033)
- [ ] `grep -r 'current_lane ==' orchestrator_api/ next/ dashboard/` returns zero matches
- [ ] Boy Scout: empty except fixed in `commands.py`; help strings extracted
- [ ] Old `validate_transition()` API still callable
- [ ] Full test suite passes with zero regressions
- [ ] Type checks pass

## Risks & Mitigations

- **Risk**: Consumer migration may reveal guard conditions not covered by WP05 property tests. **Mitigation**: Run full test suite after each migration commit; any failures indicate missing guard coverage.
- **Risk**: Dashboard kanban column labels may differ from `display_category()` output. **Mitigation**: T033 verification catches this before merge; adjust `display_category()` in WP05 if needed.
- **Risk**: Non-migrated consumers (40+) may break if any shared state is modified. **Mitigation**: Old API preserved (C-004); this WP only touches 3 specific consumer files + LANES dedup.

## Review Guidance

- Verify one-consumer-per-commit discipline was followed
- Check that NO `current_lane ==` string comparisons remain in the three migrated files
- Confirm `validate_transition()` and `ALLOWED_TRANSITIONS` are NOT modified or removed
- Verify dashboard kanban bucketing produces identical column assignments (T033)
- Check Boy Scout fixes are co-committed with the consumer migration, not standalone

## Activity Log

- 2026-04-06T06:15:00Z – system – Prompt created.
- 2026-04-06T20:29:49Z – opencode:claude-opus-4.6:python-implementer:implementer – shell_pid=152804 – Started implementation via action command
- 2026-04-06T20:52:25Z – opencode – shell_pid=152804 – All 6 subtasks (T028-T033) complete. Full quality gate passed: 8854 tests pass, no new mypy/ruff findings. C-004 backward compat verified.
- 2026-04-06T20:53:29Z – codex – shell_pid=1218758 – Started review via action command
- 2026-04-06T20:55:48Z – codex – shell_pid=1218758 – Moved to planned
- 2026-04-06T21:01:36Z – opencode – shell_pid=152804 – Started implementation via action command
- 2026-04-06T21:18:32Z – opencode – shell_pid=152804 – Review feedback addressed: (1) JSON-only stdout contract tests, (2) CANONICAL_LANES public import paths, (3) explicit in_review lane handling + tests. Ruff/mypy/pytest clean.
- 2026-04-06T21:19:26Z – opencode – shell_pid=152804 – Started review via action command
- 2026-04-06T21:26:49Z – opencode – shell_pid=152804 – Review passed: All acceptance criteria met. SC-006 verified (zero current_lane== in migrated files). FR-013 CANONICAL_LANES imports from public API. FR-014 no raw lane strings in 3 consumers. NFR-001 full suite 8861 passed. NFR-006 kanban bucketing identity verified via TestDisplayCategoryMatchesKanbanColumns. C-004 old API preserved. One-consumer-per-commit discipline followed. Boy Scout fixes in scope. in_review handling correct per FR-012a. Previous review feedback fully addressed.
