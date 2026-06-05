---
work_package_id: WP02
title: Auto-Commit Wiring, Doctor Ops, and Tests
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- FR-008
- NFR-001
- NFR-003
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-op-records-git-durability-01KTB49K
base_commit: 9299d39ae00f559517100704d98a1a5fa60171f2
created_at: '2026-06-05T06:36:57.778493+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "55376"
history:
- date: '2026-06-05'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/executor.py
- src/specify_cli/doctor/ops.py
- src/specify_cli/cli/commands/doctor.py
- tests/specify_cli/invocation/test_executor.py
- tests/specify_cli/invocation/test_doctor_ops.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

Wait for the profile to load, then proceed.

---

## Objective

1. Wire a git auto-commit in `complete_invocation()` so every completed Op record lands in `kitty-ops/` in git history.
2. Create `src/specify_cli/doctor/ops.py` with `list_orphan_ops()` — detects started-but-not-completed Op files.
3. Wire `spec-kitty doctor ops` as a new subcommand in `doctor.py`.
4. Write tests proving commit, orphan guard, `do`-regression, correlation wiring, and orphan detection.

This is WP02 of 2 for mission `op-records-git-durability-01KTB49K` (issue #1688 Step 1).

**Depends on**: WP01 (storage paths must be `kitty-ops/` before executor tests pass)

**Implement with**: `spec-kitty agent action implement WP02 --agent claude`

---

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- Execute from the lane worktree assigned to WP02.

---

## Context

After WP01, `InvocationWriter` writes to `kitty-ops/`. The executor (`ProfileInvocationExecutor`) calls `write_started()` and `complete_invocation()` for every Op. Currently there is no auto-commit — completed records sit as untracked files.

**Auto-commit invariant**: Only `complete_invocation()` triggers a commit. `write_started()` does not. This is the orphan guard: a session that crashes after `write_started()` but before `complete_invocation()` leaves an untracked file (orphan), never in git history.

**Commit failure policy**: The git commit is best-effort. If it fails (no git config, dirty index, permission error), `complete_invocation()` logs at WARNING and returns normally. The Op record is already on disk — the caller always gets the completed record back.

---

## Subtask T008: Wire git auto-commit in `complete_invocation()`

**File**: `src/specify_cli/invocation/executor.py`

**Where**: Inside `complete_invocation()`, after Step 3 (`write_completed`) and before Step 4 (evidence promotion). Insert as "Step 3a".

**What to add** (approximately):

```python
# Step 3a (NEW FR-002): Auto-commit completed Op record to kitty-ops/.
# Best-effort — failure must not block the invocation response.
self._commit_op_record(invocation_id, completed.profile_id, completed.action or "op")
```

Add a private method `_commit_op_record` to the class:

```python
def _commit_op_record(
    self,
    invocation_id: str,
    profile_id: str,
    action: str,
) -> None:
    """Auto-commit the completed Op JSONL and index to kitty-ops/ in git.

    Uses direct subprocess git — not safe_commit — because:
    - safe_commit requires worktree_root and refuses protected branches (main)
    - Op records are audit artifacts, same class as kitty-specs/ planning artifacts
    - Commit failures are WARNING-logged, never raised (best-effort)
    """
    import logging
    import subprocess

    logger = logging.getLogger(__name__)
    op_id_short = invocation_id[:8]
    message = f"op({profile_id}): {action} [{op_id_short}]"

    op_path = self._writer.invocation_path(invocation_id)
    index_path = self._writer._dir / "ops-index.jsonl"

    # Paths relative to repo_root for git add
    try:
        rel_op = str(op_path.relative_to(self._repo_root))
        rel_idx = str(index_path.relative_to(self._repo_root))
    except ValueError:
        logger.warning("op auto-commit: cannot relativize paths for %s", invocation_id)
        return

    try:
        subprocess.run(
            ["git", "-C", str(self._repo_root), "add", "--", rel_op, rel_idx],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self._repo_root), "commit", "--no-verify", "-m", message],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.warning(
            "op auto-commit failed for %s: %s", invocation_id, exc.stderr.decode(errors="replace")
        )
    except OSError as exc:
        logger.warning("op auto-commit: git not found or failed: %s", exc)
```

**Import note**: `subprocess` and `logging` are stdlib — no new dependencies. `logging` is already imported at the top of `executor.py` via other imports; verify before adding a duplicate import.

**Scope boundary**: Do NOT touch `InvocationSaaSPropagator` or `OfflineQueue`. Do NOT delete or rename any existing method.

---

## Subtask T009: Implement `list_orphan_ops()` in new `doctor/ops.py`

**New file**: `src/specify_cli/doctor/ops.py`

Create this module:

```python
"""Op orphan detection for spec-kitty doctor ops."""

from __future__ import annotations

import json
from pathlib import Path

# Files in kitty-ops/ that are NOT Op records.
_NON_OP_FILENAMES = frozenset({
    "ops-index.jsonl",
    "lifecycle.jsonl",
    "propagation-errors.jsonl",
})


def list_orphan_ops(repo_root: Path) -> list[Path]:
    """Return paths of Op JSONL files in kitty-ops/ that have no 'completed' event.

    An orphan is any <op_id>.jsonl file in kitty-ops/ that:
    - Is not in _NON_OP_FILENAMES (not the index, lifecycle, or error log)
    - Does not contain a line where json.loads(line)["event"] == "completed"

    The file may be untracked (normal for a crashed session) or tracked (abnormal
    but handled gracefully — listed as orphan if no completed event found).
    """
    kitty_ops = repo_root / "kitty-ops"
    if not kitty_ops.is_dir():
        return []

    orphans: list[Path] = []
    for path in sorted(kitty_ops.glob("*.jsonl")):
        if path.name in _NON_OP_FILENAMES:
            continue
        if not _has_completed_event(path):
            orphans.append(path)
    return orphans


def _has_completed_event(path: Path) -> bool:
    """Return True if path contains a line with event == 'completed'."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get("event") == "completed":
                return True
        except json.JSONDecodeError:
            continue
    return False
```

---

## Subtask T010: Wire `spec-kitty doctor ops` CLI subcommand

**File**: `src/specify_cli/cli/commands/doctor.py`

Add a new `@app.command(name="ops")` subcommand. Find the right insertion point:
- Run `grep -n "@app.command\|^def " src/specify_cli/cli/commands/doctor.py | head -30` to orient.
- Insert after the `invocation-pairing` command (around line 1351), which is thematically closest.

**Add the import at the top** (in the `TYPE_CHECKING` block or as a regular import — use lazy import inside the function to avoid circular imports):

```python
# inside the ops() function body:
from specify_cli.doctor.ops import list_orphan_ops
```

**Command implementation**:

```python
@app.command(name="ops")
def doctor_ops(
    json_output: bool = typer.Option(False, "--json/--no-json", help="Output JSON"),
) -> None:
    """List orphan Op records in kitty-ops/ (started but never completed)."""
    from specify_cli.doctor.ops import list_orphan_ops

    repo_root = locate_project_root()
    orphans = list_orphan_ops(repo_root)

    if json_output:
        import json as _json
        typer.echo(_json.dumps({
            "orphan_count": len(orphans),
            "orphans": [str(p.relative_to(repo_root)) for p in orphans],
        }))
        return

    console = Console()
    if not orphans:
        console.print("[green]No orphan Op records found.[/green]")
        return

    console.print(f"[yellow]Found {len(orphans)} orphan Op record(s):[/yellow]")
    for p in orphans:
        console.print(f"  {p.relative_to(repo_root)}")
```

**Finding `locate_project_root`**: It is already imported at the top of `doctor.py` (line 23: `from specify_cli.core.paths import locate_project_root`). Do not add a duplicate import.

---

## Subtask T011: Add executor commit tests (T-003, T-004, T-005)

**File**: `tests/specify_cli/invocation/test_executor.py`

These tests require a **real git repo fixture**. Add a fixture or helper:

```python
import subprocess
from pathlib import Path
import pytest

@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo in tmp_path."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True, capture_output=True)
    # Create initial commit so HEAD exists
    (tmp_path / "README.md").write_text("init")
    subprocess.run(["git", "-C", str(tmp_path), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "init"], check=True, capture_output=True)
    return tmp_path
```

### Test T-003: Commit appears in git log after `complete_invocation()`

```python
def test_complete_invocation_creates_git_commit(git_repo: Path) -> None:
    """FR-002/FR-003: complete_invocation() auto-commits to kitty-ops/."""
    executor = _make_executor(git_repo)
    payload = executor.invoke("test request", profile_hint="some-profile", actor="claude")
    executor.complete_invocation(payload.invocation_id, outcome="done")

    result = subprocess.run(
        ["git", "-C", str(git_repo), "log", "--oneline", "kitty-ops/"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip(), "Expected at least one commit touching kitty-ops/"
    # Commit message should match op(...) pattern
    assert f"op(" in result.stdout
```

### Test T-004: Op record restorable after git clean (NFR-001)

```python
def test_completed_op_restorable_after_clean(git_repo: Path) -> None:
    """NFR-001: committed Op record survives git clean + checkout."""
    executor = _make_executor(git_repo)
    payload = executor.invoke("test", profile_hint="some-profile", actor="claude")
    executor.complete_invocation(payload.invocation_id, outcome="done")

    op_path = git_repo / "kitty-ops" / f"{payload.invocation_id}.jsonl"
    assert op_path.exists()

    # Simulate git clean + restore
    subprocess.run(["git", "-C", str(git_repo), "rm", "--force", "-r", "kitty-ops/"],
                   capture_output=True)
    subprocess.run(["git", "-C", str(git_repo), "checkout", "HEAD", "--", "kitty-ops/"],
                   check=True, capture_output=True)

    assert op_path.exists(), "Op record must be restorable from git history"
```

### Test T-005: Orphan Op is NOT committed

```python
def test_orphan_op_not_in_git_log(git_repo: Path) -> None:
    """FR-004: Op without completed event must NOT be in git history."""
    executor = _make_executor(git_repo)
    # invoke() writes the started event — do NOT call complete_invocation()
    payload = executor.invoke("test", profile_hint="some-profile", actor="claude")

    result = subprocess.run(
        ["git", "-C", str(git_repo), "log", "--oneline", "kitty-ops/"],
        capture_output=True, text=True, check=True,
    )
    # No commit should reference this invocation
    assert payload.invocation_id[:8] not in result.stdout, \
        "Orphan Op must not appear in git log"

    # But the file should exist as an untracked file
    op_path = git_repo / "kitty-ops" / f"{payload.invocation_id}.jsonl"
    assert op_path.exists(), "Orphan Op file should exist as untracked"
```

**Note on `_make_executor`**: This is a helper that constructs `ProfileInvocationExecutor` with a real `ProfileRegistry` and `ActionRouter`. Look at existing tests in `test_executor.py` to reuse the pattern they already use.

---

## Subtask T012: Add `do`-regression test (T-006) and correlation wiring test (T-007)

**File**: `tests/specify_cli/invocation/test_executor.py` (same file as T011)

### Test T-006: `do` command produces a durable commit (regression guard)

```python
def test_do_command_produces_git_commit(git_repo: Path) -> None:
    """FR-008: do command (zero-propagator executor) writes and commits Op record."""
    # Replicate do_cmd._build_executor: executor WITHOUT a propagator
    from specify_cli.invocation.executor import ProfileInvocationExecutor
    from specify_cli.invocation.registry import ProfileRegistry
    from specify_cli.invocation.router import ActionRouter

    registry = ProfileRegistry(git_repo)
    router = ActionRouter(registry)
    executor = ProfileInvocationExecutor(git_repo, router=router)  # no propagator

    payload = executor.invoke("do something", actor="operator")
    executor.complete_invocation(payload.invocation_id, outcome="done")

    result = subprocess.run(
        ["git", "-C", str(git_repo), "log", "--oneline", "kitty-ops/"],
        capture_output=True, text=True, check=True,
    )
    assert "op(" in result.stdout, "do executor must produce a git commit"
```

### Test T-007: `mission_id`/`wp_id` are null for standalone; populated when passed

```python
def test_mission_correlation_fields_null_for_standalone() -> None:
    """FR-006/FR-007: standalone invocations have null mission_id and wp_id."""
    from specify_cli.invocation.record import InvocationRecord
    record = InvocationRecord(
        event="started",
        invocation_id="01KTB49KJKRJ71YR8KERVDMHHA",
        profile_id="p",
        action="a",
    )
    assert record.mission_id is None
    assert record.wp_id is None


def test_mission_correlation_fields_populated_when_set() -> None:
    """FR-007: mission_id and wp_id are preserved when passed."""
    from specify_cli.invocation.record import InvocationRecord
    record = InvocationRecord(
        event="started",
        invocation_id="01KTB49KJKRJ71YR8KERVDMHHA",
        profile_id="p",
        action="a",
        mission_id="01ABCDEFGHIJKLMNOPQRSTUVWX",
        wp_id="WP01",
    )
    assert record.mission_id == "01ABCDEFGHIJKLMNOPQRSTUVWX"
    assert record.wp_id == "WP01"
```

---

## Subtask T013: Create `test_doctor_ops.py`

**New file**: `tests/specify_cli/invocation/test_doctor_ops.py`

```python
"""Tests for spec-kitty doctor ops orphan detection (FR-005)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.doctor.ops import list_orphan_ops


class TestListOrphanOps:
    def test_empty_kitty_ops_returns_no_orphans(self, tmp_path: Path) -> None:
        (tmp_path / "kitty-ops").mkdir()
        assert list_orphan_ops(tmp_path) == []

    def test_missing_kitty_ops_returns_no_orphans(self, tmp_path: Path) -> None:
        assert list_orphan_ops(tmp_path) == []

    def test_completed_op_not_in_orphan_list(self, tmp_path: Path) -> None:
        kitty_ops = tmp_path / "kitty-ops"
        kitty_ops.mkdir()
        op_file = kitty_ops / "01ABCDEF12345678901234.jsonl"
        op_file.write_text(
            json.dumps({"event": "started", "invocation_id": "01ABCDEF12345678901234"}) + "\n" +
            json.dumps({"event": "completed", "invocation_id": "01ABCDEF12345678901234"}) + "\n"
        )
        assert list_orphan_ops(tmp_path) == []

    def test_started_only_op_is_orphan(self, tmp_path: Path) -> None:
        kitty_ops = tmp_path / "kitty-ops"
        kitty_ops.mkdir()
        op_file = kitty_ops / "01ABCDEF12345678901234.jsonl"
        op_file.write_text(
            json.dumps({"event": "started", "invocation_id": "01ABCDEF12345678901234"}) + "\n"
        )
        orphans = list_orphan_ops(tmp_path)
        assert orphans == [op_file]

    def test_non_op_files_excluded(self, tmp_path: Path) -> None:
        kitty_ops = tmp_path / "kitty-ops"
        kitty_ops.mkdir()
        for name in ("ops-index.jsonl", "lifecycle.jsonl", "propagation-errors.jsonl"):
            (kitty_ops / name).write_text("{}\n")
        assert list_orphan_ops(tmp_path) == []

    def test_multiple_orphans_returned_sorted(self, tmp_path: Path) -> None:
        kitty_ops = tmp_path / "kitty-ops"
        kitty_ops.mkdir()
        for inv_id in ("01AAAAAA00000000000000", "01BBBBBB00000000000000"):
            (kitty_ops / f"{inv_id}.jsonl").write_text(
                json.dumps({"event": "started", "invocation_id": inv_id}) + "\n"
            )
        orphans = list_orphan_ops(tmp_path)
        assert len(orphans) == 2
        # Should be sorted (list_orphan_ops uses sorted())
        assert orphans[0].name < orphans[1].name


class TestDoctorOpsCLI:
    """Integration tests: exercise `spec-kitty doctor ops` via the typer CLI surface (FR-005, charter)."""

    def _get_app(self):
        from specify_cli.cli.commands.doctor import app
        return app

    def test_no_orphans_exits_zero_with_message(self, tmp_path: Path, monkeypatch) -> None:
        """CLI reports clean when kitty-ops/ has no orphans."""
        (tmp_path / "kitty-ops").mkdir()
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(self._get_app(), ["ops"])
        assert result.exit_code == 0
        assert "No orphan" in result.output

    def test_orphan_listed_in_cli_output(self, tmp_path: Path, monkeypatch) -> None:
        """CLI lists orphan file path when one exists."""
        kitty_ops = tmp_path / "kitty-ops"
        kitty_ops.mkdir()
        (kitty_ops / "01ABCDEF12345678901234.jsonl").write_text(
            json.dumps({"event": "started", "invocation_id": "01ABCDEF12345678901234"}) + "\n"
        )
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(self._get_app(), ["ops"])
        assert result.exit_code == 0
        assert "01ABCDEF12345678901234.jsonl" in result.output

    def test_json_output_flag(self, tmp_path: Path, monkeypatch) -> None:
        """--json flag produces parseable JSON with orphan_count and orphans keys."""
        (tmp_path / "kitty-ops").mkdir()
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(self._get_app(), ["ops", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "orphan_count" in data
        assert "orphans" in data
        assert data["orphan_count"] == 0
```

**Note on `monkeypatch.chdir`**: The `doctor ops` command calls `locate_project_root()` which walks up from CWD. Using `monkeypatch.chdir(tmp_path)` plus an empty `.kittify/` sentinel (if required by `locate_project_root`) may be needed. Check `locate_project_root`'s behavior for the `tmp_path` fixture — if it requires a `.kittify/` dir or `.git/`, create one in the fixture.

---

## Subtask T014: Add CHANGELOG entry for `.kittify/events/` abandonment

**File**: `CHANGELOG.md` (repository root)

Per spec.md C-002 and Assumptions: add a CHANGELOG entry documenting the accepted data loss.

Find the `[Unreleased]` section (or the current version section) and add:

```markdown
### Changed

- Op records now stored in `kitty-ops/` (git-tracked) instead of `.kittify/events/profile-invocations/` (gitignored).
  **Note**: Pre-existing records in `.kittify/events/profile-invocations/` are abandoned and not migrated. This is accepted data loss — those records were ephemeral by design prior to this change.
```

**Validation**: `grep -n "kitty-ops" CHANGELOG.md` must return at least one line after this change.

---

## Definition of Done

- [ ] `complete_invocation()` calls `_commit_op_record()` after `write_completed()` succeeds
- [ ] `_commit_op_record()` uses direct subprocess git; errors are `logger.warning`, not raised
- [ ] Commit message matches `op(<profile_id>): <action> [<op_id[:8]>]`
- [ ] `src/specify_cli/doctor/ops.py` exists with `list_orphan_ops()` and `_has_completed_event()`
- [ ] `spec-kitty doctor ops` subcommand is registered in `doctor.py`
- [ ] `pytest tests/specify_cli/invocation/test_executor.py` passes (including T-003, T-004, T-005, T-006, T-007)
- [ ] `pytest tests/specify_cli/invocation/test_doctor_ops.py` passes (6 unit tests + 3 CLI integration tests)
- [ ] `mypy --strict src/specify_cli/invocation/executor.py src/specify_cli/doctor/ops.py` passes
- [ ] `CHANGELOG.md` updated with `.kittify/events/` abandonment note
- [ ] `InvocationSaaSPropagator` is unchanged (scope boundary)
- [ ] No `.gitignore` changes made

---

## Risks

| Risk | Mitigation |
|------|-----------|
| `doctor.py` is 3000+ lines — wrong insertion point | Use `grep -n "@app.command" src/specify_cli/cli/commands/doctor.py` to find `invocation-pairing` (~line 1351), insert `ops` immediately after |
| `subprocess` already imported? | Check with `grep -n "import subprocess" src/specify_cli/invocation/executor.py`; add import only if missing |
| T-003/T-004 need a profile fixture in `git_repo` | `ProfileRegistry` may fail in empty `tmp_path` with no profiles. Use `pytest.mark.skip` or mock the registry if profiles don't load. Check existing `test_executor.py` for how profiles are mocked. |
| `--no-verify` in commit may be unexpected | This skips pre-commit hooks in the user's repo. If that's a concern, use `--no-verify` only when an env var is set, or omit it. The simplest default is to include it since Op commits are internal bookkeeping. |

---

## Reviewer Guidance

- Verify `complete_invocation()` step numbering: 3a must appear between step 3 and step 4 (evidence promotion)
- Confirm `_commit_op_record` never raises — only `logger.warning`
- Confirm `ops` command appears in `doctor.py` via `spec-kitty doctor --help` output
- Check `test_doctor_ops.py` covers the `_NON_OP_FILENAMES` exclusion set
- Confirm `test_executor.py` T-005 asserts the file EXISTS as untracked (not deleted)

## Activity Log

- 2026-06-05T06:37:01Z – claude:sonnet:python-pedro:implementer – shell_pid=55376 – Assigned agent via action command
