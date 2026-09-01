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

SPECIFY_PROMPT = REPO_ROOT / "packs" / "built-in" / "missions" / "mission-steps" / "software-dev" / "specify" / "prompt.md"


def test_specify_template_creates_requirements_checklist() -> None:
    """`specify.md` must instruct creation of `checklists/requirements.md`.

    This is the canonical artifact contract C-003. If a future template
    edit drops this instruction, the `/spec-kitty.specify` flow would
    silently stop creating the requirements checklist — breaking the
    quality gate the planning flow depends on.
    """
    assert SPECIFY_PROMPT.exists(), (
        f"Source prompt missing: {SPECIFY_PROMPT}.\nThe software-dev /spec-kitty.specify template is the canonical owner of the requirements-checklist artifact."
    )
    text = SPECIFY_PROMPT.read_text(encoding="utf-8")
    assert "checklists/requirements.md" in text, (
        "specify.md no longer references `checklists/requirements.md`. "
        "The canonical requirements checklist artifact (C-003) must be "
        "created by /spec-kitty.specify; do not remove that instruction "
        "without an explicit migration plan."
    )


def _specify_prompt_text() -> str:
    """Return the canonical agent-host specify prompt."""
    assert SPECIFY_PROMPT.exists(), (
        f"Source prompt missing: {SPECIFY_PROMPT}.\nThe software-dev /spec-kitty.specify template is the canonical owner of the discovery gate."
    )
    return SPECIFY_PROMPT.read_text(encoding="utf-8")


def test_specify_template_orders_create_before_discovery_and_spec_authoring() -> None:
    """Issue #3619: the executable order contract must not be phrase-fakeable."""
    text = _specify_prompt_text()
    order_contract = text.split("## Execution Order Contract", maxsplit=1)[1].split("\n## ", maxsplit=1)[0]
    ordered_transitions = [
        "spec-kitty agent mission create",
        "spec-kitty agent decision open",
        "ask the discovery question",
        "spec-kitty spec-commit",
    ]
    positions = [order_contract.index(transition) for transition in ordered_transitions]
    assert positions == sorted(positions), "Specify's execution order must be create -> decision open -> ask -> substantive spec commit."


def test_specify_template_freezes_creation_contract_before_create() -> None:
    """Type/event metadata must not split after canonical MissionCreated emission."""
    text = _specify_prompt_text()
    normalized_text = " ".join(text.split())
    required_phrases = [
        "Create the Mission scaffold before asking any discovery or brief-intake question.",
        "Resolve and freeze the activated Mission type before `mission create`.",
        "Mission type cannot be changed after creation.",
        '--mission-type "<mission-type>"',
        "Do not rewrite `friendly_name`, `purpose_tldr`, `purpose_context`, or `mission_type` during specify.",
        "always commit `spec.md` and `meta.json` together",
        "Only after `create` succeeds, begin brief intake or the Discovery Gate",
        "operational preflight, not a discovery interview",
        "spec-kitty agent mission check-prerequisites --mission <provisional-slug>",
        "--resume-probe --json",
        "`not_found`: this is the only state that authorizes a new `create`.",
        "`existing`: stop and report the valid merged Mission.",
        "The returned `target_branch`, `topology`, and `pr_bound` must also match the confirmed branch contract",
        "Any result without `resume_state` is a probe/preflight failure, not proof of absence.",
        "Retry `create` only after a confirmed non-zero failure",
        "Planning artifacts do not fall back to the coordination branch",
        "Planning/spec artifacts stay in the primary partition and never transit the coordination worktree.",
    ]
    for phrase in required_phrases:
        assert phrase in normalized_text, (
            f"specify.md no longer contains the creation-contract phrase: {phrase!r}. "
            "Do not weaken the create-before-interview contract without an "
            "explicit migration plan."
        )
    assert "Ensure `mission_type` is correct." not in text
    assert "materializes the coordination worktree and lands the commit" not in text
    assert text.count("spec-kitty spec-commit --mission <slug>") == 1

    canonical_create = text.split("2. Run the creation command from repo root before the interview:", maxsplit=1)[1].split(
        "The command returns JSON with:", maxsplit=1
    )[0]
    assert canonical_create.index('spec-kitty agent mission create "<slug>"') < canonical_create.index('--mission-type "<mission-type>"')
    assert text.count('spec-kitty agent mission create "<slug>"') == 2
    assert text.count('--mission-type "<mission-type>"') == 2


def test_specify_template_hands_non_software_missions_to_their_runtime() -> None:
    """A research scaffold must never enter the software-dev authoring contract."""
    text = _specify_prompt_text()
    handoff = text.split(
        "If the frozen `<mission-type>` is not `software-dev`, query before handoff:",
        maxsplit=1,
    )[1].split("3. **Stay in the repository root checkout**", maxsplit=1)[0]

    normalized_handoff = " ".join(handoff.lower().split())
    query_command = "spec-kitty next --agent <agent> --mission <handle> --json"
    bootstrap_command = "spec-kitty next --agent <agent> --mission <handle> --result success --json"
    assert query_command in normalized_handoff
    assert bootstrap_command in normalized_handoff
    assert normalized_handoff.index(query_command) < normalized_handoff.index(bootstrap_command)
    assert '`mission_state: "not_started"`' in normalized_handoff
    assert "never pass `--result success` merely to recover lost output" in normalized_handoff
    assert "`research` begins at `scoping`" in normalized_handoff
    for forbidden_step in (
        "write FR/NFR/C rows",
        "software-dev requirements checklist",
        "spec-kitty spec-commit",
        "spec-kitty agent mission setup-plan",
    ):
        assert forbidden_step in handoff
    assert "stop executing this prompt" in handoff


def test_specify_template_preserves_confirmed_intent_gate() -> None:
    """Early scaffold creation must not authorize substantive spec content."""
    text = _specify_prompt_text()
    required_phrases = [
        'This workflow answers "What are we building?"',
        "Before writing substantive `spec.md` content or committing it",
        "A completed discovery interview with an acknowledged Intent Summary.",
        "A brief-intake summary and extracted requirement set explicitly confirmed",
        "An explicit user instruction to minimize or skip discovery",
        "primary actor",
        "one rule or invariant",
        "canonical domain term",
    ]
    for phrase in required_phrases:
        assert phrase in text, (
            f"specify.md no longer contains the confirmed-intent phrase: {phrase!r}. The early scaffold must not weaken the substantive-spec gate."
        )

    assert text.index("## Decision Moment Protocol") < text.index("## Discovery Gate (mandatory)")
    assert text.index("## Branch Strategy Confirmation") < text.index("## Decision Moment Protocol")
