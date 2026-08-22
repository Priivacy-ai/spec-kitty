"""Explicit retirement of a pre-R2 legacy sync daemon.

R2 (``docs/BEADS_PROGRAM_GRAPH.json``, "Local legacy transport/store removal")
requires that old daemons stop without a final sync. Passive idle
self-retirement already achieves that eventually (``daemon._should_self_retire``)
but gives the operator no signal and is never triggered by anything a post-R2
CLI still does, since nothing in the deleted transport surface calls
``ensure_sync_daemon_running`` any more. This module is the one explicit,
best-effort retirement step a normal post-R2 CLI invocation can call instead
of waiting on that idle clock (``m1-contract-drafts/R2.md`` §3.2.2).

Design constraints this module exists to honor, verbatim from §3.2:

* **No new drain.** This module never calls anything that flushes a queue or
  performs a "final sync" — the stop path below is built entirely from
  ``daemon.py``'s own existing no-drain primitives (``_check_sync_daemon_health``,
  ``_stop_daemon_by_http``, ``_kill_and_cleanup`` — the same three building
  blocks ``stop_sync_daemon()`` itself is assembled from). The HTTP
  ``/api/shutdown`` handler and the SIGTERM/SIGINT handler in ``daemon.py`` do
  not drain before exiting; see ``daemon.py``'s own docstrings for that
  invariant. Do not "improve" this on the way to deletion.
* **No new network primitive.** The only outbound call this module's stop
  path makes is the existing localhost-only HTTP shutdown request inside
  ``daemon._stop_daemon_by_http()``.
* **Driven by the verified owner record, not the daemon state file.** The
  stop path is addressed with the already-verified ``DaemonOwnerRecord``'s
  own ``port``/``token``/``pid`` — never ``daemon.stop_sync_daemon()``'s
  wrapper, which instead depends on the *separate* ``_daemon_state_file()``
  written by the parent CLI process only after its own post-spawn
  health-check loop succeeds (up to ~21s of retry budget in
  ``_ensure_sync_daemon_running_locked``). A live, ownership-verified daemon
  can have ``owner.json`` (self-registered synchronously on bind, before that
  loop even starts) with no state file yet — or the state file can be gone
  even though the daemon is alive (an interrupted parent, or a partially
  completed version-mismatch recycle that already unlinked it via
  ``_kill_and_cleanup`` without the SIGKILL target actually exiting). Treating
  that absence as "no daemon" and reporting success without ever contacting
  the process is exactly the bug this module exists to avoid (see the
  regression coverage in ``tests/sync/test_legacy_daemon_retirement_r2t1.py``).
* **Ownership verification before any signal.** A record naming a PID that is
  alive but does not carry the daemon's own spawn signature (the record's PID
  may have been recycled by an unrelated process) is never signaled — this
  mirrors the reap-over-kill guard ``owner.py``'s orphan sweep already
  enforces, applied here to the *known*-PID case rather than a process scan.
* **Fail closed on an unreadable record.** A corrupt ``owner.json`` is not the
  same fact as "no daemon" (#3030, FR-003) — this module refuses to act on it
  rather than guessing.

See ``kitty-specs/R2-T1-local-legacy-removal/deletion-manifest.md`` for the
destructive-manifest scope this retirement step gates: ``daemon.py`` and its
siblings are not deleted until this step ships and is proven to converge.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

import psutil

from specify_cli.core.loopback_http import build_loopback_base_url
from specify_cli.sync.daemon import _check_sync_daemon_health, _kill_and_cleanup, _stop_daemon_by_http
from specify_cli.sync.owner import (
    DaemonOwnerRecord,
    UnreadableOwnerRecord,
    _cmdline_has_daemon_spawn_signature,
    classify_owner_record,
    is_orphan,
    remove_owner_record,
)

RetirementStatus = Literal[
    "no_daemon",
    "cleared_stale",
    "unverifiable_owner_record",
    "unverified_ownership",
    "stopped",
    "already_stopped",
]
"""``"already_stopped"`` is retained in this vocabulary for renderer/doctor
compatibility (``cli/commands/sync.py``'s ``_render_legacy_daemon_retirement``
treats it as a resolved, no-issue state) but :func:`retire_legacy_sync_daemon`
no longer produces it: once ownership is verified the daemon is always
still alive, so the verified branch always takes real action and reports
``"stopped"`` — there is no legitimate "was already stopped" fact it could
observe at that point. See the module docstring's "Driven by the verified
owner record" bullet for the bug this replaces."""


@dataclass(frozen=True)
class RetirementOutcome:
    """Result of one :func:`retire_legacy_sync_daemon` call.

    ``status`` is the machine-checkable outcome; ``detail`` is an
    operator-facing, one-line explanation safe to print (never carries the
    owner record's bearer token — see ``owner.redact_token``, which this
    module has no reason to bypass since it never renders the raw record).
    """

    status: RetirementStatus
    detail: str


def _verify_daemon_ownership(record: DaemonOwnerRecord) -> bool:
    """Return True when the live process at ``record.pid`` looks like a
    genuine spec-kitty sync daemon.

    This is deliberately narrower than a full identity match against the
    record's own fields (executable path, package version, ...) — those
    describe the daemon that *wrote* the record, not a re-derivable fact
    about whatever process now holds that PID. The question this function
    answers is only: "is it safe to send this PID an HTTP shutdown call
    against the daemon's own control port?" A live process whose command
    line does not carry the production daemon spawn shape
    (``<interpreter> -c <script>`` importing and calling ``run_sync_daemon``)
    answers no, regardless of what ``record`` claims about itself.
    """
    try:
        proc = psutil.Process(record.pid)
        cmdline = proc.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False
    return bool(_cmdline_has_daemon_spawn_signature(cmdline))


def _stop_verified_daemon(record: DaemonOwnerRecord, timeout: float = 5.0) -> str:
    """Stop the daemon named by an already ownership-verified ``record``.

    Addressed entirely by ``record.port`` / ``record.token`` / ``record.pid``
    — never by ``daemon.stop_sync_daemon()``'s separate state-file dependency
    (see the module docstring's "Driven by the verified owner record" bullet
    for why that distinction matters). Reuses the same no-drain building
    blocks ``stop_sync_daemon()`` itself is built from, so this is not a new
    network primitive, only a different, already-verified source of truth
    for *which* daemon to contact.

    Because the caller only reaches this function after ``_verify_daemon_ownership``
    has confirmed the PID is alive and carries the daemon's own spawn
    signature, every branch here takes real action (contact-then-confirm, or
    kill) — there is no legitimate "nothing to do" outcome once that
    verification has passed.
    """
    if not _check_sync_daemon_health(record.port, record.token):
        _kill_and_cleanup(record.pid)
        return "Unhealthy sync daemon process stopped (verified via owner record)."

    _stop_daemon_by_http(build_loopback_base_url(record.port), record.token)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _check_sync_daemon_health(record.port, record.token, timeout=0.2):
            return "Sync daemon stopped (verified via owner record)."
        time.sleep(0.05)

    _kill_and_cleanup(record.pid)
    return "Sync daemon did not confirm shutdown within timeout; force-stopped (verified via owner record)."


def retire_legacy_sync_daemon() -> RetirementOutcome:
    """Detect and stop a pre-R2 legacy sync daemon left running on this host.

    Reachable from a normal post-R2 CLI invocation (the specific call site —
    first-command hook vs. a dedicated ``doctor`` check — is a routine
    implementation choice left to the caller; this function is the
    self-contained unit either can call). Idempotent: calling it again after
    a successful retirement, or with no daemon ever having registered,
    reports ``"no_daemon"`` and does nothing.
    """
    outcome = classify_owner_record()

    if outcome is None:
        return RetirementOutcome(
            status="no_daemon",
            detail="No legacy sync daemon owner record found; nothing to retire.",
        )

    if isinstance(outcome, UnreadableOwnerRecord):
        return RetirementOutcome(
            status="unverifiable_owner_record",
            detail=outcome.describe(),
        )

    record: DaemonOwnerRecord = outcome

    if is_orphan(record):
        remove_owner_record()
        return RetirementOutcome(
            status="cleared_stale",
            detail=(
                f"Owner record named pid={record.pid}, which is no longer "
                "alive (or its recorded executable is gone); cleared "
                "without contacting it."
            ),
        )

    if not _verify_daemon_ownership(record):
        return RetirementOutcome(
            status="unverified_ownership",
            detail=(
                f"pid={record.pid} is alive but does not carry the spec-kitty "
                "daemon spawn signature -- refusing to signal a process this "
                "record cannot verify it owns."
            ),
        )

    detail = _stop_verified_daemon(record)
    return RetirementOutcome(status="stopped", detail=detail)
