"""Daemon owner record and ownership semantics.

This module owns the canonical on-disk record describing **which** sync daemon
process currently holds the queue/control-plane lease (PID, port, auth scope,
queue DB, executable path, package version, etc.). The foreground CLI reads
this record before mutating any sync-side state and refuses to act when it
detects an *ownership mismatch* (the running daemon was started under
different identity/version than the foreground sees today). The record also
powers orphan detection: if the recorded PID is no longer alive (or its
executable is gone), the record is stale and should be reconciled rather
than trusted.

See ``kitty-specs/mvp-sync-boundary-cli-01KRVCQS/data-model.md`` for the
schema and the D-3 mismatch contract.

Design notes
------------
- The record lives at ``<sync_root>/daemon/owner.json`` (one record per host).
- Writes are atomic: a ``tempfile.NamedTemporaryFile(delete=False, dir=…)``
  in the same directory is renamed via ``os.replace`` onto the final path,
  so concurrent readers either see the previous record or the new record —
  never a partial file. ``daemon.lock`` already serialises spawn attempts,
  so no extra lock is needed at the JSON layer (C-006).
- Token redaction is *enforced* at the health-endpoint boundary: the daemon
  must call :func:`redact_token` before serialising the record into any
  HTTP response. The dataclass itself stores the raw token; do not
  ``json.dumps(asdict(record))`` into a response without redacting first.
- Orphan detection (C-002) never sends signals to PIDs we did not spawn.
  ``is_orphan`` is a *predicate*; it never calls ``os.kill``.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from specify_cli.sync.daemon import (
    _daemon_root,
    _get_package_version,
    _is_process_alive,
    _sync_root,
)

logger = logging.getLogger(__name__)


def _canonical_executable_path(value: object) -> str:
    """Return the canonical (symlink-resolved) form of an executable path.

    Resolution failures (deleted target, permission denied, runaway symlink
    loop) fall back to the raw string. Logging at DEBUG so operators can
    correlate a spurious mismatch with the underlying resolve failure.

    This is the single source of truth for executable-path normalization on
    both write paths (foreground identity, daemon record build) and the read
    path (deserialization in :func:`read_owner_record`). Compare sites SHOULD
    NOT re-resolve — by construction, every ``DaemonOwnerRecord.executable_path``
    in memory has already passed through this helper.
    """
    raw = str(value)
    try:
        return str(Path(raw).resolve())
    except (OSError, RuntimeError) as exc:
        logger.debug("executable path resolve failed: %r (%s)", raw, exc)
        return raw


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DaemonOwnerRecord:
    """Canonical owner record for the sync daemon.

    All fields are required at construction time. ``token`` is the
    daemon's control-plane bearer token and MUST be redacted before
    appearing in any health response or log line (see :func:`redact_token`).

    Fields per ``data-model.md`` D-2:

    - ``pid``: PID of the daemon process.
    - ``port``: TCP port the daemon listens on (127.0.0.1).
    - ``token``: control-plane bearer token (NEVER serialised to clients).
    - ``package_version``: ``importlib.metadata`` version of ``spec-kitty-cli``.
    - ``executable_path``: canonical (symlink-resolved) ``sys.executable`` of
      the daemon process. The invariant is established by
      :func:`_canonical_executable_path` on every write boundary (foreground
      identity, daemon record build) and on the read boundary
      (:func:`read_owner_record`). Compare sites MUST NOT re-resolve.
      Case is not normalized — case-insensitive filesystems (APFS/NTFS) may
      still produce a mismatch if daemon and foreground disagree on casing.
    - ``source_checkout_path``: repo root of the installed package (the same
      algorithm is used on the foreground side so the strings compare cleanly).
    - ``server_url``: SaaS server URL configured for this scope.
    - ``auth_principal``: authenticated user email/handle, if any.
    - ``auth_team``: authenticated team slug, if any.
    - ``auth_scope``: canonical scope string from ``build_queue_scope``.
      ``None`` here vs non-``None`` on the foreground is a mismatch (D-3).
    - ``queue_db_path``: ``default_queue_db_path()`` for this scope.
    - ``started_at``: ISO-8601 UTC timestamp recorded when the record was built.
    """

    pid: int
    port: int
    token: str
    package_version: str
    executable_path: str
    source_checkout_path: str
    server_url: str
    auth_principal: str | None
    auth_team: str | None
    auth_scope: str | None
    queue_db_path: str
    started_at: str

    def __post_init__(self) -> None:
        # Enforce the canonical-executable-path invariant at the dataclass
        # boundary so callers cannot bypass normalization by constructing a
        # record directly (e.g. test fixtures). ``frozen=True`` requires
        # ``object.__setattr__`` for the rewrite; fall back to the raw value
        # on resolve failure (logged inside the helper).
        canonical = _canonical_executable_path(self.executable_path)
        if canonical != self.executable_path:
            object.__setattr__(self, "executable_path", canonical)

    def as_dict(self) -> dict[str, Any]:
        """Return the record as a plain dict (token NOT redacted).

        Callers that expose the record outside the daemon process MUST use
        :func:`redact_token` instead.
        """
        return asdict(self)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


_OWNER_FILE_NAME = "owner.json"


def _owner_dir() -> Path:
    """Return the directory holding the canonical owner record.

    The record lives under ``<sync_root>/daemon/`` so it sits next to the
    rest of the daemon-owned state (logs, locks, sockets) instead of under
    the user-shared ``~/.spec-kitty`` root.
    """
    return _sync_root() / "daemon"


def owner_record_path() -> Path:
    """Return the canonical path to ``owner.json``."""
    return _owner_dir() / _OWNER_FILE_NAME


# ---------------------------------------------------------------------------
# Atomic write / read
# ---------------------------------------------------------------------------


def write_owner_record(record: DaemonOwnerRecord) -> Path:
    """Atomically persist *record* to ``<sync_root>/daemon/owner.json``.

    The function writes the JSON payload to a temporary file in the same
    directory and renames it onto the canonical path with :func:`os.replace`,
    which is atomic on POSIX and on NTFS (Python 3.3+ semantics). The
    temporary file is removed on any failure so the directory listing
    never accumulates orphaned ``tmp*`` siblings.

    Returns the path that was written. Also ensures the parent directory
    exists; spec-kitty owns this directory exclusively, so a permissive
    ``mkdir(parents=True, exist_ok=True)`` is safe.
    """
    target = owner_record_path()
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(record.as_dict(), sort_keys=True, indent=2) + "\n"

    tmp_fd, tmp_name = tempfile.mkstemp(prefix=".owner-", suffix=".tmp", dir=parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, target)
    except Exception:
        # Best-effort cleanup; never leak temp siblings into the daemon dir.
        with contextlib.suppress(FileNotFoundError):
            tmp_path.unlink()
        raise
    return target


def read_owner_record() -> DaemonOwnerRecord | None:
    """Read the canonical owner record, returning ``None`` if absent or invalid.

    The function is deliberately permissive about *missing* records (the
    daemon may simply not be running) but strict about *malformed* ones:
    a JSON parse error or a missing field also yields ``None`` so that
    upstream callers treat the daemon as "no recorded owner" and trigger
    the standard reconciliation path instead of crashing.
    """
    path = owner_record_path()
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return DaemonOwnerRecord(
            pid=int(data["pid"]),
            port=int(data["port"]),
            token=str(data["token"]),
            package_version=str(data["package_version"]),
            # ``executable_path`` is canonicalized in ``DaemonOwnerRecord.__post_init__``.
            executable_path=str(data["executable_path"]),
            source_checkout_path=str(data["source_checkout_path"]),
            server_url=str(data["server_url"]),
            auth_principal=(
                None if data.get("auth_principal") is None else str(data["auth_principal"])
            ),
            auth_team=(None if data.get("auth_team") is None else str(data["auth_team"])),
            auth_scope=(None if data.get("auth_scope") is None else str(data["auth_scope"])),
            queue_db_path=str(data["queue_db_path"]),
            started_at=str(data["started_at"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def remove_owner_record() -> bool:
    """Remove the owner record file. Returns True if removal occurred.

    Used by the daemon's shutdown hook. Orphan-detection (crash path) does
    NOT rely on removal — a crash that leaves the file behind is exactly
    what :func:`is_orphan` detects.
    """
    path = owner_record_path()
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
# Redaction / health response
# ---------------------------------------------------------------------------


_REDACTED_PLACEHOLDER = "<redacted>"


def redact_token(record: DaemonOwnerRecord | None) -> dict[str, Any] | None:
    """Return ``record`` as a dict with ``token`` replaced by a placeholder.

    Use this at every boundary that exposes the record to an external
    client (HTTP health endpoint, status command JSON, logs). Returns
    ``None`` when ``record`` is ``None`` so callers can pipe the result
    of :func:`read_owner_record` directly through.
    """
    if record is None:
        return None
    data = record.as_dict()
    data["token"] = _REDACTED_PLACEHOLDER
    return data


# ---------------------------------------------------------------------------
# Foreground identity
# ---------------------------------------------------------------------------


def _resolve_source_checkout_path() -> str:
    """Return the repo root of the installed ``specify_cli`` package.

    Mirrors ``Path(specify_cli.__file__).resolve().parents[2]`` without
    importing the top-level package. Importing ``specify_cli`` here would
    drag the full root CLI registration graph into daemon owner-record
    construction, which is on the restart-daemon critical path.

    ``owner.py`` lives at ``.../specify_cli/sync/owner.py`` so
    ``Path(__file__).resolve().parents[3]`` lands on the same repo /
    site-packages-relative root that ``specify_cli.__file__`` would have
    produced.
    """
    return str(Path(__file__).resolve().parents[3])


def compute_foreground_identity() -> dict[str, Any]:
    """Build the foreground's view of the comparable identity fields.

    Returns a dict shaped like the subset of :class:`DaemonOwnerRecord`
    that participates in :func:`mismatched_fields`. Fetches the scope-aware
    auth/queue values from :mod:`specify_cli.sync.queue` lazily so that
    callers without a configured environment (e.g. unit tests with a
    tmp ``HOME``) still get a valid dict with ``None`` for missing pieces.
    """
    from specify_cli.sync.queue import (  # local import: cycle-safe
        _read_server_url_for_scope,
        default_queue_db_path,
        read_queue_scope_from_credentials,
        read_queue_scope_from_session,
    )

    scope = read_queue_scope_from_session()
    if scope is None:
        scope = read_queue_scope_from_credentials()

    auth_principal: str | None = None
    auth_team: str | None = None
    if scope is not None:
        # Canonical scope is ``server|user|team`` (see build_queue_scope).
        parts = scope.split("|")
        if len(parts) == 3:
            auth_principal = parts[1] or None
            auth_team = parts[2] or None

    return {
        "package_version": _get_package_version(),
        "executable_path": _canonical_executable_path(sys.executable),
        "source_checkout_path": _resolve_source_checkout_path(),
        "server_url": _read_server_url_for_scope(),
        "auth_principal": auth_principal,
        "auth_team": auth_team,
        "auth_scope": scope,
        "queue_db_path": str(default_queue_db_path()),
    }


# ---------------------------------------------------------------------------
# Mismatch detection (D-3 / FR-007)
# ---------------------------------------------------------------------------


# D-3 fields per data-model.md. Order is intentional — callers should
# render mismatches in this order so remediation messages are stable.
MISMATCH_FIELDS: tuple[str, ...] = (
    "package_version",
    "executable_path",
    "server_url",
    "auth_scope",
    "queue_db_path",
)


def mismatched_fields(
    daemon_record: DaemonOwnerRecord,
    foreground_identity: dict[str, Any],
) -> list[str]:
    """Return the list of D-3 field names that differ between the two views.

    Comparison is exact for strings; ``None`` vs non-``None`` is a mismatch
    for ``auth_scope`` (per data-model.md). The returned list preserves the
    canonical order from :data:`MISMATCH_FIELDS`.
    """
    out: list[str] = []
    for field in MISMATCH_FIELDS:
        daemon_value = getattr(daemon_record, field)
        fg_value = foreground_identity.get(field)
        if daemon_value != fg_value:
            out.append(field)
    return out


def check_daemon_owner_match() -> tuple[bool, list[str]]:
    """Canonical pre-action coherence check.

    Returns ``(True, [])`` when either:

    * no daemon owner record exists (no daemon to disagree with), or
    * the daemon record matches the foreground on every D-3 field.

    Returns ``(False, mismatched)`` when a record exists *and* one or more
    D-3 fields differ. Callers (sync mutating commands) should refuse to
    act in the second case and surface the mismatched field list as a
    remediation hint.

    This function is the single canonical entry point referenced by
    FR-007. Any new "before I touch sync state, am I talking to the
    right daemon?" check should call this rather than re-implementing
    the comparison.
    """
    record = read_owner_record()
    if record is None:
        return True, []
    fg = compute_foreground_identity()
    diff = mismatched_fields(record, fg)
    return (not diff), diff


# ---------------------------------------------------------------------------
# Orphan detection (FR-010 / C-002)
# ---------------------------------------------------------------------------


def is_orphan(record: DaemonOwnerRecord) -> bool:
    """Return True when the recorded daemon is no longer reconcilable.

    A record is orphaned when ANY of the following is true:

    * the recorded PID is not alive (process exited, machine rebooted), or
    * the recorded executable path no longer exists on disk (the venv was
      deleted, the binary was upgraded out from under us, etc.).

    The function is a pure predicate — it never sends a signal to any
    process (C-002). Callers that wish to clean up an orphan should call
    :func:`remove_owner_record`; they MUST NOT call ``os.kill`` against
    the recorded PID (that PID may have been recycled by an unrelated
    operator process by the time the foreground reads the record).
    """
    if not _is_process_alive(record.pid):
        return True
    try:
        if not Path(record.executable_path).exists():
            return True
    except OSError:
        # If we can't even stat the path, treat the record as orphaned
        # so the reconciliation path runs.
        return True
    return False


def list_orphan_records() -> list[DaemonOwnerRecord]:
    """Return the list of currently-orphaned owner records.

    The on-disk registry today holds a single record (``owner.json``);
    this helper exists as the canonical entry point so future work can
    extend the registry to multiple records (e.g. per scope) without
    breaking callers. The current implementation reads the single record
    and either returns ``[]`` (no record, or healthy) or ``[record]``.
    """
    record = read_owner_record()
    if record is None:
        return []
    if is_orphan(record):
        return [record]
    return []


# ---------------------------------------------------------------------------
# Convenience: build a record from current process state
# ---------------------------------------------------------------------------


def build_record_for_current_process(
    *,
    pid: int,
    port: int,
    token: str,
) -> DaemonOwnerRecord:
    """Construct a :class:`DaemonOwnerRecord` for the current process.

    This is what ``daemon.py`` calls right after binding the HTTP port:
    the daemon process *is* the foreground from its own perspective, so
    all the comparable fields are sourced from :func:`compute_foreground_identity`
    plus the supplied PID/port/token and the current UTC timestamp.
    """
    identity = compute_foreground_identity()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return DaemonOwnerRecord(
        pid=pid,
        port=port,
        token=token,
        package_version=str(identity["package_version"]),
        executable_path=str(identity["executable_path"]),
        source_checkout_path=str(identity["source_checkout_path"]),
        server_url=str(identity["server_url"]),
        auth_principal=identity.get("auth_principal"),
        auth_team=identity.get("auth_team"),
        auth_scope=identity.get("auth_scope"),
        queue_db_path=str(identity["queue_db_path"]),
        started_at=now,
    )


# Keep ``_daemon_root`` reachable from the module surface so callers that
# need to ensure the dir exists outside the write path can do so without
# re-importing daemon internals.
__all__ = [
    "DaemonOwnerRecord",
    "MISMATCH_FIELDS",
    "build_record_for_current_process",
    "check_daemon_owner_match",
    "compute_foreground_identity",
    "is_orphan",
    "list_orphan_records",
    "mismatched_fields",
    "owner_record_path",
    "read_owner_record",
    "redact_token",
    "remove_owner_record",
    "write_owner_record",
    "_daemon_root",
]
