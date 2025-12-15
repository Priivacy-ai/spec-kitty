---
work_package_id: "WP04"
subtasks:
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Downstream Command Updates"
phase: "Phase 3 - Integration"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-15T11:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Downstream Command Updates

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Update all downstream commands to read mission from feature's meta.json
- Replace calls to `get_active_mission()` with `get_mission_for_feature()` where appropriate
- Maintain backward compatibility: features without mission field use software-dev

**Success Metrics** (from spec FR-011):
- `/spec-kitty.plan` on feature with `"mission": "research"` uses research templates
- `/spec-kitty.tasks` uses mission from feature context
- All slash commands work correctly with per-feature missions
- Legacy features (no mission field) continue to work with software-dev default

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/006-per-feature-mission/spec.md` (FR-011, User Story 4)
- Plan: `kitty-specs/006-per-feature-mission/plan.md` (Phase 3)

**Files to Audit**:
- All bash scripts in `.kittify/scripts/bash/`
- All prompt templates in `.kittify/missions/*/command-templates/`
- Python code in `src/specify_cli/` that references missions

**Constraints**:
- Some commands run from worktrees, some from main repo
- Feature directory path varies based on context
- Must handle missing mission field gracefully

## Subtasks & Detailed Guidance

### Subtask T017 – Identify all files calling `get_active_mission()`

- **Purpose**: Create complete audit of files needing updates
- **Files**: Repository-wide search
- **Steps**:
  1. Search for `get_active_mission` references:
     ```bash
     grep -r "get_active_mission" --include="*.py" --include="*.sh" .
     ```
  2. Search for `active-mission` references:
     ```bash
     grep -r "active-mission" --include="*.py" --include="*.sh" --include="*.md" .
     ```
  3. Create list of files to update with line numbers
  4. Categorize by type:
     - Python files → update to use `get_mission_for_feature()`
     - Bash scripts → update to read from feature's meta.json
     - Prompt templates → may need context about which mission is active
  5. Document findings for subsequent subtasks
- **Parallel?**: No (foundational for T018-T024)

### Subtask T018 – Update `setup-plan.sh` to read mission from feature

- **Purpose**: Plan command should use feature's mission, not project mission
- **Files**: `.kittify/scripts/bash/setup-plan.sh`
- **Steps**:
  1. Find where script determines feature directory (likely uses check-prerequisites.sh)
  2. Add mission reading from meta.json:
     ```bash
     # Read mission from feature's meta.json
     META_FILE="$FEATURE_DIR/meta.json"
     if [ -f "$META_FILE" ]; then
         MISSION=$(python3 -c "import json; print(json.load(open('$META_FILE')).get('mission', 'software-dev'))" 2>/dev/null || echo "software-dev")
     else
         MISSION="software-dev"
     fi
     ```
  3. Use MISSION variable to find correct template paths:
     ```bash
     MISSION_DIR=".kittify/missions/$MISSION"
     PLAN_TEMPLATE="$MISSION_DIR/templates/plan-template.md"
     ```
  4. Update template copying logic to use mission-specific templates
- **Parallel?**: No (establishes pattern for T019)

### Subtask T019 – Update `check-prerequisites.sh` to support per-feature mission

- **Purpose**: Prerequisites check should understand feature's mission context
- **Files**: `.kittify/scripts/bash/check-prerequisites.sh`
- **Steps**:
  1. Add mission field to JSON output if requested
  2. If script validates mission-specific requirements, update logic
  3. Ensure script works whether called from worktree or main repo
- **Parallel?**: Yes (once T018 pattern established)

### Subtask T020 – Update `plan.md` prompt template

- **Purpose**: Plan command should reference feature's mission
- **Files**: `.kittify/missions/software-dev/command-templates/plan.md` (and research variant)
- **Steps**:
  1. Check if template hardcodes mission assumptions
  2. If template loads other templates, ensure it uses feature's mission:
     ```markdown
     Load templates from the feature's mission directory, determined by reading
     `mission` field from the feature's `meta.json` (default: software-dev).
     ```
  3. Update any paths that reference `.kittify/missions/software-dev/` to be dynamic
- **Parallel?**: Yes (once T018 pattern established)

### Subtask T021 – Update `tasks.md` prompt template

- **Purpose**: Tasks command should use feature's mission context
- **Files**: `.kittify/missions/software-dev/command-templates/tasks.md` (and research variant)
- **Steps**:
  1. Similar to T020 - check for hardcoded mission references
  2. Update to read mission from feature's meta.json
  3. Ensure task-prompt-template.md lookup uses correct mission
- **Parallel?**: Yes (once T018 pattern established)

### Subtask T022 – Update `implement.md` prompt template

- **Purpose**: Implement command should use feature's mission context
- **Files**: `.kittify/missions/software-dev/command-templates/implement.md`
- **Steps**:
  1. Check for mission-specific logic or template references
  2. Update to read mission from feature context
  3. Ensure implementation guidance matches feature's mission workflow
- **Parallel?**: Yes (once T018 pattern established)

### Subtask T023 – Update `review.md` prompt template

- **Purpose**: Review command should use feature's mission context
- **Files**: `.kittify/missions/software-dev/command-templates/review.md`
- **Steps**:
  1. Check for mission-specific review criteria
  2. Update to use feature's mission for validation checks
  3. Research mission may have different review focus (sources, citations)
- **Parallel?**: Yes (once T018 pattern established)

### Subtask T024 – Update Python code that reads active mission

- **Purpose**: Python modules should use per-feature mission resolution
- **Files**: `src/specify_cli/` - various modules
- **Steps**:
  1. From T017 audit, identify Python files calling `get_active_mission()`
  2. For each file, determine if it should:
     - Use `get_mission_for_feature()` (when feature context available)
     - Keep `get_active_mission()` (when no feature context, e.g., init)
  3. Update imports:
     ```python
     from specify_cli.mission import get_mission_for_feature, MissionNotFoundError
     ```
  4. Update function calls, passing feature directory:
     ```python
     # Before
     mission = get_active_mission()

     # After
     mission = get_mission_for_feature(feature_dir)
     ```
  5. Handle cases where feature_dir is not available (fall back to get_active_mission or default)
- **Parallel?**: No (needs careful coordination)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing some files in audit | Use multiple search patterns; test all commands |
| Breaking existing workflows | Keep `get_active_mission()` available for cases without feature context |
| Worktree path confusion | Test from both main repo and worktree contexts |
| Research mission templates differ | Audit both mission directories for consistency |

## Definition of Done Checklist

- [ ] Complete audit of files referencing active mission (T017)
- [ ] All bash scripts updated to read from feature's meta.json
- [ ] All prompt templates updated to use feature's mission
- [ ] Python code updated where appropriate
- [ ] Backward compatibility verified (missing mission field → software-dev)
- [ ] Commands work correctly from both main repo and worktree

## Review Guidance

- Test `/spec-kitty.plan` on feature with research mission → should use research templates
- Test commands on legacy feature without mission field → should use software-dev
- Verify no hardcoded "software-dev" references remain in dynamic paths
- Check both software-dev and research mission command-templates are consistent

## Activity Log

- 2025-12-15T11:55:00Z – system – lane=planned – Prompt created.
