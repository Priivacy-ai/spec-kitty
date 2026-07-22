---
work_package_id: WP03
title: Move-task partition regression + docs campsite
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: mission/2533-pr-bound-coord-claim-precondition
merge_target_branch: mission/2533-pr-bound-coord-claim-precondition
branch_strategy: Planning artifacts for this mission were generated on mission/2533-pr-bound-coord-claim-precondition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/2533-pr-bound-coord-claim-precondition unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1250233"
shell_pid_created_at: "1784065249.79"
history:
- at: '2026-07-14T19:15:00Z'
  actor: claude
  note: WP authored from plan IC-02 (renumbered to WP03 after write-side split-out).
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_tasks_move_task_partition.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/specify_cli/cli/commands/test_tasks_move_task_partition.py
- docs/architecture/branch-target-routing.md
- docs/architecture/execution-lanes.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration.
You are the **implementer**.

## Objective

Lock the WP01 partition-aware core against future regression on its **silent** second
consumer (move-task), and correct the two architecture docs that still describe the
retired single-ref placement model. WP01/WP02 fixed the behavior; this WP guards the
neighbor and makes the docs match the kind-based partition. **No `tasks_move_task.py`
source edit** — only a new regression test that exercises it.

## Context

- **Depends on WP01** — the partition-aware staging core must already exist; assert it.
- Spec `../spec.md` (FR-005 move-task unchanged; FR-006 docs; SC-001..SC-004).
- **Why the move-task regression matters**: `_mt_untracked_planning_artifact_paths`
  (`tasks_move_task.py:1364`, called `:1400`) reuses `resolve_planning_artifact_staging`
  and swallows exceptions (`except: return ()`). A future change to the shared core
  could silently degrade move-task staging with no crash; a regression on the real path
  makes that loud.

## Subtasks

### T009 — Move-task partition regression [P]

1. Create `tests/specify_cli/cli/commands/test_tasks_move_task_partition.py`.
2. Exercise `_mt_untracked_planning_artifact_paths` (or the nearest public move-task
   entry reaching it) against a real `tmp_path` git repo where PRIMARY planning
   artifacts are committed on the feature/target branch:
   - PRIMARY artifacts are NOT reported as untracked/needing-staging against the coord
     ref (WP01 partition behavior — including `meta.json`).
   - A genuinely-dirty COORD status file IS still surfaced under a coordination topology.
3. Guard the silent consumer: call it directly and assert a non-empty, well-typed result
   for the dirty-coord case rather than the `except: return ()` empty.

**Validation**: passes against the WP01 core; would fail if the shared behavior regressed.

### T010 — Docs campsite: kind-based partition [P]

1. `docs/architecture/branch-target-routing.md:42-44` (planning/lanes → coordination
   branch) → correct to the kind-based partition: PRIMARY kinds
   (spec/plan/tasks/`tasks/WP*.md`/`data-model`/`lanes.json`/`meta.json`) → **primary
   target branch for every topology**; only COORD kinds (`status.*`, acceptance-matrix,
   issue-matrix, analysis-report) → coordination branch. Reference ADR
   `docs/adr/3.x/2026-06-24-1-kind-and-topology-aware-artifact-placement.md`.
2. `docs/architecture/execution-lanes.md:78-82` (See-Also) → update to the corrected partition.
3. Tight, factual edits; do not restructure (campsite discipline).

**Validation**: no reader can find the retired "planning artifacts → coordination branch" claim.

### T011 — Full verification

```bash
PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/test_implement_cores.py \
  tests/specify_cli/cli/commands/test_implement.py \
  tests/specify_cli/cli/commands/test_implement_writeside.py \
  tests/specify_cli/cli/commands/test_tasks_move_task_partition.py -n auto --dist loadfile -q
uv run pytest tests/architectural/test_no_legacy_terminology.py -q   # docs touch doctrine-adjacent prose
```

- Confirm SC-001 (claim end-to-end, no manual git), SC-002 (zero false aborts), SC-003
  (suites green; WP01/WP02 repros red-before/green-after), SC-004 (docs correct).
- Any pre-existing unrelated failure → open a GitHub issue before treating it as
  baseline (DIR-013); do not retry-to-green.

**Validation**: all targeted suites + terminology guard green.

## Branch Strategy

- Planning/base + merge target: `mission/2533-pr-bound-coord-claim-precondition`.
- Depends on WP01. Independent of WP02 (may run as a parallel lane). Worktree allocated
  per lane from `lanes.json` by `spec-kitty agent action implement WP03 --agent claude`.

## Definition of Done

- [ ] `test_tasks_move_task_partition.py` created and green; guards the silent consumer.
- [ ] `branch-target-routing.md:42-44` + `execution-lanes.md:78-82` corrected, ADR-referenced.
- [ ] Targeted pytest suites + `test_no_legacy_terminology.py` green.
- [ ] SC-001..SC-004 confirmed; no scope creep beyond FR-005/FR-006.

## Risks & Reviewer Guidance

- **Don't re-implement WP01/WP02** — this WP asserts and documents.
- **Regression realism** — the move-task test exercises the real consumer path (not a
  mock that would pass even if the core regressed).
- **Terminology guard** — docs sit near doctrine prose; confirm
  `test_no_legacy_terminology.py` passes.

## Activity Log

- 2026-07-14T21:28:29Z – claude:sonnet:python-pedro:implementer – shell_pid=1222954 – Assigned agent via action command
- 2026-07-14T21:40:15Z – claude:sonnet:python-pedro:implementer – shell_pid=1222954 – Ready for review
- 2026-07-14T21:40:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=1250233 – Started review via action command
- 2026-07-14T21:44:11Z – user – shell_pid=1250233 – Review passed: WP03 own commit touches only the 3 owned files (test + 2 docs); the implement_cores.py/test_implement*.py in the base diff are WP01's propagated dep commit 3d57d5c50, not WP03. Regression test exercises the REAL consumer _mt_untracked_planning_artifact_paths -> resolve_planning_artifact_staging via real git subprocess (no fake GitPort); coord branch branched off bootstrap so it genuinely diverges from primary. Both assertions present: (a) committed PRIMARY artifacts incl meta.json NOT flagged, (b) dirty COORD issue-matrix.md surfaced with extra!=() guard against the except:return() degrade. Docs corrected to kind-based partition, ADR 2026-06-24-1 referenced, no residual stale claim, tight edits. Regression + terminology guard green (uv run).
