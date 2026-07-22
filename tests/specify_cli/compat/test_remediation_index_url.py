"""WP04: remediation index URL argv + CHK028 length 512 (FR-013, FR-014)."""

from __future__ import annotations

import pytest

from specify_cli.compat._detect.install_method import InstallMethod
from specify_cli.compat._detect.runtime import (
    InstalledCliRuntime,
    PackageSource,
)
from specify_cli.compat.remediation import (
    COMMAND_ALLOWLIST_MAX_LEN,
    RemediationIntent,
    plan_remediation,
)

pytestmark = [pytest.mark.fast]

_INDEX = "https://example.invalid/simple/"
# Long enough that the composed command exceeds the legacy 128-char CHK028 cap.
_LONG_INDEX = "https://example.invalid/" + ("p" * 100) + "/simple/"


def _runtime(method: InstallMethod) -> InstalledCliRuntime:
    return InstalledCliRuntime(
        install_method=method,
        executable="/usr/local/bin/python3",
        receipt_path=None,
        tool_dir=None,
        bin_dir=None,
        is_default_tool_dir=True,
        is_default_bin_dir=True,
        python=None,
        requirements=(),
        package_source=PackageSource.UNKNOWN,
        platform="posix",
        safe_for_auto_upgrade=True,
    )


def test_command_allowlist_max_len_is_512() -> None:
    assert COMMAND_ALLOWLIST_MAX_LEN == 512


@pytest.mark.parametrize(
    "method",
    [
        InstallMethod.PIPX,
        InstallMethod.PIP_USER,
        InstallMethod.PIP_SYSTEM,
        InstallMethod.UV_TOOL,
    ],
)
def test_index_url_appended_before_package(method: InstallMethod) -> None:
    cmd = plan_remediation(
        _runtime(method),
        RemediationIntent.UPGRADE,
        None,
        package_name="acme-spec-kitty-cli",
        index_url=_LONG_INDEX,
    )
    assert cmd.argv is not None
    assert "--index-url" in cmd.argv
    idx = cmd.argv.index("--index-url")
    assert cmd.argv[idx + 1] == _LONG_INDEX
    assert "acme-spec-kitty-cli" in cmd.argv[-1]
    rendered = cmd.render("posix")
    assert _LONG_INDEX in rendered
    assert len(rendered) > 128
    assert len(rendered) <= COMMAND_ALLOWLIST_MAX_LEN


def test_extra_index_url_flag() -> None:
    cmd = plan_remediation(
        _runtime(InstallMethod.PIP_SYSTEM),
        RemediationIntent.UPGRADE,
        None,
        package_name="acme-cli",
        index_url=_INDEX,
        extra_index_url="https://extra.example.invalid/simple/",
    )
    assert cmd.argv is not None
    assert "--extra-index-url" in cmd.argv
    rendered = cmd.render("posix")
    assert len(rendered) <= COMMAND_ALLOWLIST_MAX_LEN


def test_brew_ignores_index_url() -> None:
    cmd = plan_remediation(
        _runtime(InstallMethod.BREW),
        RemediationIntent.UPGRADE,
        None,
        package_name="acme-cli",
        index_url=_INDEX,
    )
    assert cmd.argv == ("brew", "upgrade", "acme-cli")


def test_chk028_rejects_over_512() -> None:
    long_url = "https://example.invalid/" + ("a" * 480)
    cmd = plan_remediation(
        _runtime(InstallMethod.PIP_SYSTEM),
        RemediationIntent.UPGRADE,
        None,
        package_name="acme-cli",
        index_url=long_url,
    )
    assert cmd.argv is not None
    with pytest.raises(ValueError, match="CHK028"):
        cmd.render("posix")
