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

pytestmark = [pytest.mark.unit, pytest.mark.fast]

REPO_ROOT = Path(__file__).resolve().parents[2]

SPECIFY_PROMPT = (
    REPO_ROOT
    / "packs"
    / "built-in"
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


def test_specify_template_creates_mission_before_discovery_questions() -> None:
    """`specify.md` must establish a Mission before its Decision Moments.

    Agent-host specify is prompt-driven.  Creating the scaffold early gives the
    discovery interview a real Mission handle, while the separate readiness
    gate still prevents an unconfirmed intent from becoming a substantive spec.
    """
    assert SPECIFY_PROMPT.exists(), (
        f"Source prompt missing: {SPECIFY_PROMPT}.\n"
        "The software-dev /spec-kitty.specify template is the canonical "
        "owner of the discovery gate."
    )
    text = SPECIFY_PROMPT.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())
    required_phrases = [
        "Create the Mission scaffold before asking any discovery or brief-intake question.",
        "does not authorize writing substantive spec content",
        "Only after `create` succeeds, begin brief intake or the Discovery Gate",
        "operational preflight, not a discovery interview",
        "Do not ask a product, requirements, or implementation question before `create` succeeds.",
        "one bootstrap identity prompt is permitted before `create`",
        "`spec.md` and `meta.json` together",
        "`friendly_name`: provisional title",
    ]
    for phrase in required_phrases:
        assert phrase in normalized_text, (
            f"specify.md no longer contains the discovery-gate phrase: {phrase!r}. "
            "Do not remove the create-before-interview contract without an "
            "explicit migration plan."
        )

    assert text.index(required_phrases[0]) < text.index("## Decision Moment Protocol")
    assert text.index("## Decision Moment Protocol") < text.index("## Discovery Gate (mandatory)")
    assert text.index("## Branch Strategy Confirmation") < text.index("## Decision Moment Protocol")
