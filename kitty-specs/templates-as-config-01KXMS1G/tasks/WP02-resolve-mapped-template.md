---
work_package_id: WP02
title: Resolve Artifact Keys through Activated Template Configuration
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: feat/templates-as-config
merge_target_branch: feat/templates-as-config
branch_strategy: Planning artifacts for this mission were generated on feat/templates-as-config. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/templates-as-config unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 2 - Shared Selection Contract
assignee: ''
agent: "codex:gpt-5:reviewer-renata:reviewer"
shell_pid: "44082"
history:
- at: '2026-07-16T06:39:25Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/runtime/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/runtime/resolver.py
- src/specify_cli/cli/commands/agent/mission.py
- tests/runtime/test_resolver_unit.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Resolve Artifact Keys through Activated Template Configuration

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

Add one shared, typed content-template API that converts an artifact kind into the activated mission type's mapped filename and then delegates to the unchanged five-tier path resolver.

This WP is complete when:

- `spec`/`plan` selection uses `ResolvedMissionType.template_set`, never conventional filenames or profile defaults.
- Existing override → legacy → global mission → global → doctrine package precedence remains byte-for-byte effective for the mapped filename.
- Null mapping, missing key, and unresolvable mapped filename fail with actionable context naming mission type and artifact kind.
- Known configured failures never borrow a software-development template.
- The legacy/meta-less boundary is preserved but not expanded.
- The maintained `mission` shim exposes a deliberate patch/import seam for the plan command without acquiring business logic.
- Changed/new production lines meet the 90% coverage floor.

## Context & Constraints

Prerequisite WP01 must be approved. Read:

- `kitty-specs/templates-as-config-01KXMS1G/contracts/template-resolution-contract.md`
- `kitty-specs/templates-as-config-01KXMS1G/research.md`
- `kitty-specs/templates-as-config-01KXMS1G/data-model.md`
- `src/specify_cli/runtime/resolver.py`
- `src/specify_cli/cli/commands/agent/mission.py`

The existing `resolve_template(name, project_dir, mission="software-dev")` is the second-stage path resolver. Do not reorder or replace its tiers. The new entry point must not expose a default mission value that lets callers accidentally infer software-development. It may accept a `ResolvedMissionType` directly or resolve one through a clearly typed context input, but it must use the activated context rather than scanning doctrine files.

Do not change command-template resolution, workflow selection, mission enumeration, meta-less fallback policy, or package copy behavior.

## Branch Strategy

- **Strategy**: Planning artifacts are on `feat/templates-as-config`; implementation runs in the lane worktree computed in `lanes.json` and merges back into `feat/templates-as-config`.
- **Planning base branch**: `feat/templates-as-config`
- **Merge target branch**: `feat/templates-as-config`
- **Implementation command**: `spec-kitty agent action implement WP02 --agent codex`

WP02 depends on WP01. Let Spec Kitty resolve the lane base; do not manually branch from an unmerged worktree.

## Review Feedback

Inspect the WP status event stream for review feedback before editing. Address all feedback and append responses chronologically to the Activity Log.

## Subtasks & Detailed Guidance

### T007 — Campsite-clean WP02-owned resolver/shim surfaces before feature edits

- **Purpose**: Establish a clean resolver baseline before introducing the new selection contract.
- **Steps**:
  1. Inspect all owned files plus focused Sonar/local findings for resolver-domain litter.
  2. Run the existing resolver and command import tests as a preservation baseline.
  3. Remove only behavior-neutral dead imports/helpers, stale selector comments, misleading defaults documentation, or equivalent owned-file debt.
  4. If an item cannot be safely cleared, record a frozen baseline and no-growth constraint in the Activity Log.
  5. Re-run the preservation tests and record a distinct campsite entry before T008 begins RED work.
- **Files**: All owned files, without broadening the ownership map.
- **Parallel?**: No; first subtask.
- **Validation**: No selection behavior changes during this step; cleanup evidence is separable from feature evidence.

### T008 — Add red happy-path and override-precedence tests for artifact-key selection

- **Purpose**: Prove the new first-stage mapping composes with the current second-stage resolver.
- **Steps**:
  1. Add focused tests around the proposed public seam in `tests/runtime/test_resolver_unit.py`.
  2. Build a resolved software-development context whose mapping names a non-conventional fixture filename; assert the exact mapped name is searched.
  3. Stage competing files at permitted tiers and assert the existing winner remains unchanged.
  4. Cover at least project override and package default; retain existing legacy/global coverage rather than duplicating every resolver test.
  5. Assert the returned `ResolutionResult` still carries path, tier, and mission identity.
  6. Run red before production changes.
- **Files**: `tests/runtime/test_resolver_unit.py`.
- **Parallel?**: Can be authored alongside T009 before T010, with careful coordination in the shared test file.
- **Validation**: Red failure must arise because artifact-key selection does not yet exist, not because the five-tier fixture is malformed.

### T009 — Add red null, missing-key, and unresolved-file diagnostic tests

- **Purpose**: Pin fail-closed behavior and actionable error content.
- **Steps**:
  1. Cover a known activated context with `template_set=None`.
  2. Cover a non-null mapping missing the requested artifact key.
  3. Cover a mapping entry whose filename is absent from every permitted tier.
  4. Assert each diagnostic includes the mission type and requested artifact kind; the unresolved case should also expose the mapped filename where safe.
  5. Prove no fallback call searches under software-development for the first two cases.
  6. Choose a typed exception or explicit unavailable result consistent with current CLI boundaries and document it.
- **Files**: `tests/runtime/test_resolver_unit.py`.
- **Parallel?**: Yes, with T008 before implementation.
- **Notes**: Avoid brittle whole-message assertions; pin stable required fragments and error type/fields.

### T010 — Implement the typed two-stage mapped-template resolution seam

- **Purpose**: Establish the single consumer API for all content-template readers in this slice.
- **Steps**:
  1. Add a clearly named public function and any narrow typed domain error/result in `src/specify_cli/runtime/resolver.py`.
  2. Require an artifact kind and activated resolved mission context or inputs sufficient to obtain it without default inference.
  3. Read the filename only from `ResolvedMissionType.template_set`.
  4. Validate null/missing/blank states before file resolution.
  5. Delegate the filename to existing `resolve_template` with the resolved mission type ID.
  6. Translate `FileNotFoundError` only as needed to add mission/artifact diagnostic context while retaining useful cause chaining.
  7. Export the seam in `__all__` if the module uses it as its public boundary.
- **Files**: `src/specify_cli/runtime/resolver.py`.
- **Parallel?**: No; driven by T008/T009.
- **Notes**: Keep filename mapping and filesystem precedence visibly separate in code and docstrings.

### T011 — Preserve the isolated legacy/typeless boundary without new inference

- **Purpose**: Prevent issue #2658 from accidentally implementing or changing issue #2660.
- **Steps**:
  1. Inventory existing typeless callers and `get_mission_for_feature` compatibility behavior.
  2. Make the new configured-template seam reject `ResolvedMissionType.mission_type is None` with `TemplateConfigurationError`; the stable diagnostic must name mission type `<typeless>` and the requested artifact kind.
  3. Keep existing typeless readers on their unchanged, explicit legacy compatibility branch outside the new seam until issue #2660.
  4. Add tests proving neutral/blank input is rejected by the new seam and never converted to software-development.
  5. Prove known activated mission types always use the new seam and never route through the legacy branch.
  6. Do not remove or broaden the separately owned fallback; avoid widening `resolve_template`'s default parameter usage.
- **Files**: `src/specify_cli/runtime/resolver.py`, `tests/runtime/test_resolver_unit.py`.
- **Parallel?**: No; refine T010 after the core happy path passes.
- **Validation**: Search the new/changed code for new literal defaults and explain every remaining match in owned files.

### T012 — Expose the shared seam through the maintained CLI patch boundary and validate it

- **Purpose**: Preserve the de-godded mission command's historical patchability while keeping logic in the runtime resolver.
- **Steps**:
  1. Add a deliberate re-export in `src/specify_cli/cli/commands/agent/mission.py` beside the existing `resolve_template` re-export.
  2. Do not add branching or mapping logic to the shim.
  3. Update resolver tests/import assertions as needed to prove the symbol is available without import cycles.
  4. Run focused resolver tests, relevant command-module import tests, Ruff, and scoped mypy.
  5. Inspect imports for a runtime ↔ charter cycle; use established lazy-import patterns only if needed and document why.
  6. Run pytest-cov for the owned production modules, emit XML, and enforce `diff-cover coverage.xml --compare-branch <resolved-lane-base> --fail-under=90` (or repository-equivalent changed/new-code coverage).
  7. Inspect uncovered changed lines and close them with behavior-focused tests; do not reduce the threshold.
- **Files**: All three owned files.
- **Parallel?**: No; final integration task.
- **Validation**: Importing the plan command and runtime resolver in either test order must remain stable.

## Test Strategy

Testing is mandatory because this seam implements FR-003–FR-006 and is consumed by two CLI paths.

- Happy path with a deliberately non-conventional mapped filename.
- Existing tier winner preserved after mapping.
- Null mapping, missing key, missing file.
- Neutral/typeless input never becomes software-development.
- Stable typed diagnostics and exception chaining.
- Import/patch seam remains usable.
- Changed/new production-line coverage is at least 90% against the resolved lane base.

Run `tests/runtime/test_resolver_unit.py` and the smallest command import/phase test needed for the re-export. Do not run the full suite.

## Risks & Mitigations

- **Layer cycle**: keep mapping resolution at a one-way boundary and use type-only/lazy imports if existing architecture requires it.
- **Magic default survives**: make the new function require explicit context and test neutral input.
- **Tier regression**: call the unchanged resolver and assert existing `ResolutionTier` results.
- **Diagnostic loss**: preserve original `FileNotFoundError` as the chained cause.
- **Shim growth**: re-export only; no business logic in `mission.py`.
- **Coverage illusion**: use pytest-cov plus diff-cover and inspect all uncovered changed production lines.

## Definition of Done

- [ ] T007–T012 complete.
- [ ] A distinct behavior-preserving campsite entry precedes feature RED evidence.
- [ ] New API is typed, documented, and exported through the intended seams.
- [ ] Happy, override, null, missing-key, missing-file, and neutral tests pass.
- [ ] Existing resolver tier tests remain green.
- [ ] Ruff and scoped mypy pass.
- [ ] Changed/new production-line coverage is at least 90% against the resolved lane base.
- [ ] No source selection depends on `software-dev-default` or conventional content filenames.
- [ ] Only owned files changed, barring a documented non-overlapping exception.

## Review Guidance

Reviewers should trace a request from artifact kind to mapping to filename to existing `_resolve_asset`. Reject any path that skips the resolved context, scans filesystem mission types as activation, or silently uses the default argument of `resolve_template`. Verify error messages identify configuration rather than merely reporting a generic missing path. Confirm the mission shim remains a re-export-only module.

The handoff must show one compact outcome matrix with:

- configured key and winning override tier;
- configured key and package-default tier;
- null mapping;
- missing artifact key;
- mapped filename absent from all tiers;
- neutral/typeless input remaining outside the new inference contract.

## Activity Log

Append entries oldest to newest using `YYYY-MM-DDTHH:MM:SSZ – agent_id – action`.

- 2026-07-16T06:39:25Z – system – Prompt created via `/spec-kitty.tasks`.

Status is managed in `status.events.jsonl`; use Spec Kitty task movement commands rather than editing status frontmatter.
- 2026-07-16T08:15:56Z – codex:gpt-5:python-pedro:implementer – shell_pid=44082 – Assigned agent via action command
- 2026-07-16T08:18:35Z – codex:gpt-5:python-pedro:implementer – shell_pid=44082 – Campsite T007 complete before feature edits: fresh lane required uv sync --frozen --all-extras after uv run omitted filelock; preservation baseline tests/runtime/test_resolver_unit.py 20 passed; Ruff owned files 0 issues; no safe behavior-neutral litter identified, freeze clean baseline/no-growth.
- 2026-07-16T08:27:18Z – codex:gpt-5:python-pedro:implementer – shell_pid=44082 – Implementation validation: configured spec override -> OVERRIDE; configured spec package default -> PACKAGE_DEFAULT; null mapping -> TemplateConfigurationError; missing key -> TemplateConfigurationError; missing file -> TemplateConfigurationError with FileNotFoundError cause; typeless -> TemplateConfigurationError '<typeless>' with no resolver call. pytest resolver 29 passed; import/setup-plan 15 passed; diff-scoped Ruff 0 issues exit 0; scoped mypy --strict clean; diff-cover 100% (27 executable changed lines). Reader wiring intentionally remains with dependent WP03/WP04 owners.
- 2026-07-16T08:28:01Z – codex:gpt-5:python-pedro:implementer – shell_pid=44082 – Ready for independent review: forced only past false-positive primary analysis-report.md ownership preflight; lane implementation is committed/clean at 108d55618. Configured artifact-key resolution fail-closes, typeless is rejected, five-tier precedence and shim preserved; 44 tests pass, Ruff/mypy clean, diff coverage 100%.
- 2026-07-16T08:29:17Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=44082 – Started review via action command
- 2026-07-16T08:29:35Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=44082 – Started review via action command
- 2026-07-16T08:34:50Z – user – shell_pid=44082 – Review passed; force used only to bypass known unrelated untracked primary analysis-report.md falsely attributed to WP02 ownership. Evidence: explicit typed mapping seam; contextual fail-closed null/missing/blank/unresolved/<typeless> behavior; unchanged five-tier delegation; shim re-export only; 34 focused tests, Ruff, strict mypy, two-way import checks, and 100% diff coverage; only 3 owned implementation files changed.
