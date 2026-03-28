---
work_package_id: WP05
title: HIGH Priority Consumer Reroutes
lane: planned
dependencies:
- WP01
requirement_refs:
- FR-017
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
phase: Phase 2 - Consumer Rerouting
assignee: ''
agent: ''
agent_profile: implementer
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

# Work Package Prompt: WP05 – HIGH Priority Consumer Reroutes

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

1. `src/constitution/context.py` uses `MissionTemplateRepository` for all mission asset access (no direct path construction)
2. `src/constitution/catalog.py` uses `MissionTemplateRepository` for mission listing and config reading
3. `src/specify_cli/constitution/catalog.py` uses `MissionTemplateRepository` (same pattern as above)
4. `src/specify_cli/runtime/show_origin.py` uses `MissionTemplateRepository` for all discovery functions
5. No regressions: all tests for these files pass before and after

**Success gate**: For each file, run its associated tests and verify they pass. No direct mission path construction remains in these 4 files.

## Context & Constraints

- **Research**: `kitty-specs/058-mission-template-repository-refactor/research/consumer-analysis.md` (exact line numbers and patterns for each file)
- **Prerequisite**: WP04 must pass (comprehensive tests provide confidence gate)
- **Strategy**: For each file, identify existing tests → run them → make changes → re-run tests
- **Important**: Do NOT change function signatures or return types. Only change the internal implementation from direct path construction to repository API calls.

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP05 --base WP04`

## Subtasks & Detailed Guidance

### Subtask T019 – Reroute constitution/context.py

- **Purpose**: Replace 3 direct path construction patterns in `_append_action_doctrine_lines()` with repository API calls.
- **Steps**:
  1. **Before**: Run tests that exercise this file:
     ```bash
     pytest tests/constitution/ -v -k "context" 2>/dev/null || pytest tests/ -v -k "context or constitution" --co -q
     ```
  2. **Read** `src/constitution/context.py`, focusing on `_append_action_doctrine_lines()` (lines ~220-262)
  3. **Change 1** (line ~225): Replace `missions_root = resolve_doctrine_root() / "missions"` with:
     ```python
     from doctrine.missions import MissionTemplateRepository
     repo = MissionTemplateRepository.default()
     ```
  4. **Change 2** (line ~229): Replace `action_index = load_action_index(missions_root, mission, action)` with:
     ```python
     config_result = repo.get_action_index(mission, action)
     ```
     **Important**: The function currently uses `action_index` as an `ActionIndex` dataclass (with `.directives`, `.tactics`, etc. attributes). The new `config_result.parsed` returns a raw dict. You have two options:
     - **Option A**: Keep `load_action_index()` but get the path from repository:
       ```python
       idx_path = repo._action_index_path(mission, action)
       action_index = load_action_index(repo._missions_root, mission, action) if idx_path else ActionIndex(action=action)
       ```
     - **Option B**: Convert the code that reads `action_index.directives` etc. to read from `config_result.parsed.get("directives", [])` etc.
     - **Recommended**: Option A (less invasive, keeps `ActionIndex` type contract intact)
  5. **Change 3** (line ~249): Replace `guidelines_path = missions_root / mission / "actions" / action / "guidelines.md"` with:
     ```python
     guidelines_result = repo.get_action_guidelines(mission, action)
     ```
     Then replace `guidelines_path.read_text(encoding="utf-8")` with `guidelines_result.content` (check for `None` first).
  6. **After**: Re-run the same tests
- **Files**: `src/constitution/context.py`
- **Parallel?**: Yes, independent of T020-T022
- **Edge cases**: If no action index exists, `get_action_index()` returns `None`. The existing code uses `load_action_index()` which returns a fallback `ActionIndex(action=action)`. Preserve this fallback behavior.

### Subtask T020 – Reroute constitution/catalog.py

- **Purpose**: Replace `_load_template_sets_with_presence()` manual missions_root construction and directory iteration with repository API.
- **Steps**:
  1. **Before**: Run tests:
     ```bash
     pytest tests/constitution/ -v -k "catalog" 2>/dev/null || pytest tests/ -v -k "catalog" --co -q
     ```
  2. **Read** `src/constitution/catalog.py`, focusing on `_load_template_sets_with_presence()` (lines ~245-270)
  3. **Current code** constructs `missions_root` with 3 fallback strategies (lines 256, 259, 261), then iterates directories checking for `mission.yaml` (line 267). Replace the entire missions-root resolution and iteration with:
     ```python
     from doctrine.missions import MissionTemplateRepository
     repo = MissionTemplateRepository.default()
     mission_names = repo.list_missions()
     ```
  4. For each mission, where the code reads `mission.yaml` (line 267), replace with:
     ```python
     config = repo.get_mission_config(mission_name)
     if config is not None:
         # Use config.parsed instead of loading YAML manually
     ```
  5. **Keep the function return type and behavior identical**. Only the internal implementation changes.
  6. **Note**: The `resolve_doctrine_root()` function (lines 115-145) should remain -- it serves other purposes (paradigms, directives, etc. which are NOT mission-scoped). Only the mission-specific code changes.
  7. **After**: Re-run the same tests
- **Files**: `src/constitution/catalog.py`
- **Parallel?**: Yes, independent of T019, T021, T022
- **Notes**: This file also has `_get_package_asset_root` import (line 13). After this change, that import may become unused for mission purposes but may still be needed for other asset types. Check before removing.

### Subtask T021 – Reroute specify_cli/constitution/catalog.py

- **Purpose**: Same pattern as T020 but for the legacy copy in `specify_cli/constitution/`.
- **Steps**:
  1. **Before**: Run tests:
     ```bash
     pytest tests/ -v -k "catalog" --co -q
     ```
  2. **Read** `src/specify_cli/constitution/catalog.py`, focusing on `_load_template_sets()` (lines ~100-119)
  3. **Apply the same pattern as T020**: Replace missions_root construction (lines 107, 110, 112) and directory iteration (line 116) with:
     ```python
     from doctrine.missions import MissionTemplateRepository
     repo = MissionTemplateRepository.default()
     mission_names = repo.list_missions()
     ```
  4. Replace manual `mission.yaml` loading with `repo.get_mission_config(name)`.
  5. Keep function return type identical.
  6. **After**: Re-run tests
- **Files**: `src/specify_cli/constitution/catalog.py`
- **Parallel?**: Yes
- **Notes**: This is a legacy copy that duplicates `constitution/catalog.py`. After rerouting both, consider whether the duplication can be reduced (out of scope for this feature, but note it).

### Subtask T022 – Reroute specify_cli/runtime/show_origin.py

- **Purpose**: Replace 3 discovery functions that manually construct mission paths with repository API calls.
- **Steps**:
  1. **Before**: Run tests:
     ```bash
     pytest tests/ -v -k "show_origin or origin" --co -q
     ```
  2. **Read** `src/specify_cli/runtime/show_origin.py`
  3. **Change 1** (`_discover_mission_names()`, lines ~66-72):
     Current: `pkg_root = get_package_asset_root()` then iterates dirs checking `mission.yaml`.
     Replace body with:
     ```python
     from doctrine.missions import MissionTemplateRepository
     return MissionTemplateRepository.default().list_missions()
     ```
  4. **Change 2** (`_discover_command_names()`, lines ~75-95):
     Current: `pkg_root = get_package_asset_root()` then `pkg_cmd_dir = pkg_root / mission / "command-templates"` then lists `.md` files.
     Replace body with:
     ```python
     from doctrine.missions import MissionTemplateRepository
     return MissionTemplateRepository.default().list_command_templates(mission)
     ```
     **Note**: The function may also check for project-level override templates. Read the full function to understand if it merges package + override lists. If so, only replace the package-level part.
  5. **Change 3** (`_discover_template_names()`, lines ~98-114):
     Same pattern. Replace with `MissionTemplateRepository.default().list_content_templates(mission)`.
     Same caveat about override merging.
  6. **After**: Re-run tests
  7. **Cleanup**: If `get_package_asset_root` is no longer used in this file, remove the import.
- **Files**: `src/specify_cli/runtime/show_origin.py`
- **Parallel?**: Yes
- **Notes**: These functions may return combined results from package + project. Read carefully before replacing -- only the package-asset portion should use the repository.

## Test Strategy

For each subtask, identify and run the relevant tests BEFORE making changes. After changes, run the same tests again. At the end, run:

```bash
source .venv/bin/activate && .venv/bin/python -m pytest tests/constitution/ tests/specify_cli/ -v
```

If test discovery is unclear, find tests by grepping:
```bash
grep -rl "context\|catalog\|show_origin" tests/ --include="*.py"
```

## Risks & Mitigations

1. **ActionIndex dataclass vs. raw dict**: `context.py` uses `ActionIndex` attributes. Option A (keep `load_action_index()` with repository path) is safest. Option B (raw dict) changes the interface contract within the function.
2. **Override merging in show_origin.py**: The discovery functions may merge package + project assets. Only replace the package portion. Read the full function bodies carefully.
3. **Unused imports**: After rerouting, imports like `get_package_asset_root`, `resolve_doctrine_root`, `load_action_index` may become unused. Clean them up to avoid lint warnings.
4. **catalog.py duplication**: Both `constitution/catalog.py` and `specify_cli/constitution/catalog.py` have the same pattern. Apply the same fix to both.

## Review Guidance

- Verify each file no longer constructs mission paths directly (search for `/ "missions"`, `/ "command-templates"`, `/ "actions"`, `/ "templates"`)
- Verify function signatures and return types are unchanged
- Verify tests pass before and after
- Verify unused imports are cleaned up
- Verify the `ActionIndex` contract is preserved in `context.py` (either via Option A or equivalent)

## Activity Log

- 2026-03-27T04:37:32Z – system – lane=planned – Prompt created.
