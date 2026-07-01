"""Suppression matrix tests for the readiness coordinator.

Asserts FR-011 (no Teamspace leakage when hosted mode is disabled, across the
full suppression matrix) and FR-004 (output policy derivation).

Mission: cli-startup-readiness-coordinator-skeleton-01KS7JRV
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import pytest
import typer

from specify_cli.readiness import (
    AuthStatus,
    OutputPolicy,
    ReadinessResult,
    evaluate_readiness,
)
from specify_cli.readiness import coordinator as coord_module


pytestmark = [pytest.mark.unit, pytest.mark.fast]


@dataclass(frozen=True)
class MatrixRow:
    name: str
    argv: list[str]
    ci_env: bool
    isatty: bool
    hosted_enabled: bool
    expected_policy: OutputPolicy
    expected_enabled: bool


# 7-row suppression matrix (hosted mode OFF) + 1 hosted-mode-enabled row.
MATRIX_ROWS: list[MatrixRow] = [
    MatrixRow(
        name="help",
        argv=["--help"],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.NON_INTERACTIVE,
        expected_enabled=False,
    ),
    MatrixRow(
        name="version",
        argv=["--version"],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.NON_INTERACTIVE,
        expected_enabled=False,
    ),
    MatrixRow(
        name="plain_invocation",
        argv=[],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.INTERACTIVE,
        expected_enabled=False,
    ),
    MatrixRow(
        name="json",
        argv=["status", "--json"],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.MACHINE_OUTPUT,
        expected_enabled=False,
    ),
    MatrixRow(
        name="quiet",
        argv=["status", "--quiet"],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.MACHINE_OUTPUT,
        expected_enabled=False,
    ),
    MatrixRow(
        name="ci",
        argv=["status"],
        ci_env=True,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.NON_INTERACTIVE,
        expected_enabled=False,
    ),
    MatrixRow(
        name="non_tty",
        argv=["status"],
        ci_env=False,
        isatty=False,
        hosted_enabled=False,
        expected_policy=OutputPolicy.NON_INTERACTIVE,
        expected_enabled=False,
    ),
    # Hosted-mode-enabled row: still no Teamspace leakage because the auth probe
    # is not exercised in this mission.
    MatrixRow(
        name="hosted_enabled_interactive",
        argv=["status"],
        ci_env=False,
        isatty=True,
        hosted_enabled=True,
        expected_policy=OutputPolicy.INTERACTIVE,
        expected_enabled=True,
    ),
]


def _make_ctx() -> typer.Context:
    """Build a minimal typer.Context with ctx.obj=None for testing."""
    app = typer.Typer()

    @app.callback()
    def _root_cb(ctx: typer.Context) -> None:  # pragma: no cover - test scaffolding
        pass

    cmd = typer.main.get_command(app)
    return typer.Context(cmd)


@pytest.mark.parametrize("row", MATRIX_ROWS, ids=[r.name for r in MATRIX_ROWS])
def test_suppression_matrix_no_teamspace_leakage(
    row: MatrixRow,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange env: SPEC_KITTY_ENABLE_SAAS_SYNC
    if row.hosted_enabled:
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    else:
        monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    # Arrange env: CI
    if row.ci_env:
        monkeypatch.setenv("CI", "1")
    else:
        monkeypatch.delenv("CI", raising=False)

    # Suppress side-effects of the wrapped legacy nag — we are testing the
    # coordinator's suppression contract, not the nag's behavior (covered in
    # WP03 nag passthrough tests).
    monkeypatch.setattr(coord_module, "_invoke_nag", lambda ctx: None)

    # WS2 (issue #1094): the readiness auth probe now runs on the
    # hosted-enabled path. Stub it to a Teamspace-free verdict so this
    # Wave 1 suppression matrix continues to assert the "no leakage"
    # invariant deterministically — independent of any local repo state.
    from specify_cli.readiness import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "probe_auth_status",
        lambda **_kw: (AuthStatus.NOT_IN_TEAMSPACE, None),
    )

    # Arrange argv
    monkeypatch.setattr(sys, "argv", ["spec-kitty", *row.argv])

    # Arrange isatty
    monkeypatch.setattr(sys.stdout, "isatty", lambda: row.isatty)

    # Act
    ctx = _make_ctx()
    result = evaluate_readiness(ctx)

    # Assert: result fields
    assert isinstance(result, ReadinessResult), f"got {type(result)!r}"
    assert result.enabled == row.expected_enabled, f"row={row.name}: enabled mismatch ({result.enabled})"
    assert (
        result.output_policy == row.expected_policy
    ), f"row={row.name}: policy mismatch ({result.output_policy})"
    if row.expected_enabled:
        # WS2 (issue #1094) widened AuthStatus. The probe now produces one of
        # the authoritative values; the Wave 1 ``NOT_CHECKED`` sentinel is no
        # longer emitted by the coordinator. The Wave 1 readiness API
        # contract explicitly permits this enum widening.
        assert result.auth_status in {
            AuthStatus.AUTHENTICATED,
            AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
            AuthStatus.NOT_IN_TEAMSPACE,
            AuthStatus.UNKNOWN,
        }, f"row={row.name}: enabled rows expect an authoritative auth status, got {result.auth_status!r}"
        assert result.ran is True
    else:
        assert (
            result.auth_status == AuthStatus.DISABLED
        ), f"row={row.name}: disabled rows expect DISABLED"
        assert result.ran is False

    # Assert: no Teamspace leakage
    captured = capsys.readouterr()
    assert "teamspace" not in captured.out.lower(), (
        f"row={row.name}: Teamspace leaked to stdout: {captured.out!r}"
    )
    assert "teamspace" not in captured.err.lower(), (
        f"row={row.name}: Teamspace leaked to stderr: {captured.err!r}"
    )
