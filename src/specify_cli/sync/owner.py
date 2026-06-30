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
import re
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field as dataclass_field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import psutil

from specify_cli.core.loopback_http import build_loopback_url
from specify_cli.sync.daemon import (
    DAEMON_EXEC_ARG_PREFIX,
    DAEMON_SCOPE_ARG_PREFIX,
    _daemon_scope_root,
    _fetch_health_payload,
    _get_package_version,
    _is_process_alive,
    _sync_root,
)
from specify_cli.sync.classification import (
    CandidateProbe,
    CleanupClass,
    DaemonIdentityRecord,
    ForegroundScope,
    HealthProbe,
    SingletonRef,
    SkipReason,
    classify_candidate,
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


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    """Coerce an optional mapping value to ``str`` while preserving ``None``."""
    value = data.get(key)
    return None if value is None else str(value)


def _record_from_mapping(data: dict[str, Any]) -> DaemonOwnerRecord:
    """Construct a :class:`DaemonOwnerRecord` from a parsed JSON mapping.

    Raises ``KeyError`` / ``TypeError`` / ``ValueError`` on missing or
    malformed fields; callers treat any such failure as "no recorded owner".
    """
    return DaemonOwnerRecord(
        pid=int(data["pid"]),
        port=int(data["port"]),
        token=str(data["token"]),
        package_version=str(data["package_version"]),
        # ``executable_path`` is canonicalized in ``DaemonOwnerRecord.__post_init__``.
        executable_path=str(data["executable_path"]),
        source_checkout_path=str(data["source_checkout_path"]),
        server_url=str(data["server_url"]),
        auth_principal=_optional_str(data, "auth_principal"),
        auth_team=_optional_str(data, "auth_team"),
        auth_scope=_optional_str(data, "auth_scope"),
        queue_db_path=str(data["queue_db_path"]),
        started_at=str(data["started_at"]),
    )


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
        return _record_from_mapping(data)
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


def remove_owner_record_if_matches(pid: int, port: int) -> bool:
    """Remove the owner record only when it still names ``pid``/``port``.

    Multiple same-scope daemons share the historical ``owner.json`` path while
    orphans are being cleaned up. A stale daemon must not delete a newer
    singleton's owner record during its own shutdown.
    """
    record = read_owner_record()
    if record is None:
        return False
    if record.pid != pid or record.port != port:
        return False
    return remove_owner_record()


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


def compute_foreground_identity(*, allow_network: bool = True) -> dict[str, Any]:
    """Build the foreground's view of the comparable identity fields.

    Returns a dict shaped like the subset of :class:`DaemonOwnerRecord`
    that participates in :func:`mismatched_fields`.

    When ``allow_network`` is false, auth scope resolution must use only
    local session/credential state. This keeps daemon control-plane startup
    responsive; any SaaS membership rehydrate can run after health is live.

    Target authority (WP02, contract §1): when an authenticated identity is
    available, the canonical
    :func:`~specify_cli.sync.target_authority.resolve_sync_target` resolver
    supplies the one ``resolved_server_url`` *and* the queue scope **derived**
    from it (folding in ``SPEC_KITTY_SAAS_URL`` precedence). The owner record's
    ``server_url``/``auth_scope``/``queue_db_path`` therefore always describe a
    single coherent target — the daemon can never scope its queue to one target
    while sync posts to another (SC-008, C-002). Unauthenticated identity keeps
    the legacy ``queue.db`` path and the raw configured URL.
    """
    from specify_cli.sync.queue import (  # local import: cycle-safe
        _legacy_queue_db_path,
        _read_server_url_for_scope,
        read_queue_scope_from_credentials,
        read_queue_scope_from_session,
    )
    from specify_cli.sync.target_authority import resolve_sync_target

    scope = read_queue_scope_from_session(allow_rehydrate=allow_network)
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

    if auth_principal is not None:
        target = resolve_sync_target(user_id=auth_principal, team_slug=auth_team)
        server_url = target.resolved_server_url
        auth_scope: str | None = target.derived_queue_scope
        queue_db_path = str(target.queue_db_path)
    else:
        server_url = _read_server_url_for_scope()
        auth_scope = None
        queue_db_path = str(_legacy_queue_db_path())

    return {
        "package_version": _get_package_version(),
        "executable_path": _canonical_executable_path(sys.executable),
        "source_checkout_path": _resolve_source_checkout_path(),
        "server_url": server_url,
        "auth_principal": auth_principal,
        "auth_team": auth_team,
        "auth_scope": auth_scope,
        "queue_db_path": queue_db_path,
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
# Canonical orphan reaper (FR-014b / FR-015 / #1071)
# ---------------------------------------------------------------------------
#
# Before this consolidation there were THREE orphan-reaping surfaces, each
# with its own detection + kill logic:
#
#   1. ``owner.is_orphan`` / ``list_orphan_records`` — record-based predicate
#      (recorded PID dead OR recorded executable gone). No kill.
#   2. ``orphan_sweep.enumerate_orphans`` / ``sweep_orphans`` — port-scan
#      (9400..9450, ``/api/health`` fingerprint) + HTTP-shutdown→terminate→kill
#      escalation.
#   3. ``daemon.scan_sync_daemons`` / ``cleanup_orphan_sync_daemons`` —
#      host-wide ``run_sync_daemon`` cmdline-scan + terminate→kill.
#
# FR-015 (C-005 net-subtraction) collapses these into ONE canonical reaper,
# keyed on the candidate's interpreter identity plus the daemon-root scope
# marker embedded in its cmdline at spawn. The single kill escalation lives in
# :func:`_sweep_daemon_process` below; the old surfaces now delegate their
# kill logic to it, and :func:`reap_orphan_daemons` is the single reaper wired
# into the daemon spawn hot path (``ensure_sync_daemon_running``).
#
# Scope safety (reaper-over-kill risk, #1071, FR-008): the kill gate is scoped on
# exactly TWO dimensions — a host-wide ``run_sync_daemon`` process is only reaped
# when (a) its cmdline carries the daemon-root scope marker
# (``daemon.DAEMON_SCOPE_ARG_PREFIX``, embedded at spawn) for THIS process's
# daemon state root, AND (b) its cmdline has the production spawn shape (a ``-c``
# flag whose script payload references ``run_sync_daemon``). Interpreter identity
# is deliberately NOT a third gate: under FR-008 a version/executable mismatch is
# *stale-version evidence* (an older daemon is still safe to reap when the two
# gates above match — that is the #2261 fix), never a reason to spare or kill on
# its own. The exec marker (``daemon.DAEMON_EXEC_ARG_PREFIX``) and ``Process.exe()``
# are still recorded for diagnostics/classification, but they no longer gate the
# kill — see the gate at the top of ``reap_orphan_daemons`` below. A daemon
# belonging to a different daemon root (different ``$HOME`` / container) — or one
# carrying no recognizable marker at all (spawned before the marker existed) — is
# left untouched: never kill what cannot be positively attributed to this scope.


# Per-step escalation waits (seconds). Mirror the previous ``orphan_sweep``
# budgets so existing timing characteristics are preserved.
_TERMINATE_WAIT_S: float = 1.0
_KILL_WAIT_S: float = 1.0


@dataclass
class ReapResult:
    """Outcome of a canonical reap pass over scoped orphan daemons.

    ``reaped`` lists the PIDs that were terminated (or were already gone).
    ``failed`` lists ``(pid, reason)`` pairs for orphans that survived every
    escalation step. ``skipped_out_of_scope`` lists PIDs of live
    ``run_sync_daemon`` processes that were left alone because their
    cmdline daemon-root scope marker is missing or names a different daemon
    state root.  Version / executable mismatch is no longer a skip gate
    (FR-008): same-scope daemons from prior versions are now reaped.
    ``skipped_details`` carries structured ``DaemonIdentityRecord`` entries
    for every skipped candidate (``cleanup_class`` + ``skip_reason``).
    """

    reaped: list[int] = dataclass_field(default_factory=list)
    failed: list[tuple[int, str]] = dataclass_field(default_factory=list)
    skipped_out_of_scope: list[int] = dataclass_field(default_factory=list)
    skipped_details: list[DaemonIdentityRecord] = dataclass_field(default_factory=list)


def canonical_executable_scope() -> str:
    """Return the canonical (symlink-resolved) interpreter path of this process.

    This is the *interpreter* dimension of the reap scope. It is necessary
    but NOT sufficient for reaping: :func:`reap_orphan_daemons` additionally
    requires a matching daemon-root scope marker in the candidate's cmdline —
    the ``$HOME`` / state-root dimension of the #1071 reaper-over-kill guard.
    """
    return _canonical_executable_path(sys.executable)


def _process_executable_scopes(
    proc: psutil.Process,
    cmdline: Sequence[str] = (),
) -> set[str]:
    """Return every canonical interpreter identity attributable to *proc*.

    Collects three identity sources, each symlink-resolved via
    :func:`_canonical_executable_path`:

    * ``Process.exe()`` — the executable image the kernel reports;
    * the first *cmdline* token — the interpreter path argv carries;
    * the spawn-recorded exec marker (``daemon.DAEMON_EXEC_ARG_PREFIX``),
      an inert argv token embedded by ``_spawn_sync_daemon_process``.

    The spawn-recorded marker is what keeps the reaper effective on macOS
    framework Python (empirically: Homebrew builds): the spawned interpreter
    re-execs the ``Resources/Python.app/Contents/MacOS/Python`` stub, so the
    running daemon's ``exe()`` AND ``argv[0]`` BOTH report the stub path and
    can never equal the foreground's ``canonical_executable_scope()``. Only
    the argv tail — preserved verbatim across the re-exec — still names the
    interpreter the spawn actually used. An empty set means nothing was
    resolvable; callers must treat the process as out-of-scope rather than
    risk killing a stranger.
    """
    scopes: set[str] = set()
    with contextlib.suppress(psutil.Error, OSError):
        exe = proc.exe()
        if exe:
            scopes.add(_canonical_executable_path(exe))
    if cmdline:
        scopes.add(_canonical_executable_path(str(cmdline[0])))
        for part in cmdline:
            text = str(part)
            if text.startswith(DAEMON_EXEC_ARG_PREFIX):
                scopes.add(
                    _canonical_executable_path(text[len(DAEMON_EXEC_ARG_PREFIX):])
                )
    return scopes


def _cmdline_daemon_root_marker(cmdline: Sequence[str]) -> str | None:
    """Extract the daemon-root scope marker from a daemon's cmdline, if any.

    Returns the marker payload (the spawning process's resolved daemon state
    root) or ``None`` when no marker is present. Daemons spawned before the
    marker existed carry none and are conservatively treated as out-of-scope.
    """
    for part in cmdline:
        text = str(part)
        if text.startswith(DAEMON_SCOPE_ARG_PREFIX):
            return text[len(DAEMON_SCOPE_ARG_PREFIX):]
    return None


def _cmdline_has_daemon_spawn_signature(cmdline: Sequence[str]) -> bool:
    """Return True when *cmdline* has the production daemon spawn shape.

    The production spawn (``daemon._spawn_sync_daemon_process``) always runs
    ``<interpreter> -c <script> …`` where the script imports and calls
    ``run_sync_daemon``. Requiring the ``-c``-adjacent script token — not
    merely *any* token mentioning ``run_sync_daemon`` — keeps a stray
    marker-bearing process (e.g. a tool invoked with a
    ``…run_sync_daemon….py`` script path) out of the kill set.
    """
    parts = [str(part) for part in cmdline]
    return any(
        part == "-c" and "run_sync_daemon" in parts[index + 1]
        for index, part in enumerate(parts[:-1])
    )


def _sweep_daemon_process(
    pid: int,
    *,
    terminate_wait_s: float = _TERMINATE_WAIT_S,
    kill_wait_s: float = _KILL_WAIT_S,
) -> tuple[bool, str | None, str | None]:
    """Canonical kill escalation for a single daemon PID.

    Escalation: ``terminate()`` (wait up to ``terminate_wait_s``) → ``kill()``
    (wait up to ``kill_wait_s``). Returns
    ``(reaped, cleanup_path, failure_reason)`` where ``cleanup_path`` is
    ``terminate`` or ``kill`` when a signal step actually closed the process.
    ``reaped`` is True when the process is gone after escalation (including the
    race where it vanished before we acted). This is the SINGLE kill path
    consumed by the canonical reaper and by the legacy ``orphan_sweep`` /
    ``daemon`` sweep shims.
    """
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return True, None, None
    except psutil.AccessDenied:
        return False, None, "access_denied_opening_process"

    try:
        proc.terminate()
    except psutil.NoSuchProcess:
        return True, None, None
    except psutil.AccessDenied:
        return False, None, "access_denied_on_terminate"

    if _wait_for_exit(proc, terminate_wait_s):
        return True, "terminate", None

    try:
        proc.kill()
    except psutil.NoSuchProcess:
        return True, None, None
    except psutil.AccessDenied:
        return False, None, "access_denied_on_kill"

    if _wait_for_exit(proc, kill_wait_s):
        return True, "kill", None
    return False, None, "still_alive_after_kill"


def _wait_for_exit(proc: psutil.Process, timeout_s: float) -> bool:
    """Wait up to ``timeout_s`` for *proc* to exit; return True once it is gone."""
    wait_fn = getattr(proc, "wait", None)
    if callable(wait_fn):
        try:
            wait_fn(timeout=timeout_s)
            return True
        except psutil.TimeoutExpired:
            pass
        except psutil.NoSuchProcess:
            return True
        except TypeError:
            # Test doubles may stub ``wait()`` without a ``timeout`` kwarg.
            with contextlib.suppress(Exception):
                wait_fn(timeout_s)
                return True
    return not _is_process_alive(proc.pid)


_HEALTH_ENDPOINT_PATH: str = "/api/health"
_PORT_IN_SCRIPT_RE: re.Pattern[str] = re.compile(r"run_sync_daemon\(\s*(\d+)")


def _extract_port_from_cmdline(cmdline: Sequence[str]) -> int | None:
    """Parse the daemon port from the ``-c`` script token in a spawn cmdline.

    The spawn script is ``run_sync_daemon({port}, {repr(token)})``, so the port
    is the first integer argument to ``run_sync_daemon``.  Returns ``None`` when
    no matching token is found.
    """
    for part in cmdline:
        m = _PORT_IN_SCRIPT_RE.search(str(part))
        if m:
            return int(m.group(1))
    return None


def _probe_health(port: int) -> HealthProbe:
    """Fetch ``/api/health`` for *port* and return a populated ``HealthProbe``.

    All network failures result in ``HealthProbe(responded=False, ...)``.
    ``owner_pid`` / ``owner_port`` are taken from the ``owner`` sub-dict in
    the health payload (the redacted record the daemon self-reports).
    """
    url = build_loopback_url(port, _HEALTH_ENDPOINT_PATH)
    data = _fetch_health_payload(url)
    if not data:
        return HealthProbe(
            responded=False,
            status=None,
            protocol_version=None,
            package_version=None,
            daemon_family=None,
            owner_pid=None,
            owner_port=None,
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
        )
    owner_block: dict[str, Any] = data.get("owner") or {}
    return HealthProbe(
        responded=True,
        status=data.get("status"),
        protocol_version=data.get("protocol_version"),
        package_version=data.get("package_version"),
        daemon_family=data.get("daemon_family"),
        owner_pid=owner_block.get("pid"),
        owner_port=owner_block.get("port"),
        queue_db_path=owner_block.get("queue_db_path"),
        auth_scope=owner_block.get("auth_scope"),
        server_url=owner_block.get("server_url"),
    )


def _classify_orphan(
    orphan_pid: int,
    orphan_cmdline: Sequence[str],
    foreground: ForegroundScope,
    *,
    health: HealthProbe | None = None,
) -> DaemonIdentityRecord:
    """Classify one orphan candidate via ``classify_candidate``.

    Extracts the daemon-root marker, spawn-shape flag, and executable summary
    from the cmdline using existing helpers.  Passes the caller-supplied
    *health* probe (or ``None`` for cmdline-only startup classification; callers
    that have port access may supply a live probe to get a fully-populated
    record per the normative decision table).

    ``health=None`` means the daemon's responsiveness was not checked; the
    classifier returns ``operator_required/unresponsive`` for any candidate
    that passes rows 1–6 but lacks a health self-report (D-01).  The startup
    reaper's kill gate is the scope marker + spawn shape (see
    ``reap_orphan_daemons``), so the classifier result is used for structured
    reporting / ``skipped_details`` in that context.

    This is the testable unit extracted to keep ``reap_orphan_daemons``
    complexity ≤ 15 (Sonar S3776 / ruff C901).
    """
    singleton_scope_id = _cmdline_daemon_root_marker(orphan_cmdline)
    spawn_shape_ok = _cmdline_has_daemon_spawn_signature(orphan_cmdline)

    exe_summary: str | None = None
    with contextlib.suppress(psutil.Error, OSError):
        proc = psutil.Process(orphan_pid)
        scopes = _process_executable_scopes(proc, orphan_cmdline)
        exe_summary = ", ".join(sorted(scopes)) if scopes else None

    port = _extract_port_from_cmdline(orphan_cmdline)

    probe = CandidateProbe(
        port=port if port is not None else 0,
        listener_pid=orphan_pid,
        health=health,
        singleton_scope_id=singleton_scope_id,
        spawn_shape_ok=spawn_shape_ok,
        executable_summary=exe_summary,
        owner_present=False,
    )
    return classify_candidate(probe, foreground)


def reap_orphan_daemons(
    *,
    executable_scope: str | None = None,
    dry_run: bool = False,
) -> ReapResult:
    """Canonical reaper: terminate stale ``run_sync_daemon`` orphans in scope.

    This is the ONE reaper (FR-015) wired into the ``ensure_sync_daemon_running``
    spawn hot path so every spawn reaps stale orphans belonging to THIS daemon
    scope first (FR-014b / #1071).

    Discovery reuses the host-wide cmdline-scan (``scan_sync_daemons``); the
    recorded-singleton PID is already excluded by it.

    **Kill authority — daemon-root scope marker is primary (FR-008).**
    A candidate is in scope when BOTH of the following hold:

    * its cmdline carries the daemon-root scope marker naming THIS process's
      resolved daemon state root, AND
    * its cmdline has the production spawn shape (``-c`` flag referencing
      ``run_sync_daemon``).

    Executable / version identity (the old third condition) is **stale-version
    evidence only and is NOT a kill gate (FR-008)**.  Same-scope daemons from
    a prior installed version therefore flip from skipped → reaped — this is
    the direct fix for the 18-orphan accumulation reported in #2261.

    Conservative protections preserved (T009):
    * Pre-marker daemons (no scope arg) → ``operator_required/pre_marker``:
      not reaped; surfaced by ``sync status`` / ``sync doctor``.
    * Cross-root daemons (marker ≠ this root) → ``operator_required/cross_root``:
      not reaped; requires ``auth doctor --reset --force`` (WP05).
    * The recorded singleton is never in ``orphan_processes`` (already excluded
      by ``scan_sync_daemons``), so it is never a kill candidate.
    * ``owner.json`` (``read_owner_record``) is never consulted for kill
      decisions (FR-003); ``skipped_details`` carries classification records
      for observability only.

    ``executable_scope`` is accepted for backward compatibility but is no longer
    used in the kill decision (FR-008); it is carried in ``ForegroundScope``
    for diagnostic / skip-details enrichment only.

    With ``dry_run=True`` no signals are sent; in-scope candidates still appear
    in ``result.reaped`` to indicate they *would* be reaped.
    """
    from specify_cli.sync.daemon import scan_sync_daemons

    root_scope = _daemon_scope_root()
    foreground = ForegroundScope(
        scope_id=root_scope,
        # FR-008: executable_scope is evidence only, not a kill gate.
        executable_scope=executable_scope or canonical_executable_scope(),
        singleton=SingletonRef(pid=None, port=None),
    )
    result = ReapResult()

    report = scan_sync_daemons()
    for orphan in report.orphan_processes:
        port = _extract_port_from_cmdline(orphan.cmdline)
        health = _probe_health(port) if port is not None else None
        record = _classify_orphan(orphan.pid, orphan.cmdline, foreground, health=health)

        if record.cleanup_class != CleanupClass.SAFE_AUTO:
            if record.skip_reason in {
                SkipReason.cross_root,
                SkipReason.pre_marker,
                SkipReason.missing_pid,
            }:
                result.skipped_out_of_scope.append(orphan.pid)
            result.skipped_details.append(record)
            continue

        if not record.spawn_shape_ok:
            result.skipped_out_of_scope.append(orphan.pid)
            result.skipped_details.append(record)
            continue

        if dry_run:
            result.reaped.append(orphan.pid)
            continue

        reaped, _cleanup_path, reason = _sweep_daemon_process(orphan.pid)
        if reaped:
            result.reaped.append(orphan.pid)
        else:
            result.failed.append((orphan.pid, reason or "unknown_failure"))

    return result


# ---------------------------------------------------------------------------
# Convenience: build a record from current process state
# ---------------------------------------------------------------------------


def build_record_for_current_process(
    *,
    pid: int,
    port: int,
    token: str,
    allow_network: bool = True,
) -> DaemonOwnerRecord:
    """Construct a :class:`DaemonOwnerRecord` for the current process.

    This is what ``daemon.py`` calls right after binding the HTTP port:
    the daemon process *is* the foreground from its own perspective, so
    all the comparable fields are sourced from :func:`compute_foreground_identity`
    plus the supplied PID/port/token and the current UTC timestamp.

    Daemon startup passes ``allow_network=False`` for the initial owner
    record so TeamSpace membership rehydrate can never delay the first
    health response.
    """
    identity = compute_foreground_identity(allow_network=allow_network)
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
    # MISMATCH_FIELDS: demoted — intra-module constant; no cross-module src/
    # from-import callers (WP01 harden-dead-symbol-gate-01KW0RJR).
    # ReapResult: demoted — no cross-module src/ from-import callers (WP01).
    "build_record_for_current_process",
    # canonical_executable_scope: demoted — no cross-module src/ from-import
    # callers (WP01 harden-dead-symbol-gate-01KW0RJR).
    # check_daemon_owner_match: demoted — no cross-module src/ callers;
    # only exercised by tests (WP01 harden-dead-symbol-gate-01KW0RJR).
    "compute_foreground_identity",
    "is_orphan",
    "list_orphan_records",
    "mismatched_fields",
    "owner_record_path",
    "read_owner_record",
    "reap_orphan_daemons",
    "redact_token",
    # remove_owner_record: internal primitive; runtime callers use the
    # pid/port-guarded remove_owner_record_if_matches wrapper.
    "remove_owner_record_if_matches",
    "write_owner_record",
    # _daemon_root: private symbol re-exported from daemon — removed from
    # __all__ (WP01 harden-dead-symbol-gate-01KW0RJR). Remains importable
    # as an unexported internal for intra-package use.
]
