"""Mode-aware safety predicate tests for the ``dashboard`` command (WP10 / T041).

Dashboard flag inventory (2026-04-27)
--------------------------------------
- ``--port``  : SAFE  (selects server port, no disk mutation)
- ``--open``  : SAFE  (opens browser, no disk mutation)
- ``--json``  : SAFE  (read-only output, no disk mutation)
- ``--kill``  : UNSAFE (stops dashboard server AND clears metadata on disk)

Because ``--kill`` is the only real mutating flag today, the test suite uses
``monkeypatch`` to inject a synthetic flag (``--synthetic-write``) alongside
the real ``--kill`` flag, demonstrating how future maintainers add new unsafe
flags without touching the predicate logic.

Test layers
-----------
1. Direct predicate tests — call ``_dashboard_predicate`` with fabricated
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
    _DASHBOARD_UNSAFE_FLAGS,
    _dashboard_predicate,
    register_mode_predicates,
)
from specify_cli.migration.gate import check_schema_version


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inv(
    command_path: tuple[str, ...] = ("dashboard",),
    raw_args: tuple[str, ...] = (),
) -> SimpleNamespace:
    """Build a minimal invocation namespace."""
    return SimpleNamespace(command_path=command_path, raw_args=raw_args)


# ---------------------------------------------------------------------------
# T041-A: Direct predicate tests
# ---------------------------------------------------------------------------


class TestDashboardPredicateDirect:
    """Unit tests that call _dashboard_predicate directly."""

    def test_no_flags_is_safe(self) -> None:
        """Bare ``dashboard`` (no flags) must be SAFE."""
        assert _dashboard_predicate(_inv()) == Safety.SAFE

    @pytest.mark.parametrize("flag", sorted(_DASHBOARD_UNSAFE_FLAGS))
    def test_real_unsafe_flag_is_unsafe(self, flag: str) -> None:
        """Each real unsafe flag must yield UNSAFE when present in raw_args."""
        assert _dashboard_predicate(_inv(raw_args=(flag,))) == Safety.UNSAFE

    def test_safe_flag_port_is_safe(self) -> None:
        """``--port`` is a safe flag and must not trigger UNSAFE."""
        assert _dashboard_predicate(_inv(raw_args=("--port", "9238"))) == Safety.SAFE

    def test_safe_flag_open_is_safe(self) -> None:
        """``--open`` is a safe flag and must not trigger UNSAFE."""
        assert _dashboard_predicate(_inv(raw_args=("--open",))) == Safety.SAFE

    def test_safe_flag_json_is_safe(self) -> None:
        """``--json`` is a safe flag and must not trigger UNSAFE."""
        assert _dashboard_predicate(_inv(raw_args=("--json",))) == Safety.SAFE

    def test_monkeypatched_synthetic_flag_is_unsafe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Future mutating flags can be added by extending _DASHBOARD_UNSAFE_FLAGS.

        This forward-looking test uses monkeypatch to verify the mechanism works
        without modifying the production frozenset.
        """
        monkeypatch.setattr(
            safety_modes,
            "_DASHBOARD_UNSAFE_FLAGS",
            frozenset({"--synthetic-write"}),
        )
        # Also patch inside the predicate's closure reference
        monkeypatch.setattr(
            "specify_cli.compat.safety_modes._DASHBOARD_UNSAFE_FLAGS",
            frozenset({"--synthetic-write"}),
        )
        # Call through the module-level name since the predicate reads the
        # module global (_DASHBOARD_UNSAFE_FLAGS) at call time.
        result = safety_modes._dashboard_predicate(_inv(raw_args=("--synthetic-write",)))
        assert result == Safety.UNSAFE

    def test_synthetic_flag_without_patch_is_safe(self) -> None:
        """A flag not in _DASHBOARD_UNSAFE_FLAGS must return SAFE."""
        result = _dashboard_predicate(_inv(raw_args=("--synthetic-write",)))
        assert result == Safety.SAFE


# ---------------------------------------------------------------------------
# T041-B: classify() integration tests
# ---------------------------------------------------------------------------


class TestDashboardClassifyIntegration:
    """Tests that verify the predicate is wired into the SAFETY_REGISTRY."""

    def setup_method(self) -> None:
        """Ensure predicates are registered before each test."""
        register_mode_predicates()

    def test_classify_no_flags_is_safe(self) -> None:
        """classify() on a bare dashboard invocation must return SAFE."""
        assert classify(_inv()) == Safety.SAFE

    @pytest.mark.parametrize("flag", sorted(_DASHBOARD_UNSAFE_FLAGS))
    def test_classify_unsafe_flag_is_unsafe(self, flag: str) -> None:
        """classify() must return UNSAFE when a mutating flag is present."""
        assert classify(_inv(raw_args=(flag,))) == Safety.UNSAFE

    def test_classify_safe_flags_is_safe(self) -> None:
        """classify() returns SAFE for known read-only flags."""
        assert classify(_inv(raw_args=("--port", "8080", "--open", "--json"))) == Safety.SAFE

    def test_idempotent_registration(self) -> None:
        """Calling register_mode_predicates() twice must not duplicate entries."""
        register_mode_predicates()
        register_mode_predicates()
        # After multiple registrations, classify() still works correctly.
        assert classify(_inv()) == Safety.SAFE
        assert classify(_inv(raw_args=("--kill",))) == Safety.UNSAFE


# ---------------------------------------------------------------------------
# T041-C: Gate integration tests (uses fixture_project_too_new)
# ---------------------------------------------------------------------------


class TestDashboardGateIntegration:
    """End-to-end gate tests using check_schema_version."""

    def test_safe_invocation_not_blocked(self, fixture_project_too_new: Path) -> None:
        """A bare ``dashboard`` (no flags) must not be blocked on a too-new project."""
        # Provide raw_args via sys.argv simulation — gate passes raw_args from sys.argv.
        # check_schema_version only takes invoked_subcommand, so SAFE/UNSAFE is
        # determined by classify(Invocation(command_path=("dashboard",), raw_args=sys.argv[1:])).
        # With no mutating flags in sys.argv, this should pass cleanly.
        check_schema_version(fixture_project_too_new, invoked_subcommand="dashboard")

    def test_unsafe_kill_flag_is_blocked(
        self,
        fixture_project_too_new: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``dashboard --kill`` must be blocked (exit 5) on a too-new project.

        We inject ``--kill`` into sys.argv so the Invocation.raw_args carries it.
        """
        import sys  # noqa: PLC0415

        monkeypatch.setattr(sys, "argv", ["spec-kitty", "dashboard", "--kill"])
        with pytest.raises(SystemExit) as exc_info:
            check_schema_version(fixture_project_too_new, invoked_subcommand="dashboard")
        assert exc_info.value.code == 5, f"Expected exit 5 (BLOCK_CLI_UPGRADE), got {exc_info.value.code!r}"
