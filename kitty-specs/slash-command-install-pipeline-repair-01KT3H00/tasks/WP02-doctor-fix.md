---
work_package_id: WP02
title: Fix doctor skills — slash-command audit and --fix repair
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-010
- FR-011
- C-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T014
- T015
- T016
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/doctor.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## ⚑ ATDD-First commit (charter C-011 — mandatory)

Before writing any implementation code, commit a minimal failing test to `tests/specify_cli/cli/commands/test_doctor_slash_commands.py` (create the file if absent):

```python
def test_doctor_skills_output_includes_slash_commands_section():
    """Fails until FR-005/FR-007 is implemented: doctor currently has no Slash Commands section."""
    from click.testing import CliRunner
    from specify_cli.cli.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "skills"])
    assert "Slash Commands" in result.output  # fails until WP02 adds the audit section
```

Run this test — it must be **RED** before you proceed. Commit it alone as the first commit of this lane. The reviewer will verify red → green.

---

## Objective

Extend `src/specify_cli/cli/commands/doctor.py` to detect and repair slash-command gaps for configured agents (GitHub #1609). Also extend `src/specify_cli/runtime/agent_commands.py` with an `agent_keys` parameter so `--fix` can scope its repair (T014 — this is a downstream extension to a file owned by WP01; WP01 remains the authoritative owner of `agent_commands.py`).

**Prerequisite**: WP01 merged.

```bash
spec-kitty agent action implement WP02 --agent claude
```

---

## Subtask T009 — Add `_get_slash_command_agents()` to doctor.py

Add near `_load_command_skill_state()`:

```python
def _get_slash_command_agents(project_path: Path) -> list[str]:
    """Configured slash-command agents (excludes Agent-Skills agents)."""
    from specify_cli.core.config import AGENT_COMMAND_CONFIG
    from specify_cli.skills.command_installer import SUPPORTED_AGENTS
    try:
        config = load_agent_config(project_path)
        available = set(config.available)
    except Exception:
        available = set(AGENT_COMMAND_CONFIG.keys())
    slash_agents = set(AGENT_COMMAND_CONFIG.keys()) - set(SUPPORTED_AGENTS)
    return sorted(available & slash_agents)
```

---

## Subtask T010 — Add `SlashCommandGap` dataclass and `_load_slash_command_state()`

```python
@dataclass
class SlashCommandGap:
    agent_key: str
    command: str
    expected_path: Path
    status: str  # "missing" | "stale"

def _load_slash_command_state(project_path: Path) -> tuple[list[str], list[SlashCommandGap]]:
    """Return (configured_agents, gaps) for slash-command pipeline."""
    from specify_cli.core.config import AGENT_COMMAND_CONFIG
    from specify_cli.runtime.agent_commands import (
        get_global_command_dir, _compute_output_filename,
        _VERSION_MARKER_PREFIX, _VERSION_MARKER_HEAD_LINES,
    )
    from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS, CLI_DRIVEN_COMMANDS
    from specify_cli.runtime.bootstrap import _get_cli_version

    current_version = _get_cli_version()
    configured = _get_slash_command_agents(project_path)
    gaps: list[SlashCommandGap] = []
    for agent_key in configured:
        cfg = AGENT_COMMAND_CONFIG.get(agent_key)
        if cfg is None:
            continue
        cmd_dir = get_global_command_dir(agent_key)
        for command in sorted(PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS):
            filename = _compute_output_filename(command, agent_key)
            path = cmd_dir / filename
            if not path.exists():
                gaps.append(SlashCommandGap(agent_key, command, path, "missing"))
            else:
                try:
                    head = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                                     .splitlines()[:_VERSION_MARKER_HEAD_LINES])
                    if f"{_VERSION_MARKER_PREFIX} {current_version}" not in head:
                        gaps.append(SlashCommandGap(agent_key, command, path, "stale"))
                except OSError:
                    gaps.append(SlashCommandGap(agent_key, command, path, "missing"))
    return configured, gaps
```

If `_compute_output_filename` is not exported, inline as `f"spec-kitty.{command}.{cfg['ext']}"`.

---

## Subtask T011 — Extend `doctor skills` output with Slash Commands section

After the existing Agent Skills output block, add:

```python
configured_slash, slash_gaps = _load_slash_command_state(project_path)
if configured_slash:
    if not slash_gaps:
        console.print(f"[green]Slash Commands[/green]: all configured agents healthy ({len(configured_slash)} agent(s))\n")
    else:
        console.print("\n[bold]Slash Commands[/bold] — gap(s) found\n")
        for agent_key in configured_slash:
            agent_gaps = [g for g in slash_gaps if g.agent_key == agent_key]
            status = "✓" if not agent_gaps else "✗"
            color = "green" if not agent_gaps else "red"
            console.print(f"  [{color}]{status}[/{color}] {agent_key}: {len(agent_gaps)} gap(s)" if agent_gaps else f"  [{color}]{status}[/{color}] {agent_key}: all commands present")
            for gap in agent_gaps[:5]:
                console.print(f"      {gap.status}: {gap.expected_path.name}")
            if len(agent_gaps) > 5:
                console.print(f"      ... and {len(agent_gaps) - 5} more")
        if not fix:
            console.print("\nRun [cyan]spec-kitty doctor skills --fix[/cyan] to reinstall missing slash commands.")
```

---

## Subtask T012 — Return unhealthy aggregate when slash gaps exist

Find the `healthy` boolean used for overall exit code. Add:

```python
slash_healthy = not slash_gaps
overall_healthy = agent_skills_healthy and slash_healthy
```

Ensure exit code reflects `overall_healthy`, not just Agent Skills health.

---

## Subtask T014 — Extend `ensure_global_agent_commands()` with `agent_keys` param

In `src/specify_cli/runtime/agent_commands.py`, add optional `agent_keys` parameter:

```python
def ensure_global_agent_commands(
    *,
    agent_keys: list[str] | None = None,
) -> None:
    ...
    from specify_cli.core.config import AGENT_COMMAND_CONFIG
    keys_to_process = agent_keys if agent_keys is not None else list(AGENT_COMMAND_CONFIG.keys())
    # use keys_to_process in the agent iteration loop
```

Backward-compatible: existing callers pass no `agent_keys` and get all agents.

---

## Subtask T015 — Add `_repair_slash_command_state()` and wire `--fix`

In `doctor.py`:

```python
def _repair_slash_command_state(
    project_path: Path,
    configured_agents: list[str],
    gaps: list[SlashCommandGap],
) -> list[str]:
    """Reinstall missing slash-command files. Returns list of repaired paths."""
    if not gaps:
        return []
    from specify_cli.runtime.agent_commands import ensure_global_agent_commands
    ensure_global_agent_commands(agent_keys=configured_agents)
    return [str(g.expected_path) for g in gaps]
```

In the `skills` `--fix` path, after detecting slash gaps:

```python
if fix and slash_gaps:
    repaired = _repair_slash_command_state(project_path, configured_slash, slash_gaps)
    console.print(f"\n[green]Repaired:[/green] {len(repaired)} slash command file(s)")
    _, remaining = _load_slash_command_state(project_path)
    slash_healthy = not remaining
```

---

## Subtask T016 — Implement early-return guard

`_repair_slash_command_state()` must return `[]` immediately when `gaps` is empty, without calling `ensure_global_agent_commands`. The installer itself also writes files only when content differs. This is a behavioral constraint (not a test); idempotency is verified by T027 in WP05.

---

## Definition of Done

- [ ] ATDD stub committed and confirmed RED on `planning_base_branch` before first implementation commit
- [ ] `_get_slash_command_agents()` returns configured slash-command agents only
- [ ] `_load_slash_command_state()` detects missing and stale files
- [ ] `doctor skills` output includes Slash Commands section
- [ ] `doctor skills` exits non-zero when slash-command files are missing
- [ ] `ensure_global_agent_commands()` accepts `agent_keys` (backward-compatible; WP01 owns the file)
- [ ] `_repair_slash_command_state()` returns `[]` immediately when `gaps` is empty (T016)
- [ ] `doctor skills --fix` repairs gaps scoped to configured agents only
- [ ] ATDD stub test now GREEN
- [ ] `mypy --strict` on changed functions — zero errors
- [ ] `ruff check` — zero violations
- [ ] Timing gate: `time uv run spec-kitty doctor skills` < 3 seconds (NFR-002)

## Risks

- `doctor.py` is large. Read the file structure before inserting to find the correct location.
- The `project_path` for `_get_slash_command_agents` must match how other checks obtain it.
- Do not change the Agent Skills audit path.
