"""Golden-CLI characterization harness for ``spec-kitty sync`` (WP02).

This is the *safety net* the whole Wave-4 ``sync.py`` degod (WP03 -> WP12)
rests on. It freezes the **observable** contract of the ``sync`` Typer app --
each subcommand's flag set, exit code, and ``--json`` envelope *shape* -- by
driving :data:`specify_cli.cli.commands.sync.app` in-process through
:class:`typer.testing.CliRunner`. Every later extraction commit MUST keep these
snapshots green (INV-1): the harness lands *before* the first ``sync.py`` body
is relocated.

Design invariants (why the assertions look the way they do):

* **Assert exit code AND output shape; never volatile values.** Timestamps,
  SHAs, absolute paths, versions, PIDs, ULIDs, and environment-derived counts
  are redacted via :mod:`tests.characterization._normalize` before any
  comparison. For ``--json`` arms we assert the *key set* and value *types*, not
  the payload contents.
* **Hermetic + reproducible.** The autouse fixture pins
  ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` (the CORRECT enable var -- the misnamed
  ``SPEC_KITTY_SAAS_SYNC`` reads nothing and would silently freeze the *skip*
  arm, finding Pd-1), pairs it with ``SPEC_KITTY_SYNC_DISABLE=1`` (orthogonal:
  disables network/gate work, not render -- the hermetic-golden combo, Pd-5),
  isolates ``HOME``/``XDG_*`` to ``tmp_path``, pins UTF-8 capture for emoji
  glyphs, forces a wide console so Rich never soft-wraps a ``--json`` line, and
  ``chdir``\\s into a fresh non-repo directory so no snapshot depends on the
  developer's checkout, auth state, or ``~/.spec-kitty``.

Scope note (WP-translation guard #6): the four GAP commands whose *substantive*
render arms are frozen in their own extraction WPs are ``sync_workspace``
(WP11) and the ``diagnose`` full ``{total,valid,invalid,results:[...]}`` report
(intentionally never extracted -- post-tasks squad Rn-4). The cheap/deterministic
``--json`` arms that live on otherwise-safe surfaces (``status --check --json``,
``diagnose --json`` skip/empty) ARE frozen here. Per the load-bearing Rn-1
correction, ``status`` full human-render and ``doctor`` render are ALSO frozen
here (stubbing the pre-existing ``get_vcs`` / ``_check_server_connection`` /
``scan_sync_daemons`` seams) because the shared render helpers they exercise
(``_render_per_project_store`` / ``_render_consent_readability`` /
``_render_tracker_egress``) are churned by WP04/WP07 *before* the status/doctor
extraction WPs; freezing them only in WP09/WP10 would lock in a WP04/WP07
regression.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

import pytest
from click.testing import Result
from typer.testing import CliRunner

import specify_cli.cli.commands.sync as sync
import specify_cli.sync.background as sync_bg
import specify_cli.sync.daemon as sync_daemon
import specify_cli.sync.preflight as sync_preflight
import specify_cli.sync.queue as sync_queue
from specify_cli.cli.commands._auth_recovery import RecoveryOutcome
from specify_cli.cli.commands.sync import app
from specify_cli.delivery.dispatcher import DispatchSummary
from tests.characterization._normalize import normalize_envelope

# ---------------------------------------------------------------------------
# T006 -- the co-gate seam-callee set (INV-4).
#
# The ~79 existing tests that ``monkeypatch.setattr("...commands.sync.<name>",
# ...)`` are an explicit co-gate: after each WP03+ relocation these symbols MUST
# remain reachable as ``sync.<name>`` module attributes (via the late-bound
# ``sync_module.<name>`` convention established in WP03). This is the
# deduplicated ``<name>`` set (79 patch call-sites collapse to these 27 distinct
# callees), derived from a fresh grep of the test tree:
#
#     grep -rEo 'setattr\(\s*(sync_cmd|sync_module|sync_command|sync_mod)\s*,\s*
#         "[A-Za-z_]+"' tests/            # module-alias setattr form
#     grep -rEo 'commands\.sync\.[A-Za-z_]+' tests/   # string-patch / attr form
#
# Later WPs check their relocations against this live artifact (not prose in a
# research file). ``test_seam_callees_resolve_on_module`` keeps it executable.
SYNC_MONKEYPATCH_SEAM_NAMES: tuple[str, ...] = (
    "_EVENT_SYNC_DISPATCH_BATCH_LIMIT",
    "_assert_event_sync_runtime_authority",
    "_auto_converge_legacy_on_enable",
    "_check_server_connection",
    "_current_event_sync_scope",
    "_event_sync_access_token",
    "_event_sync_report",
    "_event_sync_retained_work_present",
    "_git_repair",
    "_load_event_sync_config",
    "_materialize_private_source_project",
    "_open_event_sync_runtime",
    "_open_journal_readonly",
    "_open_project_dispatch_runtime",
    "_require_active_checkout",
    "_require_daemon_owner_coherence",
    "_resolve_active_receiver",
    "_resolve_gated_receiver",
    "_resolve_history_import_receiver",
    "_run_consent_index_backfill",
    "_run_dispatch_batches",
    "_run_event_sync_dispatch",
    "enforce_teamspace_mission_state_ready",
    "get_vcs",
    "handle_unauthenticated_with_teamspace",
    "is_saas_sync_enabled",
    "tracker_egress_verdict",
)

# The 22 registered ``sync`` subcommands (their operator-facing names).
ALL_SUBCOMMANDS: tuple[str, ...] = (
    "routes",
    "share",
    "unshare",
    "opt-in",
    "opt-out",
    "import-history",
    "workspace",
    "server",
    "now",
    "gc",
    "archive",
    "purge",
    "project-store-preview",
    "project-store-migrate",
    "project-store-status",
    "project-store-quarantine",
    "project-store-history",
    "migrate",
    "mode",
    "status",
    "diagnose",
    "doctor",
)

# The core ``status --check --json`` envelope keys the contract freezes. Both the
# coherent (exit 0) and incoherent (exit 2) arms carry at least these; the exit-2
# arm additionally merges the seven additive event-sync sections (asserted as a
# superset, never an exact match, so an additive section is not a false regression).
STATUS_CHECK_CORE_KEYS: frozenset[str] = frozenset(
    {
        "ok",
        "exit_code",
        "auth_required",
        "auth_present",
        "remote_sync",
        "live_orphan_daemon_count",
        "daemon_scan_diagnostic",
        "foreground",
        "daemon_owner_record",
        "active_queue",
        "project_store_diagnostic",
        "legacy_queue",
        "mismatches",
        "orphan_records",
    }
)

runner = CliRunner()

pytestmark = [pytest.mark.fast]


@pytest.fixture(autouse=True)
def _hermetic_sync_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the CORRECT SaaS-enable var + HOME/XDG isolation + wide UTF-8 capture.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` reaches the non-skip render arms;
    ``SPEC_KITTY_SYNC_DISABLE=1`` keeps the golden hermetic (no real network/gate
    work). ``chdir(tmp_path)`` removes the developer checkout from the picture so
    exit codes are environment-independent (the canonical characterization
    pattern used across the sync test tree).
    """
    home = tmp_path / "home"
    for sub in ("", "cfg", "data", "state", "cache", "AppData"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / "cache"))
    monkeypatch.setenv("LOCALAPPDATA", str(home / "AppData"))
    # Pd-1: the enable var is SPEC_KITTY_ENABLE_SAAS_SYNC. The misnamed form must
    # never be what reaches the code -- delete it so a stray shell export cannot
    # silently freeze the skip arm.
    monkeypatch.delenv("SPEC_KITTY_SAAS_SYNC", raising=False)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setenv("SPEC_KITTY_SYNC_DISABLE", "1")
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    # Force a wide console so Rich never soft-wraps a ``console.print(json)`` line
    # (which would inject hard newlines into an otherwise single-line envelope).
    monkeypatch.setenv("COLUMNS", "1000")
    monkeypatch.chdir(tmp_path)


def invoke(*args: str) -> Result:
    """Drive the ``sync`` app in-process and return the click ``Result``."""
    return runner.invoke(app, list(args))


def _parse_json_arm(output: str) -> dict[str, Any]:
    """Decode a ``--json`` arm, tolerating Rich soft-wrap newlines.

    ``status --check --json`` writes straight to ``sys.stdout`` (never wrapped);
    the ``diagnose --json`` arms go through ``console.print`` and may be
    Rich-wrapped. Any literal newline in a single-object envelope is Rich's soft
    wrap (a real newline inside the JSON would be escaped as ``\\n``), so
    stripping newlines reconstructs a parseable object.
    """
    text = output.strip()
    try:
        parsed: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError:
        parsed = json.loads(text.replace("\n", ""))
    return parsed


def _norm(text: str, root: Path) -> str:
    """Redact volatile values (paths/SHAs/timestamps/PIDs/ULIDs) for comparison."""
    return normalize_envelope(text, root, str(Path.home()))


class _FakeUnit:
    def __enter__(self) -> _FakeUnit:
        return self

    def __exit__(self, *exc: object) -> Literal[False]:
        return False


class _FakeStore:
    database_path = Path("/fake/store.db")

    def unit_of_work(self) -> _FakeUnit:
        return _FakeUnit()

    def layout_generation(self) -> int:
        return 1


class _FakeRuntime:
    store = _FakeStore()

    def close(self) -> None:
        return None


class _FakeEmptyQueue:
    MAX_QUEUE_SIZE = 1000

    def __init__(self, *args: object, **kwargs: object) -> None:
        return None

    def drain_queue(self, limit: int | None = None) -> list[object]:
        return []


def _stub_render_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    """Freeze the render seams the Rn-1 status/doctor goldens depend on.

    ``get_vcs`` / ``_check_server_connection`` are ``sync`` module attributes;
    ``scan_sync_daemons`` / ``get_sync_daemon_status`` are re-imported locally
    inside the command bodies, so they are pinned on their source module.
    """
    zero_orphans = SimpleNamespace(orphan_count=0, orphan_processes=[])
    monkeypatch.setattr(sync_daemon, "scan_sync_daemons", lambda *a, **k: zero_orphans)
    monkeypatch.setattr(
        sync_daemon,
        "get_sync_daemon_status",
        lambda *a, **k: SimpleNamespace(
            healthy=False,
            url=None,
            pid=None,
            port=None,
            sync_running=False,
            websocket_status="Disconnected",
            last_sync=None,
            consecutive_failures=0,
        ),
    )
    monkeypatch.setattr(sync, "_check_server_connection", lambda url: ("[green]Connected[/green]", ""))
    monkeypatch.setattr(sync, "get_vcs", lambda *a, **k: None)


# ===========================================================================
# T005 -- flag matrix (the "not --json-happy-path-only" freeze, contract rule 1)
# ===========================================================================


@pytest.mark.parametrize("command", ALL_SUBCOMMANDS)
def test_help_renders_for_every_subcommand(command: str) -> None:
    """``--help`` is the deterministic flag-set freeze for all 22 subcommands."""
    result = invoke(command, "--help")
    assert result.exit_code == 0
    assert "Usage:" in result.output


def _declared_option_flags(command: str) -> set[str]:
    """The option flags a ``sync`` subcommand DECLARES, read from its function
    signature rather than from a rendered ``--help``.

    ``--help`` renders the *shared, process-global* ``sync.app``; a leaky sibling
    test elsewhere in a whole-tree shard can mutate that app object and strip a
    command's params, which manifests here as a phantom "lost <flag>" that never
    reproduces in isolation. The declared option set on the command's own
    function is the pollution-immune source of truth for this freeze (the render
    itself is still frozen by ``test_help_renders_for_every_subcommand``).

    Typer combines a boolean flag pair into a single ``"--flag/--no-flag"``
    declaration, so each ``param_decls`` entry is split on ``/`` to recover the
    individual flag tokens.
    """
    import inspect

    import typer

    func = getattr(sync, command)
    flags: set[str] = set()
    for param in inspect.signature(func).parameters.values():
        default = param.default
        if isinstance(default, typer.models.OptionInfo):
            for decl in default.param_decls or ():
                flags.update(token for token in decl.split("/") if token.startswith("-"))
    return flags


@pytest.mark.parametrize(
    ("command", "expected_flags"),
    [
        ("now", {"--report", "--strict", "--no-strict"}),
        ("mode", {"--endpoint"}),
        ("diagnose", {"--json"}),
        ("status", {"--check", "--json"}),
    ],
)
def test_flag_matrix_for_flagged_commands(command: str, expected_flags: set[str]) -> None:
    """The load-bearing option flags on each flagged surface are frozen.

    Asserted against the command's declared ``typer.Option`` set (see
    :func:`_declared_option_flags`) so a whole-tree-shard sibling that mutates the
    shared ``sync.app`` cannot produce a phantom "lost <flag>".
    """
    declared = _declared_option_flags(command)
    for flag in expected_flags:
        assert flag in declared, f"{command} lost {flag} (declared: {sorted(declared)})"


# The safe black-box matrix: (argv, expected_exit, stable_substring | None).
# Each arm is the deterministic outcome under the hermetic (non-repo cwd) env.
_SAFE_MATRIX: tuple[tuple[list[str], int, str | None], ...] = (
    (["routes"], 1, "Could not locate the active Spec Kitty checkout"),
    (["share"], 2, "Usage:"),  # missing required TEAM_SLUG argument
    (["unshare"], 2, "Usage:"),
    (["opt-in"], 2, "Refusing `spec-kitty sync opt-in`"),
    (["opt-out"], 2, "Refusing `spec-kitty sync opt-out`"),
    (["gc"], 1, "Retention unavailable"),
    (["archive"], 1, "Retention unavailable"),
    (["mode"], 0, "Event sync mode"),
    (["migrate"], 1, "shared-store"),
    (["project-store-preview"], 2, "Usage:"),  # missing required options
    (["project-store-migrate"], 2, "Usage:"),
    (["project-store-status"], 2, "Usage:"),
    (["project-store-quarantine"], 2, "Usage:"),
    (["project-store-history"], 1, None),  # emits a volatile dict repr; freeze exit only
    (["import-history"], 1, "Could not locate the active Spec Kitty checkout"),
    (["server"], 0, "Server URL"),
    (["diagnose"], 2, "Unable to diagnose sync queue"),
)


@pytest.mark.parametrize(("argv", "expected_exit", "substring"), _SAFE_MATRIX)
def test_safe_subcommand_exit_and_shape(argv: list[str], expected_exit: int, substring: str | None, tmp_path: Path) -> None:
    """Freeze exit code (+ a stable, redacted output marker) for safe surfaces."""
    result = invoke(*argv)
    assert result.exit_code == expected_exit, result.output
    if substring is not None:
        assert substring in _norm(result.output, tmp_path)


# ===========================================================================
# T005 -- ``now`` (contract item 5): the four exit arms
# ===========================================================================


def test_now_preflight_refuses_exit_2() -> None:
    """The FR-002 structural preflight refuses (exit 2) before any enqueue."""
    result = invoke("now")
    assert result.exit_code == 2
    assert "Refusing `spec-kitty sync now`" in result.output


def test_now_saas_disabled_silent_skip_exit_0(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract item 7 -- the coord exit-0 silent-skip arm.

    With the boundary preflight satisfied but SaaS sync disabled, ``now`` prints
    the disabled notice and returns ``Exit(0)`` -- it must never be "cleaned up"
    into an error. Freeze the exact print + exit-0 behaviour.
    """
    monkeypatch.setattr(sync_preflight, "run_preflight", lambda *a, **k: SimpleNamespace(ok=True, render=lambda c: None))
    monkeypatch.setattr(sync, "is_saas_sync_enabled", lambda: False)
    result = invoke("now")
    assert result.exit_code == 0
    assert "SPEC_KITTY_ENABLE_SAAS_SYNC" in result.output


def _stub_now_dispatch_to_recovery(monkeypatch: pytest.MonkeyPatch, outcome: RecoveryOutcome) -> None:
    """Route ``now`` past preflight into the unauthenticated-recovery branch."""
    monkeypatch.setattr(sync_preflight, "run_preflight", lambda *a, **k: SimpleNamespace(ok=True, render=lambda c: None))
    monkeypatch.setattr(sync, "enforce_teamspace_mission_state_ready", lambda **k: None)
    monkeypatch.setattr(sync, "_event_sync_retained_work_present", lambda: True)
    monkeypatch.setattr(
        sync_bg,
        "get_sync_service",
        lambda *a, **k: SimpleNamespace(queue=SimpleNamespace(size=lambda: 1), drain_body_uploads_only=lambda: None),
    )
    # A summary that selected work but made no durable progress (recorded == 0)
    # is the dispatch analogue of the legacy per-event unauthenticated result --
    # it routes through the teamspace-aware recovery handler.
    summary = DispatchSummary(target_id=None, selected=1, delivered=0, duplicate=0, pending=0, rejected=0, transient=0, terminal_failed=0)
    monkeypatch.setattr(sync, "_run_event_sync_dispatch", lambda: summary)
    monkeypatch.setattr(sync, "handle_unauthenticated_with_teamspace", lambda **k: outcome)


def test_now_unauthenticated_exit_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unauthenticated with no connected teamspace -> legacy strict exit 1."""
    _stub_now_dispatch_to_recovery(monkeypatch, RecoveryOutcome.NO_TEAMSPACE)
    result = invoke("now")
    assert result.exit_code == 1


def test_now_logged_out_on_connected_teamspace_exit_4(monkeypatch: pytest.MonkeyPatch) -> None:
    """Logged-out on a connected teamspace -> EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE (4)."""
    _stub_now_dispatch_to_recovery(monkeypatch, RecoveryOutcome.EXIT_4)
    result = invoke("now")
    assert result.exit_code == 4


# ===========================================================================
# T005 -- ``status --check --json`` (contract item 1): both exit arms
# ===========================================================================


def test_status_check_json_incoherent_exit_2() -> None:
    """SAAS enabled + no auth -> single JSON envelope, exit 2, human block suppressed."""
    result = invoke("status", "--check", "--json")
    assert result.exit_code == 2
    payload = _parse_json_arm(result.output)
    assert set(payload) >= STATUS_CHECK_CORE_KEYS
    assert payload["ok"] is False
    assert payload["exit_code"] == 2
    assert isinstance(payload["foreground"], dict)
    assert isinstance(payload["mismatches"], list)


def test_status_check_json_coherent_exit_0(monkeypatch: pytest.MonkeyPatch) -> None:
    """A coherent boundary (no orphans, auth not required, store available) -> exit 0."""
    fake_fg = SimpleNamespace(
        package_version="0.0.0",
        executable_path=Path("/x"),
        source_path=Path("/y"),
        server_url="https://s",
        team_or_user="u",
        queue_db_path=Path("/q"),
        pid=1,
    )
    fake_fs = SimpleNamespace(
        ok=True,
        foreground=fake_fg,
        daemon_record=None,
        daemon_status="none",
        project_store_diagnostic=None,
        legacy_event_rows=0,
        legacy_body_upload_rows=0,
        legacy_rows_for_scope=0,
        mismatches=[],
        orphan_records=[],
    )
    monkeypatch.setattr(sync_preflight, "build_boundary_failure_set", lambda *a, **k: fake_fs)
    monkeypatch.setattr(sync_daemon, "scan_sync_daemons", lambda *a, **k: SimpleNamespace(orphan_count=0, orphan_processes=[]))
    monkeypatch.setattr(sync, "is_saas_sync_enabled", lambda: False)

    def _fake_report(payload: dict[str, Any], runtime: object) -> dict[str, Any]:
        payload = dict(payload)
        payload["event_journal"] = {"retained_event_count": 0}
        payload["body_upload_compatibility"] = {"body_upload_queue_count": 0}
        return payload

    monkeypatch.setattr(sync, "_open_event_sync_runtime_readonly", lambda *a, **k: _FakeRuntime())
    monkeypatch.setattr(sync, "_event_sync_report", _fake_report)

    result = invoke("status", "--check", "--json")
    assert result.exit_code == 0
    payload = _parse_json_arm(result.output)
    assert set(payload) >= STATUS_CHECK_CORE_KEYS
    assert payload["ok"] is True
    assert payload["exit_code"] == 0


# ===========================================================================
# T005 -- ``diagnose --json`` (contract item 6): the two cheap deterministic arms
# ===========================================================================


def test_diagnose_json_store_unavailable_exit_2() -> None:
    """Store unavailable -> ``{available:false, error, results:[]}`` at exit 2."""
    result = invoke("diagnose", "--json")
    assert result.exit_code == 2
    payload = _parse_json_arm(result.output)
    assert set(payload) == {"available", "error", "results"}
    assert payload["available"] is False
    assert payload["results"] == []


def test_diagnose_json_empty_queue_exit_0(monkeypatch: pytest.MonkeyPatch) -> None:
    """Store available but empty -> ``{total:0, valid:0, invalid:0, results:[]}`` at exit 0."""
    monkeypatch.setattr(sync, "_open_event_sync_runtime", lambda *a, **k: _FakeRuntime())
    monkeypatch.setattr(sync_queue, "OfflineQueue", _FakeEmptyQueue)
    monkeypatch.setattr(sync_queue, "get_max_queue_size", lambda: 1000)
    result = invoke("diagnose", "--json")
    assert result.exit_code == 0
    payload = _parse_json_arm(result.output)
    assert set(payload) == {"total", "valid", "invalid", "results"}
    assert payload["total"] == 0
    assert payload["results"] == []


# ===========================================================================
# Rn-1 (the load-bearing fix) -- freeze the ``status`` full human-render AND the
# ``doctor`` render NOW, so a WP04/WP07 churn of the shared render helpers cannot
# regress unnoticed. WP09/WP10 later *verify* these; they do not re-freeze.
# ===========================================================================


def test_status_full_human_render_frozen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Snapshot the full ``status`` table (no ``--check``) + exit code.

    Stubs the pre-existing render seams to fixed values; the SaaS-enable var is
    live (Pd-1) so we exercise the non-skip arm -- a snapshot showing only the
    "sync disabled" skip text would be a frozen-wrong-arm defect.
    """
    _stub_render_seams(monkeypatch)
    result = invoke("status")
    assert result.exit_code == 0
    rendered = _norm(result.output, tmp_path)
    for marker in (
        "Spec Kitty Sync Status",
        "SaaS Sync",
        "Enabled",  # proves the non-skip arm was reached
        "Daemon",
        "Sync Mode",
        "WebSocket",
        "Auth",
        "Server URL",
        "Config File",
        "Queue empty",
        "Identity Boundary",
    ):
        assert marker in rendered, f"status full render lost {marker!r}"


def test_doctor_render_frozen_unhealthy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Snapshot the ``doctor`` Rich table + the three shared-helper blocks + summary.

    ``doctor`` takes no args and has no ``--json`` (Pd-3). The three churned
    render helpers (``_render_per_project_store`` / ``_render_consent_readability``
    / ``_render_tracker_egress``) all render here -- this is the byte-stable net
    WP04/WP07 must keep green.
    """
    _stub_render_seams(monkeypatch)
    result = invoke("doctor")
    assert result.exit_code == 0
    rendered = _norm(result.output, tmp_path)
    for marker in (
        "Sync Doctor",
        "Server URL",
        "Auth",
        "Consent record readability",  # _render_consent_readability
        "Tracker egress",  # _render_tracker_egress
    ):
        assert marker in rendered, f"doctor render lost {marker!r}"
    # Unhealthy summary (the store is unavailable in the hermetic env, so the
    # queue-health check appends an issue). The alternate "No issues detected.
    # Sync is healthy." branch requires a fully-consented project fixture and is
    # verified by WP10's doctor-extraction golden.
    assert "Issues found:" in rendered


def test_doctor_logged_out_on_connected_teamspace_exit_4(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ``EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE`` (exit 4) recovery arm of ``doctor``."""
    _stub_render_seams(monkeypatch)
    monkeypatch.setattr(sync, "handle_unauthenticated_with_teamspace", lambda **k: RecoveryOutcome.EXIT_4)
    result = invoke("doctor")
    assert result.exit_code == 4


def test_doctor_no_teamspace_recovery_exit_0(monkeypatch: pytest.MonkeyPatch) -> None:
    """No connected teamspace -> ``doctor`` completes at exit 0 despite surfacing issues."""
    _stub_render_seams(monkeypatch)
    monkeypatch.setattr(sync, "handle_unauthenticated_with_teamspace", lambda **k: RecoveryOutcome.NO_TEAMSPACE)
    result = invoke("doctor")
    assert result.exit_code == 0


# ===========================================================================
# T006 -- the seam-callee set is a live, executable co-gate baseline (INV-4)
# ===========================================================================


# ===========================================================================
# FR-014 (mission sync-deactivate-by-default) -- the deactivated/no-op arm.
#
# Every arm above self-pins ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` via the autouse
# fixture, so they exercise the ENABLED render path. FR-014 requires the golden
# to ALSO freeze the default-off contract: with sync inactive, the ``sync`` CLI
# must still LOAD and REPORT its inactive posture (a read-only no-op) rather than
# perform sync work or crash. This arm clears the sync env in the test body
# (which runs after the autouse fixture, so it deterministically wins) to put the
# process in the sync_disabled posture.
# ===========================================================================

_SYNC_POSTURE_ENV_VARS = (
    "SPEC_KITTY_ENABLE_SAAS_SYNC",
    "SPEC_KITTY_SYNC_DISABLE",
    "SPEC_KITTY_SYNC_MINIMAL_IMPORT",
)


def _force_sync_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear every SaaS-sync env var so ``sync_active()`` reads False.

    Runs in the test body, after the autouse ``_hermetic_sync_env`` fixture, so
    it overrides that fixture's ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` pin -- the
    canonical ``sync_disabled`` posture from ``tests/conftest.py``.
    """
    for var in _SYNC_POSTURE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_status_reports_inactive_when_sync_off(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """FR-014 inactive arm: ``sync status`` still loads and reports the disabled
    posture (exit 0, read-only no-op) when SaaS sync is off.

    A snapshot showing the ENABLED row here would be a frozen-wrong-arm defect --
    the mirror of the Pd-1 concern the opt-in arms guard against.
    """
    _force_sync_inactive(monkeypatch)
    _stub_render_seams(monkeypatch)
    result = invoke("status")
    assert result.exit_code == 0, result.output
    rendered = _norm(result.output, tmp_path)
    assert "Spec Kitty Sync Status" in rendered, "the status surface must still load"
    assert "Disabled" in rendered, "the SaaS Sync row must report the inactive posture"
    # The honest disabled notice names the opt-in env var (saas_sync_disabled_message).
    assert "SPEC_KITTY_ENABLE_SAAS_SYNC" in rendered, "must tell the operator how to opt in"


def test_now_reports_inactive_and_no_ops_when_sync_off(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """FR-014 inactive arm: with the preflight satisfied but sync off, ``now``
    prints the disabled notice and returns exit 0 -- it performs no sync work.

    Complements ``test_now_saas_disabled_silent_skip_exit_0`` (which monkeypatches
    ``is_saas_sync_enabled``): this drives the real env-var posture end to end.
    """
    _force_sync_inactive(monkeypatch)
    monkeypatch.setattr(sync_preflight, "run_preflight", lambda *a, **k: SimpleNamespace(ok=True, render=lambda c: None))
    result = invoke("now")
    assert result.exit_code == 0, result.output
    rendered = _norm(result.output, tmp_path)
    assert "SPEC_KITTY_ENABLE_SAAS_SYNC" in rendered, "the disabled notice must name the opt-in var"


@pytest.mark.parametrize("seam_name", SYNC_MONKEYPATCH_SEAM_NAMES)
def test_seam_callees_resolve_on_module(seam_name: str) -> None:
    """Every documented seam MUST resolve as a ``sync.<name>`` attribute today.

    This is the pre-decomposition truth WP03+ must preserve after relocation: a
    relocated symbol that stops resolving as ``sync.<name>`` breaks the ~79
    monkeypatch call-sites that target it.
    """
    assert hasattr(sync, seam_name), f"seam callee {seam_name!r} no longer resolves on the sync module"
