"""Tests for the surviving team_projection seam: the per-WP team-field allowlist.

The D1 projection pipeline was deleted (#6); what remains — and what Team
Kitty ports when rendering WP detail from committed state — is
:data:`TEAM_WP_ALLOWED_FIELDS`, its deliberate exclusion set, and the closed
allowlist semantics those two sets define.
"""

from __future__ import annotations

import pytest

from specify_cli.team_projection import TEAM_WP_ALLOWED_FIELDS as PACKAGE_EXPORTED_ALLOWED
from specify_cli.team_projection.mission_view import (
    _ALL_RECOGNIZED_WP_FIELDS,
    _KNOWN_BUT_EXCLUDED_WP_FIELDS,
    TEAM_WP_ALLOWED_FIELDS,
    UnknownWPStateFieldError,
    _filter_wp_state,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class TestAllowlistContract:
    """The allowlist is a ported contract: its exact content is pinned."""

    def test_team_allowed_fields_exact_content(self) -> None:
        assert frozenset(
            {
                "lane",
                "actor",
                "last_transition_at",
                "last_event_id",
                "force_count",
                "agent",
                "assignee",
                "role",
                "agent_profile",
                "agent_profile_version",
                "model",
                "provider",
                "review",
                "tracker_refs",
                "subtasks",
                "review_result",
            }
        ) == TEAM_WP_ALLOWED_FIELDS

    def test_known_but_excluded_fields_exact_content(self) -> None:
        assert frozenset(
            {"shell_pid", "shell_pid_created_at", "notes"}
        ) == _KNOWN_BUT_EXCLUDED_WP_FIELDS

    def test_excluded_set_is_disjoint_from_allowed_set(self) -> None:
        assert not (_KNOWN_BUT_EXCLUDED_WP_FIELDS & TEAM_WP_ALLOWED_FIELDS)

    def test_all_recognized_is_the_union(self) -> None:
        assert _ALL_RECOGNIZED_WP_FIELDS == TEAM_WP_ALLOWED_FIELDS | _KNOWN_BUT_EXCLUDED_WP_FIELDS

    def test_package_root_reexports_module_constant(self) -> None:
        assert PACKAGE_EXPORTED_ALLOWED is TEAM_WP_ALLOWED_FIELDS


class TestFilterWpState:
    def test_keeps_only_allowed_fields_that_are_present(self) -> None:
        filtered = _filter_wp_state(
            {"lane": "doing", "actor": "robert", "subtasks": [{"t": 1}], "tracker_refs": None}
        )
        assert filtered == {
            "lane": "doing",
            "actor": "robert",
            "subtasks": [{"t": 1}],
            "tracker_refs": None,
        }

    def test_drops_known_but_excluded_fields_silently(self) -> None:
        filtered = _filter_wp_state({"lane": "doing", "shell_pid": 4242, "notes": "unreviewed"})
        assert filtered == {"lane": "doing"}

    def test_unknown_field_raises_closed_allowlist_error(self) -> None:
        with pytest.raises(UnknownWPStateFieldError) as refused:
            _filter_wp_state({"lane": "doing", "future_runtime_slot": "x"})
        assert "future_runtime_slot" in str(refused.value)

    def test_empty_state_filters_to_empty(self) -> None:
        assert _filter_wp_state({}) == {}
