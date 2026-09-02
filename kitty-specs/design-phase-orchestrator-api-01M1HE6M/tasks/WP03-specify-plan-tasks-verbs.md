---
work_package_id: WP03
title: specify/plan/tasks orchestrator-api verbs
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-001
- NFR-002
- NFR-005
- C-001
planning_base_branch: feat/design-phase-orchestrator-api-3837
merge_target_branch: feat/design-phase-orchestrator-api-3837
branch_strategy: Planning artifacts for this mission were generated on feat/design-phase-orchestrator-api-3837. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/design-phase-orchestrator-api-3837 unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
scope: codebase-wide
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/orchestrator_api/
create_intent:
- tests/specify_cli/orchestrator_api/test_specify_plan_tasks_verbs.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/orchestrator_api/test_specify_plan_tasks_verbs.py
- tests/specify_cli/orchestrator_api/test_commands_fail_closed.py
- tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py
role: implementer
tags: []
tracker_refs: []
---

# WP03 — specify / plan / tasks orchestrator-api verbs

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: (unset — select at implementation time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Add three new orchestrator-api verbs — `specify`, `plan`, `tasks` — as thin
callers of the SAME service functions the host CLI already calls, so an
external host can create a mission, scaffold its plan, and finalize its
work packages entirely through orchestrator-api, matching FR-001/002/003.

## Context

Per spec Clarification 1 (do not re-derive): `specify`/`plan`/`tasks` on
the host CLI (`src/specify_cli/cli/commands/lifecycle.py:129,212,266`) are
already thin shims delegating to `agent_feature.create_mission`
(`mission_create.py:627`), `agent_feature.setup_plan`
(`mission_setup_plan.py:1097`), `agent_feature.finalize_tasks`
(`mission_finalize.py:3075`) — all three already accept `json_output: bool`
and skip the interactive interview path when `json_output=True`.

**Payload-shape correction — this is the one non-obvious part of this
WP**: `plan` and `tasks` are unenriched pass-throughs
(`lifecycle.py:219,273` call `agent_feature.setup_plan(...,
json_output=json_output)` / `agent_feature.finalize_tasks(...,
json_output=json_output)` directly and return the raw JSON payload) —
your `plan`/`tasks` verbs should do the same: call the service function
in-process with `json_output=True` and pass its returned dict straight
through as `data` (after `validate_outbound_payload`). `specify` is
**NOT** a raw pass-through: when `json_output=True`, `lifecycle.py:161-162`
routes through `_create_mission_for_specify_json` (`lifecycle.py:66-92`),
which captures `agent_feature.create_mission`'s stdout and re-emits it
through `_with_specify_scaffold_state` (`lifecycle.py:51-58`) — adding
`scaffold_only`, `spec_state`, `next_action`, `next_step` fields BEFORE the
host CLI's `--json` caller ever sees them. Your `specify` verb must target
this ENRICHED shape — either call `_create_mission_for_specify_json`
directly in-process, or replicate its enrichment step in-process — NOT the
raw `create_mission` payload one layer beneath it. Read `lifecycle.py:51-92`
before implementing; matching the real host-CLI `--json` contract (not an
internal implementation detail one layer beneath it) is Acceptance
Scenario 1's own bar.

**Pattern precedent**: follow `start-review` (`commands.py:1286-1360`)
byte-for-byte in structure — `--policy` required-and-validated first
(`POLICY_METADATA_REQUIRED` / `POLICY_VALIDATION_FAILED` via
`_parse_policy_or_fail`), mission resolution via
`_resolve_mission_dir_or_fail`, the underlying call in a `try/except`
mapping domain exceptions to `_fail(cmd, error_code, message, ...)`, then
`validate_outbound_payload(data, "orchestrator_api")` before
`make_envelope(command=cmd, success=True, data=data)` → `_emit(envelope)`.
All three new verbs register on the SAME `app = typer.Typer(...)` instance
the 10 existing verbs use — no new Typer app, no new envelope helper.

**NFR-001 (do not break the 10 existing verbs)**: this WP is purely
additive — new `@app.command` functions appended to `commands.py`. Do not
touch any existing verb's function body, decorator, or helper
(`_fail`/`_emit`/`_resolve_mission_dir_or_fail`/etc.) beyond what's needed
to add the three new ones.

**C-001**: confirm before finishing that no import of `spec-kitty-events`/
`spec-kitty-tracker` was introduced by this WP (`grep -rn "spec_kitty_events\|spec_kitty_tracker" src/specify_cli/orchestrator_api/commands.py` should stay empty).

## Subtask T009: RED — author `test_specify_plan_tasks_verbs.py`

**Purpose**: Land a genuinely failing ATDD test before any of the three
verbs exist.

**Steps**:
1. Create `tests/specify_cli/orchestrator_api/test_specify_plan_tasks_verbs.py`.
2. Using this repo's existing CLI-invocation test pattern for
   orchestrator-api commands (reuse whatever `CliRunner`/subprocess
   invocation helper `test_commands_fail_closed.py` or
   `test_transition_subtask_gate.py` already use — do not hand-roll a new
   invocation helper), write:
   - Acceptance Scenario 1: `specify --mission-type <type> --policy <...>`
     against a scratch project with no existing mission for the slug →
     asserts `success: true` and the ENRICHED `data` shape
     (`scaffold_only`, `spec_state`, `next_action`, `next_step`, plus mission
     slug / dir / `spec.md` path) — this assertion is what makes the test
     genuinely RED pre-implementation (the `specify` command does not exist
     in `commands.py` yet → Typer "no such command" / non-zero exit).
   - Acceptance Scenario 2: `plan --mission <slug> --policy <...>` against
     an already-`specify`'d mission → asserts `data.plan_path` and the file
     exists on disk.
   - Acceptance Scenario 3: `tasks --mission <slug> --policy <...>` against
     a mission with a completed `tasks/` dir → asserts the finalized WP
     manifest shape (WP count, WP ids) matches
     `agent_feature.finalize_tasks(..., json_output=True)`'s existing shape.
   - Acceptance Scenario 4: `specify` called twice for the same slug →
     asserts `success: false` with a structured `error_code` (not a bare
     exception) and the existing mission directory untouched.
3. Since these tests exercise real mission scaffolding (real files under
   `kitty-specs/<slug>/`, real git operations via `create_mission`), mark
   `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]`, matching
   `test_transition_subtask_gate.py`'s precedent (real fixture-mission I/O)
   — NOT `pytest.mark.fast` (`test_commands_fail_closed.py`'s convention),
   which this repo's own definition (`pytest.ini:25`) reserves for
   no-subprocess/no-git-overhead tests. This determines which CI job
   collects it: `fast-tests-core-misc`'s specify-cli-rest shard runs `-m
   "fast and not windows_ci and not regression"` and will NOT collect this
   file; `integration-tests-core-misc` runs `-m 'not windows_ci and
   (git_repo or integration or architectural) and not timing and not
   regression'` and WILL.
4. Confirm collection/run failure on `planning_base_branch` before writing
   any verb implementation — commit this file alone as the RED commit.

**Files**: `tests/specify_cli/orchestrator_api/test_specify_plan_tasks_verbs.py` (new, ~150-220 lines).

**Validation**: `pytest tests/specify_cli/orchestrator_api/test_specify_plan_tasks_verbs.py -v` fails (command not found / non-zero exit) on `planning_base_branch`.

## Subtask T010: Implement `specify` verb (FR-001)

**Purpose**: Add the enriched-shape `specify` command.

**Steps**:
1. Add `@app.command(name="specify")` to `commands.py`, options:
   `--mission-type` (required), `--topology` (optional), `--mission`
   (the new mission's slug/name — check `lifecycle.py:129`'s own option
   name for the equivalent host-CLI flag and mirror it), `--policy`
   (required for this mutating verb, `POLICY_METADATA_REQUIRED` pattern).
2. In-process call into `_create_mission_for_specify_json` (or replicate
   its `_with_specify_scaffold_state` enrichment step in-process) —
   NEVER shell out to the host CLI.
3. Map `create_mission`'s already-established duplicate-mission error to a
   structured `error_code` via `_fail` (Acceptance Scenario 4) — do not let
   it propagate as a bare exception/traceback.
4. `data` carries: mission slug, mission directory path, `spec.md` path,
   `scaffold_only`, `spec_state`, `next_action`, `next_step`.

**Files**: `src/specify_cli/orchestrator_api/commands.py` (~50-70 new lines).

**Validation**: T009's Scenario 1 and 4 tests pass.

## Subtask T011: Implement `plan` verb (FR-002)

**Purpose**: Add the raw-pass-through `plan` command.

**Steps**:
1. Add `@app.command(name="plan")`, options `--mission` (required),
   `--policy` (required).
2. Call `agent_feature.setup_plan(..., json_output=True)` in-process;
   return its raw dict as `data` (after `validate_outbound_payload`) — do
   NOT add enrichment fields `specify` has; this is a deliberate,
   spec-confirmed asymmetry (Clarification 1).

**Files**: `src/specify_cli/orchestrator_api/commands.py` (~30-40 new lines).

**Validation**: T009's Scenario 2 test passes; `data.plan_path` points at
`kitty-specs/<slug>/plan.md` and the file exists on disk.

## Subtask T012: Implement `tasks` verb (FR-003)

**Purpose**: Add the raw-pass-through `tasks` (finalize) command.

**Steps**:
1. Add `@app.command(name="tasks")`, options `--mission` (required),
   `--policy` (required).
2. Call `agent_feature.finalize_tasks(..., json_output=True)` in-process;
   return its raw dict as `data`.

**Files**: `src/specify_cli/orchestrator_api/commands.py` (~30-40 new lines).

**Validation**: T009's Scenario 3 test passes.

## Subtask T013: Negative-path fail-closed coverage (NFR-002/SC-004)

**Purpose**: Every new verb's failure path returns a structured
`error_code`, never a bare exception/traceback/empty envelope.

**Steps**:
1. Extend `tests/specify_cli/orchestrator_api/test_commands_fail_closed.py`
   and `test_typed_error_fail_closed.py` with cases for all three new
   verbs: missing `--policy` → `POLICY_METADATA_REQUIRED`; invalid policy →
   `POLICY_VALIDATION_FAILED`; `specify` on a slug that already has a
   mission directory → the structured duplicate-mission error; `plan`/
   `tasks` against a nonexistent mission slug → `MISSION_NOT_FOUND`
   (mirroring `_resolve_mission_dir_or_fail`'s existing pattern).
2. These two files are ALREADY marked `pytestmark = [pytest.mark.fast]` at
   file scope — keep your additions consistent with that (pure in-process
   calls against a mocked/lightweight mission dir, no real git I/O); do not
   change the file-level marker.

**Files**: `tests/specify_cli/orchestrator_api/test_commands_fail_closed.py`, `tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py` (extended, not rewritten — a handful of new test functions each).

**Validation**: New negative-path cases pass; existing cases in both files remain unmodified and green.

## Subtask T014: Re-run existing verb surface (NFR-001)

**Purpose**: Confirm the 10 pre-existing orchestrator-api verbs are
unchanged in behavior, request shape, and response shape.

**Steps**:
1. Run the full `tests/specify_cli/orchestrator_api/` directory (all
   existing files, unmodified by this WP beyond T013's additions) and
   confirm zero regressions against WP01's baseline snapshot.

**Files**: none new — verification only.

**Validation**: Full `tests/specify_cli/orchestrator_api/` run green (module
NFR-001 confirmation), modulo any pre-existing #3284 red already recorded
in `tracer-tooling-friction.md`.

## Write-Scope / Adjacent Open PRs (state per WP, do not omit)

`orchestrator_api/commands.py` is a **same-file overlap** with **PR #3826**
(`pr/3131-merge-retention`), which touched `commands.py`'s merge-mission
area (`merge_mission`/`_execute_lane_merge`/`_build_merge_preflight`) —
different functions from this WP's additions, but the same physical file.
**PR #3826 merged into `main` on 2026-09-02**; this mission's own branch
(`feat/design-phase-orchestrator-api-3837`) has not yet rebased onto that
merge as of this tasks phase, so `commands.py`'s merge-mission area on
`main` already differs from this branch even though the touched functions
don't overlap — implementers should be aware of that state rather than
treating it as a future "if #3826 lands" contingency. This WP is additionally marked
`scope: codebase-wide` in its own frontmatter (see Note below) because it
is one of five WPs (WP03/04/05/06/08) that concurrently add new
`@app.command` functions to this same file — the ownership validator's
overlap check only exempts either (a) a dependency-ordered pair, or (b)
a WP marked `codebase-wide`; since WP03-06/08 are deliberately mutually
independent (plan.md's "5 concurrent lanes"), `codebase-wide` is the
mechanism this mission uses instead of forcing an artificial dependency
chain across them. **This does not relax the requirement to review the
same-file merge order at implementation time** — sequence the MERGES of
WP03/04/05/06/08 (not necessarily their implementation), per this repo's
ownership-map-leeway standing order.

Additionally: this WP's `specify` verb calls `agent_feature.create_mission`
(`mission_create.py:627`, read-path caller only — this WP does not edit
`mission_create.py`), which **PR #3826** also touched directly — a
behavioural (not file-ownership) rebase risk. **PR #3826 has already
merged into `main`** (this mission's branch has not yet rebased onto it),
so this WP's `create_mission`/`setup_plan` wrapper assumptions should be
re-verified against `main`'s current state at implementation time — this
is a check due now, not a future contingency deferred to "if #3826
lands." This WP's `plan` verb calls
`agent_feature.setup_plan` (`mission_setup_plan.py:1097`), which **PR
#3836** (`fix/custom-mission-type-second-class-3830`) edits directly —
same category of behavioural rebase risk. Neither PR edits
`orchestrator_api/commands.py`'s `specify`/`plan`/`tasks` functions
themselves (this WP owns those), but both are live, in-flight changes to
functions this WP calls into.

## Definition of Done

- [ ] RED commit: `test_specify_plan_tasks_verbs.py` fails on `planning_base_branch`.
- [ ] GREEN commit(s): all three verbs implemented, T009's 4 scenarios pass.
- [ ] `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` on the new test file.
- [ ] Negative-path cases added to the two shared `fast`-marked fail-closed files.
- [ ] Full existing `tests/specify_cli/orchestrator_api/` suite green (NFR-001).
- [ ] `mypy --strict` / `ruff check` clean on `commands.py`.
- [ ] `grep` confirms zero `spec-kitty-events`/`spec-kitty-tracker` reference introduced (C-001).

Run: `spec-kitty agent action implement WP03 --agent <name>`

## Risks

- **Enrichment-shape miss on `specify`**: the most likely mistake in this
  WP is returning `create_mission`'s raw payload instead of the enriched
  `_create_mission_for_specify_json` shape — re-read Clarification 1
  before implementing, this is explicitly the one place this mission's
  spec corrected an earlier draft's wrong assumption.
- **Same-file merge collision** with WP04/05/06/08, and same-file overlap
  with the now-merged PR #3826 — see Write-Scope note above; coordinate
  merge order explicitly rather than discovering the conflict at merge
  time, and re-verify `commands.py`'s merge-mission area against `main`'s
  current state (which already carries #3826) before merging.

## Reviewer Guidance

- Confirm `specify`'s `data` shape includes all four scaffold-state fields
  (`scaffold_only`, `spec_state`, `next_action`, `next_step`) — a payload
  missing these is the Clarification 1 regression this WP exists to avoid.
- Confirm `plan`/`tasks` are genuinely unenriched pass-throughs (no added
  fields beyond what `agent_feature.setup_plan`/`finalize_tasks` already
  return) — the asymmetry with `specify` is intentional, not an oversight
  to "fix" toward symmetry.
- Confirm the new test file's marker and directory placement collect it
  into `integration-tests-core-misc`, not silently into neither job.
