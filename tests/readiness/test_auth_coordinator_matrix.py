"""Integration matrix for the readiness coordinator's auth wiring.

WS2 (issue Priivacy-ai/spec-kitty#1094).

Eight rows mirror Scenarios 1–8 in
``kitty-specs/auth-readiness-from-any-command-01KS7PQZ/spec.md``. Each row
exercises ``evaluate_readiness(ctx)`` end-to-end through the coordinator
with a stubbed probe verdict and a stubbed nag, and asserts the resulting
``AuthStatus`` plus the stderr / stdout contract.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
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


@dataclass(frozen=True)
class AuthMatrixRow:
    name: str
    argv: list[str]
    ci_env: bool
    isatty: bool
    hosted_enabled: bool
    probe_return: tuple[AuthStatus, str | None]
    expected_status: AuthStatus
    expected_policy: OutputPolicy
    # Predicates run against (stdout, stderr) captured output.
    stdout_assert: Callable[[str], bool]
    stderr_assert: Callable[[str], bool]


_TEAMSPACE = "acme-team"


def _stderr_contains_panel(text: str) -> bool:
    """Multiline interactive panel must include both handle and remediation."""
    return _TEAMSPACE in text and "spec-kitty auth login" in text and ("\n" in text)


def _stderr_is_canonical_line(text: str) -> bool:
    """Non-interactive case must emit exactly the canonical single line."""
    expected = (
        "spec-kitty: logged_out_on_connected_teamspace "
        f"teamspace={_TEAMSPACE} "
        "command=spec-kitty "
        "action=run-spec-kitty-auth-login\n"
    )
    return text == expected


def _stderr_no_teamspace(text: str) -> bool:
    return "teamspace" not in text.lower()


def _empty(text: str) -> bool:
    return text == ""


MATRIX: list[AuthMatrixRow] = [
    # Scenario 1 — hosted OFF: no leakage anywhere, DISABLED.
    AuthMatrixRow(
        name="hosted_off_silent",
        argv=[],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        probe_return=(AuthStatus.NOT_IN_TEAMSPACE, None),  # not consulted on hosted-off
        expected_status=AuthStatus.DISABLED,
        expected_policy=OutputPolicy.INTERACTIVE,
        stdout_assert=_empty,
        stderr_assert=_stderr_no_teamspace,
    ),
    # Scenario 2 — hosted ON, authenticated, TTY: silent.
    AuthMatrixRow(
        name="hosted_on_authenticated_tty",
        argv=[],
        ci_env=False,
        isatty=True,
        hosted_enabled=True,
        probe_return=(AuthStatus.AUTHENTICATED, None),
        expected_status=AuthStatus.AUTHENTICATED,
        expected_policy=OutputPolicy.INTERACTIVE,
        stdout_assert=_empty,
        stderr_assert=_stderr_no_teamspace,
    ),
    # Scenario 3 — hosted ON, logged-out, connected Teamspace, TTY:
    # interactive multiline panel.
    AuthMatrixRow(
        name="hosted_on_logged_out_tty",
        argv=[],
        ci_env=False,
        isatty=True,
        hosted_enabled=True,
        probe_return=(AuthStatus.LOGGED_OUT_IN_TEAMSPACE, _TEAMSPACE),
        expected_status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        expected_policy=OutputPolicy.INTERACTIVE,
        stdout_assert=_empty,
        stderr_assert=_stderr_contains_panel,
    ),
    # Scenario 4 — hosted ON, logged-out, non-TTY (CI): single-line canonical.
    AuthMatrixRow(
        name="hosted_on_logged_out_non_tty",
        argv=[],
        ci_env=True,
        isatty=False,
        hosted_enabled=True,
        probe_return=(AuthStatus.LOGGED_OUT_IN_TEAMSPACE, _TEAMSPACE),
        expected_status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        expected_policy=OutputPolicy.NON_INTERACTIVE,
        stdout_assert=_empty,
        stderr_assert=_stderr_is_canonical_line,
    ),
    # Scenario 5 — hosted ON, logged-out, no Teamspace markers: silent.
    AuthMatrixRow(
        name="hosted_on_not_in_teamspace_tty",
        argv=[],
        ci_env=False,
        isatty=True,
        hosted_enabled=True,
        probe_return=(AuthStatus.NOT_IN_TEAMSPACE, None),
        expected_status=AuthStatus.NOT_IN_TEAMSPACE,
        expected_policy=OutputPolicy.INTERACTIVE,
        stdout_assert=_empty,
        stderr_assert=_stderr_no_teamspace,
    ),
    # Scenario 6 — hosted ON, logged-out, --json: status still recorded,
    # stderr silent.
    AuthMatrixRow(
        name="hosted_on_logged_out_json",
        argv=["--json"],
        ci_env=False,
        isatty=True,
        hosted_enabled=True,
        probe_return=(AuthStatus.LOGGED_OUT_IN_TEAMSPACE, _TEAMSPACE),
        expected_status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        expected_policy=OutputPolicy.MACHINE_OUTPUT,
        stdout_assert=_empty,
        stderr_assert=_stderr_no_teamspace,
    ),
    # Scenario 7 — hosted ON, logged-out, --quiet: silent.
    AuthMatrixRow(
        name="hosted_on_logged_out_quiet",
        argv=["--quiet"],
        ci_env=False,
        isatty=True,
        hosted_enabled=True,
        probe_return=(AuthStatus.LOGGED_OUT_IN_TEAMSPACE, _TEAMSPACE),
        expected_status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        expected_policy=OutputPolicy.MACHINE_OUTPUT,
        stdout_assert=_empty,
        stderr_assert=_stderr_no_teamspace,
    ),
    # Scenario 8 — hosted ON, authenticated, --help: silent.
    AuthMatrixRow(
        name="hosted_on_authenticated_help",
        argv=["--help"],
        ci_env=False,
        isatty=True,
        hosted_enabled=True,
        probe_return=(AuthStatus.AUTHENTICATED, None),
        expected_status=AuthStatus.AUTHENTICATED,
        expected_policy=OutputPolicy.NON_INTERACTIVE,
        stdout_assert=_empty,
        stderr_assert=_empty,
    ),
]


def _make_ctx() -> typer.Context:
    app = typer.Typer()

    @app.callback()
    def _root_cb(ctx: typer.Context) -> None:  # pragma: no cover - scaffolding
        pass

    cmd = typer.main.get_command(app)
    return typer.Context(cmd)


@pytest.mark.parametrize("row", MATRIX, ids=[r.name for r in MATRIX])
def test_auth_matrix(
    row: AuthMatrixRow,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Hosted mode env.
    if row.hosted_enabled:
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    else:
        monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    # CI env (affects OutputPolicy).
    if row.ci_env:
        monkeypatch.setenv("CI", "1")
    else:
        monkeypatch.delenv("CI", raising=False)

    # Stable argv for output-policy derivation.
    monkeypatch.setattr(sys, "argv", ["spec-kitty", *row.argv])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: row.isatty)

    # Stub the nag so it never writes to stderr (covered by separate tests).
    monkeypatch.setattr(coord_module, "_invoke_nag", lambda ctx: None)

    # Stub the probe to deterministically return the row's verdict.
    from specify_cli.readiness import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "probe_auth_status",
        lambda **_kw: row.probe_return,
    )

    # Act.
    ctx = _make_ctx()
    result = evaluate_readiness(ctx)

    # Assert structural fields.
    assert isinstance(result, ReadinessResult)
    assert result.auth_status == row.expected_status, (
        f"row={row.name}: got auth_status={result.auth_status!r}, expected {row.expected_status!r}"
    )
    assert result.output_policy == row.expected_policy, (
        f"row={row.name}: got policy={result.output_policy!r}, expected {row.expected_policy!r}"
    )
    if row.hosted_enabled:
        assert result.enabled is True
        assert result.ran is True
    else:
        assert result.enabled is False
        assert result.ran is False
        # On the hosted-off path the coordinator must still set DISABLED.
        assert result.auth_status == AuthStatus.DISABLED

    # Assert output contract.
    captured = capsys.readouterr()
    assert row.stdout_assert(captured.out), (
        f"row={row.name}: stdout failed predicate; got {captured.out!r}"
    )
    assert row.stderr_assert(captured.err), (
        f"row={row.name}: stderr failed predicate; got {captured.err!r}"
    )


def test_coordinator_swallows_probe_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A probe that raises must not crash the CLI — coordinator degrades to UNKNOWN."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty"])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(coord_module, "_invoke_nag", lambda ctx: None)

    from specify_cli.readiness import auth as auth_module

    def _boom(**_kw: object) -> tuple[AuthStatus, str | None]:
        raise RuntimeError("synthetic probe failure")

    monkeypatch.setattr(auth_module, "probe_auth_status", _boom)

    ctx = _make_ctx()
    result = evaluate_readiness(ctx)

    assert isinstance(result, ReadinessResult)
    # The coordinator should degrade to UNKNOWN, not collapse to _NOOP_DISABLED.
    assert result.auth_status == AuthStatus.UNKNOWN
    assert result.enabled is True
    assert result.ran is True

    captured = capsys.readouterr()
    assert captured.out == ""
    # No teamspace text leaks when probe failed → no handle to render.
    assert "teamspace" not in captured.err.lower()


def test_coordinator_swallows_render_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A renderer that raises must not crash the CLI."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty"])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(coord_module, "_invoke_nag", lambda ctx: None)

    from specify_cli.readiness import auth as auth_module
    from specify_cli.readiness import render as render_module

    monkeypatch.setattr(
        auth_module,
        "probe_auth_status",
        lambda **_kw: (AuthStatus.LOGGED_OUT_IN_TEAMSPACE, _TEAMSPACE),
    )

    def _boom(**_kw: object) -> None:
        raise RuntimeError("synthetic renderer failure")

    monkeypatch.setattr(render_module, "render_auth_guidance", _boom)

    ctx = _make_ctx()
    result = evaluate_readiness(ctx)

    # Despite renderer failure, coordinator still returns a valid result with
    # the authoritative auth_status.
    assert isinstance(result, ReadinessResult)
    assert result.auth_status == AuthStatus.LOGGED_OUT_IN_TEAMSPACE
    assert result.enabled is True
    assert result.ran is True


def test_nag_still_fires_after_auth_guidance(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Nag must still be invoked exactly once on the hosted-enabled path,
    regardless of auth verdict. Wave 1 invariant preserved."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty"])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    call_count = {"n": 0}

    def _counting_nag(_ctx: typer.Context) -> None:
        call_count["n"] += 1

    monkeypatch.setattr(coord_module, "_invoke_nag", _counting_nag)

    from specify_cli.readiness import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "probe_auth_status",
        lambda **_kw: (AuthStatus.LOGGED_OUT_IN_TEAMSPACE, _TEAMSPACE),
    )

    ctx = _make_ctx()
    result = evaluate_readiness(ctx)

    assert call_count["n"] == 1
    assert result.nag_invoked is True
    assert result.auth_status == AuthStatus.LOGGED_OUT_IN_TEAMSPACE

    # Second call uses cache: nag must NOT fire again.
    evaluate_readiness(ctx)
    assert call_count["n"] == 1
