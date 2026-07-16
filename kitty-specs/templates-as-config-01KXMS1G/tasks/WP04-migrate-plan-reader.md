---
work_package_id: WP04
title: Scaffold and Compare Plans from Mission Configuration
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
- T019
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 3 - Production Reader Migration
assignee: ''
agent: "codex:gpt-5:reviewer-renata:reviewer"
shell_pid: "44082"
history:
- at: '2026-07-16T06:39:25Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
- tests/integration/test_specify_plan_commit_boundary.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Scaffold and Compare Plans from Mission Configuration

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

Migrate both plan scaffolding and pristine-template comparison to the activated mission type's mapped `plan` template while preserving the setup-plan lifecycle and commit boundary.

This WP is complete when:

- `_scaffold_plan_template` resolves the `plan` artifact through the WP02 seam.
- `_is_plan_pristine` compares against the exact same effective mapped template winner.
- Software-development package and override content remain unchanged.
- Null mapping, missing `plan`, and missing mapped file produce actionable failure with no software-development substitution.
- Existing scaffold-only, insufficient, substantive, commit hash, JSON, branch contract, documentation wiring, and lifecycle behavior remain green.
- Resolution does not emit duplicate legacy warnings or select different tiers between scaffold and comparison.
- Changed/new production lines meet the 90% coverage floor.

## Context & Constraints

WP02 must be approved. Read:

- `kitty-specs/templates-as-config-01KXMS1G/contracts/template-resolution-contract.md`
- `kitty-specs/templates-as-config-01KXMS1G/quickstart.md`
- `src/specify_cli/cli/commands/agent/mission_setup_plan.py`
- `tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py`
- `tests/integration/test_specify_plan_commit_boundary.py`

The command currently hard-codes `_mission.resolve_template("plan-template.md", repo_root, mission="software-dev")` in both scaffold and pristine paths. Replace both with the shared mapped-template patch seam while retaining the de-godded module's historical `mission.<symbol>` patch architecture.

Do not modify SaaS authentication policy, feature-dir routing, branch selection, documentation mission wiring, plan substantiveness rules, or commit placement except where required to pass the resolved template result through unchanged.

## Branch Strategy

- **Strategy**: Planning artifacts are on `feat/templates-as-config`; implementation runs in the lane worktree computed in `lanes.json` and merges back into `feat/templates-as-config`.
- **Planning base branch**: `feat/templates-as-config`
- **Merge target branch**: `feat/templates-as-config`
- **Implementation command**: `spec-kitty agent action implement WP04 --agent codex`

WP04 and WP03 are parallel after WP02. Use only the WP04 lane worktree and do not edit mission creation.

## Review Feedback

Inspect status events for `review_ref` before editing. Resolve all feedback and append chronological Activity Log entries.

## Subtasks & Detailed Guidance

### T019 — Campsite-clean WP04-owned plan-command surfaces before feature edits

- **Purpose**: Establish a clean, behavior-preserving setup-plan baseline before replacing template authority.
- **Steps**:
  1. Inspect every owned file and focused Sonar/local findings for plan-command-domain litter.
  2. Run the existing phase and commit-boundary tests as a preservation baseline.
  3. Remove only behavior-neutral dead imports/helpers, stale selector comments, or misleading local type annotations inside ownership.
  4. If cleanup cannot safely resolve an item, record its frozen baseline and no-growth constraint in the Activity Log.
  5. Re-run preservation tests and record a distinct campsite entry before T020 begins RED work.
- **Files**: All owned files only.
- **Parallel?**: No; first subtask.
- **Validation**: No plan scaffolding, comparison, lifecycle, or commit behavior changes during campsite cleanup.

### T020 — Add red plan-scaffold tests for mapped filenames and override winners

- **Purpose**: Pin the production plan phase to artifact-key configuration rather than conventional filenames.
- **Steps**:
  1. Extend `_scaffold_plan_template` phase tests to patch the new maintained seam.
  2. Use a resolved context whose `plan` mapping names a non-conventional fixture file.
  3. Assert the mapped file is copied to `plan.md` and the resolver receives the real mission type.
  4. Add/extend the integration fixture for doctrine package default.
  5. Add an override-tier fixture and assert its exact bytes win.
  6. Run red against current hard-coded `plan-template.md` behavior.
- **Files**: Both owned test files.
- **Parallel?**: No; primary acceptance contract.
- **Validation**: The integration path must execute setup-plan logic, not just the WP02 helper.

### T021 — Add red plan tests for null, missing-key, and unresolved-file diagnostics

- **Purpose**: Ensure plan setup fails closed and identifies configuration errors.
- **Steps**:
  1. Cover `template_set: null` for a known activated type.
  2. Cover a mapping without `plan`.
  3. Cover a mapped filename absent from all tiers.
  4. Assert mission type and artifact kind appear in the stable diagnostic surface.
  5. Assert `plan.md` is not scaffolded from software-development and no plan commit is created.
  6. Verify JSON mode returns structured failure rather than leaking a traceback where the command architecture expects handled errors.
- **Files**: `tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py` and integration file where process behavior is needed.
- **Parallel?**: Yes, can be written alongside T020 before implementation.
- **Notes**: Do not change the separately observed SaaS sync severity in this mission.

### T022 — Migrate plan scaffolding to the shared mapped-template seam

- **Purpose**: Remove hard-coded software-development authority from the plan writer.
- **Steps**:
  1. Obtain the mission type from the feature directory using the existing canonical helper.
  2. Call the WP02 symbol through the `_mission` shim with artifact kind `plan` and explicit repository/feature context.
  3. Copy the returned effective path with existing metadata/encoding behavior.
  4. Preserve the no-op when `plan.md` already exists.
  5. Preserve exception cause and allow the command boundary to render actionable output.
  6. Remove the explicit filename and `mission="software-dev"` arguments from the scaffold path.
- **Files**: `src/specify_cli/cli/commands/agent/mission_setup_plan.py`.
- **Parallel?**: No; follows T020/T021.
- **Validation**: Existing phase patching must remain stable through the mission shim.

### T023 — Make pristine comparison use the same effective resolved template

- **Purpose**: Prevent scaffolding and commit classification from comparing different files.
- **Steps**:
  1. Route `_is_plan_pristine` through the same mapped-template seam and same mission context as scaffolding.
  2. Prefer passing/reusing the resolution result where it avoids duplicate resolution and warnings without distorting phase boundaries.
  3. Assert byte-equal scaffold remains pristine.
  4. Assert modified but insufficient plan is not pristine and follows existing blocked behavior.
  5. Cover an override winner so comparison is against the override, not package default.
- **Files**: Production phase module and both owned tests.
- **Parallel?**: No; coupled to T022.
- **Notes**: Do not weaken `_is_substantive` or treat arbitrary prose as completed planning.

### T024 — Preserve plan commit, branch, JSON, and lifecycle semantics

- **Purpose**: Prove only template authority changed.
- **Steps**:
  1. Run existing scaffold-only, insufficient, and substantive commit tests.
  2. Assert substantive plan commit hash and status remain exposed in JSON.
  3. Preserve current/target/base/planning/merge branch fields.
  4. Preserve `SpecifyCompleted`, `PlanStarted`, and `PlanCompleted` ordering/conditions.
  5. Preserve documentation wiring behavior for documentation missions once the template contract allows/denies the artifact.
  6. Avoid “fixing” context/coordination path inconsistencies recorded in tooling friction.
- **Files**: Both owned test modules; production only for narrow pass-through adjustments.
- **Parallel?**: Can be audited while red tests are prepared, but final assertions follow T022/T023.
- **Validation**: No new commit occurs for missing configuration or an unchanged/pristine boundary beyond established behavior.

### T025 — Run focused plan-phase and commit-boundary quality gates

- **Purpose**: Produce objective reader-specific handoff evidence.
- **Steps**:
  1. Run `tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py`.
  2. Run affected cases in `tests/integration/test_specify_plan_commit_boundary.py`.
  3. Run Ruff on changed files.
  4. Run scoped mypy for the production phase module.
  5. Search the production file for hard-coded `plan-template.md`/software-development template selection and justify any non-selection mentions.
  6. Review the diff for issue #2659–#2661 scope and non-owned edits.
  7. Run pytest-cov for the setup-plan production module, emit XML, and enforce `diff-cover coverage.xml --compare-branch <resolved-lane-base> --fail-under=90` (or repository-equivalent changed/new-code coverage).
  8. Inspect uncovered changed lines and add behavior-focused tests rather than lowering the threshold.
- **Files**: No new files.
- **Parallel?**: No; final gate.

## Test Strategy

Tests are mandatory under FR-007/FR-009.

- Phase-unit red tests for mapped filename and all three failure states.
- Integration test for real package-default and override file bytes.
- Scaffold/pristine identity using the same winner.
- Existing two-pass plan and commit-boundary regression coverage.
- JSON/branch/lifecycle preservation.
- Ruff and scoped mypy.
- Changed/new production-line coverage of at least 90% against the resolved lane base.

Use command-local SaaS sync disablement when running tests/commands if the environment inherits `SPEC_KITTY_ENABLE_SAAS_SYNC=1`; do not change product SaaS policy in this WP.

## Risks & Mitigations

- **Different winners**: reuse one seam/context and assert override-based pristine behavior.
- **Duplicate warnings/I/O**: reuse the resolution result where compatible with phase design.
- **Patch seam break**: call through `_mission` and preserve deliberate shim re-export.
- **Lifecycle drift**: keep existing integration tests green and add only template-specific assertions.
- **Scope distraction**: recorded CLI routing/SaaS issues remain outside #2658.
- **Coverage illusion**: pair pytest-cov XML with diff-cover and inspect uncovered changed lines.

## Definition of Done

- [ ] T019–T025 complete.
- [ ] A distinct behavior-preserving campsite entry precedes feature RED evidence.
- [ ] Mapped package and override plan content passes through the real command path.
- [ ] Null/missing/unresolved states fail actionably without commit or borrowed template.
- [ ] Scaffold and pristine checks resolve the same winner.
- [ ] Existing branch, JSON, lifecycle, and commit-boundary tests pass.
- [ ] Ruff and scoped mypy pass.
- [ ] Changed/new production-line coverage is at least 90% against the resolved lane base.
- [ ] Only owned files changed or a justified non-overlapping exception is recorded.

## Review Guidance

Review both hard-coded call sites; fixing only scaffold while leaving pristine comparison on software-development is a rejection. Verify the real mission type comes from mission metadata/context and the mapped result retains override precedence. Re-run the substantive-plan commit test and inspect JSON branch contract. Do not accept broadened changes to SaaS or coordination routing.

## Activity Log

Append entries oldest to newest using `YYYY-MM-DDTHH:MM:SSZ – agent_id – action`.

- 2026-07-16T06:39:25Z – system – Prompt created via `/spec-kitty.tasks`.

Status is managed in `status.events.jsonl`; use Spec Kitty task movement commands rather than editing status frontmatter.
- 2026-07-16T08:36:13Z – codex:gpt-5:python-pedro:implementer – shell_pid=44082 – Assigned agent via action command
- 2026-07-16T08:56:09Z – codex:gpt-5:python-pedro:implementer – shell_pid=44082 – Ready for review: configured plan mapping drives scaffold and pristine comparison; typed null/missing/unresolved failures are structured, typeless compatibility retained; 95 tests pass, Ruff/strict mypy pass, diff coverage 100%. Forced only because the known unrelated primary analysis-report.md residue is falsely classified as WP04-owned; implementation worktree and owned code/test files are committed cleanly.
- 2026-07-16T08:57:04Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=44082 – Started review via action command
- 2026-07-16T09:02:03Z – user – shell_pid=44082 – Review passed: live setup-plan resolves the configured plan mapping once and shares its exact winner across scaffold/pristine checks; package and override bytes, null/missing/unresolved fail-closed diagnostics, typeless legacy compatibility, commit/JSON/branch/lifecycle behavior, ownership, Ruff, strict mypy, 56 focused tests, and 100% diff coverage verified. Anti-patterns all PASS. Narrow force used only because the known unrelated untracked analysis-report.md residue is falsely classified as WP04-owned.
