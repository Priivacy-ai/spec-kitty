"""WP04: upgrade_hint shares CHK028 allowlist length 512 (FR-014)."""

from __future__ import annotations

import pytest

from specify_cli.compat._detect.install_method import InstallMethod
from specify_cli.compat.remediation import COMMAND_ALLOWLIST_MAX_LEN
from specify_cli.compat.upgrade_hint import UpgradeHint

pytestmark = [pytest.mark.fast]


def test_shared_allowlist_constant() -> None:
    assert COMMAND_ALLOWLIST_MAX_LEN == 512


def test_long_index_command_accepted() -> None:
    long_index = "https://example.invalid/" + ("p" * 100) + "/simple/"
    command = f"pip install --upgrade --index-url {long_index} acme-spec-kitty-cli"
    assert 128 < len(command) <= COMMAND_ALLOWLIST_MAX_LEN
    hint = UpgradeHint(
        install_method=InstallMethod.PIP_SYSTEM,
        command=command,
        note=None,
    )
    assert hint.command == command


def test_over_max_still_rejected() -> None:
    command = "pip install " + ("x" * COMMAND_ALLOWLIST_MAX_LEN)
    with pytest.raises(ValueError, match="CHK028"):
        UpgradeHint(
            install_method=InstallMethod.PIP_SYSTEM,
            command=command,
            note=None,
        )
