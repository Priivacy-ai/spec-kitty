---
work_package_id: WP06
title: finalize-tasks / map-requirements CLI Wiring
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-004
- FR-007
- FR-008
- C-002
planning_base_branch: pr/bare-prose-requirements-uncounted
merge_target_branch: pr/bare-prose-requirements-uncounted
branch_strategy: Planning artifacts for this mission were generated on pr/bare-prose-requirements-uncounted. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/bare-prose-requirements-uncounted unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T030a
- T031
- T032a
- T032
- T033
phase: Phase 3 - Consumers (parallel with WP07, after WP05)
history:
- at: '2026-08-14T02:50:21Z'
  actor: system
  action: Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)
agent_profile: ''
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_finalize.py
- src/specify_cli/cli/commands/agent/tasks_mapping_core.py
- src/specify_cli/cli/commands/agent/tasks_map_requirements.py
- tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/json/byte_contracts.json
- tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – `finalize-tasks` / `map-requirements` CLI Wiring

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, or select via `spec-kitty agent profile list` for an
`implement`-typed WP on `src/specify_cli/cli/commands/agent/`.

---

## Objectives & Success Criteria

Implement IC-03 (plan.md): wire `find_bare_prose_requirement_ids` into
`mission_finalize.py::_validate_requirement_mapping` (the post-WP02-split orchestrator)
and `tasks_mapping_core.py::plan_mapping`, surfacing `bare_prose_requirement_ids` as a
distinct payload field on both, with each call site's own fail-loud wrapper (IC-04).

Success: Story 1 AC1/AC2 — the issue's exact repro spec.md drives both `finalize-tasks`
and `map-requirements`; both fail (non-zero exit / blocking JSON result / non-clean
coverage report) naming FR-001 and FR-002 explicitly, not merely appending to
`requirement_extraction_warnings`.

## Context & Constraints

- **Do not start this WP's `mission_finalize.py` edits before WP02's campsite-clean
  split has landed.** This WP's new branch must land against the already-decomposed
  helper shape, never adding a branch to the pre-split 16-complexity function.
- **Do not start before WP03 has landed** — this WP calls
  `find_bare_prose_requirement_ids` directly.
- **Sequenced after WP05** (the chokepoint) per tasks.md's "Parallelism & Chokepoints"
  section — this WP does not itself touch a chokepoint, but is scheduled after WP05
  completes as a conservative reading of the mission-serializing chokepoint rule.
- `mission_finalize.py` and `tasks_mapping_core.py` are **separate call sites** from the
  `runtime_bridge_cores` pure core (WP05) — they duplicate its missing/unknown/unmapped
  logic rather than sharing it. This WP's wiring is independent of WP05's.
- **Field-naming discipline**: use the identical field name, `bare_prose_requirement_ids`,
  on both payloads — do not let the two commands' JSON output drift.
- **Do not merge the new field into `unmapped_functional_requirements`** — "declared but
  not yet mapped to a WP" and "never declared at all" are different remediation stories
  for an operator; keep them as separate, distinctly-labeled fields.
- **Canonical-sources rule**: before adding a new test file, locate the existing one —
  see T030 below for the already-located set.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `pr/bare-prose-requirements-uncounted`;
  completed changes must merge back into `pr/bare-prose-requirements-uncounted`
  (base `op/3394-requirement-citation-scope` @ `ab15225ea`).
- **Planning base branch**: `pr/bare-prose-requirements-uncounted` (mission topology).
- **Merge target branch**: `pr/bare-prose-requirements-uncounted`.

> **ATDD RED verification uses `ab15225ea`, not the fields above or `main`.** Same
> caveat as WP03/WP05.

## Subtasks & Detailed Guidance

### Subtask T029 – ATDD RED-first commit

- **Purpose**: Charter C-011 binding.
- **Steps**: Write failing tests for `finalize-tasks` and `map-requirements` against
  Story 1's exact repro spec.md fixture. Verify RED against **`ab15225ea`**.
- **Notes**: This commit lands BEFORE T031/T032's implementation commits.

### Subtask T030 – Locate existing test files (do not create parallel files)

- **Purpose**: Canonical-sources rule — do not duplicate coverage.
- **Steps**: Confirmed via `git grep -l _validate_requirement_mapping tests/` /
  `git grep -l plan_mapping tests/`:
  `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py` (the ONLY hit
  for `_validate_requirement_mapping` — **not** `test_finalize_provenance_guard.py`,
  which is a different, unrelated file, the #3311 provenance-preservation guard, with
  zero references to `_validate_requirement_mapping`; re-run the grep live at
  implementation time),
  `tests/specify_cli/cli/commands/agent/test_tasks_mapping_core.py`,
  `tests/specify_cli/cli/commands/agent/test_tasks_map_requirements_seam.py`,
  `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py`,
  `tests/specify_cli/cli/commands/agent/test_tasks_core_backed_orchestration.py`. Add
  new cases to whichever already covers the relevant command. Also in scope: the
  byte-frozen JSON contract fixture — see T030a.

### Subtask T030a – Byte-frozen `map_requirements_success` fixture will break

- **Purpose**: T032 changes `MappingPlan`'s shape; the CI-enforced byte contract must be
  deliberately re-frozen, not silently left red or silently avoided.
- **Steps**: After T032 lands, run
  `tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py`; observe the expected
  byte mismatch on the `map_requirements_success` case (pinned in
  `tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/json/byte_contracts.json`);
  deliberately re-freeze the fixture for that one case only — do not touch any other
  pinned case in the same file.
- **#3395 collision warning**: #3395's own diff already modifies this exact
  `map_requirements_success` `expected_stdout` string (adding
  `"requirement_extraction_warnings": []`). When rebasing onto #3395's tip and
  re-freezing this case, PRESERVE the `requirement_extraction_warnings` field —
  add `bare_prose_requirement_ids` alongside it, do not overwrite or drop it.

### Subtask T031 – Wire `_validate_requirement_mapping`

- **Purpose**: `finalize-tasks` surfaces the new signal.
- **Plumbing prerequisite (corrects an earlier drafting error in this WP)**:
  `_validate_requirement_mapping` does **NOT** already have `spec_content` in scope —
  neither its parameter list nor its sole call site carries it, and
  `_read_spec_requirement_ids` parses `spec_content` locally but returns only
  `(all_ids, functional_ids, warnings)`, never the raw text. Before wiring the
  predicate, do ONE of: (a) change `_read_spec_requirement_ids`'s return type to also
  yield the raw `spec_content` and thread it through the call chain into a new
  `_validate_requirement_mapping` parameter, or (b) have the caller re-read spec.md
  once, mirroring the pattern used at `_check_bare_prose_requirements_ready` (WP05).
  WP02's "same call signature, no behaviour change" constraint applies only to the
  pre-existing parameters — this WP is explicitly allowed to add the new one.
- **Steps**: In `mission_finalize.py`'s post-WP02-split orchestrator, using the
  `spec_content` now plumbed in above: compute the bare-prose candidates once, and if
  non-empty, fail exactly like the existing missing/unknown/unmapped path — add
  `bare_prose_requirement_ids` as an additional, separately-labeled field on the
  JSON/console payload. Wrap the detector call fail-loud: catch any exception once,
  convert to an explicit non-empty failure, textually separate from any swallow-and-log
  wrapper (same pattern as WP05/T023).

### Subtask T032a – Extend `MappingRequest` with the plumbing `plan_mapping` needs

- **Purpose**: `plan_mapping` has the identical unscoped gap as T031, structurally more
  consequential since `plan_mapping` (`tasks_mapping_core.py::plan_mapping`, line 123)
  is documented pure/no-I/O (INV-4) — raw spec text must never be passed into it.
- **Correcting an earlier drafting error in this subtask**: `spec_content` is NOT read
  "earlier in the same function" as the `MappingRequest(...)` construction — it is read
  as a local variable inside `_mr_resolve_read_dirs` (`tasks_map_requirements.py`,
  Phase C, around line 306), a *different* function from `_mr_plan` (Phase D, line 328)
  where `MappingRequest(...)` is actually constructed. Confirmed by direct read: the
  shared `_MapReqState` object the two phases thread through today stores only
  `spec_content`'s *derived products* (`all_spec_ids`, `functional_ids`,
  `requirement_extraction_warnings`) — it does not currently carry the raw
  `spec_content` string itself, so `_mr_plan` has no existing access to it.
- **Steps**: Extend `MappingRequest` (`tasks_mapping_core.py`, `class MappingRequest`)
  with a new `bare_prose_requirement_ids: frozenset[str]` field. Add a new field to
  `_MapReqState` (e.g. `spec_content: str = ""`), set it in `_mr_resolve_read_dirs`
  (Phase C) alongside the existing derived fields, and read it back in `_mr_plan`
  (Phase D) — mirroring T031's own plumbing fix for `mission_finalize.py`. Update the
  `MappingRequest(...)` construction site in `_mr_plan` to call
  `find_bare_prose_requirement_ids(st.spec_content)` and pass the resulting ids into the
  new field. Wrap that call fail-loud at the shell call site, same pattern as
  T031/WP05-T023 — the wrapper lives in the shell, never inside `plan_mapping`.

### Subtask T032 – Wire `plan_mapping`/`compute_coverage`

- **Purpose**: `map-requirements` surfaces the new signal.
- **Steps**: Read `req.bare_prose_requirement_ids` (populated by T032a) inside
  `plan_mapping` and add it under the same field name, `bare_prose_requirement_ids`, to
  the returned `MappingPlan`. `plan_mapping` itself never calls the detector or touches
  raw text — it only consumes the already-computed ids T032a supplies, preserving its
  pure/no-I/O contract.

### Subtask T033 – Acceptance tests

- **Purpose**: Story 1 AC1/AC2 + Story 4 negative-space, at the CLI-command level.
- **Steps**: Confirm both commands surface FR-001/FR-002 as a blocking result on the
  exact repro fixture. Confirm #3394's repro shape (Story 4) stays green on both
  commands, unmodified in pinned pre-existing assertions.

## Test Strategy

- The five located test files from T030, plus new cases inside them (not new files).
- `tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py` — run after T032 lands
  (T030a); expect and deliberately fix the `map_requirements_success` byte mismatch by
  re-freezing that one fixture case in
  `tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/json/byte_contracts.json`.
- Run: `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ -n 8 --dist loadfile -q`
  scoped to the relevant test files.

## Risks & Mitigations

- Payload-shape drift between the two CLI commands' JSON output — mitigated by using
  the identical field name in both, verified in T033.
- Silently leaving `test_tasks_json_bytes.py` red instead of deliberately re-freezing the
  one affected case — mitigated by T030a being an explicit, named subtask.

## Review Guidance

- Confirm the new field is additive, not merged into `unmapped_functional_requirements`.
- Confirm both call sites' fail-loud wrapper is textually separate from any
  swallow-and-log helper.
- Confirm no new test file was created where an existing one already covers the
  command (T030's canonical-sources check).
- Confirm `plan_mapping` was not handed raw `spec_content` directly (T032a's
  pure/no-I/O contract) — only the already-computed `bare_prose_requirement_ids`.
- Confirm `test_tasks_json_bytes.py`'s `map_requirements_success` case was deliberately
  re-frozen (T030a), and that no other pinned byte-contract case changed.

## Activity Log

- 2026-08-14T02:50:21Z – system – Prompt created.
