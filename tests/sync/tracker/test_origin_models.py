"""Tests for specify_cli.tracker.origin_models dataclasses."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from specify_cli.tracker.origin_models import (
    MissionFromTicketResult,
    OriginCandidate,
    SearchOriginResult,
)


# ---------------------------------------------------------------------------
# OriginCandidate
# ---------------------------------------------------------------------------


class TestOriginCandidate:
    """Tests for the OriginCandidate frozen dataclass."""

    def test_construct_with_valid_fields(self) -> None:
        candidate = OriginCandidate(
            external_issue_id="issue-123",
            external_issue_key="PROJ-42",
            title="Fix login page",
            status="In Progress",
            url="https://tracker.example.com/PROJ-42",
            match_type="exact",
        )
        assert candidate.external_issue_id == "issue-123"
        assert candidate.external_issue_key == "PROJ-42"
        assert candidate.title == "Fix login page"
        assert candidate.status == "In Progress"
        assert candidate.url == "https://tracker.example.com/PROJ-42"
        assert candidate.match_type == "exact"

    def test_frozen_raises_on_attribute_assignment(self) -> None:
        candidate = OriginCandidate(
            external_issue_id="id-1",
            external_issue_key="KEY-1",
            title="Title",
            status="Open",
            url="https://example.com",
            match_type="text",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            candidate.title = "Changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        kwargs = {
            "external_issue_id": "id-1",
            "external_issue_key": "KEY-1",
            "title": "Title",
            "status": "Open",
            "url": "https://example.com",
            "match_type": "exact",
        }
        assert OriginCandidate(**kwargs) == OriginCandidate(**kwargs)

    def test_text_match_type(self) -> None:
        candidate = OriginCandidate(
            external_issue_id="id-2",
            external_issue_key="KEY-2",
            title="Fuzzy match",
            status="Done",
            url="https://example.com/2",
            match_type="text",
        )
        assert candidate.match_type == "text"


# ---------------------------------------------------------------------------
# SearchOriginResult
# ---------------------------------------------------------------------------


class TestSearchOriginResult:
    """Tests for the SearchOriginResult frozen dataclass."""

    def test_empty_candidates(self) -> None:
        result = SearchOriginResult(
            candidates=[],
            provider="jira",
            resource_type="jira_project",
            resource_id="PROJ",
            query_used="login bug",
        )
        assert result.candidates == []
        assert result.provider == "jira"
        assert result.resource_type == "jira_project"
        assert result.resource_id == "PROJ"
        assert result.query_used == "login bug"

    def test_populated_candidates_preserve_order(self) -> None:
        c1 = OriginCandidate(
            external_issue_id="id-1",
            external_issue_key="KEY-1",
            title="First",
            status="Open",
            url="https://example.com/1",
            match_type="exact",
        )
        c2 = OriginCandidate(
            external_issue_id="id-2",
            external_issue_key="KEY-2",
            title="Second",
            status="Done",
            url="https://example.com/2",
            match_type="text",
        )
        result = SearchOriginResult(
            candidates=[c1, c2],
            provider="linear",
            resource_type="linear_team",
            resource_id="TEAM-A",
            query_used="feature request",
        )
        assert len(result.candidates) == 2
        assert result.candidates[0] is c1
        assert result.candidates[1] is c2

    def test_frozen_raises_on_attribute_assignment(self) -> None:
        result = SearchOriginResult(
            candidates=[],
            provider="jira",
            resource_type="jira_project",
            resource_id="PROJ",
            query_used="query",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.provider = "linear"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MissionFromTicketResult
# ---------------------------------------------------------------------------


class TestMissionFromTicketResult:
    """Tests for the MissionFromTicketResult mutable dataclass."""

    def test_construct_with_path_and_dict(self) -> None:
        result = MissionFromTicketResult(
            feature_dir=Path("/tmp/kitty-specs/061-feature"),
            feature_slug="061-feature",
            origin_ticket={
                "provider": "linear",
                "resource_type": "linear_team",
                "resource_id": "TEAM-A",
                "external_issue_id": "id-1",
                "external_issue_key": "KEY-1",
                "external_issue_url": "https://example.com/1",
                "title": "Fix login",
            },
            event_emitted=False,
        )
        assert result.feature_dir == Path("/tmp/kitty-specs/061-feature")
        assert result.feature_slug == "061-feature"
        assert result.origin_ticket["provider"] == "linear"
        assert result.event_emitted is False

    def test_mutable_attribute_assignment(self) -> None:
        result = MissionFromTicketResult(
            feature_dir=Path("/tmp/a"),
            feature_slug="a",
            origin_ticket={"provider": "jira"},
            event_emitted=False,
        )
        # Should NOT raise -- MissionFromTicketResult is mutable
        result.event_emitted = True
        assert result.event_emitted is True

        result.feature_slug = "updated-slug"
        assert result.feature_slug == "updated-slug"
