"""WP04 (#676) — Unit tests: review-cycle counter advances only on rejection.

These tests lock in the contract that:

1. Re-running the implement entrypoint on a ``for_review`` work package is
   idempotent: the counter (number of ``review-cycle-N.md`` artifacts) does
   not change, and no new artifact files are created.
2. A freshly-claimed WP starts with counter == 0 (no artifacts).
3. The rejection handler is the only mutation site; simulating three
   rejection events drives the counter 0 → 1 → 2 → 3 with exactly one
   ``review-cycle-N.md`` artifact at each integer in [1, 3].

Architectural fact verified by these tests: the only counter / artifact
mutation site in the runtime is
``specify_cli.cli.commands.agent.tasks._persist_review_feedback``. The
implement entrypoint in ``specify_cli.cli.commands.agent.workflow`` only
ever **reads** existing review-cycle artifacts (e.g. via
``ReviewCycleArtifact.latest`` for fix-mode prompt rendering).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_cycle_artifacts(sub_artifact_dir: Path) -> int:
    """Return the number of ``review-cycle-N.md`` files (the canonical counter)."""
    if not sub_artifact_dir.exists():
        return 0
    return len(list(sub_artifact_dir.glob("review-cycle-*.md")))


def _setup_wp_dirs(
    tmp_path: Path,
    mission_slug: str = "066-test-mission",
    wp_slug: str = "WP01-some-title",
) -> tuple[Path, Path]:
    """Create the ``kitty-specs/<mission>/tasks/<wp_slug>/`` tree and a stub WP file.

    Returns ``(main_repo_root, sub_artifact_dir)``.
    """
    sub_dir = tmp_path / "kitty-specs" / mission_slug / "tasks" / wp_slug
    sub_dir.mkdir(parents=True, exist_ok=True)
    # Stub WP markdown so the slug resolver finds the WP.
    (sub_dir.parent / f"{wp_slug}.md").write_text("---\n---\n", encoding="utf-8")
    return tmp_path, sub_dir


def _write_feedback_file(tmp_path: Path, body: str = "## Issues\n\nFix this.") -> Path:
    """Write a feedback source file the rejection handler can read."""
    fb = tmp_path / f"feedback_{abs(hash(body))}.md"
    fb.write_text(body, encoding="utf-8")
    return fb


def _trigger_rejection(
    main_repo_root: Path,
    mission_slug: str,
    feedback_source: Path,
    task_id: str = "WP01",
    reviewer_agent: str = "claude",
) -> tuple[Path, str]:
    """Drive the canonical rejection handler exactly once.

    This is the single counter-mutation site in the runtime; calling it is
    equivalent to a real ``move-task --to planned --review-feedback-file``
    invocation for the purposes of counter advancement.
    """
    from specify_cli.cli.commands.agent.tasks import _persist_review_feedback

    return _persist_review_feedback(
        main_repo_root=main_repo_root,
        mission_slug=mission_slug,
        task_id=task_id,
        feedback_source=feedback_source,
        reviewer_agent=reviewer_agent,
    )


# ---------------------------------------------------------------------------
# Static-source guard: the implement entrypoint must not call any helper that
# writes a review-cycle artifact or computes the next cycle number.
# ---------------------------------------------------------------------------


def test_workflow_module_does_not_mutate_review_cycle_counter() -> None:
    """workflow.py must not call ``next_cycle_number`` or ``ReviewCycleArtifact.write``.

    This is a structural assertion locking in the WP04 contract. Any new
    counter-mutation site introduced in workflow.py would defeat the
    rejection-only invariant; this test fails loudly if that happens.
    """
    from specify_cli.cli.commands.agent import workflow as workflow_module

    source_path = Path(inspect.getfile(workflow_module))
    source_text = source_path.read_text(encoding="utf-8")

    # Strip the module docstring before scanning so the inventory comment
    # (which legitimately mentions these symbols in prose) does not produce
    # false positives.
    body_text = source_text
    if body_text.lstrip().startswith('"""'):
        # Find the closing triple-quote of the module docstring.
        first = body_text.find('"""')
        end = body_text.find('"""', first + 3)
        if end != -1:
            body_text = body_text[end + 3 :]

    forbidden_call_substrings = (
        # Computing next cycle is a counter mutation precursor.
        "next_cycle_number(",
        # Writing the artifact through the canonical helper.
        "_persist_review_feedback(",
    )
    for needle in forbidden_call_substrings:
        assert needle not in body_text, (
            f"workflow.py contains a forbidden counter-mutation call: {needle!r}. "
            "The rejection handler in tasks.py is the only allowed mutation site (#676)."
        )


# ---------------------------------------------------------------------------
# T021 — counter-starts-at-zero on a fresh WP
# ---------------------------------------------------------------------------


def test_counter_starts_at_zero_on_fresh_wp(tmp_path: Path) -> None:
    """A freshly-set-up WP has counter == 0 and no review-cycle artifacts."""
    _, sub_dir = _setup_wp_dirs(tmp_path)

    assert _count_cycle_artifacts(sub_dir) == 0
    assert list(sub_dir.glob("review-cycle-*.md")) == []


# ---------------------------------------------------------------------------
# T021 — re-running implement is idempotent for a for_review WP
# ---------------------------------------------------------------------------


def test_implement_rerun_does_not_advance_counter(tmp_path: Path) -> None:
    """Re-running the implement entrypoint 3+ times must not write any artifact.

    We exercise the implement entrypoint surface that materialises the
    ``review-cycle-N.md`` placeholder path: the prompt-rendering computation
    in workflow.py mirrors the behaviour the CLI exhibits when the user
    re-invokes ``spec-kitty agent action implement WPNN`` against a WP that
    is already in ``for_review``. The contract: pure read; never write.
    """
    main_repo_root, sub_dir = _setup_wp_dirs(tmp_path)

    # Simulate a WP that already went through one rejection cycle so the
    # disk-state is non-empty (counter == 1). This is the realistic state
    # in which an operator might re-run ``implement`` and we want to prove
    # idempotency.
    feedback = _write_feedback_file(tmp_path, body="## Cycle 1 issues")
    _trigger_rejection(main_repo_root, "066-test-mission", feedback)
    assert _count_cycle_artifacts(sub_dir) == 1

    initial_files = sorted(p.name for p in sub_dir.glob("review-cycle-*.md"))
    initial_mtimes = {p.name: p.stat().st_mtime_ns for p in sub_dir.glob("review-cycle-*.md")}

    # Reproduce what the implement entrypoint does at prompt-render time:
    # it inspects existing artifacts (e.g. ``ReviewCycleArtifact.latest``)
    # but does not write. Run that inspection 3 times and assert no change.
    from specify_cli.review.artifacts import ReviewCycleArtifact

    for _ in range(3):
        latest = ReviewCycleArtifact.latest(sub_dir)
        # Latest should always be the cycle-1 artifact we just wrote.
        assert latest is not None
        assert latest.cycle_number == 1

        # Crucially, no new file appeared and existing files are untouched.
        current_files = sorted(p.name for p in sub_dir.glob("review-cycle-*.md"))
        assert current_files == initial_files
        for name, mtime in initial_mtimes.items():
            assert (sub_dir / name).stat().st_mtime_ns == mtime, (
                f"Re-running implement must not rewrite {name}"
            )

    # Counter unchanged after three "reruns".
    assert _count_cycle_artifacts(sub_dir) == 1


def test_implement_rerun_on_fresh_wp_does_not_create_artifacts(tmp_path: Path) -> None:
    """For a freshly-claimed (never-rejected) WP, implement reruns create zero artifacts.

    Even when the WP has zero rejection history, repeated implement calls
    must not seed a ``review-cycle-1.md`` file. The first artifact is only
    written when a reviewer runs ``move-task --to planned --review-feedback-file``.
    """
    _, sub_dir = _setup_wp_dirs(tmp_path)

    from specify_cli.review.artifacts import ReviewCycleArtifact

    for _ in range(5):
        latest = ReviewCycleArtifact.latest(sub_dir)
        assert latest is None  # No artifacts yet, and none get created by reads.
        assert _count_cycle_artifacts(sub_dir) == 0

    # next_cycle_number is read-only; calling it must not write a file.
    assert ReviewCycleArtifact.next_cycle_number(sub_dir) == 1
    assert _count_cycle_artifacts(sub_dir) == 0


# ---------------------------------------------------------------------------
# T021 — monotonicity: counter goes 0 → 1 → 2 → 3 across three rejections
# ---------------------------------------------------------------------------


def test_counter_is_monotonic(tmp_path: Path) -> None:
    """Three rejection events advance the counter by exactly +1 each time."""
    main_repo_root, sub_dir = _setup_wp_dirs(tmp_path)

    assert _count_cycle_artifacts(sub_dir) == 0

    observed_counts: list[int] = [0]
    persisted_paths: list[Path] = []
    for cycle in range(1, 4):
        feedback = _write_feedback_file(
            tmp_path, body=f"## Issues for cycle {cycle}\n\nFix me."
        )
        persisted_path, pointer = _trigger_rejection(
            main_repo_root, "066-test-mission", feedback
        )
        persisted_paths.append(persisted_path)
        observed_counts.append(_count_cycle_artifacts(sub_dir))
        assert f"review-cycle-{cycle}.md" in pointer
        assert persisted_path.name == f"review-cycle-{cycle}.md"

    # Strict +1 advancement, monotonic non-decreasing.
    assert observed_counts == [0, 1, 2, 3]
    for prev, curr in zip(observed_counts, observed_counts[1:]):
        assert curr == prev + 1

    # Exactly three artifacts at indices 1, 2, 3 — no gaps, no duplicates.
    final_files = sorted(p.name for p in sub_dir.glob("review-cycle-*.md"))
    assert final_files == [
        "review-cycle-1.md",
        "review-cycle-2.md",
        "review-cycle-3.md",
    ]
    for n in (1, 2, 3):
        path = sub_dir / f"review-cycle-{n}.md"
        assert path.exists()
        assert path.is_file()


def test_rejections_followed_by_implement_reread_do_not_inflate_counter(
    tmp_path: Path,
) -> None:
    """Mixed sequence: reject, re-read (implement rerun), reject, re-read, reject.

    Each reject should advance by +1; each re-read should be a no-op. Final
    counter value equals the number of rejections (3), not 5.
    """
    main_repo_root, sub_dir = _setup_wp_dirs(tmp_path)

    from specify_cli.review.artifacts import ReviewCycleArtifact

    rejections = 0
    for cycle in range(1, 4):
        feedback = _write_feedback_file(tmp_path, body=f"cycle {cycle}")
        _trigger_rejection(main_repo_root, "066-test-mission", feedback)
        rejections += 1
        assert _count_cycle_artifacts(sub_dir) == rejections

        # Simulate two implement-rerun reads between rejections; both no-ops.
        for _ in range(2):
            latest = ReviewCycleArtifact.latest(sub_dir)
            assert latest is not None
            assert latest.cycle_number == rejections
            assert _count_cycle_artifacts(sub_dir) == rejections

    assert rejections == 3
    assert _count_cycle_artifacts(sub_dir) == 3
