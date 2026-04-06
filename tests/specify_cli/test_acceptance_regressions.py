"""Regression tests for acceptance pipeline fixes (feature 052).

Each test targets exactly one of the 4 regressions fixed in WP01-WP03:
- T012: materialize() no longer dirties the repo during verification
- T013: perform_acceptance() persists accept_commit SHA to meta.json
- T014: standalone tasks_cli.py --help works via subprocess
- T015: malformed JSONL raises AcceptanceError, not StoreError
- T016: acceptance.py and acceptance_support.py stay API-aligned
"""

from __future__ import annotations

import inspect
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import pytest

from specify_cli.acceptance import (
    AcceptanceError,
    AcceptanceSummary,
    collect_feature_summary,
    perform_acceptance,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import StoreError, append_event


# ---------------------------------------------------------------------------
# Shared test helper
# ---------------------------------------------------------------------------

_FEATURE_SLUG = "099-test-feature"


def _create_test_feature(
    tmp_path: Path,
    feature_slug: str = _FEATURE_SLUG,
    *,
    malformed_events: str | None = None,
) -> Tuple[Path, Path]:
    """Create a minimal but valid feature for acceptance testing.

    Returns (repo_root, feature_dir).
    """
    repo_root = tmp_path
    # Initialise a git repo
    subprocess.run(
        ["git", "init", str(repo_root)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )

    feature_dir = repo_root / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # meta.json
    meta = {
        "feature_number": "099",
        "slug": feature_slug,
        "feature_slug": feature_slug,
        "friendly_name": "Test Feature",
        "mission": "software-dev",
        "target_branch": "main",
        "created_at": "2026-01-01T00:00:00Z",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # Minimal required artifacts
    for fname in ("spec.md", "plan.md", "tasks.md"):
        (feature_dir / fname).write_text(f"# {fname}\nDone.\n")

    # WP file with all required frontmatter fields
    wp_content = (
        "---\n"
        'work_package_id: "WP01"\n'
        'title: "Test WP"\n'
        'lane: "done"\n'
        'assignee: "test-agent"\n'
        'agent: "test-agent"\n'
        'shell_pid: "12345"\n'
        "---\n"
        "# WP01\nDone.\n"
    )
    (tasks_dir / "WP01-test.md").write_text(wp_content)

    # Status event log
    if malformed_events is not None:
        (feature_dir / "status.events.jsonl").write_text(malformed_events)
    else:
        # Build a valid transition chain: planned -> done (with force to skip intermediate)
        from ulid import ULID

        now = datetime.now(timezone.utc).isoformat()
        event = StatusEvent(
            event_id=str(ULID()),
            mission_slug=feature_slug,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.DONE,
            at=now,
            actor="test-agent",
            force=True,
            execution_mode="direct_repo",
            reason="Test setup: skip to done",
        )
        append_event(feature_dir, event)

        # Pre-materialize so status.json is part of the committed state.
        # In real usage, status.json would already exist from prior operations.
        from specify_cli.status.reducer import materialize

        materialize(feature_dir)

    # Initial commit so the repo is clean
    subprocess.run(
        ["git", "-C", str(repo_root), "add", "-A"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )

    return repo_root, feature_dir


# ---------------------------------------------------------------------------
# T012: materialize() does not dirty the repo
# ---------------------------------------------------------------------------


def test_collect_feature_summary_does_not_dirty_repo(tmp_path: Path) -> None:
    """Regression: collect_feature_summary() must not leave the repo dirty.

    Before the fix, materialize() wrote status.json (with a fresh timestamp)
    *before* the git-cleanliness check, making every clean feature fail.
    """
    repo_root, _feature_dir = _create_test_feature(tmp_path)

    summary = collect_feature_summary(repo_root, _FEATURE_SLUG)
    assert summary.git_dirty == [], f"First call dirtied the repo: {summary.git_dirty}"

    # Call a second time -- must still report clean (no cumulative drift)
    summary2 = collect_feature_summary(repo_root, _FEATURE_SLUG)
    assert summary2.git_dirty == [], f"Second call dirtied the repo: {summary2.git_dirty}"


# ---------------------------------------------------------------------------
# T013: accept_commit persisted to meta.json
# ---------------------------------------------------------------------------


def test_perform_acceptance_persists_accept_commit(tmp_path: Path) -> None:
    """Regression: perform_acceptance() must write the commit SHA to meta.json.

    Before the fix, record_acceptance() was called with accept_commit=None
    and the real SHA was never written back after the commit was created.
    """
    repo_root, feature_dir = _create_test_feature(tmp_path)

    summary = collect_feature_summary(repo_root, _FEATURE_SLUG)
    result = perform_acceptance(summary, mode="local", actor="test-agent")

    # Read meta.json after acceptance
    meta = json.loads((feature_dir / "meta.json").read_text())

    # accept_commit must be a valid 40-char hex SHA
    accept_commit = meta.get("accept_commit")
    assert accept_commit is not None, "accept_commit missing from meta.json"
    assert re.fullmatch(r"[0-9a-f]{40}", accept_commit), f"accept_commit is not a valid SHA: {accept_commit!r}"

    # acceptance_history[-1] must match
    history = meta.get("acceptance_history", [])
    assert history, "acceptance_history is empty"
    assert history[-1].get("accept_commit") == accept_commit, (
        f"acceptance_history[-1]['accept_commit'] mismatch: {history[-1].get('accept_commit')!r} != {accept_commit!r}"
    )

    # AcceptanceResult.accept_commit must also match
    assert result.accept_commit == accept_commit, (
        f"Result.accept_commit mismatch: {result.accept_commit!r} != {accept_commit!r}"
    )


# ---------------------------------------------------------------------------
# Integration branch guard: merge guidance must not target integration branch
# ---------------------------------------------------------------------------


class TestIntegrationBranchGuard:
    """perform_acceptance() must never emit 'git merge <integration>' or
    'git branch -d <integration>' when the current branch IS the integration
    branch (e.g. main, 2.x).
    """

    def _make_summary_on_branch(
        self, tmp_path: Path, branch: str, *, target_branch: str = "main"
    ) -> AcceptanceSummary:
        """Create a minimal AcceptanceSummary as if on *branch*."""
        repo_root, feature_dir = _create_test_feature(tmp_path)
        # Patch meta.json with the desired target_branch and recommit
        # so the repo stays clean (summary.ok requires no dirty files).
        meta_path = feature_dir / "meta.json"
        meta = json.loads(meta_path.read_text())
        meta["target_branch"] = target_branch
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        subprocess.run(
            ["git", "-C", str(repo_root), "add", "-A"],
            check=True, capture_output=True,
        )
        # Commit only if there are staged changes (target_branch may already
        # match the value written by _create_test_feature).
        diff = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if diff.returncode != 0:
            subprocess.run(
                ["git", "-C", str(repo_root), "commit", "-m", "patch target_branch"],
                check=True, capture_output=True,
            )

        summary = collect_feature_summary(tmp_path, _FEATURE_SLUG)
        # Override the detected branch to simulate the desired state
        object.__setattr__(summary, "branch", branch)
        return summary

    def test_branch_main_no_merge_guidance(self, tmp_path: Path) -> None:
        """branch='main' with target_branch='main' must NOT produce 'git merge main'."""
        summary = self._make_summary_on_branch(tmp_path, "main", target_branch="main")
        result = perform_acceptance(summary, mode="local", actor="tester", auto_commit=False)

        merged = " ".join(result.instructions + result.cleanup_instructions)
        assert "git merge main" not in merged, (
            f"Should not suggest merging integration branch. instructions={result.instructions}"
        )
        assert "git branch -d main" not in merged, (
            f"Should not suggest deleting integration branch. cleanup={result.cleanup_instructions}"
        )

    def test_branch_2x_no_merge_guidance(self, tmp_path: Path) -> None:
        """branch='2.x' with target_branch='2.x' must NOT produce 'git merge 2.x'."""
        summary = self._make_summary_on_branch(tmp_path, "2.x", target_branch="2.x")
        result = perform_acceptance(summary, mode="local", actor="tester", auto_commit=False)

        merged = " ".join(result.instructions + result.cleanup_instructions)
        assert "git merge 2.x" not in merged
        assert "git branch -d 2.x" not in merged

    def test_pr_mode_integration_branch_no_push_branch(self, tmp_path: Path) -> None:
        """PR mode on integration branch should not say 'Push your branch'."""
        summary = self._make_summary_on_branch(tmp_path, "main", target_branch="main")
        result = perform_acceptance(summary, mode="pr", actor="tester", auto_commit=False)

        merged = " ".join(result.instructions)
        assert "Push your branch" not in merged, (
            f"Should not suggest pushing integration branch as feature. instructions={result.instructions}"
        )

    def test_feature_branch_still_gets_merge_guidance(self, tmp_path: Path) -> None:
        """A real feature branch must still get full merge + cleanup guidance."""
        summary = self._make_summary_on_branch(
            tmp_path, "kitty/mission-054-my-feature-lane-a", target_branch="main"
        )
        result = perform_acceptance(summary, mode="local", actor="tester", auto_commit=False)

        merged = " ".join(result.instructions + result.cleanup_instructions)
        assert "git merge kitty/mission-054-my-feature-lane-a" in merged, (
            f"Feature branch should get merge guidance. instructions={result.instructions}"
        )
        assert "git branch -d kitty/mission-054-my-feature-lane-a" in merged, (
            f"Feature branch should get cleanup guidance. cleanup={result.cleanup_instructions}"
        )

    def test_well_known_branch_without_meta_target(self, tmp_path: Path) -> None:
        """When meta.json has no target_branch, well-known names are guarded."""
        repo_root, feature_dir = _create_test_feature(tmp_path)
        # Remove target_branch from meta and recommit
        meta_path = feature_dir / "meta.json"
        meta = json.loads(meta_path.read_text())
        meta.pop("target_branch", None)
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        subprocess.run(
            ["git", "-C", str(repo_root), "add", "-A"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_root), "commit", "-m", "remove target_branch"],
            check=True, capture_output=True,
        )

        summary = collect_feature_summary(tmp_path, _FEATURE_SLUG)
        object.__setattr__(summary, "branch", "master")
        result = perform_acceptance(summary, mode="local", actor="tester", auto_commit=False)

        merged = " ".join(result.instructions + result.cleanup_instructions)
        assert "git merge master" not in merged
        assert "git branch -d master" not in merged


# ---------------------------------------------------------------------------
# T014: standalone tasks_cli.py --help works
# ---------------------------------------------------------------------------


def test_standalone_tasks_cli_help() -> None:
    """Regression: tasks_cli.py must work via subprocess without pip install.

    The sys.path bootstrap must add the repo src/ root so that
    specify_cli.* imports resolve from a checkout.
    """
    # Find the script relative to the repo src layout
    src_dir = Path(__file__).resolve().parents[2] / "src"
    script_path = src_dir / "specify_cli" / "scripts" / "tasks" / "tasks_cli.py"
    assert script_path.exists(), f"tasks_cli.py not found at {script_path}"

    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "PYTHONPATH": ""},
    )

    assert result.returncode == 0, f"tasks_cli.py --help failed (rc={result.returncode}):\n{result.stderr}"
    assert "ModuleNotFoundError" not in result.stderr, f"ModuleNotFoundError in stderr:\n{result.stderr}"
    # Confirm help text actually rendered
    assert "usage" in result.stdout.lower() or "--help" in result.stdout, (
        f"Help text not found in stdout:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# T015: malformed JSONL raises AcceptanceError
# ---------------------------------------------------------------------------


class TestMalformedJsonlRaisesAcceptanceError:
    """Regression: malformed status.events.jsonl must raise AcceptanceError.

    Before the fix, StoreError propagated uncaught to the CLI layer,
    producing an unhandled traceback instead of a structured error.
    """

    def test_completely_invalid_json(self, tmp_path: Path) -> None:
        """Totally invalid JSON raises AcceptanceError with 'corrupted'."""
        repo_root, _feature_dir = _create_test_feature(
            tmp_path,
            malformed_events="this is not valid json\n",
        )

        with pytest.raises(AcceptanceError, match="corrupted") as exc_info:
            collect_feature_summary(repo_root, _FEATURE_SLUG)

        # Must be AcceptanceError, NOT StoreError
        assert not isinstance(exc_info.value, StoreError)

    def test_partially_valid_jsonl(self, tmp_path: Path) -> None:
        """First line valid JSON, second line invalid -- still AcceptanceError."""
        valid_line = json.dumps({"key": "value"})
        malformed = f"{valid_line}\nthis is broken\n"
        repo_root, _feature_dir = _create_test_feature(
            tmp_path,
            malformed_events=malformed,
        )

        with pytest.raises(AcceptanceError, match="corrupted") as exc_info:
            collect_feature_summary(repo_root, _FEATURE_SLUG)

        assert not isinstance(exc_info.value, StoreError)

    def test_empty_events_file_does_not_raise(self, tmp_path: Path) -> None:
        """Empty file (zero bytes) is not an error -- read_events returns []."""
        repo_root, _feature_dir = _create_test_feature(
            tmp_path,
            malformed_events="",
        )

        # Should not raise -- empty events file is valid
        summary = collect_feature_summary(repo_root, _FEATURE_SLUG)
        # But the feature won't be "ok" because there's no canonical state
        assert isinstance(summary, AcceptanceSummary)


# ---------------------------------------------------------------------------
# T016: Copy-parity assertions
# ---------------------------------------------------------------------------


def test_copy_parity_between_acceptance_modules() -> None:
    """Verify acceptance_support.py re-exports match acceptance.py exactly.

    After deduplication, acceptance_support.py is a thin re-export wrapper.
    The __all__ sets must be equal, and every re-exported name must be the
    exact same object (not a copy).
    """
    from specify_cli import acceptance
    from specify_cli.scripts.tasks import acceptance_support

    # __all__ parity: sets must be equal
    core_exports = set(acceptance.__all__)
    standalone_exports = set(acceptance_support.__all__)
    assert core_exports == standalone_exports, (
        f"Wrapper must re-export all canonical names. "
        f"Missing: {core_exports - standalone_exports}, "
        f"Extra: {standalone_exports - core_exports}"
    )

    # Object identity: re-exports must be the same objects, not copies
    for name in acceptance.__all__:
        assert getattr(acceptance, name) is getattr(acceptance_support, name), (
            f"{name} in acceptance_support is not the same object as in acceptance"
        )

    # Function signature parity for key functions (validates re-exports match)
    parity_functions = [
        "collect_feature_summary",
        "detect_feature_slug",
        "perform_acceptance",
        "choose_mode",
    ]
    for fn_name in parity_functions:
        sig_core = inspect.signature(getattr(acceptance, fn_name))
        sig_standalone = inspect.signature(getattr(acceptance_support, fn_name))
        assert sig_core == sig_standalone, (
            f"{fn_name} signature mismatch:\n  acceptance:         {sig_core}\n  acceptance_support: {sig_standalone}"
        )
