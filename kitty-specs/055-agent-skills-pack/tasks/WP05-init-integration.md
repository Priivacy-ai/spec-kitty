---
work_package_id: WP05
title: Init Integration
dependencies: [WP04]
requirement_refs:
- FR-002
- FR-008
- FR-011
- NFR-001
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 1 - Core Implementation
history:
- timestamp: '2026-03-21T07:39:56Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: ''
execution_mode: code_change
mission_id: 01KN2371WVZGV7TH7WMR2CN9Q1
owned_files:
- src/doctrine/skills/**
- src/specify_cli/cli/commands/init.py
- tests/specify_cli/skills/test_init_integration.py
wp_code: WP05
---

# Work Package Prompt: WP05 – Init Integration

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Add skill installation step to `spec-kitty init` after wrapper generation
- Add progress tracking via StepTracker
- Write the managed manifest at end of init
- Handle both local dev and package template modes
- Integration test verifying skills appear after init

**Success**: Running init creates skills in correct roots alongside existing wrappers, and `.kittify/skills-manifest.json` is populated.

## Context & Constraints

- **PRD reference**: Section 9 (Installer and Distribution Plan) — `spec-kitty init` should distribute the modern skill pack
- **Constraint FR-008 / C-003**: Existing wrapper generation must continue unchanged
- **NFR-001**: Skill installation adds < 2s to init
- **Critical file**: `src/specify_cli/cli/commands/init.py` (1140 lines)
- **Integration point**: After `generate_agent_assets()` call at ~line 775, before git step at ~line 826

**Implementation command**: `spec-kitty implement WP05 --base WP04`

## Subtasks & Detailed Guidance

### Subtask T019 – Add skill installation step to init.py

- **Purpose**: Wire the installer into the init flow.
- **Steps**:
  1. Add imports to top of `src/specify_cli/cli/commands/init.py`:
     ```python
     from specify_cli.skills.registry import SkillRegistry
     from specify_cli.skills.installer import install_skills_for_agent
     from specify_cli.skills.manifest import (
         ManagedSkillManifest,
         save_manifest,
         compute_content_hash,
     )
     ```
  2. Before the per-agent loop (~line 693), initialize:
     ```python
     # Skill pack installation state
     skill_manifest = ManagedSkillManifest(
         created_at=datetime.now(timezone.utc).isoformat(),
         updated_at=datetime.now(timezone.utc).isoformat(),
         spec_kitty_version="2.0.11",
     )
     skill_registry: SkillRegistry | None = None
     shared_root_installed: set[str] = set()
     ```
  3. Inside the per-agent loop, after `generate_agent_assets()` completes successfully (~line 775), add:
     ```python
     # Install skill pack for this agent
     tracker.start(f"{agent_key}-skills")
     try:
         if skill_registry is None:
             if template_mode == "local" and local_repo is not None:
                 skill_registry = SkillRegistry.from_local_repo(local_repo)
             else:
                 skill_registry = SkillRegistry.from_package()
         skills = skill_registry.discover_skills()
         if skills:
             from specify_cli.skills.installer import install_skills_for_agent
             entries = install_skills_for_agent(
                 project_path, agent_key, skills,
                 shared_root_installed=shared_root_installed,
             )
             for entry in entries:
                 skill_manifest.add_entry(entry)
             tracker.complete(f"{agent_key}-skills", f"{len(skills)} skills installed")
         else:
             tracker.complete(f"{agent_key}-skills", "no skills found")
     except Exception as exc:
         tracker.error(f"{agent_key}-skills", str(exc))
         _logger.warning("Skill installation failed for %s: %s", agent_key, exc)
         # Non-fatal: wrappers are already installed
     ```
- **Files**: `src/specify_cli/cli/commands/init.py` (modify)
- **Notes**: Skill installation failure is non-fatal — wrappers are the baseline, skills are additive. Log warning but don't abort init.

### Subtask T020 – Add StepTracker entries

- **Purpose**: Show skill installation progress in the init output.
- **Steps**:
  1. In the tracker setup section (~line 662-675), add skill steps for each agent:
     ```python
     for agent_key in selected_agents:
         # ... existing steps ...
         tracker.add(f"{agent_key}-skills", f"{label}: install skill pack")
     ```
  2. Place the skill step after the existing per-agent steps (fetch, download, extract, etc.)
- **Files**: `src/specify_cli/cli/commands/init.py` (modify)

### Subtask T021 – Write manifest at end of init

- **Purpose**: Persist the accumulated manifest after all agents are processed.
- **Steps**:
  1. After the per-agent loop completes (before the git step at ~line 826), add:
     ```python
     # Save managed skill manifest
     if skill_manifest.entries:
         save_manifest(skill_manifest, project_path)
     ```
  2. This writes `.kittify/skills-manifest.json`
- **Files**: `src/specify_cli/cli/commands/init.py` (modify)

### Subtask T022 – Handle template_mode for skill source discovery

- **Purpose**: Ensure the skill registry uses the correct source based on init mode.
- **Steps**:
  1. Template modes:
     - `"local"`: Use `SkillRegistry.from_local_repo(local_repo)` — reads from `src/doctrine/skills/`
     - `"package"`: Use `SkillRegistry.from_package()` — reads from installed package
     - `"remote"`: Use `SkillRegistry.from_package()` — remote mode only affects wrappers
  2. This is already handled in T019 with the `template_mode` check
  3. Add debug logging:
     ```python
     if debug:
         _console.print(f"[cyan]Skill source:[/cyan] {skill_registry._skills_root}")
     ```
- **Files**: `src/specify_cli/cli/commands/init.py` (modify, part of T019)

### Subtask T023 – Integration test for init with skills

- **Purpose**: Verify the full init flow produces skills and manifest.
- **Steps**:
  1. Create `tests/specify_cli/skills/test_init_integration.py`
  2. Test approach: mock the init dependencies, call the init function, verify output
  3. Key assertions:
     - `.claude/skills/spec-kitty-setup-doctor/SKILL.md` exists (for native-root agent)
     - `.agents/skills/spec-kitty-setup-doctor/SKILL.md` exists (for shared-root agent)
     - `.kittify/skills-manifest.json` exists and contains entries
     - `.claude/commands/spec-kitty.*.md` still exist (wrappers unchanged)
  4. Use minimal test setup: mock template resolution, use test skill fixtures
- **Files**: `tests/specify_cli/skills/test_init_integration.py` (new, ~120 lines)
- **Parallel?**: Yes (after T019-T022 are done)

## Risks & Mitigations

- **Init.py complexity**: 1140 lines, surgical insertion needed → use git diff to verify only additive changes
- **Existing test breakage**: Init tests may not expect skill steps → run existing init test suite first
- **Non-fatal approach**: Skill installation failure should not abort init → wrap in try/except, log warning

## Review Guidance

- Verify no existing init behavior is modified (wrapper generation, git init, dashboard, etc.)
- Verify skill installation is after wrapper generation but before git step
- Verify manifest is written only if entries exist
- Verify template_mode handling is correct for all three modes
- Run existing init tests to confirm no regressions

## Activity Log

- 2026-03-21T07:39:56Z – system – lane=planned – Prompt created.
