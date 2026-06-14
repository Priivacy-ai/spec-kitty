"""Tests for the ReviewCycleArtifact model (WP01).

Coverage target: 90%+ for src/specify_cli/review/artifacts.py
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.review.artifacts import (
    AffectedFile,
    ReviewCycleArtifact,
    latest_review_artifact_verdict,
    rejected_review_artifact_for_terminal_lane,
)

pytestmark = pytest.mark.git_repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_artifact(**kwargs: object) -> ReviewCycleArtifact:
    defaults: dict = {
        "cycle_number": 1,
        "wp_id": "WP01",
        "mission_slug": "066-review-loop-stabilization",
        "reviewer_agent": "claude",
        "verdict": "rejected",
        "reviewed_at": "2026-04-06T12:00:00Z",
        "affected_files": [
            AffectedFile(
                path="src/specify_cli/cli/commands/agent/tasks.py",
                line_range="245-265",
            )
        ],
        "reproduction_command": "pytest tests/review/ -x",
        "body": "## Feedback\n\nPlease fix the issues.",
    }
    defaults.update(kwargs)
    return ReviewCycleArtifact(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# T1: to_dict / from_dict round-trip
# ---------------------------------------------------------------------------

def test_review_cycle_artifact_to_dict_round_trip() -> None:
    original = _sample_artifact()
    d = original.to_dict()
    restored = ReviewCycleArtifact.from_dict(d, body=original.body)

    assert restored.cycle_number == original.cycle_number
    assert restored.wp_id == original.wp_id
    assert restored.mission_slug == original.mission_slug
    assert restored.reviewer_agent == original.reviewer_agent
    assert restored.verdict == original.verdict
    assert restored.reviewed_at == original.reviewed_at
    assert restored.reproduction_command == original.reproduction_command
    assert restored.body == original.body
    assert len(restored.affected_files) == 1
    assert restored.affected_files[0].path == "src/specify_cli/cli/commands/agent/tasks.py"
    assert restored.affected_files[0].line_range == "245-265"


# ---------------------------------------------------------------------------
# T2: write() / from_file() round-trip
# ---------------------------------------------------------------------------

def test_write_and_from_file_round_trip(tmp_path: Path) -> None:
    artifact = _sample_artifact()
    dest = tmp_path / "review-cycle-1.md"
    artifact.write(dest)

    assert dest.exists()
    restored = ReviewCycleArtifact.from_file(dest)

    assert restored.cycle_number == artifact.cycle_number
    assert restored.wp_id == artifact.wp_id
    assert restored.mission_slug == artifact.mission_slug
    assert restored.reviewer_agent == artifact.reviewer_agent
    assert restored.verdict == artifact.verdict
    assert restored.reviewed_at == artifact.reviewed_at
    assert restored.reproduction_command == artifact.reproduction_command
    assert restored.body.strip() == artifact.body.strip()
    assert len(restored.affected_files) == 1
    assert restored.affected_files[0].path == artifact.affected_files[0].path
    assert restored.affected_files[0].line_range == artifact.affected_files[0].line_range


def test_write_and_from_file_preserves_complete_override(tmp_path: Path) -> None:
    """A write()→from_file() cycle must not drop the approval override (#1924).

    The override block is what the approval gate stamps onto a rejected latest
    so the terminal-lane consistency gate honors it; if to_dict() dropped it, a
    round-trip would silently reintroduce #1924-style merge gating.
    """
    artifact = _sample_artifact(
        override_actor="operator",
        override_reason="Arbiter approved despite the rejected latest cycle.",
    )
    assert artifact.has_complete_override is True

    dest = tmp_path / "review-cycle-1.md"
    artifact.write(dest)
    restored = ReviewCycleArtifact.from_file(dest)

    assert restored.has_complete_override is True
    assert restored.override_actor == artifact.override_actor
    assert restored.override_reason == artifact.override_reason


def test_to_dict_omits_override_keys_when_absent() -> None:
    """Artifacts with no override emit no override keys (byte-identical output)."""
    d = _sample_artifact().to_dict()
    assert "review_artifact_override_actor" not in d
    assert "review_artifact_override_reason" not in d


# ---------------------------------------------------------------------------
# T3: next_cycle_number() on empty dir → 1
# ---------------------------------------------------------------------------

def test_next_cycle_number_empty_dir(tmp_path: Path) -> None:
    assert ReviewCycleArtifact.next_cycle_number(tmp_path) == 1


# ---------------------------------------------------------------------------
# T4: next_cycle_number() with 3 existing files → 4
# ---------------------------------------------------------------------------

def test_next_cycle_number_with_existing(tmp_path: Path) -> None:
    for i in range(1, 4):
        (tmp_path / f"review-cycle-{i}.md").write_text("---\n---\n", encoding="utf-8")
    assert ReviewCycleArtifact.next_cycle_number(tmp_path) == 4


# ---------------------------------------------------------------------------
# T5: latest() on empty dir → None
# ---------------------------------------------------------------------------

def test_latest_empty_dir(tmp_path: Path) -> None:
    assert ReviewCycleArtifact.latest(tmp_path) is None


# ---------------------------------------------------------------------------
# T6: latest() with multiple files → highest cycle number
# ---------------------------------------------------------------------------

def test_latest_with_multiple(tmp_path: Path) -> None:
    for cycle_n in (1, 3, 2):
        artifact = _sample_artifact(cycle_number=cycle_n, body=f"cycle {cycle_n}")
        artifact.write(tmp_path / f"review-cycle-{cycle_n}.md")

    latest = ReviewCycleArtifact.latest(tmp_path)
    assert latest is not None
    assert latest.cycle_number == 3


# ---------------------------------------------------------------------------
# T7: AffectedFile with optional line_range = None
# ---------------------------------------------------------------------------

def test_affected_file_optional_line_range() -> None:
    af = AffectedFile(path="src/foo.py")
    assert af.line_range is None
    d = af.to_dict()
    assert "line_range" not in d
    restored = AffectedFile.from_dict(d)
    assert restored.line_range is None


# ---------------------------------------------------------------------------
# T8: frontmatter field completeness
# ---------------------------------------------------------------------------

def test_frontmatter_field_completeness(tmp_path: Path) -> None:
    artifact = _sample_artifact()
    dest = tmp_path / "review-cycle-1.md"
    artifact.write(dest)

    text = dest.read_text(encoding="utf-8")
    for field_name in (
        "cycle_number",
        "wp_id",
        "mission_slug",
        "reviewer_agent",
        "verdict",
        "reviewed_at",
        "affected_files",
        "reproduction_command",
    ):
        assert field_name in text, f"Missing field '{field_name}' in written artifact"


# ---------------------------------------------------------------------------
# T9: legacy feedback:// pointer resolution
# ---------------------------------------------------------------------------

def test_legacy_feedback_pointer_resolution(tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent.workflow import _resolve_review_feedback_pointer

    # Create a fake git common-dir structure
    feedback_dir = tmp_path / ".git" / "spec-kitty" / "feedback" / "066-test" / "WP01"
    feedback_dir.mkdir(parents=True)
    feedback_file = feedback_dir / "20260406T120000Z-abcd1234.md"
    feedback_file.write_text("feedback content", encoding="utf-8")

    pointer = "feedback://066-test/WP01/20260406T120000Z-abcd1234.md"

    with patch(
        "specify_cli.review.cycle._resolve_git_common_dir",
        return_value=tmp_path / ".git",
    ):
        result = _resolve_review_feedback_pointer(tmp_path, pointer)

    assert result is not None
    assert result == feedback_file.resolve()


# ---------------------------------------------------------------------------
# T10: new review-cycle:// pointer resolution
# ---------------------------------------------------------------------------

def test_new_review_cycle_pointer_resolution(tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent.workflow import _resolve_review_feedback_pointer

    # Create a fake review artifact
    artifact_dir = (
        tmp_path
        / "kitty-specs"
        / "066-review-loop-stabilization"
        / "tasks"
        / "WP01-persisted-review-artifact-model"
    )
    artifact_dir.mkdir(parents=True)
    artifact_file = artifact_dir / "review-cycle-1.md"
    _sample_artifact(
        mission_slug="066-review-loop-stabilization",
        wp_id="WP01",
        cycle_number=1,
        body="## Feedback\n\nCanonical content.",
    ).write(artifact_file)

    pointer = "review-cycle://066-review-loop-stabilization/WP01-persisted-review-artifact-model/review-cycle-1.md"
    result = _resolve_review_feedback_pointer(tmp_path, pointer)

    assert result is not None
    assert result == artifact_file.resolve()


# ---------------------------------------------------------------------------
# T11: "force-override" sentinel returns None
# ---------------------------------------------------------------------------

def test_force_override_pointer_returns_none(tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent.workflow import _resolve_review_feedback_pointer

    result = _resolve_review_feedback_pointer(tmp_path, "force-override")
    assert result is None


# ---------------------------------------------------------------------------
# T12: _persist_review_feedback() creates artifact file
# ---------------------------------------------------------------------------

def test_persist_review_feedback_creates_artifact(tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent.tasks import _persist_review_feedback

    # Build kitty-specs task directory so _resolve_wp_slug finds the slug
    task_dir = (
        tmp_path
        / "kitty-specs"
        / "066-test-mission"
        / "tasks"
        / "WP01-some-title"
    )
    task_dir.mkdir(parents=True)
    # Create a stub WP file so the directory scanner finds it
    (task_dir.parent / "WP01-some-title.md").write_text("---\n---\n", encoding="utf-8")

    # Create a feedback source file
    feedback_file = tmp_path / "feedback.md"
    feedback_file.write_text("## Issues\n\nPlease fix.", encoding="utf-8")

    persisted_path, pointer = _persist_review_feedback(
        main_repo_root=tmp_path,
        mission_slug="066-test-mission",
        task_id="WP01",
        feedback_source=feedback_file,
        reviewer_agent="claude",
    )

    assert persisted_path.exists(), f"Expected artifact at {persisted_path}"
    assert pointer.startswith("review-cycle://"), f"Expected review-cycle:// pointer, got: {pointer}"
    assert "066-test-mission" in pointer
    assert "review-cycle-1.md" in pointer

    # Verify the artifact is parseable
    artifact = ReviewCycleArtifact.from_file(persisted_path)
    assert artifact.cycle_number == 1
    assert artifact.wp_id == "WP01"
    assert artifact.mission_slug == "066-test-mission"
    assert artifact.reviewer_agent == "claude"
    assert artifact.verdict == "rejected"
    assert "Please fix." in artifact.body


def test_latest_review_artifact_verdict_reads_highest_cycle(tmp_path: Path) -> None:
    _sample_artifact(cycle_number=1, verdict="rejected").write(tmp_path / "review-cycle-1.md")
    _sample_artifact(cycle_number=2, verdict="approved").write(tmp_path / "review-cycle-2.md")

    state = latest_review_artifact_verdict(tmp_path)

    assert state is not None
    assert state.path == tmp_path / "review-cycle-2.md"
    assert state.cycle_number == 2
    assert state.verdict == "approved"


def test_terminal_lane_rejected_artifact_helper_flags_approved_or_done(tmp_path: Path) -> None:
    _sample_artifact(cycle_number=1, verdict="rejected").write(tmp_path / "review-cycle-1.md")

    approved_state = rejected_review_artifact_for_terminal_lane(tmp_path, "approved")
    done_state = rejected_review_artifact_for_terminal_lane(tmp_path, "done")

    assert approved_state is not None
    assert approved_state.verdict == "rejected"
    assert done_state is not None
    assert done_state.verdict == "rejected"


def test_terminal_lane_rejected_artifact_helper_ignores_non_rejected_latest(tmp_path: Path) -> None:
    _sample_artifact(cycle_number=1, verdict="rejected").write(tmp_path / "review-cycle-1.md")
    _sample_artifact(cycle_number=2, verdict="approved").write(tmp_path / "review-cycle-2.md")

    assert rejected_review_artifact_for_terminal_lane(tmp_path, "approved") is None
    assert rejected_review_artifact_for_terminal_lane(tmp_path, "for_review") is None


def _write_rejected_with_override(
    path: Path,
    *,
    actor: str | None = "operator",
    reason: str | None = "cycle1 verified: blocker resolved, all gates green",
) -> None:
    """Write a rejected review-cycle artifact carrying an approval-override block.

    Mirrors what the approval gate (``move-task --to approved`` over a rejected
    latest) stamps onto the artifact via ``_persist_review_artifact_override``.
    """
    _sample_artifact(cycle_number=1, verdict="rejected").write(path)
    text = path.read_text(encoding="utf-8")
    lines = ["review_artifact_override_at: '2026-06-13T17:24:12Z'"]
    if actor is not None:
        lines.append(f"review_artifact_override_actor: '{actor}'")
    if reason is not None:
        lines.append(f"review_artifact_override_reason: '{reason}'")
    block = "\n".join(lines) + "\n"
    # Inject the override keys into the YAML frontmatter (before the closing ---).
    closing = text.index("\n---", 3)
    path.write_text(text[:closing] + "\n" + block.rstrip("\n") + text[closing:], encoding="utf-8")


def test_complete_override_is_honored_for_terminal_lane(tmp_path: Path) -> None:
    """#1924: a rejected latest with a complete override is NOT a merge conflict."""
    _write_rejected_with_override(tmp_path / "review-cycle-1.md")

    state = latest_review_artifact_verdict(tmp_path)
    assert state is not None
    assert state.verdict == "rejected"
    assert state.has_override is True

    # The approval gate honored the override; the terminal-lane gate must too.
    assert rejected_review_artifact_for_terminal_lane(tmp_path, "approved") is None
    assert rejected_review_artifact_for_terminal_lane(tmp_path, "done") is None


def test_incomplete_override_still_flags_rejected_terminal_lane(tmp_path: Path) -> None:
    """An override missing the reason is incomplete and must NOT suppress the flag."""
    _write_rejected_with_override(tmp_path / "review-cycle-1.md", reason=None)

    state = latest_review_artifact_verdict(tmp_path)
    assert state is not None
    assert state.has_override is False

    flagged = rejected_review_artifact_for_terminal_lane(tmp_path, "approved")
    assert flagged is not None
    assert flagged.verdict == "rejected"
