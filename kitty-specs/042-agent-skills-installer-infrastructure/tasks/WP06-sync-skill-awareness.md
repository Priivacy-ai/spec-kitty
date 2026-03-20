---
work_package_id: WP06
title: Agent Config Sync Skill Awareness
lane: "approved"
dependencies: [WP02, WP03]
base_branch: 042-agent-skills-installer-infrastructure-WP03
base_commit: fffc6ec2d5dbd24eb746058f5087717457777579
created_at: '2026-03-20T17:29:57.784627+00:00'
subtasks:
- T028
- T029
- T030
- T031
- T032
phase: Phase 3 - Integration
assignee: ''
agent: codex
shell_pid: '43906'
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-03-20T16:29:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-016
- FR-017
- FR-023
---

# Work Package Prompt: WP06 – Agent Config Sync Skill Awareness

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP06 --base WP03
```

Depends on WP02 (skill root resolution) and WP03 (manifest CRUD).

---

## Objectives & Success Criteria

1. `spec-kitty agent config sync` reads the manifest and repairs missing skill roots.
2. Orphaned skill roots are removed only if no other configured agent needs them (shared root protection).
3. Manifest is updated after sync changes.
4. Pre-existing sync behavior (wrapper directory management) is unchanged.

## Context & Constraints

- **Spec**: FR-016, FR-017, FR-023
- **Plan**: Section 7 (Sync Modifications)
- **Current sync code**: `src/specify_cli/cli/commands/agent/config.py` lines 307–386
- **KEY_TO_AGENT_DIR mapping**: Already exists in `config.py` — check how it's defined
- **Critical**: Shared root (`.agents/skills/`) must NOT be removed if any configured agent still needs it

## Subtasks & Detailed Guidance

### Subtask T028 – Load manifest in sync_agents

**Purpose**: Make the manifest available for skill root awareness.

**Steps**:
1. At the start of `sync_agents()`, after loading config, add:
   ```python
   from specify_cli.skills.manifest import load_manifest
   manifest = load_manifest(repo_root)
   ```
2. If manifest is None (pre-Phase-0 project), skip skill root sync with a message:
   ```python
   if manifest is None:
       console.print("[dim]No skills manifest found - skipping skill root sync[/dim]")
   ```

**Files**: `src/specify_cli/cli/commands/agent/config.py`

### Subtask T029 – Repair missing skill roots

**Purpose**: Recreate skill root directories that should exist but are missing.

**Steps**:
1. After the existing `--create-missing` block, add skill root repair:
   ```python
   if create_missing and manifest:
       console.print("\n[cyan]Checking for missing skill roots...[/cyan]")
       from specify_cli.skills.roots import resolve_skill_roots
       expected_roots = resolve_skill_roots(config.available, mode=manifest.skills_mode)
       for root in expected_roots:
           root_path = repo_root / root
           if not root_path.exists():
               root_path.mkdir(parents=True, exist_ok=True)
               (root_path / ".gitkeep").write_text("", encoding="utf-8")
               console.print(f"  [green]✓[/green] Recreated skill root {root}")
               changes_made = True
   ```

**Files**: `src/specify_cli/cli/commands/agent/config.py`

### Subtask T030 – Shared root protection during orphan removal

**Purpose**: Don't remove `.agents/skills/` if any remaining configured agent needs it.

**Steps**:
1. Modify the orphan removal section to also handle skill roots:
   ```python
   if remove_orphaned and manifest:
       console.print("\n[cyan]Checking for orphaned skill roots...[/cyan]")
       # Compute which roots are still needed by configured agents
       needed_roots = set(resolve_skill_roots(config.available, mode=manifest.skills_mode))
       # Check manifest for roots that were installed but are no longer needed
       for root in manifest.installed_skill_roots:
           if root not in needed_roots:
               root_path = repo_root / root
               if root_path.exists():
                   # Only remove managed content (gitkeep), not user files
                   gitkeep = root_path / ".gitkeep"
                   if gitkeep.exists():
                       gitkeep.unlink()
                   # Only rmdir if empty (don't delete user content)
                   try:
                       root_path.rmdir()
                       console.print(f"  [green]✓[/green] Removed orphaned skill root {root}")
                       changes_made = True
                   except OSError:
                       console.print(f"  [yellow]⚠[/yellow] Skill root {root} has non-managed content, keeping")
   ```

2. **Key safety rule**: Use `rmdir()` not `shutil.rmtree()` — only removes the directory if empty (after removing the managed `.gitkeep`). This protects user-authored content.

**Files**: `src/specify_cli/cli/commands/agent/config.py`

### Subtask T031 – Update manifest after changes

**Purpose**: Keep manifest in sync with filesystem state after repair/cleanup.

**Steps**:
1. After all sync operations, if changes were made and manifest exists:
   ```python
   if changes_made and manifest:
       from specify_cli.skills.manifest import write_manifest
       from datetime import datetime, timezone
       # Recompute installed roots
       manifest.installed_skill_roots = [
           root for root in manifest.installed_skill_roots
           if (repo_root / root).exists()
       ]
       # Add any newly created roots
       for root in expected_roots:
           if root not in manifest.installed_skill_roots and (repo_root / root).exists():
               manifest.installed_skill_roots.append(root)
       manifest.installed_skill_roots.sort()
       manifest.updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
       write_manifest(repo_root, manifest)
   ```

**Files**: `src/specify_cli/cli/commands/agent/config.py`

### Subtask T032 – Unit tests

**Purpose**: Verify repair, shared root protection, and orphan cleanup.

**Steps**:
1. Create `tests/specify_cli/test_cli/test_sync_skills.py` (or add to existing sync test file)
2. Tests:

```python
# Repair missing skill root
def test_sync_repairs_missing_skill_root(tmp_path):
    # Setup: config with claude, manifest with .claude/skills/, but directory missing
    # Run sync with --create-missing
    # Verify .claude/skills/ recreated with .gitkeep

# Shared root preserved when still needed
def test_sync_preserves_shared_root_for_remaining_agent(tmp_path):
    # Setup: config has codex (removed copilot), .agents/skills/ exists
    # Run sync with --remove-orphaned
    # Verify .agents/skills/ NOT removed (codex still needs it)

# Orphaned skill root removed when no agent needs it
def test_sync_removes_orphaned_skill_root(tmp_path):
    # Setup: config has only q (wrapper-only), manifest has .agents/skills/ from when codex was configured
    # Run sync
    # Verify .agents/skills/ removed (no configured agent needs it)

# Non-managed content preserved
def test_sync_preserves_user_content_in_skill_root(tmp_path):
    # Setup: .agents/skills/ has user-created files
    # Run sync removing the root
    # Verify directory kept (rmdir fails on non-empty)
```

**Files**: `tests/specify_cli/test_cli/test_sync_skills.py` (new, ~80 lines)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Removing .agents/skills/ when another agent needs it | `resolve_skill_roots()` for remaining agents tells us exactly what's still needed |
| Deleting user content | Use `rmdir()` not `rmtree()` — only succeeds on empty dirs |
| Manifest stale after sync | Always rewrite manifest after changes |

## Review Guidance

1. Verify shared root protection logic — `.agents/skills/` must survive if ANY configured agent is shared-root-capable.
2. Verify `rmdir()` is used instead of `shutil.rmtree()` for skill root cleanup.
3. Verify manifest is updated after any sync changes.

## Activity Log

- 2026-03-20T16:29:09Z – system – lane=planned – Prompt created.
- 2026-03-20T17:37:38Z – unknown – shell_pid=15294 – lane=for_review – Ready for review: skill root awareness in agent config sync
- 2026-03-20T17:38:10Z – codex – shell_pid=43906 – lane=doing – Started review via workflow command
- 2026-03-20T17:41:51Z – codex – shell_pid=43906 – lane=approved – Review passed: skill root sync covers repair, shared-root protection, and manifest updates
