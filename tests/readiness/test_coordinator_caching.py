"""Caching invariants for the readiness coordinator.

Asserts FR-008 (get_readiness never raises, returns no-op default when no cache),
FR-009 (double-invocation returns cached result), and FR-007 (ctx.obj keying).

Mission: cli-startup-readiness-coordinator-skeleton-01KS7JRV
"""

from __future__ import annotations

import sys
from typing import Any

import pytest
import typer

from specify_cli.readiness import (
    AuthStatus,
    ReadinessResult,
    evaluate_readiness,
    get_readiness,
)
from specify_cli.readiness import coordinator as coord_module


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _make_ctx(obj: Any = None) -> typer.Context:
    """Build a minimal typer.Context with a settable ctx.obj."""
    app = typer.Typer()

    @app.callback()
    def _root_cb(ctx: typer.Context) -> None:  # pragma: no cover
        pass

    cmd = typer.main.get_command(app)
    ctx = typer.Context(cmd)
    ctx.obj = obj
    return ctx


def test_A_hosted_enabled_cached_after_first_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With SAAS sync enabled, calling evaluate_readiness twice invokes the upgrade UX once.

    WS3 (issue #1092) routed the hosted-enabled path through the new
    ``_invoke_upgrade_ux`` seam instead of the legacy ``_invoke_nag``
    renderer. Caching invariants are unchanged: a second call returns
    the same cached ReadinessResult instance and the seam fires exactly
    once.
    """
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status"])

    call_count = {"n": 0}

    def _spy_invoke(ctx: typer.Context) -> None:
        call_count["n"] += 1

    monkeypatch.setattr(coord_module, "_invoke_upgrade_ux", _spy_invoke)
    # Belt-and-suspenders: legacy _invoke_nag MUST NOT fire on hosted-enabled.
    monkeypatch.setattr(
        coord_module,
        "_invoke_nag",
        lambda ctx: pytest.fail(
            "legacy _invoke_nag should not fire on hosted-enabled path"
        ),
    )

    ctx = _make_ctx()
    first = evaluate_readiness(ctx)
    second = evaluate_readiness(ctx)

    assert call_count["n"] == 1, f"expected 1 upgrade-ux call, got {call_count['n']}"
    assert first is second, "second call should return cached result instance"
    assert first.enabled is True


def test_B_hosted_disabled_cached_after_first_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without SAAS sync, the disabled path still caches and still invokes the nag exactly once."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status"])

    call_count = {"n": 0}

    def _spy_invoke_nag(ctx: typer.Context) -> None:
        call_count["n"] += 1

    monkeypatch.setattr(coord_module, "_invoke_nag", _spy_invoke_nag)

    ctx = _make_ctx()
    first = evaluate_readiness(ctx)
    second = evaluate_readiness(ctx)

    assert call_count["n"] == 1, f"expected 1 nag call, got {call_count['n']}"
    assert first is second
    assert first.enabled is False


def test_C_get_readiness_returns_same_instance_after_evaluate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_readiness returns the cached ReadinessResult by identity."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty"])
    monkeypatch.setattr(coord_module, "_invoke_nag", lambda ctx: None)

    ctx = _make_ctx()
    evaluated = evaluate_readiness(ctx)
    retrieved = get_readiness(ctx)

    assert retrieved is evaluated


def test_D_get_readiness_fresh_ctx_returns_noop_default() -> None:
    """get_readiness on a fresh ctx with no cache returns the no-op default, does not raise."""
    ctx = _make_ctx(obj=None)
    result = get_readiness(ctx)
    assert isinstance(result, ReadinessResult)
    assert result.enabled is False
    assert result.ran is False
    assert result.auth_status == AuthStatus.DISABLED
    assert result.nag_invoked is False


def test_E_get_readiness_non_dict_ctx_obj_returns_noop_default() -> None:
    """get_readiness with a non-dict, non-None ctx.obj returns the no-op default, does not raise."""

    class _Opaque:
        pass

    ctx = _make_ctx(obj=_Opaque())
    result = get_readiness(ctx)
    assert isinstance(result, ReadinessResult)
    assert result.enabled is False
    assert result.ran is False
    assert result.auth_status == AuthStatus.DISABLED
