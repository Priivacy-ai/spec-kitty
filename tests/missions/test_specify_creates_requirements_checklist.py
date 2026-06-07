"""Lock the canonical requirements-checklist artifact contract (C-003).

The deprecated `/spec-kitty.checklist` slash-command surface was retired
in WP04 (FR-003 / FR-004 / #815). The canonical
`kitty-specs/<mission>/checklists/requirements.md` artifact MUST keep
working — it is created by `/spec-kitty.specify` during spec authoring
and is the gate that the planning flow checks before advancing.

This test locks two layers so future cleanup never accidentally removes
the artifact:

1. The `software-dev` mission's `specify` source prompt still
   contains an explicit instruction to create the file at
   `feature_dir/checklists/requirements.md`.

Both checks are static (no subprocess, no filesystem mutation) so the
test is fast and deterministic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]

SPECIFY_PROMPT = (
    REPO_ROOT
    / "src"
    / "doctrine"
    / "missions"
    / "mission-steps"
    / "software-dev"
    / "specify"
    / "prompt.md"
)


def test_specify_template_creates_requirements_checklist() -> None:
    """`specify.md` must instruct creation of `checklists/requirements.md`.

    This is the canonical artifact contract C-003. If a future template
    edit drops this instruction, the `/spec-kitty.specify` flow would
    silently stop creating the requirements checklist — breaking the
    quality gate the planning flow depends on.
    """
    assert SPECIFY_PROMPT.exists(), (
        f"Source prompt missing: {SPECIFY_PROMPT}.\n"
        "The software-dev /spec-kitty.specify template is the canonical "
        "owner of the requirements-checklist artifact."
    )
    text = SPECIFY_PROMPT.read_text(encoding="utf-8")
    assert "checklists/requirements.md" in text, (
        "specify.md no longer references `checklists/requirements.md`. "
        "The canonical requirements checklist artifact (C-003) must be "
        "created by /spec-kitty.specify; do not remove that instruction "
        "without an explicit migration plan."
    )


def test_specify_template_blocks_artifacts_until_intent_confirmed() -> None:
    """`specify.md` must keep discovery before artifact creation.

    The `/spec-kitty.specify` flow is prompt-driven for agent hosts. This static
    check protects the instruction that prevents agents from skipping the user
    interview and calling `mission create` before confirming intent.
    """
    assert SPECIFY_PROMPT.exists(), (
        f"Source prompt missing: {SPECIFY_PROMPT}.\n"
        "The software-dev /spec-kitty.specify template is the canonical "
        "owner of the discovery gate."
    )
    text = SPECIFY_PROMPT.read_text(encoding="utf-8")
    required_phrases = [
        'This workflow answers "What are we building?"',
        "Before `mission create`, before writing `spec.md`, and before committing",
        "A completed discovery interview with an acknowledged Intent Summary.",
        "A brief-intake summary and extracted requirement set explicitly confirmed",
        "primary actor",
        "one rule or invariant",
        "canonical domain term",
    ]
    for phrase in required_phrases:
        assert phrase in text, (
            f"specify.md no longer contains the discovery-gate phrase: {phrase!r}. "
            "Do not weaken /spec-kitty.specify's interview-first invariant "
            "without an explicit migration plan."
        )
