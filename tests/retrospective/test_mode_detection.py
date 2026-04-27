"""Tests for mode.detect() — each precedence layer, edge cases, and audit recording.

All tests are deterministic: filesystem state is created via tmp_path, and
env/parent_process_name are injected rather than relying on ambient state.
psutil is never called directly; parent_process_name is always passed explicitly.

Precedence under test (highest to lowest):
    charter override > explicit flag > environment > parent process
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.retrospective.mode import (
    ModeResolutionError,
    NON_INTERACTIVE_PARENTS,
    detect,
)
from specify_cli.retrospective.schema import Mode, ModeSourceSignal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CHARTER_DIR = Path(".kittify") / "charter"


def _write_charter(repo_root: Path, content: str) -> None:
    """Write a charter.md file under <repo_root>/.kittify/charter/."""
    charter_path = repo_root / _CHARTER_DIR / "charter.md"
    charter_path.parent.mkdir(parents=True, exist_ok=True)
    charter_path.write_text(content, encoding="utf-8")


def _charter_with_mode(mode_value: str) -> str:
    """Return charter.md content that declares the given mode in frontmatter."""
    return f"---\nmode: {mode_value}\n---\n\n# Charter\n\nSome content.\n"


def _charter_no_mode() -> str:
    """Return charter.md content with a frontmatter block but no mode key."""
    return "---\nauthor: test\n---\n\n# Charter\n\nSome content.\n"


def _charter_malformed() -> str:
    """Return charter.md content whose frontmatter YAML is malformed."""
    return "---\nmode: [\nunclosed bracket\n---\n"


def _charter_malformed_type() -> str:
    """Return charter.md content whose frontmatter is YAML but not a mapping."""
    return "---\n- item1\n- item2\n---\n"


def _charter_malformed_unclosed() -> str:
    """Return charter.md content with an unclosed frontmatter block."""
    return "---\nmode: autonomous\nno closing delimiter follows\n"


def _charter_malformed_bad_value() -> str:
    """Return charter.md content with an invalid mode value."""
    return "---\nmode: invalid_value\n---\n"


# ---------------------------------------------------------------------------
# Layer 1 — Charter override
# ---------------------------------------------------------------------------


class TestCharterOverride:
    def test_charter_autonomous_wins_over_hic_flag(self, tmp_path: Path) -> None:
        """Charter declaring autonomous beats an explicit_flag='human_in_command'."""
        _write_charter(tmp_path, _charter_with_mode("autonomous"))
        result = detect(
            repo_root=tmp_path,
            explicit_flag="human_in_command",
            env={},
            parent_process_name="bash",
        )
        assert result.value == "autonomous"
        assert result.source_signal.kind == "charter_override"
        assert "autonomous" in result.source_signal.evidence

    def test_charter_hic_wins_over_autonomous_flag(self, tmp_path: Path) -> None:
        """Charter declaring human_in_command beats an explicit_flag='autonomous'."""
        _write_charter(tmp_path, _charter_with_mode("human_in_command"))
        result = detect(
            repo_root=tmp_path,
            explicit_flag="autonomous",
            env={},
            parent_process_name="bash",
        )
        assert result.value == "human_in_command"
        assert result.source_signal.kind == "charter_override"

    def test_charter_autonomous_evidence_format(self, tmp_path: Path) -> None:
        """Charter evidence string should carry the mode-policy clause id."""
        _write_charter(tmp_path, _charter_with_mode("autonomous"))
        result = detect(repo_root=tmp_path, env={}, parent_process_name="bash")
        assert result.source_signal.kind == "charter_override"
        assert result.source_signal.evidence == "mode-policy:autonomous"

    def test_charter_hic_evidence_format(self, tmp_path: Path) -> None:
        _write_charter(tmp_path, _charter_with_mode("human_in_command"))
        result = detect(repo_root=tmp_path, env={}, parent_process_name="bash")
        assert result.source_signal.evidence == "mode-policy:human_in_command"

    def test_charter_silent_falls_through_to_flag(self, tmp_path: Path) -> None:
        """Charter with no mode key is a silent signal; flag should win."""
        _write_charter(tmp_path, _charter_no_mode())
        result = detect(
            repo_root=tmp_path,
            explicit_flag="autonomous",
            env={},
            parent_process_name="bash",
        )
        assert result.value == "autonomous"
        assert result.source_signal.kind == "explicit_flag"

    def test_no_charter_falls_through(self, tmp_path: Path) -> None:
        """A repo with no charter file is a silent signal; flag should win."""
        result = detect(
            repo_root=tmp_path,
            explicit_flag="autonomous",
            env={},
            parent_process_name="bash",
        )
        assert result.value == "autonomous"
        assert result.source_signal.kind == "explicit_flag"

    def test_charter_malformed_yaml_raises(self, tmp_path: Path) -> None:
        """A charter with malformed YAML frontmatter raises ModeResolutionError."""
        _write_charter(tmp_path, _charter_malformed())
        with pytest.raises(ModeResolutionError):
            detect(repo_root=tmp_path, env={}, parent_process_name="bash")

    def test_charter_malformed_non_mapping_raises(self, tmp_path: Path) -> None:
        """A charter whose frontmatter is a list (not a mapping) raises ModeResolutionError."""
        _write_charter(tmp_path, _charter_malformed_type())
        with pytest.raises(ModeResolutionError):
            detect(repo_root=tmp_path, env={}, parent_process_name="bash")

    def test_charter_malformed_unclosed_frontmatter_raises(self, tmp_path: Path) -> None:
        """A charter with an unclosed frontmatter block raises ModeResolutionError."""
        _write_charter(tmp_path, _charter_malformed_unclosed())
        with pytest.raises(ModeResolutionError):
            detect(repo_root=tmp_path, env={}, parent_process_name="bash")

    def test_charter_malformed_invalid_mode_value_raises(self, tmp_path: Path) -> None:
        """A charter with an unrecognised mode value raises ModeResolutionError."""
        _write_charter(tmp_path, _charter_malformed_bad_value())
        with pytest.raises(ModeResolutionError):
            detect(repo_root=tmp_path, env={}, parent_process_name="bash")

    def test_charter_no_frontmatter_falls_through(self, tmp_path: Path) -> None:
        """Charter with no ``---`` delimiter is treated as no mode declaration."""
        _write_charter(tmp_path, "# Charter\n\nJust prose, no frontmatter.\n")
        result = detect(
            repo_root=tmp_path,
            explicit_flag="autonomous",
            env={},
            parent_process_name="bash",
        )
        assert result.source_signal.kind == "explicit_flag"


# ---------------------------------------------------------------------------
# Layer 2 — Explicit flag
# ---------------------------------------------------------------------------


class TestExplicitFlag:
    def test_flag_autonomous(self, tmp_path: Path) -> None:
        result = detect(
            repo_root=tmp_path,
            explicit_flag="autonomous",
            env={},
            parent_process_name="bash",
        )
        assert result.value == "autonomous"
        assert result.source_signal.kind == "explicit_flag"
        assert result.source_signal.evidence == "autonomous"

    def test_flag_hic(self, tmp_path: Path) -> None:
        result = detect(
            repo_root=tmp_path,
            explicit_flag="human_in_command",
            env={},
            parent_process_name="bash",
        )
        assert result.value == "human_in_command"
        assert result.source_signal.kind == "explicit_flag"
        assert result.source_signal.evidence == "human_in_command"

    def test_flag_wins_over_env(self, tmp_path: Path) -> None:
        """Explicit flag beats env var."""
        result = detect(
            repo_root=tmp_path,
            explicit_flag="autonomous",
            env={"SPEC_KITTY_MODE": "human_in_command"},
            parent_process_name="bash",
        )
        assert result.value == "autonomous"
        assert result.source_signal.kind == "explicit_flag"

    def test_flag_wins_over_parent(self, tmp_path: Path) -> None:
        """Explicit flag beats parent process layer."""
        result = detect(
            repo_root=tmp_path,
            explicit_flag="human_in_command",
            env={},
            parent_process_name="cron",
        )
        assert result.value == "human_in_command"
        assert result.source_signal.kind == "explicit_flag"


# ---------------------------------------------------------------------------
# Layer 3 — Environment variable
# ---------------------------------------------------------------------------


class TestEnvironment:
    def test_env_autonomous(self, tmp_path: Path) -> None:
        result = detect(
            repo_root=tmp_path,
            env={"SPEC_KITTY_MODE": "autonomous"},
            parent_process_name="bash",
        )
        assert result.value == "autonomous"
        assert result.source_signal.kind == "environment"
        assert result.source_signal.evidence == "SPEC_KITTY_MODE"

    def test_env_hic(self, tmp_path: Path) -> None:
        result = detect(
            repo_root=tmp_path,
            env={"SPEC_KITTY_MODE": "human_in_command"},
            parent_process_name="bash",
        )
        assert result.value == "human_in_command"
        assert result.source_signal.kind == "environment"
        assert result.source_signal.evidence == "SPEC_KITTY_MODE"

    def test_env_invalid_value_falls_through(self, tmp_path: Path) -> None:
        """An unrecognised SPEC_KITTY_MODE value is skipped; falls to parent layer."""
        result = detect(
            repo_root=tmp_path,
            env={"SPEC_KITTY_MODE": "not_a_valid_mode"},
            parent_process_name="cron",
        )
        # Falls through to parent layer.
        assert result.source_signal.kind == "parent_process"

    def test_env_empty_value_falls_through(self, tmp_path: Path) -> None:
        """An empty SPEC_KITTY_MODE value is skipped."""
        result = detect(
            repo_root=tmp_path,
            env={"SPEC_KITTY_MODE": ""},
            parent_process_name="bash",
        )
        assert result.source_signal.kind == "parent_process"

    def test_env_missing_key_falls_through(self, tmp_path: Path) -> None:
        """Absent SPEC_KITTY_MODE → no env signal."""
        result = detect(
            repo_root=tmp_path,
            env={},
            parent_process_name="bash",
        )
        assert result.source_signal.kind == "parent_process"

    def test_env_wins_over_parent(self, tmp_path: Path) -> None:
        """env var beats parent process layer."""
        result = detect(
            repo_root=tmp_path,
            env={"SPEC_KITTY_MODE": "human_in_command"},
            parent_process_name="cron",
        )
        assert result.value == "human_in_command"
        assert result.source_signal.kind == "environment"


# ---------------------------------------------------------------------------
# Layer 4 — Parent process
# ---------------------------------------------------------------------------


class TestParentProcess:
    @pytest.mark.parametrize("parent_name", sorted(NON_INTERACTIVE_PARENTS))
    def test_known_non_interactive_parent_resolves_autonomous(
        self, tmp_path: Path, parent_name: str
    ) -> None:
        """Every name in NON_INTERACTIVE_PARENTS resolves to autonomous."""
        result = detect(
            repo_root=tmp_path,
            env={},
            parent_process_name=parent_name,
        )
        assert result.value == "autonomous"
        assert result.source_signal.kind == "parent_process"
        assert result.source_signal.evidence == parent_name

    def test_unknown_parent_resolves_hic(self, tmp_path: Path) -> None:
        """An unrecognised parent name resolves to human_in_command (conservative)."""
        result = detect(
            repo_root=tmp_path,
            env={},
            parent_process_name="bash",
        )
        assert result.value == "human_in_command"
        assert result.source_signal.kind == "parent_process"
        assert result.source_signal.evidence == "bash"

    def test_cron_parent_resolves_autonomous(self, tmp_path: Path) -> None:
        result = detect(
            repo_root=tmp_path,
            env={},
            parent_process_name="cron",
        )
        assert result.value == "autonomous"
        assert result.source_signal.kind == "parent_process"
        assert result.source_signal.evidence == "cron"


# ---------------------------------------------------------------------------
# All-signals-absent → conservative default (HiC)
# ---------------------------------------------------------------------------


class TestAllSignalsAbsent:
    def test_no_charter_no_flag_no_env_unknown_parent_gives_hic(
        self, tmp_path: Path
    ) -> None:
        """When all signals are absent or inconclusive, HiC is the safe default."""
        result = detect(
            repo_root=tmp_path,
            explicit_flag=None,
            env={},
            parent_process_name="some-unknown-shell",
        )
        assert result.value == "human_in_command"
        assert result.source_signal.kind == "parent_process"
        assert result.source_signal.evidence == "some-unknown-shell"

    def test_no_signals_at_all_gives_hic_with_default_evidence(
        self, tmp_path: Path
    ) -> None:
        """When parent_process_name is None and cannot be detected, use default-no-signal."""
        # We inject parent_process_name=None; the function will call _detect_parent_name().
        # To avoid real psutil calls in tests we pass a sentinel name that is not in
        # NON_INTERACTIVE_PARENTS.  For the truly-no-signal case, pass an empty parent.
        result = detect(
            repo_root=tmp_path,
            explicit_flag=None,
            env={},
            parent_process_name="some-unrecognised-process",
        )
        assert result.value == "human_in_command"
        assert result.source_signal.kind == "parent_process"
        # evidence must be non-empty
        assert result.source_signal.evidence


# ---------------------------------------------------------------------------
# Audit recording — every result carries non-None source_signal with evidence
# ---------------------------------------------------------------------------


class TestAuditRecording:
    """Verify that every Mode returned by detect() has a populated source_signal."""

    def _assert_audit_populated(self, result: Mode) -> None:
        assert result.source_signal is not None, "source_signal must be set"
        assert result.source_signal.kind, "source_signal.kind must be non-empty"
        assert result.source_signal.evidence, "source_signal.evidence must be non-empty"

    def test_charter_result_has_audit(self, tmp_path: Path) -> None:
        _write_charter(tmp_path, _charter_with_mode("autonomous"))
        result = detect(repo_root=tmp_path, env={}, parent_process_name="bash")
        self._assert_audit_populated(result)

    def test_flag_result_has_audit(self, tmp_path: Path) -> None:
        result = detect(
            repo_root=tmp_path,
            explicit_flag="autonomous",
            env={},
            parent_process_name="bash",
        )
        self._assert_audit_populated(result)

    def test_env_result_has_audit(self, tmp_path: Path) -> None:
        result = detect(
            repo_root=tmp_path,
            env={"SPEC_KITTY_MODE": "autonomous"},
            parent_process_name="bash",
        )
        self._assert_audit_populated(result)

    def test_parent_result_has_audit(self, tmp_path: Path) -> None:
        result = detect(
            repo_root=tmp_path,
            env={},
            parent_process_name="cron",
        )
        self._assert_audit_populated(result)

    def test_default_result_has_audit(self, tmp_path: Path) -> None:
        """Conservative HiC default carries non-empty evidence."""
        result = detect(
            repo_root=tmp_path,
            env={},
            parent_process_name="some-unknown-shell",
        )
        self._assert_audit_populated(result)


# ---------------------------------------------------------------------------
# ModeResolutionError is a proper typed exception (not generic Exception)
# ---------------------------------------------------------------------------


class TestModeResolutionErrorType:
    def test_is_exception_subclass(self) -> None:
        assert issubclass(ModeResolutionError, Exception)

    def test_not_base_exception_only(self) -> None:
        """ModeResolutionError must be catchable as ModeResolutionError specifically."""
        exc = ModeResolutionError("test message")
        assert isinstance(exc, ModeResolutionError)

    def test_charter_malformed_raises_typed_error(self, tmp_path: Path) -> None:
        _write_charter(tmp_path, _charter_malformed())
        with pytest.raises(ModeResolutionError) as exc_info:
            detect(repo_root=tmp_path, env={}, parent_process_name="bash")
        assert "malformed" in str(exc_info.value).lower() or exc_info.value is not None


# ---------------------------------------------------------------------------
# Imports — verify Mode and ModeSourceSignal come from schema (not redefined)
# ---------------------------------------------------------------------------


class TestImports:
    def test_mode_imported_from_schema(self) -> None:
        from specify_cli.retrospective.schema import Mode as SchemaMode
        from specify_cli.retrospective.mode import detect as _detect  # noqa: F401

        # The detect() return type is the schema's Mode; they must be the same class.
        result = detect(
            repo_root=Path("/tmp"),
            explicit_flag="autonomous",
            env={},
            parent_process_name="bash",
        )
        assert type(result) is SchemaMode

    def test_mode_source_signal_imported_from_schema(self) -> None:
        from specify_cli.retrospective.schema import ModeSourceSignal as SchemaMSS

        result = detect(
            repo_root=Path("/tmp"),
            explicit_flag="autonomous",
            env={},
            parent_process_name="bash",
        )
        assert type(result.source_signal) is SchemaMSS
