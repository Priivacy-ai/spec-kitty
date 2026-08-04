"""RED-FIRST P0 reproduction of #2996(b) per ADR 2026-07-17-1
(docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md).
Intentionally FAILS until the product bug is fixed — a red mainline is the
honest signal of this release-blocking P0. Do NOT xfail/skip/quarantine to
green; fix the product. Tracking issue: #2996.

Extracted (landing fold: make ``@pytest.mark.regression`` mean exactly one
thing) from ``tests/review/test_cycle.py``, which carries only these two
regression-marked tests alongside several unrelated, passing
``review.cycle`` unit tests. Those tests, and the ``_init_repo`` helper they
share with this reproduction, stay in the original file untouched; this
module carries its own copy of the tiny helper so it has no import
dependency back onto that file.

Symptom: ``create_rejected_review_cycle`` never inspects what
``feedback_source`` points at (self-referential feedback: handing it a
WP's own prior ``review-cycle-N.md`` is silently accepted and duplicated
into a new cycle) and never deduplicates a new cycle's body against a
prior cycle's body (accidental re-paste of identical feedback text
fabricates a second, indistinguishable cycle). Expected red until #2996
closes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.review.cycle import ReviewCycleError, create_rejected_review_cycle

pytestmark = [pytest.mark.regression, pytest.mark.git_repo]

MISSION_SLUG = "annoying-bugs-sweep-01KYHQ9F"
WP_ID = "WP03"
WP_SLUG = "WP03-ledger-grammar"


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)


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
    #
    # The match pattern is deliberately narrower than the original
    # "review-cycle|duplicate|feedback": today's PRE-EXISTING guards ("Review
    # feedback file not found: ..." / "Review feedback file is empty: ...")
    # both contain the word "feedback", so that loose an alternation lets an
    # unrelated failure satisfy this assertion for the wrong reason. Only a
    # message that names the self-reference explicitly can match here.
    with pytest.raises(
        ReviewCycleError, match=r"own review-cycle|self-referential feedback"
    ) as exc_info:
        create_rejected_review_cycle(
            main_repo_root=repo,
            mission_slug=MISSION_SLUG,
            wp_id=WP_ID,
            wp_slug=WP_SLUG,
            feedback_source=created.artifact_path,
            reviewer_agent="",
        )

    # The operator's stated preference is loud failures WITH clear
    # instructions: the message must name what was wrong (feedback_source is
    # the WP's own prior review-cycle artifact) and tell the caller what to
    # do instead (pass the underlying reviewer feedback, not a prior cycle
    # artifact).
    message = str(exc_info.value)
    assert created.artifact_path.name in message, (
        "error message must name the offending review-cycle artifact so the "
        f"caller can identify it -- got: {message!r}"
    )
    assert any(
        word in message.lower() for word in ("instead", "use ", "pass ", "provide ")
    ), (
        "error message must be actionable -- it must tell the caller what to "
        f"do instead of the self-referential feedback_source -- got: {message!r}"
    )

    # These hold once the guard exists: no fabricated cycle-2, and the real
    # reviewer's cycle-1 verdict remains the authoritative "latest".
    assert not (wp_dir / "review-cycle-2.md").exists()
    latest = ReviewCycleArtifact.latest(wp_dir)
    assert latest is not None
    assert latest.reviewer_agent == "reviewer-renata"


def test_new_cycle_body_never_duplicates_a_prior_cycle_file(tmp_path: Path) -> None:
    """General invariant (#2996(b)): no newly-written review-cycle artifact's
    ``body`` may be byte-identical to a prior ``review-cycle-*.md`` artifact's
    ``body`` in the same WP directory.

    Pinned INDEPENDENTLY of the self-reference guard exercised by
    ``test_self_referential_feedback_source_is_rejected``: this test drives
    ``create_rejected_review_cycle`` with an ORDINARY feedback file (never a
    review-cycle artifact) whose *content happens to equal* cycle-1's body --
    modelling a reviewer accidentally re-pasting the same feedback text, not
    reusing a prior artifact file. That keeps this test outside the
    self-reference guard's blast radius, so the two tests pin two distinct,
    independently satisfiable contracts instead of colliding on the same
    call shape.

    Expected to fail (red) today at the ``not in prior_bodies`` assertion:
    nothing in ``create_rejected_review_cycle`` deduplicates against prior
    cycle bodies, so cycle-2 is written with a body identical to cycle-1's.
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
    cycle1 = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=MISSION_SLUG,
        wp_id=WP_ID,
        wp_slug=WP_SLUG,
        feedback_source=real_feedback,
        reviewer_agent="reviewer-renata",
    )

    # An ORDINARY feedback file -- never a review-cycle artifact -- whose
    # content happens to duplicate cycle-1's body verbatim.
    duplicate_feedback = tmp_path / "duplicate-feedback.md"
    duplicate_feedback.write_text(cycle1.artifact.body, encoding="utf-8")

    cycle2 = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=MISSION_SLUG,
        wp_id=WP_ID,
        wp_slug=WP_SLUG,
        feedback_source=duplicate_feedback,
        reviewer_agent="",
    )

    # Compare BODY to BODY (parsed, frontmatter-stripped) -- not raw on-disk
    # text -- so a fix that merely reshapes ``body`` (e.g. stripping
    # frontmatter before assignment) cannot cheaply green this assertion
    # while still writing a duplicate artifact.
    prior_bodies = [
        ReviewCycleArtifact.from_file(p).body
        for p in wp_dir.glob("review-cycle-*.md")
        if p != cycle2.artifact_path
    ]
    assert cycle2.artifact.body not in prior_bodies, (
        "a newly-written review cycle's body duplicated a prior "
        f"review-cycle-*.md artifact's body verbatim:\n{cycle2.artifact.body!r}"
    )

    latest = ReviewCycleArtifact.latest(wp_dir)
    assert latest is not None
    assert latest.reviewer_agent != "unknown", (
        "a fabricated duplicate cycle must not become 'latest' with an "
        "unattributed reviewer_agent -- got 'unknown'"
    )
