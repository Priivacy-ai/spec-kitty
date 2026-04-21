---
work_package_id: WP04
title: do command
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-010
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "1662"
history:
- date: '2026-04-21'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/cli/commands/do_cmd.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/do_cmd.py
- tests/specify_cli/invocation/cli/test_do.py
tags: []
---

# WP04 — `do` Command

## Objective

Implement `spec-kitty do <request> [--json]` — the anonymous dispatch surface that always
routes through `ActionRouter` without a profile hint. This is the simplest entry point for
operators who want governance context but don't know which profile to address.

**Implementation command**:
```bash
spec-kitty agent action implement WP04 --agent claude
```

## Branch Strategy

Planning base: `main`. Merge target: `main`.
Execution worktree: allocated by `lanes.json`.

## Context

WP02 (router) must be approved. `do` is deliberately simpler than `advise`:
- No `--profile` option
- Router always invoked (no hint path)
- Same `InvocationPayload` response as `advise`
- Same error handling as `advise`

The `do_cmd.py` creates `ProfileInvocationExecutor` with the router wired in.

---

## Subtask T016 — `do_cmd.py`: `spec-kitty do`

**Purpose**: Single-purpose CLI command. No profile hint. Always goes through `ActionRouter`.

**Steps**:

1. Create `src/specify_cli/cli/commands/do_cmd.py`:

```python
from __future__ import annotations
import json
from pathlib import Path
import typer
from rich.console import Console

from specify_cli.invocation.executor import ProfileInvocationExecutor
from specify_cli.invocation.router import ActionRouter
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.errors import RouterAmbiguityError, InvocationWriteError

app = typer.Typer(name="do", help="Route a request to the best matching profile (anonymous dispatch).")
console = Console()

def _get_repo_root() -> Path:
    """Use the project's existing repo-root resolver."""
    return Path.cwd()  # replace with actual utility

def _detect_actor() -> str:
    import os
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude"
    return "operator"

@app.callback(invoke_without_command=True)
def do(
    ctx: typer.Context,
    request: str = typer.Argument(..., help="Natural language request. The router picks the best profile."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON payload"),
) -> None:
    """
    Route a request to the best-matching profile (uses ActionRouter, no explicit profile hint).

    On ambiguity: exits 1 with a structured error listing candidates.
    Use 'spec-kitty ask <profile> <request>' to be explicit.
    """
    if ctx.invoked_subcommand is not None:
        return
    repo_root = _get_repo_root()
    registry = ProfileRegistry(repo_root)
    router = ActionRouter(registry)
    executor = ProfileInvocationExecutor(repo_root, router=router)
    try:
        payload = executor.invoke(request, profile_hint=None, actor=_detect_actor())
    except RouterAmbiguityError as e:
        error_obj = {
            "error": "routing_failed",
            "error_code": e.error_code,
            "message": str(e),
            "candidates": e.candidates,
            "suggestion": e.suggestion,
        }
        if json_output:
            typer.echo(json.dumps(error_obj, indent=2), err=True)
        else:
            console.print(f"[red]Routing failed:[/red] {e.suggestion}")
            if e.candidates:
                console.print("Candidates:")
                for c in e.candidates:
                    console.print(f"  - {c['profile_id']}: {c['match_reason']}")
            console.print("\nUse 'spec-kitty ask <profile> <request>' to be explicit.")
        raise typer.Exit(1)
    except InvocationWriteError as e:
        typer.echo(json.dumps({"error": "write_failed", "message": str(e)}), err=True)
        raise typer.Exit(1)

    if json_output:
        typer.echo(json.dumps(payload.to_dict(), indent=2))
    else:
        console.print(f"[bold green]Profile:[/bold green] {payload.profile_friendly_name}")
        console.print(f"[bold]Action:[/bold] {payload.action} (confidence: {payload.router_confidence})")
        console.print(f"[dim]Invocation ID:[/dim] {payload.invocation_id}")
        if payload.governance_context_available:
            from rich.panel import Panel
            console.print(Panel(payload.governance_context_text, title="Governance Context", expand=False))
        else:
            console.print("[yellow]⚠ Governance context unavailable.[/yellow]")
```

**Files**: `src/specify_cli/cli/commands/do_cmd.py`

---

## Subtask T017 — Register `do` in `main.py`

**Steps**:

In `src/specify_cli/cli/main.py`, add:

```python
from specify_cli.cli.commands.do_cmd import app as do_app
app.add_typer(do_app, name="do")
```

**Note**: `main.py` is modified by multiple WPs (WP01, WP03, WP04, WP06). This line is a non-conflicting addition. If a merge conflict arises, keep all `add_typer()` calls.

**Files**: `src/specify_cli/cli/main.py`

---

## Subtask T018 — Integration Tests: `test_do.py`

**Test cases**:

```python
from typer.testing import CliRunner
from specify_cli.cli.main import app
import json

runner = CliRunner()

def test_do_implement_routes_to_implementer(tmp_path, monkeypatch):
    """'implement the feature' routes to implementer-fixture via CANONICAL_VERB_MAP."""
    # monkeypatch repo_root to tmp_path with fixture profiles
    result = runner.invoke(app, ["do", "implement the feature", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["profile_id"] == "implementer-fixture"
    assert data["action"] == "implement"
    assert data["router_confidence"] == "canonical_verb"
    assert data["invocation_id"]

def test_do_ambiguous_request_exits_1(tmp_path, monkeypatch):
    """Vague request 'help me' → RouterAmbiguityError → exit 1"""
    result = runner.invoke(app, ["do", "help me", "--json"])
    assert result.exit_code == 1
    # Error goes to stderr; check exit code is sufficient

def test_do_no_match_exits_1(tmp_path, monkeypatch):
    """Request with no recognizable verbs → ROUTER_NO_MATCH → exit 1"""
    result = runner.invoke(app, ["do", "the quick brown fox", "--json"])
    assert result.exit_code == 1

def test_do_creates_jsonl_record(tmp_path, monkeypatch):
    """Successful routing creates a JSONL invocation record."""
    result = runner.invoke(app, ["do", "implement the payment module", "--json"])
    assert result.exit_code == 0
    events_dir = tmp_path / ".kittify" / "events" / "profile-invocations"
    jsonl_files = list(events_dir.glob("*.jsonl")) if events_dir.exists() else []
    assert len(jsonl_files) == 1
```

**Files**: `tests/specify_cli/invocation/cli/test_do.py`

**Acceptance**:
- [ ] `spec-kitty do "implement the feature" --json` exits 0, returns InvocationPayload with correct profile
- [ ] `spec-kitty do "help me" --json` exits 1 with `ROUTER_AMBIGUOUS` or `ROUTER_NO_MATCH` error
- [ ] JSONL record created on successful routing

## Definition of Done

- [ ] `src/specify_cli/cli/commands/do_cmd.py` exists and is registered in `main.py`
- [ ] All 4 integration tests pass
- [ ] `mypy --strict` clean
- [ ] `spec-kitty do --help` renders correctly

## Risks

- **_get_repo_root helper**: Use the same utility as `advise.py` (WP03). If WP03 and WP04 are in different lanes, both implementers must use the same utility call — coordinate via the plan.
- **Duplicate `_detect_actor` function**: Both `advise.py` and `do_cmd.py` define `_detect_actor`. Move to a shared `src/specify_cli/invocation/actor.py` helper if both are in the same lane; otherwise define separately and reconcile at merge.

## Reviewer Guidance

1. Verify `do` command always passes `profile_hint=None` to the executor.
2. Verify ambiguity error contains `candidates` list (helps operator choose `ask <profile>`).
3. Verify rich output path shows `router_confidence`.
4. Verify `main.py` has exactly one `add_typer()` call for `do`.

## Activity Log

- 2026-04-21T12:28:54Z – claude:sonnet-4-6:implementer:implementer – shell_pid=92886 – Started implementation via action command
- 2026-04-21T12:33:44Z – claude:sonnet-4-6:implementer:implementer – shell_pid=92886 – WP04 complete: do command with router dispatch, 11/11 tests passing
- 2026-04-21T12:33:59Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=1662 – Started review via action command
