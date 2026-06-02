---
work_package_id: WP01
title: Resolver Fix — _get_command_templates_dir() doctrine-based path
dependencies: []
requirement_refs:
- FR-001
- FR-012
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Worktrees allocated per lane from lanes.json. WP01 has no dependencies so it can start immediately on lane-a.
subtasks:
- T001
- T002
- T003
- T004
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/runtime/
execution_mode: code_change
owned_files:
- src/specify_cli/runtime/agent_commands.py
- tests/specify_cli/runtime/test_agent_commands_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Wait for confirmation before proceeding.

---

## Objective

Fix `_get_command_templates_dir()` in `src/specify_cli/runtime/agent_commands.py` so it returns the correct `Path` to the doctrine layer's template directory. This is the root cause of GitHub issue #1608 — the function currently returns `None` because it checks two stale paths that no longer exist, causing `ensure_global_agent_commands()` to silently skip installing 8 prompt-driven commands.

**Branch strategy**: Planning base branch is `main`. Your execution workspace is allocated by `spec-kitty agent action implement WP01 --agent claude`. Work in the worktree provided; do not touch `main` directly.

---

## Context

### What is broken

`_get_command_templates_dir()` in `src/specify_cli/runtime/agent_commands.py` checks:
1. `{pkg_asset_root}/software-dev/command-templates/` — deleted when templates moved to doctrine
2. `~/.kittify/missions/software-dev/command-templates/` — also absent

Both return `None`. `ensure_global_agent_commands()` has an early return when `templates_dir is None`, so all 8 prompt-driven commands are never written. The version lock then never advances from its stale version.

### The correct pattern (already in the codebase)

`src/specify_cli/skills/command_installer.py` already solves this correctly:

```python
def _package_templates_dir(mission_type: str = "software-dev") -> Path:
    import doctrine  # noqa: PLC0415
    return (
        Path(doctrine.__file__).parent
        / "missions"
        / "mission-steps"
        / mission_type
    )
```

This works identically in editable dev installs and wheel installs. Use it as the exact pattern.

### Doctrine layout (confirmed on disk)

```
src/doctrine/missions/mission-steps/software-dev/
  analyze/prompt.md
  charter/prompt.md
  implement/prompt.md
  plan/prompt.md
  research/prompt.md
  review/prompt.md
  specify/prompt.md
  tasks/prompt.md
  tasks-finalize/prompt.md
  tasks-outline/prompt.md
  tasks-packages/prompt.md
```

The `software-dev/` directory is the root that `_get_command_templates_dir()` should return.

---

## Subtask T001 — Replace resolver body

**File**: `src/specify_cli/runtime/agent_commands.py`

**Current code** (find and replace the full `_get_command_templates_dir` function):

```python
def _get_command_templates_dir() -> Path | None:
    """Return the command-templates directory for the current CLI version.
    ...
    """
    try:
        pkg_root = get_package_asset_root()
        pkg_templates = pkg_root / DEFAULT_MISSION_KEY / "command-templates"
        if pkg_templates.is_dir():
            return Path(pkg_templates)
    except FileNotFoundError:
        pass

    runtime_templates = get_kittify_home() / "missions" / DEFAULT_MISSION_KEY / "command-templates"
    if runtime_templates.is_dir():
        return Path(runtime_templates)

    return None
```

**Replace with**:

```python
def _get_command_templates_dir() -> Path:
    """Return the mission-steps directory for software-dev commands.

    Templates ship as ``prompt.md`` files inside the ``doctrine`` package under
    ``missions/mission-steps/software-dev/<step>/prompt.md``.  Deriving the path
    from ``doctrine.__file__`` yields a real :class:`pathlib.Path` that works
    identically in editable and wheel installs.

    Raises :class:`FileNotFoundError` if the ``doctrine`` package cannot be
    located (should never occur in a supported install).
    """
    import doctrine  # noqa: PLC0415 — deferred to avoid import-time side effects

    return Path(doctrine.__file__).parent / "missions" / "mission-steps" / DEFAULT_MISSION_KEY
```

Note: `DEFAULT_MISSION_KEY` is already imported from `specify_cli.core.config`; confirm it equals `"software-dev"`. If not, use the string literal.

---

## Subtask T002 — Remove stale imports and fallback logic

After replacing the function body:

1. Check if `get_package_asset_root` is still used elsewhere in `agent_commands.py`. If not, remove the import.
2. Check if `get_kittify_home` is still used elsewhere. If not, remove the import.
3. Confirm `doctrine` is not already imported at module level (it should stay as a deferred import inside the function per the `# noqa: PLC0415` convention used throughout the codebase).

Do not touch any other functions in the file during this subtask.

---

## Subtask T003 — Update callers to remove `None` guards

The only direct caller of `_get_command_templates_dir()` is `ensure_global_agent_commands()`. Find the call site and remove the `None` guard:

**Current pattern** (approximately):
```python
templates_dir = _get_command_templates_dir()
if templates_dir is None:
    logger.debug("Command templates not found; skipping global command installation")
    return
```

**Replace with**:
```python
templates_dir = _get_command_templates_dir()
```

The `if templates_dir is None` branch is now unreachable. Remove it entirely (no silent skip, no `return`). If doctrine is absent, the `FileNotFoundError` from the resolver propagates — this is the correct failure mode for a corrupted install.

Also update any type annotations that reference `Path | None` for this value.

**Validation**:
- `grep -n "templates_dir is None\|templates_dir is not None" src/specify_cli/runtime/agent_commands.py` should return no matches after this change.

---

## Subtask T004 — Unit tests for resolver

**File to create**: `tests/specify_cli/runtime/test_agent_commands_resolver.py`

Write tests covering:

```python
def test_resolver_returns_path_under_doctrine(monkeypatch, tmp_path):
    """Resolver returns the doctrine missions/mission-steps/software-dev path."""
    # Create fake doctrine package structure
    doctrine_pkg = tmp_path / "doctrine" / "__init__.py"
    doctrine_pkg.parent.mkdir(parents=True)
    doctrine_pkg.write_text("")
    steps_dir = tmp_path / "doctrine" / "missions" / "mission-steps" / "software-dev"
    steps_dir.mkdir(parents=True)

    import types
    fake_doctrine = types.ModuleType("doctrine")
    fake_doctrine.__file__ = str(doctrine_pkg)
    monkeypatch.setitem(sys.modules, "doctrine", fake_doctrine)

    from specify_cli.runtime.agent_commands import _get_command_templates_dir
    result = _get_command_templates_dir()
    assert result == steps_dir
    assert result.is_dir()


def test_resolver_return_type_is_path_not_optional():
    """Return type annotation must be Path, not Path | None."""
    import inspect
    from specify_cli.runtime.agent_commands import _get_command_templates_dir
    hints = get_type_hints(_get_command_templates_dir)
    assert hints["return"] is Path, "Must return Path, not Optional[Path]"
```

Ensure tests are in a class or use module-level functions consistently with the project convention. Check `tests/specify_cli/runtime/` for existing test patterns.

**Validation**:
- `pytest tests/specify_cli/runtime/test_agent_commands_resolver.py -v` passes green.

---

## Definition of Done

- [ ] `_get_command_templates_dir()` return type is `Path` (not `Path | None`)
- [ ] Function body uses `doctrine.__file__`-based resolution
- [ ] `None` guard removed from `ensure_global_agent_commands()`
- [ ] Stale imports removed if unused
- [ ] `grep -rn "command-templates" src/specify_cli/runtime/agent_commands.py` returns no matches
- [ ] Unit tests pass: `pytest tests/specify_cli/runtime/test_agent_commands_resolver.py -v`
- [ ] `mypy --strict src/specify_cli/runtime/agent_commands.py` — zero errors
- [ ] `ruff check src/specify_cli/runtime/agent_commands.py` — zero violations

## Risks

- `DEFAULT_MISSION_KEY` must equal `"software-dev"`. Verify before using.
- Do not break `_sync_agent_commands()` — it receives `templates_dir` from the caller; WP02 will fix the iteration pattern separately.
- This WP must not touch `_sync_agent_commands()`. Leave it to WP02.
