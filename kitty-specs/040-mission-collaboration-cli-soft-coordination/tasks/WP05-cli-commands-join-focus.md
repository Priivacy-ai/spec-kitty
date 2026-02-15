---
work_package_id: WP05
title: CLI Commands - Join & Focus
lane: "done"
dependencies: [WP04]
base_branch: 040-mission-collaboration-cli-soft-coordination-WP04
base_commit: 02691ff86790e3b570ea00c36c4682c8dd9b6c0c
created_at: '2026-02-15T13:56:33.126459+00:00'
subtasks: [T021, T022, T027]
shell_pid: "65606"
agent: "codex"
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# WP05: CLI Commands - Join & Focus

**Purpose**: Implement mission join and focus set CLI commands with typer integration.

**Target Branch**: 2.x
**Estimated Effort**: ~300 lines

---

## Implementation Command

```bash
spec-kitty implement WP05 --base WP04
```

---

## Subtasks

### T021: Implement Mission Join Command (~120 lines)

Extend existing `src/specify_cli/cli/commands/mission.py`:

```python
import typer
from rich.console import Console
from specify_cli.collaboration.service import join_mission

console = Console()

def join_command(mission_id: str, role: str) -> None:
    """Join mission with specified role."""
    try:
        # Load SaaS config from env
        saas_api_url = os.getenv("SAAS_API_URL", "https://api.spec-kitty-saas.com")
        auth_token = os.getenv("SAAS_AUTH_TOKEN", "")

        result = join_mission(mission_id, role, saas_api_url, auth_token)

        console.print(f"✅ Joined mission [bold]{mission_id}[/bold] as [bold]{role}[/bold]")
        console.print(f"Participant ID: {result['participant_id']}")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        console.print(f"[red]❌ Network error: {e}[/red]")
        raise typer.Exit(1)

@app.command(name="join")
def join(
    mission_id: str = typer.Argument(..., help="Mission ID"),
    role: str = typer.Option(..., help="Participant role label (SaaS-validated)")
):
    """Join mission as participant."""
    join_command(mission_id, role)
```

---

### T022: Implement Mission Focus Set Command (~120 lines)

Extend existing `src/specify_cli/cli/commands/mission.py`:

```python
from specify_cli.collaboration.service import set_focus
from specify_cli.collaboration.session import resolve_mission_id

def focus_set_command(focus: str, mission_id: str | None = None) -> None:
    """Set focus target."""
    try:
        mission_id = resolve_mission_id(mission_id)
        set_focus(mission_id, focus)

        console.print(f"✅ Focus set to [bold]{focus}[/bold]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

focus_app = typer.Typer(name="focus", help="Focus management commands")

@focus_app.command(name="set")
def set_focus_cmd(
    focus: str = typer.Argument(..., help="Focus target: wp:<id>, step:<id>, or none"),
    mission_id: str | None = typer.Option(None, "--mission", help="Mission ID (default: active mission)")
):
    """Set focus target."""
    focus_set_command(focus, mission_id)
```

---

### T027: Wire Command Routing in Existing Mission Module (~60 lines)

- Keep collaboration commands in `src/specify_cli/cli/commands/mission.py` so command surface remains:
  - `spec-kitty mission join <mission_id> --role <role>`
  - `spec-kitty mission focus set <target>`
- Use sub-typers declared in the same module (for example `focus_app`) and attach them to `mission.app`.
- Do not create a new `src/specify_cli/cli/commands/mission/` package because `mission.py` already exists.
- Ensure `src/specify_cli/cli/commands/__init__.py` continues to register mission commands via existing `mission_module.app`.

---

## Validation

- ✅ `spec-kitty mission join <id> --role developer` succeeds
- ✅ `spec-kitty mission focus set wp:WP01` validates format
- ✅ Rich-formatted success messages
- ✅ Clear error handling

## Activity Log

- 2026-02-15T14:00:24Z – unknown – shell_pid=62639 – lane=for_review – Moved to for_review
- 2026-02-15T14:01:04Z – codex – shell_pid=65606 – lane=doing – Started review via workflow command
- 2026-02-15T14:04:12Z – codex – shell_pid=65606 – lane=done – Codex approval: No blocking issues. Join/focus CLI commands working correctly. 11/11 tests passing.
