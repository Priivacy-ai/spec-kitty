from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from mission_runtime import MissionArtifactKind
from specify_cli.agent_tasks_ports import (
    CommitArtifactResult,
    CommitStatusResult,
    MissionHandle,
)
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.review.cycle import (
    ReviewCycleError,
    build_review_cycle_pointer,
    create_rejected_review_cycle,
    resolve_review_cycle_pointer,
    validate_review_artifact_file,
    validate_review_cycle_pointer,
)
from specify_cli.status import TransitionRequest

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


@pytest.mark.regression
def test_new_cycle_body_never_duplicates_a_prior_cycle_file(tmp_path: Path) -> None:
    """General invariant (#2996(b)): a new review-cycle write must be REFUSED
    when its ``feedback_source`` content is byte-identical (after frontmatter
    stripping + whitespace normalization) to a prior ``review-cycle-*.md``
    artifact's body in the same WP directory.

    Pinned INDEPENDENTLY of the self-reference guard exercised by
    ``test_self_referential_feedback_source_is_rejected``: this test drives
    ``create_rejected_review_cycle`` with an ORDINARY feedback file (never a
    review-cycle artifact) whose *content happens to equal* cycle-1's body --
    modelling a reviewer accidentally re-pasting the same feedback text, not
    reusing a prior artifact file. That keeps this test outside the
    self-reference guard's blast radius, so the two tests pin two distinct,
    independently satisfiable contracts instead of colliding on the same
    call shape.

    Per this mission's finalized design (spec.md Acceptance Scenario 2's "the
    operation is refused"), a content duplicate must raise -- not silently
    write a second, wrapped cycle. This test was rewritten out of its
    pre-mission-design, non-raising shape (a post-tasks squad flagged that
    shape as a shortcut trap: satisfying its old assertions by merely
    reshaping ``body`` would reward the wrong implementation instead of a
    genuine refusal).
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

    with pytest.raises(ReviewCycleError, match=r"duplicates a prior review-cycle"):
        create_rejected_review_cycle(
            main_repo_root=repo,
            mission_slug=MISSION_SLUG,
            wp_id=WP_ID,
            wp_slug=WP_SLUG,
            feedback_source=duplicate_feedback,
            reviewer_agent="",
        )

    # The refusal means cycle 2 is never written at all -- "latest" naturally
    # stays cycle 1, with its real reviewer_agent (not a fabricated "unknown").
    assert not (wp_dir / "review-cycle-2.md").exists()
    latest = ReviewCycleArtifact.latest(wp_dir)
    assert latest is not None
    assert latest.cycle_number == 1
    assert latest.reviewer_agent == "reviewer-renata"


@pytest.mark.regression
def test_hand_edited_own_path_feedback_source_is_still_rejected(tmp_path: Path) -> None:
    """T006 step 2: a feedback file at a ``review-cycle-N.md``-shaped path
    inside the WP's OWN directory is refused even when its content has been
    hand-edited to no longer duplicate any existing cycle's body.

    Both ``test_self_referential_feedback_source_is_rejected`` (exact-path,
    exact-content) and ``test_new_cycle_body_never_duplicates_a_prior_cycle_file``
    (content-only, different path) can each be satisfied by a fix that only
    implements ONE of the two checks. This is the case that forces genuine
    path-based detection to exist alongside content-based detection: the path
    is the WP's own review-cycle home, but the content is deliberately
    different from every existing cycle's body.
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
    created = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=MISSION_SLUG,
        wp_id=WP_ID,
        wp_slug=WP_SLUG,
        feedback_source=real_feedback,
        reviewer_agent="reviewer-renata",
    )

    # Hand-edit cycle-1's own file in place: same path, deliberately DIFFERENT
    # (non-duplicate) content.
    created.artifact_path.write_text(
        "---\nverdict: rejected\n---\n\nThis text does not match any prior body.\n",
        encoding="utf-8",
    )

    with pytest.raises(ReviewCycleError, match=r"own review-cycle"):
        create_rejected_review_cycle(
            main_repo_root=repo,
            mission_slug=MISSION_SLUG,
            wp_id=WP_ID,
            wp_slug=WP_SLUG,
            feedback_source=created.artifact_path,
            reviewer_agent="reviewer-renata",
        )

    assert not (wp_dir / "review-cycle-2.md").exists()


@pytest.mark.regression
def test_unreadable_prior_cycle_does_not_crash_the_provenance_scan(
    tmp_path: Path,
) -> None:
    """M3 (adversarial squad, PR #3156): a prior ``review-cycle-N.md`` that is
    not valid UTF-8 must be SKIPPED by the provenance scan, not crash it.

    ``_guard_feedback_source_provenance`` best-effort-falls-back on
    ``ValueError`` from ``ReviewCycleArtifact.from_file`` by re-reading the
    same file with the same ``encoding="utf-8"`` -- which raises the
    IDENTICAL ``UnicodeDecodeError`` (a ``ValueError`` subclass) a second
    time, this time uncaught. One non-UTF-8 or unreadable prior artifact in a
    WP dir then bricks EVERY subsequent review-cycle write for that WP. An
    unparseable/unreadable prior artifact cannot be the duplicate being
    searched for, so it must simply be skipped.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tasks_dir = repo / "kitty-specs" / MISSION_SLUG / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / f"{WP_SLUG}.md").write_text("# WP03\n", encoding="utf-8")
    wp_dir = tasks_dir / WP_SLUG
    wp_dir.mkdir(parents=True)

    # A prior "review-cycle-1.md" that is NOT valid UTF-8 (and thus also not
    # parseable as frontmatter) -- simulates a corrupted or binary-garbled
    # prior artifact reaching the provenance scan.
    (wp_dir / "review-cycle-1.md").write_bytes(b"---\nverdict: rejected\n---\n\n\xff\xfe\x00bad")

    real_feedback = tmp_path / "feedback.md"
    real_feedback.write_text(
        "**Issue**: New, unrelated feedback.\n", encoding="utf-8"
    )

    created = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=MISSION_SLUG,
        wp_id=WP_ID,
        wp_slug=WP_SLUG,
        feedback_source=real_feedback,
        reviewer_agent="reviewer-renata",
    )

    assert created.artifact_path == wp_dir / "review-cycle-2.md"
    assert created.artifact.verdict == "rejected"


def test_create_rejected_review_cycle_with_approved_verdict(tmp_path: Path) -> None:
    """T006 step 3: the generalized writer, called with ``verdict="approved"``
    against a WP whose latest artifact is ``rejected``, writes a new
    highest-numbered artifact with ``verdict: approved`` and a real
    ``reviewer_agent``.
    """
    from specify_cli.review.artifacts import ReviewCycleArtifact

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tasks_dir = repo / "kitty-specs" / "001-mission" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-core.md").write_text("# WP01\n", encoding="utf-8")

    rejection_feedback = tmp_path / "rejection-feedback.md"
    rejection_feedback.write_text("**Issue**: Missing regression test.\n", encoding="utf-8")
    rejected_cycle = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug="001-mission",
        wp_id="WP01",
        wp_slug="WP01-core",
        feedback_source=rejection_feedback,
        reviewer_agent="reviewer-renata",
    )
    assert rejected_cycle.artifact.verdict == "rejected"

    approval_feedback = tmp_path / "approval-feedback.md"
    approval_feedback.write_text(
        "Approved by reviewer-renata: the missing test was added.\n", encoding="utf-8"
    )
    approved_cycle = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug="001-mission",
        wp_id="WP01",
        wp_slug="WP01-core",
        feedback_source=approval_feedback,
        reviewer_agent="reviewer-renata",
        verdict="approved",
    )

    assert approved_cycle.artifact.verdict == "approved"
    assert approved_cycle.artifact.cycle_number == 2
    assert approved_cycle.artifact.reviewer_agent == "reviewer-renata"
    assert approved_cycle.review_result.verdict == "approved"

    latest = ReviewCycleArtifact.latest(tasks_dir / "WP01-core")
    assert latest is not None
    assert latest.verdict == "approved"
    assert latest.cycle_number == 2


def _unprotect_main(repo: Path) -> None:
    """Disable branch protection so a real commit lands on ``main`` (T006 step 4).

    Mirrors ``tests/coordination/test_analysis_report_rehome.py``'s
    ``_disable_branch_protection`` fixture idiom.
    """
    kittify_dir = repo / ".kittify"
    kittify_dir.mkdir(parents=True, exist_ok=True)
    (kittify_dir / "config.yaml").write_text(
        "protection:\n  protected_branches: []\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "test: unprotect main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_create_rejected_review_cycle_commits_the_written_artifact(tmp_path: Path) -> None:
    """T006 step 4 / T004: passing a ``commit_router`` actually commits the write.

    Real git-fixture repo (real ``git init``), the REAL ``RealCoordCommitRouter``
    (no stubbed ``safe_commit`` -- NFR-001), post-call proof read straight from
    ``git status --porcelain`` and ``git log`` -- mirrors quickstart.md's FR-001
    commit-step verification and the fixture idiom in
    ``tests/coordination/test_analysis_report_rehome.py``.
    """
    from specify_cli.agent_tasks_ports import RealCoordCommitRouter

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tasks_dir = repo / "kitty-specs" / "001-mission" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-core.md").write_text("# WP01\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True
    )
    _unprotect_main(repo)

    feedback = tmp_path / "feedback.md"
    feedback.write_text("**Issue**: Needs another pass.\n", encoding="utf-8")

    created = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug="001-mission",
        wp_id="WP01",
        wp_slug="WP01-core",
        feedback_source=feedback,
        reviewer_agent="reviewer-renata",
        commit_router=RealCoordCommitRouter(),
    )

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    rel = str(created.artifact_path.relative_to(repo))
    assert rel not in status.stdout, (
        f"the written artifact is NOT committed -- git status still shows it:\n"
        f"{status.stdout}"
    )

    log = subprocess.run(
        ["git", "log", "-1", "--name-only", "--pretty=format:"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "review-cycle-1.md" in log.stdout


@dataclass
class _FailingCommitRouter:
    """Stub ``CoordCommitRouter`` whose ``commit_artifact`` simulates a real
    commit failure (mirrors what ``commit_for_mission`` returns when it catches
    a ``ProtectedBranchRefused``/``CalledProcessError`` -- see
    ``coordination/commit_router.py``'s ``_STATUS_ERROR`` branch) without
    needing a real protected-branch git fixture. Modeled on
    ``_RecordingCoordRouter`` in
    ``test_tasks_move_task_pre_review_gate_observability.py``.
    """

    calls: list[Path] = field(default_factory=list)

    def feature_write_dir(self, mission: MissionHandle) -> Path:
        raise AssertionError("feature_write_dir is not used by this call site")

    def commit_status(
        self,
        request: TransitionRequest,
        *,
        capability: GuardCapability,
    ) -> CommitStatusResult:
        raise AssertionError("commit_status is not used by this call site")

    def commit_artifact(
        self,
        mission: MissionHandle,
        paths: Sequence[Path],
        message: str,
        *,
        kind: MissionArtifactKind,
        policy: ProtectionPolicy,
    ) -> CommitArtifactResult:
        self.calls.extend(paths)
        return CommitArtifactResult(
            status="error",
            placement_ref=str(paths[0]) if paths else "",
            diagnostic="simulated ProtectedBranchRefused: destination branch is protected",
        )


def test_create_rejected_review_cycle_raises_when_commit_fails(tmp_path: Path) -> None:
    """Cycle 2 fix (#2697) + M2 (adversarial squad, PR #3156): a non-
    ``"committed"`` ``CommitArtifactResult`` must surface as a hard failure
    AND roll back the orphaned write -- not merely surface the failure while
    stranding an uncommitted artifact on disk.

    Before the M2 rollback fix, the write and the commit were not atomic: a
    failed commit left ``review-cycle-1.md`` on disk with no rollback. A
    rejection retry would then hit the content-identity guard against its
    own orphan ("duplicates a prior review-cycle artifact") and be refused
    forever, permanently bricking the WP. Rolling back on failure means the
    failure state is "no artifact" -- not "uncommitted artifact" -- so an
    immediate retry with the SAME feedback succeeds cleanly.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tasks_dir = repo / "kitty-specs" / "001-mission" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-core.md").write_text("# WP01\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True
    )
    _unprotect_main(repo)
    feedback = tmp_path / "feedback.md"
    feedback.write_text("**Issue**: Needs another pass.\n", encoding="utf-8")

    router = _FailingCommitRouter()

    with pytest.raises(ReviewCycleError, match="Failed to commit"):
        create_rejected_review_cycle(
            main_repo_root=repo,
            mission_slug="001-mission",
            wp_id="WP01",
            wp_slug="WP01-core",
            feedback_source=feedback,
            reviewer_agent="reviewer-renata",
            commit_router=router,
        )

    # The router WAS invoked once, with the written artifact path -- the
    # failure is real, not swallowed.
    artifact_path = tasks_dir / "WP01-core" / "review-cycle-1.md"
    assert router.calls == [artifact_path]
    # M2: the failed write is rolled back -- no orphaned artifact survives.
    assert not artifact_path.exists(), (
        "a failed commit must roll back its write -- an orphaned, "
        "uncommitted artifact would permanently brick a retry"
    )
    assert not list((tasks_dir / "WP01-core").glob("review-cycle-*.md")), (
        "no review-cycle-*.md should survive a rolled-back commit failure"
    )

    # An immediate retry with the SAME feedback, now with a working commit
    # router, must succeed and land as cycle 1 again -- proving the orphan's
    # phantom count did not inflate ``next_cycle_number``.
    from specify_cli.agent_tasks_ports import RealCoordCommitRouter

    retried = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug="001-mission",
        wp_id="WP01",
        wp_slug="WP01-core",
        feedback_source=feedback,
        reviewer_agent="reviewer-renata",
        commit_router=RealCoordCommitRouter(),
    )
    assert retried.artifact_path == artifact_path
    assert retried.artifact.cycle_number == 1


def test_create_rejected_review_cycle_without_commit_router_is_unchanged(
    tmp_path: Path,
) -> None:
    """T006 step 5: backward compatibility -- omitting ``verdict``/``commit_router``
    (every existing caller's shape) still produces identical ``rejected``,
    uncommitted behavior.
    """
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

    assert created.artifact.verdict == "rejected"
    assert created.review_result.verdict == "changes_requested"
    assert created.artifact_path == tasks_dir / "WP01-core" / "review-cycle-1.md"
    assert created.artifact_path.exists()
    # No commit_router was supplied -- the write must remain uncommitted:
    # nothing under kitty-specs/ has ever been staged/committed in this
    # fixture, so git still reports it as untracked.
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "kitty-specs" in status.stdout, (
        "an uncommitted write should still show as untracked in git status"
    )


def test_create_rejected_review_cycle_completes_within_a_fixed_time_budget(
    tmp_path: Path,
) -> None:
    """NFR-003: one write + one ``commit_artifact`` call completes quickly.

    A fixed-budget check (not a before/after benchmark) is proportionate here:
    the new work per write is one filesystem write plus one additional git
    commit -- the same shape the existing rejection path already performs
    today.
    """
    import time

    from specify_cli.agent_tasks_ports import RealCoordCommitRouter

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tasks_dir = repo / "kitty-specs" / "001-mission" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-core.md").write_text("# WP01\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True
    )
    _unprotect_main(repo)

    feedback = tmp_path / "feedback.md"
    feedback.write_text("**Issue**: Needs another pass.\n", encoding="utf-8")

    started = time.perf_counter()
    create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug="001-mission",
        wp_id="WP01",
        wp_slug="WP01-core",
        feedback_source=feedback,
        reviewer_agent="reviewer-renata",
        commit_router=RealCoordCommitRouter(),
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0, (
        f"create_rejected_review_cycle (write + commit) took {elapsed:.3f}s, "
        "expected under a generous 2s fixed budget on CI hardware"
    )
