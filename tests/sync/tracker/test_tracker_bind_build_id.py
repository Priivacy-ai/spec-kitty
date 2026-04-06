"""Tests for build_id in tracker bind payloads (T039, WP06).

Verifies that:
- project_identity dict includes build_id
- build_id is a non-empty string
- Contract gate validates tracker_bind payloads
- SaaS client passes build_id through bind endpoints
"""

from __future__ import annotations

import json as _json
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from specify_cli.core.contract_gate import ContractViolationError, validate_outbound_payload
from specify_cli.sync.project_identity import ProjectIdentity, ensure_identity
from specify_cli.tracker.saas_client import SaaSTrackerClient

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: int = 200,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    resp = httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", "https://example.com"),
    )
    if json_body is not None:
        resp._content = _json.dumps(json_body).encode()
        resp.headers["content-type"] = "application/json"
    else:
        resp._content = b""
    return resp


@pytest.fixture()
def mock_credential_store() -> MagicMock:
    store = MagicMock()
    store.get_access_token.return_value = "test-access-token"
    store.get_team_slug.return_value = "team-acme"
    return store


@pytest.fixture()
def mock_sync_config() -> MagicMock:
    config = MagicMock()
    config.get_server_url.return_value = "https://saas.example.com"
    return config


@pytest.fixture()
def client(mock_credential_store: MagicMock, mock_sync_config: MagicMock) -> SaaSTrackerClient:
    return SaaSTrackerClient(
        credential_store=mock_credential_store,
        sync_config=mock_sync_config,
        timeout=5.0,
    )


def _valid_project_identity() -> dict[str, Any]:
    return {
        "uuid": str(uuid4()),
        "slug": "my-project",
        "node_id": "a1b2c3d4e5f6",
        "repo_slug": "org/my-project",
        "build_id": str(uuid4()),
    }


# ---------------------------------------------------------------------------
# T039: build_id in bind payloads
# ---------------------------------------------------------------------------


class TestProjectIdentityBuildId:
    """Verify ProjectIdentity generates and persists build_id."""

    def test_build_id_generated_by_with_defaults(self, tmp_path):
        """with_defaults generates build_id when missing."""
        identity = ProjectIdentity()
        filled = identity.with_defaults(tmp_path)
        assert filled.build_id is not None
        assert isinstance(filled.build_id, str)
        assert len(filled.build_id) > 0

    def test_build_id_in_to_dict(self):
        """to_dict includes build_id."""
        identity = ProjectIdentity(
            project_uuid=uuid4(),
            project_slug="test",
            node_id="abc123",
            build_id="build-id-001",
        )
        d = identity.to_dict()
        assert "build_id" in d
        assert d["build_id"] == "build-id-001"

    def test_build_id_from_dict(self):
        """from_dict restores build_id."""
        d = {"uuid": str(uuid4()), "slug": "test", "node_id": "abc", "build_id": "bid-1"}
        identity = ProjectIdentity.from_dict(d)
        assert identity.build_id == "bid-1"

    def test_is_complete_requires_build_id(self):
        """is_complete returns False without build_id."""
        identity = ProjectIdentity(
            project_uuid=uuid4(),
            project_slug="test",
            node_id="abc123",
            build_id=None,
        )
        assert not identity.is_complete

    def test_is_complete_with_build_id(self):
        """is_complete returns True with all fields including build_id."""
        identity = ProjectIdentity(
            project_uuid=uuid4(),
            project_slug="test",
            node_id="abc123",
            build_id="build-001",
        )
        assert identity.is_complete

    def test_ensure_identity_generates_build_id(self, tmp_path):
        """ensure_identity populates build_id for new projects."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        identity = ensure_identity(tmp_path)
        assert identity.build_id is not None
        assert len(identity.build_id) > 0


class TestContractGateTrackerBind:
    """Contract gate validates tracker_bind payloads."""

    def test_valid_payload_passes(self):
        """Valid tracker_bind payload with build_id passes gate."""
        payload = _valid_project_identity()
        validate_outbound_payload(payload, "tracker_bind")  # Should not raise

    def test_missing_build_id_fails(self):
        """Payload without build_id fails contract gate."""
        payload = _valid_project_identity()
        del payload["build_id"]
        with pytest.raises(ContractViolationError, match="build_id"):
            validate_outbound_payload(payload, "tracker_bind")


class TestSaaSClientBindBuildId:
    """SaaS client passes build_id in bind endpoint payloads."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_bind_resolve_includes_build_id(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """bind_resolve sends project_identity with build_id."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"candidates": []})

        identity = _valid_project_identity()
        client.bind_resolve("linear", identity)

        _, kwargs = mock_http.request.call_args
        sent_payload = kwargs["json"]
        assert "build_id" in sent_payload["project_identity"]
        assert sent_payload["project_identity"]["build_id"] == identity["build_id"]

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_bind_confirm_includes_build_id(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """bind_confirm sends project_identity with build_id."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"binding_ref": "br-1", "display_label": "Test"}
        )

        identity = _valid_project_identity()
        client.bind_confirm("linear", "candidate-token-1", identity)

        _, kwargs = mock_http.request.call_args
        sent_payload = kwargs["json"]
        assert sent_payload["project_identity"]["build_id"] == identity["build_id"]

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_bind_validate_includes_build_id(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """bind_validate sends project_identity with build_id."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"valid": True})

        identity = _valid_project_identity()
        client.bind_validate("linear", "br-1", identity)

        _, kwargs = mock_http.request.call_args
        sent_payload = kwargs["json"]
        assert sent_payload["project_identity"]["build_id"] == identity["build_id"]

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_bind_resolve_rejects_missing_build_id(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """bind_resolve raises ContractViolationError without build_id."""
        identity = _valid_project_identity()
        del identity["build_id"]
        with pytest.raises(ContractViolationError, match="build_id"):
            client.bind_resolve("linear", identity)
