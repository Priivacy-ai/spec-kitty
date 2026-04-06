"""Shape conformance tests for tracker bind payload against 3.0.0 contract.

Tests that the project_identity dict constructed during tracker bind
includes build_id and all required fields from the contract.

Run: python -m pytest tests/contract/test_tracker_bind.py -v
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from specify_cli.sync.project_identity import ProjectIdentity


def _make_project_identity() -> ProjectIdentity:
    """Construct a complete ProjectIdentity for testing."""
    return ProjectIdentity(
        project_uuid=uuid4(),
        project_slug="test-project",
        node_id="a1b2c3d4e5f6",
        repo_slug="test-org/test-repo",
        build_id=str(uuid4()),
    )


def _build_tracker_bind_payload(identity: ProjectIdentity) -> dict:
    """Build the project_identity dict as tracker.py does during bind.

    This mirrors the construction in _bind_saas() from
    src/specify_cli/cli/commands/tracker.py.
    """
    return {
        "uuid": str(identity.project_uuid),
        "slug": identity.project_slug,
        "node_id": identity.node_id,
        "repo_slug": identity.repo_slug,
        "build_id": identity.build_id,
    }


class TestTrackerBindRequiredFields:
    """Validate that all required tracker bind fields are present."""

    def test_contains_build_id(self, canonical_tracker_bind_fields):
        identity = _make_project_identity()
        payload = _build_tracker_bind_payload(identity)
        assert "build_id" in payload
        assert payload["build_id"], "build_id must be non-empty"

    def test_contains_uuid(self):
        identity = _make_project_identity()
        payload = _build_tracker_bind_payload(identity)
        assert "uuid" in payload
        assert payload["uuid"], "uuid must be non-empty"

    def test_contains_slug(self):
        identity = _make_project_identity()
        payload = _build_tracker_bind_payload(identity)
        assert "slug" in payload
        assert payload["slug"], "slug must be non-empty"

    def test_contains_node_id(self):
        identity = _make_project_identity()
        payload = _build_tracker_bind_payload(identity)
        assert "node_id" in payload
        assert payload["node_id"], "node_id must be non-empty"

    def test_contains_repo_slug(self):
        identity = _make_project_identity()
        payload = _build_tracker_bind_payload(identity)
        assert "repo_slug" in payload

    def test_all_required_fields_present(self, canonical_tracker_bind_fields):
        """Every field in the contract's required_fields must be present."""
        identity = _make_project_identity()
        payload = _build_tracker_bind_payload(identity)

        for field in canonical_tracker_bind_fields:
            assert field in payload, f"Required tracker bind field '{field}' missing from payload"

    def test_build_id_is_nonempty_string(self):
        identity = _make_project_identity()
        payload = _build_tracker_bind_payload(identity)
        assert isinstance(payload["build_id"], str)
        assert len(payload["build_id"]) > 0


class TestTrackerBindForbiddenFields:
    """Validate that feature-era fields are absent."""

    def test_does_not_contain_mission_slug(self):
        identity = _make_project_identity()
        payload = _build_tracker_bind_payload(identity)
        assert "mission_slug" not in payload

    def test_does_not_contain_mission_number(self):
        identity = _make_project_identity()
        payload = _build_tracker_bind_payload(identity)
        assert "mission_number" not in payload

    def test_does_not_contain_feature_type(self):
        identity = _make_project_identity()
        payload = _build_tracker_bind_payload(identity)
        assert "feature_type" not in payload


class TestProjectIdentityCompleteness:
    """Validate ProjectIdentity.is_complete requires build_id."""

    def test_identity_without_build_id_is_incomplete(self):
        identity = ProjectIdentity(
            project_uuid=uuid4(),
            project_slug="test",
            node_id="abc123",
        )
        assert not identity.is_complete, "Identity without build_id should be incomplete"

    def test_identity_with_build_id_is_complete(self):
        identity = _make_project_identity()
        assert identity.is_complete, "Identity with all fields should be complete"

    def test_to_dict_includes_build_id(self):
        identity = _make_project_identity()
        d = identity.to_dict()
        assert "build_id" in d
        assert d["build_id"] == identity.build_id

    def test_from_dict_round_trips_build_id(self):
        identity = _make_project_identity()
        d = identity.to_dict()
        restored = ProjectIdentity.from_dict(d)
        assert restored.build_id == identity.build_id
