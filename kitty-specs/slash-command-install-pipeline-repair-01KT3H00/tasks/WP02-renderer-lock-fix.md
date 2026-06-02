---
work_package_id: WP02
title: Renderer + Lock Fix — per-step iteration and post-install lock write
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-012
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Depends on WP01. Run: spec-kitty agent action implement WP02 --agent claude'
subtasks:
- T005
- T006
- T007
- T008
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/runtime/
execution_mode: code_change
owned_files:
- src/specify_cli/runtime/agent_commands.py
- tests/specify_cli/runtime/test_agent_commands_renderer.py
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

Fix the template iteration pattern in `_sync_agent_commands()` and the version lock write position in `ensure_global_agent_commands()`. This WP resolves the remaining parts of GitHub issue #1608 after WP01 has fixed the resolver.

**Prerequisite**: WP01 must be merged before starting. Run:
```bash
spec-kitty agent action implement WP02 --agent claude
```

---

## Context

After WP01, `_get_command_templates_dir()` returns the `software-dev` mission-steps root (e.g., `doctrine/missions/mission-steps/software-dev/`). That directory contains one subdirectory per step:

```
software-dev/
  specify/prompt.md
  plan/prompt.md
  tasks/prompt.md
  ...
```

But `_sync_agent_commands()` currently does:
```python
for template_path in sorted(templates_dir.glob("*.md")):
    command = template_path.stem
```

This flat glob finds nothing because there are no `.md` files directly in `software-dev/` — they are one level deeper in `{step}/prompt.md`.

The version lock bug: `agent-commands.lock` is written before or inside the sync loop, so a partial failure or `templates_dir=None` early return leaves the lock stale. After WP01 removes the early return, lock position still needs fixing.

---

## Subtask T005 — Replace flat glob with per-step iteration

**File**: `src/specify_cli/runtime/agent_commands.py`  
**Function**: `_sync_agent_commands(agent_key, templates_dir, script_type)`

Find the prompt-driven commands loop (approximately):

```python
# --- Prompt-driven commands ---
for template_path in sorted(templates_dir.glob("*.md")):
    command = template_path.stem
    if command not in PROMPT_DRIVEN_COMMANDS:
        continue
    ...
```

Replace with:

```python
# --- Prompt-driven commands ---
for step_dir in sorted(templates_dir.iterdir()):
    if not step_dir.is_dir():
        continue
    command = step_dir.name
    if command not in PROMPT_DRIVEN_COMMANDS:
        continue
    template_path = step_dir / "prompt.md"
    ...
```

The rest of the loop body (calling `render_command_template`, writing output file, setting read-only mode) stays exactly as-is. Only the iteration and `template_path` derivation change.

---

## Subtask T006 — Add guards for missing prompt.md

Still within the rewritten loop from T005, add a guard after `template_path = step_dir / "prompt.md"`:

```python
    if not template_path.exists():
        logger.warning(
            "Step directory %r has no prompt.md; skipping command %r",
            str(step_dir),
            command,
        )
        continue
```

This is a graceful skip — if a step directory exists but has no `prompt.md` (e.g., a partial or in-progress template), we skip it without failing the entire install. The warning surfaces it for debugging.

Also add a guard for non-step directories that are not in `PROMPT_DRIVEN_COMMANDS` (already handled by the `if command not in PROMPT_DRIVEN_COMMANDS: continue` check) — confirm this guard is in place.

---

## Subtask T007 — Move version lock write to post-install

**Function**: `ensure_global_agent_commands()`

Find where the version lock (`agent-commands.lock`) is written. It should currently be written either:
- Inside the fast-path branch (version match, healthy check passes) — leave this alone
- Or inside the slow-path after acquiring the exclusive lock but before the sync loop

The fix: ensure the lock is written **only after** `_sync_agent_commands()` completes for all configured agents without raising an exception.

**Pattern to enforce**:
```python
# In the slow-path block:
try:
    for agent_key in configured_agent_keys:
        _sync_agent_commands(agent_key, templates_dir, script_type)
    # Only write the lock after ALL agents succeed
    _write_version_lock(cache_dir / _VERSION_FILENAME, current_version)
except Exception:
    logger.warning("Command sync failed; version lock not updated", exc_info=True)
    raise
```

If the lock write is already in this position, confirm it and leave it. If it's before the loop or inside the loop per-agent, move it to after.

**Validation**: After this change, the version lock at `~/.kittify/cache/agent-commands.lock` should advance from stale `3.2.0rc30` to `3.2.0rc33` on the next CLI startup.

---

## Subtask T008 — Integration test: all commands written correctly

**File to create**: `tests/specify_cli/runtime/test_agent_commands_renderer.py`

Write an integration test that exercises the full install path with a mocked doctrine package:

```python
def test_sync_agent_commands_writes_all_15_commands(monkeypatch, tmp_path):
    """After the fix, _sync_agent_commands writes 8 prompt-driven + 7 CLI-driven files."""
    from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS, CLI_DRIVEN_COMMANDS
    from specify_cli.runtime.agent_commands import _sync_agent_commands, _compute_output_filename

    # Set up fake doctrine steps directory
    steps_dir = tmp_path / "doctrine" / "missions" / "mission-steps" / "software-dev"
    for cmd in PROMPT_DRIVEN_COMMANDS:
        step = steps_dir / cmd
        step.mkdir(parents=True, exist_ok=True)
        (step / "prompt.md").write_text(f"---\ndescription: {cmd}\n---\nBody for {cmd}")

    # ... monkeypatch doctrine, AGENT_COMMAND_CONFIG for claude, etc.

    output_dir = tmp_path / "claude_commands"
    output_dir.mkdir()

    _sync_agent_commands("claude", steps_dir, "bash")

    written = {p.stem for p in output_dir.iterdir()}
    expected_prompt = {f"spec-kitty.{c}" for c in PROMPT_DRIVEN_COMMANDS}
    expected_cli = {f"spec-kitty.{c}" for c in CLI_DRIVEN_COMMANDS}
    assert expected_prompt.issubset(written), f"Missing prompt-driven: {expected_prompt - written}"
    assert expected_cli.issubset(written), f"Missing CLI-driven: {expected_cli - written}"
```

Also write a test that confirms stale files are removed when a command is no longer in the canonical set.

**Validation**:
- `pytest tests/specify_cli/runtime/test_agent_commands_renderer.py -v` passes.

---

## Definition of Done

- [ ] `_sync_agent_commands()` iterates `step_dir/prompt.md` (not flat glob)
- [ ] Missing `prompt.md` skipped with warning log, not exception
- [ ] Version lock written only after all agents sync successfully
- [ ] All 8 prompt-driven + 7 CLI-driven commands would be written for a configured claude agent
- [ ] Integration tests pass
- [ ] `mypy --strict src/specify_cli/runtime/agent_commands.py` — zero errors
- [ ] `ruff check src/specify_cli/runtime/agent_commands.py` — zero violations

## Risks

- Do not modify the `render_command_template()` call signature — it is tested independently.
- The stale-file removal loop (removes `spec-kitty.*` files no longer in canonical set) must still run after both prompt-driven and CLI-driven writes complete.
- Confirm the lock file path via `_VERSION_FILENAME` constant — do not hardcode.
