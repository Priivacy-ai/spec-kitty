---
work_package_id: WP02
title: AGENT_SKILL_CONFIG Capability Matrix
lane: planned
dependencies: []
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 0 - Foundation
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
- FR-003
- C-001
---

# Work Package Prompt: WP02 – AGENT_SKILL_CONFIG Capability Matrix

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Add the framework capability matrix from PRD section 6 as `AGENT_SKILL_CONFIG` in config.py
- Add installation class constants
- Export new symbols from the core package
- Unit tests verify all agents have correct entries

**Success**: `AGENT_SKILL_CONFIG` is importable, has entries for every agent in `AI_CHOICES`, and each entry has correct installation class and skill roots per the PRD.

## Context & Constraints

- **PRD reference**: Section 6 (Framework Capability Matrix)
- **Existing config**: `src/specify_cli/core/config.py` contains `AI_CHOICES` (13 agents) and `AGENT_COMMAND_CONFIG`
- **Constraint C-001**: 2.0.11+ only, no legacy compat

**Implementation command**: `spec-kitty implement WP02`

## Subtasks & Detailed Guidance

### Subtask T005 – Add installation class constants

- **Purpose**: Define the three installation classes as string constants for type safety and consistency.
- **Steps**:
  1. Add to `src/specify_cli/core/config.py` after `AGENT_COMMAND_CONFIG`:
     ```python
     # Skill installation classes (PRD section 6)
     SKILL_CLASS_SHARED: str = "shared-root-capable"
     SKILL_CLASS_NATIVE: str = "native-root-required"
     SKILL_CLASS_WRAPPER: str = "wrapper-only"
     ```
- **Files**: `src/specify_cli/core/config.py` (modify)

### Subtask T006 – Add `AGENT_SKILL_CONFIG` dict

- **Purpose**: Encode the PRD's capability matrix as a config constant for use by the installer.
- **Steps**:
  1. Add to `src/specify_cli/core/config.py` after the class constants:
     ```python
     AGENT_SKILL_CONFIG: dict[str, dict[str, str | list[str] | None]] = {
         "claude":       {"class": SKILL_CLASS_NATIVE,  "skill_roots": [".claude/skills/"]},
         "copilot":      {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".github/skills/"]},
         "gemini":       {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".gemini/skills/"]},
         "cursor":       {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".cursor/skills/"]},
         "qwen":         {"class": SKILL_CLASS_NATIVE,  "skill_roots": [".qwen/skills/"]},
         "opencode":     {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".opencode/skills/"]},
         "windsurf":     {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".windsurf/skills/"]},
         "codex":        {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/"]},
         "kilocode":     {"class": SKILL_CLASS_NATIVE,  "skill_roots": [".kilocode/skills/"]},
         "auggie":       {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".augment/skills/"]},
         "roo":          {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".roo/skills/"]},
         "q":            {"class": SKILL_CLASS_WRAPPER, "skill_roots": None},
         "antigravity":  {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".agent/skills/"]},
     }
     ```
  2. The matrix must exactly match PRD section 6, with `antigravity` added as shared-root-capable (not in PRD, present in 2.x `AI_CHOICES`)
- **Files**: `src/specify_cli/core/config.py` (modify)
- **Notes**: `skill_roots` is `None` for wrapper-only agents, a list of root paths for others. First root in list is the primary installation target.

### Subtask T007 – Export new symbols from `src/specify_cli/core/__init__.py`

- **Purpose**: Make the new constants importable from the core package.
- **Steps**:
  1. Add imports to `src/specify_cli/core/__init__.py`:
     ```python
     from .config import (
         AGENT_SKILL_CONFIG,
         SKILL_CLASS_SHARED,
         SKILL_CLASS_NATIVE,
         SKILL_CLASS_WRAPPER,
     )
     ```
  2. Add to `__all__` list
  3. Also add to `__all__` in `src/specify_cli/core/config.py`
- **Files**: `src/specify_cli/core/__init__.py` (modify), `src/specify_cli/core/config.py` (modify `__all__`)

### Subtask T008 – Unit tests for config entries

- **Purpose**: Verify the capability matrix is complete and correct.
- **Steps**:
  1. Create `tests/specify_cli/core/test_skill_config.py`
  2. Test cases:
     - `test_all_agents_have_skill_config` — every key in `AI_CHOICES` exists in `AGENT_SKILL_CONFIG`
     - `test_no_extra_agents_in_skill_config` — no keys in `AGENT_SKILL_CONFIG` that aren't in `AI_CHOICES`
     - `test_installation_classes_are_valid` — every `class` value is one of the three constants
     - `test_wrapper_only_has_no_roots` — agents with `wrapper-only` class have `skill_roots: None`
     - `test_non_wrapper_has_roots` — agents with non-wrapper class have `skill_roots` as non-empty list
     - `test_shared_root_includes_agents_skills` — shared-root agents have `.agents/skills/` as first root
     - `test_native_root_is_vendor_specific` — native-root agents don't start with `.agents/`
- **Files**: `tests/specify_cli/core/test_skill_config.py` (new, ~80 lines)
- **Parallel?**: Yes — can be written alongside T005-T007

## Risks & Mitigations

- **Agent list divergence**: `AI_CHOICES` may gain new agents in future → test enforces 1:1 correspondence
- **PRD matrix updates**: If PRD changes, config must be updated → test documents the contract

## Review Guidance

- Verify every agent in `AI_CHOICES` has a corresponding `AGENT_SKILL_CONFIG` entry
- Verify PRD section 6 matrix is faithfully represented
- Verify `antigravity` agent is included (present in 2.x but not in original PRD matrix)

## Activity Log

- 2026-03-21T07:39:56Z – system – lane=planned – Prompt created.
