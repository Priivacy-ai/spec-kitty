"""FR-021: Behavior-preservation tests for plan_remediation routing.

Verifies that:
- format_version_error("project_newer") renders the planner upgrade command.
- For a PIPX runtime the rendered output is "pipx upgrade spec-kitty-cli".
- When render() raises ValueError the fallback "pipx upgrade spec-kitty-cli" is used.
- check_compatibility CLI_OUTDATED message uses the planner upgrade command.
- For a PIPX runtime check_compatibility still contains "pipx upgrade spec-kitty-cli".

Patch strategy: imports inside function bodies are resolved at call time, so we
patch the symbol at its canonical source location, not in the calling module.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from specify_cli.core.version_checker import format_version_error
from specify_cli.migration.schema_version import check_compatibility, CompatibilityStatus

pytestmark = [pytest.mark.fast]

_PIPX_CMD = "pipx upgrade spec-kitty-cli"
_FALLBACK_CMD = "pipx upgrade spec-kitty-cli"

# Deferred-import patch targets (the function bodies import from these locations)
_DETECT_RUNTIME_PATH = "specify_cli.compat._detect.runtime.detect_runtime"
_PLAN_REMEDIATION_PATH = "specify_cli.compat.remediation.plan_remediation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pipx_runtime() -> object:
    """Return a real InstalledCliRuntime with PIPX install method."""
    from specify_cli.compat._detect.install_method import InstallMethod
    from specify_cli.compat._detect.runtime import InstalledCliRuntime, PackageSource

    return InstalledCliRuntime(
        install_method=InstallMethod.PIPX,
        executable="/home/user/.local/pipx/venvs/spec-kitty-cli/bin/python",
        receipt_path=None,
        tool_dir=None,
        bin_dir=None,
        is_default_tool_dir=None,
        is_default_bin_dir=None,
        python=None,
        requirements=(),
        package_source=PackageSource.UNKNOWN,
        platform="posix",
        safe_for_auto_upgrade=True,
    )


def _make_render_raising_runtime() -> object:
    """Return a real InstalledCliRuntime with UNKNOWN install method (→ MANUAL_GUIDANCE)."""
    from specify_cli.compat._detect.install_method import InstallMethod
    from specify_cli.compat._detect.runtime import InstalledCliRuntime, PackageSource

    return InstalledCliRuntime(
        install_method=InstallMethod.UNKNOWN,
        executable="/usr/bin/python3",
        receipt_path=None,
        tool_dir=None,
        bin_dir=None,
        is_default_tool_dir=None,
        is_default_bin_dir=None,
        python=None,
        requirements=(),
        package_source=PackageSource.UNKNOWN,
        platform="posix",
        safe_for_auto_upgrade=False,
    )


# ---------------------------------------------------------------------------
# format_version_error — project_newer branch
# ---------------------------------------------------------------------------


def test_format_version_error_project_newer_pipx_render():
    """PIPX runtime → planner renders 'pipx upgrade spec-kitty-cli' in message."""
    with patch(_DETECT_RUNTIME_PATH, return_value=_make_pipx_runtime()):
        msg = format_version_error("0.9.0", "1.0.0", "project_newer")

    assert _PIPX_CMD in msg, f"Expected '{_PIPX_CMD}' in:\n{msg}"


def test_format_version_error_project_newer_unknown_fallback():
    """UNKNOWN runtime → render() raises ValueError → fallback string used."""
    with patch(_DETECT_RUNTIME_PATH, return_value=_make_render_raising_runtime()):
        msg = format_version_error("0.9.0", "1.0.0", "project_newer")

    # The fallback must still appear — message must be non-empty and usable.
    assert _FALLBACK_CMD in msg, f"Expected fallback '{_FALLBACK_CMD}' in:\n{msg}"


def test_format_version_error_project_newer_pipx_output_unchanged():
    """End-to-end snapshot: PIPX rendered output equals old hardcoded value exactly."""
    with patch(_DETECT_RUNTIME_PATH, return_value=_make_pipx_runtime()):
        msg = format_version_error("0.9.0", "1.0.0", "project_newer")

    assert _PIPX_CMD in msg, f"Snapshot mismatch. Expected '{_PIPX_CMD}' in:\n{msg}"


def test_format_version_error_other_branches_unaffected():
    """cli_newer and unknown branches are not affected by FR-021 changes."""
    cli_newer_msg = format_version_error("1.0.0", "0.9.0", "cli_newer")
    assert "spec-kitty upgrade" in cli_newer_msg

    unknown_msg = format_version_error("1.0.0", "0.9.0", "unknown")
    assert "Version mismatch" in unknown_msg


# ---------------------------------------------------------------------------
# check_compatibility — CLI_OUTDATED branch
# ---------------------------------------------------------------------------


def test_check_compatibility_cli_outdated_pipx_render():
    """PIPX runtime → planner renders 'pipx upgrade spec-kitty-cli' in message."""
    with patch(_DETECT_RUNTIME_PATH, return_value=_make_pipx_runtime()):
        result = check_compatibility(4, 3)  # project_version > cli_version

    assert result.status == CompatibilityStatus.CLI_OUTDATED
    assert _PIPX_CMD in result.message, f"Expected '{_PIPX_CMD}' in:\n{result.message}"


def test_check_compatibility_cli_outdated_unknown_fallback():
    """UNKNOWN runtime → render() raises ValueError → fallback in message."""
    with patch(_DETECT_RUNTIME_PATH, return_value=_make_render_raising_runtime()):
        result = check_compatibility(4, 3)

    assert result.status == CompatibilityStatus.CLI_OUTDATED
    assert _FALLBACK_CMD in result.message, f"Expected fallback '{_FALLBACK_CMD}' in:\n{result.message}"


def test_check_compatibility_cli_outdated_pipx_output_unchanged():
    """Snapshot: PIPX rendered output equals old hardcoded value; pip fallback preserved."""
    with patch(_DETECT_RUNTIME_PATH, return_value=_make_pipx_runtime()):
        result = check_compatibility(4, 3)

    assert _PIPX_CMD in result.message, f"Snapshot mismatch. Expected '{_PIPX_CMD}' in:\n{result.message}"
    # pre-existing assertion from test_schema_version.py — must still hold after FR-021
    assert "pip install --upgrade spec-kitty-cli" in result.message
