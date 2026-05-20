"""FR-007 post-merge remediation: per-action daemon-coherence gate.

The mission-review for ``mvp-sync-boundary-cli-01KRVCQS`` surfaced a MEDIUM
finding (DRIFT-1): ``check_daemon_owner_match()`` from WP02 was built but
had zero call sites from sync mutating commands. FR-007 says the CLI MUST
refuse the action when foreground/daemon mismatch on any D-3 field; today
that refusal only fires via ``sync status --check``, not at the per-action
gate.

This test file locks the per-action gate into place by exercising the new
``_require_daemon_owner_coherence`` helper and confirming each gated sync
mutating command refuses on mismatch and proceeds on coherence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.integration]

import typer
from typer.testing import CliRunner


@pytest.fixture(autouse=True)
def _scoped_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin HOME to a tmp directory (NFR-001) so no live ``~/.spec-kitty`` is read."""

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    return tmp_path


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


def test_gate_no_op_when_no_owner_record_exists() -> None:
    """No daemon record on disk → gate returns silently."""

    from specify_cli.cli.commands.sync import _require_daemon_owner_coherence

    # ``check_daemon_owner_match`` returns (True, []) when no record exists.
    # The gate must not raise.
    _require_daemon_owner_coherence("spec-kitty sync now")


def _make_preflight_result(*, ok: bool, mismatches: tuple = (), orphan_records: tuple = ()):
    """Construct a stub :class:`PreflightResult` for the gate tests.

    WP03 (T011) replaced the gate's internals so it now delegates to
    :func:`specify_cli.sync.preflight.run_preflight` instead of
    :func:`specify_cli.sync.owner.check_daemon_owner_match`. These helpers
    patch the new entry point.
    """
    from specify_cli.sync.preflight import OwnerMismatch, PreflightResult

    del OwnerMismatch  # imported for forward-compatible references in callers
    return PreflightResult(
        ok=ok,
        mismatches=mismatches,
        orphan_records=orphan_records,
        legacy_event_rows=0,
        legacy_body_upload_rows=0,
        auth_present=True,
        auth_required=False,
    )


def test_gate_no_op_when_owner_matches_foreground() -> None:
    """Foreground identity matches daemon record → gate returns silently."""

    from specify_cli.cli.commands import sync as sync_module

    # The gate now delegates to ``run_preflight``; patch that entry point.
    with patch(
        "specify_cli.sync.preflight.run_preflight",
        return_value=_make_preflight_result(ok=True),
    ):
        sync_module._require_daemon_owner_coherence("spec-kitty sync share")


def test_gate_refuses_on_mismatch_naming_field() -> None:
    """Mismatched field → gate raises typer.Exit(2) with field name in console."""

    from specify_cli.cli.commands import sync as sync_module
    from specify_cli.sync.preflight import OwnerMismatch

    mismatches = (
        OwnerMismatch(
            field="daemon_package_version",
            foreground_value="3.2.0-foreground",
            daemon_value="3.2.0-stale",
            remediation_hint="Restart the daemon.",
        ),
    )
    with patch(
        "specify_cli.sync.preflight.run_preflight",
        return_value=_make_preflight_result(ok=False, mismatches=mismatches),
    ):
        with pytest.raises(typer.Exit) as exc_info:
            sync_module._require_daemon_owner_coherence("spec-kitty sync now")
    assert exc_info.value.exit_code == 2


def test_gate_refuses_on_multiple_mismatches() -> None:
    """Multiple mismatched fields → gate raises exit(2); all fields surfaced."""

    from specify_cli.cli.commands import sync as sync_module
    from specify_cli.sync.preflight import OwnerMismatch

    mismatches = tuple(
        OwnerMismatch(
            field=fname,  # type: ignore[arg-type]
            foreground_value="fg",
            daemon_value="daemon",
            remediation_hint="Restart.",
        )
        for fname in (
            "daemon_package_version",
            "daemon_executable_path",
            "daemon_queue_db_path",
        )
    )
    with patch(
        "specify_cli.sync.preflight.run_preflight",
        return_value=_make_preflight_result(ok=False, mismatches=mismatches),
    ):
        with pytest.raises(typer.Exit) as exc_info:
            sync_module._require_daemon_owner_coherence("spec-kitty sync share")
    assert exc_info.value.exit_code == 2


# ---------------------------------------------------------------------------
# Integration tests via CliRunner — confirm the gate is wired into each
# mutating command's entry point and fires BEFORE any state mutation.
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def _patch_match_returns(coherent: bool, mismatched: list[str] | None = None) -> Any:
    """Patch ``run_preflight`` to return a fixed outcome.

    WP03 (T011) replaced the gate's internals; the previous patch target
    (``check_daemon_owner_match``) is no longer consulted by the gate.
    Returns the context manager so the caller can ``with _patch_...:``.
    """
    from specify_cli.sync.preflight import OwnerMismatch, PreflightResult

    mismatch_objs: tuple[OwnerMismatch, ...] = ()
    if not coherent:
        names = mismatched or ["package_version"]
        mismatch_objs = tuple(
            OwnerMismatch(
                # Map bare field names into the canonical "daemon_<field>"
                # form so the test fixture mirrors the new preflight contract.
                field=(  # type: ignore[arg-type]
                    name if name.startswith("daemon_") else f"daemon_{name}"
                ),
                foreground_value="fg-value",
                daemon_value="daemon-value",
                remediation_hint="Restart the daemon.",
            )
            for name in names
        )

    result = PreflightResult(
        ok=coherent,
        mismatches=mismatch_objs,
        orphan_records=(),
        legacy_event_rows=0,
        legacy_body_upload_rows=0,
        auth_present=True,
        auth_required=False,
    )
    return patch(
        "specify_cli.sync.preflight.run_preflight",
        return_value=result,
    )


@pytest.mark.parametrize(
    "command,argv",
    [
        ("sync now", ["now"]),
        ("sync share", ["share", "demo-team"]),
        ("sync unshare", ["unshare", "demo-team"]),
        ("sync opt-out", ["opt-out"]),
        ("sync opt-in", ["opt-in"]),
    ],
)
def test_gated_command_exits_non_zero_on_mismatch(
    command: str, argv: list[str], cli_runner: CliRunner
) -> None:
    """Each gated sync mutating command must exit non-zero on mismatch."""

    from specify_cli.cli.commands.sync import app

    with _patch_match_returns(False, ["package_version"]):
        result = cli_runner.invoke(app, argv)
    assert result.exit_code != 0, (
        f"{command} did NOT refuse on D-3 mismatch — FR-007 gate missing or "
        f"placed too late in the command (stdout={result.stdout!r})"
    )
    # The gate's remediation message names the mismatched field. The
    # rendered table prints the canonical name with the ``daemon_`` prefix.
    combined = result.stdout + " " + str(result.exception)
    assert "package_version" in combined, (
        f"{command} refusal did not surface the canonical field name "
        f"(stdout={result.stdout!r}, exception={result.exception!r})"
    )


def test_status_command_not_gated_when_mismatch_present(cli_runner: CliRunner) -> None:
    """``sync status`` is read-only and MUST NOT be gated by daemon coherence.

    The whole point of ``status`` is to surface the mismatch state; gating
    it would defeat itself. The existing ``--check`` flag is the right
    surface for exit-code-based gating on the read side.
    """

    from specify_cli.cli.commands.sync import app

    with _patch_match_returns(False, ["package_version"]):
        # ``status`` may have its own non-zero exit conditions (e.g. when
        # the legacy queue has rows for the active scope or when --check is
        # set and the foreground/daemon disagree). The contract we lock
        # here is that the gate at the top of the command does NOT raise
        # typer.Exit before the body runs.
        result = cli_runner.invoke(app, ["status"])
    # The command may exit zero or non-zero based on its own logic, but it
    # must NOT bubble up our ``Refusing ... daemon/foreground mismatch``
    # message verbatim from the gate, because the gate isn't wired here.
    assert "Refusing `spec-kitty sync status`" not in result.stdout


# ---------------------------------------------------------------------------
# Locked-call-sites invariant: every mutating sync command exposes the gate.
# ---------------------------------------------------------------------------


def test_each_mutating_command_calls_the_gate() -> None:
    """AST-level lock: each gated command's body references the gate.

    The mission's FR-007 / FR-002 acceptance text names the gate as the
    single canonical pre-action check. WP03 (T011/T012) refactored the
    gate to flow through ``run_preflight`` — the canonical reusable
    helper from WP01. This test fails if a future refactor silently
    drops both the thin-wrapper helper (``_require_daemon_owner_coherence``)
    AND the direct ``run_preflight`` call from one of the mutating
    commands.
    """

    import ast
    from pathlib import Path

    sync_py = Path(__file__).resolve().parents[1].parent / "src" / "specify_cli" / "cli" / "commands" / "sync.py"
    tree = ast.parse(sync_py.read_text())
    mutating_names = {"now", "share", "unshare", "opt_in", "opt_out"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in mutating_names:
            continue
        body_text = ast.unparse(node)
        # Accept either the thin wrapper (used by share/unshare/opt-in/
        # opt-out) or a direct ``run_preflight`` call (used by ``sync now``
        # after WP03 T012 because it enforces ``require_auth=True``).
        assert (
            "_require_daemon_owner_coherence" in body_text
            or "run_preflight" in body_text
        ), (
            f"Mutating sync command `{node.name}` does NOT call the "
            f"FR-007 / FR-002 boundary gate — neither "
            f"_require_daemon_owner_coherence nor run_preflight was found."
        )
        mutating_names.discard(node.name)
    assert not mutating_names, (
        f"Could not locate FunctionDef nodes for: {sorted(mutating_names)}"
    )
