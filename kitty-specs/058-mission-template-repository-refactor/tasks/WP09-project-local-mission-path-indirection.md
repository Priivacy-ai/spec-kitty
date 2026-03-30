---
work_package_id: WP09
title: Project-Local Mission Path Indirection (constitution module)
lane: done
dependencies: [WP07]
requirement_refs:
- FR-019
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
base_branch: feature/agent-profile-implementation
base_commit: 789871e497d60eeee7cadd251a8d0623a2ba4781
created_at: '2026-03-30T04:02:22.528928+00:00'
subtasks:
- T039
- T040
- T041
- T042
phase: Phase 2 - Consumer Rerouting
assignee: ''
agent: claude
shell_pid: '21595'
review_status: approved
reviewed_by: Stijn Dejongh
history:
- timestamp: '2026-03-27T05:15:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt added during /spec-kitty.analyze HiC review (F5 decision)
agent_profile: implementer
approved_by: Stijn Dejongh
role: reviewer
---

# Work Package Prompt: WP09 -- Project-Local Mission Path Indirection

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

**Verdict**: approved | **Reviewer**: Stijn Dejongh | **Date**: 2026-03-30T04:44:13Z

Review passed: MissionType + ProjectMissionPaths singleton correctly centralizes .kittify/missions/ path construction. 1508 tests pass, zero regressions. Design exceeds WP spec per HiC direction.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

1. A `ProjectMissionPaths` class exists in `src/specify_cli/constitution/mission_paths.py`
2. All `.kittify/missions/` path construction in `manifest.py`, `mission.py`, and `config.py` flows through `ProjectMissionPaths`
3. All existing tests pass unchanged (pure indirection, no behavior change)
4. Zero new imports from `specify_cli` in the new module (only `pathlib`)

**Success gate**: `pytest tests/ -k "manifest or mission or config"` passes. Grep confirms no remaining `.kittify/missions/` path construction in the three rerouted files.

## Context & Constraints

- **HiC Decision (F5)**: The human-in-charge decided these project-local files should route through the constitution module to prepare for future constitution-aware resolution, rather than being excluded from the refactor.
- **Pure indirection**: This is an "add indirection" refactor. Behavior is identical before and after. The value is that future work targeting the constitution module has a single place to hook into.
- **No behavior change in rerouted files**: Same paths, same existence checks, same directory listings. Just sourced from `ProjectMissionPaths` instead of inline construction.

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP09 --base WP07`

(Can run in parallel with WP08.)

## Subtasks & Detailed Guidance

### Subtask T039 -- Create `ProjectMissionPaths` class

- **Purpose**: Single indirection point for all project-local mission path construction.
- **Steps**:
  1. **Create** `src/specify_cli/constitution/mission_paths.py`
  2. **Implement** `ProjectMissionPaths` with static methods:
     ```python
     from __future__ import annotations
     from pathlib import Path


     class ProjectMissionPaths:
         """Centralized project-local mission path resolution.

         All `.kittify/missions/` path construction should flow through
         this class. Future work will make resolution constitution-aware.
         """

         @staticmethod
         def missions_root(project_dir: Path) -> Path:
             """Root directory for all project-local missions."""
             return project_dir / ".kittify" / "missions"

         @staticmethod
         def mission_dir(project_dir: Path, mission: str) -> Path:
             """Directory for a specific mission."""
             return ProjectMissionPaths.missions_root(project_dir) / mission

         @staticmethod
         def mission_config(project_dir: Path, mission: str) -> Path:
             """Path to a mission's mission.yaml."""
             return ProjectMissionPaths.mission_dir(project_dir, mission) / "mission.yaml"

         @staticmethod
         def command_templates_dir(project_dir: Path, mission: str) -> Path:
             """Directory containing command templates for a mission."""
             return ProjectMissionPaths.mission_dir(project_dir, mission) / "command-templates"

         @staticmethod
         def templates_dir(project_dir: Path, mission: str) -> Path:
             """Directory containing content templates for a mission."""
             return ProjectMissionPaths.mission_dir(project_dir, mission) / "templates"
     ```
  3. **Update** `src/specify_cli/constitution/__init__.py` if needed (add export)
  4. **Verify**: `python -c "from specify_cli.constitution.mission_paths import ProjectMissionPaths; print('OK')"`
- **Files**: `src/specify_cli/constitution/mission_paths.py` (new)
- **Critical**: Zero imports from `specify_cli` — only `pathlib.Path`. This prevents import cycles.

### Subtask T040 -- Reroute `src/specify_cli/manifest.py`

- **Purpose**: Replace 4 inline `.kittify/missions/` path constructions.
- **Steps**:
  1. **Before**: Run tests:
     ```bash
     pytest tests/ -v -k "manifest" --co -q
     pytest tests/ -v -k "manifest"
     ```
  2. **Read** `src/specify_cli/manifest.py`
  3. **Replace patterns**:
     - Line ~22: `kittify_dir / "missions" / mission_key` -> `ProjectMissionPaths.mission_dir(kittify_dir, mission_key)`
     - Line ~43: `self.mission_dir / "mission.yaml"` -> `ProjectMissionPaths.mission_config(self._project_dir, self._mission_key)` (or keep as property if `mission_dir` is already stored)
     - Line ~48: `self.mission_dir / "command-templates"` -> `ProjectMissionPaths.command_templates_dir(self._project_dir, self._mission_key)`
     - Line ~72: `self.mission_dir / "command-templates"` -> same as line 48
  4. **Note**: If `self.mission_dir` is stored during `__init__`, the simplest approach is to set `self.mission_dir = ProjectMissionPaths.mission_dir(kittify_dir, mission_key)` at line 22 and leave lines 43/48/72 as `self.mission_dir / "..."`. The sub-paths are relative to mission_dir, not to kittify root.
  5. **After**: Re-run tests
- **Files**: `src/specify_cli/manifest.py`
- **Parallel?**: Yes (after T039)

### Subtask T041 -- Reroute `src/specify_cli/mission.py`

- **Purpose**: Replace 9 inline `.kittify/missions/` path constructions.
- **Steps**:
  1. **Before**: Run tests:
     ```bash
     pytest tests/ -v -k "mission" --co -q
     pytest tests/ -v -k "mission"
     ```
  2. **Read** `src/specify_cli/mission.py`
  3. **Replace patterns by group**:

     **Mission dir construction** (4 sites):
     - Line ~457: `kittify_dir / "missions" / mission_name` -> `ProjectMissionPaths.mission_dir(kittify_dir, mission_name)`
     - Line ~467: `kittify_dir / "missions" / "software-dev"` -> `ProjectMissionPaths.mission_dir(kittify_dir, "software-dev")`
     - Line ~470: same as 467
     - Line ~522: `kittify_dir / "missions" / mission_name` -> `ProjectMissionPaths.mission_dir(kittify_dir, mission_name)`

     **Missions root listing** (2 sites):
     - Line ~493: `kittify_dir / "missions"` -> `ProjectMissionPaths.missions_root(kittify_dir)`
     - Line ~714: `kittify_dir / "missions"` -> `ProjectMissionPaths.missions_root(kittify_dir)`

     **Mission config check** (2 sites):
     - Line ~500: `mission_dir / "mission.yaml"` -> `ProjectMissionPaths.mission_config(kittify_dir, mission_name)` (or keep relative if mission_dir already resolved)
     - Line ~722: same pattern

     **Command templates property** (1 site):
     - Line ~276: `self.path / "command-templates"` -> depends on how `self.path` is set. If `self.path` is already a mission_dir, this may be fine as-is or use `ProjectMissionPaths.command_templates_dir(project_dir, mission)`.

  4. **After**: Re-run tests
- **Files**: `src/specify_cli/mission.py`
- **Parallel?**: Yes (after T039)

### Subtask T042 -- Reroute `src/specify_cli/cli/commands/agent/config.py`

- **Purpose**: Replace 2 hardcoded path constructions.
- **Steps**:
  1. **Before**: Run tests:
     ```bash
     pytest tests/ -v -k "agent_config or config" --co -q
     pytest tests/specify_cli/cli/commands/test_agent_config.py -v
     ```
  2. **Read** `src/specify_cli/cli/commands/agent/config.py`
  3. **Replace patterns**:
     - Line ~145: `repo_root / ".kittify" / "missions" / "software-dev" / "command-templates"` -> `ProjectMissionPaths.command_templates_dir(repo_root, "software-dev")`
     - Line ~365: same pattern -> same replacement
  4. **Note**: The hardcoded `"software-dev"` stays. Fixing that is a separate concern.
  5. **After**: Re-run tests
- **Files**: `src/specify_cli/cli/commands/agent/config.py`
- **Parallel?**: Yes (after T039)

## Test Strategy

```bash
# Run targeted tests for rerouted files
pytest tests/ -v -k "manifest or mission or config"

# Run full suite to check for regressions
pytest tests/ -v --tb=short

# Verify no remaining inline .kittify/missions/ construction in rerouted files
rg 'kittify.*missions' src/specify_cli/manifest.py src/specify_cli/mission.py src/specify_cli/cli/commands/agent/config.py
# Expected: only imports of ProjectMissionPaths, no inline path construction
```

## Risks & Mitigations

1. **Import cycle**: `mission_paths.py` must not import from `specify_cli` beyond `pathlib`. Verified by T039 implementation constraint.
2. **`self.path` / `self.mission_dir` indirection**: Some files store the constructed path in `__init__`. The reroute may only need to change the initial construction, not every downstream usage. Read carefully before replacing.
3. **Test expectations on path construction**: Tests that mock or assert on specific path patterns may need minor updates. This is acceptable since the paths produced are identical.

## Review Guidance

- Verify `ProjectMissionPaths` has zero non-stdlib imports
- Verify all three rerouted files import from `specify_cli.constitution.mission_paths`
- Verify no remaining inline `.kittify/missions/` construction in rerouted files (grep check)
- Verify all tests pass unchanged

## Activity Log

- 2026-03-27T05:15:00Z -- system -- lane=planned -- Prompt added during /spec-kitty.analyze HiC review (F5 decision).
- 2026-03-30T04:40:47Z – unknown – shell_pid=6662 – lane=for_review – Ready for review: MissionType + ProjectMissionPaths singleton, 3 files rerouted, gap note added
- 2026-03-30T04:41:56Z – claude – shell_pid=21595 – lane=in_review – Started review via workflow command
- 2026-03-30T04:44:13Z – claude – shell_pid=21595 – lane=approved – Review passed: MissionType + ProjectMissionPaths singleton correctly centralizes .kittify/missions/ path construction. 1508 tests pass, zero regressions. Design exceeds WP spec per HiC direction.
