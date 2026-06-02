---
work_package_id: WP04
title: Doctor --fix Repair Path — wire slash-command reinstall
dependencies:
- WP02
- WP03
requirement_refs:
- C-002
- FR-006
- FR-010
- FR-011
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Depends on WP02 and WP03. Run: spec-kitty agent action implement WP04 --agent claude'
subtasks:
- T014
- T015
- T016
- T017
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/runtime/agent_commands.py
- tests/specify_cli/cli/commands/test_doctor_slash_fix.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Wait for confirmation before proceeding.

---

## Objective

Wire `doctor skills --fix` to repair slash-command gaps by calling `ensure_global_agent_commands()`, scoped to configured agents only. This completes the repair path for GitHub issue #1609 and contributes to #1610.

**Prerequisites**: WP02 and WP03 must be merged.

```bash
spec-kitty agent action implement WP04 --agent claude
```

---

## Context

After WP03, `doctor skills` detects slash-command gaps but cannot fix them. This WP adds the repair path. The key design constraints:

- **Scope guard**: only agents in `config.available` (FR-011, C-002)
- **Idempotency**: running `--fix` when everything is healthy is a silent no-op (FR-010)
- **Dependency**: repair calls `ensure_global_agent_commands()` which was fixed in WP01/WP02

---

## Subtask T014 — Add `_repair_slash_command_state()`

First, extend `ensure_global_agent_commands()` in `src/specify_cli/runtime/agent_commands.py` to accept an optional `agent_keys` parameter:

```python
def ensure_global_agent_commands(
    *,
    agent_keys: list[str] | None = None,
) -> None:
    """Install all canonical slash commands for configured agents.

    Parameters
    ----------
    agent_keys:
        When provided, only these agents are processed.  Defaults to all
        configured agents from ``AGENT_COMMAND_CONFIG``.
    """
    from specify_cli.core.config import AGENT_COMMAND_CONFIG
    # ... existing logic ...
    keys_to_process = agent_keys if agent_keys is not None else list(AGENT_COMMAND_CONFIG.keys())
    # use keys_to_process instead of hard-coded AGENT_COMMAND_CONFIG iteration
```

Then add `_repair_slash_command_state()` to `src/specify_cli/cli/commands/doctor.py`:

```python
def _repair_slash_command_state(
    project_path: Path,
    configured_agents: list[str],
    gaps: list[SlashCommandGap],
) -> list[str]:
    """Reinstall missing slash-command files for configured agents.

    Returns list of repaired file paths (empty list = no-op).
    Scope guard: only agents in ``configured_agents`` are touched.
    """
    if not gaps:
        return []

    from specify_cli.runtime.agent_commands import ensure_global_agent_commands

    try:
        ensure_global_agent_commands(agent_keys=configured_agents)
    except Exception as exc:
        logger.warning("Slash command repair failed: %s", exc, exc_info=True)
        raise

    return [str(gap.expected_path) for gap in gaps if gap.status in ("missing", "stale")]
```

---

## Subtask T015 — Wire `--fix` in `doctor skills`

In the slash-command section of `doctor skills` (added in WP03), extend the `if fix:` branch:

```python
if fix and slash_gaps:
    repaired = _repair_slash_command_state(project_path, configured_slash, slash_gaps)
    if repaired:
        console.print(f"\n[green]Repaired:[/green] {len(repaired)} slash command file(s)")
        for path in repaired[:5]:
            console.print(f"  {path}")
        if len(repaired) > 5:
            console.print(f"  ... and {len(repaired) - 5} more")
    # Re-check health after repair
    _, remaining_gaps = _load_slash_command_state(project_path)
    slash_healthy = len(remaining_gaps) == 0
    if slash_healthy:
        console.print("[green]Slash Commands:[/green] all gaps repaired\n")
    else:
        console.print(
            f"[yellow]Warning:[/yellow] {len(remaining_gaps)} gap(s) remain after repair\n"
        )
```

The fix must not run when `slash_gaps` is empty (idempotency: no unnecessary writes).

---

## Subtask T016 — Verify idempotency

Idempotency is guaranteed by two mechanisms:

1. `ensure_global_agent_commands()` only writes files when content differs from what would be written (check the existing write logic — it may already be idempotent; if not, add a content-equality check before writing).
2. `_repair_slash_command_state()` only calls the installer when `gaps` is non-empty.

Write a manual verification scenario (also covered in T017 tests):
- Run `doctor skills --fix` with all files present → confirm output shows "all configured agents healthy", no repair log, no file writes.
- Check that file timestamps are unchanged (no unnecessary writes).

---

## Subtask T017 — Integration test: gap → fix → clean

**File**: `tests/specify_cli/cli/commands/test_doctor_slash_fix.py`

```python
def test_doctor_fix_repairs_missing_command(tmp_path, monkeypatch):
    """doctor skills --fix reinstalls a missing command file."""
    # Setup: mock config with claude configured
    # Setup: create global command dir with one file missing (spec-kitty.specify.md)
    # Invoke: doctor skills --fix (via CLI runner or direct call)
    # Assert: spec-kitty.specify.md is now present in the command dir
    # Assert: exit code 0

def test_doctor_fix_is_noop_when_healthy(tmp_path, monkeypatch):
    """doctor skills --fix makes no changes when all files present."""
    # Setup: create all 15 command files with correct version markers
    # Record file mtimes before
    # Invoke: doctor skills --fix
    # Assert: all mtimes unchanged (no unnecessary writes)
    # Assert: exit code 0, output says healthy

def test_doctor_fix_scope_guard(tmp_path, monkeypatch):
    """doctor skills --fix only touches configured agents."""
    # Config: only claude in config.available
    # Setup: gemini command dir exists but gemini not in config
    # Invoke: doctor skills --fix
    # Assert: gemini command dir untouched
```

---

## Definition of Done

- [ ] `ensure_global_agent_commands()` accepts optional `agent_keys` parameter
- [ ] `_repair_slash_command_state()` calls installer scoped to configured agents only
- [ ] `doctor skills --fix` repairs missing/stale slash-command files
- [ ] Repair path is silent no-op when no gaps exist
- [ ] Scope guard verified: unconfigured agent dirs never touched
- [ ] Integration tests pass
- [ ] `mypy --strict` on changed files — zero errors
- [ ] `ruff check` — zero violations

## Risks

- The existing `ensure_global_agent_commands()` may hold an exclusive file lock. Confirm the lock behaviour doesn't block concurrent doctor runs.
- Adding `agent_keys` to `ensure_global_agent_commands()` must remain backward-compatible (existing callers pass no `agent_keys`). Use `| None = None` default, not a required parameter.
- Do not extend `--fix` to touch Agent Skills pipeline files — that pathway is handled separately.
