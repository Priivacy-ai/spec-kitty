"""Tests for context/middleware.py -- CLI middleware."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.context.middleware import (
    context_callback,
    get_context,
    require_context,
)
from specify_cli.context.models import MissionContext
from specify_cli.context.store import save_context


def _make_context(**overrides: object) -> MissionContext:
    defaults: dict[str, object] = {
        "token": "ctx-01TESTMIDDLEWARE00000000AA",
        "project_uuid": "test-uuid-1234",
        "mission_id": "057-test-feature",
        "work_package_id": "WP01",
        "wp_code": "WP01",
        "mission_slug": "057-test-feature",
        "target_branch": "main",
        "authoritative_repo": "/tmp/repo",
        "authoritative_ref": "kitty/mission-057-test-feature-lane-a",
        "owned_files": ("src/**",),
        "execution_mode": "code_change",
        "dependency_mode": "independent",
        "created_at": "2026-03-27T18:00:00+00:00",
        "created_by": "claude",
    }
    defaults.update(overrides)
    return MissionContext(**defaults)  # type: ignore[arg-type]


class TestContextCallback:
    """context_callback loads context from token into ctx.obj."""

    def test_none_context_does_nothing(self) -> None:
        ctx = MagicMock(spec=typer.Context)
        ctx.obj = None

        context_callback(ctx, None)

        # obj should be initialized but empty (no mission_context key)
        assert ctx.obj == {}

    def test_valid_token_loads_context(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mission_ctx = _make_context()
        save_context(mission_ctx, tmp_path)

        # Monkeypatch _find_repo_root to return tmp_path
        monkeypatch.setattr(
            "specify_cli.context.middleware._find_repo_root",
            lambda: tmp_path,
        )

        ctx = MagicMock(spec=typer.Context)
        ctx.obj = None

        context_callback(ctx, mission_ctx.token)

        assert ctx.obj["mission_context"] == mission_ctx

    def test_invalid_token_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Ensure contexts dir exists but empty
        (tmp_path / ".kittify" / "runtime" / "contexts").mkdir(parents=True)

        monkeypatch.setattr(
            "specify_cli.context.middleware._find_repo_root",
            lambda: tmp_path,
        )

        ctx = MagicMock(spec=typer.Context)
        ctx.obj = None

        with pytest.raises(typer.BadParameter, match="not found"):
            context_callback(ctx, "ctx-DOES-NOT-EXIST")


class TestGetContext:
    """get_context extracts MissionContext from ctx.obj."""

    def test_returns_context(self) -> None:
        mission_ctx = _make_context()

        ctx = MagicMock(spec=typer.Context)
        ctx.obj = {"mission_context": mission_ctx}

        result = get_context(ctx)
        assert result == mission_ctx

    def test_missing_context_raises(self) -> None:
        ctx = MagicMock(spec=typer.Context)
        ctx.obj = {}

        with pytest.raises(typer.BadParameter, match="No context token provided"):
            get_context(ctx)

    def test_none_obj_raises(self) -> None:
        ctx = MagicMock(spec=typer.Context)
        ctx.obj = None

        with pytest.raises(typer.BadParameter, match="No context token provided"):
            get_context(ctx)


class TestRequireContextDecorator:
    """require_context decorator enforces context availability."""

    def test_passes_when_context_present(self) -> None:
        mission_ctx = _make_context()

        ctx = MagicMock(spec=typer.Context)
        ctx.obj = {"mission_context": mission_ctx}

        @require_context
        def my_command(ctx: typer.Context) -> str:
            return "success"

        result = my_command(ctx)
        assert result == "success"

    def test_raises_when_context_missing(self) -> None:
        ctx = MagicMock(spec=typer.Context)
        ctx.obj = {}

        @require_context
        def my_command(ctx: typer.Context) -> str:
            return "should not reach"

        with pytest.raises(typer.BadParameter, match="No context token provided"):
            my_command(ctx)

    def test_works_with_kwargs(self) -> None:
        mission_ctx = _make_context()

        ctx = MagicMock(spec=typer.Context)
        ctx.obj = {"mission_context": mission_ctx}

        @require_context
        def my_command(ctx: typer.Context, name: str = "test") -> str:
            return f"hello {name}"

        result = my_command(ctx=ctx, name="world")
        assert result == "hello world"


class TestEndToEndTyperApp:
    """Integration test with a real typer app and CliRunner."""

    def test_command_with_context(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A typer command can receive and use a MissionContext."""
        mission_ctx = _make_context()
        save_context(mission_ctx, tmp_path)

        monkeypatch.setattr(
            "specify_cli.context.middleware._find_repo_root",
            lambda: tmp_path,
        )

        app = typer.Typer()

        @app.callback()
        def main(
            ctx: typer.Context,
            context: str = typer.Option(None, "--context", help="Context token"),
        ) -> None:
            context_callback(ctx, context)

        @app.command()
        def show(ctx: typer.Context) -> None:
            mc = get_context(ctx)
            print(f"WP: {mc.wp_code}")

        runner = CliRunner()
        # --context must come before subcommand (it's a callback option)
        result = runner.invoke(app, ["--context", mission_ctx.token, "show"])
        assert result.exit_code == 0, f"output: {result.output}"
        assert "WP: WP01" in result.output

    def test_command_without_context_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "specify_cli.context.middleware._find_repo_root",
            lambda: tmp_path,
        )

        app = typer.Typer()

        @app.callback()
        def main(
            ctx: typer.Context,
            context: str = typer.Option(None, "--context", help="Context token"),
        ) -> None:
            context_callback(ctx, context)

        @app.command()
        def show(ctx: typer.Context) -> None:
            mc = get_context(ctx)
            print(f"WP: {mc.wp_code}")

        runner = CliRunner()
        result = runner.invoke(app, ["show"])
        assert result.exit_code != 0
        assert "No context token provided" in result.output
