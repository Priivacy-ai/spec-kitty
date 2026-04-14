"""WP05/T020 FR-008 — ``--allow-sparse-checkout`` override bypasses preflight.

The override:
1. Logs a structured ``spec_kitty.override.sparse_checkout`` WARNING.
2. Does NOT disable the commit-layer backstop (C-007 / WP01) — that is out of
   scope of this test because we do not drive the full merge here; we assert
   that the preflight emission is correct and that the override flag is
   actually threaded through the Typer command path to
   ``require_no_sparse_checkout``.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest

from specify_cli.git import sparse_checkout as sc_mod
from specify_cli.git.sparse_checkout import (
    _reset_session_warning_state,
    require_no_sparse_checkout,
)


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-qb", "main", str(repo)])
    _run(["git", "-C", str(repo), "config", "user.email", "test@test.com"])
    _run(["git", "-C", str(repo), "config", "user.name", "Test"])
    _run(["git", "-C", str(repo), "config", "commit.gpgsign", "false"])
    (repo / "README.md").write_text("init\n")
    _run(["git", "-C", str(repo), "add", "."])
    _run(["git", "-C", str(repo), "commit", "-m", "init"])


class TestMergeWithAllowOverride:
    """FR-008: ``--allow-sparse-checkout`` bypasses the preflight AND logs the event."""

    @pytest.fixture(autouse=True)
    def _reset_warning(self) -> None:
        _reset_session_warning_state()
        yield
        _reset_session_warning_state()

    def test_override_emits_structured_log_and_does_not_raise(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Override path: preflight returns, structured log captured in caplog."""
        repo = tmp_path / "r"
        _init_git_repo(repo)
        _run(["git", "-C", str(repo), "config", "core.sparseCheckout", "true"])

        caplog.set_level(logging.WARNING, logger=sc_mod.logger.name)

        require_no_sparse_checkout(
            repo_root=repo,
            command="spec-kitty merge",
            override_flag=True,
            actor="claude",
            mission_slug="feat-test",
            mission_id="01HXYZ",
        )

        override_hits = [
            r
            for r in caplog.records
            if "spec_kitty.override.sparse_checkout" in r.getMessage()
        ]
        assert len(override_hits) == 1, (
            "FR-008 requires exactly one override log record per bypassed call"
        )
        msg = override_hits[0].getMessage()
        assert "command=spec-kitty merge" in msg
        assert "mission_slug=feat-test" in msg
        assert "mission_id=01HXYZ" in msg
        assert "actor=claude" in msg
        assert str(repo) in msg

    def test_override_flag_is_wired_from_cli_to_preflight(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify the merge command threads ``--allow-sparse-checkout`` to the preflight.

        We patch ``require_no_sparse_checkout`` at the merge-module import site
        and assert it receives ``override_flag=True`` when the CLI is invoked
        with ``--allow-sparse-checkout``. This verifies the live wiring (T020)
        independently of any downstream merge work.
        """
        from specify_cli.cli.commands import merge as merge_mod

        observed: dict[str, object] = {}

        def fake_preflight(**kwargs: object) -> None:
            observed.update(kwargs)

        monkeypatch.setattr(merge_mod, "require_no_sparse_checkout", fake_preflight)

        # Short-circuit everything else so the command returns before doing
        # actual work — we only care that the preflight was called with the
        # right override_flag.
        class _StopEarly(Exception):
            pass

        def stop_after_preflight(*_args: object, **_kwargs: object) -> object:
            raise _StopEarly()

        monkeypatch.setattr(merge_mod, "require_lanes_json", stop_after_preflight)

        repo = tmp_path / "r"
        _init_git_repo(repo)
        _run(["git", "-C", str(repo), "config", "core.sparseCheckout", "true"])

        import os

        import typer
        from typer.testing import CliRunner

        app = typer.Typer()
        app.command()(merge_mod.merge)
        runner = CliRunner()

        original_cwd = os.getcwd()
        try:
            os.chdir(repo)
            runner.invoke(
                app,
                ["--mission", "feat-test", "--allow-sparse-checkout"],
                catch_exceptions=True,
            )
        finally:
            os.chdir(original_cwd)

        assert observed.get("override_flag") is True, (
            f"--allow-sparse-checkout must thread through to require_no_sparse_checkout; "
            f"observed={observed}"
        )
        assert observed.get("command") == "spec-kitty merge"
