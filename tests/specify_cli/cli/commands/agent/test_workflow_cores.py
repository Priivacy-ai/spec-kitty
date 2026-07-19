"""Direct unit tests for ``workflow_cores.py`` (WP02, T014).

coord-authority-trio-degod-01KX7094: focused branch-coverage tests for the
pure(ish) helpers extracted from ``workflow.py`` during the ``implement``
(CC78)/``review`` (CC72)/``_resolve_review_context`` (CC37) decomposition —
in particular the four genuinely NEW pure helpers that did not exist as
named functions before this split (``pick_best_base_branch``,
``parse_dependency_wp_ids``, ``build_owned_files_review_pathspecs``,
``event_is_review_claim``), plus light direct coverage of the moved
renderers/classifiers/request dataclasses.

Marker: unit only -- no filesystem, no subprocess, no git (per the ``unit``
marker's contract in ``pytest.ini``); every function under test here takes
plain values in and returns a plain value/string out.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.cli.commands.agent import workflow_cores as cores
from specify_cli.status import AgentAssignment, Lane, StatusEvent

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# pick_best_base_branch (new, extracted from _resolve_review_context)
# ---------------------------------------------------------------------------


class TestPickBestBaseBranch:
    def test_empty_input_returns_none_and_sentinel_count(self) -> None:
        best, count = cores.pick_best_base_branch([])
        assert best is None
        assert count == -1

    def test_single_candidate_wins(self) -> None:
        best, count = cores.pick_best_base_branch([("main", 5)])
        assert best == "main"
        assert count == 5

    def test_fewest_commits_wins(self) -> None:
        best, count = cores.pick_best_base_branch(
            [("main", 10), ("2.x", 3), ("develop", 7)]
        )
        assert best == "2.x"
        assert count == 3

    def test_strict_less_than_keeps_first_scored_candidate_on_tie(self) -> None:
        """Matches the original ``count < best_count`` comparison: a TIE keeps
        the earliest-scored candidate, it does not overwrite on ``<=``."""
        best, count = cores.pick_best_base_branch(
            [("main", 4), ("develop", 4), ("2.x", 4)]
        )
        assert best == "main"
        assert count == 4

    def test_zero_count_candidate_is_picked_over_positive_counts(self) -> None:
        best, count = cores.pick_best_base_branch([("main", 0), ("develop", 9)])
        assert best == "main"
        assert count == 0


# ---------------------------------------------------------------------------
# parse_dependency_wp_ids (new, extracted from _resolve_review_context)
# ---------------------------------------------------------------------------


class TestParseDependencyWpIds:
    def test_no_dependencies_key_returns_empty(self) -> None:
        assert cores.parse_dependency_wp_ids("work_package_id: WP01\n") == []

    def test_empty_dependencies_list_returns_empty(self) -> None:
        assert cores.parse_dependency_wp_ids("dependencies: []\n") == []

    def test_single_dependency_quoted(self) -> None:
        assert cores.parse_dependency_wp_ids('dependencies: ["WP01"]\n') == ["WP01"]

    def test_multiple_dependencies_quoted(self) -> None:
        assert cores.parse_dependency_wp_ids('dependencies: ["WP01", "WP02"]\n') == [
            "WP01",
            "WP02",
        ]

    def test_multiple_dependencies_unquoted(self) -> None:
        assert cores.parse_dependency_wp_ids("dependencies: [WP01, WP02]\n") == [
            "WP01",
            "WP02",
        ]

    def test_ignores_unrelated_frontmatter(self) -> None:
        frontmatter = (
            'work_package_id: "WP03"\n'
            'title: "Some WP"\n'
            'dependencies: ["WP01"]\n'
            'agent: "claude"\n'
        )
        assert cores.parse_dependency_wp_ids(frontmatter) == ["WP01"]


# ---------------------------------------------------------------------------
# build_owned_files_review_pathspecs (new, dedupes review()'s two inline
# blocks -- S1192)
# ---------------------------------------------------------------------------


class TestBuildOwnedFilesReviewPathspecs:
    def test_empty_owned_files_returns_empty(self) -> None:
        assert cores.build_owned_files_review_pathspecs([], "my-mission") == []

    def test_files_outside_mission_root_pass_through_unmodified(self) -> None:
        owned = ["src/specify_cli/foo.py", "tests/test_foo.py"]
        result = cores.build_owned_files_review_pathspecs(owned, "my-mission")
        assert result == owned

    def test_mission_root_files_get_status_and_tasks_excludes(self) -> None:
        owned = ["kitty-specs/my-mission/spec.md", "src/foo.py"]
        result = cores.build_owned_files_review_pathspecs(owned, "my-mission")
        assert result[:2] == owned
        assert ":(exclude)kitty-specs/my-mission/tasks/**" in result
        assert ":(exclude)kitty-specs/my-mission/tasks.md" in result
        assert ":(exclude)kitty-specs/my-mission/status.events.jsonl" in result
        assert ":(exclude)kitty-specs/my-mission/status.json" in result

    def test_excludes_only_added_once_even_with_multiple_mission_root_files(
        self,
    ) -> None:
        owned = [
            "kitty-specs/my-mission/spec.md",
            "kitty-specs/my-mission/plan.md",
        ]
        result = cores.build_owned_files_review_pathspecs(owned, "my-mission")
        assert result.count(":(exclude)kitty-specs/my-mission/tasks/**") == 1


# ---------------------------------------------------------------------------
# event_is_review_claim (new, dedupes the shared predicate from
# _find_first_for_review_wp / review())
# ---------------------------------------------------------------------------


def _event(*, to_lane: Lane, review_ref: str | None) -> StatusEvent:
    return StatusEvent(
        event_id="01TESTEVENT00000000000001",
        mission_slug="trio-mission",
        wp_id="WP01",
        from_lane=Lane.FOR_REVIEW,
        to_lane=to_lane,
        at="2026-01-01T00:00:00+00:00",
        actor="reviewer-renata",
        force=False,
        execution_mode="worktree",
        review_ref=review_ref,
    )


class TestEventIsReviewClaim:
    def test_new_canonical_shape_in_review_is_claimed(self) -> None:
        assert cores.event_is_review_claim(_event(to_lane=Lane.IN_REVIEW, review_ref=None)) is True

    def test_legacy_shape_in_progress_with_sentinel_is_claimed(self) -> None:
        event = _event(to_lane=Lane.IN_PROGRESS, review_ref="action-review-claim")
        assert cores.event_is_review_claim(event) is True

    def test_in_progress_without_sentinel_is_not_claimed(self) -> None:
        event = _event(to_lane=Lane.IN_PROGRESS, review_ref=None)
        assert cores.event_is_review_claim(event) is False

    def test_for_review_lane_is_not_claimed(self) -> None:
        event = _event(to_lane=Lane.FOR_REVIEW, review_ref=None)
        assert cores.event_is_review_claim(event) is False

    def test_approved_lane_is_not_claimed(self) -> None:
        event = _event(to_lane=Lane.APPROVED, review_ref=None)
        assert cores.event_is_review_claim(event) is False


# ---------------------------------------------------------------------------
# Request dataclasses (T009/T010)
# ---------------------------------------------------------------------------


class TestRequestDataclasses:
    def test_implement_request_is_frozen(self) -> None:
        request = cores.ImplementRequest(
            wp_id="WP01",
            mission="my-mission",
            agent="claude",
            allow_sparse_checkout=False,
            acknowledge_not_bulk_edit=False,
        )
        assert request.wp_id == "WP01"
        with pytest.raises(AttributeError):
            request.wp_id = "WP02"

    def test_review_request_is_frozen(self) -> None:
        request = cores.ReviewRequest(wp_id="WP01", mission="my-mission", agent="reviewer-renata")
        assert request.agent == "reviewer-renata"
        with pytest.raises(AttributeError):
            request.agent = "someone-else"


# ---------------------------------------------------------------------------
# Light direct coverage of the moved renderers/classifiers (behaviour
# preservation for the T007 move, not new logic)
# ---------------------------------------------------------------------------


class TestMovedRenderersAndClassifiers:
    def test_normalize_wp_id_variants(self) -> None:
        assert cores.normalize_wp_id("wp01") == "WP01"
        assert cores.normalize_wp_id("WP01-some-slug") == "WP01"
        assert cores.normalize_wp_id("3") == "WP3"

    def test_render_isolation_banner_implement_mentions_subtasks(self) -> None:
        lines = cores.render_isolation_banner("WP01", "implement")
        text = "\n".join(lines)
        assert "YOU ARE ASSIGNED TO: WP01" in text
        assert "subtasks belonging to WP01" in text

    def test_render_isolation_banner_review_mentions_review_ownership(self) -> None:
        lines = cores.render_isolation_banner("WP01", "review")
        text = "\n".join(lines)
        assert "YOU ARE REVIEWING: WP01" in text
        assert "Review or approve any WP other than WP01" in text

    def test_render_wp_prompt_wrapper_wraps_content(self) -> None:
        lines = cores.render_wp_prompt_wrapper("WP BODY TEXT")
        text = "\n".join(lines)
        assert "WORK PACKAGE PROMPT BEGINS" in text
        assert "WP BODY TEXT" in text
        assert "WORK PACKAGE PROMPT ENDS" in text

    def test_render_resolved_agent_identity_defaults(self) -> None:
        assignment = AgentAssignment(tool="claude", model="sonnet", profile_id=None, role=None)
        lines = cores.render_resolved_agent_identity(assignment)
        text = "\n".join(lines)
        assert "tool       : claude" in text
        assert "profile_id : (default)" in text
        assert "role       : (default)" in text

    def test_is_missing_canonical_status_error_true_for_typed_exception(self) -> None:
        from specify_cli.status import CanonicalStatusNotFoundError

        assert cores.is_missing_canonical_status_error(CanonicalStatusNotFoundError("boom")) is True

    def test_is_missing_canonical_status_error_false_for_other_exception(self) -> None:
        assert cores.is_missing_canonical_status_error(RuntimeError("boom")) is False

    def test_missing_canonical_status_message_without_feature_dir(self) -> None:
        message = cores.missing_canonical_status_message("WP01", "my-mission")
        assert "WP01" in message
        assert "finalize-tasks" in message
        assert "my-mission" in message

    def test_auto_claim_failure_message_dependency_reason(self) -> None:
        class _Preview:
            selection_reason = "dependencies_not_satisfied"

        message = cores.auto_claim_failure_message(_Preview())
        assert "dependencies_not_satisfied" in message

    def test_auto_claim_failure_message_default(self) -> None:
        message = cores.auto_claim_failure_message(None)
        assert "No planned work packages found" in message


# ---------------------------------------------------------------------------
# review_feedback_root (structural navigation, no filesystem touch)
# ---------------------------------------------------------------------------


class TestReviewFeedbackRoot:
    def test_navigates_two_levels_up_from_feature_dir(self) -> None:
        feature_dir = Path("/repo/kitty-specs/my-mission")
        assert cores.review_feedback_root(feature_dir) == Path("/repo")
