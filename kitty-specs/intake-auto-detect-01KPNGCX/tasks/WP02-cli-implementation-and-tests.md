---
work_package_id: WP02
title: CLI Implementation & Tests
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-intake-auto-detect-01KPNGCX
base_commit: a42b7699392e55c425edc005acc3bb7a10137ffc
created_at: '2026-04-20T13:38:37.193634+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
shell_pid: "76069"
agent: "claude:sonnet:reviewer:reviewer"
history:
- date: '2026-04-20'
  author: spec-kitty.tasks
  note: Initial WP created
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- src/specify_cli/mission_brief.py
- src/specify_cli/cli/commands/intake.py
- tests/specify_cli/test_intake_sources.py
- tests/specify_cli/cli/commands/test_intake.py
tags: []
---

# WP02 — CLI Implementation & Tests

**Mission**: intake-auto-detect-01KPNGCX  
**Issue**: Priivacy-ai/spec-kitty#703  
**Depends on**: WP01 (needs `intake_sources.py` and `scan_for_plans` to exist)

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- Execution worktree is allocated per computed lane from `lanes.json` after `finalize-tasks`.
- Enter your workspace with: `spec-kitty agent action implement WP02 --agent <name>`

## Objective

Wire `--auto` into `spec-kitty intake`, extend `write_mission_brief()` to support a `source_agent` field in `brief-source.yaml`, and add comprehensive test coverage for all `--auto` scenarios.

## Context

WP01 delivered `src/specify_cli/intake_sources.py` with `HARNESS_PLAN_SOURCES` and `scan_for_plans()`. This WP consumes those. Read WP01's output before starting.

Existing files to read before modifying:
- `src/specify_cli/cli/commands/intake.py` — current `intake()` function
- `src/specify_cli/mission_brief.py` — `write_mission_brief()` signature and `source_data` dict construction

The existing `intake()` function handles `--show`, explicit path, and stdin. This WP adds `--auto` as a fourth mode. The existing modes must remain unchanged.

---

## Subtask T005 — Extend `write_mission_brief()` with Optional `source_agent` Kwarg

**Purpose**: Allow `--auto` ingestion to record which harness produced the plan in `brief-source.yaml`, without breaking existing callers.

**File**: `src/specify_cli/mission_brief.py`

**Change**: Add `source_agent: str | None = None` as a keyword-only parameter:

```python
def write_mission_brief(
    repo_root: Path,
    content: str,
    source_file: str,
    *,
    source_agent: str | None = None,
) -> tuple[Path, Path]:
```

**`source_data` dict construction** (conditional inclusion — do NOT write `null`):

```python
source_data: dict[str, str] = {
    "source_file": source_file,
    "ingested_at": ingested_at,
    "brief_hash": brief_hash,
}
if source_agent is not None:
    source_data["source_agent"] = source_agent
```

**Why `*` before `source_agent`**: Makes `source_agent` keyword-only. Existing call sites — `write_mission_brief(repo_root, content, source_file)` — compile and run without change. This is not merely nice-to-have: existing callers must not need modification.

**YAML output behavior**:
- `write_mission_brief(repo_root, content, "PLAN.md")` → `brief-source.yaml` contains `source_file`, `ingested_at`, `brief_hash` only
- `write_mission_brief(repo_root, content, "PLAN.md", source_agent="claude-code")` → `brief-source.yaml` also contains `source_agent: claude-code`

**Validation**:
- [ ] `ruff check src/specify_cli/mission_brief.py` passes
- [ ] Existing call in `intake.py` compiles without modification (verify this)
- [ ] When `source_agent=None`: `brief-source.yaml` has no `source_agent` key (not even `source_agent: null`)
- [ ] When `source_agent="claude-code"`: `brief-source.yaml` has `source_agent: claude-code`

---

## Subtask T006 — Add `--auto` Flag and Mutual Exclusion Guard

**Purpose**: Register the `--auto` flag with Typer and enforce it is mutually exclusive with a positional path argument.

**File**: `src/specify_cli/cli/commands/intake.py`

**Function signature addition**:
```python
def intake(
    path: str | None = typer.Argument(
        None,
        help="Path to plan document, or '-' to read from stdin. Omit when using --show or --auto.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing brief."),
    show: bool = typer.Option(False, "--show", help="Print current brief and provenance; no writes."),
    auto: bool = typer.Option(False, "--auto", help="Scan known harness plan locations and ingest automatically."),
) -> None:
```

**Mutual exclusion guard** (add immediately after the `--show` guard block, before any file I/O):
```python
if path is not None and auto:
    err_console.print("[red]--auto cannot be combined with a positional path argument.[/red]")
    raise typer.Exit(1)
```

**Import to add** at top of file:
```python
from specify_cli.intake_sources import scan_for_plans
```

**Placement in function body**:
```
1. --show guard (existing)
2. --auto + path mutual exclusion guard  ← NEW (T006)
3. --auto branch                         ← NEW (T007, T008, T009)
4. No path and no --show: usage hint (existing — but now also "or --auto")
5. Normal write branch (existing)
```

**Validation**:
- [ ] `spec-kitty intake --help` shows `--auto` in output
- [ ] `spec-kitty intake PLAN.md --auto` exits 1 with usage error (no file written)
- [ ] `ruff check src/specify_cli/cli/commands/intake.py` passes

---

## Subtask T007 — Implement 0-Match Path

**Purpose**: When `--auto` finds no plan files, print a friendly message and exit 1.

**File**: `src/specify_cli/cli/commands/intake.py`

**Code** (inside the `if auto:` block):
```python
if auto:
    candidates = scan_for_plans(Path.cwd())

    if not candidates:
        err_console.print(
            "No plan document detected in known harness locations.\n"
            "Pass a path explicitly: spec-kitty intake <path>"
        )
        raise typer.Exit(1)

    # ... T008 / T009 continue here
```

**Validation**:
- [ ] Running `spec-kitty intake --auto` in a directory with no matching files exits 1
- [ ] The error message is on stderr (uses `err_console`)
- [ ] No `.kittify/` files are created

---

## Subtask T008 — Implement 1-Match Path

**Purpose**: When exactly one plan file is found, ingest it automatically and print a confirmation.

**File**: `src/specify_cli/cli/commands/intake.py`

**Code** (continuation of the `if auto:` block):
```python
    if len(candidates) == 1:
        found_path, harness_key, source_agent_value = candidates[0]
        console.print(f"BRIEF DETECTED: {found_path} (source: {harness_key})")

        brief_path = repo_root / ".kittify" / MISSION_BRIEF_FILENAME
        if brief_path.exists() and not force:
            err_console.print(
                "Brief already exists at .kittify/mission-brief.md. Use --force to overwrite."
            )
            raise typer.Exit(1)

        try:
            content = found_path.read_text(encoding="utf-8")
        except OSError as exc:
            err_console.print(f"[red]Could not read file: {exc}[/red]")
            raise typer.Exit(1) from None

        write_mission_brief(repo_root, content, str(found_path), source_agent=source_agent_value)
        console.print("[green]✓[/green] Brief written to .kittify/mission-brief.md")
        console.print("[green]✓[/green] Provenance written to .kittify/brief-source.yaml")
        return
```

**Key details**:
- `source_file` passed to `write_mission_brief` is `str(found_path)` — the absolute path string
- `source_agent=source_agent_value` — may be `None` for generic fallback entries (field will be omitted from YAML)
- `--force` check mirrors the existing explicit-path branch

**Validation**:
- [ ] Single matching file → output includes `BRIEF DETECTED: <path> (source: <harness>)`
- [ ] `.kittify/mission-brief.md` is written
- [ ] `.kittify/brief-source.yaml` contains `source_agent: <harness>` when source_agent_value is non-None
- [ ] Existing brief + no `--force` → exits 1 with "already exists" message, nothing overwritten
- [ ] Existing brief + `--force` → brief overwritten, exits 0

---

## Subtask T009 — Implement 2+-Match Path

**Purpose**: When multiple plan files are found, show candidates. On a TTY, prompt for a selection. On non-TTY stdin, exit 1 with the list on stderr.

**File**: `src/specify_cli/cli/commands/intake.py`

**Code** (continuation of the `if auto:` block):
```python
    # Multiple candidates
    import sys

    err_console.print("Found multiple plan documents. Which should I use?")
    for idx, (found_path, harness_key, _) in enumerate(candidates, start=1):
        err_console.print(f"  {idx}. {found_path}  ({harness_key})")

    if not sys.stdin.isatty():
        err_console.print("\nNon-interactive stdin — pass a path explicitly: spec-kitty intake <path>")
        raise typer.Exit(1)

    # TTY: prompt for selection
    selection_str = typer.prompt("Enter number")
    try:
        selection = int(selection_str)
        if not 1 <= selection <= len(candidates):
            raise ValueError
    except ValueError:
        err_console.print(f"[red]Invalid selection. Enter a number between 1 and {len(candidates)}.[/red]")
        raise typer.Exit(1)

    found_path, harness_key, source_agent_value = candidates[selection - 1]
    console.print(f"BRIEF DETECTED: {found_path} (source: {harness_key})")

    brief_path = repo_root / ".kittify" / MISSION_BRIEF_FILENAME
    if brief_path.exists() and not force:
        err_console.print(
            "Brief already exists at .kittify/mission-brief.md. Use --force to overwrite."
        )
        raise typer.Exit(1)

    try:
        content = found_path.read_text(encoding="utf-8")
    except OSError as exc:
        err_console.print(f"[red]Could not read file: {exc}[/red]")
        raise typer.Exit(1) from None

    write_mission_brief(repo_root, content, str(found_path), source_agent=source_agent_value)
    console.print("[green]✓[/green] Brief written to .kittify/mission-brief.md")
    console.print("[green]✓[/green] Provenance written to .kittify/brief-source.yaml")
    return
```

**Import note**: `import sys` is already at the top of the module. If it isn't, add it there — do not add a local import inside the function body.

**Validation**:
- [ ] Multiple matching files → candidate list printed to stderr
- [ ] Non-TTY stdin → exits 1 without prompting
- [ ] TTY stdin, valid selection → correct file ingested
- [ ] TTY stdin, invalid number → exits 1 with error
- [ ] TTY stdin, out-of-range number → exits 1 with error

---

## Subtask T010 — Write `tests/specify_cli/test_intake_sources.py`

**Purpose**: Unit tests for `scan_for_plans()` and `HARNESS_PLAN_SOURCES` structure.

**File**: `tests/specify_cli/test_intake_sources.py` (new file)

**Test cases**:

```python
"""Unit tests for specify_cli.intake_sources."""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.intake_sources import HARNESS_PLAN_SOURCES, scan_for_plans


class TestHarnessPlanSources:
    def test_list_is_defined(self):
        assert isinstance(HARNESS_PLAN_SOURCES, list)

    def test_all_entries_have_correct_shape(self):
        for entry in HARNESS_PLAN_SOURCES:
            harness_key, source_agent_value, candidate_paths = entry
            assert isinstance(harness_key, str) and harness_key
            assert source_agent_value is None or isinstance(source_agent_value, str)
            assert isinstance(candidate_paths, list) and candidate_paths

    def test_no_overlapping_candidate_paths(self):
        """No path string should appear in two different harness entries."""
        seen: set[str] = set()
        for _, _, paths in HARNESS_PLAN_SOURCES:
            for p in paths:
                assert p not in seen, f"Duplicate path {p!r} in HARNESS_PLAN_SOURCES"
                seen.add(p)


class TestScanForPlans:
    def test_empty_dir_returns_empty(self, tmp_path: Path):
        assert scan_for_plans(tmp_path) == []

    def test_nonexistent_dir_returns_empty(self):
        assert scan_for_plans(Path("/nonexistent/path/does/not/exist")) == []

    def test_finds_file_matching_first_active_entry(self, tmp_path: Path, monkeypatch):
        """Create a file at a candidate path; verify it appears in results."""
        if not HARNESS_PLAN_SOURCES:
            pytest.skip("No active entries in HARNESS_PLAN_SOURCES")

        harness_key, source_agent_value, candidate_paths = HARNESS_PLAN_SOURCES[0]
        target = tmp_path / candidate_paths[0]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Test Plan", encoding="utf-8")

        results = scan_for_plans(tmp_path)
        assert len(results) == 1
        found_path, found_key, found_agent = results[0]
        assert found_path == target
        assert found_key == harness_key
        assert found_agent == source_agent_value

    def test_directory_at_candidate_path_is_skipped(self, tmp_path: Path, monkeypatch):
        """A directory at a candidate path must not appear in results."""
        if not HARNESS_PLAN_SOURCES:
            pytest.skip("No active entries in HARNESS_PLAN_SOURCES")

        _, _, candidate_paths = HARNESS_PLAN_SOURCES[0]
        target = tmp_path / candidate_paths[0]
        target.mkdir(parents=True, exist_ok=True)  # directory, not file

        results = scan_for_plans(tmp_path)
        assert results == []

    def test_returns_multiple_matches_in_order(self, tmp_path: Path):
        """Patch HARNESS_PLAN_SOURCES to have two entries, create both files."""
        from unittest.mock import patch

        mock_sources = [
            ("harness-a", "agent-a", ["plan-a.md"]),
            ("harness-b", "agent-b", ["plan-b.md"]),
        ]
        (tmp_path / "plan-a.md").write_text("A", encoding="utf-8")
        (tmp_path / "plan-b.md").write_text("B", encoding="utf-8")

        with patch("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", mock_sources):
            results = scan_for_plans(tmp_path)

        assert len(results) == 2
        assert results[0][1] == "harness-a"
        assert results[1][1] == "harness-b"

    def test_no_exception_on_permission_error(self, tmp_path: Path, monkeypatch):
        """scan_for_plans must not propagate PermissionError."""
        from unittest.mock import patch, MagicMock

        mock_sources = [("harness-x", "agent-x", ["secret.md"])]
        mock_path = MagicMock(spec=Path)
        mock_path.__truediv__ = lambda self, other: mock_path
        mock_path.is_file = MagicMock(side_effect=PermissionError("denied"))

        with patch("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", mock_sources):
            # Should not raise
            results = scan_for_plans(tmp_path)
        assert results == []
```

**Validation**:
- [ ] `pytest tests/specify_cli/test_intake_sources.py -v` passes
- [ ] `ruff check tests/specify_cli/test_intake_sources.py` passes

---

## Subtask T011 — Write `tests/specify_cli/cli/commands/test_intake.py`

**Purpose**: CLI integration tests for all `--auto` scenarios using `typer.testing.CliRunner` + `tmp_path`.

**File**: `tests/specify_cli/cli/commands/test_intake.py` (new file)

**Setup pattern**:
```python
"""Tests for spec-kitty intake --auto."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

# The intake command is registered on the main app; import the app:
from specify_cli.cli.app import app  # adjust import if needed


runner = CliRunner()


def _invoke(args: list[str], cwd: Path | None = None) -> ...:
    """Helper: invoke intake with optional CWD patching."""
    # CliRunner doesn't change cwd; patch Path.cwd() to return tmp_path
    if cwd is not None:
        with patch("specify_cli.cli.commands.intake.Path.cwd", return_value=cwd), \
             patch("specify_cli.cli.commands.intake._resolve_repo_root", return_value=cwd):
            return runner.invoke(app, ["intake"] + args, catch_exceptions=False)
    return runner.invoke(app, ["intake"] + args, catch_exceptions=False)
```

**Test cases to cover**:

```python
class TestAutoSingleMatch:
    def test_single_match_exits_0(self, tmp_path):
        """--auto with one matching file ingests it and exits 0."""
        ...  # Create a file matching the first active entry; assert exit_code == 0

    def test_single_match_prints_brief_detected(self, tmp_path):
        ...  # Assert "BRIEF DETECTED" in output

    def test_single_match_writes_brief(self, tmp_path):
        ...  # Assert .kittify/mission-brief.md exists after invocation

    def test_single_match_writes_source_agent(self, tmp_path):
        """brief-source.yaml contains source_agent when --auto used."""
        ...  # Parse YAML and assert 'source_agent' key present

    def test_single_match_no_force_blocks_overwrite(self, tmp_path):
        """--auto without --force refuses to overwrite existing brief."""
        ...  # Create brief, run --auto, assert exit_code == 1 and brief unchanged

    def test_single_match_with_force_overwrites(self, tmp_path):
        """--auto --force overwrites existing brief."""
        ...  # Create stale brief, run --auto --force, assert new content written


class TestAutoNoMatch:
    def test_no_match_exits_1(self, tmp_path):
        ...

    def test_no_match_prints_guidance(self, tmp_path):
        ...  # Assert "No plan document detected" in output

    def test_no_match_writes_nothing(self, tmp_path):
        ...  # Assert .kittify/ does not exist


class TestAutoMultipleMatches:
    def test_multiple_matches_non_tty_exits_1(self, tmp_path):
        """Non-TTY stdin with multiple matches exits 1."""
        # CliRunner stdin is a StringIO → isatty() returns False
        ...

    def test_multiple_matches_non_tty_prints_candidates(self, tmp_path):
        ...

    def test_multiple_matches_tty_prompts_and_ingests(self, tmp_path):
        """TTY stdin: mock isatty=True, provide selection input."""
        with patch("sys.stdin.isatty", return_value=True):
            result = runner.invoke(app, ["intake", "--auto"], input="1\n", ...)
        ...


class TestAutoMutualExclusion:
    def test_auto_with_path_exits_1(self, tmp_path):
        result = runner.invoke(app, ["intake", "PLAN.md", "--auto"])
        assert result.exit_code == 1

    def test_auto_with_path_writes_nothing(self, tmp_path):
        ...


class TestManualIntakeUnchanged:
    def test_manual_intake_has_no_source_agent(self, tmp_path):
        """Explicit path intake must NOT write source_agent to brief-source.yaml."""
        plan = tmp_path / "PLAN.md"
        plan.write_text("# Plan", encoding="utf-8")
        _invoke(["str(plan)", "--force"], cwd=tmp_path)  # actual invocation
        source = yaml.safe_load((tmp_path / ".kittify" / "brief-source.yaml").read_text())
        assert "source_agent" not in source

    def test_show_still_works(self, tmp_path):
        """--show flag is unaffected by --auto changes."""
        ...
```

**Notes on mocking `scan_for_plans`**: For most tests, create real files in `tmp_path` and let the real scan run. For the multiple-match tests, you may also patch `specify_cli.cli.commands.intake.scan_for_plans` to return a controlled two-item list. Choose whichever approach gives the clearest test.

**Notes on import path**: Find the actual app import by checking `src/specify_cli/cli/app.py` or wherever `intake` is registered. Adjust `from specify_cli.cli.app import app` accordingly.

**Validation**:
- [ ] `pytest tests/specify_cli/cli/commands/test_intake.py -v` passes (all test classes)
- [ ] `ruff check tests/specify_cli/cli/commands/test_intake.py` passes
- [ ] Every scenario from spec FR-006 through FR-015 has at least one test

---

## Definition of Done

- [ ] `ruff check src/specify_cli/mission_brief.py src/specify_cli/cli/commands/intake.py` passes
- [ ] `pytest tests/specify_cli/test_intake_sources.py tests/specify_cli/cli/commands/test_intake.py -v` — all green
- [ ] `spec-kitty intake --help` shows `--auto` flag
- [ ] `brief-source.yaml` produced by manual intake has no `source_agent` key
- [ ] `brief-source.yaml` produced by `--auto` has `source_agent` key
- [ ] Existing `spec-kitty intake <path>` behavior unchanged (run any existing tests to verify)
- [ ] No changes to files outside `owned_files`

## Risks

| Risk | Mitigation |
|------|-----------|
| Typer's CliRunner sets stdin to StringIO → `isatty()` returns False | This is the desired default for tests; mock `sys.stdin.isatty` → True for TTY-path tests |
| `Path.cwd()` inside `intake()` returns real CWD in tests | Patch `specify_cli.cli.commands.intake.Path.cwd` to return `tmp_path` |
| `_resolve_repo_root()` walks up from CWD looking for git root | Patch `_resolve_repo_root` to return `tmp_path` in tests |
| `import sys` already present vs. added inside function | Check existing imports; add at module level if missing, do NOT add inside function |

## Reviewer Guidance

- Verify that `brief-source.yaml` for a manual intake has no `source_agent` key at all (not even `null`)
- Verify that `spec-kitty intake PLAN.md --auto` exits 1 before doing any file I/O
- Check that the `--show` path is not affected: run `--show` and confirm output is unchanged
- Run `spec-kitty intake --help` and confirm `--auto` appears
- Check `ruff check` and `pytest` both pass before approving

## Activity Log

- 2026-04-20T13:38:38Z – claude:sonnet:implementer:implementer – shell_pid=72247 – Assigned agent via action command
- 2026-04-20T13:46:48Z – claude:sonnet:implementer:implementer – shell_pid=72247 – Ready for review: --auto flag implemented with all 3 result branches, source_agent in brief-source.yaml, full test coverage
- 2026-04-20T13:47:28Z – claude:sonnet:reviewer:reviewer – shell_pid=76069 – Started review via action command
