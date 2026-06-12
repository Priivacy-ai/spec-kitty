"""Shared intake-test helpers for repeated patch setup."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch


@contextmanager
def patched_harness_plan_sources(
    mock_sources: Sequence[tuple[str, str | None, list[str]]],
) -> Iterator[None]:
    """Patch the harness-plan scan table for ``scan_for_plans`` tests."""
    with patch("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", mock_sources):
        yield


@contextmanager
def patched_intake_command_environment(
    tmp_path: Path,
    mock_sources: Sequence[tuple[str, str | None, list[str]]] | None = None,
    *,
    tty: bool | None = None,
    patch_cwd: bool = True,
) -> Iterator[None]:
    """Patch the intake command's common repo-root and scan inputs.

    Patch-surface notes:

    - ``patch_cwd=True`` patches ``Path.cwd`` *on the shared pathlib.Path
      class* (the intake module has no Path of its own), so the patch is
      process-global for the duration of the context. Pass
      ``patch_cwd=False`` for tests that pass explicit paths and should
      prove they work with an unpatched cwd.
    - ``tty=True`` replaces the intake module's entire ``sys`` reference
      with a MagicMock (so ``sys.exit``/``sys.stdin`` are mocks too).
    - ``tty=None`` (default) leaves TTY detection untouched.
    """
    with ExitStack() as stack:
        if patch_cwd:
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
            stack.enter_context(patched_harness_plan_sources(mock_sources))
        if tty:
            # Patch sys as seen by the intake module so isatty() returns True.
            # CliRunner replaces sys.stdin during invoke, so we must patch the
            # module-level sys reference, not sys.stdin directly.
            mock_sys = stack.enter_context(patch("specify_cli.cli.commands.intake.sys"))
            mock_sys.stdin.isatty.return_value = True
        elif tty is False:
            stack.enter_context(patch("sys.stdin.isatty", return_value=False))
        yield
