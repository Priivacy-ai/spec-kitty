from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.review.cycle import (
    ReviewCycleError,
    build_review_cycle_pointer,
    create_rejected_review_cycle,
    resolve_review_cycle_pointer,
    validate_review_artifact_file,
    validate_review_cycle_pointer,
)

pytestmark = pytest.mark.git_repo


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)


def test_create_rejected_cycle_returns_canonical_pointer_and_review_result(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tasks_dir = repo / "kitty-specs" / "001-mission" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-core.md").write_text("# WP01\n", encoding="utf-8")
    feedback = tmp_path / "feedback.md"
    feedback.write_text("**Issue**: Fix the rejected behavior.\n", encoding="utf-8")

    created = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug="001-mission",
        wp_id="WP01",
        wp_slug="WP01-core",
        feedback_source=feedback,
        reviewer_agent="codex",
    )

    assert created.artifact_path == tasks_dir / "WP01-core" / "review-cycle-1.md"
    assert created.pointer == "review-cycle://001-mission/WP01-core/review-cycle-1.md"
    assert created.review_result.verdict == "changes_requested"
    assert created.review_result.reference == created.pointer
    assert created.review_result.feedback_path == str(created.artifact_path)
    assert validate_review_artifact_file(created.artifact_path).body.startswith("**Issue**")


def test_empty_feedback_fails_before_artifact_write(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    feedback = tmp_path / "feedback.md"
    feedback.write_text(" \n", encoding="utf-8")

    with pytest.raises(ReviewCycleError, match="empty"):
        create_rejected_review_cycle(
            main_repo_root=repo,
            mission_slug="001-mission",
            wp_id="WP01",
            wp_slug="WP01-core",
            feedback_source=feedback,
            reviewer_agent="codex",
        )

    assert not (repo / "kitty-specs").exists()


def test_invalid_review_cycle_pointer_segments_are_rejected() -> None:
    with pytest.raises(ReviewCycleError):
        validate_review_cycle_pointer("review-cycle://../WP01/review-cycle-1.md")
    with pytest.raises(ReviewCycleError):
        build_review_cycle_pointer("001-mission", "WP01-core", "notes.md")


def test_resolve_canonical_pointer_validates_required_frontmatter(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    artifact_dir = repo / "kitty-specs" / "001-mission" / "tasks" / "WP01-core"
    artifact_dir.mkdir(parents=True)
    invalid = artifact_dir / "review-cycle-1.md"
    invalid.write_text("---\nverdict: rejected\n---\n\nbody\n", encoding="utf-8")

    resolved = resolve_review_cycle_pointer(
        repo,
        "review-cycle://001-mission/WP01-core/review-cycle-1.md",
    )

    assert resolved.kind == "canonical"
    assert resolved.path is None


def test_resolve_canonical_pointer_returns_valid_artifact(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    feedback = tmp_path / "feedback.md"
    feedback.write_text("**Issue**: canonical context.\n", encoding="utf-8")
    created = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug="001-mission",
        wp_id="WP01",
        wp_slug="WP01-core",
        feedback_source=feedback,
        reviewer_agent="codex",
    )

    resolved = resolve_review_cycle_pointer(repo, created.pointer)

    assert resolved.kind == "canonical"
    assert resolved.path == created.artifact_path.resolve()
    assert resolved.warnings == ()


def test_legacy_feedback_pointer_resolves_with_warning(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    common_dir = repo / ".git"
    feedback_file = common_dir / "spec-kitty" / "feedback" / "001-mission" / "WP01" / "feedback.md"
    feedback_file.parent.mkdir(parents=True)
    feedback_file.write_text("legacy feedback", encoding="utf-8")

    with patch("specify_cli.review.cycle._resolve_git_common_dir", return_value=common_dir):
        resolved = resolve_review_cycle_pointer(repo, "feedback://001-mission/WP01/feedback.md")

    assert resolved.kind == "legacy"
    assert resolved.path == feedback_file.resolve()
    assert resolved.warnings


def test_sentinel_pointer_is_not_feedback_artifact(tmp_path: Path) -> None:
    resolved = resolve_review_cycle_pointer(tmp_path, "action-review-claim")

    assert resolved.kind == "sentinel"
    assert resolved.path is None


MISSION_SLUG = "annoying-bugs-sweep-01KYHQ9F"
WP_ID = "WP03"
WP_SLUG = "WP03-ledger-grammar"


@pytest.mark.regression
def test_self_referential_feedback_source_is_rejected(tmp_path: Path) -> None:
    """Pin #2996(b): handing ``create_rejected_review_cycle`` the WP's OWN
    prior ``review-cycle-N.md`` as ``feedback_source`` must be refused, not
    silently duplicated into a new cycle.

    Root cause (traced against ``main`` @ upstream/main):
    ``create_rejected_review_cycle``
    (``src/specify_cli/review/cycle.py:277-346``) validates ``feedback_source``
    only for existence / is-a-file / non-empty content
    (lines 288-295) and computes the next cycle number purely from
    ``len(sub_artifact_dir.glob("review-cycle-*.md")) + 1``
    (``ReviewCycleArtifact.next_cycle_number``,
    ``src/specify_cli/review/artifacts.py:288-295``) -- it never inspects
    *what* ``feedback_source`` points at. Passing the WP's own
    ``review-cycle-1.md`` (the ``--review-feedback-file`` shape from the
    ticket) is accepted: its full text -- frontmatter delimiters and all --
    is read as plain body content and written out as ``review-cycle-2.md``,
    fabricating a duplicate cycle that outranks the real reviewer's original
    verdict (``ReviewCycleArtifact.latest`` always returns the
    highest-numbered file).

    This test asserts the artifact-first, guard-second contract that would
    need to hold once #2996(b) is fixed. It is expected to fail (red) at the
    ``pytest.raises`` line TODAY, before the guard exists -- ``DID NOT RAISE``
    is the correct failure signature for a regression test pinning a missing
    guard, not a defect in the test itself.
    """
    from specify_cli.review.artifacts import ReviewCycleArtifact

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tasks_dir = repo / "kitty-specs" / MISSION_SLUG / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / f"{WP_SLUG}.md").write_text("# WP03\n", encoding="utf-8")
    wp_dir = tasks_dir / WP_SLUG

    real_feedback = tmp_path / "feedback.md"
    real_feedback.write_text(
        "**Issue**: Ledger grammar drops the census delimiter.\n",
        encoding="utf-8",
    )

    created = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=MISSION_SLUG,
        wp_id=WP_ID,
        wp_slug=WP_SLUG,
        feedback_source=real_feedback,
        reviewer_agent="reviewer-renata",
    )
    assert created.artifact_path == wp_dir / "review-cycle-1.md"
    assert created.artifact.reviewer_agent == "reviewer-renata"

    # Hand the WP's OWN canonical review-cycle-1.md back in as the feedback
    # source -- the exact ``--review-feedback-file <review-cycle-1.md path>``
    # shape from the ticket -- with an empty reviewer_agent (also from the
    # ticket).
    with pytest.raises(ReviewCycleError, match="review-cycle|duplicate|feedback"):
        create_rejected_review_cycle(
            main_repo_root=repo,
            mission_slug=MISSION_SLUG,
            wp_id=WP_ID,
            wp_slug=WP_SLUG,
            feedback_source=created.artifact_path,
            reviewer_agent="",
        )

    # These hold once the guard exists: no fabricated cycle-2, and the real
    # reviewer's cycle-1 verdict remains the authoritative "latest".
    assert not (wp_dir / "review-cycle-2.md").exists()
    latest = ReviewCycleArtifact.latest(wp_dir)
    assert latest is not None
    assert latest.reviewer_agent == "reviewer-renata"


@pytest.mark.regression
def test_new_cycle_body_never_duplicates_a_prior_cycle_file(tmp_path: Path) -> None:
    """General invariant (#2996(b)): no newly-written review-cycle artifact's
    ``body`` may be byte-identical to the full text of any prior
    ``review-cycle-*.md`` in the same WP directory.

    Demonstrates the live fabrication directly (no ``pytest.raises`` --
    today's code does NOT raise, it succeeds and duplicates): reusing
    cycle-1's own file as ``feedback_source`` for cycle-2 makes cycle-2's
    ``body`` equal to cycle-1's ENTIRE on-disk file (frontmatter + body),
    which trivially also equals cycle-1's own ``body`` is a strict subset --
    the assertion below pins the general "never a duplicate" contract and is
    expected to fail (red) today because the duplication is exactly what
    happens.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tasks_dir = repo / "kitty-specs" / MISSION_SLUG / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / f"{WP_SLUG}.md").write_text("# WP03\n", encoding="utf-8")
    wp_dir = tasks_dir / WP_SLUG

    real_feedback = tmp_path / "feedback.md"
    real_feedback.write_text(
        "**Issue**: Ledger grammar drops the census delimiter.\n",
        encoding="utf-8",
    )
    cycle1 = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=MISSION_SLUG,
        wp_id=WP_ID,
        wp_slug=WP_SLUG,
        feedback_source=real_feedback,
        reviewer_agent="reviewer-renata",
    )
    cycle1_full_text = cycle1.artifact_path.read_text(encoding="utf-8")

    cycle2 = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=MISSION_SLUG,
        wp_id=WP_ID,
        wp_slug=WP_SLUG,
        feedback_source=cycle1.artifact_path,
        reviewer_agent="",
    )

    prior_bodies = [
        p.read_text(encoding="utf-8")
        for p in wp_dir.glob("review-cycle-*.md")
        if p != cycle2.artifact_path
    ]
    assert cycle2.artifact.body not in prior_bodies, (
        "a newly-written review cycle's body duplicated a prior "
        f"review-cycle-*.md file verbatim:\n{cycle2.artifact.body!r}"
    )
    assert cycle1_full_text not in (cycle2.artifact.body,)
