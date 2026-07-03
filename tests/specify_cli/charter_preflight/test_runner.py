"""Unit tests for ``specify_cli.charter_runtime.preflight.runner`` (WP03 / FR-006..FR-008).

Test surface:

* fresh-repo path: every check fresh → ``passed=True``.
* missing-DRG path: ``synthesized_drg=missing`` → ``passed=False``,
  ``blocked_reason`` cites the synthesize command.
* dirty-worktree + ``auto_refresh=True``: no refresh runs, blocked
  reason names uncommitted artifacts.
* clean-worktree + ``auto_refresh=True``: refresh sequence runs and
  the ordered command list is captured.
* JSON serialisation (``to_dict`` / ``to_json``) is stable and matches
  the binding shape.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.charter_runtime.preflight import (
    CharterPreflightCheck,
    CharterPreflightResult,
    run_charter_preflight,
)

pytestmark = [pytest.mark.git_repo]

from ._fixtures import (
    init_git_repo,
    make_fresh_repo,
    seed_bundle_files,
    seed_charter,
    seed_manifest,
    write_metadata,
)


# ---------------------------------------------------------------------------
# Passing path
# ---------------------------------------------------------------------------


def test_fresh_repo_passes(tmp_path: Path) -> None:
    """When charter, bundle, and synthesized DRG are all fresh, preflight passes."""
    make_fresh_repo(tmp_path)
    result = run_charter_preflight(
        tmp_path,
        auto_refresh=False,
        allow_missing_charter=True,
    )
    assert isinstance(result, CharterPreflightResult)
    assert result.passed is True
    assert result.blocked_reason is None
    assert result.auto_refresh_applied is False
    assert result.auto_refresh_actions == []
    # All three layers represented in stable order.
    assert [c.name for c in result.checks] == [
        "charter_source",
        "synced_bundle",
        "synthesized_drg",
    ]
    for check in result.checks:
        assert check.state in {"fresh", "built_in_only", "skipped"}


def test_built_in_only_passes(tmp_path: Path) -> None:
    """``built_in_only: true`` with no graph.yaml is a passing state (FR-009)."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(tmp_path)
    seed_manifest(tmp_path, built_in_only=True)
    # No graph.yaml.
    result = run_charter_preflight(tmp_path)
    assert result.passed is True
    drg = next(c for c in result.checks if c.name == "synthesized_drg")
    assert drg.state == "built_in_only"


def test_missing_charter_in_fresh_project_is_advisory_not_blocking(tmp_path: Path) -> None:
    """A never-initialized charter stack is optional and must not warn-spam callers."""
    init_git_repo(tmp_path)

    result = run_charter_preflight(
        tmp_path,
        auto_refresh=False,
        allow_missing_charter=True,
    )

    assert result.passed is True
    assert result.blocked_reason is None
    assert [c.state for c in result.checks] == ["skipped", "skipped", "skipped"]
    assert result.warnings == [
        "project charter is not initialized; run `spec-kitty charter generate` "
        "when this project is ready for charter-governed workflows"
    ]


def test_missing_charter_blocks_mutation_gates_by_default(tmp_path: Path) -> None:
    """Shared runner fails closed unless a read-only/dashboard caller opts in."""
    init_git_repo(tmp_path)

    result = run_charter_preflight(tmp_path, auto_refresh=False)

    assert result.passed is False
    assert result.blocked_reason is not None
    assert [c.state for c in result.checks] == ["missing", "missing", "missing"]


# ---------------------------------------------------------------------------
# Failure paths — no auto-refresh
# ---------------------------------------------------------------------------


def test_missing_drg_blocks_with_remediation(tmp_path: Path) -> None:
    """Missing graph + manifest absent → ``synthesized_drg=missing`` → blocked."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(tmp_path)
    # Intentionally no manifest and no graph.

    result = run_charter_preflight(tmp_path, auto_refresh=False)

    assert result.passed is False
    assert result.auto_refresh_applied is False
    assert result.blocked_reason is not None
    assert "synthesize" in result.blocked_reason
    drg = next(c for c in result.checks if c.name == "synthesized_drg")
    assert drg.state == "missing"
    assert drg.remediation == "spec-kitty charter synthesize"


def test_stale_charter_blocks(tmp_path: Path) -> None:
    """A mismatched charter hash blocks with the sync remediation."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path, mismatched=True)
    seed_bundle_files(tmp_path)
    seed_manifest(tmp_path, built_in_only=True)

    result = run_charter_preflight(tmp_path)
    assert result.passed is False
    assert result.blocked_reason is not None
    assert "sync" in result.blocked_reason
    source = next(c for c in result.checks if c.name == "charter_source")
    assert source.state == "stale"


# ---------------------------------------------------------------------------
# auto_refresh=True paths
# ---------------------------------------------------------------------------


def test_auto_refresh_blocked_by_dirty_worktree(tmp_path: Path) -> None:
    """FR-008 — dirty ``.kittify/charter/`` aborts auto-refresh."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(tmp_path)
    # No manifest -> drg=missing -> not passing.

    # Add the charter directory to git (clean) then dirty it.
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed charter"],
        cwd=tmp_path,
        check=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin"},
    )
    # Now dirty the charter file.
    charter_path.write_text("# Dirty edit\n", encoding="utf-8")

    result = run_charter_preflight(tmp_path, auto_refresh=True)

    assert result.passed is False
    assert result.auto_refresh_applied is False
    assert result.auto_refresh_actions == []
    assert result.blocked_reason == "uncommitted generated artifacts; commit or stash and retry"
    # And the affected file is named in a check's detail.
    sources = [c for c in result.checks if c.name in ("charter_source", "synced_bundle")]
    assert any("uncommitted:" in c.detail for c in sources)


def test_auto_refresh_clean_worktree_runs_sequence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Clean worktree + auto_refresh runs the documented command sequence in order.

    We stub ``subprocess.run`` for the spec-kitty commands so the test
    doesn't depend on a real CLI install; the git-status invocation is
    still real so we exercise the actual dirty-detection path.
    """
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(tmp_path)
    # No manifest -> drg=missing -> needs refresh.

    # Commit everything so the worktree is clean.
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"],
        cwd=tmp_path,
        check=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin"},
    )

    # Stub the spec-kitty subprocesses to succeed and create the graph
    # so the post-refresh recompute observes a fresh DRG.
    real_run = subprocess.run
    seen: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        # Let real git invocations through.
        if cmd[:1] == ["git"]:
            return real_run(cmd, **kwargs)
        seen.append(list(cmd))
        # When 'synthesize' is requested, materialise a graph + manifest
        # so the post-recompute sees a fresh DRG.
        if cmd[:3] == ["spec-kitty", "charter", "synthesize"]:
            seed_manifest(tmp_path, built_in_only=False)
            (tmp_path / ".kittify" / "doctrine" / "graph.yaml").parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / ".kittify" / "doctrine" / "graph.yaml").write_text(
                "schema_version: '1.0'\nnodes: []\nedges: []\n", encoding="utf-8",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_charter_preflight(tmp_path, auto_refresh=True)

    # Order matters — sync (because bundle is fresh-but-charter+bundle don't have manifest cmd combination)
    # Per the algorithm: sync only skipped when both source+bundle are fresh.
    # In this test source is fresh and bundle is fresh, so sync is skipped.
    # synthesize is run, validate is run.
    assert result.auto_refresh_applied is True
    spec_kitty_calls = [c for c in seen if c[0] == "spec-kitty"]
    # Must include synthesize (drg missing) and bundle validate (always).
    cmds_as_strs = [" ".join(c) for c in spec_kitty_calls]
    assert "spec-kitty charter synthesize" in cmds_as_strs
    assert "spec-kitty charter bundle validate" in cmds_as_strs
    # And the result captured those actions in order.
    assert result.auto_refresh_actions == cmds_as_strs


def test_auto_refresh_failure_captures_blocked_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If a refresh subprocess exits non-zero, runner stops and reports."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(tmp_path)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"],
        cwd=tmp_path,
        check=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin"},
    )

    real_run = subprocess.run

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:1] == ["git"]:
            return real_run(cmd, **kwargs)
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="boom failure\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_charter_preflight(tmp_path, auto_refresh=True)
    assert result.passed is False
    assert result.auto_refresh_applied is True
    assert result.blocked_reason is not None
    assert "boom failure" in result.blocked_reason


# ---------------------------------------------------------------------------
# JSON serialisation
# ---------------------------------------------------------------------------


def test_to_dict_and_to_json_shape(tmp_path: Path) -> None:
    """The serialised result matches the binding contract shape."""
    make_fresh_repo(tmp_path)
    result = run_charter_preflight(tmp_path)
    as_dict = result.to_dict()
    assert set(as_dict.keys()) == {
        "passed",
        "checks",
        "auto_refresh_applied",
        "auto_refresh_actions",
        "blocked_reason",
    }
    assert isinstance(as_dict["checks"], list)
    assert all({"name", "state", "detail", "remediation"} <= set(c.keys()) for c in as_dict["checks"])

    # to_json round-trips.
    parsed = json.loads(result.to_json())
    assert parsed == as_dict


def test_to_dict_includes_warnings_only_when_present(tmp_path: Path) -> None:
    """The advisory field is additive only when callers need it."""
    init_git_repo(tmp_path)
    result = run_charter_preflight(
        tmp_path,
        auto_refresh=False,
        allow_missing_charter=True,
    )

    as_dict = result.to_dict()

    assert as_dict["warnings"] == [
        "project charter is not initialized; run `spec-kitty charter generate` "
        "when this project is ready for charter-governed workflows"
    ]


def test_check_dataclass_is_frozen() -> None:
    """``CharterPreflightCheck`` must be frozen (no accidental mutation)."""
    c = CharterPreflightCheck(name="x", state="fresh", detail="d", remediation=None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.detail = "y"  # type: ignore[misc]


def test_result_dataclass_is_frozen() -> None:
    """``CharterPreflightResult`` must be frozen."""
    r = CharterPreflightResult(passed=True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.passed = False  # type: ignore[misc]
