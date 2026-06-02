---
work_package_id: WP03
title: Doctor Slash-Command Audit — detect gaps for configured agents
dependencies:
- WP01
requirement_refs:
- C-002
- FR-005
- FR-007
- FR-011
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Depends on WP01. Can run in parallel with WP02. Run: spec-kitty agent action implement WP03 --agent claude'
subtasks:
- T009
- T010
- T011
- T012
- T013
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/doctor.py
- tests/specify_cli/cli/commands/test_doctor_slash_audit.py
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

Add a slash-command health check path to `doctor skills` in `src/specify_cli/cli/commands/doctor.py`. The new path checks whether each configured slash-command agent has all canonical commands present in its global directory. The check runs alongside (not replacing) the existing Agent Skills audit.

This resolves GitHub issue #1609 (read-only detection half). WP04 adds the `--fix` repair path.

**Prerequisite**: WP01 must be merged. Can run in parallel with WP02.

```bash
spec-kitty agent action implement WP03 --agent claude
```

---

## Context

### Current `doctor skills` structure

`doctor skills` currently:
1. Loads `SUPPORTED_AGENTS = ("codex","vibe","pi","letta")` from `command_installer`
2. Intersects with `config.available` → only codex/vibe/pi/letta considered
3. Calls `_load_command_skill_state()` for Agent Skills manifest check
4. Reports health for Agent Skills only

Claude and all 12 other slash-command agents (`AGENT_COMMAND_CONFIG` keys) are invisible to this check.

### What the fix adds

A parallel check path, independent of the Agent Skills path:
1. Load configured slash-command agents: `set(config.available) ∩ set(AGENT_COMMAND_CONFIG.keys())`
2. For each agent, check all 15 canonical command files exist in the agent's global dir
3. Report gaps in `doctor skills` output
4. Return unhealthy aggregate if any gap exists

---

## Subtask T009 — Add `_get_slash_command_agents()` helper

Add this function to `src/specify_cli/cli/commands/doctor.py` near the existing `_load_command_skill_state()` function:

```python
def _get_slash_command_agents(project_path: Path) -> list[str]:
    """Return agent keys that use the slash-command pipeline and are configured.

    Scope: intersection of config.yaml ``available`` list and
    :data:`specify_cli.core.config.AGENT_COMMAND_CONFIG` keys.
    Excludes Agent-Skills agents (codex, vibe, pi, letta) which are handled
    by the existing manifest audit path.
    """
    from specify_cli.core.config import AGENT_COMMAND_CONFIG
    from specify_cli.skills.command_installer import SUPPORTED_AGENTS

    try:
        config = load_agent_config(project_path)
        available = set(config.available)
    except Exception:
        available = set(AGENT_COMMAND_CONFIG.keys())  # legacy fallback: all

    slash_agents = set(AGENT_COMMAND_CONFIG.keys()) - set(SUPPORTED_AGENTS)
    return sorted(available & slash_agents)
```

Confirm `load_agent_config` is already imported in `doctor.py` — it is used by `_load_command_skill_state`. If not, add the import.

---

## Subtask T010 — Add `_load_slash_command_state()` gap checker

```python
@dataclass
class SlashCommandGap:
    agent_key: str
    command: str
    expected_path: Path
    status: str  # "missing" | "stale"


def _load_slash_command_state(
    project_path: Path,
) -> tuple[list[str], list[SlashCommandGap]]:
    """Return (configured_agents, gaps) for the slash-command pipeline.

    ``configured_agents`` are the slash-command agents in config.yaml.
    ``gaps`` are (agent_key, command, path, status) for any file that is
    absent or carries a stale version marker.
    """
    from specify_cli.core.config import AGENT_COMMAND_CONFIG
    from specify_cli.runtime.agent_commands import (
        get_global_command_dir,
        _compute_output_filename,
        _VERSION_MARKER_PREFIX,
        _VERSION_MARKER_HEAD_LINES,
    )
    from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS, CLI_DRIVEN_COMMANDS
    from specify_cli.runtime.bootstrap import _get_cli_version

    current_version = _get_cli_version()
    configured = _get_slash_command_agents(project_path)
    gaps: list[SlashCommandGap] = []

    for agent_key in configured:
        config = AGENT_COMMAND_CONFIG.get(agent_key)
        if config is None:
            continue
        cmd_dir = get_global_command_dir(agent_key)
        for command in sorted(PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS):
            filename = _compute_output_filename(command, agent_key)
            path = cmd_dir / filename
            if not path.exists():
                gaps.append(SlashCommandGap(agent_key, command, path, "missing"))
            else:
                # Check version marker in first N lines
                try:
                    head = path.read_text(encoding="utf-8", errors="replace")
                    head_lines = "\n".join(head.splitlines()[:_VERSION_MARKER_HEAD_LINES])
                    marker = f"{_VERSION_MARKER_PREFIX} {current_version}"
                    if marker not in head_lines:
                        gaps.append(SlashCommandGap(agent_key, command, path, "stale"))
                except OSError:
                    gaps.append(SlashCommandGap(agent_key, command, path, "missing"))

    return configured, gaps
```

If `_compute_output_filename` is not exported from `agent_commands`, check for it or inline the filename derivation (`f"spec-kitty.{command}.{config['ext']}"`).

---

## Subtask T011 — Extend `doctor skills` output with Slash Commands section

Find the `skills` subcommand function (around line 389 in `doctor.py`). After the existing Agent Skills output block, add the slash-command section:

```python
# --- Slash Commands ---
configured_slash, slash_gaps = _load_slash_command_state(project_path)
if configured_slash:
    if not slash_gaps:
        console.print(
            "[green]Slash Commands[/green]: all configured agents healthy "
            f"({len(configured_slash)} agent(s))\n"
        )
    else:
        console.print("\n[bold]Slash Commands[/bold] — gap(s) found\n")
        for agent_key in configured_slash:
            agent_gaps = [g for g in slash_gaps if g.agent_key == agent_key]
            if not agent_gaps:
                console.print(f"  [green]✓[/green] {agent_key}: all commands present")
            else:
                console.print(f"  [red]✗[/red] {agent_key}: {len(agent_gaps)} gap(s)")
                for gap in agent_gaps[:5]:  # cap display at 5
                    console.print(f"      {gap.status}: {gap.expected_path.name}")
                if len(agent_gaps) > 5:
                    console.print(f"      ... and {len(agent_gaps) - 5} more")
        if not fix:
            console.print(
                "\nRun [cyan]spec-kitty doctor skills --fix[/cyan] to reinstall missing slash commands."
            )
```

---

## Subtask T012 — Return unhealthy aggregate when slash gaps exist

The `skills` subcommand must exit non-zero or set an unhealthy flag when slash gaps are present — even if Agent Skills is healthy.

Find where the overall health result is computed (likely a `healthy` boolean). Add:

```python
slash_healthy = len(slash_gaps) == 0
overall_healthy = agent_skills_healthy and slash_healthy
```

Ensure the final output and exit code reflect `overall_healthy`, not just Agent Skills health.

**Validation**: 
```bash
# Delete a command, run doctor, expect unhealthy output:
rm ~/.claude/commands/spec-kitty.specify.md
spec-kitty doctor skills
# Should exit non-zero and report the gap
```

---

## Subtask T013 — Unit tests for audit logic

**File**: `tests/specify_cli/cli/commands/test_doctor_slash_audit.py`

Key test cases:

```python
def test_get_slash_command_agents_excludes_agent_skills_agents(tmp_path):
    """codex/vibe/pi/letta excluded; claude included when configured."""
    # Write config.yaml with available: [claude, codex]
    # Assert _get_slash_command_agents returns ["claude"] only

def test_load_slash_command_state_reports_missing_file(tmp_path, monkeypatch):
    """Missing command file reported as 'missing' gap."""
    # Mock get_global_command_dir to point at tmp_path
    # Don't create spec-kitty.specify.md
    # Assert gap with status="missing" for specify command

def test_doctor_skills_reports_unhealthy_on_missing_slash_command(tmp_path, monkeypatch):
    """doctor skills exits non-zero when slash commands missing."""
    # ... invoke the skills subcommand, assert exit_code != 0

def test_doctor_skills_reports_healthy_when_all_present(tmp_path, monkeypatch):
    """doctor skills reports healthy when all slash commands present."""
    # Create all 15 command files with correct version marker
    # Assert exit_code == 0
```

---

## Definition of Done

- [ ] `_get_slash_command_agents()` returns configured slash-command agents only (not codex/vibe/pi/letta)
- [ ] `_load_slash_command_state()` detects missing and stale files
- [ ] `doctor skills` output includes Slash Commands section for configured agents
- [ ] `doctor skills` exits non-zero when any slash-command file is missing
- [ ] `doctor skills` still reports healthy for Agent Skills pipeline (existing behaviour unchanged)
- [ ] Unit tests pass
- [ ] `mypy --strict src/specify_cli/cli/commands/doctor.py` — zero errors on changed functions
- [ ] `ruff check src/specify_cli/cli/commands/doctor.py` — zero violations

## Risks

- `doctor.py` is large (~2700 lines). Read the whole file structure before editing to avoid duplicating existing logic or missing the right insertion point.
- The `project_path` available to the `skills` subcommand may be the repo root or the CWD — confirm how other checks obtain it (look at `_load_command_skill_state`'s signature).
- Do not change the Agent Skills audit path — only add the new slash-command path alongside it.
