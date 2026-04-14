---
work_package_id: WP01
title: Commit-Layer Data-Loss Backstop in safe_commit
dependencies: []
requirement_refs:
- FR-011
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-legacy-sparse-and-review-lock-hardening-01KP54ZW
base_commit: b8d27a7b0990cc0451446b2c1f21ce6ffb322913
created_at: '2026-04-14T05:47:57.288577+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 0 — Data-loss foundation
shell_pid: "52930"
agent: "claude:sonnet-4.6:implementer:implementer"
history:
- timestamp: '2026-04-14T05:26:49Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/git/commit_helpers.py
execution_mode: code_change
mission_id: 01KP54ZWEEPCC2VC3YKRX1HT8W
owned_files:
- src/specify_cli/git/commit_helpers.py
- tests/unit/git/test_commit_helpers_backstop.py
- tests/integration/git/test_safe_commit_backstop.py
tags: []
wp_code: WP01
---

# Work Package Prompt: WP01 — Commit-Layer Data-Loss Backstop in `safe_commit`

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent <your-agent-name> --mission 01KP54ZW
```

No `--base` flag needed — this WP has no dependencies.

---

## Branch Strategy

- **Planning branch**: `main`
- **Final merge target**: `main`
- The execution worktree is allocated per lane by `finalize-tasks`. Resolve the actual path and branch from `lanes.json` at runtime; do not reconstruct it.

---

## Objective

Install a defence inside the shared `safe_commit` helper that **cannot be bypassed** and protects every current and future caller against the silent-data-loss pattern documented in Priivacy-ai/spec-kitty#588. The commit layer is the universal backstop across the four-layer architecture described in the mission spec.

After this WP lands, no `safe_commit` invocation can sweep sparse-excluded phantom deletions (or any other unexpected staged content) into a commit — regardless of which CLI command called it or why the staging area contains the unexpected path.

---

## Context

- The failure mode: `git stash` / `git stash pop` inside `safe_commit` interacts with `skip-worktree` bits when `HEAD` is ahead of the working tree. Sparse-excluded paths end up staged as deletions. The next commit sweeps them.
- Kent's `main` at `kg-automation` absorbed a 243-line reversion from mission 023's merge (`84bf7b6`) this way. A second reproduction on mission 025 was caught pre-commit, confirming the cascade is deterministic.
- Constraints from the mission spec: FR-011 (backstop), FR-012 (not bypassable by `--force`), C-005 (must live in `safe_commit` so every caller inherits it), C-007 (commit-time backstop protects data regardless of configuration — the `--allow-sparse-checkout` override must NOT disable it).

---

## Subtask Guidance

### T001 — Add `UnexpectedStagedPath` and `SafeCommitBackstopError` types

**Files**: `src/specify_cli/git/commit_helpers.py`

**What**: Add two new types at the top of the module (before the existing `safe_commit` function).

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class UnexpectedStagedPath:
    """A path that appeared in the staging area but was not on the caller's expected list."""
    path: str           # Path as reported by git porcelain (POSIX separators)
    status_code: str    # First two characters of git status --porcelain (e.g. "D ", "M ", "A ")


class SafeCommitBackstopError(RuntimeError):
    """Raised by safe_commit when staged paths do not match files_to_commit.

    The backstop fires BEFORE the commit is created, so the commit does not exist.
    Callers should treat this as a data-loss-prevention signal and abort.
    """

    def __init__(self, unexpected: tuple[UnexpectedStagedPath, ...], requested: tuple[str, ...]) -> None:
        self.unexpected = unexpected
        self.requested = requested
        message_lines = [
            "Commit aborted: staging area contains unexpected paths.",
            "",
            "Requested paths (what safe_commit was told to commit):",
        ]
        for p in requested:
            message_lines.append(f"  {p}")
        message_lines.append("")
        message_lines.append("Unexpected paths staged (would have been committed):")
        for p in unexpected:
            message_lines.append(f"  {p.status_code} {p.path}")
        message_lines.append("")
        message_lines.append("This usually means the working tree is behind HEAD.")
        message_lines.append("Investigate before committing:")
        message_lines.append("  git diff --cached")
        message_lines.append("  git status")
        message_lines.append("  git checkout HEAD -- <unexpected-paths>")
        message_lines.append("")
        message_lines.append("The backstop cannot be bypassed by --force.")
        super().__init__("\n".join(message_lines))
```

**Validation**:
- Types are frozen (`UnexpectedStagedPath`) or a bare `RuntimeError` subclass (`SafeCommitBackstopError`).
- The error message is multi-line and human-readable.
- The error message explicitly names the unexpected paths and the requested paths.

---

### T002 — Implement `assert_staging_area_matches_expected()`

**Files**: `src/specify_cli/git/commit_helpers.py`

**What**: Implement a helper that reads the current staging area, diffs against the caller's expected list, and raises `SafeCommitBackstopError` on mismatch.

```python
import subprocess
from collections.abc import Sequence
from pathlib import Path


def assert_staging_area_matches_expected(
    repo_path: Path,
    expected_paths: Sequence[str],
) -> None:
    """Compare staged paths to expected_paths; raise SafeCommitBackstopError on mismatch.

    Reads `git diff --cached --name-status` at `repo_path` and collects all
    currently-staged paths. Any path that is staged but not in `expected_paths`
    is a backstop violation.

    Args:
        repo_path: The repository the stage applies to (worktree root).
        expected_paths: The paths safe_commit was asked to commit, normalized to POSIX.
    """
    # git diff --cached --name-status outputs one line per staged path:
    #   "D\tdocs/runbooks/file.md"
    #   "M\tscripts/agents/AGENTS.md"
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        # Staging-area probe failed. Raise to abort the commit; caller handles.
        raise SafeCommitBackstopError(
            unexpected=(UnexpectedStagedPath(path="<probe-failed>", status_code="??"),),
            requested=tuple(expected_paths),
        )

    expected_set = {str(p).replace("\\", "/") for p in expected_paths}
    unexpected: list[UnexpectedStagedPath] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status_code, staged_path = parts
        normalized = staged_path.replace("\\", "/")
        if normalized not in expected_set:
            unexpected.append(UnexpectedStagedPath(path=normalized, status_code=f"{status_code} "))

    if unexpected:
        raise SafeCommitBackstopError(
            unexpected=tuple(unexpected),
            requested=tuple(expected_set),
        )
```

**Validation**:
- Pure function that only reads; does not mutate the staging area.
- Normalizes Windows-style separators defensively even though spec-kitty is not shipped on Windows.
- Returns `None` on success; raises on mismatch.
- Handles the `git diff --cached` failure case as a conservative abort.

---

### T003 — Wire backstop inside `safe_commit`

**Files**: `src/specify_cli/git/commit_helpers.py`

**What**: Call `assert_staging_area_matches_expected()` after `safe_commit` has staged the caller's requested paths and immediately before `git commit` runs. The `files_to_commit` passed to `safe_commit` is the expected list.

**Exactly**: Find the step in `safe_commit` that runs `git add <file>` for each `normalized_files` entry and then the step that runs `git commit`. Between them, invoke:

```python
assert_staging_area_matches_expected(repo_path, normalized_files)
```

If this raises, propagate the `SafeCommitBackstopError` up. `safe_commit` must NOT catch this exception. The surrounding `git stash pop` cleanup that `safe_commit` already does must still run (put the guard inside a try-block that ensures the stash pop still happens); the exception then surfaces to the caller.

**Not bypassable by `--force`**: callers use `--force` as an argument to the outer command, not to `safe_commit`. Do not add any bypass parameter to `safe_commit`. The backstop is unconditional.

**Validation**:
- `safe_commit` still preserves existing-staged-area semantics on the success path.
- On violation, the stash pop still runs (so the caller's staging state is restored) and the exception surfaces.
- The backstop does NOT affect the `allow_empty=True` branch: if nothing is staged, there is nothing to diff, and the backstop passes vacuously.

---

### T004 — Unit tests for backstop diff logic [P]

**Files**: `tests/unit/git/test_commit_helpers_backstop.py` (new)

**What**: Unit tests against `assert_staging_area_matches_expected()` using a temp-git fixture. No commits are created by the tests — they only exercise the staging-area probe.

Test cases:
- **Empty staging area** — expected list empty → no exception.
- **Empty staging area, non-empty expected** — no exception (nothing staged).
- **All staged paths match expected** — no exception.
- **One extra deleted path staged** — raises; `unexpected` contains that path with status `"D "`.
- **One extra modified path staged** — raises; `unexpected` contains that path with status `"M "`.
- **One extra added path staged** — raises; `unexpected` contains that path with status `"A "`.
- **Windows-style path in expected list** — normalized before compare; no false positive.
- **`git diff --cached` probe failure** — raises with `"<probe-failed>"` sentinel.

Use `pytest` + a `tmp_path` git fixture that sets up a minimal repo with a couple of committed files.

**Validation**:
- Each test runs in its own `tmp_path` to avoid cross-contamination.
- No network, no real repo mutation beyond the fixture.
- `mypy --strict` passes on the test file.

---

### T005 — Regression test that reproduces the #588 cascade [P]

**Files**: `tests/integration/git/test_safe_commit_backstop.py` (new)

**What**: Build a test that reproduces the specific sequence documented in Priivacy-ai/spec-kitty#588:

1. Initialise a temporary git repo.
2. Commit an initial set of files — include files at paths that will be "sparse-excluded" in step 3.
3. Enable `core.sparseCheckout=true` and write a restrictive pattern to `.git/info/sparse-checkout` so some committed paths are outside the cone.
4. Advance `HEAD` via a second commit that touches files inside the cone (this mirrors a merge advancing `HEAD`).
5. Refresh the index so the working tree now reflects the sparse filter against the new HEAD, producing phantom deletions in the staging area when next inspected.
6. Call `safe_commit(repo_path=tmp, files_to_commit=[<only-a-status-file>], commit_message="chore: record done transitions", allow_empty=False)` — reproducing the mission-merge housekeeping step.
7. Assert `SafeCommitBackstopError` is raised.
8. Assert no new commit was created (verify with `git rev-list HEAD` count unchanged).

Extra assertion: `--force` semantics — call a caller that exposes a `force` parameter with `force=True`, confirm the backstop still fires. (The backstop does not take `--force`; any caller that tries to pass `force=True` to bypass is a bug.)

**Validation**:
- Reproduction is deterministic across macOS and Linux.
- Test correctly detects absence of the phantom-deletion commit as success.
- Test is tagged for the `#588` regression so future developers can locate it.

---

## Definition of Done

- [ ] `UnexpectedStagedPath` and `SafeCommitBackstopError` defined in `commit_helpers.py`.
- [ ] `assert_staging_area_matches_expected()` implemented and typed.
- [ ] `safe_commit` invokes the assertion after staging and before committing; the stash-pop cleanup still runs even when the assertion raises.
- [ ] Unit tests cover the scenarios in T004; each test is independent and uses `tmp_path`.
- [ ] Regression test in T005 reproduces the #588 cascade and passes by catching `SafeCommitBackstopError`.
- [ ] `pytest tests/unit/git/test_commit_helpers_backstop.py tests/integration/git/test_safe_commit_backstop.py` passes locally.
- [ ] `mypy --strict src/specify_cli/git/commit_helpers.py` passes.
- [ ] `ruff check src/specify_cli/git/commit_helpers.py tests/unit/git/test_commit_helpers_backstop.py tests/integration/git/test_safe_commit_backstop.py` passes.
- [ ] Existing spec-kitty test suite passes (`pytest tests/`) — proves no regressions in the ~40 existing `safe_commit` callers.

## Risks

- **False positives on existing callers**: some `safe_commit` callers may legitimately have extra staged content when they call. Mitigation: run the full existing test suite after T003; if a test fails, investigate whether the caller has a real data-integrity bug that this backstop has exposed, or whether the expected_paths argument needs to be broadened for that caller.
- **Interaction with `git stash pop`**: the backstop runs AFTER the caller's `git add` and BEFORE the commit. If stash-pop somehow re-introduces unrelated staged paths, the backstop would flag them. This is actually desired behaviour — that scenario is exactly the cascade — but the error message should make clear the unexpected paths came from stash-pop.
- **Concurrent writers**: out of scope. The existing `safe_commit` is not thread-safe; this WP preserves current semantics.

## Reviewer Guidance

- Verify that `--force` CANNOT disable the backstop anywhere. Grep for `force` in `commit_helpers.py` and confirm no new parameter was added.
- Verify that the error message matches the quickstart.md Flow 4 example structurally (the quickstart text is the acceptance spec for the error shape).
- Verify that every test case in T004 has an explicit `assert` and cannot pass vacuously.
- Verify that the regression test in T005 is reproducible at least 10 times (tag it `@pytest.mark.flaky` only if there is a documented reason).

## Activity Log

- 2026-04-14T05:47:57Z – claude:sonnet-4.6:implementer:implementer – shell_pid=52930 – Assigned agent via action command
