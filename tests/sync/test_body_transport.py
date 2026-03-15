"""Tests for specify_cli.sync.body_transport module."""

from __future__ import annotations

import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import requests

from specify_cli.sync.body_transport import (
    DEFAULT_TIMEOUT_SECONDS,
    _build_request_body,
    _classify_response,
    _dispatch_404,
    _safe_json,
    push_content,
)
from specify_cli.sync.namespace import UploadStatus

pytestmark = pytest.mark.fast

@dataclass
class FakeTask:
    """Mimics BodyUploadTask fields needed by body_transport."""

    project_uuid: str = "550e8400-e29b-41d4-a716-446655440000"
    feature_slug: str = "047-feat"
    target_branch: str = "main"
    mission_key: str = "software-dev"
    manifest_version: str = "1"
    artifact_path: str = "spec.md"
    content_hash: str = "abcd1234" * 8
    hash_algorithm: str = "sha256"
    content_body: str = "# Spec\n"
    size_bytes: int = 8
    row_id: int = 1
    retry_count: int = 0
    next_attempt_at: float = 0.0
    created_at: float = 1000.0
    last_error: str | None = None


def _mock_response(status_code: int, json_body: dict | None = None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


# --- _build_request_body (T022) ---


class TestBuildRequestBody:
    def test_includes_all_10_fields(self) -> None:
        task = FakeTask()
        body = _build_request_body(task)
        assert body["project_uuid"] == task.project_uuid
        assert body["feature_slug"] == task.feature_slug
        assert body["target_branch"] == task.target_branch
        assert body["mission_key"] == task.mission_key
        assert body["manifest_version"] == task.manifest_version
        assert body["artifact_path"] == task.artifact_path
        assert body["content_hash"] == task.content_hash
        assert body["hash_algorithm"] == task.hash_algorithm
        assert body["content_body"] == task.content_body
        assert len(body) == 10

    def test_mission_slug_alias_equals_mission_key(self) -> None:
        task = FakeTask()
        body = _build_request_body(task)
        assert "mission_slug" in body
        assert body["mission_slug"] == body["mission_key"]


# --- _safe_json ---


class TestSafeJson:
    def test_returns_parsed_json(self) -> None:
        resp = _mock_response(200, {"key": "value"})
        assert _safe_json(resp) == {"key": "value"}

    def test_returns_empty_dict_on_invalid_json(self) -> None:
        resp = _mock_response(200)  # json() raises ValueError
        assert _safe_json(resp) == {}


# --- _classify_response (T020) ---


class TestClassifyResponse:
    def test_201_stored(self) -> None:
        task = FakeTask()
        resp = _mock_response(201, {"status": "stored"})
        outcome = _classify_response(task, resp)
        assert outcome.status == UploadStatus.UPLOADED
        assert outcome.reason == "stored"
        assert outcome.content_hash == task.content_hash

    def test_200_already_exists(self) -> None:
        task = FakeTask()
        resp = _mock_response(200, {"status": "already_exists"})
        outcome = _classify_response(task, resp)
        assert outcome.status == UploadStatus.ALREADY_EXISTS
        assert outcome.reason == "already_exists"

    def test_400_bad_request(self) -> None:
        task = FakeTask()
        resp = _mock_response(400, {"detail": "content_hash mismatch"})
        outcome = _classify_response(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert "bad_request" in outcome.reason
        assert "content_hash mismatch" in outcome.reason
        assert outcome.retryable is False

    def test_400_no_json(self) -> None:
        task = FakeTask()
        resp = _mock_response(400)
        outcome = _classify_response(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert outcome.retryable is False

    def test_401_unauthorized(self) -> None:
        task = FakeTask()
        resp = _mock_response(401, {"error": "authentication_required"})
        outcome = _classify_response(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert outcome.reason == "unauthorized"
        assert outcome.retryable is True

    def test_429_rate_limited(self) -> None:
        task = FakeTask()
        resp = _mock_response(429, {"error": "rate_limited"})
        outcome = _classify_response(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert outcome.reason == "rate_limited"
        assert outcome.retryable is True

    def test_500_server_error(self) -> None:
        task = FakeTask()
        resp = _mock_response(500)
        outcome = _classify_response(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert "server_error" in outcome.reason
        assert outcome.retryable is True

    def test_502_bad_gateway(self) -> None:
        task = FakeTask()
        resp = _mock_response(502)
        outcome = _classify_response(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert "server_error" in outcome.reason
        assert "502" in outcome.reason
        assert outcome.retryable is True

    def test_unexpected_status(self) -> None:
        task = FakeTask()
        resp = _mock_response(418)
        outcome = _classify_response(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert "unexpected_status" in outcome.reason
        assert outcome.retryable is False


# --- _dispatch_404 (T021) ---


class TestDispatch404:
    def test_index_entry_not_found_retryable(self) -> None:
        task = FakeTask()
        resp = _mock_response(404, {"error": "index_entry_not_found"})
        outcome = _dispatch_404(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert "index_entry_not_found" in outcome.reason
        assert outcome.retryable is True

    def test_namespace_not_found_not_retryable(self) -> None:
        task = FakeTask()
        resp = _mock_response(404, {"error": "namespace_not_found"})
        outcome = _dispatch_404(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert "namespace_not_found" in outcome.reason
        assert outcome.retryable is False

    def test_unknown_error_code_retryable(self) -> None:
        task = FakeTask()
        resp = _mock_response(404, {"error": "something_else"})
        outcome = _dispatch_404(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert outcome.retryable is True

    def test_no_json_body_retryable(self) -> None:
        task = FakeTask()
        resp = _mock_response(404)  # json() raises ValueError
        outcome = _dispatch_404(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert outcome.retryable is True

    def test_missing_error_field_retryable(self) -> None:
        task = FakeTask()
        resp = _mock_response(404, {"detail": "not found"})
        outcome = _dispatch_404(task, resp)
        assert outcome.status == UploadStatus.FAILED
        assert outcome.retryable is True


# --- push_content() (T019) ---


class TestPushContent:
    @patch("specify_cli.sync.body_transport.requests.post")
    def test_successful_upload(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(
            201, {"status": "stored"}
        )
        task = FakeTask()
        outcome = push_content(task, "token123", "https://api.example.com")
        assert outcome.status == UploadStatus.UPLOADED
        mock_post.assert_called_once()

    @patch("specify_cli.sync.body_transport.requests.post")
    def test_sends_auth_header(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(201, {"status": "stored"})
        push_content(FakeTask(), "my-secret-token", "https://api.example.com")
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["Authorization"] == "Bearer my-secret-token"

    @patch("specify_cli.sync.body_transport.requests.post")
    def test_sends_correct_url(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(201, {"status": "stored"})
        push_content(FakeTask(), "token", "https://api.example.com/")
        call_args = mock_post.call_args
        url = call_args.args[0] if call_args.args else call_args[0][0]
        assert url == "https://api.example.com/api/dossier/push-content/"

    @patch("specify_cli.sync.body_transport.requests.post")
    def test_sends_correct_payload(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(201, {"status": "stored"})
        task = FakeTask()
        push_content(task, "token", "https://api.example.com")
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["project_uuid"] == task.project_uuid
        assert payload["content_body"] == task.content_body
        assert len(payload) == 10

    @patch("specify_cli.sync.body_transport.requests.post")
    def test_uses_default_timeout(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(201, {"status": "stored"})
        push_content(FakeTask(), "token", "https://api.example.com")
        call_kwargs = mock_post.call_args
        timeout = call_kwargs.kwargs.get("timeout") or call_kwargs[1].get("timeout")
        assert timeout == DEFAULT_TIMEOUT_SECONDS

    @patch("specify_cli.sync.body_transport.requests.post")
    def test_connection_error_retryable(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.ConnectionError("Connection refused")
        task = FakeTask()
        outcome = push_content(task, "token", "https://api.example.com")
        assert outcome.status == UploadStatus.FAILED
        assert "connection_error" in outcome.reason
        assert outcome.retryable is True

    @patch("specify_cli.sync.body_transport.requests.post")
    def test_timeout_retryable(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.Timeout("Request timed out")
        task = FakeTask()
        outcome = push_content(task, "token", "https://api.example.com")
        assert outcome.status == UploadStatus.FAILED
        assert "timeout" in outcome.reason
        assert outcome.retryable is True

    @patch("specify_cli.sync.body_transport.requests.post")
    def test_custom_timeout(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(201, {"status": "stored"})
        push_content(FakeTask(), "token", "https://api.example.com", timeout=60.0)
        call_kwargs = mock_post.call_args
        timeout = call_kwargs.kwargs.get("timeout") or call_kwargs[1].get("timeout")
        assert timeout == 60.0

    @patch("specify_cli.sync.body_transport.requests.post")
    def test_server_url_trailing_slash_stripped(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(201, {"status": "stored"})
        push_content(FakeTask(), "token", "https://api.example.com///")
        call_args = mock_post.call_args
        url = call_args.args[0] if call_args.args else call_args[0][0]
        assert url == "https://api.example.com/api/dossier/push-content/"
