"""Unit tests for Gemini adapter."""

import pytest
from specify_cli.adapters.gemini import GeminiObserveDecideAdapter
from specify_cli.adapters.observe_decide import ObservationSignal


def test_gemini_adapter_normalize_identity():
    """Test ActorIdentity extraction."""
    adapter = GeminiObserveDecideAdapter()

    identity = adapter.normalize_actor_identity({"user_email": "alice@example.com"})

    assert identity.agent_type == "gemini"
    assert identity.auth_principal == "alice@example.com"
    assert len(identity.session_id) == 26  # ULID format


def test_gemini_adapter_normalize_identity_missing_email():
    """Test ActorIdentity extraction with missing user_email."""
    adapter = GeminiObserveDecideAdapter()

    identity = adapter.normalize_actor_identity({})

    assert identity.agent_type == "gemini"
    assert identity.auth_principal == "unknown"


def test_gemini_adapter_parse_observation_step_started():
    """Test observation parsing for step_started signal."""
    adapter = GeminiObserveDecideAdapter()

    signals = adapter.parse_observation("Starting step:42 execution")

    assert len(signals) == 1
    assert signals[0].signal_type == "step_started"
    assert signals[0].entity_id == "step:42"
    assert signals[0].metadata["source"] == "gemini_text_output"


def test_gemini_adapter_parse_observation_step_completed():
    """Test observation parsing for step_completed signal."""
    adapter = GeminiObserveDecideAdapter()

    signals = adapter.parse_observation("Completed step:99 successfully")

    assert len(signals) == 1
    assert signals[0].signal_type == "step_completed"
    assert signals[0].entity_id == "step:99"


def test_gemini_adapter_parse_observation_no_signals():
    """Test observation parsing with no matching patterns."""
    adapter = GeminiObserveDecideAdapter()

    signals = adapter.parse_observation("Some random output text")

    assert len(signals) == 0


def test_gemini_adapter_parse_observation_dict_input():
    """Test observation parsing with dict input (no signals expected)."""
    adapter = GeminiObserveDecideAdapter()

    signals = adapter.parse_observation({"output": "Starting step:1"})

    # Dict input is not parsed in S1/M1 baseline
    assert len(signals) == 0


def test_gemini_adapter_detect_decision_request_stub():
    """Test decision detection returns None (stub implementation)."""
    adapter = GeminiObserveDecideAdapter()

    signal = ObservationSignal(
        signal_type="decision_request",
        entity_id="decision:1",
        metadata={}
    )

    result = adapter.detect_decision_request(signal)
    assert result is None


def test_gemini_adapter_format_decision_answer():
    """Test decision answer formatting."""
    adapter = GeminiObserveDecideAdapter()

    formatted = adapter.format_decision_answer("approve")

    assert '"decision"' in formatted
    assert '"approve"' in formatted


def test_gemini_adapter_healthcheck_with_api_key(monkeypatch):
    """Test healthcheck returns ok when API key is set."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key-12345")

    adapter = GeminiObserveDecideAdapter()
    health = adapter.healthcheck()

    assert health.status == "ok"
    assert "API key found" in health.message


def test_gemini_adapter_healthcheck_without_api_key(monkeypatch):
    """Test healthcheck returns unavailable when API key is missing."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    adapter = GeminiObserveDecideAdapter()
    health = adapter.healthcheck()

    assert health.status == "unavailable"
    assert "not set" in health.message
