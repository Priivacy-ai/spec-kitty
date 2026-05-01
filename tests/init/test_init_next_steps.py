"""T1.4 — Regression tests: init next-steps output names spec-kitty next.

Verifies:
- Captured output contains "spec-kitty next"
- Captured output contains "spec-kitty agent action implement"
- Captured output does NOT contain "spec-kitty implement WP" (bare top-level CLI)
- The literal string "Initial commit from Specify template" is absent from src/

NOTE: The init command writes to an *injected* console (not stdout), so we read
from the buffer that backs that console, not from result.output.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.console import Console
from typer import Typer
from typer.testing import CliRunner

from specify_cli.cli.commands import init as init_module
from specify_cli.cli.commands.init import register_init_command


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_with_buf() -> tuple[Typer, io.StringIO]:
    """Return a minimal Typer app and the buffer backing the injected console."""
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, highlight=False)
    app = Typer()

    register_init_command(
        app,
        console=console,
        show_banner=lambda: None,
        activate_mission=lambda proj, mtype, mdisplay, _con: mdisplay,
        ensure_executable_scripts=lambda path, tracker=None: None,
    )
    return app, buf


def _run(app: Typer, args: list[str]) -> object:
    runner = CliRunner()
    return runner.invoke(app, args, catch_exceptions=True)


def _fake_copy_package(project_path: Path) -> Path:
    kittify = project_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    return kittify / "templates" / "command-templates"


# ---------------------------------------------------------------------------
# T1.4: Next-steps output names spec-kitty next + agent action
# ---------------------------------------------------------------------------


def test_init_next_steps_names_spec_kitty_next(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """T1.4: init output contains 'spec-kitty next' and 'spec-kitty agent action implement'.

    Also asserts the bare top-level CLI invocation 'spec-kitty implement WP' is absent.
    """
    app, buf = _make_app_with_buf()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(init_module, "get_local_repo_root", lambda override_path=None: None)
    monkeypatch.setattr(init_module, "copy_specify_base_from_package", _fake_copy_package)

    result = _run(app, ["init", "next-steps-proj", "--ai", "codex", "--non-interactive"])

    assert result.exit_code == 0, f"init failed (exit_code={result.exit_code})"

    # Output goes to the injected console buffer, not result.output
    output = buf.getvalue()

    # The canonical loop entry must appear
    assert "spec-kitty next" in output, f"Expected 'spec-kitty next' in init console output, but it was absent.\nActual console output:\n{output}"

    # The per-WP implement verb must appear
    assert "spec-kitty agent action implement" in output, (
        f"Expected 'spec-kitty agent action implement' in init console output, but it was absent.\nActual console output:\n{output}"
    )

    # The bare top-level CLI invocation must NOT appear
    assert "spec-kitty implement WP" not in output, (
        "Found forbidden string 'spec-kitty implement WP' in init console output — "
        "this is the old top-level CLI path and must not appear.\n"
        f"Actual console output:\n{output}"
    )


# ---------------------------------------------------------------------------
# T1.4b: The literal commit string must be absent from src/
# ---------------------------------------------------------------------------


def test_init_commit_string_absent_from_source() -> None:
    """T1.4b: The literal string 'Initial commit from Specify template' must not exist in src/.

    This ensures T001 (remove git side-effects) is complete and cannot regress.
    """
    forbidden = "Initial commit from Specify template"

    # src/ is two levels above tests/init/
    src_dir = Path(__file__).parent.parent.parent / "src"
    assert src_dir.is_dir(), f"src/ directory not found at {src_dir}"

    matches: list[Path] = []
    for path in src_dir.rglob("*.py"):
        try:
            if forbidden in path.read_text(encoding="utf-8", errors="replace"):
                matches.append(path)
        except OSError:
            pass

    assert matches == [], (
        f"Found forbidden literal string {forbidden!r} in source files:\n"
        + "\n".join(f"  {p}" for p in matches)
        + "\nThis string was removed as part of T001 (init coherence). "
        "A regression has reintroduced it."
    )
