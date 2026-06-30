"""Pure sync-daemon orphan cleanup classification engine.

This module turns one probed sync-port listener into a ``DaemonIdentityRecord``
carrying a ``cleanup_class`` (``safe_auto`` / ``operator_required`` /
``never_touch``).  It is the single decision authority both cleanup surfaces —
WP02 startup reaper and WP03 ``auth doctor`` port-scan — will consume.

Design constraints
------------------
* **Pure / dependency-light**: no process signals, no filesystem writes, no
  network I/O.  All probing happens in the callers; the classifier only decides.
* **No imports from owner.py / orphan_sweep.py / daemon.py** kill paths.
  Callers extract ``singleton_scope_id``, ``spawn_shape_ok``, and
  ``executable_summary`` from the cmdline via helpers in ``owner.py`` and pass
  the results in via ``CandidateProbe``.
* The daemon-root scope marker is the **primary kill authority** — not
  ``owner.json`` (FR-003).  ``owner_present`` is recorded for reporting only and
  must never change the verdict.
* Version / executable mismatch is stale-version *evidence*, never a skip gate
  (FR-008).

References
----------
* kitty-specs/sync-daemon-orphan-cleanup-01KWC2A3/data-model.md — normative
  decision table (rows 1–9) and ``DaemonIdentityRecord`` field table.
* kitty-specs/sync-daemon-orphan-cleanup-01KWC2A3/contracts/cleanup-classification.md
* kitty-specs/sync-daemon-orphan-cleanup-01KWC2A3/research.md  DD-01, D-01
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Port-range constants (mirrored read-only from daemon.py — do not import
# from daemon.py to keep this module free of heavy transitive dependencies).
# ---------------------------------------------------------------------------

_DAEMON_PORT_START: int = 9400
_DAEMON_PORT_END: int = _DAEMON_PORT_START + 50  # exclusive: [9400, 9450)

# Default daemon_family when the health response omits the field (WP04 adds
# it; this module must tolerate its absence when port/spawn-shape are present).
_DEFAULT_DAEMON_FAMILY: str = "sync"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CleanupClass(StrEnum):
    """Classifier verdict for a scanned sync-port listener.

    Values are ASCII snake-case strings so they round-trip through JSON and
    the ``to_dict()`` surface unchanged.
    """

    SAFE_AUTO = "safe_auto"
    """Provably ours, same-scope, responsive, not the singleton."""

    OPERATOR_REQUIRED = "operator_required"
    """Looks like SK sync but ambiguous; requires explicit operator action."""

    NEVER_TOUCH = "never_touch"
    """Not identifiable as SK sync / out-of-range; must never be killed."""


class SkipReason(StrEnum):
    """Reason a listener was not classified ``safe_auto``.

    Present on every ``DaemonIdentityRecord`` whose ``cleanup_class`` is
    *not* ``safe_auto``; ``None`` iff ``cleanup_class == safe_auto``.
    """

    is_recorded_singleton = "is_recorded_singleton"
    """Listener is the live recorded singleton — excluded from cleanup."""

    pre_marker = "pre_marker"
    """No daemon-root scope marker found in cmdline (pre-marker daemon)."""

    cross_root = "cross_root"
    """Daemon-root marker is present but belongs to a different scope."""

    missing_pid = "missing_pid"
    """Could not determine the PID of the process holding the port."""

    pid_port_mismatch = "pid_port_mismatch"
    """Health self-report PID/port do not match the actual listener."""

    unresponsive = "unresponsive"
    """Listener did not respond to ``/api/health`` (wedged/hung)."""

    not_spec_kitty = "not_spec_kitty"
    """No spawn-signature and no SK self-report; probably unrelated."""

    out_of_range = "out_of_range"
    """Port is outside the sync range ``[9400, 9450)``."""

    dashboard_family = "dashboard_family"
    """Port is in the dashboard range — sync cleanup must not touch it."""

    third_party = "third_party"
    """Foreign health response seen; process is not Spec Kitty sync."""


class IdentitySource(StrEnum):
    """How the daemon's identity was proven."""

    health_self_report = "health_self_report"
    """Identity confirmed via live ``/api/health`` response."""

    cmdline_marker = "cmdline_marker"
    """Identity inferred from the daemon-root scope marker in cmdline."""

    owner_record = "owner_record"
    """Identity inferred from the on-disk owner record."""

    none = "none"
    """Identity could not be established."""


# ---------------------------------------------------------------------------
# Input value objects (pure data — no logic)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HealthProbe:
    """Parsed ``/api/health`` response, or a sentinel for an unresponsive port.

    ``responded=False`` models a wedged listener that did not answer.
    The caller is responsible for making the HTTP request and populating this
    object; this module performs no I/O.

    Caller note: ``owner_pid`` / ``owner_port`` come from the ``owner`` block
    inside the health payload (``daemon.py:514-520``).  ``queue_db_path``,
    ``auth_scope``, and ``server_url`` are redacted reporting fields only —
    they do not influence the classification verdict.
    """

    responded: bool
    status: str | None
    protocol_version: int | None
    package_version: str | None
    # WP04 adds daemon_family to the health payload; treat None as "sync" when
    # the port is in range and the spawn signature is present.
    daemon_family: str | None
    # From the redacted owner block in the health payload.
    owner_pid: int | None
    owner_port: int | None
    # Reporting-only fields (never used in classification predicates).
    queue_db_path: str | None
    auth_scope: str | None
    server_url: str | None


@dataclass(frozen=True)
class SingletonRef:
    """PID and port of the currently recorded singleton daemon (state file).

    Callers populate this from the daemon state file (``daemon.py:270-304``).
    ``None`` values indicate the field was absent or unreadable.
    """

    pid: int | None
    port: int | None


@dataclass(frozen=True)
class CandidateProbe:
    """All pre-extracted facts about one scanned port listener.

    Callers derive ``singleton_scope_id``, ``spawn_shape_ok``, and
    ``executable_summary`` from the process cmdline via ``owner.py`` helpers:
    * ``singleton_scope_id`` — from ``_cmdline_daemon_root_marker`` +
      ``_daemon_scope_root()`` (``daemon.py:818-830``).
    * ``spawn_shape_ok``     — from ``_cmdline_has_daemon_spawn_signature``.
    * ``executable_summary`` — from ``_process_executable_scopes``.

    This module receives the already-extracted primitives and performs no
    process inspection of its own.
    """

    port: int
    listener_pid: int | None
    # None means the listener did not respond at all (caller could not even
    # attempt a probe) — distinct from HealthProbe(responded=False) which
    # means the probe was attempted but timed out / errored.
    health: HealthProbe | None
    # From _cmdline_daemon_root_marker + _daemon_scope_root():
    singleton_scope_id: str | None
    # From _cmdline_has_daemon_spawn_signature():
    spawn_shape_ok: bool
    # From _process_executable_scopes():
    executable_summary: str | None
    # Whether the on-disk owner record exists — reporting only (FR-003).
    owner_present: bool


@dataclass(frozen=True)
class ForegroundScope:
    """Identity of the currently running (foreground) CLI invocation.

    ``scope_id``       — resolved ``_daemon_scope_root()`` of this process.
    ``executable_scope`` — canonical executable scope of this process.
    ``singleton``      — PID/port from the daemon state file for this scope.
    """

    scope_id: str
    executable_scope: str
    singleton: SingletonRef


# ---------------------------------------------------------------------------
# Result record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DaemonIdentityRecord:
    """Per-candidate identity produced by the sync-daemon classification scan.

    Satisfies FR-001.  Every field listed in
    ``data-model.md`` is present.  ``cleanup_class`` and ``skip_reason``
    are the actionable verdict; all other fields are evidence / reporting.

    Invariants (enforced by ``classify_candidate``):
    * ``skip_reason is None`` ⟺ ``cleanup_class == CleanupClass.SAFE_AUTO``
    * ``owner_present`` never influences ``cleanup_class`` (FR-003)
    * ``port`` ∈ ``[9400, 9450)`` for every record this engine emits
      (the ``out_of_range`` row is never scanned, but is handled if called)
    """

    # Always "sync" for records emitted by this engine (DD-02).
    daemon_family: str
    pid: int | None
    port: int
    protocol_version: int | None
    package_version: str | None
    singleton_scope_id: str | None
    daemon_root: str | None
    queue_db_path: str | None
    auth_scope: str | None
    server_url: str | None
    # Reporting-only — must not appear in any classification predicate (FR-003).
    owner_present: bool
    identity_source: IdentitySource
    executable_summary: str | None
    spawn_shape_ok: bool
    self_report_matches_listener: bool
    is_recorded_singleton: bool
    cleanup_class: CleanupClass
    skip_reason: SkipReason | None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the snake_case JSON surface consumed by WP05.

        Key names match ``contracts/auth-doctor-json.md`` exactly.
        ``None`` values are preserved so consumers can distinguish absent from
        unknown.  Enum values are serialised as their string form.
        """
        return {
            "daemon_family": self.daemon_family,
            "pid": self.pid,
            "port": self.port,
            "protocol_version": self.protocol_version,
            "package_version": self.package_version,
            "singleton_scope_id": self.singleton_scope_id,
            "daemon_root": self.daemon_root,
            "queue_db_path": self.queue_db_path,
            "auth_scope": self.auth_scope,
            "server_url": self.server_url,
            "owner_present": self.owner_present,
            "identity_source": self.identity_source.value,
            "executable_summary": self.executable_summary,
            "spawn_shape_ok": self.spawn_shape_ok,
            "self_report_matches_listener": self.self_report_matches_listener,
            "is_recorded_singleton": self.is_recorded_singleton,
            "cleanup_class": self.cleanup_class.value,
            "skip_reason": self.skip_reason.value if self.skip_reason is not None else None,
        }


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def _is_singleton(probe: CandidateProbe, foreground: ForegroundScope) -> bool:
    """Return True if the candidate is the current recorded singleton."""
    s = foreground.singleton
    return probe.listener_pid == s.pid and probe.port == s.port


def _has_sk_identity(probe: CandidateProbe) -> bool:
    """Return True if the port looks like a Spec Kitty sync process.

    A port is identifiable as SK sync when *either*:
    * The production spawn-shape is present in the cmdline (``spawn_shape_ok``), or
    * The health response self-reports as Spec Kitty (has ``protocol_version``).
    """
    h = probe.health
    return probe.spawn_shape_ok or (
        h is not None and h.responded and h.protocol_version is not None
    )


def _self_report_matches(probe: CandidateProbe) -> bool:
    """Return True when the health payload's owner_pid/port match the listener."""
    h = probe.health
    if h is None or not h.responded:
        return False
    return h.owner_pid == probe.listener_pid and h.owner_port == probe.port


def _build_record(
    probe: CandidateProbe,
    cleanup_class: CleanupClass,
    skip_reason: SkipReason | None,
    identity_source: IdentitySource,
    is_singleton: bool,
) -> DaemonIdentityRecord:
    """Assemble a ``DaemonIdentityRecord`` from a probe + classifier verdict."""
    h = probe.health
    daemon_family: str = _DEFAULT_DAEMON_FAMILY
    if h is not None and h.responded and h.daemon_family is not None:
        daemon_family = h.daemon_family

    return DaemonIdentityRecord(
        daemon_family=daemon_family,
        pid=probe.listener_pid,
        port=probe.port,
        protocol_version=h.protocol_version if h is not None else None,
        package_version=h.package_version if h is not None else None,
        singleton_scope_id=probe.singleton_scope_id,
        daemon_root=probe.singleton_scope_id,  # resolved scope == daemon root
        queue_db_path=h.queue_db_path if h is not None else None,
        auth_scope=h.auth_scope if h is not None else None,
        server_url=h.server_url if h is not None else None,
        owner_present=probe.owner_present,
        identity_source=identity_source,
        executable_summary=probe.executable_summary,
        spawn_shape_ok=probe.spawn_shape_ok,
        self_report_matches_listener=_self_report_matches(probe),
        is_recorded_singleton=is_singleton,
        cleanup_class=cleanup_class,
        skip_reason=skip_reason,
    )


# ---------------------------------------------------------------------------
# Public classifier
# ---------------------------------------------------------------------------


def classify_candidate(
    probe: CandidateProbe,
    foreground: ForegroundScope,
) -> DaemonIdentityRecord:
    """Classify one probed sync-port listener.

    Implements the normative decision table from
    ``data-model.md`` (rows 1–9), evaluated
    top-to-bottom; the first matching row wins.

    Parameters
    ----------
    probe:
        Pre-extracted facts about the candidate listener.  Callers populate
        this from ``psutil`` / ``lsof`` (PID), ``/api/health`` (health), and
        ``owner.py`` cmdline helpers (scope / shape / executable).
    foreground:
        Identity of the running CLI invocation (scope, executable, singleton).

    Returns
    -------
    DaemonIdentityRecord
        Fully populated record including ``cleanup_class`` and ``skip_reason``.

    Notes
    -----
    * ``owner_present`` does not appear in any predicate — it is carried in the
      probe for reporting purposes only (FR-003).
    * A non-matching ``package_version`` / ``executable_summary`` is *not* a
      skip condition once rows 1–8 pass (FR-008).
    * A wedged listener (``probe.health is None`` or ``not responded``) is
      ``operator_required / unresponsive`` — never ``safe_auto`` (D-01).
    """
    is_singleton = _is_singleton(probe, foreground)

    # Row 1 — port out of range → never_touch / out_of_range
    if not (_DAEMON_PORT_START <= probe.port < _DAEMON_PORT_END):
        return _build_record(
            probe,
            CleanupClass.NEVER_TOUCH,
            SkipReason.out_of_range,
            IdentitySource.none,
            is_singleton,
        )

    # Row 2 — not identifiable as SK sync → never_touch
    if not _has_sk_identity(probe):
        # If a foreign health response was seen, the process is a third-party
        # squatter; otherwise it is simply not recognisable as SK sync.
        h = probe.health
        reason = SkipReason.third_party if h is not None and h.responded else SkipReason.not_spec_kitty
        return _build_record(
            probe,
            CleanupClass.NEVER_TOUCH,
            reason,
            IdentitySource.none,
            is_singleton,
        )

    # Row 2b — no production spawn shape → never_touch / third_party
    #
    # A Spec Kitty health-shaped response alone is not kill authority. The
    # spawn signature is required before any reset/force/startup path may send
    # a signal, even when argv carries a spoofable-looking scope marker.
    if not probe.spawn_shape_ok:
        return _build_record(
            probe,
            CleanupClass.NEVER_TOUCH,
            SkipReason.third_party,
            IdentitySource.none,
            is_singleton,
        )

    # Row 3 — is the recorded singleton → excluded from cleanup
    if is_singleton:
        return _build_record(
            probe,
            CleanupClass.NEVER_TOUCH,
            SkipReason.is_recorded_singleton,
            IdentitySource.cmdline_marker
            if probe.singleton_scope_id is not None
            else IdentitySource.none,
            True,
        )

    # Row 4 — cannot determine PID → operator_required / missing_pid
    if probe.listener_pid is None:
        return _build_record(
            probe,
            CleanupClass.OPERATOR_REQUIRED,
            SkipReason.missing_pid,
            IdentitySource.none,
            is_singleton,
        )

    # Row 5 — no daemon-root marker → operator_required / pre_marker
    if probe.singleton_scope_id is None:
        return _build_record(
            probe,
            CleanupClass.OPERATOR_REQUIRED,
            SkipReason.pre_marker,
            IdentitySource.none,
            is_singleton,
        )

    # Row 6 — scope marker present but belongs to a different root →
    #          operator_required / cross_root
    if probe.singleton_scope_id != foreground.scope_id:
        return _build_record(
            probe,
            CleanupClass.OPERATOR_REQUIRED,
            SkipReason.cross_root,
            IdentitySource.cmdline_marker,
            is_singleton,
        )

    # Row 7 — wedged / no live health self-report → operator_required / unresponsive
    #          (D-01: safe_auto requires a live self-report)
    h = probe.health
    if h is None or not h.responded:
        return _build_record(
            probe,
            CleanupClass.OPERATOR_REQUIRED,
            SkipReason.unresponsive,
            IdentitySource.cmdline_marker,
            is_singleton,
        )

    # Row 8 — health self-report PID/port do not match the listener →
    #          operator_required / pid_port_mismatch
    if h.owner_pid != probe.listener_pid or h.owner_port != probe.port:
        return _build_record(
            probe,
            CleanupClass.OPERATOR_REQUIRED,
            SkipReason.pid_port_mismatch,
            IdentitySource.health_self_report,
            is_singleton,
        )

    # Row 9 — all guards passed → safe_auto
    # FR-008: a differing package_version / executable_summary is stale-version
    # *evidence* and does NOT prevent cleanup.  No version equality check here.
    return _build_record(
        probe,
        CleanupClass.SAFE_AUTO,
        None,
        IdentitySource.health_self_report,
        is_singleton,
    )
