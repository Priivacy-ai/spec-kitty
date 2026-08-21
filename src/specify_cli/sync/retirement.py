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
  performs a "final sync" — it reuses ``daemon.stop_sync_daemon()`` unchanged,
  which already shuts the daemon down with no drain (the HTTP ``/api/shutdown``
  handler and the SIGTERM/SIGINT handler in ``daemon.py`` do not drain before
  exiting; see ``daemon.py``'s own docstrings for that invariant). Do not
  "improve" this on the way to deletion.
* **No new network primitive.** The only outbound call this module's stop
  path makes is the existing localhost-only HTTP shutdown request inside
  ``stop_sync_daemon()``.
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

from dataclasses import dataclass
from typing import Literal

import psutil

from specify_cli.sync.daemon import stop_sync_daemon
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

    stopped, message = stop_sync_daemon()
    return RetirementOutcome(
        status="stopped" if stopped else "already_stopped",
        detail=message,
    )
