"""Unit tests for the readiness auth-guidance renderer (WS2, issue #1094).

Validates the suppression / output matrix described in the module docstring of
``specify_cli.readiness.render``.
"""

from __future__ import annotations

import pytest

from specify_cli.readiness.coordinator import AuthStatus, OutputPolicy
from specify_cli.readiness.render import render_auth_guidance


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_interactive_logged_out_renders_multiline_panel_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    render_auth_guidance(
        status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        teamspace="acme-team",
        command_name="status",
        output_policy=OutputPolicy.INTERACTIVE,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    # Body must include the teamspace handle and the remediation command.
    assert "acme-team" in captured.err
    assert "spec-kitty auth login" in captured.err
    # Multi-line guidance — guard with a low bar of "more than 1 line".
    assert captured.err.count("\n") >= 1


def test_non_interactive_logged_out_emits_canonical_single_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    render_auth_guidance(
        status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        teamspace="acme-team",
        command_name="status",
        output_policy=OutputPolicy.NON_INTERACTIVE,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    expected = (
        "spec-kitty: logged_out_on_connected_teamspace "
        "teamspace=acme-team "
        "command=status "
        "action=run-spec-kitty-auth-login\n"
    )
    assert captured.err == expected


def test_machine_output_logged_out_is_silent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    render_auth_guidance(
        status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        teamspace="acme-team",
        command_name="status",
        output_policy=OutputPolicy.MACHINE_OUTPUT,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize(
    "status",
    [
        AuthStatus.AUTHENTICATED,
        AuthStatus.NOT_IN_TEAMSPACE,
        AuthStatus.UNKNOWN,
        AuthStatus.DISABLED,
        AuthStatus.NOT_CHECKED,
    ],
)
@pytest.mark.parametrize(
    "policy",
    [OutputPolicy.INTERACTIVE, OutputPolicy.NON_INTERACTIVE, OutputPolicy.MACHINE_OUTPUT],
)
def test_non_logged_out_statuses_render_nothing(
    status: AuthStatus,
    policy: OutputPolicy,
    capsys: pytest.CaptureFixture[str],
) -> None:
    render_auth_guidance(
        status=status,
        teamspace="acme-team",  # Ignored for non-LOGGED_OUT statuses.
        command_name="status",
        output_policy=policy,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize("handle", [None, "", "   "])
def test_logged_out_without_handle_renders_nothing(
    handle: str | None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    render_auth_guidance(
        status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        teamspace=handle,
        command_name="status",
        output_policy=OutputPolicy.INTERACTIVE,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_renderer_does_not_raise_on_panel_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Force the Rich-backed path to raise; the renderer must fall through to
    # the plain-text fallback (still on stderr) without raising.
    import rich.panel as panel_mod

    class _BoomPanel:
        def __init__(self, *_a: object, **_kw: object) -> None:
            raise RuntimeError("synthetic Rich failure")

    monkeypatch.setattr(panel_mod, "Panel", _BoomPanel)

    # Should not raise.
    render_auth_guidance(
        status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        teamspace="acme-team",
        command_name="status",
        output_policy=OutputPolicy.INTERACTIVE,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    # Plain-text fallback still contains the remediation + the handle.
    assert "acme-team" in captured.err
    assert "spec-kitty auth login" in captured.err


def test_renderer_swallows_outer_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Make the inner _render_interactive_panel raise to verify the outermost
    # try/except suppresses it. The renderer's contract is "never raises".
    import specify_cli.readiness.render as render_mod

    def _boom(*_a: object, **_kw: object) -> None:
        raise RuntimeError("synthetic interactive renderer failure")

    monkeypatch.setattr(render_mod, "_render_interactive_panel", _boom)

    # Must NOT raise.
    render_auth_guidance(
        status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        teamspace="acme-team",
        command_name="status",
        output_policy=OutputPolicy.INTERACTIVE,
    )


def test_renderer_handles_missing_command_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    render_auth_guidance(
        status=AuthStatus.LOGGED_OUT_IN_TEAMSPACE,
        teamspace="acme-team",
        command_name="",  # empty
        output_policy=OutputPolicy.NON_INTERACTIVE,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    # Falls back to the literal "spec-kitty" sentinel.
    assert "command=spec-kitty " in captured.err
