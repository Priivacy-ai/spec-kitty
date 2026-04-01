---
work_package_id: WP01
title: Canonical Skill Source Layout & Registry
dependencies: []
requirement_refs:
- FR-001
- C-004
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 0 - Foundation
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
- src/doctrine/**
- src/specify_cli/runtime/home.py
- src/specify_cli/skills/**
- src/specify_cli/template/__init__.py
- src/specify_cli/templates/skills/<skill-name/**
- tests/specify_cli/skills/__init__.py
- tests/specify_cli/skills/test_registry.py
wp_code: WP01
---

# Work Package Prompt: WP01 – Canonical Skill Source Layout & Registry

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create the canonical skill source directory under `src/doctrine/skills/`
- Create the `src/specify_cli/skills/` Python package
- Implement a skill registry that discovers canonical skills from either local dev checkout or installed package
- Unit tests for the registry with 90%+ coverage

**Success**: `SkillRegistry.discover_skills()` returns a list of `CanonicalSkill` objects from a test fixture directory, with correct file lists.

## Context & Constraints

- **PRD reference**: Section 9 (Installer and Distribution Plan) — canonical authored source at `src/specify_cli/templates/skills/<skill-name>/SKILL.md`. Adapted to `src/doctrine/skills/<skill-name>/` per 2.x architecture.
- **Constraint C-004**: Canonical skill source must reside in `src/doctrine/skills/`
- **Architecture**: `src/doctrine/` is already bundled via `also_copy` in `pyproject.toml`, so no packaging changes needed
- **Existing patterns**: `get_local_repo_root()` in `src/specify_cli/template/__init__.py` and `get_package_asset_root()` in `src/specify_cli/runtime/home.py` provide the two discovery paths

**Implementation command**: `spec-kitty implement WP01`

## Subtasks & Detailed Guidance

### Subtask T001 – Create `src/doctrine/skills/` directory structure

- **Purpose**: Establish the canonical authored skill source directory in the doctrine content layer.
- **Steps**:
  1. Create `src/doctrine/skills/` directory
  2. Create a placeholder directory `src/doctrine/skills/spec-kitty-setup-doctor/` with an empty `SKILL.md` (real content in WP08)
     ```yaml
     ---
     name: spec-kitty-setup-doctor
     description: "Placeholder — full content authored in WP08"
     ---

     # spec-kitty-setup-doctor

     Placeholder skill. See WP08 for full implementation.
     ```
  3. Create empty `references/` and `scripts/` subdirectories under the skill with `.gitkeep` files
- **Files**:
  - `src/doctrine/skills/spec-kitty-setup-doctor/SKILL.md` (new)
  - `src/doctrine/skills/spec-kitty-setup-doctor/references/.gitkeep` (new)
  - `src/doctrine/skills/spec-kitty-setup-doctor/scripts/.gitkeep` (new)
- **Notes**: The directory structure must match the PRD's canonical layout: `SKILL.md` at root, optional `references/`, `scripts/`, `assets/` subdirectories.

### Subtask T002 – Create `src/specify_cli/skills/` package

- **Purpose**: Create the Python package that will hold all skill distribution runtime code.
- **Steps**:
  1. Create `src/specify_cli/skills/__init__.py` with public API exports:
     ```python
     """Skill distribution runtime for Spec Kitty 2.0.11+."""

     from __future__ import annotations

     from .registry import CanonicalSkill, SkillRegistry

     __all__ = ["CanonicalSkill", "SkillRegistry"]
     ```
  2. Ensure the directory is a proper Python package
- **Files**:
  - `src/specify_cli/skills/__init__.py` (new)
- **Notes**: Additional exports (manifest, installer, verifier) will be added by subsequent WPs.

### Subtask T003 – Implement `src/specify_cli/skills/registry.py`

- **Purpose**: Discover canonical skills from the doctrine layer, whether from a local dev checkout or an installed package.
- **Steps**:
  1. Define `CanonicalSkill` dataclass:
     ```python
     @dataclass(frozen=True)
     class CanonicalSkill:
         name: str                    # e.g., "spec-kitty-setup-doctor"
         skill_dir: Path              # Directory containing SKILL.md
         skill_md: Path               # Path to SKILL.md
         references: list[Path]       # Files in references/ subdirectory
         scripts: list[Path]          # Files in scripts/ subdirectory
         assets: list[Path]           # Files in assets/ subdirectory

         @property
         def all_files(self) -> list[Path]:
             """All installable files (SKILL.md + references + scripts + assets)."""
             return [self.skill_md] + self.references + self.scripts + self.assets
     ```
  2. Define `SkillRegistry` class:
     ```python
     class SkillRegistry:
         def __init__(self, skills_root: Path) -> None:
             self._skills_root = skills_root

         @classmethod
         def from_local_repo(cls, repo_root: Path) -> SkillRegistry:
             """Create registry from local dev checkout."""
             return cls(repo_root / "src" / "doctrine" / "skills")

         @classmethod
         def from_package(cls) -> SkillRegistry:
             """Create registry from installed package."""
             from specify_cli.runtime.home import get_package_asset_root
             pkg_root = get_package_asset_root()
             return cls(pkg_root / "doctrine" / "skills")

         def discover_skills(self) -> list[CanonicalSkill]:
             """Discover all valid skills in the skills root."""
             # Scan for directories containing SKILL.md
             ...

         def get_skill(self, name: str) -> CanonicalSkill | None:
             """Get a specific skill by name."""
             ...
     ```
  3. Implement `discover_skills()`:
     - List all subdirectories of `self._skills_root`
     - For each subdirectory, check if `SKILL.md` exists
     - If yes, build a `CanonicalSkill` with all files from `references/`, `scripts/`, `assets/`
     - Sort results by name for deterministic ordering
  4. Implement `get_skill()` — look up a single skill by name
- **Files**:
  - `src/specify_cli/skills/registry.py` (new, ~80 lines)
- **Notes**:
  - Use `pathlib` for all path operations
  - Handle missing `skills_root` gracefully (return empty list, not crash)
  - Ignore directories that don't contain SKILL.md (e.g., `__pycache__`)
  - All type annotations required (mypy --strict)

### Subtask T004 – Unit tests for registry

- **Purpose**: Verify registry discovers skills correctly from fixture directories.
- **Steps**:
  1. Create `tests/specify_cli/skills/__init__.py`
  2. Create `tests/specify_cli/skills/test_registry.py`
  3. Test cases:
     - `test_discover_skills_finds_valid_skill` — create a skill dir with SKILL.md, verify discovery
     - `test_discover_skills_ignores_dir_without_skill_md` — directory without SKILL.md is skipped
     - `test_discover_skills_empty_root` — empty skills root returns empty list
     - `test_discover_skills_missing_root` — nonexistent root returns empty list
     - `test_discover_skills_collects_references_scripts_assets` — verify all file types collected
     - `test_get_skill_by_name` — lookup returns correct skill
     - `test_get_skill_not_found` — lookup returns None for missing name
     - `test_from_local_repo` — verify path construction from repo root
  4. Use `tmp_path` fixture to create test skill directories
- **Files**:
  - `tests/specify_cli/skills/__init__.py` (new)
  - `tests/specify_cli/skills/test_registry.py` (new, ~120 lines)
- **Parallel?**: Yes — can be written alongside T003

## Risks & Mitigations

- **Path differences in CI**: Package asset root may not exist in test environments → use `tmp_path` fixtures with mocked paths
- **Platform differences**: Windows vs Unix path separators → use `pathlib.Path` exclusively

## Review Guidance

- Verify `CanonicalSkill.all_files` includes SKILL.md and all sibling directory files
- Verify registry handles edge cases (empty, missing, invalid directories)
- Verify type annotations pass mypy --strict
- Check that no absolute paths are hardcoded

## Activity Log

- 2026-03-21T07:39:56Z – system – lane=planned – Prompt created.
