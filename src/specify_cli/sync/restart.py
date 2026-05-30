"""Compose stop + launch primitives to restart the sync daemon.

This module is the single source of truth for the
``spec-kitty doctor restart-daemon`` subcommand. It deliberately does NOT
re-implement any daemon lifecycle logic: it reads the on-disk
:class:`~specify_cli.sync.owner.DaemonOwnerRecord` to surface the
previous PID, then composes:

- :func:`specify_cli.sync.daemon.stop_sync_daemon` to terminate the
  daemon recorded in owner/state metadata (used by the existing operator
  workflow).
- :func:`specify_cli.sync.daemon.ensure_sync_daemon_running` with
  ``intent=REMOTE_REQUIRED`` to respawn the daemon at the foreground
  executable/source (used by ``sync now`` and the event emitter).

The function exits early with a structured :class:`RestartResult` on
each failure-mode boundary defined in
``contracts/doctor-restart-daemon.md``:

- exit 0  → ``status="restarted"`` (happy path; ``status="stale_owner_cleaned"``
  is reported on the rendered surface but still exits 0)
- exit 1  → ``status="no_owner"``
- exit 2  → ``status="respawn_failed"``
- exit 3  → ``status="stop_failed"``

C-004: this module is a *read-only* consumer of
:class:`~specify_cli.sync.owner.DaemonOwnerRecord` and
:class:`~specify_cli.sync.preflight.ForegroundIdentity`. It MUST NOT
rename or mutate any field on either dataclass.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


__all__ = [
    "restart_daemon",
    "render_restart_result",
]


RestartStatus = Literal[
    "restarted",
    "no_owner",
    "stop_failed",
    "respawn_failed",
    "stale_owner_cleaned",
]

_RESTART_STOP_TIMEOUT_SECONDS = 1.0
_RESTART_HEALTH_WAIT_SECONDS = 3.0
_OWNER_RECORD_GRACE_SECONDS = 2.0
_OWNER_RECORD_POLL_SECONDS = 0.05


@dataclass(frozen=True)
class RestartResult:
    """Structured outcome of :func:`restart_daemon`.

    Frozen so callers can rely on hashability for assertion / snapshot
    use in tests.

    Attributes:
        status: One of the literal :data:`RestartStatus` values.
        exit_code: Process exit code per the contract's exit-code matrix.
        previous_pid: PID recorded in owner/state metadata before the restart,
            or ``None`` when no PID metadata was present.
        new_pid: PID of the freshly-launched daemon, or ``None`` if launch
            did not run (no_owner / stop_failed) or did not return a PID
            (respawn_failed, including ``skipped_reason`` paths).
        error: Human-readable error message when a failure mode applies;
            ``None`` on the happy path.
    """

    status: RestartStatus
    exit_code: int
    previous_pid: int | None
    new_pid: int | None
    error: str | None


def _read_previous_pid() -> int | None:
    """Return the PID recorded in owner/state metadata, or ``None`` if absent."""
    # Local import keeps module import cheap and avoids cycles with
    # ``specify_cli.sync.owner`` at module load time.
    from specify_cli.sync.owner import read_owner_record

    record = read_owner_record()
    if record is not None:
        return int(record.pid)
    return _read_daemon_state_pid()


def _owner_record_present() -> bool:
    """Return True iff an owner record (parsed or malformed) is on disk."""
    from specify_cli.sync.owner import owner_record_path

    return bool(owner_record_path().exists())


def _daemon_state_metadata_present() -> bool:
    """Return True iff daemon state metadata exists on disk."""
    from specify_cli.sync.daemon import DAEMON_STATE_FILE

    return bool(DAEMON_STATE_FILE.exists())


def _restartable_daemon_state_metadata_present() -> bool:
    """Return True iff daemon state metadata is parseable enough to stop."""
    from specify_cli.sync.daemon import DAEMON_STATE_FILE, _parse_daemon_file

    if not DAEMON_STATE_FILE.exists():
        return False
    _url, port, _token, _pid = _parse_daemon_file(DAEMON_STATE_FILE)
    return port is not None


def _read_daemon_state_pid() -> int | None:
    """Return the PID from daemon state metadata, or ``None`` if absent/invalid."""
    from specify_cli.sync.daemon import DAEMON_STATE_FILE, _parse_daemon_file

    if not DAEMON_STATE_FILE.exists():
        return None
    _url, _port, _token, pid = _parse_daemon_file(DAEMON_STATE_FILE)
    return pid


def _owner_record_present_after_grace() -> bool:
    """Allow a short grace window for owner registration after daemon start."""
    if _owner_record_present():
        return True
    if not _daemon_state_metadata_present():
        return False

    deadline = time.monotonic() + _OWNER_RECORD_GRACE_SECONDS
    while time.monotonic() < deadline:
        time.sleep(_OWNER_RECORD_POLL_SECONDS)
        if _owner_record_present():
            return True
    return _owner_record_present()


def _registered_daemon_metadata_present_after_grace() -> bool:
    """Return True when restartable daemon metadata is present.

    The owner record is richer, but the daemon state file is sufficient for
    stop/respawn. macOS can observe a started daemon with state metadata before
    or without owner registration; restart-daemon should reconcile that state,
    not refuse with ``no_owner``.
    """
    if _owner_record_present_after_grace():
        return True
    return _restartable_daemon_state_metadata_present()


def restart_daemon(repo_root: Path) -> RestartResult:  # noqa: ARG001 — reserved for future repo-scoped state
    """Restart the registered sync daemon at the foreground version/source.

    Composition pipeline:

    1. Read restartable on-disk daemon metadata. If absent, return a
       ``no_owner`` result (exit 1) directing the operator to
       ``spec-kitty sync now``.
    2. Capture the previous PID from owner/state metadata (best-effort: a
       malformed record yields ``previous_pid=None`` but still proceeds
       through the stop step when restartable daemon state metadata exists).
    3. Call :func:`stop_sync_daemon`. Two normal outcomes:

       - ``(True, _)`` — process stopped or unhealthy metadata cleared.
         The "unhealthy metadata cleared" branch is the ``stale_owner_cleaned``
         path; both continue to the launch step.
       - ``(False, msg)`` — stop failed; return ``stop_failed`` (exit 3)
         and leave the owner record state alone.

    4. Call :func:`ensure_sync_daemon_running` with ``intent=REMOTE_REQUIRED``
       to respawn the daemon at the foreground binding. If the outcome's
       ``started`` flag is ``False`` and ``skipped_reason`` is not the
       benign "already running" sentinel, treat it as ``respawn_failed``
       (exit 2).

    The function never spawns a subprocess directly and never writes the
    owner record itself; both sides of the pipeline are owned by the
    existing primitives.
    """
    # Step 1 + 2 — read existing owner/state metadata. We tolerate a malformed
    # owner record by treating ``previous_pid`` as unknown but still proceeding
    # through stop when restartable daemon state metadata exists. Corrupt
    # state-only metadata is not restartable, so it stays on the ``no_owner``
    # boundary instead of laundering a local metadata parse failure as
    # ``stop_failed``.
    metadata_present = _registered_daemon_metadata_present_after_grace()
    if not metadata_present:
        return RestartResult(
            status="no_owner",
            exit_code=1,
            previous_pid=None,
            new_pid=None,
            error=(
                "No registered sync daemon — run `spec-kitty sync now` to "
                "launch one."
            ),
        )

    previous_pid = _read_previous_pid()

    # Local imports — keeps cycles tight and lets test monkeypatches target
    # the canonical symbol on the ``specify_cli.sync.daemon`` module.
    from specify_cli.sync.daemon import (
        DaemonIntent,
        ensure_sync_daemon_running,
        stop_sync_daemon,
    )

    # Step 3 — stop the running daemon. ``stop_sync_daemon`` returns
    # ``(stopped_or_cleaned, message)``. The ``False`` branch is the
    # "no metadata to stop" or "stop failed" boundary; we map it to
    # ``stop_failed`` and surface the message verbatim.
    try:
        stopped, stop_message = stop_sync_daemon(timeout=_RESTART_STOP_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 — surface as stop_failed per contract
        return RestartResult(
            status="stop_failed",
            exit_code=3,
            previous_pid=previous_pid,
            new_pid=None,
            error=f"Stop failed: {exc}",
        )

    # ``stop_sync_daemon`` returns ``False`` only when no daemon metadata
    # was found at the stop entry-point. Because we already verified the
    # owner record exists above, this branch indicates the metadata file
    # was removed between the owner-record check and the stop call (a
    # race condition); surface as stop_failed and leave further
    # remediation to the operator.
    if not stopped:
        return RestartResult(
            status="stop_failed",
            exit_code=3,
            previous_pid=previous_pid,
            new_pid=None,
            error=f"Stop reported no action: {stop_message}",
        )

    # The "Unhealthy sync daemon..." messages indicate the previous PID
    # was already dead / unresponsive; we still continue to the launch
    # step but we flag this as ``stale_owner_cleaned`` on success so the
    # operator sees a notice.
    stale_owner_cleaned = "Unhealthy" in stop_message or "invalid" in stop_message

    # Step 4 — respawn the daemon at the foreground binding.
    try:
        outcome = ensure_sync_daemon_running(
            intent=DaemonIntent.REMOTE_REQUIRED,
            health_wait_seconds=_RESTART_HEALTH_WAIT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 — surface as respawn_failed per contract
        return RestartResult(
            status="respawn_failed",
            exit_code=2,
            previous_pid=previous_pid,
            new_pid=None,
            error=f"Respawn failed: {exc}",
        )

    if not outcome.started:
        return RestartResult(
            status="respawn_failed",
            exit_code=2,
            previous_pid=previous_pid,
            new_pid=outcome.pid,
            error=(
                "Respawn skipped: "
                f"{outcome.skipped_reason or 'unknown reason'}"
            ),
        )

    final_status: RestartStatus = (
        "stale_owner_cleaned" if stale_owner_cleaned else "restarted"
    )
    return RestartResult(
        status=final_status,
        exit_code=0,
        previous_pid=previous_pid,
        new_pid=outcome.pid,
        error=None,
    )


def render_restart_result(result: RestartResult, *, json_output: bool) -> str:
    """Render *result* either as a JSON object or as a short human line.

    Returns the string the CLI should emit. Centralising the renderer here
    keeps the CLI wrapper in ``doctor.py`` thin and lets unit tests assert
    on the rendered form without invoking the Typer wrapper.
    """
    if json_output:
        return json.dumps(asdict(result), sort_keys=True)

    if result.status == "restarted":
        return (
            f"Sync daemon restarted (previous_pid={result.previous_pid}, "
            f"new_pid={result.new_pid})."
        )
    if result.status == "stale_owner_cleaned":
        return (
            f"Stale daemon owner record cleaned; daemon restarted "
            f"(previous_pid={result.previous_pid}, new_pid={result.new_pid})."
        )
    if result.status == "no_owner":
        return result.error or (
            "No registered sync daemon — run `spec-kitty sync now`."
        )
    if result.status == "stop_failed":
        return f"Daemon stop failed: {result.error or 'unknown error'}"
    if result.status == "respawn_failed":
        return f"Daemon respawn failed: {result.error or 'unknown error'}"
    # Defensive fallback — keep mypy --strict happy on the Literal narrowing.
    return f"Unexpected restart status: {result.status}"
