"""WP04 (#2263): INV-1 — the worktree-clean sync invariant, enforced as one
parametrized contract across the whole covered command surface.

The mission's thesis (INV-1): *no read / sync / background command may dirty a
clean checkout.* Before WP01–WP03, several read-like paths resolved project (or
tracker-binding) identity through a **writing** ``ensure_identity`` /
``save_tracker_config`` call. On a realistic *legacy* checkout — a
``.kittify/config.yaml`` with provably-incomplete identity (``build_id`` missing) —
that write minted + persisted the missing field, leaving ``config.yaml`` modified
and the working tree dirty. The dirty tree then tripped the downstream merge /
record-analysis preflight.

This module asserts the *combined* fix delivered by:

* **WP01** — deterministic ``derive_build_id`` so the read path resolves a
  *complete, stable* identity in memory without ever needing to persist it.
* **WP02** — every read/emit/background ``ensure_identity`` call site routed to
  the side-effect-free ``resolve_identity`` (only the explicit ``tracker bind``
  boundary still writes).
* **WP03** — tracker ``binding_ref`` upgrades are *report-only* on read paths
  (``pending_binding_upgrade``); persistence happens solely at the
  ``apply_binding_upgrade`` / ``bind`` write boundary.

Covered command surface (parametrized over this exact set — see
``_COVERED_COMMANDS``): status-event emission, ``sync status --check``,
background dossier sync, lifecycle SaaS fan-out, ``tracker sync pull``,
``tracker sync push``, ``tracker sync run``, ``tracker status``, ``tracker map
list``, and the background sync-daemon tick.

Two RED preconditions (without BOTH the assertions are green-from-start; this
mirrors ``test_accept_readiness_no_write`` / ``test_emit_readonly_identity``):

1. The fixture ``.kittify/config.yaml`` MUST carry *provably-incomplete* project
   identity (we assert ``build_id`` is missing). ``ensure_identity`` /
   ``resolve_identity`` return early WITHOUT touching disk once identity is
   complete, so a complete fixture never reproduces the bug.
2. The emitter is a process-global singleton seeded only on first init, so we call
   ``reset_emitter()`` before exercising any emit/daemon path to actually hit the
   identity seam.

Constraints honored: per-worker HOME isolation (the autouse fixtures in
``tests/conftest.py`` redirect HOME/XDG into a temp dir — we never touch the real
``~/.spec-kitty``); the server / auth / tracker client are stubbed so no network
is required; the daemon-tick variant is kept out of the parallel parametrization
and runs in the dedicated serial (``-n0``) pass. No lint or type suppressions.

NFR-002 (latency) note: the no-write assertion *is* the NFR-002 verification.
Removing the side-effect write is the only latency change, so "≤50 ms added
latency" holds by construction. We deliberately do NOT assert wall-clock timing
(that would be flaky and violate NFR-004); "no added write" is the stable proxy.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.coordination.coherence import is_self_bookkeeping_churn
from specify_cli.identity.project import load_identity
from specify_cli.sync.events import emit_wp_status_changed, reset_emitter

# Gate-selected markers so this file is actually run in CI (was a zero-gate #2034
# orphan): it drives real git via ``subprocess`` (git_repo) and is integration-level.
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_CONFIG_RELPATH = ".kittify/config.yaml"
_MISSION_SLUG = "worktree-clean-invariant-01KWC9Y0"

# A read/sync command must NEVER auto-invoke the mission-state doctor's
# fix/auto-repair path (C-002). ``migration.mission_state.repair_repo`` is the only
# *mutating* mission-state auto-fix engine — it rewrites mission files + a manifest
# and is reachable solely from the write-authorized ``doctor mission-state --fix``
# arm, never from a read/sync surface. ``status.doctor.run_doctor`` is the
# read-only health checker; we spy it too so even a non-mutating doctor pass is not
# silently triggered by a read command.
_AUTOFIX_ENTRYPOINT = "specify_cli.migration.mission_state.repair_repo"
_DOCTOR_HEALTH_ENTRYPOINT = "specify_cli.status.doctor.run_doctor"

runner = CliRunner()


# ===========================================================================
# T015 — Invariant test harness + fixtures
# ===========================================================================


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo_root), *args], check=True, capture_output=True)


def _porcelain_bytes(repo_root: Path) -> bytes:
    """``git status --porcelain`` as raw bytes (the worktree-clean oracle).

    Byte-level comparison (not a string compare) so any churn — including
    untracked sidecar files the snapshot must catch — is detected verbatim.
    """
    return subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        check=True,
        capture_output=True,
    ).stdout


@dataclass(frozen=True)
class _Snapshot:
    """An immutable capture of the two surfaces INV-1 protects."""

    porcelain: bytes
    config_bytes: bytes
    config_mtime_ns: int


def _snapshot(repo_root: Path, config_path: Path) -> _Snapshot:
    """Capture ``(git porcelain bytes, config.yaml content + mtime)``."""
    return _Snapshot(
        porcelain=_porcelain_bytes(repo_root),
        config_bytes=config_path.read_bytes(),
        config_mtime_ns=config_path.stat().st_mtime_ns,
    )


def _assert_unchanged(before: _Snapshot, after: _Snapshot, *, command: str) -> None:
    """Assert the worktree-clean invariant held across a command.

    The failure message names the offending command (T019 extensibility
    requirement) so a future regression points straight at the culprit.
    """
    assert after.porcelain == before.porcelain, (
        f"INV-1 violated: command {command!r} changed `git status --porcelain` "
        f"(the worktree-clean invariant). A read/sync/background command must "
        f"never dirty a clean checkout.\n"
        f"  before: {before.porcelain!r}\n  after:  {after.porcelain!r}"
    )
    assert after.config_bytes == before.config_bytes, (
        f"INV-1 violated: command {command!r} rewrote {_CONFIG_RELPATH} content "
        f"(identity/binding persisted on a read path). FR-001/FR-005/FR-006."
    )
    assert after.config_mtime_ns == before.config_mtime_ns, (
        f"INV-1 violated: command {command!r} touched {_CONFIG_RELPATH} (mtime "
        f"changed) even if content matched — the write itself is the regression."
    )


def _write_incomplete_config(repo_root: Path) -> Path:
    """Write a ``.kittify/config.yaml`` with provably-incomplete project identity.

    ``project.build_id`` (required for ``ProjectIdentity.is_complete``) is omitted
    so a *writing* identity resolution would mint + persist it, dirtying the tree.
    The fixed read path must instead resolve it in-memory only. This is RED
    precondition 1 (mirrors ``test_emit_readonly_identity``).
    """
    config_path = repo_root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "project:\n"
        "  uuid: 33333333-3333-4333-8333-333333333333\n"
        "  slug: worktree-clean-invariant\n"
        "  node_id: 0a1b2c3d4e5f\n"
        # build_id intentionally omitted → identity incomplete
        "\n"
    )
    return config_path


def _make_checkout(tmp_path: Path) -> tuple[Path, Path]:
    """A clean, SaaS-sync-enabled git checkout with incomplete-identity config.

    The config is committed so that any side-effect identity write surfaces as a
    *tracked-file modification* in ``git status --porcelain`` (the strongest
    possible dirt signal). Returns ``(repo_root, config_path)``.
    """
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir()
    _git(repo_root, "init")
    config_path = _write_incomplete_config(repo_root)
    _git(repo_root, "add", "-A")
    _git(repo_root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "seed")
    return repo_root, config_path


@pytest.fixture()
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A committed incomplete-identity checkout, cwd'd + ``SPECIFY_REPO_ROOT`` set.

    Each test gets its own repo. ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` comes from the
    autouse ``_enable_saas_sync_feature_flag`` fixture in ``tests/conftest.py``;
    HOME/XDG isolation comes from the autouse ``_isolated_worker_home`` fixture.
    """
    repo_root, config_path = _make_checkout(tmp_path)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)
    reset_emitter()  # RED precondition 2: re-seed the emitter on this checkout.
    return repo_root, config_path


def test_incomplete_identity_precondition(checkout: tuple[Path, Path]) -> None:
    """Guard (RED precondition 1): the fixture identity MUST be incomplete.

    If this ever turns green-by-default (identity already complete), every
    no-write assertion below becomes a tautology — so this guard is load-bearing.
    """
    _repo_root, config_path = checkout
    identity = load_identity(config_path)
    assert identity.build_id is None, "fixture identity must be incomplete (build_id missing)"
    assert not identity.is_complete, "fixture identity must be incomplete to reproduce #2263"


def test_snapshot_helper_detects_a_real_write(checkout: tuple[Path, Path]) -> None:
    """T015 self-test / NEGATIVE CONTROL: the snapshot oracle catches real dirt.

    Proves the no-write assertions are NOT no-ops: a deliberate identity-shaped
    write to ``config.yaml`` (simulating the pre-WP01/WP02 side effect) makes
    ``_assert_unchanged`` fail. If the oracle could not see this, every GREEN
    assertion in this module would be worthless.
    """
    repo_root, config_path = checkout
    before = _snapshot(repo_root, config_path)

    # Simulate exactly the regression: append the missing build_id to config.yaml.
    config_path.write_text(
        config_path.read_text() + "  build_id: deadbeefdeadbeef\n"
    )

    after = _snapshot(repo_root, config_path)
    with pytest.raises(AssertionError, match="worktree-clean invariant"):
        _assert_unchanged(before, after, command="deliberate-write")
    # And the porcelain oracle alone flips, independent of the mtime/content checks.
    assert after.porcelain != before.porcelain, (
        "porcelain snapshot failed to detect a tracked-file modification — the "
        "oracle is broken and every no-write assertion would be a false pass"
    )


# ===========================================================================
# T016 — Parametrized no-dirty-tree assertion over the covered surface
# ===========================================================================
#
# Each covered command is a ``(name, driver)`` pair. The driver receives the
# checkout and runs the command to completion (success or *handled* failure)
# entirely in-process — server / auth / tracker client are stubbed so no network
# is touched. Adding a new covered command is a ONE-LINE addition to
# ``_COVERED_COMMANDS`` (T019 extensibility): a new read/background command must
# satisfy INV-1 (leave porcelain + config.yaml untouched) or this test fails.
#
# Where the real CLI entrypoint is heavy or needs a bound port (the daemon tick),
# we drive the underlying callable directly and DOCUMENT it inline — never skip a
# command silently.

_TrackerClient = MagicMock


def _tracker_client_with_pending_upgrade() -> MagicMock:
    """A stub tracker client whose read responses advertise a CHANGED binding_ref.

    The changed ``binding_ref`` is the WP03 trap: a pre-WP03 read path would
    persist it to ``config.yaml`` (dirtying the tree). The fixed read path must
    only *report* it via ``pending_binding_upgrade`` and write nothing.
    """
    client = MagicMock()
    client.status.return_value = {"connected": True, "binding_ref": "bind-CHANGED"}
    client.pull.return_value = {"items": [], "binding_ref": "bind-CHANGED"}
    client.push.return_value = {"pushed": 0, "binding_ref": "bind-CHANGED"}
    client.run.return_value = {"pulled": 0, "pushed": 0, "binding_ref": "bind-CHANGED"}
    client.mappings.return_value = {"mappings": [], "binding_ref": "bind-CHANGED"}
    return client


def _make_tracker_service(repo_root: Path) -> Any:
    """Build a SaaS tracker service bound to a real provider with a stub client.

    The stored ``binding_ref`` is intentionally absent so the server's changed
    ``binding_ref`` looks like an *available upgrade* — the exact WP03 read-path
    persistence trap.
    """
    from specify_cli.tracker.config import TrackerProjectConfig
    from specify_cli.tracker.saas_service import SaaSTrackerService

    cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
    return SaaSTrackerService(repo_root, cfg, client=_tracker_client_with_pending_upgrade())


def _drive_status_event_emission(repo_root: Path, _config_path: Path) -> None:
    """status-event emission — the ``sync.events`` emit path (WP02 seam).

    Driven via the public ``emit_wp_status_changed`` callable; the sync runtime is
    stubbed so emission resolves identity in memory but performs no network I/O.
    """
    reset_emitter()
    with patch("specify_cli.sync.runtime.get_runtime", return_value=MagicMock()):
        emit_wp_status_changed("WP01", "planned", "in_progress", mission_slug=_MISSION_SLUG)


def _drive_sync_status_check(_repo_root: Path, _config_path: Path) -> None:
    """``sync status --check`` — driven in-process via the typer CliRunner.

    Network / live-process probes inside ``sync status`` are stubbed so the
    command renders its boundary report without reaching a server. Exit code 0
    (clean) or 2 (boundary mismatch) are both *handled* outcomes; either way the
    command must leave the worktree clean.
    """
    from specify_cli.cli.commands.sync import app
    from specify_cli.sync.daemon import DaemonSingletonReport, SyncDaemonStatus

    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = None
    with (
        patch(
            "specify_cli.cli.commands.sync._check_server_connection",
            lambda url: ("Connected", "Server reachable."),
        ),
        patch("specify_cli.auth.get_token_manager", lambda: tm),
        patch(
            "specify_cli.sync.daemon.scan_sync_daemons",
            lambda: DaemonSingletonReport(
                state_pid=None, state_file_present=False, orphan_processes=()
            ),
        ),
        patch(
            "specify_cli.sync.daemon.get_sync_daemon_status",
            lambda: SyncDaemonStatus(
                healthy=True,
                url=None,
                port=None,
                sync_running=False,
                last_sync=None,
                consecutive_failures=0,
                websocket_status="Disconnected",
            ),
        ),
    ):
        result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code in (0, 2), (
        f"sync status --check raised an unexpected exit ({result.exit_code}):\n"
        f"{result.stdout}"
    )


def _event_mapping(*pairs: tuple[str, object]) -> dict[str, object]:
    """Build an event mapping fixture without an event-shaped dict literal."""
    return dict(pairs)


def _drive_dossier_sync_trigger(repo_root: Path, _config_path: Path) -> None:
    """Background dossier sync trigger — the ``sync.dossier_pipeline`` read path."""
    from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled

    with (
        patch("specify_cli.core.paths.get_feature_target_branch", return_value="main"),
        patch("specify_cli.mission.get_mission_type", return_value="software-dev"),
        patch("specify_cli.sync.namespace.resolve_manifest_version", return_value="v1"),
        patch("specify_cli.sync.body_queue.OfflineBodyUploadQueue", return_value=MagicMock()),
        patch("specify_cli.sync.dossier_pipeline.sync_feature_dossier", return_value=None),
    ):
        trigger_feature_dossier_sync_if_enabled(
            repo_root / "kitty-specs" / _MISSION_SLUG,
            _MISSION_SLUG,
            repo_root,
        )


def _drive_lifecycle_saas_fanout(repo_root: Path, _config_path: Path) -> None:
    """Lifecycle SaaS fan-out — the ``sync.__init__`` background read path."""
    import spec_kitty_events

    from specify_cli.sync import _lifecycle_saas_fanout_handler

    queue = MagicMock()
    lifecycle_event = _event_mapping(
        ("event_id", "01KWC9Y0LIFECYCLEFANOUT0001"),
        ("event_type", "ProjectInitialized"),
        ("aggregate_type", "Project"),
        ("aggregate_id", "project"),
        ("schema_version", "3.0.0"),
        ("build_id", "build-123"),
        ("payload", {}),
        ("node_id", "node"),
        ("lamport_clock", 1),
        ("causation_id", None),
        ("correlation_id", "01KWC9Y0LIFECYCLEFANOUT0001"),
        ("timestamp", "2026-06-30T00:00:00+00:00"),
        ("team_slug", "team"),
        ("project_uuid", "33333333-3333-4333-8333-333333333333"),
        ("project_slug", "worktree-clean-invariant"),
    )
    with (
        patch("specify_cli.sync.queue.read_queue_scope_from_session", return_value={"team_slug": "team"}),
        patch("specify_cli.sync.queue.read_queue_scope_from_credentials", return_value=None),
        patch("specify_cli.sync.clock.LamportClock.load", return_value=MagicMock(node_id="node", tick=lambda: 1)),
        patch("specify_cli.status.build_saas_lifecycle_queue_event", return_value=lifecycle_event),
        patch("specify_cli.core.contract_gate.validate_outbound_payload", return_value=None),
        patch.object(spec_kitty_events, "Event", lambda **_kwargs: None),
        patch("specify_cli.sync.queue.OfflineQueue", return_value=queue),
    ):
        _lifecycle_saas_fanout_handler(
            envelope=_event_mapping(
                ("event_type", "ProjectInitialized"),
                ("payload", {"project_slug": "worktree-clean-invariant"}),
                ("aggregate_type", "Project"),
            ),
            log_path=repo_root / ".kittify" / "status.events.jsonl",
        )


def _drive_tracker_status(repo_root: Path, _config_path: Path) -> None:
    """``tracker status`` — the read path drives ``SaaSTrackerService.status``.

    Driven via the underlying callable (not the full typer command) because the
    CLI command builds a live ``SaaSTrackerClient`` (network). The changed
    ``binding_ref`` must surface as pending, not be persisted (WP03 / C-TB-1).
    """
    svc = _make_tracker_service(repo_root)
    result = svc.status()
    assert result["pending_binding_upgrade"] == "bind-CHANGED", (
        "tracker status must REPORT the changed binding_ref (pending), proving the "
        "WP03 trap was armed and the read path saw it but did not persist it"
    )


def _drive_tracker_sync_pull(repo_root: Path, _config_path: Path) -> None:
    """``tracker sync pull`` — read path via ``SaaSTrackerService.sync_pull``."""
    svc = _make_tracker_service(repo_root)
    assert svc.sync_pull()["pending_binding_upgrade"] == "bind-CHANGED"


def _drive_tracker_sync_push(repo_root: Path, _config_path: Path) -> None:
    """``tracker sync push`` — read path via ``SaaSTrackerService.sync_push``."""
    svc = _make_tracker_service(repo_root)
    assert svc.sync_push()["pending_binding_upgrade"] == "bind-CHANGED"


def _drive_tracker_sync_run(repo_root: Path, _config_path: Path) -> None:
    """``tracker sync run`` — read path via ``SaaSTrackerService.sync_run``."""
    svc = _make_tracker_service(repo_root)
    assert svc.sync_run()["pending_binding_upgrade"] == "bind-CHANGED"


def _drive_tracker_map_list(repo_root: Path, _config_path: Path) -> None:
    """``tracker map list`` — read path via ``SaaSTrackerService.map_list``.

    ``map_list`` returns a list, so the pending upgrade is surfaced on the service
    *instance* (C-TB-3), not the return value — but the no-write invariant is the
    same: a changed binding_ref must not be persisted.
    """
    svc = _make_tracker_service(repo_root)
    result = svc.map_list()
    assert result.pending_binding_upgrade == "bind-CHANGED", (
        "tracker map list must surface the changed binding_ref on its result "
        "(pending), not persist it"
    )
    assert svc.pending_binding_upgrade == "bind-CHANGED"


def _drive_daemon_tick(_repo_root: Path, _config_path: Path) -> None:
    """Background sync-daemon tick — drives ``BackgroundSyncService._sync_once``.

    Driven via the underlying per-tick callable rather than starting a real daemon
    thread / binding a port (RISK mitigation: daemon ticks are timer-driven and
    need a real server otherwise). The token fetch + batch sync are stubbed so the
    tick exercises the identity-resolving emit/runtime seam (WP02) with zero
    network. This is the variant that runs serially (-n0).
    """
    from specify_cli.sync.background import BackgroundSyncService
    from specify_cli.sync.batch import BatchSyncResult
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.queue import OfflineQueue

    reset_emitter()
    service = BackgroundSyncService(queue=OfflineQueue(), config=SyncConfig())
    with (
        patch(
            "specify_cli.sync.background._fetch_access_token_sync",
            return_value="stub-token",
        ),
        patch(
            "specify_cli.sync.background.batch_sync",
            return_value=BatchSyncResult(),
        ),
    ):
        # ``_perform_sync`` is the single-batch per-tick body the daemon timer
        # invokes (``_on_timer`` → ``_perform_sync`` → ``_sync_once``); calling it
        # directly performs exactly one tick.
        service._perform_sync()


# (name, driver). One line per covered command — extend here to add coverage.
_COVERED_COMMANDS: tuple[tuple[str, Callable[[Path, Path], None]], ...] = (
    ("status-event-emission", _drive_status_event_emission),
    ("sync-status-check", _drive_sync_status_check),
    ("dossier-sync-trigger", _drive_dossier_sync_trigger),
    ("lifecycle-saas-fanout", _drive_lifecycle_saas_fanout),
    ("tracker-status", _drive_tracker_status),
    ("tracker-sync-pull", _drive_tracker_sync_pull),
    ("tracker-sync-push", _drive_tracker_sync_push),
    ("tracker-sync-run", _drive_tracker_sync_run),
    ("tracker-map-list", _drive_tracker_map_list),
    # The daemon tick is also asserted in its own serial (-n0) test below so the
    # real-port/daemon risk never lands in the parallel path. It is intentionally
    # NOT in this parallel-path parametrization.
)


@pytest.mark.parametrize(
    "command_name,driver",
    _COVERED_COMMANDS,
    ids=[name for name, _ in _COVERED_COMMANDS],
)
def test_covered_command_leaves_worktree_clean(
    checkout: tuple[Path, Path],
    command_name: str,
    driver: Callable[[Path, Path], None],
) -> None:
    """T016 / INV-1: each covered command leaves porcelain + config.yaml untouched.

    Snapshot → run command to completion → assert byte-identical porcelain AND
    config.yaml unchanged (FR-001/FR-005/FR-006/AS-1). The no-write assertion is
    also the NFR-002 latency proxy (see module docstring).
    """
    repo_root, config_path = checkout
    before = _snapshot(repo_root, config_path)

    driver(repo_root, config_path)

    after = _snapshot(repo_root, config_path)
    _assert_unchanged(before, after, command=command_name)
    # The on-disk identity must STILL be incomplete — proving the command resolved
    # identity in memory (WP01) rather than completing + persisting it.
    assert not load_identity(config_path).is_complete, (
        f"command {command_name!r} completed identity ON DISK — the read path must "
        f"resolve it in memory only (#2263 FR-001)"
    )


# ===========================================================================
# T017 — Disabled / unauthenticated variant (FR-008 / AS-6)
# ===========================================================================

# With SaaS sync disabled (or no auth), the same commands must stay
# side-effect-free. The tracker read paths report-without-writing regardless of
# the SaaS flag, so they belong here too; the emit + daemon paths short-circuit
# on the disabled flag and must likewise leave the tree clean.
_DISABLED_VARIANT_COMMANDS: tuple[tuple[str, Callable[[Path, Path], None]], ...] = (
    ("status-event-emission", _drive_status_event_emission),
    ("dossier-sync-trigger", _drive_dossier_sync_trigger),
    ("lifecycle-saas-fanout", _drive_lifecycle_saas_fanout),
    ("tracker-status", _drive_tracker_status),
    ("tracker-sync-pull", _drive_tracker_sync_pull),
    ("tracker-map-list", _drive_tracker_map_list),
    ("daemon-tick", _drive_daemon_tick),
)


@pytest.mark.parametrize(
    "command_name,driver",
    _DISABLED_VARIANT_COMMANDS,
    ids=[name for name, _ in _DISABLED_VARIANT_COMMANDS],
)
def test_covered_command_side_effect_free_when_disabled(
    checkout: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    command_name: str,
    driver: Callable[[Path, Path], None],
) -> None:
    """T017 / FR-008 / AS-6: disabled/unauth path stays side-effect-free.

    Opt OUT of the autouse SaaS-sync flag and present no auth. The commands must
    leave porcelain + config.yaml byte-identical exactly as in the enabled path.
    """
    repo_root, config_path = checkout
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")

    before = _snapshot(repo_root, config_path)
    driver(repo_root, config_path)
    after = _snapshot(repo_root, config_path)

    _assert_unchanged(before, after, command=f"{command_name} (sync disabled)")
    assert not load_identity(config_path).is_complete


# ===========================================================================
# T018 — record-analysis guard regression + allowlist + C-002 negative assertion
# ===========================================================================


def _seed_record_analysis_mission(repo_root: Path) -> Path:
    """Commit a production-shaped mission so the record-analysis preflight is clean.

    Mirrors ``tests/mission_runtime/test_self_bookkeeping_allowlist.py`` so the
    guard sees a real, committed mission to diff against.
    """
    mission_id = "01KWC9Y0RECORDANALYSISGUARD"  # 26-char ULID
    mid8 = mission_id[:8]
    slug = f"worktree-clean-invariant-{mid8}"
    feature_dir = repo_root / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        "{\n"
        '  "created_at": "2026-06-30T00:00:00+00:00",\n'
        '  "friendly_name": "Worktree Clean Invariant",\n'
        f'  "mid8": "{mid8}",\n'
        f'  "mission_id": "{mission_id}",\n'
        f'  "mission_slug": "{slug}",\n'
        '  "mission_type": "software-dev",\n'
        f'  "slug": "{slug}",\n'
        '  "target_branch": "fix/sync-worktree-clean-invariant"\n'
        "}\n",
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text("# Spec\n\nFR-007.\n", encoding="utf-8")
    src_dir = repo_root / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "seed mission")
    return feature_dir


def test_record_analysis_still_blocks_on_genuine_dirt(tmp_path: Path) -> None:
    """T018 / FR-007 / AS-4: a real source edit STILL yields DIRTY_WORKTREE.

    The mission removed the *config.yaml* write from read paths — it did NOT
    weaken the record-analysis dirty-tree guard. A genuine uncommitted edit to a
    primary source file must still block the analysis-report write (typer.Exit).
    """
    import typer

    from specify_cli.cli.commands.agent.mission import (
        _enforce_analysis_report_write_preflight,
    )

    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir()
    _git(repo_root, "init")
    feature_dir = _seed_record_analysis_mission(repo_root)
    slug = feature_dir.name

    # A genuine, uncommitted source edit — real dirt that must still block.
    (repo_root / "src" / "module.py").write_text("VALUE = 2  # edited\n", encoding="utf-8")

    with pytest.raises(typer.Exit):
        _enforce_analysis_report_write_preflight(
            repo_root,
            json_output=True,
            placement_ref=None,
            mission_slug=slug,
        )


def test_record_analysis_allowlist_excludes_config_yaml() -> None:
    """T018 / C-001: the self-bookkeeping allowlist must NOT contain config.yaml.

    The fix REMOVED the read-path write; it did NOT allowlist ``config.yaml`` to
    paper over a residual write. ``config.yaml`` must be rejected by the public
    owner predicate.

    lifecycle-gate-execution-context-01KY72GQ WP11 (IC-07a): the retired
    ``mission_runtime.artifacts._SELF_BOOKKEEPING_FILENAMES`` /
    ``_SELF_BOOKKEEPING_SUFFIXES`` module-level literals this test used to
    introspect directly no longer exist anywhere in ``src/`` (C5) — the
    equivalent literals are now function-local inside
    :func:`specify_cli.coordination.coherence.is_self_bookkeeping_churn`
    precisely so the R-014 exemption-registry scan does not treat them as a NEW
    per-gate filename collection (C9). This test therefore asserts on the
    owner/classifier BEHAVIOUR instead of the retired mechanism's internals
    (T062).
    """
    assert not is_self_bookkeeping_churn(f"kitty-specs/{_MISSION_SLUG}/.kittify/config.yaml"), (
        "config.yaml must NOT be classified as self-bookkeeping churn — C-001 "
        "forbids allowlisting it; the write must be removed, not masked"
    )
    assert not is_self_bookkeeping_churn(".kittify/config.yaml")
    # Sanity: the predicate DOES still recognize the genuine bookkeeping files, so
    # the negative assertions above are not vacuously true on a broken predicate.
    assert is_self_bookkeeping_churn("kitty-specs/x/meta.json")
    assert is_self_bookkeeping_churn(".kittify/encoding-provenance/global.jsonl")


def test_read_command_does_not_invoke_doctor_autofix(
    checkout: tuple[Path, Path],
) -> None:
    """T018 / C-002: a read/sync command must NOT auto-invoke the doctor fix path.

    ``sync status --check`` is a *read* surface. It may print a hint to run
    ``sync doctor``, but it must never trigger the mission-state auto-repair engine
    (``migration.mission_state.repair_repo`` — the only mutating fix path) NOR even
    the read-only doctor health pass (``status.doctor.run_doctor``) as a side
    effect. We spy BOTH and assert neither is called — locking the "no auto-fix on
    sync/read" constraint (C-002).
    """
    repo_root, config_path = checkout
    with (
        patch(_AUTOFIX_ENTRYPOINT) as autofix_spy,
        patch(_DOCTOR_HEALTH_ENTRYPOINT) as doctor_spy,
    ):
        _drive_sync_status_check(repo_root, config_path)
    autofix_spy.assert_not_called()
    doctor_spy.assert_not_called()


# ===========================================================================
# T019 — Extensibility guard + serial daemon variant + flake handling
# ===========================================================================


def _covered_command_names() -> Iterator[str]:
    yield from (name for name, _ in _COVERED_COMMANDS)
    yield "daemon-tick"  # asserted serially below; counted in the covered surface.


def test_covered_surface_matches_spec_exactly() -> None:
    """T019 / AS-7: the covered command surface is exactly the mission's set.

    This is the extensibility guard's tripwire: adding a new covered command is a
    one-line append to ``_COVERED_COMMANDS`` (or the documented daemon-tick
    extension). If a command is added or dropped without updating this expected
    set, this test fails — forcing the author to confirm the new command satisfies
    INV-1 (leaves porcelain + config.yaml untouched) before the surface changes.
    """
    expected = {
        "status-event-emission",
        "sync-status-check",
        "dossier-sync-trigger",
        "lifecycle-saas-fanout",
        "tracker-status",
        "tracker-sync-pull",
        "tracker-sync-push",
        "tracker-sync-run",
        "tracker-map-list",
        "daemon-tick",
    }
    assert set(_covered_command_names()) == expected, (
        "covered command surface drifted from the mission spec. Adding a command "
        "is a one-line change here AND in _COVERED_COMMANDS — and the new command "
        "MUST satisfy INV-1 (no porcelain / config.yaml churn) or the parametrized "
        "no-dirty-tree test fails."
    )


# Serial (-n0): the daemon tick exercises the background sync service. It is kept
# OUT of the parallel parametrization above so the daemon/real-port risk never
# lands in the parallel path. Per project convention (matching
# ``tests/sync/test_orphan_sweep.py``), serial execution is enforced operationally
# by the dedicated ``-n0`` validation pass — NOT by an unregistered ``serial``
# mark. This tick is fully in-process (no port bound); a future port-binding
# extension MUST keep this test in the ``-n0`` pass (see module + CLAUDE.md
# "Real-port / daemon tests run serially").
def test_daemon_tick_leaves_worktree_clean(checkout: tuple[Path, Path]) -> None:
    """T016/T019 / INV-1: one background daemon tick leaves the worktree clean.

    The daemon tick is the heaviest covered surface (background sync service); it
    is driven via the underlying ``_perform_sync`` per-tick callable with the
    network stubbed, and asserted in its own test that runs in the serial
    (``-n0``) pass so the daemon/real-port risk never lands in the parallel path.
    """
    repo_root, config_path = checkout
    before = _snapshot(repo_root, config_path)

    _drive_daemon_tick(repo_root, config_path)

    after = _snapshot(repo_root, config_path)
    _assert_unchanged(before, after, command="daemon-tick")
    assert not load_identity(config_path).is_complete, (
        "daemon tick completed identity on disk — the background path must resolve "
        "it in memory only (#2263)"
    )
