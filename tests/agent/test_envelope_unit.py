"""Unit tests for orchestrator_api.envelope module."""

from __future__ import annotations

import json

import pytest

from specify_cli.orchestrator_api.envelope import (
    BANNED_FLAGS,
    CONTRACT_VERSION,
    PolicyMetadata,
    make_envelope,
    parse_and_validate_policy,
    policy_to_dict,
)


pytestmark = [pytest.mark.unit]

class TestMakeEnvelope:
    def test_make_envelope_shape(self):
        """All 7 required keys present with correct types."""
        env = make_envelope("test-cmd", True, {"foo": "bar"})
        assert set(env.keys()) == {
            "contract_version",
            "command",
            "timestamp",
            "correlation_id",
            "success",
            "error_code",
            "data",
        }
        assert env["contract_version"] == CONTRACT_VERSION
        assert env["command"] == "orchestrator-api.test-cmd"
        assert isinstance(env["timestamp"], str)
        assert env["correlation_id"].startswith("corr-")
        assert env["success"] is True
        assert env["error_code"] is None
        assert env["data"] == {"foo": "bar"}

    def test_make_envelope_failure(self):
        """Failure envelope: success=False, error_code propagated, data empty dict."""
        env = make_envelope("test-cmd", False, {}, error_code="SOME_ERROR")
        assert env["success"] is False
        assert env["error_code"] == "SOME_ERROR"
        assert env["data"] == {}

    def test_make_envelope_unique_correlation_ids(self):
        """Each envelope has a unique correlation_id."""
        env1 = make_envelope("cmd", True, {})
        env2 = make_envelope("cmd", True, {})
        assert env1["correlation_id"] != env2["correlation_id"]


class TestParsePolicyValid:
    def _valid_policy(self, **overrides) -> dict:
        base = {
            "orchestrator_id": "test-orch-v1",
            "orchestrator_version": "0.1.0",
            "agent_family": "claude",
            "approval_mode": "supervised",
            "sandbox_mode": "sandbox",
            "network_mode": "restricted",
            "dangerous_flags": [],
        }
        base.update(overrides)
        return base

    def test_parse_policy_valid(self):
        """Happy path: all fields parsed correctly."""
        policy_dict = self._valid_policy(tool_restrictions="read_only")
        raw = json.dumps(policy_dict)
        policy = parse_and_validate_policy(raw)
        assert isinstance(policy, PolicyMetadata)
        assert policy.orchestrator_id == "test-orch-v1"
        assert policy.orchestrator_version == "0.1.0"
        assert policy.agent_family == "claude"
        assert policy.approval_mode == "supervised"
        assert policy.sandbox_mode == "sandbox"
        assert policy.network_mode == "restricted"
        assert policy.dangerous_flags == []
        assert policy.tool_restrictions == "read_only"

    def test_parse_policy_missing_required_field(self):
        """Missing required field raises ValueError."""
        policy_dict = self._valid_policy()
        del policy_dict["orchestrator_id"]
        raw = json.dumps(policy_dict)
        with pytest.raises(ValueError, match="missing required field"):
            parse_and_validate_policy(raw)

    def test_parse_policy_rejects_secret_in_value(self):
        """Field value containing 'token' raises ValueError."""
        policy_dict = self._valid_policy(orchestrator_id="my_token_here_xyz")
        raw = json.dumps(policy_dict)
        with pytest.raises(ValueError, match="appears to contain a secret"):
            parse_and_validate_policy(raw)

    def test_parse_policy_required_fields_must_be_strings(self):
        """Structured required fields cannot bypass policy metadata scanning."""
        policy_dict = self._valid_policy(orchestrator_id=["API_KEY=abc123"])
        raw = json.dumps(policy_dict)
        with pytest.raises(ValueError, match="orchestrator_id must be a string"):
            parse_and_validate_policy(raw)

    def test_parse_policy_dangerous_flags_must_be_list(self):
        """dangerous_flags as string raises ValueError."""
        policy_dict = self._valid_policy(dangerous_flags="--full-auto")
        raw = json.dumps(policy_dict)
        with pytest.raises(ValueError, match="must be a JSON array"):
            parse_and_validate_policy(raw)

    def test_parse_policy_rejects_secret_in_dangerous_flags_entry(self):
        """Secret-like dangerous_flags entries are rejected before persistence."""
        policy_dict = self._valid_policy(
            dangerous_flags=["AWS_SECRET_ACCESS_KEY=abc123"]
        )
        raw = json.dumps(policy_dict)
        with pytest.raises(ValueError, match="appears to contain a secret"):
            parse_and_validate_policy(raw)

    def test_parse_policy_dangerous_flags_entries_must_be_strings(self):
        """Structured dangerous_flags entries cannot bypass string scanning."""
        policy_dict = self._valid_policy(dangerous_flags=[{"name": "--full-auto"}])
        raw = json.dumps(policy_dict)
        with pytest.raises(ValueError, match="entries must be strings"):
            parse_and_validate_policy(raw)

    def test_parse_policy_preserves_valid_dangerous_flags_entries(self):
        """Non-secret, non-banned dangerous_flags entries survive validation unchanged."""
        policy_dict = self._valid_policy(dangerous_flags=["--some-allowed-flag"])
        raw = json.dumps(policy_dict)
        policy = parse_and_validate_policy(raw)
        assert policy.dangerous_flags == ["--some-allowed-flag"]

    @pytest.mark.parametrize("banned_flag", sorted(BANNED_FLAGS))
    def test_parse_policy_rejects_banned_flag(self, banned_flag: str) -> None:
        """Every BANNED_FLAGS entry must be rejected with a clear error."""
        policy_dict = self._valid_policy(dangerous_flags=[banned_flag])
        raw = json.dumps(policy_dict)
        with pytest.raises(ValueError, match="banned flag"):
            parse_and_validate_policy(raw)

    def test_parse_policy_tool_restrictions_must_be_string_or_null(self):
        """Structured tool_restrictions cannot bypass policy metadata scanning."""
        policy_dict = self._valid_policy(tool_restrictions=["API_KEY=abc123"])
        raw = json.dumps(policy_dict)
        with pytest.raises(ValueError, match="tool_restrictions must be a string or null"):
            parse_and_validate_policy(raw)

    def test_parse_policy_invalid_json(self):
        """Invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="not valid JSON"):
            parse_and_validate_policy("not-json{{")

    def test_parse_policy_not_object(self):
        """JSON array instead of object raises ValueError."""
        with pytest.raises(ValueError, match="must be a JSON object"):
            parse_and_validate_policy("[1, 2, 3]")

    def test_policy_to_dict_roundtrip(self):
        """dict → parse → dict is stable."""
        policy_dict = self._valid_policy()
        raw = json.dumps(policy_dict)
        policy = parse_and_validate_policy(raw)
        result = policy_to_dict(policy)
        assert result["orchestrator_id"] == policy_dict["orchestrator_id"]
        assert result["orchestrator_version"] == policy_dict["orchestrator_version"]
        assert result["agent_family"] == policy_dict["agent_family"]
        assert result["dangerous_flags"] == policy_dict["dangerous_flags"]
        assert result["tool_restrictions"] is None
