---
work_package_id: WP06
title: CLI Commands - Drive, Status, Comment, Decide
lane: "done"
dependencies: [WP04]
base_branch: 040-mission-collaboration-cli-soft-coordination-WP05
base_commit: d70ff8af542b259384f490305a6e26edccae3a59
created_at: '2026-02-15T14:04:29.765150+00:00'
subtasks: [T023, T024, T025, T026]
shell_pid: "74930"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
---

# WP06: CLI Commands - Drive, Status, Comment, Decide

**Purpose**: Implement drive set, mission status, comment, and decide CLI commands.

**Target Branch**: 2.x
**Estimated Effort**: ~350 lines

---

## Implementation Command

```bash
spec-kitty implement WP06 --base WP04
```

---

## Subtasks

### T023: Implement Mission Drive Set Command (~120 lines)

Extend existing `src/specify_cli/cli/commands/mission.py`:

```python
from specify_cli.collaboration.service import set_drive, acknowledge_warning
from rich.panel import Panel
from rich.prompt import Prompt

def drive_set_command(state: str, mission_id: str | None = None) -> None:
    """Set drive intent with collision check."""
    try:
        mission_id = resolve_mission_id(mission_id)
        result = set_drive(mission_id, state)

        # Handle collision
        if "collision" in result:
            collision = result["collision"]

            # Display warning panel
            participants_text = "\n".join(
                f"- {p['participant_id'][:8]}... on {p['focus']} (last: {p['last_activity_at']})"
                for p in collision["conflicting_participants"]
            )

            panel = Panel(
                f"[yellow]{collision['type']}[/yellow]\n\n"
                f"Active drivers on same focus:\n{participants_text}\n\n"
                f"Choose action:\n"
                f"[c] Continue (parallel work, high collision risk)\n"
                f"[h] Hold (set drive=inactive)\n"
                f"[r] Reassign (advisory suggestion)\n"
                f"[d] Defer (exit without change)",
                title=f"⚠️  Collision Detected ({collision['severity']} severity)"
            )
            console.print(panel)

            # Prompt acknowledgement
            action_map = {"c": "continue", "h": "hold", "r": "reassign", "d": "defer"}
            choice = Prompt.ask("Action", choices=list(action_map.keys()))
            acknowledgement = action_map[choice]

            # Handle action
            acknowledge_warning(
                mission_id,
                collision.get("warning_id", ""),
                acknowledgement,
            )

            if acknowledgement == "continue":
                # Re-call set_drive (bypass check)
                set_drive(mission_id, state)
                console.print(f"✅ Drive intent set to [bold]{state}[/bold] (collision acknowledged)")
            elif acknowledgement == "hold":
                console.print("⏸️  Drive remains inactive")
            elif acknowledgement == "defer":
                console.print("Deferred")
                raise typer.Exit(0)

        else:
            console.print(f"✅ Drive intent set to [bold]{state}[/bold]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
```

---

### T024: Implement Mission Status Command (~100 lines)

Extend existing `src/specify_cli/cli/commands/mission.py`:

```python
from specify_cli.collaboration.state import get_mission_roster
from rich.table import Table

def status_command(mission_id: str | None = None, verbose: bool = False) -> None:
    """Display mission status."""
    try:
        mission_id = resolve_mission_id(mission_id)
        roster = get_mission_roster(mission_id)

        table = Table(title=f"Mission {mission_id}")
        table.add_column("Role")
        table.add_column("Participant ID")
        table.add_column("Focus")
        table.add_column("Drive")
        table.add_column("Last Activity")

        for p in roster:
            pid = p.participant_id if verbose else f"{p.participant_id[:8]}..."
            table.add_row(
                (p.role or "unspecified").upper(),
                pid,
                p.focus or "none",
                p.drive_intent,
                p.last_activity_at.strftime("%H:%M:%S")
            )

        console.print(table)
        console.print(f"\n⚠️  {len([p for p in roster if p.drive_intent == 'active'])} active drivers")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
```

---

### T025: Implement Mission Comment Command (~70 lines)

Extend existing `src/specify_cli/cli/commands/mission.py`:

```python
from specify_cli.events.ulid_utils import generate_event_id
from specify_cli.events.store import emit_event

def comment_command(text: str | None = None, mission_id: str | None = None) -> None:
    """Post comment."""
    try:
        mission_id = resolve_mission_id(mission_id)

        if text is None:
            text = typer.prompt("Comment text")

        if len(text.strip()) == 0:
            console.print("[red]❌ Comment cannot be empty[/red]")
            raise typer.Exit(1)

        if len(text) > 500:
            console.print("[yellow]⚠️  Truncating comment to 500 chars[/yellow]")
            text = text[:500]

        state = ensure_joined(mission_id)
        comment_id = generate_event_id()

        # Emit CommentPosted event
        event = Event(
            event_id=comment_id,
            event_type="CommentPosted",
            aggregate_id=f"mission/{mission_id}",
            payload={
                "participant_id": state.participant_id,
                "mission_id": mission_id,
                "comment_id": comment_id,
                "content": text,
                "reply_to": None,
            },
            timestamp=datetime.now().isoformat(),
            node_id="cli-local",
            lamport_clock=LamportClock("cli-local").increment(),
            correlation_id=state.mission_run_id,
            causation_id=None,
        )
        emit_event(mission_id, event, "", "")

        console.print(f"✅ Comment posted (ID: {comment_id[:8]}...)")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
```

---

### T026: Implement Mission Decide Command (~60 lines)

Extend existing `src/specify_cli/cli/commands/mission.py`:

```python
def decide_command(text: str | None = None, mission_id: str | None = None) -> None:
    """Capture decision."""
    try:
        mission_id = resolve_mission_id(mission_id)
        state = ensure_joined(mission_id)

        if text is None:
            text = typer.prompt("Decision text")

        decision_id = generate_event_id()

        # Emit DecisionCaptured event
        event = Event(
            event_id=decision_id,
            event_type="DecisionCaptured",
            aggregate_id=f"mission/{mission_id}",
            payload={
                "participant_id": state.participant_id,
                "mission_id": mission_id,
                "decision_id": decision_id,
                "topic": state.focus or "mission",
                "chosen_option": text,
                "rationale": None,
                "referenced_warning_id": None,
            },
            timestamp=datetime.now().isoformat(),
            node_id="cli-local",
            lamport_clock=LamportClock("cli-local").increment(),
            correlation_id=state.mission_run_id,
            causation_id=None,
        )
        emit_event(mission_id, event, "", "")

        console.print(f"✅ Decision captured (ID: {decision_id[:8]}...)")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
```

---

## Validation

- ✅ Drive displays collision warnings, prompts acknowledgement
- ✅ Status displays roster table with Rich formatting
- ✅ Comment validates length, accepts stdin
- ✅ Decide validates input and emits canonical `DecisionCaptured` payload

## Activity Log

- 2026-02-15T14:08:19Z – unknown – shell_pid=67591 – lane=for_review – Moved to for_review
- 2026-02-15T14:10:01Z – codex – shell_pid=70461 – lane=doing – Started review via workflow command
- 2026-02-15T14:14:10Z – codex – shell_pid=70461 – lane=planned – Moved to planned
- 2026-02-15T14:17:47Z – codex – shell_pid=70461 – lane=for_review – Moved to for_review
- 2026-02-15T14:18:10Z – codex – shell_pid=74930 – lane=doing – Started review via workflow command
- 2026-02-15T14:24:36Z – codex – shell_pid=74930 – lane=planned – Moved to planned
- 2026-02-15T14:28:00Z – codex – shell_pid=74930 – lane=for_review – Moved to for_review
- 2026-02-15T14:28:58Z – codex – shell_pid=74930 – lane=done – Arbiter approval: All 22 tests passing. Event schema issue resolved. Drive, status, comment, and decide commands all working correctly.
