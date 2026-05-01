"""CLI-path size-cap regressions for ``spec-kitty intake``.

The size-cap helpers (:func:`specify_cli.intake.scanner.read_brief` and
:func:`read_stdin_capped`) are individually tested in
``tests/integration/test_intake_size_cap.py``. Those tests exercise the
helpers in isolation; they do *not* prove that the live ``intake`` CLI
actually invokes them. Mission ``stability-and-hygiene-hardening-2026-04``
shipped the helpers, but its first review caught that the CLI still called
``sys.stdin.read()`` and ``Path.read_text()`` directly — the production
path bypassed the cap.

This module pins the CLI invariant: ``spec-kitty intake`` MUST surface a
non-zero exit and a structured "too large" message when the input exceeds
the configured cap, both for stdin and for explicit file paths.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.intake import intake
from specify_cli.mission_brief import BRIEF_SOURCE_FILENAME, MISSION_BRIEF_FILENAME

pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]


_runner = CliRunner()


@pytest.fixture()
def intake_app() -> typer.Typer:
    app = typer.Typer()
    app.command()(intake)
    return app


def _stub_repo_root_to(tmp_path: Path):
    """Pin ``_resolve_repo_root`` to the test's tmp_path."""
    return patch(
        "specify_cli.cli.commands.intake._resolve_repo_root",
        return_value=tmp_path,
    )


# ---------------------------------------------------------------------------
# File path
# ---------------------------------------------------------------------------


def test_cli_rejects_oversized_file_via_production_path(
    intake_app: typer.Typer, tmp_path: Path
) -> None:
    """A file larger than the configured cap MUST be rejected by the CLI.

    Regression: the CLI previously had its own ``stat() + read_text()``
    pair. After the wire-up, it must route through ``read_brief()``.
    """
    cap = 1024  # 1 KB cap so the test stays cheap
    over = tmp_path / "big.md"
    over.write_bytes(b"x" * (cap + 1))

    with (
        _stub_repo_root_to(tmp_path),
        patch(
            "specify_cli.cli.commands.intake.load_max_brief_bytes",
            return_value=cap,
        ),
    ):
        result = _runner.invoke(intake_app, [str(over)])

    assert result.exit_code == 1, (
        f"CLI must reject oversized file with non-zero exit. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "too large" in result.output.lower(), (
        f"Structured 'too large' message missing from CLI output: {result.output!r}"
    )
    # And no brief / source artifact may have been written.
    assert not (tmp_path / ".kittify" / MISSION_BRIEF_FILENAME).exists()
    assert not (tmp_path / ".kittify" / BRIEF_SOURCE_FILENAME).exists()


def test_cli_accepts_file_at_cap_via_production_path(
    intake_app: typer.Typer, tmp_path: Path
) -> None:
    """A file exactly at the cap is accepted (cap is ``> cap``, not ``>=``)."""
    cap = 1024
    exact = tmp_path / "exact.md"
    exact.write_bytes(b"x" * cap)

    with (
        _stub_repo_root_to(tmp_path),
        patch(
            "specify_cli.cli.commands.intake.load_max_brief_bytes",
            return_value=cap,
        ),
    ):
        result = _runner.invoke(intake_app, [str(exact)])

    assert result.exit_code == 0, (
        f"At-cap file must succeed. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert (tmp_path / ".kittify" / MISSION_BRIEF_FILENAME).exists()


def test_cli_distinguishes_missing_from_unreadable_via_production_path(
    intake_app: typer.Typer, tmp_path: Path
) -> None:
    """Missing-file path must produce a 'not found' message, not a generic one."""
    missing = tmp_path / "nope.md"

    with (
        _stub_repo_root_to(tmp_path),
        patch(
            "specify_cli.cli.commands.intake.load_max_brief_bytes",
            return_value=5 * 1024 * 1024,
        ),
    ):
        result = _runner.invoke(intake_app, [str(missing)])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# Stdin
# ---------------------------------------------------------------------------


def test_cli_rejects_oversized_stdin_via_production_path(
    intake_app: typer.Typer, tmp_path: Path
) -> None:
    """Stdin payloads larger than the cap MUST be rejected via the CLI.

    Regression: the CLI used to call ``sys.stdin.read()`` directly,
    buffering the entire payload regardless of size. The wire-up
    routes stdin through ``read_stdin_capped()`` which reads at most
    ``cap + 1`` bytes.
    """
    cap = 1024
    payload = "y" * (cap + 1)

    with (
        _stub_repo_root_to(tmp_path),
        patch(
            "specify_cli.cli.commands.intake.load_max_brief_bytes",
            return_value=cap,
        ),
    ):
        result = _runner.invoke(intake_app, ["-"], input=payload)

    assert result.exit_code == 1, (
        f"CLI must reject oversized stdin payload with non-zero exit. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "too large" in result.output.lower(), (
        f"Structured 'too large' message missing from CLI output: {result.output!r}"
    )
    assert not (tmp_path / ".kittify" / MISSION_BRIEF_FILENAME).exists()


def test_cli_accepts_stdin_under_cap_via_production_path(
    intake_app: typer.Typer, tmp_path: Path
) -> None:
    cap = 1024
    payload = "# small brief from stdin"

    with (
        _stub_repo_root_to(tmp_path),
        patch(
            "specify_cli.cli.commands.intake.load_max_brief_bytes",
            return_value=cap,
        ),
    ):
        result = _runner.invoke(intake_app, ["-"], input=payload)

    assert result.exit_code == 0, (
        f"Under-cap stdin must succeed. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    brief = tmp_path / ".kittify" / MISSION_BRIEF_FILENAME
    assert brief.exists()
    # The writer prepends provenance comments; the user payload must appear
    # somewhere in the resulting brief.
    assert payload in brief.read_text(encoding="utf-8")
