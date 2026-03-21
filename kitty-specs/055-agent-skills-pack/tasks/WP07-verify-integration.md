---
work_package_id: WP07
title: Verify Integration
lane: planned
dependencies: [WP06]
subtasks:
- T028
- T029
- T030
- T031
phase: Phase 2 - Integration
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-21T07:39:56Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-006
- FR-012
---

# Work Package Prompt: WP07 – Verify Integration

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Wire skill verification into the existing `spec-kitty verify` command
- Display skill verification results with Rich formatting
- Detect duplicate skill names across installed roots
- Integration test

**Success**: `spec-kitty verify` shows a "Managed Skills" section with installed/missing/drifted counts.

## Context & Constraints

- **Dependencies**: WP06 (verifier module)
- **Critical file**: `src/specify_cli/verify_enhanced.py`
- **Existing output**: Read verify_enhanced.py to understand its output patterns and match formatting

**Implementation command**: `spec-kitty implement WP07 --base WP06`

## Subtasks & Detailed Guidance

### Subtask T028 – Add managed skill checks to verify_enhanced.py

- **Purpose**: Call skill verifier and include results in the verify output.
- **Steps**:
  1. Read `src/specify_cli/verify_enhanced.py` to understand the existing structure
  2. Add import: `from specify_cli.skills.verifier import verify_installed_skills`
  3. Add a new check section that:
     - Calls `verify_installed_skills(project_path)`
     - Adds results to the overall verify output
     - Marks verify as failed if `result.ok` is False
  4. Place the skill check after existing file manifest checks
- **Files**: `src/specify_cli/verify_enhanced.py` (modify)
- **Notes**: Follow existing code patterns for adding check sections. Don't restructure existing code.

### Subtask T029 – Display skill verification results with Rich formatting

- **Purpose**: Show clear, actionable output for skill verification status.
- **Steps**:
  1. Match the existing Rich formatting patterns in verify_enhanced.py
  2. Display:
     - Header: "Managed Skills" or "Skill Pack"
     - Summary: "X installed, Y missing, Z drifted"
     - If all ok: green checkmark line
     - If issues: list each missing/drifted file with skill name and path
     - If no manifest: "No skill manifest found (run spec-kitty init to install skills)"
  3. Use Rich `Panel`, `Table`, or inline formatting consistent with existing output
- **Files**: `src/specify_cli/verify_enhanced.py` (modify, part of T028)

### Subtask T030 – Detect duplicate skill names across roots

- **Purpose**: Warn if the same skill name appears in multiple roots (FR-012).
- **Steps**:
  1. After verification, scan all skill roots for `SKILL.md` files
  2. Parse `name:` from frontmatter of each SKILL.md
  3. If any name appears in multiple roots, add warning to verify output
  4. This is a warning, not a failure — duplicates don't break functionality
- **Files**: `src/specify_cli/verify_enhanced.py` (modify)
- **Notes**: Use `ruamel.yaml` for frontmatter parsing (already a dependency). Only check configured agents' roots.

### Subtask T031 – Integration test for verify with skills

- **Purpose**: Verify the full `spec-kitty verify` output includes skill status.
- **Steps**:
  1. Create `tests/specify_cli/skills/test_verify_integration.py`
  2. Test cases:
     - `test_verify_shows_skills_section` — verify output contains skill check section
     - `test_verify_reports_missing_skill` — deleted skill file shows in output
     - `test_verify_reports_drifted_skill` — modified skill file shows in output
     - `test_verify_no_manifest_shows_info` — no manifest → informational message
  3. Use test fixtures with installed skills and manifest
- **Files**: `tests/specify_cli/skills/test_verify_integration.py` (new, ~100 lines)
- **Parallel?**: Yes (after T028-T030)

## Risks & Mitigations

- **verify_enhanced.py output contract**: Existing tools may parse verify output → add new section, don't modify existing sections
- **Performance**: Scanning all skill roots for duplicates → only scan configured agents, skip if no manifest

## Review Guidance

- Verify new section matches existing Rich formatting style
- Verify no existing verify output is modified
- Verify duplicate detection only warns, doesn't fail

## Activity Log

- 2026-03-21T07:39:56Z – system – lane=planned – Prompt created.
