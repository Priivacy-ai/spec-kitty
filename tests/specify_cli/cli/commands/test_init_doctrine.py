"""ATDD acceptance tests for WP07: Constitution Defaults File + Init Integration.

US-1 scenarios 1-3 and US-2 scenarios 1-4.
Requirements: FR-001, FR-002, FR-003, FR-004, FR-005, FR-015, FR-020, NFR-001, C-002.

These tests must FAIL before T028-T031 are implemented.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# US-1: Accept Defaults
# ---------------------------------------------------------------------------


def test_init_accept_defaults_creates_constitution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """US-1 Scenario 1: fresh project, user selects 'accept defaults' → constitution created."""
    (tmp_path / ".kittify" / "constitution").mkdir(parents=True)

    # Simulate user typing "defaults" at the governance prompt
    monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "defaults")

    from specify_cli.cli.commands.init import _run_doctrine_stack_init
    from rich.console import Console

    console = Console(quiet=True)
    result = _run_doctrine_stack_init(tmp_path, non_interactive=False, console=console)

    assert result is True
    constitution_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
    assert constitution_path.exists(), (
        f"Constitution not found at {constitution_path}. "
        "Expected '_run_doctrine_stack_init' to generate it when user selects 'defaults'."
    )
    assert constitution_path.stat().st_size > 0, "Constitution file is empty"


def test_init_non_interactive_applies_defaults(tmp_path: Path) -> None:
    """US-1 Scenario 2: --non-interactive on fresh project → constitution created without prompts."""
    (tmp_path / ".kittify" / "constitution").mkdir(parents=True)

    from specify_cli.cli.commands.init import _run_doctrine_stack_init
    from rich.console import Console

    console = Console(quiet=True)
    result = _run_doctrine_stack_init(tmp_path, non_interactive=True, console=console)

    assert result is True
    constitution_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
    assert constitution_path.exists(), (
        f"Constitution not found at {constitution_path}. "
        "Expected non-interactive mode to apply doctrine defaults automatically."
    )
    assert constitution_path.stat().st_size > 0, "Constitution file is empty"


def test_init_skips_doctrine_if_constitution_exists(tmp_path: Path) -> None:
    """US-1 Scenario 3: project with existing constitution → doctrine step skipped."""
    constitution_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
    constitution_path.parent.mkdir(parents=True)
    original_content = "# Existing Constitution\n\nAlready configured.\n"
    constitution_path.write_text(original_content, encoding="utf-8")

    from specify_cli.cli.commands.init import _run_doctrine_stack_init
    from rich.console import Console

    output = io.StringIO()
    console = Console(file=output)
    result = _run_doctrine_stack_init(tmp_path, non_interactive=False, console=console)

    assert result is True
    # Constitution must NOT be overwritten
    assert constitution_path.read_text(encoding="utf-8") == original_content, (
        "Constitution was overwritten — skip-if-exists check is missing or broken."
    )
    output_text = output.getvalue()
    assert "skip" in output_text.lower() or "already exists" in output_text.lower() or "existing" in output_text.lower(), (
        f"Expected skip message but got: {output_text!r}"
    )


# ---------------------------------------------------------------------------
# US-2: Configure Manually
# ---------------------------------------------------------------------------


def test_init_configure_manually_asks_interview_depth(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """US-2 Scenario 1: user selects 'manual' path → interview depth question is asked."""
    (tmp_path / ".kittify" / "constitution").mkdir(parents=True)

    depth_prompts: list[str] = []

    def tracking_prompt(text: str, *args: object, **kwargs: object) -> str:
        if any(kw in text.lower() for kw in ("depth", "minimal", "comprehensive")):
            depth_prompts.append(text)
        return "minimal"

    monkeypatch.setattr("typer.prompt", tracking_prompt)

    from specify_cli.cli.commands.init import _run_inline_interview
    from rich.console import Console

    console = Console(quiet=True)
    _run_inline_interview(tmp_path, console)

    assert len(depth_prompts) > 0, (
        "Expected at least one prompt asking for interview depth (minimal/comprehensive) "
        f"but got depth_prompts={depth_prompts!r}"
    )


def test_init_configure_manually_informs_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """US-2 Scenario 2: 'configure manually' path → informational message shown before interview."""
    (tmp_path / ".kittify" / "constitution").mkdir(parents=True)

    monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "minimal")

    from specify_cli.cli.commands.init import _run_inline_interview
    from rich.console import Console

    output = io.StringIO()
    console = Console(file=output)
    _run_inline_interview(tmp_path, console)

    output_text = output.getvalue()
    assert "constitution" in output_text.lower() or "governance" in output_text.lower(), (
        "Expected informational message about constitution/governance before the interview starts. "
        f"Got: {output_text!r}"
    )


def test_init_configure_manually_generates_constitution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """US-2 Scenario 3: user completes inline interview → constitution generated."""
    (tmp_path / ".kittify" / "constitution").mkdir(parents=True)

    # Return "minimal" for all prompts (depth question + all interview questions)
    monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "minimal")

    from specify_cli.cli.commands.init import _run_inline_interview
    from rich.console import Console

    console = Console(quiet=True)
    result = _run_inline_interview(tmp_path, console)

    assert result is True
    constitution_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
    assert constitution_path.exists(), (
        f"Constitution not found at {constitution_path}. "
        "Expected _run_inline_interview to generate it after a complete interview."
    )
    assert constitution_path.stat().st_size > 0, "Constitution file is empty"


def test_init_resume_after_interrupt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """US-2 Scenario 4: interrupted init with checkpoint → resume/restart offered.
    Selecting 'restart' discards checkpoint; fresh start applies defaults.
    """
    (tmp_path / ".kittify" / "constitution").mkdir(parents=True)

    # Create a fake checkpoint from a previous interrupted session
    checkpoint_path = tmp_path / ".kittify" / ".init-checkpoint.yaml"
    from kernel.atomic import atomic_write
    atomic_write(
        checkpoint_path,
        "phase: interview\ndepth: minimal\nanswers_so_far: {}\n",
        mkdir=True,
    )
    assert checkpoint_path.exists(), "Precondition: checkpoint must exist before test"

    # Simulate: user sees resume prompt, chooses 'restart', then 'defaults' for the fresh start
    responses = iter(["restart", "defaults"])
    monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: next(responses))

    from specify_cli.cli.commands.init import _run_doctrine_stack_init
    from rich.console import Console

    console = Console(quiet=True)
    result = _run_doctrine_stack_init(tmp_path, non_interactive=False, console=console)

    assert result is True
    # Checkpoint must be deleted after 'restart'
    assert not checkpoint_path.exists(), (
        "Checkpoint was not deleted after user selected 'restart'. "
        "FR-020 requires that restart discards the previous checkpoint."
    )
