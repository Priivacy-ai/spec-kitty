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
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field as dataclass_field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import psutil

from specify_cli.sync.daemon import (
    DAEMON_EXEC_ARG_PREFIX,
    DAEMON_SCOPE_ARG_PREFIX,
    _daemon_scope_root,
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
    """
    from specify_cli.sync.queue import (  # local import: cycle-safe
        _read_server_url_for_scope,
        default_queue_db_path,
        read_queue_scope_from_credentials,
        read_queue_scope_from_session,
    )

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

    return {
        "package_version": _get_package_version(),
        "executable_path": _canonical_executable_path(sys.executable),
        "source_checkout_path": _resolve_source_checkout_path(),
        "server_url": _read_server_url_for_scope(),
        "auth_principal": auth_principal,
        "auth_team": auth_team,
        "auth_scope": scope,
        "queue_db_path": str(default_queue_db_path(allow_rehydrate=allow_network)),
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
# Scope safety (reaper-over-kill risk, #1071): reaping is scoped on THREE
# dimensions — a host-wide ``run_sync_daemon`` process is only reaped when
# (a) its cmdline carries the daemon-root scope marker
# (``daemon.DAEMON_SCOPE_ARG_PREFIX``, embedded at spawn) for THIS process's
# daemon state root, AND (b) its cmdline has the production spawn shape (a
# ``-c`` flag whose script payload references ``run_sync_daemon``), AND
# (c) its interpreter identity resolves to the SAME canonical executable as
# the foreground that is spawning — where identity is taken from
# ``Process.exe()``, ``argv[0]``, or the spawn-recorded exec marker
# (``daemon.DAEMON_EXEC_ARG_PREFIX``). The exec marker is load-bearing on
# macOS framework Python, whose re-exec rewrites BOTH ``exe()`` AND
# ``argv[0]`` to the ``Python.app`` stub. A daemon belonging to a different
# daemon root (different ``$HOME`` / container) — or one carrying no
# recognizable marker at all (spawned before the marker existed) — is left
# untouched: never kill what cannot be positively attributed to this scope.


# Per-step escalation waits (seconds). Mirror the previous ``orphan_sweep``
# budgets so existing timing characteristics are preserved.
_TERMINATE_WAIT_S: float = 1.0
_KILL_WAIT_S: float = 1.0


@dataclass(frozen=True)
class ReapResult:
    """Outcome of a canonical reap pass over scoped orphan daemons.

    ``reaped`` lists the PIDs that were terminated (or were already gone).
    ``failed`` lists ``(pid, reason)`` pairs for orphans that survived every
    escalation step. ``skipped_out_of_scope`` lists PIDs of live
    ``run_sync_daemon`` processes that were left alone because their
    interpreter does not match the foreground executable identity, or their
    cmdline daemon-root scope marker is missing or names a different daemon
    state root.
    """

    reaped: list[int] = dataclass_field(default_factory=list)
    failed: list[tuple[int, str]] = dataclass_field(default_factory=list)
    skipped_out_of_scope: list[int] = dataclass_field(default_factory=list)


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
) -> tuple[bool, str | None]:
    """Canonical kill escalation for a single daemon PID.

    Escalation: ``terminate()`` (wait up to ``terminate_wait_s``) → ``kill()``
    (wait up to ``kill_wait_s``). Returns ``(reaped, failure_reason)``.
    ``reaped`` is True when the process is gone after escalation (including the
    race where it vanished before we acted). This is the SINGLE kill path
    consumed by the canonical reaper and by the legacy ``orphan_sweep`` /
    ``daemon`` sweep shims.
    """
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return True, None
    except psutil.AccessDenied:
        return False, "access_denied_opening_process"

    try:
        proc.terminate()
    except psutil.NoSuchProcess:
        return True, None
    except psutil.AccessDenied:
        return False, "access_denied_on_terminate"

    if _wait_for_exit(proc, terminate_wait_s):
        return True, None

    try:
        proc.kill()
    except psutil.NoSuchProcess:
        return True, None
    except psutil.AccessDenied:
        return False, "access_denied_on_kill"

    if _wait_for_exit(proc, kill_wait_s):
        return True, None
    return False, "still_alive_after_kill"


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
    recorded-singleton PID is already excluded by it. A candidate orphan is in
    scope ONLY when ALL THREE hold:

    * its cmdline carries the daemon-root scope marker
      (``daemon.DAEMON_SCOPE_ARG_PREFIX``, embedded at spawn by
      ``_spawn_sync_daemon_process``) naming THIS process's resolved daemon
      state root, and
    * its cmdline has the production spawn shape — a ``-c`` flag whose script
      payload references ``run_sync_daemon`` — so a process that merely
      mentions the daemon elsewhere in its argv is never a kill candidate,
      and
    * its interpreter identity matches *executable_scope* (defaults to this
      process's canonical interpreter); ``Process.exe()``, the first cmdline
      token, and the spawn-recorded exec marker
      (``daemon.DAEMON_EXEC_ARG_PREFIX``) are each accepted after symlink
      resolution. The exec marker is the only identity that survives macOS
      framework Python's re-exec, which rewrites BOTH ``exe()`` AND
      ``argv[0]`` to the ``Python.app`` stub.

    Anything else — different daemon root, missing/unrecognized marker
    (daemons spawned before the marker existed), non-spawn-shaped cmdline,
    unresolvable identity — is conservatively skipped: never kill what cannot
    be positively attributed to this scope. Pre-marker orphans are therefore
    no longer auto-reaped; ``sync status`` / ``sync doctor`` surface them to
    the operator (via ``scan_sync_daemons``), and clearing them is a manual
    step — no production surface invokes ``cleanup_orphan_sync_daemons``
    automatically.

    With ``dry_run=True`` no signals are sent; the report still classifies each
    orphan as in-scope (would-reap) or out-of-scope (skipped).
    """
    from specify_cli.sync.daemon import scan_sync_daemons

    scope = executable_scope or canonical_executable_scope()
    root_scope = _daemon_scope_root()
    result = ReapResult()

    report = scan_sync_daemons()
    for orphan in report.orphan_processes:
        marker = _cmdline_daemon_root_marker(orphan.cmdline)
        if marker is None or marker != root_scope:
            result.skipped_out_of_scope.append(orphan.pid)
            continue

        if not _cmdline_has_daemon_spawn_signature(orphan.cmdline):
            result.skipped_out_of_scope.append(orphan.pid)
            continue

        try:
            proc = psutil.Process(orphan.pid)
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            result.skipped_out_of_scope.append(orphan.pid)
            continue

        if scope not in _process_executable_scopes(proc, orphan.cmdline):
            result.skipped_out_of_scope.append(orphan.pid)
            continue

        if dry_run:
            result.reaped.append(orphan.pid)
            continue

        reaped, reason = _sweep_daemon_process(orphan.pid)
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
    "remove_owner_record",
    "write_owner_record",
    # _daemon_root: private symbol re-exported from daemon — removed from
    # __all__ (WP01 harden-dead-symbol-gate-01KW0RJR). Remains importable
    # as an unexported internal for intra-package use.
]
