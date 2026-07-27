---
work_package_id: WP07
title: Remaining Reroutes + Bug Fix + Validation
lane: "done"
dependencies: [WP05, WP06]
requirement_refs:
- FR-017
- NFR-002
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
base_branch: feature/agent-profile-implementation
base_commit: 8eb05adc3d929758c53473e9b6a0ac7dec949a21
created_at: '2026-03-28T11:09:26.777404+00:00'
subtasks:
- T027
- T028
- T029
- T030
phase: Phase 2 - Consumer Rerouting
assignee: ''
agent: "opencode"
shell_pid: '113162'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
review_feedback: feedback://058-mission-template-repository-refactor/WP07/20260329T063105Z-b40c6cdd.md
history:
- timestamp: '2026-03-27T04:37:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer
approved_by: "Stijn Dejongh"
role: reviewer
---

# Work Package Prompt: WP07 – Remaining Reroutes + Bug Fix + Validation

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**



**Verdict**: approved | **Reviewer**: Stijn Dejongh | **Date**: 2026-03-29T08:11:08Z

Reviewed and merged to feature/agent-profile-implementation. Reroutes T027/T028 verified, TemplateResult bug fixed, all acceptance criteria met. | Done override: Branch deleted after manual merge to feature/agent-profile-implementation; merge commit verified on target branch.
**Verdict**: approved | **Reviewer**: Stijn Dejongh | **Date**: 2026-03-29T07:29:48Z

Review passed (2nd review): All 5 acceptance criteria verified. T027-T030 reroutes correctly use MissionTemplateRepository. TemplateResult bug fixed in commit 2ef55498. Test suite: 51 failed / 7295 passed — identical to baseline (zero regressions). Validation grep confirms no direct mission path construction in rerouted callers.
**Verdict**: changes_requested | **Reviewer**: Stijn Dejongh | **Date**: 2026-03-29T06:31:05Z

# WP07 Review Feedback — REJECTED

**Reviewer**: opencode
**Date**: 2026-03-29

## Verdict: REJECT

WP07's core reroute work (T027-T029) is correct and well-implemented. However, the commit bundles massive out-of-scope doctrine changes that violate WP isolation rules and introduce 4 test regressions.

---

## Issue 1: Out-of-scope doctrine pruning (BLOCKING)

**Description**: The single WP07 commit deletes ~39 doctrine files and adds 5 new ones that are entirely outside WP07's scope. WP07's acceptance criteria are limited to:
1. Reroute `constitution/compiler.py`
2. Reroute `specify_cli/constitution/compiler.py`
3. Fix stale path in `feature.py`
4. Full pytest suite passes with zero regressions
5. Validation grep confirms no direct mission path construction

The following out-of-scope changes are included:

- **Deleted agent profiles**: `python-implementer.agent.yaml` (165 lines)
- **Gutted reviewer profile**: Removed tactic/toolguide references, directive references, operating procedures from `reviewer.agent.yaml`
- **Deleted 11 quickstart candidate imports** (`_reference/quickstart-agent-augmented-development/candidates/`)
- **Deleted 2 procedures**: `refactoring.procedure.yaml`, `test-first-bug-fixing.procedure.yaml`
- **Deleted 1 paradigm**: `atomic-design.paradigm.yaml`
- **Deleted 1 styleguide**: `python-conventions.styleguide.yaml`
- **Deleted 1 directive**: `034-test-first-development.directive.yaml`
- **Deleted ~20 shipped tactics** and emptied ~12 refactoring tactic files
- **Deleted toolguide**: `PYTHON_REVIEW_CHECKS.md` + `python-review-checks.toolguide.yaml`
- **Trimmed 4 schema files**: Removed `tactic-references`, `toolguide-references`, `styleguide-references`, `self-review-protocol` from agent-profile schema; removed `anti_patterns`, `notes` from procedure schema; removed `patterns`, `tooling` from styleguide schema; removed `failure_modes`, `notes` from tactic schema
- **Added 5 new tactic/directive files**: `acceptance-test-first.tactic.yaml`, `glossary-curation-interview.tactic.yaml`, `tdd-red-green-refactor.tactic.yaml`, `zombies-tdd.tactic.yaml`, `test-first.directive.yaml`
- **Changed tactic directory layout**: `rglob` → `glob` in multiple test files (flattening shipped tactic subdirectories)

**How to fix**: Split the commit. Keep only the T027-T030 changes (compiler reroutes, feature.py fix, test updates for `MissionRepository` → `MissionTemplateRepository` API rename, and `template_path.read_text()` → `template_path.content` migration fix). Remove all doctrine file deletions, schema modifications, new tactic additions, and profile changes. Those belong in a separate WP or should be discussed with the human first.

---

## Issue 2: 4 test regressions introduced by WP07 (BLOCKING)

**Description**: The following 4 tests pass on the base branch (`feature/agent-profile-implementation`) but fail on WP07:

### 2a: `tests/doctrine/test_shipped_profiles.py::TestShippedProfilesLoad::test_all_seven_profiles_load`
- Test expects exactly 7 profiles, but `generic-agent` still exists in `shipped/`, giving 8
- Root cause: WP07 modified the test to expect 7 (removing `python-implementer` and `generic-agent`) and deleted `python-implementer`, but did NOT move `generic-agent` out of `shipped/`

### 2b: `tests/doctrine/test_shipped_profiles.py::TestShippedProfilesLoad::test_expected_profile_ids_present`
- Same root cause as 2a — `generic-agent` is still in `shipped/` but removed from `EXPECTED_PROFILE_IDS`

### 2c: `tests/doctrine/test_generic_agent_profile.py::test_generic_agent_not_in_shipped`
- WP07 added this new test asserting `generic-agent.agent.yaml` must NOT exist in `shipped/`, but it does exist. The test was written for a state that doesn't match the actual code.

### 2d: `tests/agent/test_review_template_dependency_warnings.py::test_mission_review_template_dependency_warnings`
- `MissionTemplateRepository.get_command_template()` returns a `TemplateResult` object, not a `Path`. The test calls `path.exists()` which fails with `AttributeError: 'TemplateResult' object has no attribute 'exists'`
- The helper function `_assert_required_keys` expects a `Path` but now receives a `TemplateResult`

**How to fix**:
- For 2a-2c: Either move `generic-agent.agent.yaml` from `shipped/` to `_proposed/` (but this is out-of-scope for WP07), or revert the test changes and keep `generic-agent` in the expected set
- For 2d: Use `path.content` instead of `path.read_text()` in the test helper, or extract the path from the `TemplateResult` object

---

## Issue 3: Acceptance criterion #4 not met (BLOCKING)

**Description**: WP07 acceptance criterion #4 states "Full pytest suite passes with zero regressions." The 4 regressions above violate this criterion. All 4 failures are confirmed new (0 failures in these tests on the base branch, 4 on WP07).

**How to fix**: Fix the 4 regressions listed in Issue 2.

---

## Summary

The core reroute logic (T027-T029) is solid and correctly uses `MissionTemplateRepository`. The `feature.py` stale path fix is appropriate. The `MissionRepository` → `MissionTemplateRepository` test renames are legitimate scope for WP07. However, the doctrine pruning is out of scope and the test regressions must be fixed before approval.

**Remediation priority**:
1. Revert all doctrine file deletions, schema changes, and new tactic/directive additions (out of scope)
2. Revert profile changes (python-implementer deletion, reviewer gutting, generic-agent test expectations)
3. Fix the `TemplateResult` vs `Path` bug in `test_review_template_dependency_warnings`
4. Re-run full test suite to confirm zero regressions

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

1. `constitution/compiler.py` uses `MissionTemplateRepository` for mission config access
2. `specify_cli/constitution/compiler.py` uses `MissionTemplateRepository` for mission config access
3. Stale path in `feature.py` line ~1716 is fixed (references pre-migration `specify_cli/missions/` directory)
4. Full `pytest` suite passes with zero regressions
5. Validation grep confirms: no direct mission path construction in production code outside `repository.py`, shipped migrations, and `test_package_bundling.py`

**Success gate**: `pytest` passes. Grep validation clean.

## Context & Constraints

- **Research**: `kitty-specs/058-mission-template-repository-refactor/research/consumer-analysis.md` (see "Additional Files Discovered" section)
- **Prerequisite**: WP05 and WP06 must be complete (all major consumers rerouted)
- **Explicitly excluded from rerouting**:
  - `kernel/paths.py` -- foundational, cannot import from `doctrine` (circular)
  - `specify_cli/manifest.py` -- project-local paths under `.kittify/missions/`
  - `specify_cli/mission.py` -- project-local paths under `.kittify/missions/`
  - `specify_cli/cli/commands/agent/config.py` -- project-local paths under `.kittify/missions/`
  - All migration files in `specify_cli/upgrade/migrations/` -- frozen historical snapshots (C-001)

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP07 --base WP06`

(If WP05 and WP06 both need to be bases, use `--base WP06` since WP06 depends on WP04 which WP05 also depends on. The merge will resolve.)

## Subtasks & Detailed Guidance

### Subtask T027 – Reroute constitution/compiler.py

- **Purpose**: Replace direct `doctrine_root / "missions" / mission / "mission.yaml"` with repository API.
- **Steps**:
  1. **Before**: Run tests:
     ```bash
     pytest tests/ -v -k "compiler" --co -q
     pytest tests/constitution/ -v
     ```
  2. **Read** `src/constitution/compiler.py`, find line ~601 where it constructs `doctrine_root / "missions" / mission / "mission.yaml"`
  3. **Replace** with:
     ```python
     from doctrine.missions import MissionTemplateRepository
     config = MissionTemplateRepository.default().get_mission_config(mission)
     if config is not None:
         # Use config.parsed for the dict data
         # Or config.content for the raw YAML text
     ```
  4. Understand the calling context: What does the compiler do with the mission.yaml content? Does it need the parsed dict, the raw text, or the file path? Adjust the replacement accordingly.
  5. **After**: Re-run tests
- **Files**: `src/constitution/compiler.py`
- **Parallel?**: Yes, independent of T028-T030

### Subtask T028 – Reroute specify_cli/constitution/compiler.py

- **Purpose**: Same pattern as T027 for the legacy copy.
- **Steps**:
  1. **Before**: Run tests related to this compiler
  2. **Read** `src/specify_cli/constitution/compiler.py`, find line ~333
  3. **Apply same replacement** as T027
  4. **After**: Re-run tests
- **Files**: `src/specify_cli/constitution/compiler.py`
- **Parallel?**: Yes, independent of T027

### Subtask T029 – Fix stale path in feature.py

- **Purpose**: Fix a pre-existing bug where `feature.py` references the old `specify_cli/missions/` directory (which was migrated to `doctrine/missions/`).
- **Steps**:
  1. **Read** `src/specify_cli/cli/commands/agent/feature.py`, find line ~1716:
     ```python
     Path(__file__).resolve().parents[3] / "specify_cli" / "missions" / mission_key / "mission.yaml"
     ```
  2. **Understand context**: What is this code trying to do? It's constructing a path to a mission's `mission.yaml`. The `Path(__file__).parents[3]` traversal goes up from `src/specify_cli/cli/commands/agent/feature.py` to the repo root, then down to `specify_cli/missions/` -- but that directory no longer exists (migrated to `doctrine/missions/`).
  3. **Replace** with the appropriate repository call:
     ```python
     from doctrine.missions import MissionTemplateRepository
     config = MissionTemplateRepository.default().get_mission_config(mission_key)
     # Or if a path is needed:
     config_path = MissionTemplateRepository.default()._mission_config_path(mission_key)
     ```
  4. **Determine what's needed**: If the code reads the file, use `get_mission_config()`. If it checks existence, use `_mission_config_path()` is not None. If it passes the path to another function, use `_mission_config_path()`.
  5. **After**: Run feature-related tests:
     ```bash
     pytest tests/ -v -k "feature" --co -q
     ```
- **Files**: `src/specify_cli/cli/commands/agent/feature.py`
- **Parallel?**: Yes, independent of T027-T028
- **Notes**: This is a pre-existing bug that's being fixed opportunistically. The stale path probably causes a silent failure today (returns `None` because the file doesn't exist at the old location).

### Subtask T030 – Full test suite + validation grep

- **Purpose**: Final validation. Confirm no regressions and no remaining direct mission path construction.
- **Steps**:
  1. **Run full test suite**:
     ```bash
     source .venv/bin/activate && .venv/bin/python -m pytest tests/ -v
     ```
  2. **Fix any failures**. Common causes:
     - Tests that mock `get_package_asset_root` may need to mock `MissionTemplateRepository.default()._missions_root` instead
     - Tests that import old method names (e.g., `get_command_template` expecting `Path`) need updating
     - Import path changes
  3. **Run validation grep** to confirm no direct mission path construction remains in production code:
     ```bash
     # Check for direct mission path construction patterns
     # Should only find: repository.py, kernel/paths.py, migrations, test_package_bundling.py, project-local code (manifest.py, mission.py)
     grep -rn 'missions_root.*"command-templates"' src/ --include="*.py" | grep -v repository.py | grep -v migrations | grep -v test_
     grep -rn 'missions_root.*"templates"' src/ --include="*.py" | grep -v repository.py | grep -v migrations | grep -v test_
     grep -rn 'missions_root.*"actions"' src/ --include="*.py" | grep -v repository.py | grep -v migrations | grep -v test_
     grep -rn '"missions".*"command-templates"' src/ --include="*.py" | grep -v repository.py | grep -v migrations
     grep -rn 'get_package_asset_root' src/ --include="*.py"
     ```
  4. **Evaluate remaining `get_package_asset_root` callers**: Some legitimate callers may remain (e.g., `kernel/paths.py` which IS the implementation). Document which callers are expected vs. which need further migration.
  5. **Run the comprehensive test module**:
     ```bash
     source .venv/bin/activate && .venv/bin/python -m pytest tests/doctrine/test_mission_template_repository.py -v
     ```
  6. **Report**: List any remaining direct path constructions with justification for each (project-local, migration file, foundational module, etc.).
- **Files**: Multiple (test fixes as needed)
- **Parallel?**: No, must run after T027-T029

## Test Strategy

This is the final validation WP. Run the full suite:

```bash
source .venv/bin/activate && .venv/bin/python -m pytest tests/ -v --tb=short
```

Expected outcome: All tests pass. Any failures are regressions from WP05-WP06 changes that need fixing here.

## Risks & Mitigations

1. **Hidden consumers surface**: The grep validation in T030 may find patterns missed in the research. Fix them in this WP if they're small, or document them for a follow-up if they're complex.
2. **Test mocks targeting old APIs**: Tests that mock `get_package_asset_root` or old method names may need updating. These are legitimate test changes.
3. **feature.py stale path may not have tests**: The buggy code path in `feature.py` may be untested. Fix it anyway -- it's a correctness issue.
4. **Merge conflicts if WP05 and WP06 ran in parallel**: The worktree model handles this, but review merge carefully.

## Review Guidance

- Verify grep validation is clean (only expected files have direct path construction)
- Verify full test suite passes
- Verify the `feature.py` bug fix is correct (test it manually if no automated tests exist)
- Verify all `get_package_asset_root` usages are either in legitimate places (kernel/paths.py) or have been rerouted
- Verify the "Explicitly excluded from rerouting" files in Context section are truly excluded and documented

## Activity Log

- 2026-03-27T04:37:32Z – system – lane=planned – Prompt created.
- 2026-03-28T12:51:26Z – unknown – shell_pid=98083 – lane=for_review – Ready for review: rerouted remaining direct mission paths to MissionTemplateRepository, fixed stale path, boyscout test fixes
- 2026-03-29T06:13:32Z – opencode – shell_pid=113162 – lane=in_review – Started review via workflow command
- 2026-03-29T06:14:11Z – opencode – shell_pid=113162 – lane=for_review – Returned to for_review - accidentally claimed during WP08 review
- 2026-03-29T06:16:40Z – opencode – shell_pid=113162 – lane=in_review – Started review via workflow command
- 2026-03-29T06:31:05Z – opencode – shell_pid=113162 – lane=planned – Moved to planned
- 2026-03-29T06:45:31Z – opencode – shell_pid=113162 – lane=planned – Review feedback revised: Issue 1 (out-of-scope doctrine pruning) withdrawn — those changes are on the parallel base-branch track, not WP07. Remaining issues: (1) rebase needed onto current feature/agent-profile-implementation, (2) TemplateResult vs Path bug in test_review_template_dependency_warnings. Updated feedback at /tmp/spec-kitty-review-feedback-WP07.md
- 2026-03-29T07:29:48Z – opencode – shell_pid=113162 – lane=approved – Review passed (2nd review): All 5 acceptance criteria verified. T027-T030 reroutes correctly use MissionTemplateRepository. TemplateResult bug fixed in commit 2ef55498. Test suite: 51 failed / 7295 passed — identical to baseline (zero regressions). Validation grep confirms no direct mission path construction in rerouted callers.
- 2026-03-29T08:11:08Z – opencode – shell_pid=113162 – lane=done – Reviewed and merged to feature/agent-profile-implementation. Reroutes T027/T028 verified, TemplateResult bug fixed, all acceptance criteria met. | Done override: Branch deleted after manual merge to feature/agent-profile-implementation; merge commit verified on target branch.
