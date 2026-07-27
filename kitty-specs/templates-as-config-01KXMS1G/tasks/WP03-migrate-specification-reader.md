---
work_package_id: WP03
title: Scaffold Specifications from Mission Configuration
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-009
tracker_refs: []
planning_base_branch: feat/templates-as-config
merge_target_branch: feat/templates-as-config
branch_strategy: Planning artifacts for this mission were generated on feat/templates-as-config. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/templates-as-config unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 3 - Production Reader Migration
assignee: ''
agent: "codex:gpt-5:reviewer-renata:reviewer"
shell_pid: "44082"
history:
- at: '2026-07-16T06:39:25Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/mission_creation.py
- tests/specify_cli/core/test_feature_creation.py
- tests/specify_cli/core/test_mission_creation_specify_started.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Scaffold Specifications from Mission Configuration

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

Migrate the real mission-creation specification reader from hard-coded local paths and an empty-file fallback to the activated mission type's mapped `spec` template.

This WP is complete when:

- `create_mission_core` selects the `spec` filename through the WP02 seam.
- The selected filename still honors the established five-tier precedence.
- Software-development mission creation writes the same effective shipped content as before the authority swap.
- A known activated mission type with null/missing/unresolvable `spec` configuration fails actionably and never writes a borrowed or empty specification.
- Failure leaves no misleading successful lifecycle/commit state.
- Existing identity, metadata, topology, event, task-directory, and `created_files` contracts remain green.
- Changed/new production lines meet the 90% coverage floor.

## Context & Constraints

WP02 must be approved. Read the mission contract and the creation transaction in full before editing:

- `kitty-specs/templates-as-config-01KXMS1G/spec.md`, Scenario 1–3 and edge cases
- `kitty-specs/templates-as-config-01KXMS1G/contracts/template-resolution-contract.md`
- `src/specify_cli/core/mission_creation.py`
- `tests/specify_cli/core/test_feature_creation.py`
- `tests/specify_cli/core/test_mission_creation_specify_started.py`

The current code checks only `.kittify/templates/spec-template.md` and `templates/spec-template.md`; if neither exists it touches an empty `spec.md`. Remove that selection authority. Preserve unrelated creation behavior and do not redesign coordination topology, commit placement, SaaS sync, or status ownership.

Known typeless compatibility is separately owned by issue #2660. Do not broaden or remove it. This WP handles a mission type already selected for the creation request.

The authoritative editable acceptance surfaces are the two owned core test modules listed above. `tests/specify_cli/cli/commands/agent/test_mission_create*.py` is adjacent read-only regression coverage for this WP: run affected cases when useful, but do not edit those CLI files or move the canonical assertions out of the core tests.

## Branch Strategy

- **Strategy**: Planning artifacts are on `feat/templates-as-config`; implementation runs in the lane worktree computed in `lanes.json` and merges back into `feat/templates-as-config`.
- **Planning base branch**: `feat/templates-as-config`
- **Merge target branch**: `feat/templates-as-config`
- **Implementation command**: `spec-kitty agent action implement WP03 --agent codex`

WP03 and WP04 are parallel after WP02. Stay inside WP03's computed lane and owned files; do not edit the plan reader.

## Review Feedback

Inspect the status event stream for `review_ref` before implementation. Address all returned findings and append chronological Activity Log entries.

## Subtasks & Detailed Guidance

### T013 — Campsite-clean WP03-owned mission-creation surfaces before feature edits

- **Purpose**: Establish a behavior-preserving creation baseline before changing specification authority.
- **Steps**:
  1. Inspect all owned files and focused Sonar/local findings for mission-creation-domain litter.
  2. Run the existing owned core tests as the preservation baseline.
  3. Remove only behavior-neutral dead imports/helpers, stale empty-spec comments, or misleading local annotations within ownership.
  4. If cleanup cannot safely resolve an item, record its frozen baseline and no-growth constraint in the Activity Log.
  5. Re-run preservation tests and record a distinct campsite entry before T014's RED test evidence.
- **Files**: All owned files only.
- **Parallel?**: No; first subtask.
- **Validation**: No mission lifecycle or template behavior changes during campsite cleanup.

### T014 — Add red mission-creation tests for doctrine-mapped specification templates

- **Purpose**: Drive the production entry point outside-in, not just the shared helper.
- **Steps**:
  1. Extend `tests/specify_cli/core/test_feature_creation.py` using the existing repository/git fixture style.
  2. Stage an activated software-development mapping and package-default spec template; create a mission through `create_mission_core`.
  3. Assert `spec.md` contains the mapped template content and appears in `created_files` as before.
  4. Add a project override for the mapped filename and assert its content wins.
  5. Where practical, use a non-conventional mapped filename fixture so the test would fail if production code still manufactures `spec-template.md`.
  6. Run red and record the current empty/hard-coded behavior.
- **Files**: `tests/specify_cli/core/test_feature_creation.py`.
- **Parallel?**: No; primary acceptance path.
- **Validation**: Exercise `create_mission_core`, not a private copy helper.

### T015 — Add red mission-creation tests for absent and invalid configuration

- **Purpose**: Ensure known mission configuration fails closed without leaving misleading artifacts.
- **Steps**:
  1. Cover an activated type with `template_set: null`.
  2. Cover a mapping that omits `spec`.
  3. Cover a mapped filename absent from every tier.
  4. Assert errors include mission type and `spec`; the missing-file case should include the mapped filename.
  5. Assert no software-development template content is written.
  6. Inspect the creation phase at which resolution should happen and assert no false `SpecifyStarted`/success state is emitted after failure.
- **Files**: Both owned test files.
- **Parallel?**: Yes, fixtures can be prepared alongside T014 before production editing.
- **Notes**: Do not overclaim rollback beyond existing transaction behavior; pin the safest consistent boundary and document it.

### T016 — Migrate specification scaffolding to the shared mapped-template seam

- **Purpose**: Remove hard-coded filename/path authority from mission creation.
- **Steps**:
  1. Resolve the selected mission type through the canonical creation inputs already available in `create_mission_core`.
  2. Call the WP02 mapped-template API with artifact kind `spec` and explicit project/feature context.
  3. Copy the returned effective path to `feature_dir/spec.md` using the existing encoding/filesystem conventions.
  4. Remove the two direct path probes and empty-file fallback for configured mission types.
  5. Preserve a separately named legacy path only if required by the existing typeless contract; do not route known activated types through it.
  6. Keep error chaining/context intact for CLI rendering.
- **Files**: `src/specify_cli/core/mission_creation.py`.
- **Parallel?**: No; follows red tests.
- **Validation**: Search the changed creation block for manufactured content-template filenames and software-development defaults.

### T017 — Preserve creation transaction, event, metadata, and created-file behavior

- **Purpose**: Limit the change to template authority and prevent lifecycle regressions.
- **Steps**:
  1. Run/extend assertions for `meta.json`, tasks README, `.gitkeep`, status stream, target branch, and coordination metadata.
  2. Confirm `spec.md` is recorded exactly once in `created_files` on success.
  3. Confirm `MissionCreated` and `SpecifyStarted` remain ordered and emitted once on success.
  4. Confirm failure does not emit a success payload or commit a false completed state.
  5. Avoid changing the separately observed `pr_bound`/coordination behaviors unless the mapped-template integration strictly requires it.
- **Files**: Both owned test modules and production file if a narrow ordering fix is required.
- **Parallel?**: No; integration regression pass after T016.
- **Notes**: Existing unrelated CLI inconsistencies are recorded in traces, not repaired here.

### T018 — Run focused mission-creation regression, style, and type gates

- **Purpose**: Prove the reader migration is reviewable independently of the plan reader.
- **Steps**:
  1. Run both owned pytest modules.
  2. Run the smallest adjacent mission-creation identity/topology tests necessary to prove no transaction drift.
  3. Run Ruff on changed files.
  4. Run scoped mypy for `mission_creation.py` using repository conventions.
  5. Check the diff for edits outside ownership and for issue #2659–#2661 scope.
  6. Record the successful effective template path/tier in the handoff.
  7. Run affected `tests/specify_cli/cli/commands/agent/test_mission_create*.py` cases as read-only adjacent regression coverage when they exercise the changed path; do not edit those files.
  8. Run pytest-cov for `mission_creation.py`, emit XML, and enforce `diff-cover coverage.xml --compare-branch <resolved-lane-base> --fail-under=90` (or repository-equivalent changed/new-code coverage).
- **Files**: No new files.
- **Parallel?**: No; final gate.

## Test Strategy

FR-007/FR-009 and the charter make tests mandatory.

- Production-entry acceptance: `create_mission_core` writes mapped content.
- Override compatibility: mapped filename's existing winning tier is unchanged.
- Negative configuration: null, missing key, missing file.
- Lifecycle regression: events/metadata/files are unchanged on success and not falsely completed on failure.
- Focused static gates: Ruff and mypy.
- Coverage gate: at least 90% of changed/new production lines against the resolved lane base.

Use realistic filesystem fixtures. Avoid mocking the entire resolver chain; patch only environment roots/repositories where existing tests already establish that seam.

## Risks & Mitigations

- **Partial mission state**: resolve at the safest point in the existing transaction and assert event behavior.
- **Hidden filename convention**: use at least one non-conventional mapped fixture.
- **Typeless scope creep**: keep legacy behavior visibly separate and unchanged.
- **Commit topology drift**: run adjacent placement/topology tests without editing their files.
- **Mock-only green**: assert real output bytes in `spec.md`.
- **Surface drift**: keep canonical assertions in the owned core tests; CLI tests remain read-only regression coverage.

## Definition of Done

- [ ] T013–T018 complete.
- [ ] A distinct behavior-preserving campsite entry precedes feature RED evidence.
- [ ] Red-first evidence exists for the prior hard-coded/empty behavior.
- [ ] Software-development package and override spec content are correct.
- [ ] Null/missing/unresolved cases fail actionably with no borrowed content.
- [ ] Mission creation lifecycle/metadata regression checks pass.
- [ ] Ruff and scoped mypy pass.
- [ ] Changed/new production-line coverage is at least 90% against the resolved lane base.
- [ ] Only owned files changed or a justified non-overlapping exception is recorded.

## Review Guidance

Reviewers should stage a real creation fixture and inspect `spec.md` bytes. Confirm production code does not check conventional template paths directly and does not touch an empty spec for a known configured mission. Examine the resolution point relative to lifecycle events so an early configuration error cannot masquerade as successful creation. Reject changes to coordination/SaaS behaviors unrelated to the template reader.

Require the implementation handoff to identify:

- the previous red failure demonstrating empty/hard-coded behavior;
- package and override winners with exact output bytes;
- the lifecycle boundary chosen for configuration failure;
- adjacent identity/topology regressions executed without modification;
- confirmation that the plan reader and legacy fallback were not edited.

## Activity Log

Append entries oldest to newest using `YYYY-MM-DDTHH:MM:SSZ – agent_id – action`.

- 2026-07-16T06:39:25Z – system – Prompt created via `/spec-kitty.tasks`.

Status is managed in `status.events.jsonl`; use Spec Kitty task movement commands rather than editing status frontmatter.
- 2026-07-16T08:35:53Z – codex:gpt-5:python-pedro:implementer – shell_pid=44082 – Assigned agent via action command
- 2026-07-16T08:49:20Z – codex:gpt-5:python-pedro:implementer – shell_pid=44082 – Forced only past the known unrelated primary analysis-report.md residue (CLI reported it as WP03-owned despite WP03 owning only core mission creation files). Ready for review: campsite baseline 18/18 preserved with no safe litter; RED 6/6 exposed hard-coded/empty behavior; mapped override and package-default content now flow through create_mission_core before state creation. Core 24/24 and adjacent CLI 36/36 pass; Ruff check exit 0; mypy --strict exit 0; diff-cover 100% (8/8 changed production lines). Live CLI/tracker callers verified and old spec-template probes removed. Commit 3415b0c99.
- 2026-07-16T08:49:56Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=44082 – Started review via action command
- 2026-07-16T08:55:27Z – user – shell_pid=44082 – Review passed: forced only past known unrelated primary analysis-report.md residue falsely classified as WP03-owned. Reviewer Renata incremental/reverse-spec pass confirmed mapped spec selection reaches live create_mission_core callers; override/package bytes, null/missing/unresolved fail-closed behavior, pre-state lifecycle boundary, metadata/events/created_files preservation, and removal of hard-coded probes. Core 24/24 and adjacent read-only CLI 36/36 pass; Ruff, mypy --strict, diff-check pass; diff-cover 100%. Anti-patterns: dead code PASS; synthetic fixtures PASS; silent empty return PASS; FR coverage PASS; frozen surface PASS; locked decisions PASS; shared ownership PASS; production fragility PASS.
