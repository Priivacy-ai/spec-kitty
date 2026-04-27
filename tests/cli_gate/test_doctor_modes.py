"""Mode-aware safety predicate tests for the ``doctor`` command (WP10 / T041).

Doctor flag inventory (2026-04-27)
------------------------------------
Subcommand flags:
  - ``command-files --json``        : SAFE  (read-only output)
  - ``state-roots --json``          : SAFE  (read-only output)
  - ``identity --json``             : SAFE  (read-only output)
  - ``identity --mission``          : SAFE  (scoping, no disk mutation)
  - ``identity --fail-on``          : SAFE  (exit-code control, no disk mutation)
  - ``shim-registry --json``        : SAFE  (read-only output)
  - ``sparse-checkout``             : SAFE  (detection-only mode)
  - ``sparse-checkout --fix``       : UNSAFE (applies git remediation to disk)

``--fix`` is the only real mutating flag today.  The test suite also uses
``monkeypatch`` to inject a synthetic flag (``--synthetic-apply``) as a
forward-looking demonstration for future maintainers.

Test layers
-----------
1. Direct predicate tests — call ``_doctor_predicate`` with fabricated
   ``SimpleNamespace`` invocations (fast, no I/O).
2. ``classify()`` integration tests — ensure the predicate is wired into the
   registry and the public API returns the expected Safety value.
3. Gate integration tests — call ``check_schema_version`` against a
   ``fixture_project_too_new`` project to confirm that SAFE invocations pass
   through and UNSAFE invocations raise ``SystemExit(5)``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import specify_cli.compat.safety_modes as safety_modes
from specify_cli.compat.safety import Safety, classify
from specify_cli.compat.safety_modes import (
    _DOCTOR_UNSAFE_FLAGS,
    _doctor_predicate,
    register_mode_predicates,
)
from specify_cli.migration.gate import check_schema_version


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inv(
    command_path: tuple[str, ...] = ("doctor",),
    raw_args: tuple[str, ...] = (),
) -> SimpleNamespace:
    """Build a minimal invocation namespace."""
    return SimpleNamespace(command_path=command_path, raw_args=raw_args)


# ---------------------------------------------------------------------------
# T041-A: Direct predicate tests
# ---------------------------------------------------------------------------


class TestDoctorPredicateDirect:
    """Unit tests that call _doctor_predicate directly."""

    def test_no_flags_is_safe(self) -> None:
        """Bare ``doctor`` (no flags) must be SAFE."""
        assert _doctor_predicate(_inv()) == Safety.SAFE

    @pytest.mark.parametrize("flag", sorted(_DOCTOR_UNSAFE_FLAGS))
    def test_real_unsafe_flag_is_unsafe(self, flag: str) -> None:
        """Each real unsafe flag must yield UNSAFE when present in raw_args."""
        assert _doctor_predicate(_inv(raw_args=(flag,))) == Safety.UNSAFE

    def test_safe_flag_json_is_safe(self) -> None:
        """``--json`` is a safe flag and must not trigger UNSAFE."""
        assert _doctor_predicate(_inv(raw_args=("--json",))) == Safety.SAFE

    def test_safe_flag_mission_is_safe(self) -> None:
        """``--mission`` is a safe flag and must not trigger UNSAFE."""
        assert _doctor_predicate(_inv(raw_args=("--mission", "083-foo"))) == Safety.SAFE

    def test_safe_flag_fail_on_is_safe(self) -> None:
        """``--fail-on`` is a safe flag and must not trigger UNSAFE."""
        assert _doctor_predicate(_inv(raw_args=("--fail-on", "legacy,orphan"))) == Safety.SAFE

    def test_monkeypatched_synthetic_flag_is_unsafe(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Future mutating flags can be added by extending _DOCTOR_UNSAFE_FLAGS.

        This forward-looking test uses monkeypatch to verify the mechanism works
        without modifying the production frozenset.
        """
        monkeypatch.setattr(
            safety_modes,
            "_DOCTOR_UNSAFE_FLAGS",
            frozenset({"--synthetic-apply"}),
        )
        result = safety_modes._doctor_predicate(_inv(raw_args=("--synthetic-apply",)))
        assert result == Safety.UNSAFE

    def test_synthetic_flag_without_patch_is_safe(self) -> None:
        """A flag not in _DOCTOR_UNSAFE_FLAGS must return SAFE."""
        result = _doctor_predicate(_inv(raw_args=("--synthetic-apply",)))
        assert result == Safety.SAFE

    def test_fix_in_subcommand_args_is_unsafe(self) -> None:
        """``--fix`` anywhere in raw_args (e.g. sparse-checkout --fix) is UNSAFE."""
        result = _doctor_predicate(
            _inv(raw_args=("sparse-checkout", "--fix"))
        )
        assert result == Safety.UNSAFE


# ---------------------------------------------------------------------------
# T041-B: classify() integration tests
# ---------------------------------------------------------------------------


class TestDoctorClassifyIntegration:
    """Tests that verify the predicate is wired into the SAFETY_REGISTRY."""

    def setup_method(self) -> None:
        """Ensure predicates are registered before each test."""
        register_mode_predicates()

    def test_classify_no_flags_is_safe(self) -> None:
        """classify() on a bare doctor invocation must return SAFE."""
        assert classify(_inv()) == Safety.SAFE

    @pytest.mark.parametrize("flag", sorted(_DOCTOR_UNSAFE_FLAGS))
    def test_classify_unsafe_flag_is_unsafe(self, flag: str) -> None:
        """classify() must return UNSAFE when a mutating flag is present."""
        assert classify(_inv(raw_args=(flag,))) == Safety.UNSAFE

    def test_classify_read_only_flags_are_safe(self) -> None:
        """classify() returns SAFE for known read-only flags."""
        assert classify(_inv(raw_args=("--json",))) == Safety.SAFE
        assert classify(_inv(raw_args=("--mission", "my-feature"))) == Safety.SAFE
        assert classify(_inv(raw_args=("--fail-on", "legacy"))) == Safety.SAFE

    def test_classify_subcommand_with_fix_is_unsafe(self) -> None:
        """classify() returns UNSAFE for doctor sparse-checkout --fix."""
        assert classify(_inv(raw_args=("sparse-checkout", "--fix"))) == Safety.UNSAFE

    def test_idempotent_registration(self) -> None:
        """Calling register_mode_predicates() twice must not duplicate entries."""
        register_mode_predicates()
        register_mode_predicates()
        # After multiple registrations, classify() still works correctly.
        assert classify(_inv()) == Safety.SAFE
        assert classify(_inv(raw_args=("--fix",))) == Safety.UNSAFE


# ---------------------------------------------------------------------------
# T041-C: Gate integration tests (uses fixture_project_too_new)
# ---------------------------------------------------------------------------


class TestDoctorGateIntegration:
    """End-to-end gate tests using check_schema_version."""

    def test_safe_invocation_not_blocked(self, fixture_project_too_new: Path) -> None:
        """A bare ``doctor`` (no flags) must not be blocked on a too-new project."""
        check_schema_version(fixture_project_too_new, invoked_subcommand="doctor")

    def test_unsafe_fix_flag_is_blocked(
        self,
        fixture_project_too_new: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``doctor sparse-checkout --fix`` must be blocked (exit 5) on a too-new project.

        We inject ``--fix`` into sys.argv so the Invocation.raw_args carries it.
        """
        import sys  # noqa: PLC0415

        monkeypatch.setattr(
            sys, "argv", ["spec-kitty", "doctor", "sparse-checkout", "--fix"]
        )
        with pytest.raises(SystemExit) as exc_info:
            check_schema_version(fixture_project_too_new, invoked_subcommand="doctor")
        assert exc_info.value.code == 5, (
            f"Expected exit 5 (BLOCK_CLI_UPGRADE), got {exc_info.value.code!r}"
        )

    def test_safe_doctor_json_not_blocked(
        self,
        fixture_project_too_new: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``doctor --json`` must not be blocked on a too-new project."""
        import sys  # noqa: PLC0415

        monkeypatch.setattr(sys, "argv", ["spec-kitty", "doctor", "--json"])
        check_schema_version(fixture_project_too_new, invoked_subcommand="doctor")
