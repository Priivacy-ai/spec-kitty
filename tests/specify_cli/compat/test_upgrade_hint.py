"""Unit tests for UpgradeHint and build_upgrade_hint (T013 — hint catalog coverage).

Every InstallMethod value must yield a valid hint satisfying the invariant
(exactly one of command / note is non-None).  Security properties are tested
by attempting to construct an UpgradeHint with a disallowed command string.
"""

from __future__ import annotations

import pytest

from specify_cli.compat._detect.install_method import InstallMethod
from specify_cli.compat.upgrade_hint import UpgradeHint, build_upgrade_hint


# ---------------------------------------------------------------------------
# Invariant: exactly one of command / note is non-None
# ---------------------------------------------------------------------------


class TestInvariant:
    @pytest.mark.parametrize("method", list(InstallMethod))
    def test_every_method_produces_valid_hint(self, method: InstallMethod) -> None:
        """build_upgrade_hint must return a hint satisfying the invariant."""
        hint = build_upgrade_hint(method)
        assert hint.install_method == method
        # Exactly one of command/note is non-None.
        assert (hint.command is None) != (hint.note is None), (
            f"{method}: expected exactly one of command/note to be set; command={hint.command!r}, note={hint.note!r}"
        )

    @pytest.mark.parametrize("method", list(InstallMethod))
    def test_hint_is_frozen(self, method: InstallMethod) -> None:
        """UpgradeHint is frozen — mutation must raise."""
        hint = build_upgrade_hint(method)
        with pytest.raises((AttributeError, TypeError)):
            hint.command = "new value"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Command-bearing hints (PIPX, PIP_USER, PIP_SYSTEM, BREW)
# ---------------------------------------------------------------------------


class TestCommandHints:
    @pytest.mark.parametrize(
        "method,expected_fragment",
        [
            (InstallMethod.PIPX, "pipx upgrade"),
            (InstallMethod.PIP_USER, "pip install --user --upgrade"),
            (InstallMethod.PIP_SYSTEM, "pip install --upgrade"),
            (InstallMethod.BREW, "brew upgrade"),
        ],
    )
    def test_command_contains_expected_fragment(self, method: InstallMethod, expected_fragment: str) -> None:
        hint = build_upgrade_hint(method)
        assert hint.command is not None
        assert expected_fragment in hint.command
        assert hint.note is None

    @pytest.mark.parametrize(
        "method",
        [InstallMethod.PIPX, InstallMethod.PIP_USER, InstallMethod.PIP_SYSTEM, InstallMethod.BREW],
    )
    def test_command_does_not_contain_ansi(self, method: InstallMethod) -> None:
        hint = build_upgrade_hint(method)
        assert hint.command is not None
        assert "\x1b" not in hint.command
        assert "\033" not in hint.command


# ---------------------------------------------------------------------------
# Note-only hints (SOURCE, SYSTEM_PACKAGE, UNKNOWN)
# ---------------------------------------------------------------------------


class TestNoteHints:
    @pytest.mark.parametrize(
        "method",
        [InstallMethod.SOURCE, InstallMethod.SYSTEM_PACKAGE, InstallMethod.UNKNOWN],
    )
    def test_note_hints_have_no_command(self, method: InstallMethod) -> None:
        """SOURCE, SYSTEM_PACKAGE, UNKNOWN MUST NOT carry a runnable command (CHK031)."""
        hint = build_upgrade_hint(method)
        assert hint.command is None, f"{method}: command must be None for security (CHK031); got {hint.command!r}"
        assert hint.note is not None
        assert len(hint.note) > 0

    def test_unknown_note_mentions_docs_or_upgrade(self) -> None:
        hint = build_upgrade_hint(InstallMethod.UNKNOWN)
        # The note should be informative, not a bare runnable command.
        assert hint.command is None
        assert "install" in hint.note.lower() or "upgrade" in hint.note.lower()

    def test_source_note_mentions_source_or_workflow(self) -> None:
        hint = build_upgrade_hint(InstallMethod.SOURCE)
        assert hint.command is None
        text = hint.note.lower()
        assert "source" in text or "dev" in text or "pip install" in text


# ---------------------------------------------------------------------------
# Security: disallowed characters in command field
# ---------------------------------------------------------------------------


class TestCommandSanitisation:
    @pytest.mark.parametrize(
        "bad_command",
        [
            "\x1b[31mevil\x1b[0m",  # ANSI escape sequence
            "$(whoami)",  # shell subshell injection
            "cmd; other",  # semicolon (shell separator)
            "cmd && other",  # && (shell AND) — & not in allowed set
            "cmd | cat",  # pipe — | not in allowed set
            "a" * 129,  # too long (>128 chars)
            "",  # empty string
            "cmd\nnewline",  # embedded newline
            "cmd\ttab",  # embedded tab
            "cmd `backtick`",  # backtick — ` not in allowed set
            "cmd#comment",  # hash — # not in allowed set
        ],
    )
    def test_disallowed_command_raises_value_error(self, bad_command: str) -> None:
        """Constructing an UpgradeHint with a disallowed command must raise ValueError."""
        with pytest.raises(ValueError, match="disallowed"):
            UpgradeHint(
                install_method=InstallMethod.PIPX,
                command=bad_command,
                note=None,
            )

    def test_allowed_command_passes(self) -> None:
        hint = UpgradeHint(
            install_method=InstallMethod.PIPX,
            command="pipx upgrade spec-kitty-cli",
            note=None,
        )
        assert hint.command == "pipx upgrade spec-kitty-cli"

    def test_none_command_with_note_passes(self) -> None:
        hint = UpgradeHint(
            install_method=InstallMethod.UNKNOWN,
            command=None,
            note="Some manual instructions.",
        )
        assert hint.note == "Some manual instructions."
        assert hint.command is None


# ---------------------------------------------------------------------------
# Invariant enforcement at construction time
# ---------------------------------------------------------------------------


class TestInvariantEnforcement:
    def test_both_command_and_note_raises(self) -> None:
        with pytest.raises(ValueError):
            UpgradeHint(
                install_method=InstallMethod.PIPX,
                command="pipx upgrade spec-kitty-cli",
                note="Some note",
            )

    def test_neither_command_nor_note_raises(self) -> None:
        with pytest.raises(ValueError):
            UpgradeHint(
                install_method=InstallMethod.PIPX,
                command=None,
                note=None,
            )


# ---------------------------------------------------------------------------
# build_upgrade_hint with package argument (reserved path)
# ---------------------------------------------------------------------------


class TestBuildUpgradeHintPackageArg:
    def test_package_arg_is_accepted_without_error(self) -> None:
        """The *package* kwarg is accepted (reserved for future use)."""
        hint = build_upgrade_hint(InstallMethod.PIPX, package="spec-kitty-cli")
        assert hint.install_method == InstallMethod.PIPX
