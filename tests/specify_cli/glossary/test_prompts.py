"""Tests for Typer prompts and non-interactive detection (WP06/T026, T027)."""

import os
import pytest
from unittest.mock import patch

import typer

from specify_cli.glossary.models import (
    SemanticConflict,
    Severity,
    TermSurface,
    ConflictType,
    SenseRef,
)
from specify_cli.glossary.prompts import (
    PromptChoice,
    is_interactive,
    auto_defer_conflicts,
    prompt_conflict_resolution,
    prompt_conflict_resolution_safe,
    prompt_context_change_confirmation,
    log_non_interactive_context,
)


@pytest.fixture
def ambiguous_conflict():
    """Ambiguous conflict with 2 candidates."""
    return SemanticConflict(
        term=TermSurface("workspace"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        confidence=0.9,
        candidate_senses=[
            SenseRef("workspace", "mission_local", "Git worktree directory", 0.9),
            SenseRef("workspace", "team_domain", "VS Code workspace file", 0.7),
        ],
        context="description field",
    )


@pytest.fixture
def no_candidate_conflict():
    """Conflict with 0 candidates."""
    return SemanticConflict(
        term=TermSurface("helper"),
        conflict_type=ConflictType.UNKNOWN,
        severity=Severity.LOW,
        confidence=0.3,
        candidate_senses=[],
        context="output field",
    )


class TestIsInteractive:
    """Test is_interactive() detection."""

    @patch("specify_cli.glossary.prompts.sys")
    def test_non_tty_returns_false(self, mock_sys):
        """Non-TTY stdin returns False."""
        mock_sys.stdin.isatty.return_value = False
        assert is_interactive() is False

    @patch("specify_cli.glossary.prompts.sys")
    def test_ci_env_var_returns_false(self, mock_sys):
        """CI=true env var returns False even with TTY."""
        mock_sys.stdin.isatty.return_value = True
        with patch.dict(os.environ, {"CI": "true"}):
            assert is_interactive() is False

    @patch("specify_cli.glossary.prompts.sys")
    def test_github_actions_returns_false(self, mock_sys):
        """GITHUB_ACTIONS env var returns False."""
        mock_sys.stdin.isatty.return_value = True
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            assert is_interactive() is False

    @patch("specify_cli.glossary.prompts.sys")
    def test_jenkins_home_returns_false(self, mock_sys):
        """JENKINS_HOME env var returns False."""
        mock_sys.stdin.isatty.return_value = True
        with patch.dict(os.environ, {"JENKINS_HOME": "/var/jenkins"}, clear=False):
            assert is_interactive() is False

    @patch("specify_cli.glossary.prompts.sys")
    def test_gitlab_ci_returns_false(self, mock_sys):
        """GITLAB_CI env var returns False."""
        mock_sys.stdin.isatty.return_value = True
        with patch.dict(os.environ, {"GITLAB_CI": "true"}, clear=False):
            assert is_interactive() is False

    @patch("specify_cli.glossary.prompts.sys")
    def test_circleci_returns_false(self, mock_sys):
        """CIRCLECI env var returns False."""
        mock_sys.stdin.isatty.return_value = True
        with patch.dict(os.environ, {"CIRCLECI": "true"}, clear=False):
            assert is_interactive() is False

    @patch("specify_cli.glossary.prompts.sys")
    def test_buildkite_returns_false(self, mock_sys):
        """BUILDKITE env var returns False."""
        mock_sys.stdin.isatty.return_value = True
        with patch.dict(os.environ, {"BUILDKITE": "true"}, clear=False):
            assert is_interactive() is False

    @patch("specify_cli.glossary.prompts.sys")
    def test_tty_no_ci_returns_true(self, mock_sys):
        """TTY stdin with no CI env vars returns True."""
        mock_sys.stdin.isatty.return_value = True
        # Clear all CI env vars
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k
            not in [
                "CI",
                "GITHUB_ACTIONS",
                "JENKINS_HOME",
                "GITLAB_CI",
                "CIRCLECI",
                "TRAVIS",
                "BUILDKITE",
            ]
        }
        with patch.dict(os.environ, env_clean, clear=True):
            assert is_interactive() is True


class TestAutoDefer:
    """Test auto_defer_conflicts."""

    def test_empty_list(self):
        """Empty conflicts returns empty list."""
        result = auto_defer_conflicts([])
        assert result == []

    def test_all_deferred(self, ambiguous_conflict, no_candidate_conflict):
        """All conflicts get DEFER choice."""
        result = auto_defer_conflicts([ambiguous_conflict, no_candidate_conflict])
        assert len(result) == 2
        for conflict, choice, value in result:
            assert choice == PromptChoice.DEFER
            assert value is None

    def test_preserves_conflict_objects(self, ambiguous_conflict):
        """Conflict objects are preserved in output."""
        result = auto_defer_conflicts([ambiguous_conflict])
        assert result[0][0] is ambiguous_conflict


class TestPromptConflictResolution:
    """Test prompt_conflict_resolution interactive prompts."""

    @patch("specify_cli.glossary.prompts.typer.prompt", return_value="1")
    def test_select_first_candidate(self, mock_prompt, ambiguous_conflict):
        """Selecting '1' returns (SELECT_CANDIDATE, 0)."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.SELECT_CANDIDATE
        assert value == 0  # 0-indexed

    @patch("specify_cli.glossary.prompts.typer.prompt", return_value="2")
    def test_select_second_candidate(self, mock_prompt, ambiguous_conflict):
        """Selecting '2' returns (SELECT_CANDIDATE, 1)."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.SELECT_CANDIDATE
        assert value == 1

    @patch("specify_cli.glossary.prompts.typer.prompt", return_value="D")
    def test_defer(self, mock_prompt, ambiguous_conflict):
        """Selecting 'D' returns (DEFER, None)."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.DEFER
        assert value is None

    @patch("specify_cli.glossary.prompts.typer.prompt", return_value="d")
    def test_defer_lowercase(self, mock_prompt, ambiguous_conflict):
        """Lowercase 'd' is converted to uppercase."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.DEFER
        assert value is None

    @patch("specify_cli.glossary.prompts.typer.prompt", side_effect=["C", "My custom definition"])
    def test_custom_sense(self, mock_prompt, ambiguous_conflict):
        """Selecting 'C' then providing definition returns (CUSTOM_SENSE, definition)."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.CUSTOM_SENSE
        assert value == "My custom definition"

    @patch("specify_cli.glossary.prompts.typer.prompt", side_effect=["c", "A definition"])
    def test_custom_sense_lowercase(self, mock_prompt, ambiguous_conflict):
        """Lowercase 'c' is accepted for custom sense."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.CUSTOM_SENSE
        assert value == "A definition"

    @patch("specify_cli.glossary.prompts.typer.echo")
    @patch("specify_cli.glossary.prompts.typer.prompt", side_effect=["C", "  ", "C", "Valid definition"])
    def test_empty_custom_definition_rejected(self, mock_prompt, mock_echo, ambiguous_conflict):
        """Empty custom definition is rejected and re-prompts."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.CUSTOM_SENSE
        assert value == "Valid definition"
        # Verify error message was shown
        error_calls = [str(c) for c in mock_echo.call_args_list if "empty" in str(c).lower()]
        assert len(error_calls) > 0

    @patch("specify_cli.glossary.prompts.typer.echo")
    @patch("specify_cli.glossary.prompts.typer.prompt", side_effect=["X", "D"])
    def test_invalid_input_reprompts(self, mock_prompt, mock_echo, ambiguous_conflict):
        """Invalid input shows error and re-prompts."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.DEFER
        # Verify error message was shown for 'X'
        error_calls = [str(c) for c in mock_echo.call_args_list if "invalid" in str(c).lower()]
        assert len(error_calls) > 0

    @patch("specify_cli.glossary.prompts.typer.echo")
    @patch("specify_cli.glossary.prompts.typer.prompt", side_effect=["99", "1"])
    def test_out_of_range_number_reprompts(self, mock_prompt, mock_echo, ambiguous_conflict):
        """Number > num_candidates shows error and re-prompts."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.SELECT_CANDIDATE
        assert value == 0
        # Verify error message was shown for '99'
        error_calls = [
            str(c) for c in mock_echo.call_args_list if "between 1 and" in str(c).lower() or "enter" in str(c).lower()
        ]
        assert len(error_calls) > 0

    @patch("specify_cli.glossary.prompts.typer.echo")
    @patch("specify_cli.glossary.prompts.typer.prompt", side_effect=["0", "1"])
    def test_zero_rejected(self, mock_prompt, mock_echo, ambiguous_conflict):
        """'0' is rejected as out of range."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.SELECT_CANDIDATE
        assert value == 0  # Eventually selected '1' which is index 0

    @patch("specify_cli.glossary.prompts.typer.prompt", return_value="  D  ")
    def test_whitespace_stripped(self, mock_prompt, ambiguous_conflict):
        """Leading/trailing whitespace is stripped."""
        choice, value = prompt_conflict_resolution(ambiguous_conflict)
        assert choice == PromptChoice.DEFER

    @patch("specify_cli.glossary.prompts.typer.prompt", side_effect=typer.Abort)
    @patch("specify_cli.glossary.prompts.typer.echo")
    def test_ctrl_c_raises_abort(self, mock_echo, mock_prompt, ambiguous_conflict):
        """Ctrl+C raises typer.Abort."""
        with pytest.raises(typer.Abort):
            prompt_conflict_resolution(ambiguous_conflict)

    @patch("specify_cli.glossary.prompts.typer.prompt", return_value="D")
    def test_no_candidates_only_c_and_d(self, mock_prompt, no_candidate_conflict):
        """Conflict with 0 candidates only shows C and D options."""
        choice, value = prompt_conflict_resolution(no_candidate_conflict)
        assert choice == PromptChoice.DEFER

    @patch("specify_cli.glossary.prompts.typer.echo")
    @patch("specify_cli.glossary.prompts.typer.prompt", side_effect=["3", "D"])
    def test_number_rejected_when_no_candidates(self, mock_prompt, mock_echo, no_candidate_conflict):
        """Number input rejected when conflict has no candidates."""
        choice, value = prompt_conflict_resolution(no_candidate_conflict)
        assert choice == PromptChoice.DEFER


class TestPromptConflictResolutionSafe:
    """Test safe prompt wrapper with non-interactive detection."""

    @patch("specify_cli.glossary.prompts.is_interactive", return_value=False)
    @patch("specify_cli.glossary.prompts.typer.echo")
    def test_non_interactive_auto_defers(self, mock_echo, mock_is_interactive, ambiguous_conflict):
        """Non-interactive mode auto-defers."""
        choice, value = prompt_conflict_resolution_safe(ambiguous_conflict)
        assert choice == PromptChoice.DEFER
        assert value is None

    @patch("specify_cli.glossary.prompts.is_interactive", return_value=False)
    @patch("specify_cli.glossary.prompts.typer.echo")
    def test_non_interactive_prints_message(self, mock_echo, mock_is_interactive, ambiguous_conflict):
        """Non-interactive mode prints auto-defer message."""
        prompt_conflict_resolution_safe(ambiguous_conflict)
        echo_text = str(mock_echo.call_args_list)
        assert "workspace" in echo_text.lower() or "auto-deferring" in echo_text.lower()

    @patch("specify_cli.glossary.prompts.is_interactive", return_value=True)
    @patch(
        "specify_cli.glossary.prompts.prompt_conflict_resolution",
        return_value=(PromptChoice.SELECT_CANDIDATE, 0),
    )
    def test_interactive_delegates_to_prompt(self, mock_prompt, mock_is_interactive, ambiguous_conflict):
        """Interactive mode delegates to prompt_conflict_resolution."""
        choice, value = prompt_conflict_resolution_safe(ambiguous_conflict)
        assert choice == PromptChoice.SELECT_CANDIDATE
        assert value == 0
        mock_prompt.assert_called_once_with(ambiguous_conflict)


class TestPromptContextChangeConfirmation:
    """Test context change confirmation prompt."""

    @patch("specify_cli.glossary.prompts.typer.confirm", return_value=True)
    @patch("specify_cli.glossary.prompts.typer.echo")
    def test_user_confirms(self, mock_echo, mock_confirm):
        """User confirming returns True."""
        result = prompt_context_change_confirmation("abcdef1234567890abcdef", "1234567890abcdef1234")
        assert result is True

    @patch("specify_cli.glossary.prompts.typer.confirm", return_value=False)
    @patch("specify_cli.glossary.prompts.typer.echo")
    def test_user_declines(self, mock_echo, mock_confirm):
        """User declining returns False."""
        result = prompt_context_change_confirmation("abcdef1234567890abcdef", "1234567890abcdef1234")
        assert result is False

    @patch("specify_cli.glossary.prompts.typer.confirm", return_value=False)
    @patch("specify_cli.glossary.prompts.typer.echo")
    def test_shows_hash_comparison(self, mock_echo, mock_confirm):
        """Shows original and current hash in output."""
        prompt_context_change_confirmation("abcdef1234567890abcdef", "1234567890abcdef1234")
        echo_text = str(mock_echo.call_args)
        assert "abcdef1234567890" in echo_text  # First 16 chars
        assert "1234567890abcdef" in echo_text


class TestLogNonInteractiveContext:
    """Test log_non_interactive_context."""

    @patch("specify_cli.glossary.prompts.is_interactive", return_value=True)
    def test_interactive_no_log(self, mock_is_interactive, caplog):
        """No log output in interactive mode."""
        import logging

        with caplog.at_level(logging.INFO):
            log_non_interactive_context()
        assert "Non-interactive mode" not in caplog.text

    @patch("specify_cli.glossary.prompts.is_interactive", return_value=False)
    @patch("specify_cli.glossary.prompts.sys")
    def test_non_interactive_logs(self, mock_sys, mock_is_interactive, caplog):
        """Logs non-interactive context details."""
        import logging

        mock_sys.stdin.isatty.return_value = False
        with caplog.at_level(logging.INFO):
            log_non_interactive_context()
        assert "Non-interactive mode" in caplog.text


class TestPromptChoiceEnum:
    """Test PromptChoice enum values."""

    def test_select_candidate_value(self):
        assert PromptChoice.SELECT_CANDIDATE == "select"

    def test_custom_sense_value(self):
        assert PromptChoice.CUSTOM_SENSE == "custom"

    def test_defer_value(self):
        assert PromptChoice.DEFER == "defer"
