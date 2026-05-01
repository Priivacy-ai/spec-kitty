"""Tests for tracker binding discovery dataclasses and helpers."""

from __future__ import annotations

import pytest

from specify_cli.tracker.discovery import (
    BindableResource,
    BindCandidate,
    BindResult,
    ResolutionResult,
    ValidationResult,
    find_candidate_by_position,
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture()
def full_resource_data() -> dict:
    return {
        "candidate_token": "cand_01HXYZ",
        "display_label": "My Project (LINEAR-123)",
        "provider": "linear",
        "provider_context": {
            "team_name": "Engineering",
            "workspace_name": "Acme Corp",
        },
        "binding_ref": "srm_01HXYZ",
        "bound_project_slug": "my-project",
        "bound_at": "2026-03-01T10:00:00Z",
    }


@pytest.fixture()
def full_candidate_data() -> dict:
    return {
        "candidate_token": "cand_01HABC",
        "display_label": "My Project (LINEAR-123)",
        "confidence": "high",
        "match_reason": "project_slug matches existing mapping",
        "sort_position": 0,
    }


@pytest.fixture()
def full_bind_result_data() -> dict:
    return {
        "binding_ref": "srm_01HXYZ",
        "display_label": "My Project (LINEAR-123)",
        "provider": "linear",
        "provider_context": {
            "team_name": "Engineering",
            "workspace_name": "Acme Corp",
        },
        "bound_at": "2026-04-04T08:32:00Z",
    }


# ── BindableResource ────────────────────────────────────────────────────


class TestBindableResourceFromApi:
    """T009: BindableResource.from_api tests."""

    def test_full_response(self, full_resource_data: dict) -> None:
        resource = BindableResource.from_api(full_resource_data)

        assert resource.candidate_token == "cand_01HXYZ"
        assert resource.display_label == "My Project (LINEAR-123)"
        assert resource.provider == "linear"
        assert resource.provider_context == {
            "team_name": "Engineering",
            "workspace_name": "Acme Corp",
        }
        assert resource.binding_ref == "srm_01HXYZ"
        assert resource.bound_project_slug == "my-project"
        assert resource.bound_at == "2026-03-01T10:00:00Z"
        assert resource.is_bound is True

    def test_minimal_response(self) -> None:
        data = {
            "candidate_token": "cand_min",
            "display_label": "Unbound Resource",
            "provider": "jira",
        }
        resource = BindableResource.from_api(data)

        assert resource.candidate_token == "cand_min"
        assert resource.display_label == "Unbound Resource"
        assert resource.provider == "jira"
        assert resource.provider_context == {}
        assert resource.binding_ref is None
        assert resource.bound_project_slug is None
        assert resource.bound_at is None
        assert resource.is_bound is False

    def test_missing_required_field(self) -> None:
        data = {
            "display_label": "Missing token",
            "provider": "linear",
        }
        with pytest.raises(KeyError, match="candidate_token"):
            BindableResource.from_api(data)


# ── BindCandidate ───────────────────────────────────────────────────────


class TestBindCandidateFromApi:
    """T009: BindCandidate.from_api tests."""

    def test_full_response(self, full_candidate_data: dict) -> None:
        candidate = BindCandidate.from_api(full_candidate_data)

        assert candidate.candidate_token == "cand_01HABC"
        assert candidate.display_label == "My Project (LINEAR-123)"
        assert candidate.confidence == "high"
        assert candidate.match_reason == "project_slug matches existing mapping"
        assert candidate.sort_position == 0

    def test_missing_required_field(self) -> None:
        data = {
            "candidate_token": "cand_x",
            "display_label": "X",
            "confidence": "low",
            # missing match_reason and sort_position
        }
        with pytest.raises(KeyError, match="match_reason"):
            BindCandidate.from_api(data)


# ── BindResult ──────────────────────────────────────────────────────────


class TestBindResultFromApi:
    """T009: BindResult.from_api tests."""

    def test_full_response(self, full_bind_result_data: dict) -> None:
        result = BindResult.from_api(full_bind_result_data)

        assert result.binding_ref == "srm_01HXYZ"
        assert result.display_label == "My Project (LINEAR-123)"
        assert result.provider == "linear"
        assert result.provider_context == {
            "team_name": "Engineering",
            "workspace_name": "Acme Corp",
        }
        assert result.bound_at == "2026-04-04T08:32:00Z"

    def test_minimal_response(self) -> None:
        data = {
            "binding_ref": "srm_min",
            "display_label": "Minimal",
            "provider": "github",
            "bound_at": "2026-04-04T09:00:00Z",
        }
        result = BindResult.from_api(data)

        assert result.binding_ref == "srm_min"
        assert result.provider_context == {}

    def test_missing_required_field(self) -> None:
        data = {
            "display_label": "No ref",
            "provider": "linear",
            "bound_at": "2026-04-04T09:00:00Z",
        }
        with pytest.raises(KeyError, match="binding_ref"):
            BindResult.from_api(data)


# ── ValidationResult ────────────────────────────────────────────────────


class TestValidationResultFromApi:
    """T009: ValidationResult.from_api tests."""

    def test_valid_response(self) -> None:
        data = {
            "valid": True,
            "binding_ref": "srm_01HXYZ",
            "display_label": "My Project (LINEAR-123)",
            "provider": "linear",
            "provider_context": {
                "team_name": "Engineering",
                "workspace_name": "Acme Corp",
            },
        }
        result = ValidationResult.from_api(data)

        assert result.valid is True
        assert result.binding_ref == "srm_01HXYZ"
        assert result.display_label == "My Project (LINEAR-123)"
        assert result.provider == "linear"
        assert result.provider_context == {
            "team_name": "Engineering",
            "workspace_name": "Acme Corp",
        }
        assert result.reason is None
        assert result.guidance is None

    def test_invalid_response(self) -> None:
        data = {
            "valid": False,
            "binding_ref": "srm_01HXYZ",
            "reason": "mapping_deleted",
            "guidance": "Run `tracker bind --provider linear` to rebind.",
        }
        result = ValidationResult.from_api(data)

        assert result.valid is False
        assert result.binding_ref == "srm_01HXYZ"
        assert result.reason == "mapping_deleted"
        assert result.guidance == "Run `tracker bind --provider linear` to rebind."
        assert result.display_label is None
        assert result.provider is None
        assert result.provider_context is None

    def test_minimal_response(self) -> None:
        data = {
            "valid": True,
            "binding_ref": "srm_min",
        }
        result = ValidationResult.from_api(data)

        assert result.valid is True
        assert result.binding_ref == "srm_min"
        assert result.reason is None
        assert result.guidance is None
        assert result.display_label is None
        assert result.provider is None
        assert result.provider_context is None

    def test_missing_required_field(self) -> None:
        data = {"valid": True}  # missing binding_ref
        with pytest.raises(KeyError, match="binding_ref"):
            ValidationResult.from_api(data)


# ── ResolutionResult ────────────────────────────────────────────────────


class TestResolutionResultFromApi:
    """T009: ResolutionResult.from_api tests."""

    def test_exact_match(self) -> None:
        data = {
            "match_type": "exact",
            "candidate_token": "cand_01HXYZ",
            "binding_ref": "srm_01HXYZ",
            "display_label": "My Project (LINEAR-123)",
            "candidates": [],
        }
        result = ResolutionResult.from_api(data)

        assert result.match_type == "exact"
        assert result.candidate_token == "cand_01HXYZ"
        assert result.binding_ref == "srm_01HXYZ"
        assert result.display_label == "My Project (LINEAR-123)"
        assert result.candidates == []

    def test_candidates_match(self, full_candidate_data: dict) -> None:
        second_candidate = {
            "candidate_token": "cand_01HDEF",
            "display_label": "Backend API (LINEAR-456)",
            "confidence": "medium",
            "match_reason": "repo_slug partial match",
            "sort_position": 1,
        }
        data = {
            "match_type": "candidates",
            "candidate_token": None,
            "binding_ref": None,
            "display_label": None,
            "candidates": [full_candidate_data, second_candidate],
        }
        result = ResolutionResult.from_api(data)

        assert result.match_type == "candidates"
        assert result.candidate_token is None
        assert result.binding_ref is None
        assert result.display_label is None
        assert len(result.candidates) == 2
        assert isinstance(result.candidates[0], BindCandidate)
        assert result.candidates[0].sort_position == 0
        assert result.candidates[1].sort_position == 1
        assert result.candidates[1].confidence == "medium"

    def test_no_match(self) -> None:
        data = {
            "match_type": "none",
            "candidate_token": None,
            "binding_ref": None,
            "display_label": None,
            "candidates": [],
        }
        result = ResolutionResult.from_api(data)

        assert result.match_type == "none"
        assert result.candidate_token is None
        assert result.candidates == []

    def test_minimal_response(self) -> None:
        data = {"match_type": "none"}
        result = ResolutionResult.from_api(data)

        assert result.match_type == "none"
        assert result.candidate_token is None
        assert result.binding_ref is None
        assert result.display_label is None
        assert result.candidates == []

    def test_missing_required_field(self) -> None:
        data = {"candidates": []}  # missing match_type
        with pytest.raises(KeyError, match="match_type"):
            ResolutionResult.from_api(data)


# ── find_candidate_by_position ──────────────────────────────────────────


class TestFindCandidateByPosition:
    """T010: find_candidate_by_position tests."""

    @pytest.fixture()
    def two_candidates(self) -> list[BindCandidate]:
        return [
            BindCandidate(
                candidate_token="cand_a",
                display_label="First",
                confidence="high",
                match_reason="slug match",
                sort_position=0,
            ),
            BindCandidate(
                candidate_token="cand_b",
                display_label="Second",
                confidence="medium",
                match_reason="partial match",
                sort_position=1,
            ),
        ]

    def test_find_candidate_valid(
        self, two_candidates: list[BindCandidate]
    ) -> None:
        """select_n=1 returns sort_position=0."""
        result = find_candidate_by_position(two_candidates, select_n=1)
        assert result is not None
        assert result.candidate_token == "cand_a"
        assert result.sort_position == 0

    def test_find_candidate_second(
        self, two_candidates: list[BindCandidate]
    ) -> None:
        """select_n=2 returns sort_position=1."""
        result = find_candidate_by_position(two_candidates, select_n=2)
        assert result is not None
        assert result.candidate_token == "cand_b"
        assert result.sort_position == 1

    def test_find_candidate_out_of_range(
        self, two_candidates: list[BindCandidate]
    ) -> None:
        """select_n=99 returns None."""
        result = find_candidate_by_position(two_candidates, select_n=99)
        assert result is None

    def test_find_candidate_zero(
        self, two_candidates: list[BindCandidate]
    ) -> None:
        """select_n=0 returns None (no sort_position=-1)."""
        result = find_candidate_by_position(two_candidates, select_n=0)
        assert result is None

    def test_find_candidate_empty_list(self) -> None:
        """Empty candidates returns None."""
        result = find_candidate_by_position([], select_n=1)
        assert result is None
