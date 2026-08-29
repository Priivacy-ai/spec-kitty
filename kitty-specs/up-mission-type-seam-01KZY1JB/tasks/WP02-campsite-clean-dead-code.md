---
work_package_id: WP02
title: 'Campsite-clean opening commit: delete two dead-code clusters, fix the stale WP06 docstring'
dependencies:
- WP01
requirement_refs:
- FR-010
- FR-011
- FR-013
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T002
- T003
- T004
phase: Phase 1 - Campsite-clean opening commit (IC-06, mission's first CODE commit)
assignee: ''
agent: claude
history:
- at: '2026-08-13T00:00:00Z'
  actor: system
  action: Prompt generated during /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/activation/resolver.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/activation/resolver.py
- tests/charter/test_resolver.py
- src/specify_cli/cli/commands/mission_type.py
- tests/cli/test_charter_mission_type_commands.py
- src/doctrine/missions/mission_type_repository.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Campsite-clean opening commit: delete two dead-code clusters, fix the stale WP06 docstring

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` and behave according to its guidance
before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

This is the mission's **first CODE commit** — a distinct, behavior-preserving deletion pass per
plan.md's "Campsite-Clean Opening Commit" section and Standing Order #2 (tidy-first). It is
**not** a grab-bag: it folds exactly the two pieces of domain-matched debt spec.md already
requires in this mission's own touched surfaces (CL-004, CL-004a), plus the one stale-docstring
fix (FR-011) that would otherwise misdirect the next reader (you, in WP03) toward a seam that does
not exist.

Three independent deletions/fixes, each behavior-preserving (zero production callers today,
confirmed below):

1. **FR-010/CL-004**: delete `resolve_mission_steps` (`src/charter/activation/resolver.py:908`, live-verify
   the exact end line before deleting — plan.md cites `908-937`) and its single test in
   `tests/charter/test_resolver.py`. Confirmed zero production callers by repo-wide grep during
   planning; **re-verify live before deleting**: `grep -rn "resolve_mission_steps" src/ tests/`
   should show only the definition and its one test call site.
2. **FR-013/CL-004a**: delete `list_cmd` (`src/specify_cli/cli/commands/mission_type.py:150-151`,
   live-verify), `_print_available_missions` (line ~122, live-verify — delete the whole function
   body), and — **only** the `discover_missions` name, not the whole import statement — from the
   multi-name import block (~lines 38-46). The other six names in that same import block
   (`Mission`, `MissionError`, `MissionNotFoundError`, `get_mission_by_name`,
   `get_mission_for_feature`, `list_available_missions`) each have a live caller elsewhere in the
   file — **re-verify this live** with `grep -n "Mission\b\|MissionError\|MissionNotFoundError\|
   get_mission_by_name\|get_mission_for_feature\|list_available_missions" src/specify_cli/cli/
   commands/mission_type.py` before touching the import block; only remove `discover_missions`
   itself.
3. **FR-011/CL-004**: correct the docstring of `_inject_projected_fields`
   (`src/doctrine/missions/mission_type_repository.py:171`, live-verify) that currently claims (at
   ~line 177) org/project overrides apply "through the separate runtime consumer switch, WP06."
   This is false — that WP06 (`kitty-specs/mission-step-authority-01KXNZMT/tasks/WP06-consumer-
   switch.md`) is a caching-authority switch, not an org/project seam. Replace with an accurate
   statement that org/project overrides are handled by the new layered lookup this mission adds in
   WP03 (IC-01/IC-02) — not by any WP06 consumer switch. (You are writing this docstring *before*
   WP03's factory exists; word it as "the layered lookup this mission introduces" rather than
   naming a specific function signature you haven't written yet, or come back and tighten it once
   WP03 lands, whichever your workflow prefers — the important thing is the false "WP06" claim is
   gone.)

**Success** = all three deletions/fixes land in one commit (or a tight sequence of commits within
this WP — spec.md's atomicity requirement is about IC-06 as a unit, not literally one git commit),
the full existing test suite for the touched files still collects and passes (minus the two
deleted tests, whose removal is itself validated by the suite no longer referencing them), and
`tests/cli/test_charter_mission_type_commands.py` gains one new assertion that `list_mission_types`
is the sole `"list"` command registered on the Typer app (CL-004a / SC-006, made executable rather
than left as a manual grep).

## Context & Constraints

- Read `kitty-specs/up-mission-type-seam-01KZY1JB/plan.md`'s "Campsite-Clean Opening Commit" and
  "IC-06" sections in full before starting — they carry the exact rationale for why these two
  deletions are safe (zero production callers, confirmed twice — once at spec authoring, once at
  plan authoring) and why the import-pruning must be surgical (delete only the one dead name, not
  the whole import block — smallest-viable-diff discipline per the charter's change-scope
  reconciliation order).
- **This WP is also this mission's Baseline-capture point.** Before your first functional commit,
  run plan.md's exact Baseline pytest invocation against the mission's `planning_base_branch`
  merge-base (recorded as `main` @ `ab0a0b9b5` in this mission's own
  `tracer-tooling-friction.md`):

  ```bash
  uv run pytest tests/doctrine/missions/test_mission_type_repository.py \
    tests/charter/test_mission_type_profiles.py tests/charter/test_resolver.py \
    tests/charter/test_charter_import_time_io.py tests/cli/test_charter_activate_warning.py \
    tests/cli/test_charter_mission_type_commands.py tests/cli/test_doctrine_commands.py \
    tests/specify_cli/cli/commands/test_mission_type_template_set_cli.py \
    tests/runtime/test_runtime_seam.py \
    tests/architectural/test_layer_rules.py tests/architectural/test_charter_facades_reexport_doctrine.py \
    tests/architectural/test_no_inert_schema_slots.py \
    -v --tb=short
  ```

  Run this against the merge-base commit — checked out read-only, or via
  `PYTHONPATH=<merge-base worktree>/src` per CLAUDE.md's documented technique, **never** by
  mutating this mission's own working tree. Record any failure observed there as **pre-existing
  red**, attributable to issue #3284 (23 untracked test failures + 2 errors on `main`) or a
  category-2/3 cause (CI-environment config, stale install) per CLAUDE.md's three-way
  classification — do NOT "fix" it, and do NOT let a later WP's reviewer misattribute it to this
  mission. Note the baseline result in this WP's Activity Log (below) so subsequent WPs' reviewers
  have it on record without re-running the baseline themselves. Per the charter's Pre-existing
  Failure Reporting Rule, if you find pre-existing red not already covered by issue #3284, open a
  GitHub issue reporting it (command run, failure summary, why you believe it's pre-existing)
  before treating it as accepted baseline context.
- **Terminology**: no `feature*` alias is introduced or preserved by this WP's deletions — the
  deleted `list_cmd`/`_print_available_missions`/`discover_missions` cluster was about *missions*
  (the work unit's legacy `.kittify/missions/` scanner), not mission-*types*; deleting it does not
  touch the Terminology Canon either way.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on
  `kitty/mission-up-mission-type-seam-01KZY1JB`. During `/spec-kitty.implement` this WP may branch
  from a dependency-specific base, but completed changes must merge back into
  `kitty/mission-up-mission-type-seam-01KZY1JB` unless the human explicitly redirects the landing
  branch.
- **Planning base branch**: `kitty/mission-up-mission-type-seam-01KZY1JB`
- **Merge target branch**: `main`

## Subtasks & Detailed Guidance

### Subtask T002 – Delete `resolve_mission_steps` and its test (FR-010/CL-004)

- **Purpose**: a function with zero production callers, twice flagged dead by review, and excluded
  from `__all__` to dodge a dead-symbol gate, stops persisting as bait for future confusion.
- **Steps**: live-verify zero callers beyond the one test
  (`grep -rn "resolve_mission_steps" src/ tests/`); delete the function from
  `src/charter/activation/resolver.py`; delete its single test from `tests/charter/test_resolver.py` (the
  test that asserts only `isinstance(result, dict)` and non-empty length, per plan.md's own
  characterization — confirm this matches what you find, and if the live test asserts more than
  that, note the discrepancy in your Activity Log entry).
- **Files**: `src/charter/activation/resolver.py`, `tests/charter/test_resolver.py`.
- **Parallel?**: Can proceed alongside T003/T004 (different files), but land as part of the same
  WP commit sequence.
- **Notes**: Confirm `resolve_mission_steps` is not exported in any `__all__` before deleting
  (already established by spec CL-004, but re-verify: `grep -n "__all__" src/charter/activation/resolver.py`).

### Subtask T003 – Delete `list_cmd` / `_print_available_missions` / the `discover_missions` import (FR-013/CL-004a)

- **Purpose**: Typer's registration order means the *second* `@app.command("list")` registration
  (`list_mission_types`, ~line 1429) silently wins over the first (`list_cmd`, ~line 150) with no
  error or warning — this dead code sits in the exact file FR-006/FR-007/FR-008 (WP07) modify, and
  per the canonical-source-unification standing order it must go.
- **Steps**:
  1. Live-verify: `grep -n '@app.command("list")' src/specify_cli/cli/commands/mission_type.py`
     shows exactly two registrations today; confirm which one is `list_cmd` and which is
     `list_mission_types`.
  2. Delete `list_cmd` (its full function body and the `@app.command("list")` decorator above it).
  3. Delete `_print_available_missions` (its full function body).
  4. Remove only `discover_missions` from the multi-name import block — live-verify the other six
     names each still have a caller (see Objectives point 2 above for the exact grep) before
     touching the import line.
  5. Confirm `list_mission_types` is now the sole `"list"` command handler:
     `grep -n '@app.command("list")' src/specify_cli/cli/commands/mission_type.py` shows exactly
     one hit.
- **Files**: `src/specify_cli/cli/commands/mission_type.py`.
- **Parallel?**: Can proceed alongside T002/T004.
- **Notes**: Do not touch `list_mission_types` itself in this WP — WP07 (FR-006/FR-007/FR-008)
  extends the mission-type CLI surfaces later; this WP only removes the shadowed dead handler.

### Subtask T004 – Add the sole-`list`-handler regression test, and fix `_inject_projected_fields`'s stale docstring (FR-011/CL-004, FR-013's test half)

- **Purpose**: two independent items bundled here because both are small, both are in this WP's
  scope, and both close out this WP's "campsite-clean" mandate.
- **Steps** (docstring fix):
  1. Live-verify the current docstring text of `_inject_projected_fields`
     (`src/doctrine/missions/mission_type_repository.py`, ~line 171) — confirm the false "WP06"
     claim at ~line 177 (`grep -n -A 15 "_inject_projected_fields" src/doctrine/missions/
     mission_type_repository.py`).
  2. Replace the false sentence with an accurate one: org/project overrides are handled by the new
     layered lookup this mission introduces (WP03/IC-01, threaded further by WP04/IC-02) — not by
     any WP06 consumer switch. Do not claim the new lookup already exists with a specific function
     name if WP03 has not landed yet in your working sequence; word it forward-looking and
     accurate ("the layered lookup this mission's WP03 introduces" or similar), or land this docs
     fix once WP03 exists if your implementation order makes that cleaner — either is acceptable as
     long as the false claim is gone in the same PR.
- **Steps** (regression test):
  1. In `tests/cli/test_charter_mission_type_commands.py`, add a test that constructs the Typer
     app (however the existing tests in that file do so — follow the file's own pattern) and
     asserts exactly one `"list"` command is registered, and that it is `list_mission_types` (by
     identity or by asserting the deleted `list_cmd`'s distinguishing behavior — e.g. the legacy
     `.kittify/missions/`-scanning output — is absent).
  2. This test should be **RED before T003's deletion and GREEN after** if you write it before
     deleting `list_cmd` — but since Typer's silent-second-registration-wins behavior means the
     *output* was already `list_mission_types`'s output even with the shadowed handler present,
     the more direct assertion is on the **registration count** (exactly one `"list"` command),
     which *is* red before the deletion (two registrations exist) and green after (one does). Write
     it that way so the test actually proves the deletion happened, not just that the surviving
     handler's output looks right (which it already did, pre-fix, due to the shadow).
- **Files**: `src/doctrine/missions/mission_type_repository.py` (docstring only),
  `tests/cli/test_charter_mission_type_commands.py`.
- **Parallel?**: Can proceed alongside T002/T003.
- **Notes**: The registration-count assertion is the one piece of this WP that is genuinely
  red-before-green — call it out as such in your commit message, even though it's not the
  mission's NFR-005-designated red-first fix (that's WP06's job); it's still good practice to be
  explicit about what was red and why.

## Test Strategy

- **Per-AC / per-SC**: this WP proves **SC-005** ("`resolve_mission_steps` and its test are
  removed from the codebase, and `_inject_projected_fields`'s docstring no longer references
  'WP06' as an org/project seam — both verified by direct inspection/grep in CI") and **SC-006**
  ("`list_cmd`, `_print_available_missions`, and the `discover_missions` import are removed... and
  `list_mission_types` remains the sole `@app.command("list")` handler... verified by direct
  inspection/grep in CI"). Concretely: `grep -c "resolve_mission_steps" src/charter/activation/resolver.py`
  returns 0; `grep -n "WP06" src/doctrine/missions/mission_type_repository.py` returns nothing (or
  nothing in the org/project-seam sense — re-check the exact string); the new registration-count
  test from T004 is the executable proof for SC-006, not merely a manual grep.
- **Test surface**: `tests/charter/test_resolver.py` (minus the deleted test),
  `tests/cli/test_charter_mission_type_commands.py` (plus the new registration-count test). No new
  test file is created by this WP.
- **Commands**: `uv run pytest tests/charter/test_resolver.py
  tests/cli/test_charter_mission_type_commands.py -v`

## Risks & Mitigations

- **Risk**: deleting more of the multi-name import block than just `discover_missions`, which
  would be a larger, unauthorized diff per the charter's smallest-viable-diff discipline.
  **Mitigation**: the explicit live-verification grep in T003 step 4 before touching the import
  line.
- **Risk**: the docstring fix names a specific WP03 function signature that then doesn't match
  what WP03 actually ships. **Mitigation**: word the fix in terms of "the layered lookup this
  mission introduces" rather than a specific function name, or defer the exact wording tightening
  to after WP03 lands (still within this WP's scope/PR).
- **Risk**: misattributing pre-existing red (issue #3284 or category 2/3) as this WP's own
  regression. **Mitigation**: the Baseline capture in Context & Constraints above, run and
  recorded before this WP's first functional commit.

## Gate Set (this WP's Definition of Done)

Per plan.md's Gate Set:

- **`fast-tests-charter` + `integration-tests-charter`** (`--cov=charter --cov-fail-under=55`) —
  `src/charter/activation/resolver.py` is directly in scope.
- **`fast-tests-cli` + `integration-tests-cli`** (`--cov=src/specify_cli/cli`) —
  `src/specify_cli/cli/commands/mission_type.py` is directly in scope.
- **`diff-coverage` (critical-path, 90%, `[ENFORCED]`)** over `src/charter/*` — this WP's diff in
  `resolver.py` is a pure deletion (no new lines needing coverage), but confirm the diff-coverage
  tool handles deletion-only diffs cleanly (it should — no new uncovered lines are introduced).
- **`arch-adversarial`** (`tests/adversarial tests/architectural tests/architecture tests/lint`) —
  this WP's deletions must not regress `test_no_dead_symbols` or any other architectural gate; if
  anything, deleting confirmed-dead code should only ever help these gates, never hurt them.
- **`doctoral schema freshness`, `Contextive glossary`, `TID251`, `Typer JSON error surface`,
  `patch() target validation`, `Bandit`, `pip-audit`, `commitlint`** — always-on in the `lint` job,
  run regardless.
- `make lint` locally before handing off.
- **No new architectural-baseline edits** — this WP's design goal (shared with the whole mission,
  per CL-001) is zero `_inert_slots_baseline.yaml` edits; pure deletions should not require any.

## Review Guidance

- Confirm the two deletions are genuinely behavior-preserving: re-run the live-verification greps
  from T002/T003 yourself as a reviewer, don't trust the implementer's report alone.
- Confirm the import-block edit removed **only** `discover_missions`, not the whole block.
- Confirm the docstring fix no longer says "WP06" in the org/project-seam sense, and does not
  introduce a *new* false claim in its place.
- Confirm the new registration-count test in `tests/cli/test_charter_mission_type_commands.py` is
  a real assertion on registration count (or equivalent proof), not merely a re-assertion of
  `list_mission_types`'s existing output (which would have passed even before the deletion, due to
  Typer's silent-shadow behavior).
- Confirm the Baseline capture was run and recorded (see Context & Constraints) before treating any
  test failure encountered during this WP as this WP's own regression.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-13T00:00:00Z – system – Prompt created.
