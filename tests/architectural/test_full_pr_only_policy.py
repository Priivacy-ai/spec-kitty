"""Protect the user-directed full-PR-only workflow from doctrine drift."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.doctrine]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ACTIVE_POLICY_PATHS = (
    Path("AGENTS.md"),
    Path(".kittify/charter/charter.md"),
    Path(".kittify/charter/charter.yaml"),
    Path(".kittify/charter/references.yaml"),
    Path("docs/development/onboarding-run.md"),
    Path("src/doctrine/directives/built-in/046-readable-consistent-prs.directive.yaml"),
    Path("src/doctrine/missions/mission-steps/software-dev/implement/prompt.md"),
    Path("src/doctrine/procedures/built-in/mission-wrap-up-sequence.procedure.yaml"),
)
_DRAFT_PR_INSTRUCTION = re.compile(
    r"(?<!non[- ])\bdraft[-\s]+(?:pull\s+request|pr)\b", re.IGNORECASE
)


def _draft_pr_instruction_paths(repo_root: Path) -> list[Path]:
    """Return active guidance files that still instruct agents to open drafts."""
    return [
        path
        for path in _ACTIVE_POLICY_PATHS
        if _DRAFT_PR_INSTRUCTION.search((repo_root / path).read_text(encoding="utf-8"))
    ]


def test_active_pr_guidance_requires_full_non_draft_pull_requests() -> None:
    """Every active agent policy must express the same full-PR-only rule."""
    missing_policy = [
        path
        for path in _ACTIVE_POLICY_PATHS
        if "full, non-draft" not in (_REPO_ROOT / path).read_text(encoding="utf-8").casefold()
    ]

    assert not missing_policy, (
        "Active PR guidance must require a full, non-draft pull request: "
        f"{[str(path) for path in missing_policy]}"
    )


def test_active_pr_guidance_never_instructs_agents_to_open_drafts() -> None:
    """Draft PRs are not a staging state in the active agent workflow."""
    offenders = _draft_pr_instruction_paths(_REPO_ROOT)

    assert not offenders, (
        "Active guidance still instructs agents to open draft PRs: "
        f"{[str(path) for path in offenders]}"
    )


def test_draft_pr_instruction_detector_rejects_a_planted_legacy_rule(tmp_path: Path) -> None:
    """Prove the drift detector catches an instruction to open a draft PR."""
    for path in _ACTIVE_POLICY_PATHS:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Open a full, non-draft pull request.", encoding="utf-8")

    planted = _ACTIVE_POLICY_PATHS[0]
    (tmp_path / planted).write_text("Open a draft PR first.", encoding="utf-8")

    assert _draft_pr_instruction_paths(tmp_path) == [planted]
