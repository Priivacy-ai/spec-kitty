"""Unit tests for InstalledCliRuntime, UvRequirement, and PackageSource (WP01 T005).

Covers:
- Construction with all fields populated
- Construction with all optional fields None/empty
- PackageSource enum membership and string values
- Frozen constraint (FrozenInstanceError on field assignment)
- CHK028 regex parity between remediation.py and upgrade_hint.py
"""

from __future__ import annotations

import pytest

from specify_cli.compat._detect.install_method import InstallMethod
from specify_cli.compat._detect.runtime import (
    InstalledCliRuntime,
    PackageSource,
    UvRequirement,
)


pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# PackageSource enum
# ---------------------------------------------------------------------------


class TestPackageSource:
    def test_all_seven_members_present(self) -> None:
        members = {m.name for m in PackageSource}
        assert members == {
            "PYPI_SPECIFIER",
            "GIT",
            "URL",
            "DIRECTORY",
            "EDITABLE",
            "PATH",
            "UNKNOWN",
        }

    @pytest.mark.parametrize(
        "member,expected_value",
        [
            (PackageSource.PYPI_SPECIFIER, "pypi-specifier"),
            (PackageSource.GIT, "git"),
            (PackageSource.URL, "url"),
            (PackageSource.DIRECTORY, "directory"),
            (PackageSource.EDITABLE, "editable"),
            (PackageSource.PATH, "path"),
            (PackageSource.UNKNOWN, "unknown"),
        ],
    )
    def test_string_values(self, member: PackageSource, expected_value: str) -> None:
        assert str(member) == expected_value
        assert member.value == expected_value


# ---------------------------------------------------------------------------
# UvRequirement dataclass
# ---------------------------------------------------------------------------


class TestUvRequirement:
    def test_construct_with_name_only(self) -> None:
        req = UvRequirement(name="spec-kitty-cli")
        assert req.name == "spec-kitty-cli"
        assert req.specifier is None
        assert req.directory is None
        assert req.editable is None
        assert req.path is None
        assert req.git is None
        assert req.url is None

    def test_construct_with_all_fields(self) -> None:
        req = UvRequirement(
            name="spec-kitty-cli",
            specifier="==3.2.0",
            directory="/some/dir",
            editable="/editable/path",
            path="/wheel.whl",
            git="https://github.com/example/repo.git",
            url="https://example.com/pkg.tar.gz",
        )
        assert req.name == "spec-kitty-cli"
        assert req.specifier == "==3.2.0"
        assert req.directory == "/some/dir"
        assert req.editable == "/editable/path"
        assert req.path == "/wheel.whl"
        assert req.git == "https://github.com/example/repo.git"
        assert req.url == "https://example.com/pkg.tar.gz"

    def test_frozen_constraint(self) -> None:
        req = UvRequirement(name="spec-kitty-cli")
        with pytest.raises((AttributeError, TypeError)):
            req.name = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# InstalledCliRuntime dataclass
# ---------------------------------------------------------------------------


class TestInstalledCliRuntime:
    def _make_full(self) -> InstalledCliRuntime:
        from pathlib import Path

        req = UvRequirement(name="spec-kitty-cli", specifier="==3.2.0")
        return InstalledCliRuntime(
            install_method=InstallMethod.UV_TOOL,
            executable="/home/user/.local/share/uv/tools/spec-kitty-cli/bin/python",
            receipt_path=Path("/home/user/.local/share/uv/tools/spec-kitty-cli/uv-receipt.toml"),
            tool_dir=Path("/home/user/.local/share/uv/tools"),
            bin_dir=Path("/home/user/.local/bin"),
            is_default_tool_dir=True,
            is_default_bin_dir=True,
            python="3.11",
            requirements=(req,),
            package_source=PackageSource.PYPI_SPECIFIER,
            platform="posix",
            safe_for_auto_upgrade=True,
        )

    def test_construct_with_all_fields_populated(self) -> None:
        rt = self._make_full()
        assert rt.install_method == InstallMethod.UV_TOOL
        assert rt.executable == "/home/user/.local/share/uv/tools/spec-kitty-cli/bin/python"
        assert rt.receipt_path is not None
        assert rt.tool_dir is not None
        assert rt.bin_dir is not None
        assert rt.is_default_tool_dir is True
        assert rt.is_default_bin_dir is True
        assert rt.python == "3.11"
        assert len(rt.requirements) == 1
        assert rt.requirements[0].name == "spec-kitty-cli"
        assert rt.package_source == PackageSource.PYPI_SPECIFIER
        assert rt.platform == "posix"
        assert rt.safe_for_auto_upgrade is True

    def test_construct_with_optional_fields_none(self) -> None:
        rt = InstalledCliRuntime(
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
        assert rt.receipt_path is None
        assert rt.tool_dir is None
        assert rt.bin_dir is None
        assert rt.is_default_tool_dir is None
        assert rt.is_default_bin_dir is None
        assert rt.python is None
        assert rt.requirements == ()

    def test_requirements_is_empty_tuple_not_none(self) -> None:
        rt = InstalledCliRuntime(
            install_method=InstallMethod.PIPX,
            executable="/usr/bin/python",
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
        assert rt.requirements == ()
        assert isinstance(rt.requirements, tuple)

    def test_platform_windows(self) -> None:
        rt = InstalledCliRuntime(
            install_method=InstallMethod.PIP_USER,
            executable="C:\\Python311\\python.exe",
            receipt_path=None,
            tool_dir=None,
            bin_dir=None,
            is_default_tool_dir=None,
            is_default_bin_dir=None,
            python=None,
            requirements=(),
            package_source=PackageSource.UNKNOWN,
            platform="windows",
            safe_for_auto_upgrade=True,
        )
        assert rt.platform == "windows"

    def test_frozen_constraint(self) -> None:
        rt = self._make_full()
        with pytest.raises((AttributeError, TypeError)):
            rt.executable = "/other/python"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CHK028 regex parity: remediation.py vs upgrade_hint.py
# ---------------------------------------------------------------------------


class TestChk028RegexParity:
    def test_remediation_command_re_matches_upgrade_hint_command_re(self) -> None:
        """CHK028 regex in remediation.py must be identical to upgrade_hint.py."""
        from specify_cli.compat.remediation import _COMMAND_RE as remediation_re
        from specify_cli.compat.upgrade_hint import _COMMAND_RE as hint_re

        # Compare the underlying pattern strings.
        assert remediation_re.pattern == hint_re.pattern, (
            f"CHK028 regex mismatch: remediation.py has {remediation_re.pattern!r}, "
            f"upgrade_hint.py has {hint_re.pattern!r}"
        )

    def test_chk028_regex_accepts_valid_commands(self) -> None:
        from specify_cli.compat.remediation import _COMMAND_RE

        valid = [
            "pipx upgrade spec-kitty-cli",
            "uv tool install --force spec-kitty-cli==3.2.0",
            "pip install --user --upgrade spec-kitty-cli",
            "brew upgrade spec-kitty-cli",
        ]
        for cmd in valid:
            assert _COMMAND_RE.match(cmd), f"Expected match for: {cmd!r}"

    def test_chk028_regex_rejects_shell_metacharacters(self) -> None:
        from specify_cli.compat.remediation import _COMMAND_RE

        invalid = [
            "echo $(id)",
            "cmd && rm -rf /",
            "cmd; evil",
            "cmd | pipe",
            "cmd > /dev/null",
        ]
        for cmd in invalid:
            assert _COMMAND_RE.match(cmd) is None, f"Expected no match for: {cmd!r}"
