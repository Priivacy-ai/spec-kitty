"""Strict JSON envelope contract tests (WP02, GitHub #842).

Locks in the FR-003 / FR-004 / NFR-001 / SC-002 contract:

* Every covered ``--json`` command produces stdout that
  ``json.loads(stdout)`` accepts as a top-level JSON object, in every
  SaaS state.
* No bare diagnostic line (e.g. ``"Not authenticated, skipping sync"``)
  ever leaks onto stdout outside the JSON envelope.

The contract MUST hold in all four SaaS states:

* ``disabled`` — ``SPEC_KITTY_ENABLE_SAAS_SYNC`` unset.
* ``unauthorized`` — flag set, no valid auth.
* ``network_failed`` — flag set, SaaS unreachable (mock raises).
* ``authorized_success`` — flag set, auth and SaaS reachable.

Test surface
------------

These tests are intentionally narrow: they exercise the ``--json``
contract only — they do not assert the *content* of the envelope, only
that it parses cleanly and that no forbidden bare strings appear on
stdout.  The list of covered commands is the production surface
identified during T007.  When a new ``--json`` command is added, append
its argv list to ``_COVERED_COMMANDS``.

Helper-level coverage for :func:`specify_cli.sync.diagnose.emit_diagnostic`
also lives in this file so the WP02 deliverable is testable as a unit
without a CLI subprocess.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.context import app as context_app
from specify_cli.cli.commands.agent.mission import app as mission_app
from specify_cli.sync.diagnose import emit_diagnostic


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Forbidden strings — ground truth for the bare-stdout regression scan
# ---------------------------------------------------------------------------

# These are exact strings that the bug at #842 caused to leak onto stdout.
# Any new bare-string leak discovered later should be appended here.
FORBIDDEN_STDOUT_STRINGS: tuple[str, ...] = (
    "Not authenticated, skipping sync",
    "skipping sync",
    "Not authenticated. Run `spec-kitty auth login`",
)


# ---------------------------------------------------------------------------
# Covered commands — strict-JSON contract surface
# ---------------------------------------------------------------------------


# Each entry is ``(label, app, argv, expects_success)``.  ``app`` is the
# Typer sub-app the command lives under, ``argv`` is the trailing
# arguments after the sub-app's own root.  ``expects_success`` indicates
# whether an exit code of 0 is required (some commands legitimately exit
# non-zero in the synthetic environment but MUST still emit strict JSON).
_COVERED_COMMANDS: list[tuple[str, Any, list[str], bool]] = [
    # mission branch-context: no filesystem dependencies beyond a git repo;
    # exits 0 on a clean branch, non-zero on detached HEAD / non-git, but
    # MUST always emit a parseable JSON object on stdout.
    (
        "mission_branch_context",
        mission_app,
        ["branch-context", "--json"],
        False,  # exit code may be non-zero in temp dir; we only assert JSON parse
    ),
    # mission setup-plan: SaaS-touching planner-setup; in a tmp dir with no
    # mission selected it returns a structured error envelope on stdout.
    (
        "mission_setup_plan",
        mission_app,
        ["setup-plan", "--mission", "nonexistent-mission", "--json"],
        False,
    ),
    # agent context resolve: invokes the SaaS-touching action-context resolver
    # path. With no mission in the temp dir it returns a MISSING_MISSION /
    # MISSION_NOT_FOUND error envelope — still strict JSON, still on stdout.
    # Typer collapses single-command apps so we omit the "resolve" prefix.
    (
        "agent_context_resolve",
        context_app,
        ["--action", "specify", "--mission", "nonexistent-mission", "--json"],
        False,
    ),
]


# ---------------------------------------------------------------------------
# SaaS state matrix
# ---------------------------------------------------------------------------


_SAAS_STATES: tuple[str, ...] = (
    "disabled",
    "unauthorized",
    "network_failed",
    "authorized_success",
)


@pytest.fixture()
def set_saas_state(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Return a callable that switches the test process into a SaaS state.

    Avoids real network/auth: we only manipulate the env var and (where
    necessary) monkeypatch the auth/sync surfaces so each branch
    deterministically takes its skip path.
    """

    def _apply(state: str) -> None:
        if state == "disabled":
            monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
        elif state == "unauthorized":
            monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
            # Force the token manager to report "not authenticated" if any
            # code path consults it during the command's lifecycle.
            try:
                from specify_cli.auth import get_token_manager

                tm = get_token_manager()
                # Best-effort: not all token managers expose this attribute,
                # but the tests don't depend on it — the env-var alone is
                # sufficient for the strict-JSON contract.
                if hasattr(tm, "_force_unauthenticated_for_tests"):
                    tm._force_unauthenticated_for_tests()  # type: ignore[attr-defined]
            except Exception:
                pass
        elif state == "network_failed":
            monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
            # Patch httpx.Client.request to raise a connection error if any
            # SaaS code path tries to reach out.  We use a minimal patch so
            # imports remain lightweight.
            import httpx

            def _boom(*_args: object, **_kwargs: object) -> None:
                raise httpx.ConnectError("simulated network failure")

            monkeypatch.setattr(httpx.Client, "request", _boom, raising=False)
        elif state == "authorized_success":
            monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
        else:  # pragma: no cover - defensive
            raise ValueError(f"unknown SaaS state: {state!r}")

    return _apply


@pytest.fixture()
def runner() -> CliRunner:
    """Return a typer CliRunner. typer >=0.13 separates stdout/stderr by default."""
    return CliRunner()


# ---------------------------------------------------------------------------
# T010 — strict-JSON parse across the (command × SaaS state) matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("saas_state", _SAAS_STATES)
@pytest.mark.parametrize(
    "label,app,argv,expects_success",
    _COVERED_COMMANDS,
    ids=[c[0] for c in _COVERED_COMMANDS],
)
def test_strict_json_parses_in_all_saas_states(
    label: str,
    app: Any,
    argv: list[str],
    expects_success: bool,
    saas_state: str,
    runner: CliRunner,
    set_saas_state: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``json.loads(stdout)`` MUST succeed in every SaaS state."""
    set_saas_state(saas_state)
    # Anchor the command in tmp_path so it can't accidentally talk to the
    # real repo state.  branch-context falls back gracefully to an error
    # JSON envelope when there is no git repo.
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, argv, catch_exceptions=False)

    assert result.stdout, (
        f"[{label}/{saas_state}] expected stdout output, got empty.\n"
        f"stderr={result.stderr!r}"
    )

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"[{label}/{saas_state}] stdout is not strict JSON: {exc}\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )

    assert isinstance(parsed, dict), (
        f"[{label}/{saas_state}] top-level JSON must be an object, "
        f"got {type(parsed).__name__}"
    )

    if expects_success:
        assert result.exit_code == 0, (
            f"[{label}/{saas_state}] expected exit 0, got {result.exit_code}.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# T011 — bare-string regression scan on stdout
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,app,argv,_expects_success",
    _COVERED_COMMANDS,
    ids=[c[0] for c in _COVERED_COMMANDS],
)
def test_no_bare_diagnostic_lines_on_stdout(
    label: str,
    app: Any,
    argv: list[str],
    _expects_success: bool,
    runner: CliRunner,
    set_saas_state: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No FORBIDDEN string from #842 may appear on stdout — even unauthorized."""
    set_saas_state("unauthorized")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, argv, catch_exceptions=False)

    for forbidden in FORBIDDEN_STDOUT_STRINGS:
        assert forbidden not in result.stdout, (
            f"[{label}] forbidden string {forbidden!r} leaked to stdout.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# Helper-level coverage for emit_diagnostic (T008 unit tests)
# ---------------------------------------------------------------------------


def test_emit_diagnostic_json_mode_false_writes_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``json_mode=False`` MUST land on stderr — never stdout."""
    emit_diagnostic("hello-stderr", category="auth", json_mode=False)
    captured = capsys.readouterr()
    assert "hello-stderr" not in captured.out
    assert "hello-stderr" in captured.err


def test_emit_diagnostic_json_mode_true_no_envelope_writes_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``json_mode=True`` without an envelope still writes to stderr."""
    emit_diagnostic(
        "hello-stderr-json", category="sync", json_mode=True, envelope=None
    )
    captured = capsys.readouterr()
    assert "hello-stderr-json" not in captured.out
    assert "hello-stderr-json" in captured.err


def test_emit_diagnostic_json_mode_true_with_envelope_nests_under_diagnostics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With an envelope, the message is nested and NEITHER stream sees it."""
    envelope: dict[str, Any] = {"result": "success"}
    emit_diagnostic(
        "nested-msg", category="tracker", json_mode=True, envelope=envelope
    )
    captured = capsys.readouterr()
    assert envelope == {
        "result": "success",
        "diagnostics": {"tracker": ["nested-msg"]},
    }
    assert "nested-msg" not in captured.out
    assert "nested-msg" not in captured.err


def test_emit_diagnostic_envelope_appends_when_category_already_present() -> None:
    """Multiple messages in the same category accumulate as a list."""
    envelope: dict[str, Any] = {}
    emit_diagnostic("first", category="auth", json_mode=True, envelope=envelope)
    emit_diagnostic("second", category="auth", json_mode=True, envelope=envelope)
    assert envelope["diagnostics"]["auth"] == ["first", "second"]


def test_emit_diagnostic_envelope_diagnostics_collision_falls_back_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """If the envelope already used ``diagnostics`` for non-dict, fall back."""
    envelope: dict[str, Any] = {"diagnostics": "already-a-string"}
    emit_diagnostic("fallback-msg", category="sync", json_mode=True, envelope=envelope)
    captured = capsys.readouterr()
    # Envelope is left unmolested.
    assert envelope == {"diagnostics": "already-a-string"}
    # Message went to stderr.
    assert "fallback-msg" not in captured.out
    assert "fallback-msg" in captured.err


def test_emit_diagnostic_envelope_category_collision_falls_back_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """If ``diagnostics[category]`` is not a list, do not mutate; stderr fallback."""
    envelope: dict[str, Any] = {"diagnostics": {"sync": "wrong-shape"}}
    emit_diagnostic("category-fallback", category="sync", json_mode=True, envelope=envelope)
    captured = capsys.readouterr()
    assert envelope == {"diagnostics": {"sync": "wrong-shape"}}
    assert "category-fallback" not in captured.out
    assert "category-fallback" in captured.err


# ---------------------------------------------------------------------------
# Sanity: forbidden string list is non-empty (guards against future regressions)
# ---------------------------------------------------------------------------


def test_forbidden_string_list_is_non_empty() -> None:
    assert len(FORBIDDEN_STDOUT_STRINGS) >= 2
    assert "Not authenticated, skipping sync" in FORBIDDEN_STDOUT_STRINGS


# ---------------------------------------------------------------------------
# Sanity: env var manipulation isolates correctly across parametrised runs
# ---------------------------------------------------------------------------


def test_set_saas_state_disabled_unsets_env_var(
    set_saas_state: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    set_saas_state("disabled")
    assert "SPEC_KITTY_ENABLE_SAAS_SYNC" not in os.environ


def test_set_saas_state_unauthorized_sets_env_var(set_saas_state: Any) -> None:
    set_saas_state("unauthorized")
    assert os.environ.get("SPEC_KITTY_ENABLE_SAAS_SYNC") == "1"
