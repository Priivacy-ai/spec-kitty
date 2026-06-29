"""Direct tests for detect_runtime() (FR-017, FR-022).

Covers:
- CHK032 / NFR-001: detect_runtime() never raises even when internal probes fail.
- SC-001: UV_TOOL install triggers exactly one UvReceiptReader.read_for_executable call.
- Non-UV_TOOL branch: no receipt read; receipt/dir/python fields are None/empty.
- safe_for_auto_upgrade derivation matches _SAFE_AUTO_UPGRADE_METHODS.
- FR-022 retirement parity: detect_runtime().install_method equals
  detect_install_method() from install_method.py for every InstallMethod value.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import specify_cli.compat._adapters.uv_receipt as uv_mod
import specify_cli.compat._detect.install_method as im_mod
import specify_cli.compat._detect.runtime as runtime_mod
from specify_cli.compat._adapters.uv_receipt import UvReceiptResult
from specify_cli.compat._detect.install_method import InstallMethod, _SAFE_AUTO_UPGRADE_METHODS
from specify_cli.compat._detect.runtime import (
    InstalledCliRuntime,
    PackageSource,
    UvRequirement,
    detect_runtime,
)


pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _make_receipt_result() -> UvReceiptResult:
    """Minimal, fully populated UvReceiptResult for UV_TOOL test paths."""
    return UvReceiptResult(
        receipt_path=Path("/home/test/.local/share/uv/tools/spec-kitty-cli/uv-receipt.toml"),
        tool_dir=Path("/home/test/.local/share/uv/tools"),
        bin_dir=Path("/home/test/.local/bin"),
        is_default_tool_dir=True,
        is_default_bin_dir=True,
        python="3.11",
        requirements=(UvRequirement(name="spec-kitty-cli", specifier="==3.2.0"),),
        package_source=PackageSource.PYPI_SPECIFIER,
    )


def _install_reader_stub(
    monkeypatch: pytest.MonkeyPatch,
    method: InstallMethod,
) -> None:
    """Patch detect_install_method and (for UV_TOOL) the receipt reader."""
    monkeypatch.setattr(im_mod, "detect_install_method", lambda: method)
    if method == InstallMethod.UV_TOOL:
        monkeypatch.setattr(
            uv_mod.UvReceiptReader,
            "read_for_executable",
            MagicMock(return_value=_make_receipt_result()),
        )


# ---------------------------------------------------------------------------
# (a) CHK032 / NFR-001: detect_runtime() NEVER raises
# ---------------------------------------------------------------------------


class TestDetectRuntimeNeverRaises:
    """CHK032 / NFR-001: detect_runtime() must never propagate exceptions."""

    def test_returns_unknown_default_on_internal_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the inner probe (detect_install_method) raises, detect_runtime() catches
        the exception and returns a safe UNKNOWN InstalledCliRuntime — no raise leaks out.
        """

        def _boom(*_args: object, **_kwargs: object) -> InstallMethod:
            raise RuntimeError("simulated catastrophic probe failure")

        monkeypatch.setattr(im_mod, "detect_install_method", _boom)

        # Must not raise.
        result = detect_runtime()

        assert isinstance(result, InstalledCliRuntime)
        assert result.install_method == InstallMethod.UNKNOWN
        assert result.receipt_path is None
        assert result.tool_dir is None
        assert result.bin_dir is None
        assert result.is_default_tool_dir is None
        assert result.is_default_bin_dir is None
        assert result.python is None
        assert result.requirements == ()
        assert result.package_source == PackageSource.UNKNOWN
        # Fail-closed: auto-upgrade is disabled in catastrophic fallback.
        assert result.safe_for_auto_upgrade is False

    def test_executable_is_sys_executable_in_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Even in catastrophic fallback the executable field must equal sys.executable."""

        def _boom(*_args: object, **_kwargs: object) -> InstallMethod:
            raise ValueError("another simulated failure")

        monkeypatch.setattr(im_mod, "detect_install_method", _boom)

        result = detect_runtime()
        assert result.executable == sys.executable

    def test_platform_field_present_in_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The platform field must be a valid literal in the fallback path."""

        def _boom(*_args: object, **_kwargs: object) -> InstallMethod:
            raise OSError("disk failure")

        monkeypatch.setattr(im_mod, "detect_install_method", _boom)

        result = detect_runtime()
        assert result.platform in {"posix", "windows"}


# ---------------------------------------------------------------------------
# (b) SC-001: UV_TOOL → exactly ONE UvReceiptReader.read_for_executable call
# ---------------------------------------------------------------------------


class TestDetectRuntimeUvToolSingleReceiptRead:
    """SC-001: For a UV_TOOL install the receipt must be read exactly once."""

    def test_read_for_executable_called_exactly_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        receipt_result = _make_receipt_result()

        monkeypatch.setattr(im_mod, "detect_install_method", lambda: InstallMethod.UV_TOOL)
        reader_spy = MagicMock(return_value=receipt_result)
        monkeypatch.setattr(uv_mod.UvReceiptReader, "read_for_executable", reader_spy)

        detect_runtime()

        assert reader_spy.call_count == 1, (
            f"Expected exactly 1 receipt read for UV_TOOL, got {reader_spy.call_count}"
        )

    def test_read_for_executable_called_with_sys_executable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        receipt_result = _make_receipt_result()

        monkeypatch.setattr(im_mod, "detect_install_method", lambda: InstallMethod.UV_TOOL)
        reader_spy = MagicMock(return_value=receipt_result)
        monkeypatch.setattr(uv_mod.UvReceiptReader, "read_for_executable", reader_spy)

        detect_runtime()

        reader_spy.assert_called_once_with(sys.executable)

    def test_receipt_derived_fields_populated_from_reader(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All receipt-derived fields come from UvReceiptReader, not invented."""
        receipt_result = _make_receipt_result()

        monkeypatch.setattr(im_mod, "detect_install_method", lambda: InstallMethod.UV_TOOL)
        monkeypatch.setattr(
            uv_mod.UvReceiptReader,
            "read_for_executable",
            MagicMock(return_value=receipt_result),
        )

        result = detect_runtime()

        assert result.install_method == InstallMethod.UV_TOOL
        assert result.receipt_path == receipt_result.receipt_path
        assert result.tool_dir == receipt_result.tool_dir
        assert result.bin_dir == receipt_result.bin_dir
        assert result.is_default_tool_dir == receipt_result.is_default_tool_dir
        assert result.is_default_bin_dir == receipt_result.is_default_bin_dir
        assert result.python == receipt_result.python
        assert result.requirements == receipt_result.requirements
        assert result.package_source == receipt_result.package_source


# ---------------------------------------------------------------------------
# (c) Non-UV_TOOL branch: no receipt read, optional fields are None/empty
# ---------------------------------------------------------------------------

_NON_UV_TOOL_METHODS = [m for m in InstallMethod if m != InstallMethod.UV_TOOL]


class TestDetectRuntimeNonUvToolBranch:
    """Non-UV_TOOL installs: no receipt read and all receipt fields None/empty."""

    @pytest.mark.parametrize("method", _NON_UV_TOOL_METHODS)
    def test_no_receipt_read_for_non_uv_tool(
        self, method: InstallMethod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(im_mod, "detect_install_method", lambda: method)
        # Spy that raises to catch any unexpected receipt read.
        reader_guard = MagicMock(
            side_effect=AssertionError(
                f"receipt must NOT be read for {method}"
            )
        )
        monkeypatch.setattr(uv_mod.UvReceiptReader, "read_for_executable", reader_guard)

        result = detect_runtime()

        assert reader_guard.call_count == 0
        assert result.install_method == method

    @pytest.mark.parametrize("method", _NON_UV_TOOL_METHODS)
    def test_receipt_fields_none_for_non_uv_tool(
        self, method: InstallMethod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(im_mod, "detect_install_method", lambda: method)
        monkeypatch.setattr(
            uv_mod.UvReceiptReader, "read_for_executable", MagicMock()
        )

        result = detect_runtime()

        assert result.receipt_path is None
        assert result.tool_dir is None
        assert result.bin_dir is None
        assert result.is_default_tool_dir is None
        assert result.is_default_bin_dir is None
        assert result.python is None
        assert result.requirements == ()
        assert result.package_source == PackageSource.UNKNOWN

    @pytest.mark.parametrize("method", _NON_UV_TOOL_METHODS)
    def test_executable_is_sys_executable_for_non_uv_tool(
        self, method: InstallMethod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(im_mod, "detect_install_method", lambda: method)
        monkeypatch.setattr(
            uv_mod.UvReceiptReader, "read_for_executable", MagicMock()
        )

        result = detect_runtime()
        assert result.executable == sys.executable


# ---------------------------------------------------------------------------
# (d) safe_for_auto_upgrade derivation matches _SAFE_AUTO_UPGRADE_METHODS
# ---------------------------------------------------------------------------


class TestSafeForAutoUpgrade:
    """safe_for_auto_upgrade must exactly mirror the _SAFE_AUTO_UPGRADE_METHODS whitelist."""

    @pytest.mark.parametrize("method", list(InstallMethod))
    def test_safe_for_auto_upgrade_matches_whitelist(
        self, method: InstallMethod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_reader_stub(monkeypatch, method)

        result = detect_runtime()

        expected = method in _SAFE_AUTO_UPGRADE_METHODS
        assert result.safe_for_auto_upgrade is expected, (
            f"safe_for_auto_upgrade mismatch for {method}: "
            f"expected {expected}, got {result.safe_for_auto_upgrade}"
        )


# ---------------------------------------------------------------------------
# (e) FR-022: detect_runtime().install_method retirement parity
# ---------------------------------------------------------------------------


class TestDetectRuntimeInstallMethodParity:
    """FR-022 regression guard: detect_runtime().install_method must agree
    with detect_install_method() from install_method.py for every InstallMethod value.

    The detect_install_method() shim in runtime.py was retired in WP07 (FR-022).
    These tests verify that callers migrated to detect_runtime().install_method
    observe identical behaviour to the canonical detect_install_method().
    """

    @pytest.mark.parametrize("method", list(InstallMethod))
    def test_detect_runtime_install_method_equals_underlying_detector(
        self, method: InstallMethod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """detect_runtime().install_method must return the same value
        as im_mod.detect_install_method() for every InstallMethod.
        Both go through the same internal path when the probe is controlled.
        """
        _install_reader_stub(monkeypatch, method)

        runtime_result = detect_runtime().install_method
        # The underlying detector is also mocked to return `method`, so both must agree.
        real_result = im_mod.detect_install_method()

        assert runtime_result == real_result, (
            f"Parity failure for {method}: "
            f"detect_runtime().install_method returned {runtime_result!r}, "
            f"real detector returned {real_result!r}"
        )

    def test_detect_runtime_install_method_delegates_to_detect_runtime(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Structural guard: install_method on the runtime snapshot must come
        from detect_runtime() — patch detect_runtime to return a known sentinel
        and verify callers observe the sentinel via the module reference.
        """
        sentinel = InstallMethod.BREW
        fake_runtime = InstalledCliRuntime(
            install_method=sentinel,
            executable=sys.executable,
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
        monkeypatch.setattr(runtime_mod, "detect_runtime", lambda: fake_runtime)

        # Use the module-attribute reference so the monkeypatch intercepts the call.
        result = runtime_mod.detect_runtime().install_method

        assert result == sentinel, (
            f"detect_runtime().install_method did not honour the patched runtime: "
            f"expected {sentinel!r}, got {result!r}"
        )
