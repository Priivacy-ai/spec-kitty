---
work_package_id: WP07
title: Command-Skill Manifest Repair and Roo Code Deprecation
dependencies:
- WP01
requirement_refs:
- FR-030
- FR-031
- FR-032
- FR-033
- FR-034
- FR-035
- FR-036
tracker_refs: []
planning_base_branch: feat/agent-profile-projection-plugin-production
merge_target_branch: feat/agent-profile-projection-plugin-production
branch_strategy: Planning artifacts for this mission were generated on feat/agent-profile-projection-plugin-production. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/agent-profile-projection-plugin-production unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-agent-profile-projection-plugin-production-01KV3NGS-01KV3NGS
base_commit: unknown
created_at: '2026-06-14T20:41:27.482661+00:00'
subtasks:
- T028
- T029
- T030
- T031
- T032
- T033
- T034
agent: claude
shell_pid: '72856'
history:
- at: '2026-06-14T00:00:00Z'
  event: created
  actor: claude
agent_profile: engineer
authoritative_surface: src/specify_cli/skills/
create_intent:
- src/specify_cli/upgrade/migrations/m_0_9_4_roo_deprecation.py
- docs/supported-agents.md
execution_mode: code_change
owned_files:
- src/specify_cli/skills/manifest_store.py
- src/specify_cli/skills/manifest.py
- src/specify_cli/core/config.py
- src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py
- src/specify_cli/upgrade/migrations/m_0_9_4_roo_deprecation.py
- README.md
- docs/supported-agents.md
role: Senior Python Engineer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading any other section of this prompt, load your agent profile:

```
/ad-hoc-profile-load engineer
```

---

## Objective

Make stale command-skill manifests self-heal during `spec-kitty upgrade` (going from 11-entry rc36/rc43 manifests to the canonical count); apply the WP01 drift policy to drifted SKILL.md files; detect and remove unsafe symlink artifacts; fully remove Roo Code from `AI_CHOICES`, `AGENT_DIRS`, and `config.yaml`; emit a deprecation notice when `.roo/` is detected; and clean up documentation.

This WP pairs with WP01 (drift policy service) and must land after it.

---

## Context

Two distinct problem areas in this WP:

**Area A: Manifest self-heal (T028-T030)**
The command-skill manifest (`command-skills-manifest.json`) in rc36/rc43 projects has 11 entries. The canonical set is 15 (or whatever `spec-kitty skills list --canonical` returns). The manifest must be repaired during `upgrade`, not just reported. Drifted SKILL.md files (content has changed) must follow the drift policy from WP01 — no silent overwrite, use `run_surface_repair()` to handle them. Unsafe symlink artifacts like `.agents/skills/spec-kitty.advise` were created by a past migration bug and must be cleaned up.

**Area B: Roo Code removal (T031-T034)**
Roo Code (the editor) shut down. Its entries must be removed from the codebase. However: do NOT break projects that already have a `.roo/` directory by deleting it — preserve it and emit a deprecation notice. The C-007 constraint says: handle Roo Code absence gracefully, no failure if `.roo/` is absent.

**Key constraint from CLAUDE.md**: Use `get_agent_dirs_for_project()` for migration code. Never hardcode `AGENT_DIRS`. When removing Roo from `AGENT_DIRS`, also remove it from the migration that builds `AGENT_DIRS` — but verify all callers of `AGENT_DIRS` still work.

---

## Subtask Guidance

### T028 — Repair stale manifests (11→canonical count) during upgrade

In `src/specify_cli/skills/manifest_store.py`, add a `repair_stale_manifest()` function:

```python
def repair_stale_manifest(
    project_root: Path,
    *,
    canonical_commands: list[str],
) -> ManifestRepairResult:
    """
    Compare the manifest entry count against canonical_commands.
    If stale, add missing entries and remove orphaned entries.
    Returns a result describing what was added/removed.
    """
```

Call this from the post-migration hook in `upgrade/runner.py` (after WP01 wires `run_surface_repair()`). The repair is always auto-applied (no prompt needed) — stale manifest repair is Rule 2 (auto-repair), not Rule 3 (prompt).

Determine `canonical_commands` from `spec-kitty skills list --canonical --json` or by reading from `src/specify_cli/skills/command_renderer.py`'s canonical set.

Do NOT call this from within a specific-version migration file — the manifest repair should be idempotent and version-independent. Place it in the post-migration hook alongside `run_surface_repair()`.

### T029 — Apply drift policy to drifted SKILL.md files

Drifted SKILL.md files (files whose content hash differs from canonical) must route through the WP01 `run_surface_repair()` function — not through a separate code path.

Verify that `SurfaceRepairService` (or its updated version from WP01) correctly identifies drifted SKILL.md files in `.agents/skills/spec-kitty.<cmd>/SKILL.md`. The `SurfaceKind` for these is `COMMAND_SKILL` with wire value `command_skill`.

If the current `SurfaceRepairService` only handles `SurfaceKind.AGENT_PROFILE` (`agent_profile`) surfaces, extend it to also enumerate `SurfaceKind.COMMAND_SKILL` (`command_skill`) surfaces and apply the same drift detection + policy logic.

### T030 — Detect and remove unsafe symlink artifacts

During upgrade, check for symlinks in `.agents/skills/`:

```python
def _remove_unsafe_skill_symlinks(project_root: Path) -> list[Path]:
    """Remove spec-kitty.* symlinks in .agents/skills/ that are broken or external."""
    skills_dir = project_root / ".agents" / "skills"
    removed = []
    if not skills_dir.exists():
        return removed
    for entry in skills_dir.iterdir():
        # Only touch spec-kitty.* entries — never remove arbitrary user symlinks
        if not entry.name.startswith("spec-kitty."):
            continue
        if entry.is_symlink():
            target = entry.resolve() if entry.exists() else None
            if target is None or not str(target).startswith(str(project_root)):
                entry.unlink()
                removed.append(entry)
    return removed
```

Include the count of removed symlinks in the `DriftPolicySummary` from WP01 (add a `removed_symlinks: list[Path]` field).

This specifically targets the `.agents/skills/spec-kitty.advise` symlink artifact from a past migration bug. The `entry.name.startswith("spec-kitty.")` guard ensures we never touch arbitrary user-owned symlinks in the same directory — only act on actual `is_symlink()` entries whose name matches the spec-kitty skill naming convention.

### T031 — Remove `roo` from `AI_CHOICES` in `config.py` and from `AGENT_DIRS`

In `src/specify_cli/core/config.py`, remove the Roo Code entry from `AI_CHOICES`:

```python
# REMOVE this line:
"roo": "Roo Code",
```

Before removing, grep for all callers of `AI_CHOICES` to understand impact:
```bash
grep -r "AI_CHOICES" src/
grep -r '"roo"' src/
```

Also remove from `AGENT_DIRS` in `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`. The `("roo", "commands")` tuple (or equivalent) must be removed. Use `get_agent_dirs_for_project()` everywhere it was used — never reconstruct the list manually.

Verify that no test or code hardcodes `"roo"` as an expected agent key after this change. If tests reference `"roo"`, update them to reflect the post-deprecation state.

### T032 — Emit Roo Code deprecation notice when `.roo/` detected during upgrade

In the new migration `src/specify_cli/upgrade/migrations/m_0_9_4_roo_deprecation.py`:

```python
from specify_cli.agent_utils.directories import get_agent_dirs_for_project

def migrate(project_path: Path, **kwargs) -> MigrationResult:
    roo_dir = project_path / ".roo"
    if not roo_dir.exists():
        return MigrationResult(success=True, changed=False)

    # Emit deprecation notice — do NOT delete .roo/ directory
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    console.print(Panel(
        "[yellow]Roo Code has been discontinued as of 2026-05-15.[/yellow]\n"
        "The [bold].roo/[/bold] directory has been preserved but Roo Code\n"
        "will no longer be maintained or generated by spec-kitty.\n"
        "You may safely delete [bold].roo/[/bold] if you are not using Roo Code.",
        title="Roo Code Deprecation Notice",
        border_style="yellow",
    ))
    return MigrationResult(success=True, changed=False, notes="Roo Code deprecation notice emitted.")
```

**Do NOT delete `.roo/`**. The C-007 constraint is: preserve existing `.roo/` directories; only stop generating new ones.

Register this migration in the migration registry with an appropriate version number (after the WP01 migration `m_0_9_3`).

### T033 — Remove `roo` from `.kittify/config.yaml` when present during upgrade

Extend `m_0_9_4_roo_deprecation.py` to also clean `roo` from the project's agent config:

```python
# load_agent_config / save_agent_config live in specify_cli.core.agent_config, NOT agent_utils.directories
from specify_cli.core.agent_config import load_agent_config, save_agent_config, AgentConfig

config = load_agent_config(project_path)
# AgentConfig is a dataclass; access .available (list[str]), not config.get("agents", [])
if "roo" in config.available:
    updated = AgentConfig(
        available=[a for a in config.available if a != "roo"],
        auto_commit=config.auto_commit,
    )
    save_agent_config(project_path, updated)
    return MigrationResult(success=True, changed=True, notes="Removed roo from agent config.")
```

Include this in the upgrade summary: `Removed 'roo' from .kittify/config.yaml (Roo Code discontinued).`

This must only run if `.kittify/config.yaml` exists and contains `roo`. Do not create `config.yaml` if it doesn't exist.

### T034 — Update `README.md` and `docs/` to remove Roo Code from Supported AI Agents

In `README.md`, remove Roo Code from the Supported AI Agents table. Add a note at the bottom of the table:

```markdown
> **Roo Code** support was removed in 3.2.0. Roo Code (the editor) discontinued service on 2026-05-15.
> Existing `.roo/` directories are preserved; new generation is no longer supported.
```

If `docs/supported-agents.md` (or equivalent) exists, apply the same edit there.

Run the terminology guard to ensure no Roo Code references survive in user-facing prose:
```bash
pytest tests/architectural/test_no_legacy_terminology.py
```

If the terminology guard does not cover Roo Code deprecation, that is fine — the test only enforces the `Mission`/`feature` canon. Manually verify no other docs reference Roo Code as an active agent.

---

## Branch Strategy

- **Planning base branch**: `feat/agent-profile-projection-plugin-production`
- **Final merge target**: `feat/agent-profile-projection-plugin-production`
- **Depends on**: WP01 (drift policy service must exist before T028-T030)

To start work: `spec-kitty agent action implement WP07 --agent claude`

---

## Definition of Done

- [ ] Stale manifests (11→canonical count) auto-repaired during upgrade
- [ ] Drifted SKILL.md files route through `run_surface_repair()` from WP01
- [ ] Unsafe symlinks in `.agents/skills/` detected and removed; count in summary
- [ ] `"roo"` removed from `AI_CHOICES` in `config.py`
- [ ] `"roo"` removed from `AGENT_DIRS` in `m_0_9_1_complete_lane_migration.py`
- [ ] `m_0_9_4_roo_deprecation.py` migration registered; emits Rich deprecation panel when `.roo/` detected
- [ ] `.roo/` directory preserved (NOT deleted)
- [ ] `roo` removed from `.kittify/config.yaml` when present
- [ ] `README.md` Roo Code row removed; deprecation note added
- [ ] `ruff check` and `mypy --strict` pass on all changed modules
- [ ] Terminology guard (`pytest tests/architectural/test_no_legacy_terminology.py`) passes

---

## Risks

- Removing `"roo"` from `AI_CHOICES` may break `spec-kitty init --ai roo` — add a user-facing error: `"roo" is no longer supported (Roo Code discontinued 2026-05-15)`
- `AGENT_DIRS` may be used in tests that enumerate all 12 configured agents — those tests will need to be updated to 11 or to check dynamically
- `load_agent_config` / `save_agent_config` may use ruamel.yaml which preserves comments; verify the save doesn't strip YAML comments from `config.yaml`
- The Rich deprecation panel assumes a TTY is available — gate behind `console.is_terminal` or use `typer.echo` fallback
