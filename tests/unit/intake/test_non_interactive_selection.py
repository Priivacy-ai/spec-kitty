"""Intake candidate-selection honors the non-interactive contract (#2912).

``_prompt_candidate_selection`` must never block on ``typer.prompt`` when the
caller is non-interactive; routing its gate through ``is_interactive`` means
``SPEC_KITTY_NON_INTERACTIVE`` now makes it exit with guidance instead of
hanging on a silent stdin pipe.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands import intake

pytestmark = [pytest.mark.fast]


def _candidates() -> list[tuple[Path, str, str | None]]:
    return [
        (Path("plan-a.md"), "claude", None),
        (Path("plan-b.md"), "codex", None),
    ]


def test_prompt_candidate_selection_exits_when_non_interactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", "1")
    # Guard: prove we exit BEFORE reaching the prompt, not because prompt failed.
    monkeypatch.setattr(
        intake.typer, "prompt", lambda *a, **k: pytest.fail("must not prompt")
    )

    with pytest.raises(typer.Exit) as exc:
        intake._prompt_candidate_selection(_candidates())

    assert exc.value.exit_code == 1


def test_prompt_candidate_selection_force_interactive_reaches_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The FORCE_INTERACTIVE escape hatch reaches the prompt even on a pipe."""
    monkeypatch.setenv("SPEC_KITTY_FORCE_INTERACTIVE", "1")
    monkeypatch.delenv("SPEC_KITTY_NON_INTERACTIVE", raising=False)
    monkeypatch.setattr(intake.typer, "prompt", lambda *a, **k: "1")

    path, harness, _ = intake._prompt_candidate_selection(_candidates())

    assert path == Path("plan-a.md")
    assert harness == "claude"
