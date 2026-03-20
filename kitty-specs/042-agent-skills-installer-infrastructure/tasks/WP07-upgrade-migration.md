---
work_package_id: WP07
title: Upgrade Migration
lane: "for_review"
dependencies: [WP01, WP02, WP03, WP04]
base_branch: 042-agent-skills-installer-infrastructure-WP04
base_commit: 02040aa5810b7dde66c0e3394a7178d059c38ca9
created_at: '2026-03-20T17:41:02.463722+00:00'
subtasks:
- T033
- T034
- T035
- T036
phase: Phase 3 - Integration
assignee: ''
agent: coordinator
shell_pid: '48735'
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-20T16:29:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-020
- FR-021
- FR-022
- NFR-006
---

# Work Package Prompt: WP07 – Upgrade Migration

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP07 --base WP04
```

Depends on WP01–WP04.

---

## Objectives & Success Criteria

1. Pre-Phase-0 projects gain a manifest and empty skill roots after running `spec-kitty upgrade`.
2. Existing wrapper files are tracked in the manifest with correct hashes.
3. Migration is idempotent — running twice produces same result.
4. Migration is config-aware — only processes configured agents.
5. No existing files are modified or deleted.

## Context & Constraints

- **Spec**: FR-020, FR-021, FR-022, NFR-006
- **Plan**: Section 8 (Upgrade Migration)
- **Migration base class**: `src/specify_cli/upgrade/migrations/base.py`
- **Migration registry**: Decorated with `@MigrationRegistry.register`
- **Existing pattern**: Study `m_0_9_1_complete_lane_migration.py` for the canonical migration pattern
- **Config-aware**: Use `get_agent_dirs_for_project()` to only process configured agents
- **Version**: Target 2.1.0

## Subtasks & Detailed Guidance

### Subtask T033 – Create migration class

**Purpose**: Scaffold the migration file following the established pattern.

**Steps**:
1. Create `src/specify_cli/upgrade/migrations/m_2_1_0_agent_surface_manifest.py`
2. Define class:
   ```python
   from specify_cli.upgrade.migrations.base import BaseMigration, MigrationResult, MigrationRegistry

   @MigrationRegistry.register
   class AgentSurfaceManifestMigration(BaseMigration):
       migration_id = "2_1_0_agent_surface_manifest"
       description = "Add skills manifest and empty skill roots for configured agents"
       target_version = "2.1.0"
       min_version = None  # Applicable to any previous version
   ```

**Files**: `src/specify_cli/upgrade/migrations/m_2_1_0_agent_surface_manifest.py` (new, ~120 lines)

### Subtask T034 – Implement detect() and can_apply()

**Purpose**: Determine if migration should run.

**Steps**:
1. `detect()` returns `True` if project has `.kittify/config.yaml` but no `.kittify/agent-surfaces/skills-manifest.yaml`:
   ```python
   def detect(self, project_path: Path) -> bool:
       config_exists = (project_path / ".kittify" / "config.yaml").exists()
       manifest_exists = (project_path / ".kittify" / "agent-surfaces" / "skills-manifest.yaml").exists()
       return config_exists and not manifest_exists
   ```

2. `can_apply()` returns `(True, "")` always (migration is safe and idempotent):
   ```python
   def can_apply(self, project_path: Path) -> tuple[bool, str]:
       return True, ""
   ```

**Files**: `src/specify_cli/upgrade/migrations/m_2_1_0_agent_surface_manifest.py`

### Subtask T035 – Implement apply()

**Purpose**: Create manifest from current state and add empty skill roots.

**Steps**:
1. Read configured agents:
   ```python
   from specify_cli.agent_utils.directories import get_agent_dirs_for_project
   from specify_cli.core.agent_config import get_configured_agents

   agents = get_configured_agents(project_path)
   if not agents:
       return MigrationResult(success=True, message="No agents configured, skipping")
   ```

2. Resolve skill roots in auto mode:
   ```python
   from specify_cli.skills.roots import resolve_skill_roots
   resolved_roots = resolve_skill_roots(agents, mode="auto")
   ```

3. Create empty skill roots:
   ```python
   if not dry_run:
       for root in resolved_roots:
           root_path = project_path / root
           root_path.mkdir(parents=True, exist_ok=True)
           gitkeep = root_path / ".gitkeep"
           if not gitkeep.exists():
               gitkeep.write_text("", encoding="utf-8")
   ```

4. Build manifest from existing wrapper files:
   ```python
   from specify_cli.skills.manifest import ManagedFile, SkillsManifest, compute_file_hash, write_manifest
   from specify_cli.core.agent_surface import get_agent_surface

   managed_files: list[ManagedFile] = []

   # Track skill root markers
   for root in resolved_roots:
       gitkeep = project_path / root / ".gitkeep"
       if gitkeep.exists():
           managed_files.append(ManagedFile(
               path=f"{root}.gitkeep",
               sha256=compute_file_hash(gitkeep),
               file_type="skill_root_marker",
           ))

   # Track existing wrapper files
   agent_dirs = get_agent_dirs_for_project(project_path)
   for agent_root, subdir in agent_dirs:
       wrapper_dir = project_path / agent_root / subdir
       if wrapper_dir.exists():
           for f in sorted(wrapper_dir.iterdir()):
               if f.is_file() and f.name.startswith("spec-kitty."):
                   managed_files.append(ManagedFile(
                       path=str(f.relative_to(project_path)),
                       sha256=compute_file_hash(f),
                       file_type="wrapper",
                   ))
   ```

5. Write manifest:
   ```python
   if not dry_run:
       now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
       manifest = SkillsManifest(
           spec_kitty_version="2.1.0",
           created_at=now_iso,
           updated_at=now_iso,
           skills_mode="auto",
           selected_agents=agents,
           installed_skill_roots=resolved_roots,
           managed_files=managed_files,
       )
       write_manifest(project_path, manifest)

   return MigrationResult(
       success=True,
       message=f"Created skills manifest with {len(resolved_roots)} skill root(s) and {len(managed_files)} tracked file(s)",
   )
   ```

6. Respect `dry_run` parameter — don't create files/dirs when `dry_run=True`.

**Files**: `src/specify_cli/upgrade/migrations/m_2_1_0_agent_surface_manifest.py`

### Subtask T036 – Migration tests

**Purpose**: Verify migration correctness across configurations.

**Steps**:
1. Create `tests/specify_cli/test_migrations/test_agent_surface_migration.py`
2. Tests:

```python
# Detect: project without manifest → True
def test_detect_no_manifest(tmp_path):
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("agents:\n  available:\n    - claude\n")
    migration = AgentSurfaceManifestMigration()
    assert migration.detect(tmp_path)

# Detect: project with manifest → False
def test_detect_with_manifest(tmp_path):
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("agents:\n  available:\n    - claude\n")
    (tmp_path / ".kittify" / "agent-surfaces").mkdir(parents=True)
    (tmp_path / ".kittify" / "agent-surfaces" / "skills-manifest.yaml").write_text("")
    assert not AgentSurfaceManifestMigration().detect(tmp_path)

# Apply: creates manifest and skill roots
def test_apply_creates_manifest(tmp_path):
    # Setup config with claude + codex
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n    - codex\n"
    )
    # Create existing wrapper dirs
    (tmp_path / ".claude" / "commands").mkdir(parents=True)
    (tmp_path / ".claude" / "commands" / "spec-kitty.specify.md").write_text("test")
    (tmp_path / ".codex" / "prompts").mkdir(parents=True)
    (tmp_path / ".codex" / "prompts" / "spec-kitty.specify.md").write_text("test")

    result = AgentSurfaceManifestMigration().apply(tmp_path)
    assert result.success

    # Verify manifest exists
    assert (tmp_path / ".kittify" / "agent-surfaces" / "skills-manifest.yaml").exists()
    # Verify skill roots created
    assert (tmp_path / ".agents" / "skills" / ".gitkeep").exists()  # for codex
    assert (tmp_path / ".claude" / "skills" / ".gitkeep").exists()  # for claude
    # Verify existing wrappers untouched
    assert (tmp_path / ".claude" / "commands" / "spec-kitty.specify.md").read_text() == "test"

# Apply: idempotent (run twice, same result)
def test_apply_idempotent(tmp_path):
    # Setup and apply once
    # ... (same as above)
    # Apply again
    result2 = AgentSurfaceManifestMigration().apply(tmp_path)
    # detect() returns False now (manifest exists), but apply still succeeds if called

# Apply: config-aware (only configured agents)
def test_apply_config_aware(tmp_path):
    # Setup config with only opencode
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - opencode\n"
    )
    result = AgentSurfaceManifestMigration().apply(tmp_path)
    assert result.success
    # Verify .agents/skills/ created (opencode is shared-root-capable)
    assert (tmp_path / ".agents" / "skills" / ".gitkeep").exists()
    # Verify .claude/skills/ NOT created (claude not configured)
    assert not (tmp_path / ".claude" / "skills").exists()
```

**Files**: `tests/specify_cli/test_migrations/test_agent_surface_migration.py` (new, ~100 lines)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Migration runs before AGENT_SURFACE_CONFIG exists (old code) | Migration targets 2.1.0 — only runs on new CLI version |
| Wrapper files have unexpected names | Only collect files matching `spec-kitty.*` pattern |
| Legacy project without config.yaml | `get_configured_agents()` returns empty list → migration skips gracefully |

## Review Guidance

1. Verify `dry_run` parameter is respected (no filesystem changes).
2. Verify idempotency — running twice doesn't duplicate entries.
3. Verify only configured agents get skill roots.
4. Verify existing wrapper files are not modified.

## Activity Log

- 2026-03-20T16:29:09Z – system – lane=planned – Prompt created.
- 2026-03-20T17:41:02Z – coordinator – shell_pid=48735 – lane=doing – Assigned agent via workflow command
- 2026-03-20T17:45:27Z – coordinator – shell_pid=48735 – lane=for_review – Ready for review: migration creates skills manifest and empty skill roots for configured agents, tracks existing wrappers, is idempotent and config-aware. All 15 tests pass.
