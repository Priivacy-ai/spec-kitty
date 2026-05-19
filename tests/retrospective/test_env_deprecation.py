"""Dedicated test module for env-var deprecation behavior.

This is the ONLY test module in the suite that is permitted to set or mutate
the ``SPEC_KITTY_RETROSPECTIVE`` or ``SPEC_KITTY_MODE`` environment variables
via ``monkeypatch.setenv`` or ``os.environ`` mutations (FR-016 enforcement).

Tests here cover:
- One-warning-per-process budget (NFR-006)
- Durable config/charter wins over env var (FR-015)
- ``SPEC_KITTY_NO_DEPRECATION_WARNINGS=1`` suppresses Rich stderr but NOT Python
  ``DeprecationWarning`` (T031)
- Source-map records ``<env:...>`` attribution when env is the only opinion (T005/WP01)

Process-global state note
--------------------------
``_EMITTED`` in ``deprecation.py`` is a module-level set.  The ``reset_emitted``
fixture (autouse) calls ``reset_emitted_for_testing()`` before and after every
test to prevent cross-test contamination.  All tests in this module MUST keep
the ``reset_emitted`` fixture in scope.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.retrospective.deprecation import (
    _DOCS_URL,
    REPLACEMENT_KEYS,
    reset_emitted_for_testing,
    warn_env_var_deprecated,
)
from specify_cli.retrospective.policy import resolve_policy

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Autouse fixture: reset _EMITTED between every test in this module
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_emitted() -> Iterator[None]:
    """Reset the module-level _EMITTED set before and after each test.

    This fixture is autouse so every test in this module gets a clean slate.
    Tests outside this module should NOT interact with _EMITTED.
    """
    reset_emitted_for_testing()
    yield
    reset_emitted_for_testing()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(repo_root: Path, content: str) -> None:
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yaml").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# TestOneWarningPerProcess
# ---------------------------------------------------------------------------


class TestOneWarningPerProcess:
    """NFR-006: exactly one DeprecationWarning per var name per process."""

    def test_warn_emitted_once_per_var(self) -> None:
        """Calling warn_env_var_deprecated twice emits exactly one warning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warn_env_var_deprecated(
                "SPEC_KITTY_RETROSPECTIVE",
                REPLACEMENT_KEYS["SPEC_KITTY_RETROSPECTIVE"],
                _DOCS_URL,
            )
            warn_env_var_deprecated(
                "SPEC_KITTY_RETROSPECTIVE",
                REPLACEMENT_KEYS["SPEC_KITTY_RETROSPECTIVE"],
                _DOCS_URL,
            )

        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 1

    def test_resolve_policy_called_twice_warns_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """resolve_policy() called twice with env var set → one DeprecationWarning."""
        monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", "1")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            resolve_policy(tmp_path)
            resolve_policy(tmp_path)

        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
            and "SPEC_KITTY_RETROSPECTIVE" in str(w.message)
        ]
        assert len(deprecation_warnings) == 1

    def test_two_different_vars_each_warn_once(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Each distinct env var name gets its own one-shot budget."""
        monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", "1")
        monkeypatch.setenv("SPEC_KITTY_MODE", "autonomous")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            resolve_policy(tmp_path)
            resolve_policy(tmp_path)

        retro_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
            and "SPEC_KITTY_RETROSPECTIVE" in str(w.message)
        ]
        mode_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
            and "SPEC_KITTY_MODE" in str(w.message)
        ]
        assert len(retro_warnings) == 1
        assert len(mode_warnings) == 1

    def test_warning_message_contains_replacement_key(self) -> None:
        """The DeprecationWarning message mentions the canonical replacement key."""
        with pytest.warns(DeprecationWarning, match="retrospective.enabled"):
            warn_env_var_deprecated(
                "SPEC_KITTY_RETROSPECTIVE",
                REPLACEMENT_KEYS["SPEC_KITTY_RETROSPECTIVE"],
                _DOCS_URL,
            )

    def test_warning_message_contains_docs_url(self) -> None:
        """The DeprecationWarning message includes the docs URL."""
        with pytest.warns(DeprecationWarning, match="use-retrospective-learning"):
            warn_env_var_deprecated(
                "SPEC_KITTY_RETROSPECTIVE",
                REPLACEMENT_KEYS["SPEC_KITTY_RETROSPECTIVE"],
                _DOCS_URL,
            )


# ---------------------------------------------------------------------------
# TestDurableConfigWinsOverEnvVar
# ---------------------------------------------------------------------------


class TestDurableConfigWinsOverEnvVar:
    """FR-015: durable config/charter wins; env var is observed but never overrides."""

    def test_config_enabled_false_wins_over_env_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config ``retrospective.enabled: false`` wins even when env var says 1."""
        _write_config(tmp_path, "retrospective:\n  enabled: false\n")
        monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", "1")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            policy, source_map = resolve_policy(tmp_path)

        # Policy respects config (enabled=False)
        assert policy.enabled is False

        # Warning still fires — env var is set regardless of whether it wins
        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
            and "SPEC_KITTY_RETROSPECTIVE" in str(w.message)
        ]
        assert len(deprecation_warnings) == 1

    def test_charter_enabled_false_wins_over_env_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Charter ``retrospective.enabled: false`` wins over env var."""
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True, exist_ok=True)
        (charter_dir / "charter.md").write_text(
            "---\nretrospective:\n  enabled: false\n---\n# Charter\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", "1")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            policy, source_map = resolve_policy(tmp_path)

        assert policy.enabled is False

        # Warning fires (env var is set)
        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
            and "SPEC_KITTY_RETROSPECTIVE" in str(w.message)
        ]
        assert len(deprecation_warnings) == 1

    def test_no_durable_config_env_var_observed_in_source_map(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When only env is set, source_map records the env observation."""
        monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", "1")

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            policy, source_map = resolve_policy(tmp_path)

        # Source map should record env observation
        assert source_map["enabled"] == "<env:SPEC_KITTY_RETROSPECTIVE>"
        # Policy remains at default (env var is observed, not applied)
        assert policy.enabled is True  # built-in default is True

    def test_config_wins_source_map_does_not_record_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When config sets the field, source_map points to config, not env."""
        _write_config(tmp_path, "retrospective:\n  enabled: false\n")
        monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", "1")

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            policy, source_map = resolve_policy(tmp_path)

        # Source map should show config, not env
        assert "<env:" not in source_map["enabled"]
        assert ".kittify/config.yaml" in source_map["enabled"]


# ---------------------------------------------------------------------------
# TestRichStderrSuppression
# ---------------------------------------------------------------------------


class TestRichStderrSuppression:
    """T031: SPEC_KITTY_NO_DEPRECATION_WARNINGS=1 suppresses Rich stderr but NOT DeprecationWarning."""

    def test_deprecation_warning_still_fires_when_suppressed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Python DeprecationWarning is NOT suppressed by SPEC_KITTY_NO_DEPRECATION_WARNINGS."""
        monkeypatch.setenv("SPEC_KITTY_NO_DEPRECATION_WARNINGS", "1")

        with pytest.warns(DeprecationWarning, match="SPEC_KITTY_RETROSPECTIVE"):
            warn_env_var_deprecated(
                "SPEC_KITTY_RETROSPECTIVE",
                REPLACEMENT_KEYS["SPEC_KITTY_RETROSPECTIVE"],
                _DOCS_URL,
            )

    def test_rich_stderr_suppressed_when_flag_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rich Console print is skipped when SPEC_KITTY_NO_DEPRECATION_WARNINGS=1."""
        monkeypatch.setenv("SPEC_KITTY_NO_DEPRECATION_WARNINGS", "1")

        # Patch Console to detect if print is called
        from rich.console import Console as _RichConsole

        original_init = _RichConsole.__init__
        captured_console: list[_RichConsole] = []

        def patched_init(self: _RichConsole, **kwargs: object) -> None:
            original_init(self, **kwargs)  # type: ignore[arg-type]
            captured_console.append(self)

        with (
            warnings.catch_warnings(record=True),
            patch("rich.console.Console.__init__", patched_init),
        ):
            warnings.simplefilter("always")
            warn_env_var_deprecated(
                "SPEC_KITTY_RETROSPECTIVE",
                REPLACEMENT_KEYS["SPEC_KITTY_RETROSPECTIVE"],
                _DOCS_URL,
            )

        # Console should never have been instantiated (early return before Console call)
        assert len(captured_console) == 0

    def test_rich_stderr_fires_when_flag_not_set(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Without suppression flag, the Rich notice fires and produces stderr output."""
        # Ensure suppression flag is absent
        monkeypatch.delenv("SPEC_KITTY_NO_DEPRECATION_WARNINGS", raising=False)

        # Redirect Rich's Console(stderr=True) output; capsys captures sys.stderr
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            warn_env_var_deprecated(
                "SPEC_KITTY_RETROSPECTIVE",
                REPLACEMENT_KEYS["SPEC_KITTY_RETROSPECTIVE"],
                _DOCS_URL,
            )

        # Rich Console writes to stderr; capsys should capture it
        captured = capsys.readouterr()
        assert "DEPRECATED" in captured.err or "SPEC_KITTY_RETROSPECTIVE" in captured.err

    def test_suppress_env_var_for_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SPEC_KITTY_NO_DEPRECATION_WARNINGS suppression works for SPEC_KITTY_MODE too."""
        monkeypatch.setenv("SPEC_KITTY_NO_DEPRECATION_WARNINGS", "1")

        with pytest.warns(DeprecationWarning, match="SPEC_KITTY_MODE"):
            warn_env_var_deprecated(
                "SPEC_KITTY_MODE",
                REPLACEMENT_KEYS["SPEC_KITTY_MODE"],
                _DOCS_URL,
            )


# ---------------------------------------------------------------------------
# TestEnvVarObservationInSourceMap
# ---------------------------------------------------------------------------


class TestEnvVarObservationInSourceMap:
    """T005/WP01: source_map records <env:...> when env is the only opinion."""

    def test_retro_env_recorded_in_source_map(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SPEC_KITTY_RETROSPECTIVE set → source_map['enabled'] = '<env:...>'."""
        monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", "1")

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            policy, source_map = resolve_policy(tmp_path)

        assert source_map["enabled"] == "<env:SPEC_KITTY_RETROSPECTIVE>"

    def test_mode_env_recorded_in_source_map(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SPEC_KITTY_MODE set → source_map records env for timing and failure_policy."""
        monkeypatch.setenv("SPEC_KITTY_MODE", "autonomous")

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            policy, source_map = resolve_policy(tmp_path)

        assert source_map["timing"] == "<env:SPEC_KITTY_MODE>"
        assert source_map["failure_policy"] == "<env:SPEC_KITTY_MODE>"

    def test_no_env_vars_no_env_observation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without env vars set, source_map has no <env:...> entries."""
        monkeypatch.delenv("SPEC_KITTY_RETROSPECTIVE", raising=False)
        monkeypatch.delenv("SPEC_KITTY_MODE", raising=False)

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            policy, source_map = resolve_policy(tmp_path)

        env_entries = {k: v for k, v in source_map.items() if "<env:" in v}
        assert env_entries == {}

    def test_env_observation_does_not_change_resolved_policy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Env vars are observed (source_map) but do not override built-in defaults."""
        monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", "1")
        monkeypatch.setenv("SPEC_KITTY_MODE", "autonomous")

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            policy, source_map = resolve_policy(tmp_path)

        # Policy should be at built-in defaults (env vars observed but never applied)
        assert policy.enabled is True  # built-in default
        assert policy.timing == "post_completion"  # built-in default
        assert policy.failure_policy == "warn"  # built-in default

    def test_deprecation_warning_emitted_when_env_observed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Source map recording and deprecation warning fire together."""
        monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", "1")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _, source_map = resolve_policy(tmp_path)

        assert source_map["enabled"] == "<env:SPEC_KITTY_RETROSPECTIVE>"
        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
            and "SPEC_KITTY_RETROSPECTIVE" in str(w.message)
        ]
        assert len(deprecation_warnings) == 1
