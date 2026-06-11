"""Shared intake-test helpers for repeated patch setup."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch


@contextmanager
def patched_intake_command_environment(
    tmp_path: Path,
    mock_sources: list[tuple[str, str | None, list[str]]] | None = None,
    *,
    tty: bool = False,
) -> Iterator[None]:
    """Patch the intake command's common repo-root and scan inputs."""
    with ExitStack() as stack:
        stack.enter_context(
            patch("specify_cli.cli.commands.intake.Path.cwd", return_value=tmp_path)
        )
        stack.enter_context(
            patch(
                "specify_cli.cli.commands.intake._resolve_repo_root",
                return_value=tmp_path,
            )
        )
        if mock_sources is not None:
            stack.enter_context(
                patch("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", mock_sources)
            )
        if tty:
            mock_sys = stack.enter_context(patch("specify_cli.cli.commands.intake.sys"))
            mock_sys.stdin.isatty.return_value = True
        yield


@contextmanager
def patched_harness_plan_sources(
    mock_sources: list[tuple[str, str | None, list[str]]],
) -> Iterator[None]:
    """Patch the harness-plan scan table for ``scan_for_plans`` tests."""
    with patch("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", mock_sources):
        yield
