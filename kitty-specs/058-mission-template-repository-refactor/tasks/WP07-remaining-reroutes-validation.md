---
work_package_id: WP07
title: Remaining Reroutes + Bug Fix + Validation
lane: planned
dependencies: [WP05, WP06]
requirement_refs:
- FR-017
- NFR-002
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
phase: Phase 2 - Consumer Rerouting
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-27T04:37:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
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

*[This section is empty initially.]*

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
