---
work_package_id: WP04
title: Skill Installer
lane: planned
dependencies:
- WP01
subtasks:
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Core Implementation
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
- FR-002
- FR-003
- FR-004
- FR-008
---

# Work Package Prompt: WP04 – Skill Installer

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Implement the skill installer that copies canonical skills to agent-specific skill roots
- Route skills correctly based on the framework capability matrix (AGENT_SKILL_CONFIG)
- Handle shared-root deduplication (install once to `.agents/skills/`)
- Build manifest entries during installation
- Unit tests with 90%+ coverage

**Success**: Given test skills and test agents, skills are copied to correct roots, shared roots are deduplicated, and manifest entries are correctly built.

## Context & Constraints

- **PRD reference**: Section 9 (Installer and Distribution Plan)
- **Dependencies**: WP01 (registry), WP02 (config), WP03 (manifest)
- **Constraint FR-008**: Existing wrapper generation must not be affected
- **Research R-6**: Shared-root agents install to `.agents/skills/` only (first root)

**Implementation command**: `spec-kitty implement WP04 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T014 – Implement `install_skills_for_agent()`

- **Purpose**: Copy all canonical skills into the correct skill root for a single agent.
- **Steps**:
  1. Create `src/specify_cli/skills/installer.py`
  2. Implement:
     ```python
     def install_skills_for_agent(
         project_path: Path,
         agent_key: str,
         skills: list[CanonicalSkill],
         *,
         shared_root_installed: set[str] | None = None,
     ) -> list[ManagedFileEntry]:
         """Install skills for one agent. Returns manifest entries created.

         Args:
             project_path: Project root directory.
             agent_key: Agent identifier (e.g., "claude").
             skills: List of canonical skills to install.
             shared_root_installed: Set of skill names already installed to shared root.
                 Pass a mutable set to enable deduplication across agents.

         Returns:
             List of ManagedFileEntry for each installed file.
         """
     ```
  3. Logic:
     - Look up `agent_key` in `AGENT_SKILL_CONFIG`
     - If `class` is `wrapper-only` → return empty list (skip)
     - If `class` is `shared-root-capable` → use first root (`.agents/skills/`)
       - Check `shared_root_installed` set; skip if already installed
       - Add to set after installation
     - If `class` is `native-root-required` → use first root (vendor-specific)
     - For each skill: copy `SKILL.md`, `references/`, `scripts/`, `assets/` into target root
     - Build `ManagedFileEntry` for each copied file
- **Files**: `src/specify_cli/skills/installer.py` (new, ~100 lines)
- **Notes**: Use `shutil.copy2` for file copies, `shutil.copytree` with `dirs_exist_ok=True` for directories. Create target directories with `mkdir(parents=True, exist_ok=True)`.

### Subtask T015 – Implement `install_all_skills()`

- **Purpose**: Orchestrate skill installation across all selected agents.
- **Steps**:
  1. Add to `src/specify_cli/skills/installer.py`:
     ```python
     def install_all_skills(
         project_path: Path,
         agent_keys: list[str],
         registry: SkillRegistry,
     ) -> ManagedSkillManifest:
         """Install skills for all agents. Returns populated manifest."""
     ```
  2. Logic:
     - Call `registry.discover_skills()` to get all canonical skills
     - Create empty `ManagedSkillManifest` with current timestamp and version
     - Create shared `shared_root_installed: set[str]` for deduplication
     - For each agent: call `install_skills_for_agent()`, collect entries
     - Add all entries to manifest
     - Return manifest (caller responsible for saving)
- **Files**: `src/specify_cli/skills/installer.py` (modify)

### Subtask T016 – Handle shared-root deduplication

- **Purpose**: Ensure skills are installed once to `.agents/skills/`, not repeatedly for each shared-root agent.
- **Steps**:
  1. The `shared_root_installed` set tracks which skills have been copied to `.agents/skills/`
  2. When a shared-root-capable agent is processed:
     - If skill name is in the set → create manifest entry pointing to existing shared path (no file copy)
     - If skill name is NOT in the set → copy files, add to set, create manifest entry
  3. Each agent still gets its own manifest entries (different `agent_key`) but pointing to the same `installed_path`
- **Files**: `src/specify_cli/skills/installer.py` (integrated into T014)
- **Notes**: This means 5 shared-root agents + 1 skill = 1 file copy + 5 manifest entries (all pointing to `.agents/skills/spec-kitty-setup-doctor/SKILL.md`)

### Subtask T017 – Build manifest entries during installation

- **Purpose**: Create accurate `ManagedFileEntry` objects for each installed file.
- **Steps**:
  1. For each file copied (or deduplicated), create:
     ```python
     ManagedFileEntry(
         skill_name=skill.name,
         source_file=str(file_path.relative_to(skill.skill_dir)),
         installed_path=str(target_path.relative_to(project_path)),
         installation_class=config["class"],
         agent_key=agent_key,
         content_hash=compute_content_hash(target_path),
         installed_at=datetime.now(timezone.utc).isoformat(),
     )
     ```
  2. Hash is computed from the installed file (after copy), not from source
- **Files**: `src/specify_cli/skills/installer.py` (integrated into T014)

### Subtask T018 – Unit tests for installer

- **Purpose**: Verify correct installation routing, deduplication, and manifest entry creation.
- **Steps**:
  1. Create `tests/specify_cli/skills/test_installer.py`
  2. Test cases:
     - `test_install_native_root_agent` — claude gets skills in `.claude/skills/`
     - `test_install_shared_root_agent` — codex gets skills in `.agents/skills/`
     - `test_install_wrapper_only_agent_skipped` — q gets no skills, empty entries
     - `test_shared_root_deduplication` — two shared-root agents share one file copy
     - `test_manifest_entries_created` — verify entry fields are correct
     - `test_install_all_skills_orchestration` — full flow with mixed agents
     - `test_install_preserves_existing_files` — existing non-managed files not deleted
     - `test_install_copies_references_and_scripts` — subdirectories are copied
  3. Create test fixtures: minimal `CanonicalSkill` with SKILL.md in `tmp_path`
- **Files**: `tests/specify_cli/skills/test_installer.py` (new, ~180 lines)
- **Parallel?**: Yes

## Risks & Mitigations

- **Shared root race condition**: Parallel agents could try to install simultaneously → single-threaded init loop prevents this
- **File permission errors**: `shutil.copy2` may fail on read-only targets → catch and report clearly
- **Empty skill directories**: Skill with only SKILL.md and no subdirs → handle gracefully (just copy SKILL.md)

## Review Guidance

- Verify deduplication: shared root only gets one copy per skill
- Verify wrapper-only agents are truly skipped
- Verify manifest entries have correct `installed_path` relative to project root
- Verify `content_hash` is computed from installed file, not source

## Activity Log

- 2026-03-21T07:39:56Z – system – lane=planned – Prompt created.
