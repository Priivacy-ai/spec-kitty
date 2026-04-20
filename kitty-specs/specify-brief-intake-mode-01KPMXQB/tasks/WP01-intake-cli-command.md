---
work_package_id: WP01
title: spec-kitty intake CLI Command
dependencies: []
requirement_refs:
- C-001
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-specify-brief-intake-mode-01KPMXQB
base_commit: d1666da8961b8183d32c9e501fdb1912e54648b4
created_at: '2026-04-20T08:18:29.061065+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
shell_pid: "96385"
agent: "claude:sonnet:reviewer:reviewer"
history:
- date: '2026-04-20'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- src/specify_cli/mission_brief.py
- src/specify_cli/cli/commands/intake.py
- src/specify_cli/cli/commands/__init__.py
- .gitignore
- tests/specify_cli/test_mission_brief.py
- tests/specify_cli/cli/commands/test_intake.py
tags: []
---

# WP01 — `spec-kitty intake` CLI Command

## Objective

Implement the complete `spec-kitty intake <path>` command: a new root-level standalone CLI command that ingests any Markdown plan document into `.kittify/mission-brief.md` (with provenance header) and `.kittify/brief-source.yaml` (SHA-256 fingerprint + metadata). Both files are gitignored. The command also supports stdin (`-`), `--force` overwrite, and `--show` read-only inspection.

This WP is independent of WP02 (template edit) and can run concurrently.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP01 --agent <name>`; do not guess the worktree path

## Context

### Reference Pattern

The authoritative reference implementation is `src/specify_cli/tracker/ticket_context.py`. Read it fully before writing `mission_brief.py`. The structure to follow:

- Module-level filename constants
- `write_*()` helper that creates `.kittify/` if absent, writes the file, returns `Path`
- `read_*()` helper that returns `None` if absent, catches exceptions
- `clear_*()` helper that calls `path.unlink()` only if `path.exists()`
- No auth credentials, no network calls, plain YAML for metadata

### Existing CLI Registration Pattern

In `src/specify_cli/cli/commands/__init__.py`:

- Top-level imports (alphabetical): `from . import <name> as <name>_module`
- Registration inside `register_commands()`: `app.command()(<module>.fn)`
- Standalone root-level commands use `app.command()` (not `app.add_typer`)
- Line 55 shows the pattern: `app.command()(lifecycle_module.plan)` — `intake` uses the same form

### Existing Test Pattern

In `tests/specify_cli/cli/commands/`:

```python
from __future__ import annotations
from pathlib import Path
import pytest
from typer.testing import CliRunner
from specify_cli import app   # or from specify_cli.cli.commands.intake import app

pytestmark = pytest.mark.fast
runner = CliRunner()
```

Use `runner.invoke(app, ["intake", "PLAN.md"], catch_exceptions=False)` for integration tests against the full app. For unit tests of `mission_brief.py`, use `tmp_path` fixtures directly (no CliRunner needed).

---

## Subtasks

### T001 — Create `src/specify_cli/mission_brief.py`

**Purpose**: Provide the business logic for reading, writing, and clearing the mission brief artifacts. This is the single source of truth for file paths and content format.

**File**: `src/specify_cli/mission_brief.py` (new, ~80 lines)

**Implementation**:

1. Define constants:
   ```python
   MISSION_BRIEF_FILENAME = "mission-brief.md"
   BRIEF_SOURCE_FILENAME = "brief-source.yaml"
   ```

2. Implement `write_mission_brief(repo_root: Path, content: str, source_file: str) -> tuple[Path, Path]`:
   - Compute `brief_hash = hashlib.sha256(content.encode()).hexdigest()`
   - Compute `ingested_at` as `datetime.now(tz=timezone.utc).isoformat()`
   - Build provenance header (two HTML comment lines):
     ```
     <!-- spec-kitty intake: ingested from {source_file} at {ingested_at} -->
     <!-- brief_hash: {brief_hash} -->
     ```
   - Write `kittify / MISSION_BRIEF_FILENAME` with header + `"\n\n"` + content
   - Write `kittify / BRIEF_SOURCE_FILENAME` with ruamel.yaml:
     ```yaml
     source_file: <source_file>
     ingested_at: "<ingested_at>"
     brief_hash: "<brief_hash>"
     ```
   - Returns `(brief_path, source_path)`
   - Creates `.kittify/` with `mkdir(exist_ok=True)` if absent

3. Implement `read_mission_brief(repo_root: Path) -> str | None`:
   - Returns full file content of `mission-brief.md` or `None` if absent/unreadable

4. Implement `read_brief_source(repo_root: Path) -> dict[str, Any] | None`:
   - Returns parsed YAML of `brief-source.yaml` or `None` if absent/unparseable

5. Implement `clear_mission_brief(repo_root: Path) -> None`:
   - Unlinks `mission-brief.md` and `brief-source.yaml` if they exist (silently skip if absent)

**Type annotations**: All functions must have full annotations. Use `from __future__ import annotations`. Import `Any` from `typing`.

**Imports needed**: `hashlib`, `datetime.datetime`, `datetime.timezone`, `pathlib.Path`, `typing.Any`, `ruamel.yaml`

**Validation**:
- [ ] `mypy --strict src/specify_cli/mission_brief.py` passes with zero errors
- [ ] Module exports: `write_mission_brief`, `read_mission_brief`, `read_brief_source`, `clear_mission_brief`, `MISSION_BRIEF_FILENAME`, `BRIEF_SOURCE_FILENAME`

---

### T002 — Create `src/specify_cli/cli/commands/intake.py`

**Purpose**: Implement the `spec-kitty intake` root-level CLI command as a thin typer wrapper around `mission_brief.py`.

**File**: `src/specify_cli/cli/commands/intake.py` (new, ~90 lines)

**Implementation**:

```python
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from specify_cli.mission_brief import (
    read_brief_source,
    read_mission_brief,
    write_mission_brief,
    MISSION_BRIEF_FILENAME,
)

console = Console()
err_console = Console(stderr=True)


def intake(
    path: Optional[str] = typer.Argument(
        None,
        help="Path to plan document, or '-' to read from stdin. Omit when using --show.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing brief."),
    show: bool = typer.Option(False, "--show", help="Print current brief and provenance; no writes."),
) -> None:
    """Ingest a plan document as a mission brief for /spec-kitty.specify."""
    repo_root = Path.cwd()
    ...
```

**Command dispatch logic** (evaluate in this order):

1. **`--show` branch**: if `show` is True
   - Read `read_mission_brief(repo_root)` and `read_brief_source(repo_root)`
   - If both absent: `err_console.print("[red]No brief found at .kittify/mission-brief.md[/red]")`, `raise typer.Exit(1)`
   - Otherwise: print source provenance line, then brief content; exit 0

2. **No path and no `--show`**: if `path is None`
   - `err_console.print("[red]Provide a file path, '-' for stdin, or --show[/red]")`
   - `raise typer.Exit(1)`

3. **Normal write branch**: `path` is set
   - Check existing brief: `brief_path = repo_root / ".kittify" / MISSION_BRIEF_FILENAME`
   - If exists and not `--force`: print "Brief already exists at .kittify/mission-brief.md. Use --force to overwrite.", `raise typer.Exit(1)`
   - Read content:
     - If `path == "-"`: `content = sys.stdin.read()`; `source_file = "stdin"`
     - Else: validate file exists, `content = Path(path).read_text(encoding="utf-8")`; `source_file = path`
   - Call `write_mission_brief(repo_root, content, source_file)`
   - Print `"[green]✓[/green] Brief written to .kittify/mission-brief.md"` and `"[green]✓[/green] Provenance written to .kittify/brief-source.yaml"`

**Error handling**:
- File not found: catch `FileNotFoundError`, print helpful message, `raise typer.Exit(1)`
- Read errors: catch `OSError`, print message, `raise typer.Exit(1)`

**Validation**:
- [ ] `mypy --strict src/specify_cli/cli/commands/intake.py` passes

---

### T003 — Register intake in `src/specify_cli/cli/commands/__init__.py`

**Purpose**: Wire the `intake` command into the root CLI app so `spec-kitty intake` resolves correctly.

**File**: `src/specify_cli/cli/commands/__init__.py` (modify)

**Changes** (two edits, both small):

1. Add import in alphabetical order in the import block (after `glossary`, before `implement`):
   ```python
   from . import intake as intake_module
   ```

2. Add registration inside `register_commands()` alongside other standalone commands (keep alphabetical order near `implement`):
   ```python
   app.command()(intake_module.intake)
   ```

**Validation**:
- [ ] `spec-kitty intake --help` prints usage without error
- [ ] `mypy --strict src/specify_cli/cli/commands/__init__.py` passes

---

### T004 — Update `.gitignore`

**Purpose**: Ensure both brief artifacts are gitignored so they never accidentally land in version control.

**File**: `.gitignore` (modify)

Add two lines immediately after the existing `ticket-context.md` and `pending-origin.yaml` block (search for that block to find the right location):

```
.kittify/mission-brief.md
.kittify/brief-source.yaml
```

**Validation**:
- [ ] `git check-ignore -v .kittify/mission-brief.md` returns a match
- [ ] `git check-ignore -v .kittify/brief-source.yaml` returns a match

---

### T005 — Write `tests/specify_cli/test_mission_brief.py`

**Purpose**: Unit-test every public function in `mission_brief.py` using `tmp_path` fixtures. No CLI involved.

**File**: `tests/specify_cli/test_mission_brief.py` (new, ~120 lines)

**Test cases**:

```python
from __future__ import annotations
from pathlib import Path
import pytest
from specify_cli.mission_brief import (
    write_mission_brief, read_mission_brief, read_brief_source, clear_mission_brief,
    MISSION_BRIEF_FILENAME, BRIEF_SOURCE_FILENAME,
)

pytestmark = pytest.mark.fast
```

| Test | Asserts |
|------|---------|
| `test_write_creates_kittify_if_absent` | `.kittify/` created automatically |
| `test_write_brief_content` | `mission-brief.md` contains provenance header + original content |
| `test_write_brief_hash_is_sha256_of_raw_content` | SHA-256 of original content matches `brief_hash` in header and YAML |
| `test_write_source_yaml_fields` | `brief-source.yaml` has `source_file`, `ingested_at`, `brief_hash` |
| `test_write_source_stdin` | `source_file` is `"stdin"` when passed as such |
| `test_read_brief_returns_none_when_absent` | Returns `None` if file missing |
| `test_read_brief_returns_content_when_present` | Returns full file content (header + body) |
| `test_read_source_returns_none_when_absent` | Returns `None` if file missing |
| `test_read_source_returns_dict_when_present` | Returns dict with expected keys |
| `test_clear_removes_both_files` | Both files absent after clear |
| `test_clear_is_idempotent` | No error if files already absent |
| `test_write_twice_overwrites` | Second write replaces first (hash changes) |

**Validation**:
- [ ] `pytest tests/specify_cli/test_mission_brief.py -v` — all tests pass
- [ ] Coverage ≥ 90% on `mission_brief.py`

---

### T006 — Write `tests/specify_cli/cli/commands/test_intake.py`

**Purpose**: Integration-test the `spec-kitty intake` command end-to-end using `CliRunner` against the real app.

**File**: `tests/specify_cli/cli/commands/test_intake.py` (new, ~150 lines)

**Setup pattern** (mirrors existing CLI tests):

```python
from __future__ import annotations
from pathlib import Path
import pytest
from typer.testing import CliRunner
from specify_cli import app

pytestmark = pytest.mark.fast
runner = CliRunner()
```

Because `CliRunner` runs in a temp environment, use `mix_stderr=False` and set `env={"HOME": str(tmp_path)}` or use `monkeypatch.chdir(tmp_path)` to control `Path.cwd()` inside the command.

**Test cases**:

| Test | Invocation | Asserts |
|------|-----------|---------|
| `test_intake_file_writes_artifacts` | `intake PLAN.md` | exit 0, both `.kittify/` files exist |
| `test_intake_file_content_in_brief` | `intake PLAN.md` | original content present in `mission-brief.md` |
| `test_intake_stdin` | `intake -` (with `input=`) | exit 0, source_file is "stdin" |
| `test_intake_force_overwrites` | two `intake` calls with `--force` on second | exit 0, content updated |
| `test_intake_no_force_exits_1` | two `intake` calls, no `--force` | second exits 1, first file unchanged |
| `test_intake_show_prints_brief` | `intake --show` after writing | exit 0, output contains provenance |
| `test_intake_show_no_brief_exits_1` | `intake --show` with no brief | exits 1 |
| `test_intake_missing_file_exits_1` | `intake nonexistent.md` | exits 1, no files written |

**CliRunner stdin pattern**:
```python
result = runner.invoke(app, ["intake", "-"], input="my plan content\n", catch_exceptions=False)
```

**Working directory pattern** — use `monkeypatch` to redirect `Path.cwd()`:
```python
def test_intake_file_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    plan_file = tmp_path / "PLAN.md"
    plan_file.write_text("# My Plan\n\nDo stuff.")
    result = runner.invoke(app, ["intake", str(plan_file)], catch_exceptions=False)
    assert result.exit_code == 0
    assert (tmp_path / ".kittify" / "mission-brief.md").exists()
    assert (tmp_path / ".kittify" / "brief-source.yaml").exists()
```

**Validation**:
- [ ] `pytest tests/specify_cli/cli/commands/test_intake.py -v` — all tests pass
- [ ] `mypy --strict tests/specify_cli/cli/commands/test_intake.py` passes (or `# type: ignore` with justification if test-only)

---

## Definition of Done

- [ ] `src/specify_cli/mission_brief.py` exists, passes `mypy --strict`
- [ ] `src/specify_cli/cli/commands/intake.py` exists, passes `mypy --strict`
- [ ] `spec-kitty intake --help` shows correct usage
- [ ] `spec-kitty intake PLAN.md` writes both `.kittify/` files when run from a real repo
- [ ] `spec-kitty intake PLAN.md` (second run, no `--force`) exits 1 and files unchanged
- [ ] `spec-kitty intake PLAN.md --force` overwrites successfully
- [ ] `spec-kitty intake --show` prints brief + provenance
- [ ] `.gitignore` contains both new entries
- [ ] All unit and integration tests pass
- [ ] No regressions in existing `spec-kitty plan` command (`spec-kitty plan --help` still works)

## Risks

| Risk | Mitigation |
|------|-----------|
| `Path.cwd()` in tests resolves to project root, not `tmp_path` | Use `monkeypatch.chdir(tmp_path)` in every test |
| ruamel.yaml round-trip alters field order in `brief-source.yaml` | Use `yaml.dump(data, ...)` with explicit key ordering; test field presence not exact text |
| stdin read blocks on TTY in interactive use | CliRunner provides `input=` for tests; production stdin is fine for piped use |
| `__init__.py` import order breaks linter | Keep alphabetical order; verify `ruff check` passes after edit |

## Reviewer Guidance

- Verify the provenance header format matches exactly: two HTML comment lines, then blank line, then content
- Verify `brief_hash` in the YAML matches SHA-256 of the *raw* content (before header), not the stored file
- Verify `read_mission_brief` returns `None` (not `""`) when file is absent
- Verify `clear_mission_brief` is idempotent — second call must not raise
- Verify existing `spec-kitty plan` command (`lifecycle_module.plan`) is unaffected by the new registration

## Activity Log

- 2026-04-20T08:18:32Z – claude:sonnet:implementer:implementer – shell_pid=94785 – Assigned agent via action command
- 2026-04-20T08:26:12Z – claude:sonnet:implementer:implementer – shell_pid=94785 – All 6 subtasks implemented and tested: mission_brief.py module, intake CLI command, __init__.py registration, .gitignore entries, unit tests (12 passing), CLI integration tests (8 passing), mypy --strict clean
- 2026-04-20T08:26:47Z – claude:sonnet:reviewer:reviewer – shell_pid=96385 – Started review via action command
- 2026-04-20T08:30:40Z – claude:sonnet:reviewer:reviewer – shell_pid=96385 – Review passed: all acceptance criteria met
