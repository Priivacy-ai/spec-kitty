"""Tests for ``specify_cli.widen.audience``.

Covers: trim parsing, cancel paths, SaaS error handling, confirmation output.
Interactive prompt is exercised via ``monkeypatch`` on ``console.input``.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

from rich.console import Console

from specify_cli.saas_client import (
    SaasAuthError,
    SaasClientError,
    SaasTimeoutError,
)
from specify_cli.widen.audience import (
    _parse_audience_input,
    _prompt_audience,
    run_audience_review,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(members: list[str] | None = None, side_effect: Exception | None = None) -> MagicMock:
    """Return a mock SaasClient."""
    client = MagicMock()
    if side_effect is not None:
        client.get_audience_default.side_effect = side_effect
    else:
        client.get_audience_default.return_value = members if members is not None else []
    return client


def _make_console() -> tuple[Console, StringIO]:
    """Return a Console writing to a StringIO buffer, plus the buffer itself."""
    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=True)
    return console, buf


# ---------------------------------------------------------------------------
# _parse_audience_input — unit tests
# ---------------------------------------------------------------------------


class TestParseAudienceInput:
    DEFAULT = ["Alice Johnson", "Bob Smith", "Carol Lee", "Dana Park"]

    def test_empty_string_returns_full_default(self) -> None:
        result, unknown = _parse_audience_input("", self.DEFAULT)
        assert result == self.DEFAULT
        assert unknown == []

    def test_whitespace_only_returns_full_default(self) -> None:
        result, unknown = _parse_audience_input("   ", self.DEFAULT)
        assert result == self.DEFAULT
        assert unknown == []

    def test_commas_only_treated_as_empty(self) -> None:
        result, unknown = _parse_audience_input(",,,", self.DEFAULT)
        assert result == self.DEFAULT
        assert unknown == []

    def test_csv_with_all_known_names(self) -> None:
        result, unknown = _parse_audience_input("Alice Johnson, Carol Lee", self.DEFAULT)
        assert result == ["Alice Johnson", "Carol Lee"]
        assert unknown == []

    def test_csv_case_insensitive_match(self) -> None:
        result, unknown = _parse_audience_input("alice johnson, CAROL LEE", self.DEFAULT)
        # Should return canonical casing from default_audience
        assert result == ["Alice Johnson", "Carol Lee"]
        assert unknown == []

    def test_csv_with_unknown_name_includes_it(self) -> None:
        result, unknown = _parse_audience_input("Alice Johnson, Eve Newcomer", self.DEFAULT)
        assert "Alice Johnson" in result
        assert "Eve Newcomer" in result
        assert unknown == ["Eve Newcomer"]

    def test_all_unknown_names(self) -> None:
        result, unknown = _parse_audience_input("Zara X, Yuri Z", self.DEFAULT)
        assert result == ["Zara X", "Yuri Z"]
        assert unknown == ["Zara X", "Yuri Z"]

    def test_single_known_name(self) -> None:
        result, unknown = _parse_audience_input("Bob Smith", self.DEFAULT)
        assert result == ["Bob Smith"]
        assert unknown == []

    def test_extra_whitespace_around_names(self) -> None:
        result, unknown = _parse_audience_input("  Alice Johnson  ,  Dana Park  ", self.DEFAULT)
        assert result == ["Alice Johnson", "Dana Park"]
        assert unknown == []


# ---------------------------------------------------------------------------
# _prompt_audience — cancel paths
# ---------------------------------------------------------------------------


class TestPromptAudience:
    def test_cancel_keyword_returns_none(self) -> None:
        console, buf = _make_console()
        with patch.object(console, "input", return_value="cancel"):
            result = _prompt_audience(console)
        assert result is None

    def test_cancel_case_insensitive(self) -> None:
        console, _ = _make_console()
        with patch.object(console, "input", return_value="CANCEL"):
            result = _prompt_audience(console)
        assert result is None

    def test_cancel_with_whitespace(self) -> None:
        console, _ = _make_console()
        with patch.object(console, "input", return_value="  cancel  "):
            result = _prompt_audience(console)
        assert result is None

    def test_keyboard_interrupt_returns_none(self) -> None:
        console, buf = _make_console()
        with patch.object(console, "input", side_effect=KeyboardInterrupt):
            result = _prompt_audience(console)
        assert result is None
        output = buf.getvalue()
        assert "canceled" in output.lower()

    def test_eof_error_returns_none(self) -> None:
        console, _ = _make_console()
        with patch.object(console, "input", side_effect=EOFError):
            result = _prompt_audience(console)
        assert result is None

    def test_normal_input_returned(self) -> None:
        console, _ = _make_console()
        with patch.object(console, "input", return_value="Alice Johnson"):
            result = _prompt_audience(console)
        assert result == "Alice Johnson"

    def test_empty_input_returned(self) -> None:
        console, _ = _make_console()
        with patch.object(console, "input", return_value=""):
            result = _prompt_audience(console)
        assert result == ""


# ---------------------------------------------------------------------------
# run_audience_review — integration-style tests
# ---------------------------------------------------------------------------


class TestRunAudienceReview:
    MEMBERS = ["Alice Johnson", "Bob Smith", "Carol Lee"]

    def _run(
        self,
        input_text: str,
        members: list[str] | None = None,
        side_effect: Exception | None = None,
    ) -> tuple[list[str] | None, str]:
        """Run audience review with patched console.input, return (result, output)."""
        client = _make_client(
            members=members if members is not None else self.MEMBERS,
            side_effect=side_effect,
        )
        console, buf = _make_console()
        with patch.object(console, "input", return_value=input_text):
            result = run_audience_review(client, "mission-abc", "Should we use PostgreSQL?", console)
        return result, buf.getvalue()

    def test_empty_input_returns_full_default(self) -> None:
        result, _ = self._run("")
        assert result == self.MEMBERS

    def test_csv_trim_returns_subset(self) -> None:
        result, _ = self._run("Alice Johnson, Carol Lee")
        assert result == ["Alice Johnson", "Carol Lee"]

    def test_csv_with_unknown_name_includes_it(self) -> None:
        result, output = self._run("Alice Johnson, Eve Newcomer")
        assert result is not None
        assert "Alice Johnson" in result
        assert "Eve Newcomer" in result
        assert "Note:" in output
        assert "Eve Newcomer" in output

    def test_cancel_keyword_returns_none(self) -> None:
        result, _ = self._run("cancel")
        assert result is None

    def test_keyboard_interrupt_returns_none(self) -> None:
        client = _make_client(members=self.MEMBERS)
        console, buf = _make_console()
        with patch.object(console, "input", side_effect=KeyboardInterrupt):
            result = run_audience_review(client, "mission-abc", "Question?", console)
        assert result is None

    def test_confirmation_message_shown(self) -> None:
        result, output = self._run("Alice Johnson")
        assert result is not None
        assert "Audience confirmed:" in output
        assert "Alice Johnson" in output
        assert "1 members" in output
        assert "Calling widen endpoint" in output

    def test_panel_title_truncated_to_60_chars(self) -> None:
        long_question = "A" * 80
        client = _make_client(members=self.MEMBERS)
        console, buf = _make_console()
        with patch.object(console, "input", return_value=""):
            run_audience_review(client, "mission-abc", long_question, console)
        output = buf.getvalue()
        # Title is "Widen: " + first 60 chars — should not contain 61st char
        # In the rendered output there should be 60 'A' chars but not 61
        assert "A" * 60 in output
        # The 61st char should not appear in the title context
        # (Panel title is truncated at :60 before passing to Panel)
        panel_section = output[: output.index("Default audience")]
        assert len([c for c in panel_section if c == "A"]) <= 60

    def test_empty_audience_from_saas_returns_none(self) -> None:
        result, output = self._run("", members=[])
        assert result is None
        assert "No default audience" in output

    def test_saas_timeout_error_returns_none(self) -> None:
        result, output = self._run("", side_effect=SaasTimeoutError("timed out"))
        assert result is None
        assert "Widen failed:" in output
        assert "timed out" in output.lower()
        assert "Returning to interview prompt" in output

    def test_saas_auth_error_returns_none(self) -> None:
        result, output = self._run("", side_effect=SaasAuthError("Forbidden", status_code=403))
        assert result is None
        assert "Widen failed:" in output
        assert "Authentication error" in output
        assert "Returning to interview prompt" in output

    def test_saas_generic_error_returns_none(self) -> None:
        result, output = self._run("", side_effect=SaasClientError("something went wrong"))
        assert result is None
        assert "Widen failed:" in output
        assert "something went wrong" in output
        assert "Returning to interview prompt" in output

    def test_saas_client_called_with_mission_id(self) -> None:
        client = _make_client(members=self.MEMBERS)
        console, _ = _make_console()
        with patch.object(console, "input", return_value=""):
            run_audience_review(client, "mission-xyz-123", "Question?", console)
        client.get_audience_default.assert_called_once_with("mission-xyz-123")

    def test_widen_key_audience_included_in_output(self) -> None:
        result, output = self._run("")
        assert result == self.MEMBERS
        # Names should appear in the panel body
        assert "Alice Johnson" in output
        assert "Bob Smith" in output
        assert "Carol Lee" in output
