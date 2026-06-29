"""Tests for UvReceiptReader and UvReceiptResult (WP02 T011).

Parity coverage for all parsing paths in the single authoritative reader.
No internet or uv process required — all I/O is faked via tmp_path fixtures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from specify_cli.compat._adapters.uv_receipt import UvReceiptReader, UvReceiptResult
from specify_cli.compat._detect.runtime import PackageSource

pytestmark = [pytest.mark.fast]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PACKAGE_NAME = "spec-kitty-cli"

_FULL_RECEIPT_TOML = """\
[tool]
python = "3.11"
bin_dir = "/home/user/.local/bin"

[[tool.requirements]]
name = "spec-kitty-cli"
specifier = "==3.2.0"

[[tool.requirements]]
name = "pytest"
specifier = ">=7"
"""

_GIT_RECEIPT_TOML = """\
[tool]
python = "3.12"

[[tool.requirements]]
name = "spec-kitty-cli"
git = "https://github.com/example/spec-kitty.git"
"""

_EDITABLE_RECEIPT_TOML = """\
[tool]

[[tool.requirements]]
name = "spec-kitty-cli"
editable = "/home/user/projects/spec-kitty"
"""

_URL_RECEIPT_TOML = """\
[tool]

[[tool.requirements]]
name = "spec-kitty-cli"
url = "https://example.com/spec-kitty-3.2.0-py3-none-any.whl"
"""

_DIRECTORY_RECEIPT_TOML = """\
[tool]

[[tool.requirements]]
name = "spec-kitty-cli"
directory = "/home/user/projects/spec-kitty"
"""

_PATH_RECEIPT_TOML = """\
[tool]

[[tool.requirements]]
name = "spec-kitty-cli"
path = "/home/user/wheels/spec-kitty.whl"
"""

_NO_SPEC_KITTY_RECEIPT_TOML = """\
[tool]
python = "3.11"

[[tool.requirements]]
name = "some-other-package"
specifier = ">=1.0"
"""

_MINIMAL_RECEIPT_TOML = """\
[tool]

[[tool.requirements]]
name = "spec-kitty-cli"
"""


def _make_uv_tool_env(tmp_path: Path, receipt_content: str, use_scripts: bool = False) -> tuple[Path, Path]:
    """Create a fake uv tool environment and return (executable, receipt_path)."""
    bin_name = "scripts" if use_scripts else "bin"
    bin_dir = tmp_path / "tool-env" / bin_name
    bin_dir.mkdir(parents=True)
    executable = bin_dir / "python"
    executable.touch()

    receipt_path = tmp_path / "tool-env" / "uv-receipt.toml"
    receipt_path.write_text(receipt_content, encoding="utf-8")

    return executable, receipt_path


# ---------------------------------------------------------------------------
# UvReceiptResult: construction
# ---------------------------------------------------------------------------


class TestUvReceiptResultConstruction:
    def test_frozen_dataclass(self) -> None:
        result = UvReceiptResult(
            receipt_path=None,
            tool_dir=None,
            bin_dir=None,
            is_default_tool_dir=None,
            is_default_bin_dir=None,
            python=None,
            requirements=(),
            package_source=PackageSource.UNKNOWN,
        )
        with pytest.raises((AttributeError, TypeError)):
            result.python = "3.11"  # type: ignore[misc]

    def test_all_none_fields_allowed(self) -> None:
        result = UvReceiptResult(
            receipt_path=None,
            tool_dir=None,
            bin_dir=None,
            is_default_tool_dir=None,
            is_default_bin_dir=None,
            python=None,
            requirements=(),
            package_source=PackageSource.UNKNOWN,
        )
        assert result.receipt_path is None
        assert result.requirements == ()
        assert result.package_source == PackageSource.UNKNOWN


# ---------------------------------------------------------------------------
# UvReceiptReader.read_for_executable: happy path
# ---------------------------------------------------------------------------


class TestReadForExecutableHappyPath:
    def test_all_fields_populated_from_full_receipt(self, tmp_path: Path) -> None:
        executable, receipt_path = _make_uv_tool_env(tmp_path, _FULL_RECEIPT_TOML)

        result = UvReceiptReader.read_for_executable(str(executable))

        assert result.receipt_path == receipt_path
        assert result.python == "3.11"
        assert result.bin_dir == Path("/home/user/.local/bin")
        assert len(result.requirements) == 2
        assert result.requirements[0].name == _PACKAGE_NAME
        assert result.requirements[0].specifier == "==3.2.0"
        assert result.requirements[1].name == "pytest"
        assert result.requirements[1].specifier == ">=7"
        assert result.package_source == PackageSource.PYPI_SPECIFIER
        # All entries use modelled keys → is_supported True (nothing discarded).
        assert all(req.is_supported for req in result.requirements)

    def test_unknown_requirement_key_marks_entry_unsupported(self, tmp_path: Path) -> None:
        """A receipt key the domain does not model flags is_supported=False.

        Load-bearing for FR-019 / SC-003 / issue #1358 "nothing discarded": the
        remediation planner refuses to reconstruct a command from an unsupported
        entry rather than silently collapsing it to a PyPI name.
        """
        receipt = (
            "[tool]\n"
            'requirements = [{ name = "spec-kitty-cli", unknown-source = "opaque" }]\n'
        )
        executable, _ = _make_uv_tool_env(tmp_path, receipt)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert len(result.requirements) == 1
        assert result.requirements[0].is_supported is False

    def test_tool_dir_from_path_derivation(self, tmp_path: Path) -> None:
        executable, _ = _make_uv_tool_env(tmp_path, _FULL_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        # tool_dir = receipt_path.parent.parent (tool-env's parent)
        assert result.tool_dir == tmp_path

    def test_tool_dir_from_env_var(self, tmp_path: Path, monkeypatch: Any) -> None:
        custom_tool_dir = tmp_path / "custom-tool-dir"
        monkeypatch.setenv("UV_TOOL_DIR", str(custom_tool_dir))
        executable, _ = _make_uv_tool_env(tmp_path, _FULL_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.tool_dir == custom_tool_dir

    def test_git_source_detection(self, tmp_path: Path) -> None:
        executable, _ = _make_uv_tool_env(tmp_path, _GIT_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.package_source == PackageSource.GIT
        assert result.requirements[0].git == "https://github.com/example/spec-kitty.git"
        assert result.python == "3.12"

    def test_editable_source_detection(self, tmp_path: Path) -> None:
        executable, _ = _make_uv_tool_env(tmp_path, _EDITABLE_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.package_source == PackageSource.EDITABLE
        assert result.requirements[0].editable == "/home/user/projects/spec-kitty"

    def test_url_source_detection(self, tmp_path: Path) -> None:
        executable, _ = _make_uv_tool_env(tmp_path, _URL_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.package_source == PackageSource.URL

    def test_directory_source_detection(self, tmp_path: Path) -> None:
        executable, _ = _make_uv_tool_env(tmp_path, _DIRECTORY_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.package_source == PackageSource.DIRECTORY

    def test_path_source_detection(self, tmp_path: Path) -> None:
        executable, _ = _make_uv_tool_env(tmp_path, _PATH_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.package_source == PackageSource.PATH

    def test_minimal_receipt_name_only(self, tmp_path: Path) -> None:
        """Receipt with name only (no specifier) → PYPI_SPECIFIER."""
        executable, _ = _make_uv_tool_env(tmp_path, _MINIMAL_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.package_source == PackageSource.PYPI_SPECIFIER

    def test_scripts_bin_dir_name(self, tmp_path: Path) -> None:
        """Windows-style 'Scripts' directory is also recognised."""
        executable, receipt_path = _make_uv_tool_env(tmp_path, _FULL_RECEIPT_TOML, use_scripts=True)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.receipt_path == receipt_path

    def test_bin_dir_from_entrypoints(self, tmp_path: Path) -> None:
        """bin_dir is derived from entrypoint install-path when not explicit."""
        install_path = "/home/user/.local/bin/spec-kitty"
        receipt_toml = f"""\
[tool]

[[tool.entrypoints]]
name = "spec-kitty"
install-path = "{install_path}"

[[tool.requirements]]
name = "spec-kitty-cli"
specifier = "==3.2.0"
"""
        executable, _ = _make_uv_tool_env(tmp_path, receipt_toml)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.bin_dir == Path("/home/user/.local/bin")


# ---------------------------------------------------------------------------
# UvReceiptReader.read_for_executable: error paths (NFR-003)
# ---------------------------------------------------------------------------


class TestReadForExecutableErrorPaths:
    def test_no_receipt_file_returns_empty(self, tmp_path: Path) -> None:
        bin_dir = tmp_path / "tool-env" / "bin"
        bin_dir.mkdir(parents=True)
        executable = bin_dir / "python"
        executable.touch()
        # No uv-receipt.toml created.
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.receipt_path is None
        assert result.requirements == ()
        assert result.package_source == PackageSource.UNKNOWN

    def test_malformed_toml_returns_empty(self, tmp_path: Path) -> None:
        bin_dir = tmp_path / "tool-env" / "bin"
        bin_dir.mkdir(parents=True)
        executable = bin_dir / "python"
        executable.touch()
        receipt = tmp_path / "tool-env" / "uv-receipt.toml"
        receipt.write_text("this is not valid TOML {{{{", encoding="utf-8")

        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.receipt_path is None
        assert result.requirements == ()

    def test_executable_not_in_bin_returns_empty(self, tmp_path: Path) -> None:
        """Executable not under bin/ or scripts/ → no receipt."""
        executable = tmp_path / "python"
        executable.touch()
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.receipt_path is None

    def test_nonexistent_executable_returns_empty(self) -> None:
        result = UvReceiptReader.read_for_executable("/nonexistent/path/to/python")
        assert result.receipt_path is None
        assert result.requirements == ()

    def test_no_spec_kitty_requirement_returns_unknown_source(self, tmp_path: Path) -> None:
        executable, _ = _make_uv_tool_env(tmp_path, _NO_SPEC_KITTY_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        # Receipt was found but no spec-kitty requirement → UNKNOWN source
        assert result.receipt_path is not None
        assert result.package_source == PackageSource.UNKNOWN

    def test_never_raises_on_any_input(self) -> None:
        """Exhaustive no-raise check with various bad inputs."""
        for bad_exe in ["", "/dev/null", "/nonexistent", None]:  # type: ignore[list-item]
            if bad_exe is None:
                continue
            result = UvReceiptReader.read_for_executable(bad_exe)
            assert isinstance(result, UvReceiptResult)


# ---------------------------------------------------------------------------
# UvReceiptReader.exists_for
# ---------------------------------------------------------------------------


class TestExistsFor:
    def test_returns_true_when_receipt_exists_with_spec_kitty(self, tmp_path: Path) -> None:
        executable, _ = _make_uv_tool_env(tmp_path, _FULL_RECEIPT_TOML)
        assert UvReceiptReader.exists_for(executable) is True

    def test_returns_false_when_no_receipt(self, tmp_path: Path) -> None:
        bin_dir = tmp_path / "tool-env" / "bin"
        bin_dir.mkdir(parents=True)
        executable = bin_dir / "python"
        executable.touch()
        assert UvReceiptReader.exists_for(executable) is False

    def test_returns_false_when_receipt_has_no_spec_kitty(self, tmp_path: Path) -> None:
        executable, _ = _make_uv_tool_env(tmp_path, _NO_SPEC_KITTY_RECEIPT_TOML)
        assert UvReceiptReader.exists_for(executable) is False

    def test_returns_false_when_not_in_bin_dir(self, tmp_path: Path) -> None:
        executable = tmp_path / "python"
        executable.touch()
        assert UvReceiptReader.exists_for(executable) is False

    def test_returns_false_on_nonexistent_path(self) -> None:
        assert UvReceiptReader.exists_for(Path("/nonexistent/path/python")) is False

    def test_never_raises(self, tmp_path: Path) -> None:
        for bad in [Path(""), Path("/nonexistent/bin/python"), tmp_path / "python"]:
            result = UvReceiptReader.exists_for(bad)
            assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Custom UV_TOOL_DIR env var
# ---------------------------------------------------------------------------


class TestCustomUvToolDir:
    def test_tool_dir_reflects_env_var(self, tmp_path: Path, monkeypatch: Any) -> None:
        custom_dir = tmp_path / "my-custom-tool-dir"
        monkeypatch.setenv("UV_TOOL_DIR", str(custom_dir))
        executable, _ = _make_uv_tool_env(tmp_path, _FULL_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        assert result.tool_dir == custom_dir

    def test_tool_dir_without_env_var_uses_path_derivation(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        monkeypatch.delenv("UV_TOOL_DIR", raising=False)
        executable, _ = _make_uv_tool_env(tmp_path, _FULL_RECEIPT_TOML)
        result = UvReceiptReader.read_for_executable(str(executable))
        # Without env var, tool_dir is derived from the receipt path:
        # receipt is at tmp_path/tool-env/uv-receipt.toml
        # tool_dir = receipt.parent.parent = tmp_path
        assert result.tool_dir == tmp_path
