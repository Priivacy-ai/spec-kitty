"""Integration tests for :mod:`specify_cli.git.sparse_checkout` detection.

These tests exercise ``scan_repo`` / ``scan_path`` against real ``git init`` and
``git worktree add`` invocations, not mocked subprocess calls. They are the
end-to-end backstop for WP02's detection primitive: if the shape of git's
per-worktree sparse-checkout configuration ever changes under us, these tests
break first.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.git.sparse_checkout import (
    SparseCheckoutPreflightError,
    require_no_sparse_checkout,
    scan_path,
    scan_repo,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo_with_commit(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", str(repo)])
    _run(["git", "-C", str(repo), "config", "user.email", "test@example.com"])
    _run(["git", "-C", str(repo), "config", "user.name", "Test User"])
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _run(["git", "-C", str(repo), "add", "README.md"])
    _run(["git", "-C", str(repo), "commit", "-m", "init"])


# ---------------------------------------------------------------------------
# End-to-end detection
# ---------------------------------------------------------------------------


class TestEndToEndDetection:
    def test_fresh_repo_reports_inactive(self, tmp_path: Path) -> None:
        repo = tmp_path / "r"
        _init_repo_with_commit(repo)

        report = scan_repo(repo)

        assert report.any_active is False
        assert report.primary.is_active is False
        assert report.worktrees == ()
        assert report.affected_paths == ()

    def test_enabling_sparse_checkout_flips_detection(self, tmp_path: Path) -> None:
        repo = tmp_path / "r"
        _init_repo_with_commit(repo)

        _run(
            ["git", "-C", str(repo), "config", "core.sparseCheckout", "true"],
        )

        report = scan_repo(repo)
        assert report.primary.config_enabled is True
        assert report.primary.is_active is True
        assert report.any_active is True
        assert report.affected_paths == (repo,)

    def test_primary_clean_worktree_sparse_detected(self, tmp_path: Path) -> None:
        """Worktree-scoped config alone must flip ``any_active`` to True.

        Uses ``extensions.worktreeConfig=true`` + ``git config --worktree`` so
        the flag lives in the per-worktree config only. This is the realistic
        way to have a sparse worktree without affecting the primary repo.
        """
        repo = tmp_path / "r"
        _init_repo_with_commit(repo)

        wt = repo / ".worktrees" / "lane-a"
        _run(
            [
                "git",
                "-C",
                str(repo),
                "worktree",
                "add",
                "-b",
                "feature/lane-a",
                str(wt),
            ],
        )

        # Enable worktree-scoped config storage.
        _run(["git", "-C", str(repo), "config", "extensions.worktreeConfig", "true"])
        # Enable sparse in the worktree only (per-worktree config file).
        _run(
            [
                "git",
                "-C",
                str(wt),
                "config",
                "--worktree",
                "core.sparseCheckout",
                "true",
            ],
        )

        report = scan_repo(repo)
        assert report.primary.is_active is False
        assert len(report.worktrees) == 1
        wt_state = report.worktrees[0]
        assert wt_state.is_active is True
        assert wt_state.is_worktree is True
        assert wt_state.path == wt
        # Pattern file should resolve under <git-common-dir>/worktrees/<name>/info/
        # even though it may not exist yet.
        assert wt_state.pattern_file_path is not None
        assert "worktrees" in str(wt_state.pattern_file_path)
        assert report.any_active is True
        assert wt in report.affected_paths

    def test_primary_sparse_worktree_clean(self, tmp_path: Path) -> None:
        """Primary has sparse; worktree does not — both must be probed correctly."""
        repo = tmp_path / "r"
        _init_repo_with_commit(repo)
        _run(["git", "-C", str(repo), "config", "core.sparseCheckout", "true"])

        wt = repo / ".worktrees" / "lane-b"
        _run(
            [
                "git",
                "-C",
                str(repo),
                "worktree",
                "add",
                "-b",
                "feature/lane-b",
                str(wt),
            ],
        )

        report = scan_repo(repo)
        assert report.primary.is_active is True
        assert len(report.worktrees) == 1
        # The worktree inherits the repo-local config because git's config
        # resolution layers worktree > repo for a worktree checkout.
        # We only assert on any_active (FR-001) here — the exact inheritance
        # behaviour is documented in the WP risks section.
        assert report.any_active is True
        assert repo in report.affected_paths

    def test_pattern_file_line_count_counted_without_comments(self, tmp_path: Path) -> None:
        repo = tmp_path / "r"
        _init_repo_with_commit(repo)
        _run(["git", "-C", str(repo), "config", "core.sparseCheckout", "true"])
        pf = repo / ".git" / "info" / "sparse-checkout"
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_text(
            "\n".join(
                [
                    "# header comment",
                    "src/",
                    "",
                    "tests/",
                    "   ",
                    "docs/",
                    "# trailing",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        state = scan_path(repo, is_worktree=False)
        assert state.pattern_file_present is True
        assert state.pattern_line_count == 3


# ---------------------------------------------------------------------------
# Preflight wiring
# ---------------------------------------------------------------------------


class TestPreflight:
    def test_clean_repo_passes_preflight(self, tmp_path: Path) -> None:
        repo = tmp_path / "r"
        _init_repo_with_commit(repo)

        require_no_sparse_checkout(
            repo,
            command="merge",
            override_flag=False,
            actor="tester",
            mission_slug="some-mission",
            mission_id="01HXYZ",
        )

    def test_sparse_repo_raises_preflight(self, tmp_path: Path) -> None:
        repo = tmp_path / "r"
        _init_repo_with_commit(repo)
        _run(["git", "-C", str(repo), "config", "core.sparseCheckout", "true"])

        with pytest.raises(SparseCheckoutPreflightError) as ei:
            require_no_sparse_checkout(
                repo,
                command="merge",
                override_flag=False,
                actor="tester",
                mission_slug="some-mission",
                mission_id="01HXYZ",
            )

        err = ei.value
        assert err.command == "merge"
        assert err.report.any_active is True
        msg = str(err)
        assert "merge aborted" in msg
        assert "legacy sparse-checkout state detected" in msg
        assert "spec-kitty doctor sparse-checkout --fix" in msg
        assert "--allow-sparse-checkout" in msg
        assert str(repo) in msg

    def test_override_flag_emits_structured_log_and_does_not_raise(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        from specify_cli.git import sparse_checkout as sc_mod

        repo = tmp_path / "r"
        _init_repo_with_commit(repo)
        _run(["git", "-C", str(repo), "config", "core.sparseCheckout", "true"])

        caplog.set_level(logging.WARNING, logger=sc_mod.logger.name)

        require_no_sparse_checkout(
            repo,
            command="merge",
            override_flag=True,
            actor="tester",
            mission_slug="feat-slug",
            mission_id="01HXYZ",
        )

        override_hits = [r for r in caplog.records if "spec_kitty.override.sparse_checkout" in r.getMessage()]
        assert len(override_hits) == 1
        msg = override_hits[0].getMessage()
        assert "command=merge" in msg
        assert "mission_slug=feat-slug" in msg
        assert "mission_id=01HXYZ" in msg
        assert "actor=tester" in msg
        assert str(repo) in msg
