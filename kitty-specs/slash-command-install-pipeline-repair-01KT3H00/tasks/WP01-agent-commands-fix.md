---
work_package_id: WP01
title: Fix agent_commands.py — resolver, renderer, lock
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-012
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T005
- T006
- T007
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/runtime/
execution_mode: code_change
owned_files:
- src/specify_cli/runtime/agent_commands.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## ⚑ Preflight (before first implementation commit)

### 1. Assign GitHub issues to HiC (charter binding)

```bash
unset GITHUB_TOKEN
gh issue edit 1608 --assignee rdouglass
gh issue edit 1609 --assignee rdouglass
gh issue edit 1610 --assignee rdouglass
```

### 2. ATDD-First commit (charter C-011 — mandatory)

Before writing any implementation code, commit a minimal failing test to `tests/specify_cli/runtime/test_agent_commands.py` (create the file if absent):

```python
def test_resolver_returns_path_not_none():
    """Fails until FR-001 is implemented: resolver currently returns None."""
    from specify_cli.runtime.agent_commands import _get_command_templates_dir
    result = _get_command_templates_dir()
    assert result is not None
    assert result.is_absolute()
```

Run `pytest tests/specify_cli/runtime/test_agent_commands.py::test_resolver_returns_path_not_none -v` — it must be **RED** before you proceed. Commit this test alone as the first commit of this lane. The reviewer will verify the test was red on `planning_base_branch` and green on the final commit.

---

## Objective

Fix `src/specify_cli/runtime/agent_commands.py` to repair the three broken behaviours that cause 8 of 15 slash commands to never be installed (GitHub #1608):

1. **Resolver** (`_get_command_templates_dir`): returns `None` — must return a real `Path`
2. **Renderer** (`_sync_agent_commands`): flat `.glob("*.md")` finds nothing — must iterate per-step subdirs
3. **Lock** (`ensure_global_agent_commands`): written before sync — must write after all syncs succeed

```bash
spec-kitty agent action implement WP01 --agent claude
```

---

## Context

Templates moved from `src/specify_cli/missions/software-dev/command-templates/` to `src/doctrine/missions/mission-steps/software-dev/{step}/prompt.md`. The resolver still searches the old flat path. The exact fix pattern already exists in the codebase at `src/specify_cli/skills/command_installer.py:_package_templates_dir()`.

---

## Subtask T001 — Replace `_get_command_templates_dir()` body

Find `_get_command_templates_dir()` in `src/specify_cli/runtime/agent_commands.py`. Replace the entire body:

```python
def _get_command_templates_dir() -> Path:
    """Return the mission-steps dir for software-dev commands (doctrine package).

    Uses ``doctrine.__file__`` — works identically in editable and wheel installs.
    Raises ``FileNotFoundError`` if doctrine is absent (corrupted install).
    """
    import doctrine  # noqa: PLC0415
    return Path(doctrine.__file__).parent / "missions" / "mission-steps" / DEFAULT_MISSION_KEY
```

Return type changes from `Path | None` to `Path`. `DEFAULT_MISSION_KEY` is already imported from `specify_cli.core.config` and equals `"software-dev"`.

---

## Subtask T002 — Remove stale imports and None guards

1. Remove the `None` early-return guard in `ensure_global_agent_commands()`:
   ```python
   # DELETE these lines:
   if templates_dir is None:
       logger.debug("Command templates not found; skipping global command installation")
       return
   ```
2. Check if `get_package_asset_root` and `get_kittify_home` are still used elsewhere in `agent_commands.py`. Remove their imports if not.
3. Update any local variable annotations referencing `Path | None`.

Validation: `grep -n "templates_dir is None\|templates_dir is not None" src/specify_cli/runtime/agent_commands.py` → no matches.

---

## Subtask T003 — Update caller type annotations

In `ensure_global_agent_commands()`, the local variable `templates_dir` now has type `Path`. Update any annotation if present. Confirm the call to `_sync_agent_commands(agent_key, templates_dir, script_type)` passes without None-check wrappers.

---

## Subtask T005 — Replace flat glob with per-step iteration

In `_sync_agent_commands()`, find the prompt-driven loop:

```python
# OLD:
for template_path in sorted(templates_dir.glob("*.md")):
    command = template_path.stem
    if command not in PROMPT_DRIVEN_COMMANDS:
        continue
```

Replace with:

```python
# NEW:
for step_dir in sorted(templates_dir.iterdir()):
    if not step_dir.is_dir():
        continue
    command = step_dir.name
    if command not in PROMPT_DRIVEN_COMMANDS:
        continue
    template_path = step_dir / "prompt.md"
```

The remainder of the loop body (render_command_template, write, chmod) is unchanged.

---

## Subtask T006 — Add missing prompt.md guard

Immediately after `template_path = step_dir / "prompt.md"` (from T005):

```python
    if not template_path.exists():
        logger.warning("Step %r has no prompt.md; skipping %r", str(step_dir), command)
        continue
```

---

## Subtask T007 — Move version lock write to post-sync

Find where `agent-commands.lock` is written in `ensure_global_agent_commands()`. Ensure it is written **only after** all `_sync_agent_commands()` calls complete successfully:

```python
try:
    for agent_key in keys_to_process:
        _sync_agent_commands(agent_key, templates_dir, script_type)
    _write_version_lock(cache_dir / _VERSION_FILENAME, current_version)
except Exception:
    logger.warning("Command sync failed; lock not updated", exc_info=True)
    raise
```

If the lock write is already after the loop, confirm and leave it. If it's before or inside the loop, move it.

---

## Definition of Done

- [ ] ATDD stub committed and confirmed RED on `planning_base_branch` before first implementation commit
- [ ] GitHub issues #1608, #1609, #1610 assigned to HiC
- [ ] `_get_command_templates_dir()` returns `Path` (not `Path | None`)
- [ ] `None` guard removed from `ensure_global_agent_commands()`
- [ ] `_sync_agent_commands()` iterates `step_dir/prompt.md` (not flat glob)
- [ ] Missing `prompt.md` skipped with warning, not exception
- [ ] Version lock written only after all syncs succeed (full agent loop wrapped in try/except)
- [ ] ATDD stub test now GREEN
- [ ] `mypy --strict src/specify_cli/runtime/agent_commands.py` — zero errors
- [ ] `ruff check src/specify_cli/runtime/agent_commands.py` — zero violations
- [ ] Timing gate: `time uv run spec-kitty doctor skills` < 2 seconds on warm filesystem (fast-path sanity)

## Risks

- Do not touch `_sync_agent_commands()`'s stale-file removal loop — it must still run after all writes.
- WP02 will extend `ensure_global_agent_commands()` with `agent_keys` param; leave that for WP02.
