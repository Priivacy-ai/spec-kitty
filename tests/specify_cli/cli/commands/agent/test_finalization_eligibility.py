"""Unit tests for the pure finalization eligibility projection."""

from __future__ import annotations

import pytest

from specify_cli.cli.commands.agent.finalization_eligibility import (
    filter_by_wp_ids,
    project_finalization_eligibility,
)
from specify_cli.status.models import Lane

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_unchanged_graph_is_normalized_deterministically() -> None:
    result = project_finalization_eligibility(
        ["WP02", "WP01"],
        {"WP02": ["WP01", "WP01"], "WP01": []},
        {"WP01": Lane.PLANNED, "WP02": Lane.DONE},
    )

    assert result.known_wp_ids == ("WP01", "WP02")
    assert result.eligible_wp_ids == ("WP01", "WP02")
    assert result.canceled_wp_ids == ()
    assert dict(result.eligible_dependencies) == {"WP01": (), "WP02": ("WP01",)}
    assert result.stale_dependencies == ()


@pytest.mark.windows_ci
def test_canceled_node_is_excluded_and_all_cut_edges_are_sorted() -> None:
    result = project_finalization_eligibility(
        ["WP04", "WP03", "WP02", "WP01"],
        {
            "WP04": ["WP03", "WP01"],
            "WP03": ["WP02"],
            "WP02": ["WP01"],
            "WP01": [],
        },
        {"WP01": Lane.CANCELED, "WP03": Lane.CANCELED},
    )

    assert result.eligible_wp_ids == ("WP02", "WP04")
    assert result.canceled_wp_ids == ("WP01", "WP03")
    assert [item.to_dict() for item in result.stale_dependencies] == [
        {
            "dependent_wp_id": "WP02",
            "canceled_dependency_wp_id": "WP01",
            "recovery": "Remove the dependency or repoint WP02 to a non-canceled prerequisite.",
        },
        {
            "dependent_wp_id": "WP04",
            "canceled_dependency_wp_id": "WP01",
            "recovery": "Remove the dependency or repoint WP04 to a non-canceled prerequisite.",
        },
        {
            "dependent_wp_id": "WP04",
            "canceled_dependency_wp_id": "WP03",
            "recovery": "Remove the dependency or repoint WP04 to a non-canceled prerequisite.",
        },
    ]
    assert dict(result.eligible_dependencies) == {"WP02": (), "WP04": ()}


@pytest.mark.parametrize(
    "lane",
    [Lane.DONE, Lane.BLOCKED, Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS],
)
def test_only_exact_canceled_state_is_excluded(lane: Lane) -> None:
    result = project_finalization_eligibility(["WP01"], {"WP01": []}, {"WP01": lane})

    assert result.eligible_wp_ids == ("WP01",)


def test_missing_or_reopened_current_state_is_eligible() -> None:
    missing = project_finalization_eligibility(["WP01"], {"WP01": []}, {})
    reopened = project_finalization_eligibility(["WP01"], {"WP01": []}, {"WP01": Lane.PLANNED})

    assert missing.eligible_wp_ids == reopened.eligible_wp_ids == ("WP01",)


def test_canceled_source_edges_do_not_block_and_all_canceled_is_explicit() -> None:
    result = project_finalization_eligibility(
        ["WP01", "WP02"],
        {"WP01": ["WP02"], "WP02": ["WP01"]},
        {"WP01": Lane.CANCELED, "WP02": Lane.CANCELED},
    )

    assert result.all_canceled
    assert result.eligible_wp_ids == ()
    assert dict(result.eligible_dependencies) == {}
    assert result.stale_dependencies == ()


def test_projection_and_keyed_filter_are_repeatable() -> None:
    inputs = (["WP02", "WP01"], {"WP02": ["WP01"], "WP01": []}, {"WP01": Lane.CANCELED})

    first = project_finalization_eligibility(*inputs)
    second = project_finalization_eligibility(*inputs)

    assert first == second
    assert filter_by_wp_ids({"WP01": 1, "WP02": 2, "WP99": 99}, first.eligible_wp_ids) == {"WP02": 2}
