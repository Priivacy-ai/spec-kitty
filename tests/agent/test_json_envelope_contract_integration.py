"""Regression tests for orchestrator-api JSON envelope contract (issue #177).

Tests cover:
  Repro 2 -- Parser-level errors (missing required args, unknown options,
             missing option values) must return a JSON envelope with
             ``success: false`` and ``error_code: "USAGE_ERROR"``.
  Repro 3 -- The dead ``--no-json`` flag has been removed; passing it must
             be rejected with a ``USAGE_ERROR`` envelope.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from specify_cli.orchestrator_api.commands import app
from specify_cli import app as root_app

import pytest

pytestmark = pytest.mark.git_repo

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_envelope(output: str) -> dict:
    """Parse the last non-empty line of output as JSON.

    The error handler may emit a single JSON line; we grab it reliably even
    if other output is mixed in (e.g. traceback noise from CliRunner).
    """
    for line in reversed(output.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise AssertionError(f"No JSON envelope found in output:\n{output}")


def _assert_usage_error(output: str, *, substring: str | None = None) -> dict:
    """Assert the output is a USAGE_ERROR JSON envelope and return it."""
    env = _parse_envelope(output)
    assert env["success"] is False, f"Expected success=false, got: {env}"
    assert env["error_code"] == "USAGE_ERROR", f"Expected USAGE_ERROR, got: {env['error_code']}"
    assert "message" in env["data"], f"Expected 'message' in data, got: {env['data']}"
    if substring is not None:
        assert substring.lower() in env["data"]["message"].lower(), f"Expected '{substring}' in message '{env['data']['message']}'"
    return env


# ---------------------------------------------------------------------------
# Repro 2: Parser-level errors must be JSON envelopes
# ---------------------------------------------------------------------------


class TestParserErrorsReturnJSON:
    """Missing required args and unknown options must return USAGE_ERROR JSON."""

    def test_feature_state_missing_required_feature(self):
        """feature-state requires --mission; omitting it should be USAGE_ERROR."""
        result = runner.invoke(app, ["feature-state"])
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--mission")

    def test_list_ready_missing_required_feature(self):
        """list-ready requires --mission; omitting it should be USAGE_ERROR."""
        result = runner.invoke(app, ["list-ready"])
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--mission")

    def test_transition_missing_required_args(self):
        """transition requires --feature, --wp, --to, --actor; omitting all should error."""
        result = runner.invoke(app, ["transition"])
        assert result.exit_code != 0
        _assert_usage_error(result.output)

    def test_start_implementation_missing_all_args(self):
        """start-implementation requires --feature, --wp, --actor."""
        result = runner.invoke(app, ["start-implementation"])
        assert result.exit_code != 0
        _assert_usage_error(result.output)

    def test_accept_feature_missing_required_args(self):
        """accept-feature requires --feature and --actor."""
        result = runner.invoke(app, ["accept-feature"])
        assert result.exit_code != 0
        _assert_usage_error(result.output)

    def test_append_history_missing_required_args(self):
        """append-history requires --feature, --wp, --actor, --note."""
        result = runner.invoke(app, ["append-history"])
        assert result.exit_code != 0
        _assert_usage_error(result.output)

    def test_unknown_option_returns_json(self):
        """An unknown option like --bogus should return USAGE_ERROR JSON."""
        result = runner.invoke(app, ["contract-version", "--bogus"])
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--bogus")

    def test_unknown_subcommand_returns_json(self):
        """An unknown subcommand should return USAGE_ERROR JSON."""
        result = runner.invoke(app, ["nonexistent-subcommand"])
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="nonexistent-subcommand")

    def test_missing_option_value_returns_json(self):
        """--feature without a value should return USAGE_ERROR JSON."""
        result = runner.invoke(app, ["feature-state", "--feature"])
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--feature")


# ---------------------------------------------------------------------------
# Repro 2: Envelope shape validation
# ---------------------------------------------------------------------------


class TestUsageErrorEnvelopeShape:
    """The USAGE_ERROR envelope must have the full canonical shape."""

    def test_envelope_has_all_required_keys(self):
        result = runner.invoke(app, ["feature-state"])
        env = _parse_envelope(result.output)
        required_keys = {
            "contract_version",
            "command",
            "timestamp",
            "correlation_id",
            "success",
            "error_code",
            "data",
        }
        assert required_keys.issubset(set(env.keys())), f"Missing keys: {required_keys - set(env.keys())}"

    def test_envelope_command_is_unknown(self):
        """When --mission is omitted, the command is still identified; command='orchestrator-api.feature-state'."""
        result = runner.invoke(app, ["feature-state"])
        env = _parse_envelope(result.output)
        assert env["command"] == "orchestrator-api.feature-state"

    def test_correlation_id_present(self):
        result = runner.invoke(app, ["feature-state"])
        env = _parse_envelope(result.output)
        assert env["correlation_id"].startswith("corr-")


# ---------------------------------------------------------------------------
# Repro 3: --no-json flag is removed (breaking change)
# ---------------------------------------------------------------------------


class TestNoJsonFlagRemoved:
    """The --no-json flag must no longer be accepted."""

    def test_no_json_flag_rejected_on_contract_version(self):
        result = runner.invoke(app, ["contract-version", "--no-json"])
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--no-json")

    def test_no_json_flag_rejected_on_feature_state(self):
        result = runner.invoke(app, ["feature-state", "--feature", "dummy", "--no-json"])
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--no-json")

    def test_no_json_flag_rejected_on_transition(self):
        result = runner.invoke(
            app,
            [
                "transition",
                "--feature",
                "dummy",
                "--wp",
                "WP01",
                "--to",
                "done",
                "--actor",
                "test",
                "--no-json",
            ],
        )
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--no-json")

    def test_json_flag_also_rejected(self):
        """--json was part of --json/--no-json pair; both must be gone."""
        result = runner.invoke(app, ["contract-version", "--json"])
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--json")


# ---------------------------------------------------------------------------
# Positive control: valid commands still work
# ---------------------------------------------------------------------------


class TestValidCommandsStillWork:
    """Ensure the JSON error handler doesn't break normal command execution."""

    def test_contract_version_still_returns_success(self):
        result = runner.invoke(app, ["contract-version"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["error_code"] is None

    def test_contract_version_with_provider_version(self):
        result = runner.invoke(app, ["contract-version", "--provider-version", "0.1.0"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True


# ---------------------------------------------------------------------------
# Root CLI path: orchestrator-api invoked through the real root CLI app
# ---------------------------------------------------------------------------


class TestRootCLIPath:
    """Invoke orchestrator-api commands through the root CLI app.

    The existing test classes above invoke the orchestrator-api sub-app
    directly. This class exercises the NESTED dispatch path through the
    root ``spec-kitty`` CLI -- the exact path that external orchestrators
    use and the path that was broken in Issue #304 / GH issue #3.
    """

    # -- T005: success tests ------------------------------------------------

    def test_contract_version_success_through_root(self):
        """contract-version through root CLI produces valid JSON envelope."""
        result = runner.invoke(root_app, ["orchestrator-api", "contract-version"])
        assert result.exit_code == 0, result.output
        data = _parse_envelope(result.output)
        assert data["success"] is True
        assert data["error_code"] is None
        assert data["data"]["api_version"] is not None

    def test_contract_version_with_provider_through_root(self):
        """contract-version with --provider-version through root CLI."""
        result = runner.invoke(
            root_app,
            [
                "orchestrator-api",
                "contract-version",
                "--provider-version",
                "0.1.0",
            ],
        )
        assert result.exit_code == 0, result.output
        data = _parse_envelope(result.output)
        assert data["success"] is True

    # -- T006: error tests (regression for Issue #304) ----------------------

    def test_unknown_flag_through_root(self):
        """Unknown flag through root CLI must return USAGE_ERROR JSON, not prose.

        This is the definitive regression test for Issue #304.
        """
        result = runner.invoke(
            root_app,
            [
                "orchestrator-api",
                "contract-version",
                "--bogus",
            ],
        )
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--bogus")

    def test_unknown_subcommand_through_root(self):
        """Unknown subcommand through root CLI must return USAGE_ERROR JSON."""
        result = runner.invoke(
            root_app,
            [
                "orchestrator-api",
                "nonexistent-command",
            ],
        )
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="nonexistent-command")

    def test_missing_required_args_through_root(self):
        """Missing required args through root CLI must return USAGE_ERROR JSON."""
        result = runner.invoke(
            root_app,
            [
                "orchestrator-api",
                "feature-state",
            ],
        )
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--mission")

    def test_json_flag_rejected_through_root(self):
        """--json flag through root CLI must return USAGE_ERROR (no such flag)."""
        result = runner.invoke(
            root_app,
            [
                "orchestrator-api",
                "contract-version",
                "--json",
            ],
        )
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--json")

    def test_group_level_unknown_flag_through_root(self):
        """Unknown flag on the group itself (not a subcommand) must return JSON.

        orchestrator-api --bogus (flag on the group, before subcommand
        resolution) hits make_context(), not invoke(). Without the
        make_context() override this produces prose from BannerGroup.
        """
        result = runner.invoke(
            root_app,
            [
                "orchestrator-api",
                "--bogus",
            ],
        )
        assert result.exit_code != 0
        _assert_usage_error(result.output, substring="--bogus")
