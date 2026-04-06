"""Shape conformance tests for body sync payload against 3.0.0 contract.

Tests that _build_request_body() produces payloads with mission-era naming
(mission_slug, mission_type) and excludes forbidden legacy fields.

Run: python -m pytest tests/contract/test_body_sync.py -v
"""

from __future__ import annotations

import pytest

from specify_cli.sync.body_queue import BodyUploadTask
from specify_cli.sync.body_transport import _build_request_body


def _make_body_upload_task() -> BodyUploadTask:
    """Construct a BodyUploadTask with canonical test data."""
    return BodyUploadTask(
        row_id=1,
        project_uuid="00000000-0000-0000-0000-000000000001",
        mission_slug="064-test-mission",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
        artifact_path="spec.md",
        content_hash="abc123def456",
        hash_algorithm="sha256",
        content_body="# Test Spec\n\nTest content.",
        size_bytes=28,
        retry_count=0,
        next_attempt_at=0.0,
        created_at=1000000000.0,
        last_error=None,
    )


class TestBodySyncRequiredFields:
    """Validate that all required body sync fields are present."""

    def test_contains_mission_slug(self, canonical_body_sync_fields):
        task = _make_body_upload_task()
        body = _build_request_body(task)
        assert "mission_slug" in body
        assert body["mission_slug"] == "064-test-mission"

    def test_contains_mission_type(self, canonical_body_sync_fields):
        task = _make_body_upload_task()
        body = _build_request_body(task)
        assert "mission_type" in body
        assert body["mission_type"] == "software-dev"

    def test_contains_project_uuid(self):
        task = _make_body_upload_task()
        body = _build_request_body(task)
        assert "project_uuid" in body
        assert body["project_uuid"] == "00000000-0000-0000-0000-000000000001"

    def test_contains_target_branch(self):
        task = _make_body_upload_task()
        body = _build_request_body(task)
        assert "target_branch" in body

    def test_contains_manifest_version(self):
        task = _make_body_upload_task()
        body = _build_request_body(task)
        assert "manifest_version" in body

    def test_all_required_fields_present(self, canonical_body_sync_fields):
        """Every field in the contract's required_fields must be present."""
        task = _make_body_upload_task()
        body = _build_request_body(task)

        for field in canonical_body_sync_fields:
            assert field in body, f"Required body sync field '{field}' missing from payload"

    def test_payload_has_exactly_9_fields(self):
        """The body sync payload should have exactly 9 fields (5 namespace + 4 artifact)."""
        task = _make_body_upload_task()
        body = _build_request_body(task)
        assert len(body) == 9, f"Expected 9 fields, got {len(body)}: {sorted(body.keys())}"


class TestBodySyncForbiddenFields:
    """Validate that forbidden legacy fields are absent."""

    def test_does_not_contain_feature_slug(self, forbidden_body_sync_fields):
        task = _make_body_upload_task()
        body = _build_request_body(task)
        assert "feature_slug" not in body, "feature_slug is forbidden in body sync payload"

    def test_does_not_contain_mission_key(self, forbidden_body_sync_fields):
        task = _make_body_upload_task()
        body = _build_request_body(task)
        assert "mission_key" not in body, "mission_key is forbidden in body sync payload"

    def test_no_forbidden_fields_present(self, forbidden_body_sync_fields):
        """No field from the contract's forbidden_fields may appear."""
        task = _make_body_upload_task()
        body = _build_request_body(task)

        for field in forbidden_body_sync_fields:
            assert field not in body, f"Forbidden body sync field '{field}' present in payload"


class TestBodySyncFieldNames:
    """Validate the exact set of field names in the payload."""

    def test_expected_field_set(self):
        """Payload must contain exactly the 5 namespace + 4 artifact fields."""
        task = _make_body_upload_task()
        body = _build_request_body(task)

        expected_fields = {
            # 5 namespace fields (FR-002)
            "project_uuid",
            "mission_slug",
            "target_branch",
            "mission_type",
            "manifest_version",
            # 4 artifact fields (FR-003)
            "artifact_path",
            "content_hash",
            "hash_algorithm",
            "content_body",
        }
        actual_fields = set(body.keys())
        assert actual_fields == expected_fields, (
            f"Field mismatch.\n"
            f"  Missing: {expected_fields - actual_fields}\n"
            f"  Extra: {actual_fields - expected_fields}"
        )
