"""Tests for ProfileInvocationExecutor."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.errors import InvocationWriteError, ProfileNotFoundError
from specify_cli.invocation.executor import InvocationPayload, ProfileInvocationExecutor
from specify_cli.invocation.writer import EVENTS_DIR


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "profiles"

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "compact governance context"

_MISSING_CTX = MagicMock()
_MISSING_CTX.mode = "missing"
_MISSING_CTX.text = ""


def _setup_fixture_profiles(tmp_path: Path) -> None:
    """Copy fixture profiles into simulated project structure."""
    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInvokeWithProfileHint:
    def test_invoke_with_profile_hint_returns_payload(self, tmp_path: Path) -> None:
        _setup_fixture_profiles(tmp_path)
        with patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_COMPACT_CTX,
        ) as mock_ctx:
            executor = ProfileInvocationExecutor(tmp_path)
            payload = executor.invoke("implement the feature", profile_hint="implementer-fixture")

        assert isinstance(payload, InvocationPayload)
        assert payload.profile_id == "implementer-fixture"
        assert payload.profile_friendly_name == "Implementer (fixture)"
        assert payload.action is not None
        # mark_loaded=False is critical — verify it was passed
        mock_ctx.assert_called_once()
        _, kwargs = mock_ctx.call_args
        assert kwargs.get("mark_loaded") is False

    def test_invoke_creates_jsonl_file(self, tmp_path: Path) -> None:
        _setup_fixture_profiles(tmp_path)
        with patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_COMPACT_CTX,
        ):
            executor = ProfileInvocationExecutor(tmp_path)
            payload = executor.invoke("implement feature", profile_hint="implementer-fixture")

        events_dir = tmp_path / EVENTS_DIR
        jsonl_files = list(events_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1
        assert jsonl_files[0].name == f"{payload.invocation_id}.jsonl"

    def test_invoke_writes_started_event_to_jsonl(self, tmp_path: Path) -> None:
        _setup_fixture_profiles(tmp_path)
        with patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_COMPACT_CTX,
        ):
            executor = ProfileInvocationExecutor(tmp_path)
            payload = executor.invoke("test", profile_hint="implementer-fixture")

        events_dir = tmp_path / EVENTS_DIR
        jsonl_file = events_dir / f"{payload.invocation_id}.jsonl"
        lines = [line for line in jsonl_file.read_text().splitlines() if line.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["event"] == "started"
        assert data["profile_id"] == "implementer-fixture"


class TestInvokeNoRouterNoHintRaises:
    def test_invoke_without_router_or_hint_raises_runtime_error(self, tmp_path: Path) -> None:
        _setup_fixture_profiles(tmp_path)
        executor = ProfileInvocationExecutor(tmp_path, router=None)
        with pytest.raises(RuntimeError, match="No profile_hint and no router"):
            executor.invoke("some request")


class TestInvokeMissingProfileHintRaises:
    def test_invoke_with_unknown_profile_hint_raises_profile_not_found_error(self, tmp_path: Path) -> None:
        executor = ProfileInvocationExecutor(tmp_path)
        with (
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
            pytest.raises(ProfileNotFoundError),
        ):
            executor.invoke("test", profile_hint="no-such-profile")


class TestInvokeDegradedCharter:
    def test_invoke_missing_charter_sets_context_unavailable(self, tmp_path: Path) -> None:
        """When charter is missing, governance_context_available=False, JSONL still written."""
        _setup_fixture_profiles(tmp_path)
        with patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_MISSING_CTX,
        ):
            executor = ProfileInvocationExecutor(tmp_path)
            payload = executor.invoke("test", profile_hint="implementer-fixture")

        assert payload.governance_context_available is False
        # JSONL must still be written even when charter is missing
        events_dir = tmp_path / EVENTS_DIR
        jsonl_files = list(events_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1


class TestInvokeMarkLoadedFalse:
    def test_context_state_json_not_modified_after_invoke(self, tmp_path: Path) -> None:
        """context-state.json must NOT be modified after invoke — mark_loaded=False is critical."""
        _setup_fixture_profiles(tmp_path)
        # Ensure context-state.json directory exists
        state_dir = tmp_path / ".kittify" / "charter"
        state_dir.mkdir(parents=True)
        state_file = state_dir / "context-state.json"
        state_file.write_text('{"specify": {"first_load": true}}', encoding="utf-8")

        initial_content = state_file.read_text(encoding="utf-8")

        with patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_COMPACT_CTX,
        ) as mock_ctx:
            executor = ProfileInvocationExecutor(tmp_path)
            executor.invoke("test", profile_hint="implementer-fixture")

        # mark_loaded=False must have been passed to prevent state mutation
        _, kwargs = mock_ctx.call_args
        assert kwargs.get("mark_loaded") is False

        # State file must remain unmodified
        assert state_file.read_text(encoding="utf-8") == initial_content


class TestInvokeWriteFailureRaises:
    def test_invoke_propagates_invocation_write_error(self, tmp_path: Path) -> None:
        _setup_fixture_profiles(tmp_path)
        with (
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
            patch(
                "specify_cli.invocation.executor.InvocationWriter.write_started",
                side_effect=InvocationWriteError("disk full"),
            ),
        ):
            executor = ProfileInvocationExecutor(tmp_path)
            with pytest.raises(InvocationWriteError):
                executor.invoke("test", profile_hint="implementer-fixture")
