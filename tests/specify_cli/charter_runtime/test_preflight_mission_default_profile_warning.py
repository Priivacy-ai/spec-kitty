"""#4115: ``charter preflight`` advisory warnings for deactivated
mission-step default profiles.

A project that deactivated a shipped agent profile named in
``_ACTION_PROFILE_DEFAULTS`` still reports FRESH on every freshness layer —
deactivation is legitimate state, not staleness — while its built-in
missions are one dispatch away from a role fallback (or a blocked step when
no same-role profile is activated). The preflight runner therefore appends
one ADVISORY warning per deactivated default profile to
``CharterPreflightResult.warnings`` (never affecting ``passed``), computed
from the three-state ``activated_agent_profiles`` set.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.charter_runtime.preflight import run_charter_preflight
from specify_cli.charter_runtime.preflight import runner as runner_module

pytestmark = pytest.mark.fast


def _write_config(tmp_path: Path, config: str) -> Path:
    kittify = tmp_path / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(config, encoding="utf-8")
    return tmp_path


def test_deactivated_default_profiles_surface_as_advisory_warnings(
    tmp_path: Path,
) -> None:
    """An explicit ``activated_agent_profiles`` set that omits a table
    default yields one warning per omitted default — naming the profile, a
    bound step, and the fallback role — without changing ``passed``."""
    repo_root = _write_config(
        tmp_path,
        "activated_agent_profiles:\n  - my-implementer\nmission_type_activations:\n  - software-dev\n",
    )

    result = run_charter_preflight(repo_root)

    profile_warnings = [warning for warning in result.warnings if "built-in default profile" in warning]
    # All four table defaults are omitted (my-implementer is a different id
    # from implementer-ivan) — one warning per deactivated default.
    assert len(profile_warnings) == 4
    assert any("researcher-robbie" in w and "software-dev/specify" in w for w in profile_warnings)
    assert any("architect-alphonso" in w and "software-dev/plan" in w for w in profile_warnings)
    assert any("implementer-ivan" in w and "software-dev/implement" in w for w in profile_warnings)
    assert any("reviewer-renata" in w and "software-dev/review" in w for w in profile_warnings)
    # Advisory only: the warnings never flip the freshness verdict.
    assert result.passed is True or result.blocked_reason is not None


def test_inert_activation_state_yields_no_profile_warnings(tmp_path: Path) -> None:
    """``activated_agent_profiles`` absent (default-allow) is inert — every
    table default is available, so no warning fires."""
    repo_root = _write_config(
        tmp_path,
        "activated_directives:\n  - some-directive\nmission_type_activations:\n  - software-dev\n",
    )

    result = run_charter_preflight(repo_root)

    assert not [w for w in result.warnings if "built-in default profile" in w]


def test_fully_activated_defaults_yield_no_profile_warnings(tmp_path: Path) -> None:
    """An explicit set that CONTAINS every table default is also quiet: the
    warnings fire on deactivation, not on the mere presence of a set."""
    repo_root = _write_config(
        tmp_path,
        "activated_agent_profiles:\n"
        "  - researcher-robbie\n"
        "  - architect-alphonso\n"
        "  - implementer-ivan\n"
        "  - reviewer-renata\n"
        "  - my-implementer\n"
        "mission_type_activations:\n  - software-dev\n",
    )

    result = run_charter_preflight(repo_root)

    assert not [w for w in result.warnings if "built-in default profile" in w]


def test_unreadable_activation_state_never_raises(tmp_path: Path) -> None:
    """The runner's never-raise contract: a config read that blows up
    produces no profile warnings and no exception — the freshness layers
    own fail-closed treatment of a malformed config."""
    repo_root = _write_config(tmp_path, "mission_type_activations:\n  - software-dev\n")

    with patch(
        "charter.activation.pack_context.PackContext.from_config",
        side_effect=RuntimeError("boom"),
    ):
        result = run_charter_preflight(repo_root)

    assert not [w for w in result.warnings if "built-in default profile" in w]
    # The freshness core still ran and produced its normal result shape.
    assert result.checks


def test_warnings_append_to_existing_result_warnings(tmp_path: Path) -> None:
    """The wrapper is additive: a result that already carries warnings (the
    advisory missing-charter path) keeps them and appends the profile ones."""
    from specify_cli.charter_runtime.preflight.result import CharterPreflightResult

    repo_root = _write_config(
        tmp_path,
        "activated_agent_profiles:\n  - my-implementer\nmission_type_activations:\n  - software-dev\n",
    )

    # Drive additivity through the real seam: seed the freshness core with a
    # result that already carries one warning, then run the public wrapper.
    real_core = runner_module._run_charter_preflight_freshness(repo_root, auto_refresh=False, allow_missing_charter=False, strict=False)
    seeded = CharterPreflightResult(
        passed=real_core.passed,
        checks=real_core.checks,
        auto_refresh_applied=real_core.auto_refresh_applied,
        auto_refresh_actions=real_core.auto_refresh_actions,
        blocked_reason=real_core.blocked_reason,
        warnings=["pre-existing warning"],
    )
    with patch.object(runner_module, "_run_charter_preflight_freshness", return_value=seeded):
        result = run_charter_preflight(repo_root)

    assert result.warnings[0] == "pre-existing warning"
    assert any("built-in default profile" in w for w in result.warnings[1:])
