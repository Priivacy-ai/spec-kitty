---
work_package_id: WP06
title: invocations list + skill pack updates
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
history:
- date: '2026-04-21'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/cli/commands/invocations_cmd.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/invocations_cmd.py
- tests/specify_cli/invocation/cli/test_invocations.py
- .agents/skills/spec-kitty.advise/**
tags: []
---

# WP06 — `invocations list` + Skill Pack Updates

## Objective

Implement `spec-kitty invocations list` — the operator's view into the local JSONL audit log.
Benchmark performance at 10K entries. Update agent skill packs to document the new surfaces.

**Implementation command**:
```bash
spec-kitty agent action implement WP06 --agent claude
```

## Branch Strategy

Planning base: `main`. Merge target: `main`.
Execution worktree: allocated by `lanes.json`.

## Context

WP01 (writer + JSONL structure) must be approved. This WP reads from the event log but does not write to it.

**Storage path**: `.kittify/events/profile-invocations/` (one JSONL file per invocation)
**Performance threshold**: `invocations list` must complete in < 200ms for 100 most recent records when the directory has 10,000 JSONL files (NFR-008).

---

## Subtask T022 — `invocations_cmd.py`: `spec-kitty invocations list`

**Purpose**: Query the local JSONL audit log and return a list of recent invocation records.

**Steps**:

1. Create `src/specify_cli/cli/commands/invocations_cmd.py`:

```python
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterator
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="invocations", help="Query local invocation records.")
console = Console()

EVENTS_DIR = ".kittify/events/profile-invocations"

def _get_repo_root() -> Path:
    return Path.cwd()  # replace with actual utility

def _read_last_line(path: Path) -> dict | None:
    """Read the last JSONL line from a file (O(1) seek-to-end)."""
    try:
        with path.open("rb") as f:
            # Seek to end and read backward for last non-empty line
            f.seek(0, 2)  # end of file
            size = f.tell()
            if size == 0:
                return None
            # Read up to 4KB from the end to find the last line
            f.seek(max(0, size - 4096))
            tail = f.read().decode("utf-8", errors="replace")
        lines = [l.strip() for l in tail.splitlines() if l.strip()]
        if not lines:
            return None
        return json.loads(lines[-1])
    except (OSError, json.JSONDecodeError):
        return None

def _read_first_line(path: Path) -> dict | None:
    """Read the first JSONL line (the started event)."""
    try:
        with path.open("r", encoding="utf-8") as f:
            line = f.readline().strip()
            return json.loads(line) if line else None
    except (OSError, json.JSONDecodeError):
        return None

def _iter_records(
    events_dir: Path,
    profile_filter: str | None,
    limit: int,
) -> Iterator[dict]:
    """
    Yield record dicts by scanning the directory.
    Each file: read first line (started) + last line (may be completed).
    Sort by started_at descending, yield up to limit.
    """
    if not events_dir.exists():
        return

    # Filename is <invocation_id>.jsonl — no profile prefix in filename.
    # Profile filtering requires reading each file's first line content.
    # Sort by started_at from file CONTENT (not mtime) to get correct temporal ordering.
    # Using mtime would produce wrong ordering when old invocations are later completed.
    raw_records = []
    for path in events_dir.glob("*.jsonl"):
        started = _read_first_line(path)
        if started is None:
            continue
        # Apply profile filter by reading content (not filename)
        if profile_filter and started.get("profile_id") != profile_filter:
            continue
        last = _read_last_line(path)
        record = dict(started)
        if last and last.get("event") == "completed" and last.get("invocation_id") == record.get("invocation_id"):
            record["completed_at"] = last.get("completed_at")
            record["outcome"] = last.get("outcome")
            record["evidence_ref"] = last.get("evidence_ref")
            record["status"] = "closed"
        else:
            record["status"] = "open"
        raw_records.append(record)

    # Sort by started_at descending (ISO-8601 strings sort lexicographically)
    raw_records.sort(key=lambda r: r.get("started_at", ""), reverse=True)

    count = 0
    for record in raw_records:
        if count >= limit:
            break
        yield record
        count += 1


@app.command("list")
def list_invocations(
    profile: str | None = typer.Option(None, "--profile", "-p", help="Filter by profile ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max records to show (default: 20)"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON array"),
) -> None:
    """List recent invocation records from the local audit log."""
    repo_root = _get_repo_root()
    events_dir = repo_root / EVENTS_DIR
    records = list(_iter_records(events_dir, profile, limit))

    if json_output:
        typer.echo(json.dumps(records, indent=2))
        return

    if not records:
        console.print("[dim]No invocation records found.[/dim]")
        return

    table = Table(title="Recent Invocations")
    table.add_column("Invocation ID", style="dim")
    table.add_column("Profile")
    table.add_column("Action")
    table.add_column("Status")
    table.add_column("Started At")
    for r in records:
        status_style = "green" if r.get("status") == "closed" else "yellow"
        table.add_row(
            r.get("invocation_id", "?")[:12] + "…",
            r.get("profile_id", "?"),
            r.get("action", "?"),
            f"[{status_style}]{r.get('status', '?')}[/{status_style}]",
            (r.get("started_at") or "?")[:19],
        )
    console.print(table)
```

**Files**: `src/specify_cli/cli/commands/invocations_cmd.py`

---

## Subtask T023 — Register `invocations` in `main.py`

**Steps**:

In `src/specify_cli/cli/main.py`, add:
```python
from specify_cli.cli.commands.invocations_cmd import app as invocations_app
app.add_typer(invocations_app, name="invocations")
```

**Files**: `src/specify_cli/cli/main.py`

---

## Subtask T024 — Benchmark + Optional Index

**Purpose**: Verify that `invocations list` completes within 200ms for 100 records from a 10,000-file directory.

**Steps**:

1. Write a benchmark fixture generator in the test file:
```python
def create_fixture_invocations(events_dir: Path, count: int) -> None:
    """Create `count` synthetic JSONL files for benchmarking."""
    from ulid2 import generate_ulid_as_uuid
    import datetime
    events_dir.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        inv_id = str(generate_ulid_as_uuid())
        path = events_dir / f"implementer-fixture-{inv_id}.jsonl"
        record = {"event": "started", "invocation_id": inv_id, "profile_id": "implementer-fixture",
                  "action": "implement", "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
```

2. Run performance test:
```python
def test_list_performance_10k(tmp_path):
    """invocations list for 100 records from 10K files must complete in < 200ms."""
    import time
    events_dir = tmp_path / ".kittify" / "events" / "profile-invocations"
    create_fixture_invocations(events_dir, 10_000)
    start = time.monotonic()
    records = list(_iter_records(events_dir, None, 100))
    elapsed = time.monotonic() - start
    assert len(records) == 100
    assert elapsed < 0.200, f"Performance gate failed: {elapsed:.3f}s (threshold: 0.200s)"
```

3. **If the test fails** (> 200ms): implement an append-only invocation index at `.kittify/events/invocation-index.jsonl`. The writer's `write_started()` appends `{invocation_id, profile_id, started_at}` to this index after the per-invocation file is created. The `_iter_records` function then reads the index in reverse instead of scanning the directory.

The index approach:
```python
INDEX_PATH = ".kittify/events/invocation-index.jsonl"

def _append_to_index(repo_root: Path, record: dict) -> None:
    index = repo_root / INDEX_PATH
    index.parent.mkdir(parents=True, exist_ok=True)
    with index.open("a") as f:
        f.write(json.dumps({"invocation_id": record["invocation_id"],
                            "profile_id": record["profile_id"],
                            "started_at": record["started_at"]}) + "\n")
```

**Decision during WP06**: only implement the index if the performance gate fails. Do not add it preemptively.

---

## Subtask T025 — Integration Tests: `test_invocations.py`

**Test cases**:

```python
from typer.testing import CliRunner
from specify_cli.cli.main import app
import json

runner = CliRunner()

def test_invocations_list_json_empty(tmp_path, monkeypatch):
    """Empty log → empty JSON array."""
    result = runner.invoke(app, ["invocations", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == []

def test_invocations_list_shows_records(tmp_path, monkeypatch):
    """After creating 3 records, list returns 3."""
    # create 3 JSONL files in tmp_path/.kittify/events/profile-invocations/
    ...
    result = runner.invoke(app, ["invocations", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 3

def test_invocations_list_limit(tmp_path, monkeypatch):
    """--limit 2 returns at most 2 records even with 5 files."""
    ...
    result = runner.invoke(app, ["invocations", "list", "--limit", "2", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) <= 2

def test_invocations_list_profile_filter(tmp_path, monkeypatch):
    """--profile implementer-fixture filters out reviewer-fixture records."""
    ...
    result = runner.invoke(app, ["invocations", "list", "--profile", "implementer-fixture", "--json"])
    data = json.loads(result.output)
    assert all(r["profile_id"] == "implementer-fixture" for r in data)

def test_invocations_list_shows_status(tmp_path, monkeypatch):
    """Closed records show status=closed; open records show status=open."""
    ...  # create one open and one closed record
    result = runner.invoke(app, ["invocations", "list", "--json"])
    data = json.loads(result.output)
    statuses = {r["invocation_id"]: r["status"] for r in data}
    assert "closed" in statuses.values()
    assert "open" in statuses.values()
```

**Files**: `tests/specify_cli/invocation/cli/test_invocations.py`

---

## Subtask T026 — Skill Pack: `.agents/skills/spec-kitty.advise/SKILL.md`

**Purpose**: Document the new `advise`, `ask`, `do`, `profiles list`, `invocations list`, and `profile-invocation complete` commands for Codex/Vibe/agent-skills consumers.

**Steps**:

1. Create `.agents/skills/spec-kitty.advise/SKILL.md`:

```markdown
# spec-kitty.advise

Get governance context for an action and open an invocation record.

## Usage

### Discover profiles
\`\`\`bash
spec-kitty profiles list --json
\`\`\`

### Get governance context (opens invocation record)
\`\`\`bash
spec-kitty advise "implement WP03" --json
spec-kitty ask pedro "review WP05" --json
spec-kitty do "implement the payment module" --json
\`\`\`

Response fields: `invocation_id`, `profile_id`, `action`, `governance_context_text`, `governance_context_hash`, `governance_context_available`, `router_confidence`.

### Close the record
\`\`\`bash
spec-kitty profile-invocation complete --invocation-id <id> --profile-id <profile_id> --outcome done
\`\`\`

### Review recent invocations
\`\`\`bash
spec-kitty invocations list --limit 10 --json
spec-kitty invocations list --profile pedro --json
\`\`\`

## When to use

- Before implementing: `spec-kitty ask <profile> "implement <feature>"` to get governance context
- After implementing: `spec-kitty profile-invocation complete --invocation-id <id> --outcome done`
- When profile is unknown: `spec-kitty do "implement <feature>"` (router picks best profile)

## What gets recorded

Every invocation writes one JSONL record to `.kittify/events/profile-invocations/`.
This is the Tier 1 minimal viable trail — always written, never skipped.

## Invariants

- `advise`/`ask`/`do` NEVER spawn a separate LLM call
- The `governance_context_text` is assembled from the project's DRG
- If `governance_context_available` is false, run `spec-kitty charter synthesize`
```

Also update `spec-kitty-saas/.kittify/command-skills-manifest.json` if it tracks skill packs — check manifest format and add `spec-kitty.advise` entry if applicable.

**Files**: `.agents/skills/spec-kitty.advise/SKILL.md`

**Acceptance**:
- [ ] All 5 `test_invocations.py` tests pass
- [ ] Performance gate: < 200ms at 10K files (or index implemented)
- [ ] `spec-kitty invocations list --json` returns valid JSON
- [ ] Skill pack SKILL.md exists with accurate command documentation
- [ ] `mypy --strict` clean on `invocations_cmd.py`

## Definition of Done

- [ ] `spec-kitty invocations list [--profile] [--limit] [--json]` works end-to-end
- [ ] Performance gate passes (< 200ms, or index implemented)
- [ ] Skill pack `.agents/skills/spec-kitty.advise/SKILL.md` committed
- [ ] All tests pass, `mypy --strict` clean

## Risks

- **Performance at 10K files**: `os.scandir` is fast but 10K `readline()` calls may exceed 200ms on slow disks or CI. If the benchmark fails, implement the index immediately in this WP.
- **`command-skills-manifest.json`**: Check `.kittify/command-skills-manifest.json` to see if a new skill entry is required. If so, update it as part of T026.

## Reviewer Guidance

1. Verify `_read_last_line` uses an O(1) seek-to-end approach, not `readlines()[-1]`.
2. Verify performance benchmark is present and passes (< 200ms).
3. Verify skill pack SKILL.md mentions the `governance_context_text` field.
4. Verify `main.py` has exactly one `add_typer()` call for `invocations`.
