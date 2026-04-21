---
work_package_id: WP03
title: advise + ask + profile-invocation complete CLI
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-006
- FR-007
- FR-008
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Planning base: main. Merge target: main. Execution worktrees are allocated per computed lane from lanes.json.'
subtasks:
- T011
- T012
- T013
- T014
- T015
history:
- date: '2026-04-21'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/cli/commands/advise.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/advise.py
- src/specify_cli/cli/main.py
- tests/specify_cli/invocation/cli/test_advise.py
tags: []
---

# WP03 — `advise` + `ask` + `profile-invocation complete` CLI

## Objective

Implement the three primary CLI surfaces for profile-governed invocations:
- `spec-kitty advise <request> [--profile <name>] [--json]` — opens an invocation record
- `spec-kitty ask <profile> <request> [--json]` — named-profile shorthand
- `spec-kitty profile-invocation complete --invocation-id <id> [--outcome] [--evidence]` — closes the record

These are the surfaces a host-LLM agent (Claude Code, Codex, Cursor) calls to get governance context and close invocation records.

**Implementation command**:
```bash
spec-kitty agent action implement WP03 --agent claude
```

## Branch Strategy

Planning base: `main`. Merge target: `main`.
Execution worktree: allocated by `lanes.json`.

## Context

WP01 and WP02 must be approved. This WP creates `advise.py` and registers three command groups in `main.py`.

**Critical invariants**:
- `advise` MUST NOT spawn a LLM call — it only calls `ProfileInvocationExecutor.invoke()`
- On write failure (`InvocationWriteError`): exit code 1, structured JSON error to stderr
- `--json` flag: write JSON to stdout; rich output to stdout for non-JSON
- Router ambiguity from `--profile`-less `advise`: structured JSON error, exit 1

---

## Subtask T011 — `advise.py`: `spec-kitty advise`

**Purpose**: Main `advise` command. Creates executor with router, calls `invoke()`, outputs `InvocationPayload`.

**Steps**:

1. Create `src/specify_cli/cli/commands/advise.py`:

```python
from __future__ import annotations
import json
import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel

from specify_cli.invocation.executor import ProfileInvocationExecutor, InvocationPayload
from specify_cli.invocation.router import ActionRouter
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.errors import (
    RouterAmbiguityError,
    ProfileNotFoundError,
    InvocationWriteError,
    ContextUnavailableError,
)

app = typer.Typer(name="advise", help="Get governance context for an action (opens an invocation record).")
console = Console()

def _get_repo_root() -> Path:
    """Use the project's existing repo-root resolver."""
    # Replace with actual utility: e.g., from specify_cli.context import get_repo_root
    return Path.cwd()

def _build_executor(repo_root: Path) -> ProfileInvocationExecutor:
    registry = ProfileRegistry(repo_root)
    router = ActionRouter(registry)
    return ProfileInvocationExecutor(repo_root, router=router)

def _detect_actor() -> str:
    """Detect caller identity from environment."""
    import os
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude"
    if os.environ.get("CODEX_CLI"):
        return "codex"
    return "operator"

@app.callback(invoke_without_command=True)
def advise(
    ctx: typer.Context,
    request: str = typer.Argument(..., help="Natural language request to route"),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Explicit profile ID or name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON payload"),
) -> None:
    """Get governance context for a request. Opens an invocation record. Does NOT spawn an LLM."""
    if ctx.invoked_subcommand is not None:
        return
    repo_root = _get_repo_root()
    executor = _build_executor(repo_root)
    try:
        payload = executor.invoke(request, profile_hint=profile, actor=_detect_actor())
    except RouterAmbiguityError as e:
        error_obj = {
            "error": "routing_failed",
            "error_code": e.error_code,
            "message": str(e),
            "candidates": e.candidates,
            "suggestion": e.suggestion,
        }
        typer.echo(json.dumps(error_obj), err=True)
        raise typer.Exit(1)
    except ProfileNotFoundError as e:
        typer.echo(json.dumps({"error": "profile_not_found", "message": str(e)}), err=True)
        raise typer.Exit(1)
    except InvocationWriteError as e:
        typer.echo(json.dumps({"error": "write_failed", "message": str(e)}), err=True)
        raise typer.Exit(1)

    if json_output:
        typer.echo(json.dumps(payload.to_dict(), indent=2))
    else:
        _render_rich_payload(payload)

def _render_rich_payload(payload: InvocationPayload) -> None:
    """Rich console output for human-readable advise response."""
    console.print(f"[bold green]Profile:[/bold green] {payload.profile_friendly_name} ({payload.profile_id})")
    console.print(f"[bold]Action:[/bold] {payload.action}")
    if payload.router_confidence:
        console.print(f"[dim]Router confidence:[/dim] {payload.router_confidence}")
    console.print(f"[dim]Invocation ID:[/dim] {payload.invocation_id}")
    if payload.governance_context_available:
        console.print(Panel(payload.governance_context_text, title="Governance Context", expand=False))
    else:
        console.print("[yellow]⚠ Governance context unavailable.[/yellow] Run 'spec-kitty charter synthesize'.")
    console.print(f"\n[dim]Close this record:[/dim] spec-kitty profile-invocation complete --invocation-id {payload.invocation_id}")
```

**Files**: `src/specify_cli/cli/commands/advise.py`

---

## Subtask T012 — `spec-kitty ask <profile> <request>`

**Purpose**: Thin shim over `advise --profile`. Added as a top-level command in the same `advise.py` file.

**Steps**:

Add a separate typer app for `ask` in `advise.py`:

```python
ask_app = typer.Typer(name="ask", help="Invoke a named profile directly.")

@ask_app.callback(invoke_without_command=True)
def ask(
    ctx: typer.Context,
    profile: str = typer.Argument(..., help="Profile ID or name"),
    request: str = typer.Argument(..., help="Natural language request"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Invoke a named profile. Equivalent to 'advise --profile <profile> <request>'."""
    if ctx.invoked_subcommand is not None:
        return
    repo_root = _get_repo_root()
    executor = _build_executor(repo_root)
    try:
        payload = executor.invoke(request, profile_hint=profile, actor=_detect_actor())
    except (RouterAmbiguityError, ProfileNotFoundError, InvocationWriteError) as e:
        error_obj = {"error": type(e).__name__.lower(), "message": str(e)}
        typer.echo(json.dumps(error_obj), err=True)
        raise typer.Exit(1)
    if json_output:
        typer.echo(json.dumps(payload.to_dict(), indent=2))
    else:
        _render_rich_payload(payload)
```

**Files**: `src/specify_cli/cli/commands/advise.py` (append to file)

---

## Subtask T013 — `spec-kitty profile-invocation complete`

**Purpose**: Closes an open invocation record by appending the `completed` event.

**Steps**:

Add a `profile_invocation_app` typer in `advise.py`:

```python
profile_invocation_app = typer.Typer(name="profile-invocation", help="Manage invocation records.")

@profile_invocation_app.command("complete")
def complete_invocation(
    invocation_id: str = typer.Option(..., "--invocation-id", "-i", help="Invocation ULID to close"),
    profile_id: str = typer.Option(..., "--profile-id", help="Profile ID for the invocation"),
    outcome: str | None = typer.Option(None, "--outcome", help="done | failed | abandoned"),
    evidence: str | None = typer.Option(None, "--evidence", help="Path to evidence file (Tier 2 promotion)"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Close an open invocation record."""
    from specify_cli.invocation.writer import InvocationWriter
    repo_root = _get_repo_root()
    writer = InvocationWriter(repo_root)
    try:
        completed = writer.write_completed(
            invocation_id=invocation_id,
            profile_id=profile_id,
            repo_root=repo_root,
            outcome=outcome,
            evidence_ref=evidence,
        )
    except Exception as e:
        typer.echo(json.dumps({"error": "complete_failed", "message": str(e)}), err=True)
        raise typer.Exit(1)
    if json_output:
        typer.echo(json.dumps(completed.model_dump(), indent=2))
    else:
        console.print(f"[green]✓[/green] Invocation [bold]{invocation_id}[/bold] closed.")
        if outcome:
            console.print(f"  Outcome: {outcome}")
```

**Note on `--profile-id`**: The `write_completed` method needs `profile_id` to locate the JSONL file (filename is `<profile_id>-<invocation_id>.jsonl`). The operator receives `profile_id` in the `InvocationPayload` from `advise` / `ask` / `do`.

**Files**: `src/specify_cli/cli/commands/advise.py` (append)

---

## Subtask T014 — Register command groups in `main.py`

**Purpose**: Wire `advise`, `ask`, and `profile-invocation` command groups into the main CLI app.

**Steps**:

In `src/specify_cli/cli/main.py`, add:

```python
from specify_cli.cli.commands.advise import app as advise_app, ask_app, profile_invocation_app
app.add_typer(advise_app, name="advise")
app.add_typer(ask_app, name="ask")
app.add_typer(profile_invocation_app, name="profile-invocation")
```

**Note**: `main.py` is also modified by WP01 (profiles), WP04 (do), WP06 (invocations). Since these WPs are in different lanes but serialized via dependencies, conflicts in `main.py` must be resolved at merge time. Each implementer adds their `add_typer()` line — these are non-conflicting additions.

**Files**: `src/specify_cli/cli/main.py`

---

## Subtask T015 — Integration Tests: `test_advise.py`

**Purpose**: Integration tests using `typer.testing.CliRunner` to cover `advise`, `ask`, and `profile-invocation complete`.

**Test cases**:

```python
from typer.testing import CliRunner
from specify_cli.cli.main import app

runner = CliRunner()

def test_advise_with_explicit_profile_json(tmp_path, monkeypatch):
    """advise --profile implementer-fixture returns valid JSON InvocationPayload."""
    # setup: copy fixture profiles to tmp_path/.kittify/profiles/
    # monkeypatch repo root to tmp_path
    result = runner.invoke(app, ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "invocation_id" in data
    assert data["profile_id"] == "implementer-fixture"
    assert data["action"] == "implement"
    # Verify JSONL file was created
    jsonl_files = list((tmp_path / ".kittify/events/profile-invocations").glob("*.jsonl"))
    assert len(jsonl_files) == 1

def test_advise_missing_profile_exits_1(tmp_path, monkeypatch):
    result = runner.invoke(app, ["advise", "implement", "--profile", "nonexistent", "--json"])
    assert result.exit_code == 1
    err = json.loads(result.output or result.stderr or "")
    assert "profile_not_found" in err.get("error", "")

def test_advise_no_charter_governance_context_unavailable(tmp_path, monkeypatch):
    """When charter is missing, governance_context_available=False but exit 0."""
    result = runner.invoke(app, ["advise", "implement", "--profile", "implementer-fixture", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["governance_context_available"] is False
    assert data["invocation_id"]  # record still written

def test_ask_shim_delegates_to_advise(tmp_path, monkeypatch):
    """ask implementer-fixture 'implement feature' == advise --profile implementer-fixture 'implement feature'"""
    result = runner.invoke(app, ["ask", "implementer-fixture", "implement the feature", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["profile_id"] == "implementer-fixture"

def test_profile_invocation_complete(tmp_path, monkeypatch):
    """Complete closes the record."""
    # First open a record
    result = runner.invoke(app, ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"])
    invocation_id = json.loads(result.output)["invocation_id"]
    # Then close it
    result2 = runner.invoke(app, [
        "profile-invocation", "complete",
        "--invocation-id", invocation_id,
        "--profile-id", "implementer-fixture",
        "--outcome", "done",
        "--json",
    ])
    assert result2.exit_code == 0
    data2 = json.loads(result2.output)
    assert data2["event"] == "completed"
    assert data2["outcome"] == "done"
```

**Files**: `tests/specify_cli/invocation/cli/test_advise.py`

**Acceptance**:
- [ ] All 5 integration tests pass
- [ ] `mypy --strict` clean on `advise.py`
- [ ] `spec-kitty advise --help` shows description and options correctly

## Definition of Done

- [ ] `spec-kitty advise <request> --profile <p> --json` exits 0, returns InvocationPayload JSON, creates JSONL file
- [ ] `spec-kitty ask <profile> <request> --json` exits 0, same contract as advise
- [ ] `spec-kitty profile-invocation complete --invocation-id <id> --profile-id <p>` appends completed event
- [ ] Missing profile → exit 1, JSON error on stderr
- [ ] Write failure → exit 1, JSON error on stderr
- [ ] `mypy --strict` clean

## Risks

- **`--profile-id` UX**: Requiring `--profile-id` in `profile-invocation complete` adds friction. Alternative: scan JSONL files to find the invocation by ID regardless of profile. Evaluate during implementation and choose the simpler approach (ID-only lookup is fine if we add a `find_by_invocation_id(repo_root, invocation_id)` helper to the writer).
- **`_get_repo_root()` pattern**: Use the project's existing utility, not `Path.cwd()`. Check how other commands resolve the repo root.

## Reviewer Guidance

1. Verify `advise` command does not import any LLM client.
2. Verify JSON errors go to stderr, not stdout.
3. Verify a JSONL file is created before `typer.echo()` in the happy path.
4. Verify rich output path doesn't crash on empty governance_context_text.
5. Verify `ask` is genuinely a thin delegation, not duplicated logic.
