---
work_package_id: WP01
title: Project Doctrine Template Mapping into Resolved Context
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-009
tracker_refs: []
planning_base_branch: feat/templates-as-config
merge_target_branch: feat/templates-as-config
branch_strategy: Planning artifacts for this mission were generated on feat/templates-as-config. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/templates-as-config unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Canonical Configuration Foundation
assignee: ''
agent: "codex:gpt-5:reviewer-renata:reviewer"
shell_pid: "44082"
history:
- at: '2026-07-16T06:39:25Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/mission_type_profiles.py
- tests/charter/test_resolved_mission_type_context.py
- tests/doctrine/missions/test_mission_type_repository.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Project Doctrine Template Mapping into Resolved Context

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

Complete the reserved `ResolvedMissionType.template_set` slot using the activated doctrine `MissionType` artifact as its sole authority.

This WP is complete when:

- The shipped `software-dev` resolved context exposes exactly `spec → spec-template.md` and `plan → plan-template.md`.
- Activated `documentation`, `research`, and `plan` mission types expose explicit null, matching their artifacts.
- A typeless neutral context remains null and never becomes software-development configuration.
- The public resolved value cannot mutate repository-owned canonical state.
- Repeated reads are deterministic and cached.
- Constructing/using the action-sequence hot path stays inside the existing 100 ms typical-local-project budget and does not eagerly read the mapping slot.
- Focused pytest, Ruff, and mypy checks pass for the owned files, and changed/new production lines meet the 90% coverage floor.

## Context & Constraints

Read these mission artifacts before editing:

- `kitty-specs/templates-as-config-01KXMS1G/spec.md`
- `kitty-specs/templates-as-config-01KXMS1G/plan.md`
- `kitty-specs/templates-as-config-01KXMS1G/data-model.md`
- `kitty-specs/templates-as-config-01KXMS1G/contracts/template-resolution-contract.md`
- `.kittify/charter/charter.md`

Current code facts:

- `src/doctrine/missions/models.py` already models `MissionType.template_set` as `dict[str, str] | None`.
- The software-development YAML already declares both in-scope keys; the other built-ins declare null.
- `ResolvedMissionType.template_set` is currently a reserved `str | None` field populated with `None`.
- Other disk-backed fields use private thunks plus `cached_property` to protect the runtime hot path.
- `MissionTypeProfile.template_set` is a legacy/profile governance string and MUST NOT populate this mapping.

Do not redesign mission-type activation, enumerate filesystem mission types as availability, edit doctrine YAML values, or change release/version metadata.

## Branch Strategy

- **Strategy**: Planning artifacts are on `feat/templates-as-config`; implementation runs in the lane worktree computed in `lanes.json` and merges back into `feat/templates-as-config`.
- **Planning base branch**: `feat/templates-as-config`
- **Merge target branch**: `feat/templates-as-config`
- **Implementation command**: `spec-kitty agent action implement WP01 --agent codex`

Enter only the workspace returned for WP01 by the Spec Kitty runtime. Do not implement in the primary planning checkout and do not create a worktree manually.

## Review Feedback

Before implementation, inspect the status event stream for `review_ref`. If this WP has been rejected, treat every referenced review item as required work and append responses to the Activity Log in chronological order.

## Subtasks & Detailed Guidance

### T001 — Campsite-clean WP01-owned context/repository surfaces before feature edits

- **Purpose**: Start from a clean, behavior-preserving baseline and prevent nearby debt from being carried into the new mapping seam.
- **Steps**:
  1. Inspect every owned production/test file and the current focused Sonar/local static findings before writing a feature test.
  2. Run the existing focused tests for those files and record the preservation baseline.
  3. Resolve only domain-matched litter in the owned files: stale reserved-slot comments, dead helpers/imports, misleading type annotations, or already-reported local issues whose cleanup preserves behavior.
  4. If a litter class cannot safely be cleared in this WP, record its frozen baseline and an explicit no-growth constraint in the Activity Log.
  5. Re-run the preservation tests and create a distinct campsite Activity Log entry before starting T002's RED test work.
- **Files**: All owned files, without expanding ownership.
- **Parallel?**: No; this is the first implementation subtask.
- **Validation**: The campsite step causes no feature behavior change and has separate before/after evidence from the later authority-swap edits.

### T002 — Add red doctrine/context tests for exact mapping and explicit null values

- **Purpose**: Pin the authored doctrine boundary and the public resolved-context behavior before production changes.
- **Steps**:
  1. In `tests/doctrine/missions/test_mission_type_repository.py`, load built-in artifacts through the real repository boundary.
  2. Assert the exact software-development mapping, including key names and filenames.
  3. Assert explicit null for documentation, research, and plan built-ins.
  4. In `tests/charter/test_resolved_mission_type_context.py`, replace the reserved-slot assertion with parameterized exact projection assertions.
  5. Include the neutral/typeless context and prove it remains null.
  6. Run the new tests red before touching production code and preserve the failing output in the implementation notes/activity entry.
- **Files**: Both owned test files.
- **Parallel?**: No; these assertions define the implementation contract.
- **Validation**: Failures must demonstrate that the current context returns `None` for software-development, not fail due to fixture/setup mistakes.

### T003 — Replace the reserved slot with a typed lazy/cached mapping projection

- **Purpose**: Make the resolved bundle expose the mapping without adding eager I/O.
- **Steps**:
  1. Change the public field shape from the profile string type to `Mapping[str, str] | None` or an equivalently immutable read shape.
  2. Add a private thunk for the doctrine mapping, excluded from equality/repr consistently with existing deferred fields.
  3. Expose the public value via `cached_property`; neutral context returns null without a thunk.
  4. Copy/freeze the repository result so a consumer cannot mutate cached doctrine model state.
  5. Update comments/docstrings that still call the slot reserved, but avoid touching unrelated legacy profile-string documentation.
- **Files**: `src/charter/mission_type_profiles.py`.
- **Parallel?**: No; depends on T002's red contract.
- **Notes**: Keep ordering deterministic. Python dict insertion order is acceptable only if the source/copy path is deterministic and tests prove it.

### T004 — Source the projection only from the activated doctrine mission-type artifact

- **Purpose**: Enforce doctrine → charter activation → resolved context as the single authority chain.
- **Steps**:
  1. Use the existing doctrine mission-type repository/service seam rather than parsing YAML directly.
  2. Bind lookup to the already resolved/registered `type_key`; do not scan all mission files to infer availability.
  3. Preserve explicit null exactly.
  4. Ensure unknown/unactivated behavior continues to follow existing resolver policy before the mapping thunk is exposed.
  5. Confirm no read of `MissionTypeProfile.template_set`, charter compiler default, or `software-dev-default` contributes to the mapping.
- **Files**: `src/charter/mission_type_profiles.py`.
- **Parallel?**: No; completes T003.
- **Validation**: A project/profile string override must not change the artifact mapping asserted in context tests.

### T005 — Prove immutability/determinism and protect the 100 ms hot-path budget

- **Purpose**: Satisfy NFR-001/NFR-002 and prevent subtle shared-state regressions.
- **Steps**:
  1. Resolve the same activated type repeatedly and assert identical ordered items.
  2. Read `bundle.template_set` twice and prove repository access occurs once for that bundle.
  3. Attempt consumer mutation when the chosen type permits it; assert mutation is rejected or isolated from later resolutions.
  4. Extend the existing hot-path/performance style used in this test module rather than inventing a flaky wall-clock harness.
  5. Assert action-sequence access alone does not trigger template repository I/O.
- **Files**: `tests/charter/test_resolved_mission_type_context.py`.
- **Parallel?**: Yes, once T002 has established fixtures; coordinate before editing the shared file.
- **Notes**: Use a generous, repository-established timing technique and a typical local fixture. Do not benchmark network or git operations.

### T006 — Run focused context/repository type, style, behavior, and changed-code coverage gates

- **Purpose**: Hand off a reviewable foundational seam with objective evidence.
- **Steps**:
  1. Run the two owned pytest modules.
  2. Run any immediately adjacent existing mission-type resolution test needed to catch import/activation regressions.
  3. Run Ruff on changed files.
  4. Run mypy strict using the repository's scoped invocation for `src/charter/mission_type_profiles.py`.
  5. Run the owned tests with pytest-cov XML output and then `diff-cover coverage.xml --compare-branch <resolved-lane-base> --fail-under=90` (or the repository-equivalent changed/new-code command).
  6. Inspect any uncovered changed production line; add a behavior-focused test or explain why the line is excluded by repository policy rather than weakening the threshold.
  7. Inspect the diff for profile-string leakage, eager reads, version edits, or non-owned changes.
- **Files**: No additional files.
- **Parallel?**: No; final WP gate.
- **Validation**: Record commands and results in the Activity Log/implementation handoff.

## Test Strategy

Testing is mandatory under FR-009 and the charter's ATDD-first rule.

- Red-first: exact software-development mapping through the public bundle.
- Boundary: real doctrine repository values for all four built-ins.
- Negative: explicit null and typeless neutral context.
- Structural: mapping is not sourced from profile defaults.
- Non-functional: cached deterministic read and hot-path non-regression.
- Coverage: at least 90% of changed/new production lines in this WP, measured against the resolved lane base.

Do not run the entire repository suite. Use the owned test modules plus the smallest adjacent resolver tests necessary to prove imports and activation behavior.

## Risks & Mitigations

- **Eager I/O**: follow the existing thunk/cached-property design and test call counts.
- **Mutable leakage**: return an immutable/copy boundary and test repeated resolutions after attempted mutation.
- **Wrong authority**: repository-backed tests and a profile-override negative case prevent substitution.
- **Type ambiguity**: distinguish the legacy string field from this artifact mapping in names and annotations.
- **Scope creep**: no activation enumeration or fallback retirement belongs here.
- **Coverage illusion**: pair pytest-cov with diff-cover against the lane base and inspect uncovered changed lines.

## Definition of Done

- [ ] T001–T006 are complete and marked through Spec Kitty status commands.
- [ ] A distinct behavior-preserving campsite baseline/cleanup entry precedes feature RED evidence.
- [ ] All owned tests pass after demonstrating the intended red state first.
- [ ] `ResolvedMissionType.template_set` exposes exact doctrine mapping/null semantics.
- [ ] Hot-path and deterministic/cached assertions pass.
- [ ] Ruff and scoped mypy pass.
- [ ] Changed/new production-line coverage is at least 90% against the resolved lane base.
- [ ] Only owned files changed, or any exceptional out-of-map edit has a one-line rationale and no overlap.
- [ ] Implementation is ready for a distinct reviewer.

## Review Guidance

Review from the public `resolve_mission_type_context` contract inward. Confirm the mapping comes from the activated doctrine artifact, not the similarly named profile field. Inspect whether the thunk is truly lazy, whether a mutable dictionary can leak, and whether null is preserved for all three non-software built-ins. Reject timing tests that are vacuous or unstable and reject any new software-development inference.

Reviewer evidence should include:

- the exact repository-versus-context mapping matrix;
- a call-count or equivalent proof that lazy access is real;
- the scoped performance measurement and threshold;
- a negative proof that profile overrides do not author artifact mappings;
- confirmation that no doctrine YAML or version file changed.

## Activity Log

Append entries oldest to newest using `YYYY-MM-DDTHH:MM:SSZ – agent_id – action`.

- 2026-07-16T06:39:25Z – system – Prompt created via `/spec-kitty.tasks`.

Status is managed in `status.events.jsonl`; use Spec Kitty task movement commands rather than editing status frontmatter.
- 2026-07-16T07:31:12Z – codex:gpt-5:python-pedro:implementer – shell_pid=6396 – Assigned agent via action command
- 2026-07-16T07:34:23Z – codex:gpt-5:python-pedro:implementer – shell_pid=6396 – T001 campsite baseline complete before RED: owned files clean; uv run --extra test pytest -q tests/charter/test_resolved_mission_type_context.py tests/doctrine/missions/test_mission_type_repository.py => 44 passed, 3 existing DoctrineLayerCollisionWarning warnings; uv run --extra lint ruff check <owned files> => passed; uv run --extra lint mypy --strict src/charter/mission_type_profiles.py => passed. No domain-matched litter required behavior-preserving edits; frozen warning baseline=3 with no-growth constraint.
- 2026-07-16T07:37:44Z – codex:gpt-5:python-pedro:implementer – shell_pid=6396 – T002 RED evidence: targeted repository/context contract run produced 6 expected failures and 18 passes. Failures prove software-dev ResolvedMissionType.template_set remains None/eager field and lacks doctrine-backed lazy cache; repository exact/null assertions already pass. No fixture/setup failures.
- 2026-07-16T07:44:52Z – codex:gpt-5:python-pedro:implementer – shell_pid=6396 – T003-T006 GREEN evidence: immutable MappingProxyType projection is wired through resolve_mission_type_context to the doctrine MissionTypeRepository only; neutral/non-software/unregistered values remain null; profile-string override cannot author mappings. Owned pytest => 55 passed with 4 intentional DoctrineLayerCollisionWarning warnings; adjacent resolver pytest => 32 passed; diff-scoped Ruff => exit 0; scoped mypy --strict => exit 0; diff-cover => 15 changed production lines, 0 missing, 100%; hot-path p95 test remains below 100ms and proves template_set is not cached until accessed; caller grep confirms thunk wiring.
- 2026-07-16T08:09:02Z – codex:gpt-5:python-pedro:implementer – shell_pid=6396 – Ready for review: exact doctrine mapping/null semantics, lazy immutable caching, 55 owned + 32 adjacent tests, Ruff/mypy clean, diff-cover 100%. Forced only because guard misclassified unrelated untracked analysis-report.md as WP01-owned.
- 2026-07-16T08:09:31Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=44082 – Started review via action command
- 2026-07-16T08:14:36Z – user – shell_pid=44082 – Review passed by reviewer-renata: exact software-dev mapping and explicit null matrix verified through production repository/context paths; MappingProxyType defensive copy rejects mutation; cached_property proves one lazy doctrine read per bundle and no eager template read on action-sequence hot path; profile string override cannot author the mapping; 69 focused/adjacent tests passed, Ruff passed, scoped mypy --strict passed, and diff-cover reports 15/15 changed production lines (100%). Anti-patterns: dead code PASS (public seam is wired inside resolver and explicitly consumed by dependent WP02); synthetic fixtures PASS; silent empty returns PASS (three None paths are required null semantics); FR coverage PASS for FR-001/FR-002/FR-009; frozen surface PASS; locked decisions PASS; shared ownership N/A; production fragility PASS (no new raises). No doctrine YAML, release/version, or out-of-scope files changed. Forced transition only because approval guard misclassified unrelated untracked mission analysis-report.md as WP01-owned.
