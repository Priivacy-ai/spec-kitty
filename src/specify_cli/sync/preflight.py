"""Sync boundary preflight: reusable gate for SaaS-producing CLI commands.

This module composes the existing daemon-owner and queue-detection helpers
into a structured :class:`PreflightResult` that downstream CLI entry points
(``sync now``, ``setup-plan``, etc.) call into before producing any
SaaS-visible work.

The preflight is read-only: it never mutates queue state, never writes to
the owner record, and never makes a SaaS HTTP round-trip. It exists so
sync-producing commands can refuse early, with a structured diagnosis of
*why*, when the daemon owner record disagrees with the foreground process
on any of the six canonical D-3 fields, when an orphan owner record is
present, when legacy queue rows still belong to the active scope, or
when hosted auth is required but absent.

The six canonical mismatch field names (per ``spec.md`` Domain Language)
are intentionally fixed and surface in operator-facing output:

- ``daemon_package_version``
- ``daemon_executable_path``
- ``daemon_source_path``
- ``daemon_server_url``
- ``daemon_team_or_user``
- ``daemon_queue_db_path``

Cross-platform contract (C-008): every file-system path is a
``pathlib.Path``; home-directory lookups go through ``Path.home()``
(resolves ``USERPROFILE`` on Windows, ``HOME`` on POSIX). Tests isolate
the operator's home by patching ``pathlib.Path.home()`` so the same
fixtures run on Linux, macOS, and Windows 10+.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from rich.console import Console
from rich.table import Table

from specify_cli.sync.owner import (
    DaemonOwnerRecord,
    _canonical_executable_path,
    is_orphan,
    list_orphan_records,
    owner_record_path,
    read_owner_record,
)


__all__ = [
    "run_preflight",
    "build_boundary_failure_set",
]


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


MismatchField = Literal[
    "daemon_package_version",
    "daemon_executable_path",
    "daemon_source_path",
    "daemon_server_url",
    "daemon_team_or_user",
    "daemon_queue_db_path",
]


# Canonical order — the operator-facing output renders rows in this order so
# the visual layout stays stable across invocations (NFR-004).
_CANONICAL_FIELD_ORDER: tuple[MismatchField, ...] = (
    "daemon_package_version",
    "daemon_executable_path",
    "daemon_source_path",
    "daemon_server_url",
    "daemon_team_or_user",
    "daemon_queue_db_path",
)


_UNSET_PLACEHOLDER = "<unset>"


# Remediation hints, keyed by canonical field name. Kept short so the
# refusal output fits within the NFR-004 25-line budget.
#
# The four "restart-class" mismatches (package_version, executable_path,
# source_path, queue_db_path) all share a single canonical remedy phrase
# so a future grep stays uniform and the operator sees one consistent
# action: run `spec-kitty doctor restart-daemon`, then verify with
# `spec-kitty sync status --check`. The two auth-class mismatches
# (server_url, team_or_user) keep their own phrasing because their
# remedy involves an auth step before the restart.
_RESTART_DAEMON_REMEDY: str = (
    "Run `spec-kitty doctor restart-daemon` to restart the daemon at the "
    "foreground version/source, then verify with `spec-kitty sync status "
    "--check`."
)

_REMEDIATION_HINTS: dict[MismatchField, str] = {
    "daemon_package_version": _RESTART_DAEMON_REMEDY,
    "daemon_executable_path": _RESTART_DAEMON_REMEDY,
    "daemon_source_path": _RESTART_DAEMON_REMEDY,
    "daemon_server_url": (
        "Reauthenticate (`spec-kitty auth login`) or restart the daemon "
        "against the matching server."
    ),
    "daemon_team_or_user": (
        "Re-authenticate as the foreground team/user (`spec-kitty auth "
        "logout` then `spec-kitty auth login`) and then run `spec-kitty "
        "doctor restart-daemon`."
    ),
    "daemon_queue_db_path": _RESTART_DAEMON_REMEDY,
}


@dataclass(frozen=True)
class ForegroundIdentity:
    """Comparable identity of the foreground (operator-invoked) CLI process.

    See ``data-model.md`` for invariants. Both ``server_url`` and
    ``team_or_user`` are ``None`` exactly when hosted auth is absent;
    they are never one-without-the-other.
    """

    package_version: str
    executable_path: Path
    source_path: Path
    server_url: str | None
    team_or_user: str | None
    queue_db_path: Path
    pid: int


@dataclass(frozen=True)
class OwnerMismatch:
    """A single canonical-field disagreement between foreground and daemon."""

    field: MismatchField
    foreground_value: str
    daemon_value: str
    remediation_hint: str


@dataclass(frozen=True)
class PreflightResult:
    """Structured outcome of :func:`run_preflight`.

    Frozen for hash-stability so downstream tests can snapshot the result.
    """

    ok: bool
    mismatches: tuple[OwnerMismatch, ...] = ()
    orphan_records: tuple[DaemonOwnerRecord, ...] = ()
    legacy_event_rows: int = 0
    legacy_body_upload_rows: int = 0
    auth_present: bool = False
    auth_required: bool = True
    # Defensive: keep an internal field reserved for future expansion without
    # breaking the frozen-dataclass equality contract.
    _reserved: tuple[()] = field(default=(), repr=False, compare=False)

    @property
    def legacy_rows_for_scope(self) -> int:
        """Total legacy rows belonging to the current scope (event + body)."""
        return self.legacy_event_rows + self.legacy_body_upload_rows

    # ------------------------------------------------------------------
    # Human-readable rendering
    # ------------------------------------------------------------------

    def render(self, console: Console) -> None:
        """Render a refusal block to *console*.

        No-op when :attr:`ok` is ``True``. The total output is bounded to
        ``≤ 25`` visible lines for ``≤ 6`` mismatches and ``≤ 3`` orphan
        records (NFR-004).
        """
        if self.ok:
            return

        n_mis = len(self.mismatches)
        n_orphan = len(self.orphan_records)
        k_legacy = self.legacy_rows_for_scope

        console.print(
            f"Sync boundary refused: {n_mis} mismatched field(s); "
            f"{n_orphan} orphan daemon record(s); {k_legacy} legacy rows "
            f"in scope."
        )

        if self.mismatches:
            console.print(_build_mismatch_table(self.mismatches))

        # Remediation bullets — compressed for the NFR-004 25-line budget
        # at 80 columns. Most daemon-field mismatches share a single
        # ``restart-daemon`` remediation, so the worst case (all six
        # canonical fields disagree) emits at most three mismatch bullets:
        #
        # 1. one combined ``restart-daemon`` bullet for the four restart-
        #    class fields (package_version / executable_path / source_path /
        #    queue_db_path);
        # 2. one ``daemon_server_url`` bullet (reauth or restart against
        #    matching server);
        # 3. one ``daemon_team_or_user`` bullet (switch team/user or
        #    restart).
        #
        # ``daemon_server_url`` and ``daemon_team_or_user`` keep their own
        # bullets because their remediations differ from the simple
        # restart-daemon path (they involve auth).
        remediation_lines = _build_remediation_lines(
            self.mismatches,
            orphan_count=n_orphan,
            legacy_rows=k_legacy,
            auth_required=self.auth_required,
            auth_present=self.auth_present,
        )
        if remediation_lines:
            console.print("Remediation:")
            for line in remediation_lines:
                console.print(line)

    # ------------------------------------------------------------------
    # JSON serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of the result.

        Used by ``--json`` flag paths in ``sync status --check`` and the
        preflight's optional debug surface.
        """
        return {
            "ok": self.ok,
            "mismatches": [
                {
                    "field": m.field,
                    "foreground_value": m.foreground_value,
                    "daemon_value": m.daemon_value,
                    "remediation_hint": m.remediation_hint,
                }
                for m in self.mismatches
            ],
            "orphan_records": [
                _orphan_record_to_dict(record) for record in self.orphan_records
            ],
            "legacy_event_rows": self.legacy_event_rows,
            "legacy_body_upload_rows": self.legacy_body_upload_rows,
            "legacy_rows_for_scope": self.legacy_rows_for_scope,
            "auth_present": self.auth_present,
            "auth_required": self.auth_required,
        }


def _orphan_record_to_dict(record: DaemonOwnerRecord) -> dict[str, Any]:
    """Render an orphan record as a plain dict (token redacted)."""
    data: dict[str, Any] = dict(record.as_dict())
    if "token" in data:
        data["token"] = "<redacted>"  # noqa: S105 - intentional redaction marker
    return data


def _build_mismatch_table(mismatches: tuple[OwnerMismatch, ...]) -> Table:
    """Build a stable mismatch table ordered by canonical field sequence."""
    table = Table(title=None, show_lines=False)
    table.add_column("Field", style="bold")
    table.add_column("Foreground")
    table.add_column("Daemon")
    by_field: dict[MismatchField, OwnerMismatch] = {m.field: m for m in mismatches}
    for field_name in _CANONICAL_FIELD_ORDER:
        mismatch = by_field.get(field_name)
        if mismatch is None:
            continue
        table.add_row(
            mismatch.field,
            mismatch.foreground_value,
            mismatch.daemon_value,
        )
    return table


def _build_remediation_lines(
    mismatches: tuple[OwnerMismatch, ...],
    *,
    orphan_count: int,
    legacy_rows: int,
    auth_required: bool,
    auth_present: bool,
) -> list[str]:
    """Return the compressed remediation bullets for a preflight failure."""
    remediation_lines: list[str] = []
    mismatch_fields = {m.field for m in mismatches}
    restart_class: tuple[MismatchField, ...] = (
        "daemon_package_version",
        "daemon_executable_path",
        "daemon_source_path",
        "daemon_queue_db_path",
    )
    if any(field_name in mismatch_fields for field_name in restart_class):
        remediation_lines.append(f"  • {_RESTART_DAEMON_REMEDY}")
    if "daemon_server_url" in mismatch_fields:
        remediation_lines.append(
            "  • Reauthenticate (`spec-kitty auth login`) or restart "
            "the daemon against the matching server."
        )
    if "daemon_team_or_user" in mismatch_fields:
        remediation_lines.append(
            "  • Re-authenticate as the foreground team/user "
            "(`spec-kitty auth logout` then `spec-kitty auth login`) "
            "and then run `spec-kitty doctor restart-daemon`."
        )
    if orphan_count:
        remediation_lines.append(
            f"  • Run `spec-kitty doctor orphan-daemons` to clean up "
            f"{orphan_count} orphan daemon record(s)."
        )
    if legacy_rows > 0:
        remediation_lines.append(
            f"  • Run `spec-kitty sync now` to flush {legacy_rows} legacy "
            f"rows for the current scope after the boundary is coherent."
        )
    if auth_required and not auth_present:
        remediation_lines.append(
            "  • Run `spec-kitty auth login` — SaaS sync enabled but "
            "no authenticated identity is available."
        )
    return remediation_lines


# ---------------------------------------------------------------------------
# Foreground identity collection
# ---------------------------------------------------------------------------


def _resolve_source_path() -> Path:
    """Return the resolved root of the installed ``specify_cli`` package.

    Mirrors the same algorithm the daemon uses (``parents[2]`` from the
    package's ``__file__``) so foreground and daemon values compare cleanly
    when both processes share an interpreter.
    """
    import specify_cli  # local import keeps module import-time cheap

    src_file = getattr(specify_cli, "__file__", None)
    if src_file is None:
        # Pathological case — fall back to a stable but well-defined path.
        return Path(sys.prefix).resolve()
    return Path(src_file).resolve().parents[2]


def _read_queue_scope_local_only() -> str | None:
    """Read the queue scope from already-persisted local state only.

    Cycle-3 read-only fix: the public helper
    ``specify_cli.sync.queue.read_queue_scope_from_session`` calls
    ``resolve_private_team_id_for_ingress`` which can transitively invoke
    ``TokenManager.rehydrate_membership_if_needed()`` — and that issues a
    ``GET /api/v1/me`` HTTP request when the in-memory session lacks a
    Private Teamspace. That violates the preflight contract
    (``contracts/sync-boundary-preflight.md``: "The helper does not mutate
    state and does not call SaaS endpoints").

    This helper replicates the on-disk-only portion of that logic:

    1. Inspect the in-memory ``TokenManager`` session (no rehydrate). If
       the session already exposes a Private Teamspace, derive the scope
       from it via the pure helper :func:`require_private_team_id`.
    2. Otherwise, fall back to reading credentials directly from disk via
       :func:`read_queue_scope_from_credentials`, which is a pure TOML
       read with no SaaS round-trip.
    3. If neither path yields a scope, return ``None`` — the preflight
       then treats the foreground as unauthenticated for queue-path
       purposes, which is the correct read-only outcome.

    Never calls ``resolve_private_team_id_for_ingress`` and never reaches
    ``rehydrate_membership_if_needed``.

    Target authority (WP02, contract §1): the scope is **derived** from
    :func:`~specify_cli.sync.target_authority.resolve_sync_target`
    (``derived_queue_scope`` = resolved URL + identity), never re-derived here
    from a self-read URL. So preflight, the owner record, and sync all key off
    the same resolved target even when ``SPEC_KITTY_SAAS_URL`` overrides
    ``config.toml`` (SC-008). The resolver is purely descriptive — it opens no
    connection, so the read-only/no-SaaS contract is preserved.
    """
    identity = _read_scope_identity_local_only()
    if identity is None:
        return None
    email, team_id = identity

    from specify_cli.sync.target_authority import resolve_sync_target

    # ``specify_cli.*`` cross-package imports are ``Any`` to mypy
    # (follow_imports=skip); coerce ``derived_queue_scope`` (a ``str``) at the
    # typed boundary.
    return str(resolve_sync_target(user_id=email, team_slug=team_id).derived_queue_scope)


def _read_scope_identity_local_only() -> tuple[str, str] | None:
    """Return ``(email, team_id)`` from local session/credentials only — no SaaS.

    Strictly on-disk / in-memory reads: the in-memory ``TokenManager`` session
    is inspected via the **pure** :func:`require_private_team_id` (never the
    rehydrating ``resolve_private_team_id_for_ingress``), then the on-disk
    ``credentials`` TOML. Returns ``None`` when no authenticated identity can be
    resolved locally, which the preflight treats as unauthenticated.
    """
    # Local imports keep module import-time cheap and avoid top-level
    # cycles with sync.queue / auth.
    from specify_cli.auth.manager import get_token_manager
    from specify_cli.auth.session import StoredSession, require_private_team_id
    from specify_cli.sync.queue import read_queue_scope_from_credentials

    # Step 1: try the in-memory session via PURE helpers only.
    session: StoredSession | None
    try:
        token_manager = get_token_manager()
        session = token_manager.get_current_session()
    except Exception:
        session = None

    if session is not None and session.email:
        # ``require_private_team_id`` is a pure function (no I/O, no
        # mutation) — see specify_cli.auth.session. It returns ``None``
        # without attempting any rehydrate when the in-memory session
        # has no Private Teamspace, which is exactly the read-only
        # behaviour the preflight contract requires.
        team_id = require_private_team_id(session)
        if team_id is not None:
            return session.email, team_id

    # Step 2: fall back to the on-disk credentials file (TOML read,
    # no SaaS round-trip). Canonical scope is ``server|user|team``.
    credentials_scope: str | None = read_queue_scope_from_credentials()
    if credentials_scope:
        parts = credentials_scope.split("|")
        if len(parts) == 3 and parts[1]:
            return parts[1], parts[2] or "no-team"
    return None


def _resolve_queue_db_path_readonly() -> Path:
    """Return the active queue DB path without triggering migration or SaaS.

    ``specify_cli.sync.queue.default_queue_db_path`` resolves the same path
    but invokes ``_migrate_legacy_queue_to_scope`` as a side effect when an
    auth scope is present (queue.py:797). Calling it from the preflight
    would violate the read-only contract (T003) and silently move legacy
    rows out of the legacy DB the preflight is supposed to *report on*.

    Additionally, ``read_queue_scope_from_session`` (which the prior
    cycle-2 fix used) can transitively reach
    ``TokenManager.rehydrate_membership_if_needed()`` → ``GET /api/v1/me``
    when the in-memory session lacks a Private Teamspace, which would be a
    SaaS round-trip from inside the preflight. Cycle-3 routes through
    :func:`_read_queue_scope_local_only` instead — strictly on-disk /
    in-memory reads, no SaaS.

    Returns the legacy ``~/.spec-kitty/queue.db`` for unauthenticated
    sessions and the scoped path under ``~/.spec-kitty/queues/`` for
    authenticated sessions, without touching either DB.
    """
    # Local import keeps module import-time cheap and avoids a top-level
    # cycle with sync.queue.
    from specify_cli.sync.queue import (
        _legacy_queue_db_path,
        scope_db_path,
    )

    scope = _read_queue_scope_local_only()
    if scope:
        return Path(scope_db_path(scope))
    return Path(_legacy_queue_db_path())


def collect_foreground_identity(repo_root: Path) -> ForegroundIdentity:
    """Return a :class:`ForegroundIdentity` describing the current process.

    *repo_root* is accepted for API symmetry with ``run_preflight`` and to
    keep the door open for repo-relative settings in future revisions; the
    current implementation does not consult the repo for any field.

    ``server_url`` and ``team_or_user`` are ``None`` when hosted auth is
    absent (per the data-model invariant).
    """
    del repo_root  # reserved for future use; identity is process-scoped today

    # Local imports keep this module cheap to import for callers that only
    # need the dataclasses.
    #
    # IMPORTANT (cycle-2 read-only fix): we deliberately do NOT call
    # ``specify_cli.sync.owner.compute_foreground_identity`` here, because
    # that helper internally calls ``default_queue_db_path()`` which
    # triggers ``_migrate_legacy_queue_to_scope`` as a side effect when an
    # auth scope exists (queue.py:797). That would violate T003's
    # read-only contract and erase the legacy rows the preflight is
    # supposed to report on.
    #
    # IMPORTANT (cycle-3 read-only fix): we additionally do NOT call
    # ``read_queue_scope_from_session`` here, because that helper goes
    # through ``resolve_private_team_id_for_ingress`` →
    # ``TokenManager.rehydrate_membership_if_needed`` which can issue a
    # ``GET /api/v1/me`` HTTP request when the in-memory session lacks a
    # Private Teamspace. The preflight contract forbids any SaaS
    # round-trip. We use :func:`_read_queue_scope_local_only` instead —
    # strictly on-disk + pure-function reads.
    from specify_cli.sync.daemon import _get_package_version
    from specify_cli.sync.target_authority import resolve_sync_target

    # Target authority (WP02, contract §1): resolve the one canonical target
    # ONCE from the local identity. ``server_url`` and the queue db path then
    # both describe that single resolved target (env-or-config), so the
    # foreground can never compare against the daemon on a split target
    # (SC-008). ``server_url``/``team_or_user`` stay ``None`` exactly when no
    # authenticated identity is present (data-model invariant).
    identity = _read_scope_identity_local_only()

    server_url: str | None = None
    team_or_user: str | None = None
    if identity is not None:
        email, team_id = identity
        target = resolve_sync_target(user_id=email, team_slug=team_id)
        server_url = target.resolved_server_url
        team_or_user = f"{email}/{team_id}" if team_id else str(email)
        queue_db_path = target.queue_db_path
    else:
        queue_db_path = _resolve_queue_db_path_readonly()

    executable_path = Path(_canonical_executable_path(sys.executable))
    source_path = _resolve_source_path()

    return ForegroundIdentity(
        package_version=str(_get_package_version()),
        executable_path=executable_path,
        source_path=source_path,
        server_url=server_url,
        team_or_user=team_or_user,
        queue_db_path=queue_db_path,
        pid=os.getpid(),
    )


# ---------------------------------------------------------------------------
# Mismatch detection
# ---------------------------------------------------------------------------


def _format_value(value: object) -> str:
    """Render a comparable value for display, mapping ``None`` to ``<unset>``."""
    if value is None:
        return _UNSET_PLACEHOLDER
    # Paths and strings render cleanly via str(); ints / others fall back too.
    return str(value)


def _daemon_team_or_user(record: DaemonOwnerRecord) -> str | None:
    """Render the daemon's ``team_or_user`` from its split fields.

    The on-disk record splits the identity across ``auth_principal`` and
    ``auth_team``; the canonical mismatch field combines them into a single
    ``team_or_user`` value so the operator sees one row, not two.
    """
    principal = record.auth_principal
    team = record.auth_team
    if not principal:
        return None
    if team:
        return f"{principal}/{team}"
    return str(principal)


def _build_mismatches(
    foreground: ForegroundIdentity,
    record: DaemonOwnerRecord,
) -> tuple[OwnerMismatch, ...]:
    """Compare *foreground* against *record* on each canonical D-3 field."""
    daemon_team_or_user = _daemon_team_or_user(record)

    # (canonical_field, foreground_value, daemon_value)
    # ``record.executable_path`` is already canonicalized at read time by
    # :func:`specify_cli.sync.owner._canonical_executable_path`; no defensive
    # resolve here (asymmetric resolution would re-introduce the bug this
    # canonicalization closes).
    comparisons: list[tuple[MismatchField, object, object]] = [
        ("daemon_package_version", foreground.package_version, record.package_version),
        ("daemon_executable_path", foreground.executable_path, Path(record.executable_path)),
        ("daemon_source_path", foreground.source_path, Path(record.source_checkout_path)),
        ("daemon_server_url", foreground.server_url, record.server_url or None),
        ("daemon_team_or_user", foreground.team_or_user, daemon_team_or_user),
        ("daemon_queue_db_path", foreground.queue_db_path, Path(record.queue_db_path)),
    ]

    out: list[OwnerMismatch] = []
    for field_name, fg_value, daemon_value in comparisons:
        # Skip the comparison when both sides are None (no mismatch).
        if fg_value is None and daemon_value is None:
            continue
        # Normalise to strings for stable comparison and rendering. Paths
        # compare on their resolved string form to avoid spurious diffs
        # caused by trailing separators or relative segments.
        fg_str = _format_value(fg_value)
        daemon_str = _format_value(daemon_value)
        if fg_str == daemon_str:
            continue
        out.append(
            OwnerMismatch(
                field=field_name,
                foreground_value=fg_str,
                daemon_value=daemon_str,
                remediation_hint=_REMEDIATION_HINTS[field_name],
            )
        )

    # Preserve canonical order.
    ordered: dict[MismatchField, OwnerMismatch] = {m.field: m for m in out}
    return tuple(ordered[f] for f in _CANONICAL_FIELD_ORDER if f in ordered)


# ---------------------------------------------------------------------------
# Legacy-row detection
# ---------------------------------------------------------------------------


def _count_legacy_rows_for_scope(
    foreground: ForegroundIdentity,
) -> tuple[int, int]:
    """Return ``(legacy_event_rows, legacy_body_upload_rows)`` for the scope.

    Composes the existing ``detect_legacy_rows_for_scope`` helper. WP02
    extended that helper to return a structured ``LegacyRowCounts`` value
    with named subtotals, so this wrapper just reads them off directly
    instead of bucketing per-table counts itself. We keep the
    ``isinstance``/getattr probing for forward compatibility with the
    backwards-compat dict shape exposed by ``LegacyRowCounts``.
    """
    from specify_cli.sync.queue import (
        build_queue_scope,
        detect_legacy_rows_for_scope,
    )

    scope = _build_legacy_scope(foreground, build_queue_scope)

    try:
        counts = detect_legacy_rows_for_scope(scope)
    # Defensive: never block preflight on a legacy-row query error.
    except Exception:
        return (0, 0)

    # Preferred path: the structured ``LegacyRowCounts`` exposes the
    # subtotals directly. Older fakes in tests may still return a plain
    # ``dict`` keyed by table name; handle both shapes.
    event_rows_attr = getattr(counts, "event_rows", None)
    body_rows_attr = getattr(counts, "body_upload_rows", None)
    if isinstance(event_rows_attr, int) and isinstance(body_rows_attr, int):
        return event_rows_attr, body_rows_attr

    event_rows = 0
    body_rows = 0
    items_fn = getattr(counts, "items", None)
    if items_fn is None:
        return (0, 0)
    for table_name, count in items_fn():
        if not isinstance(count, int):
            continue
        if table_name == "body_upload_queue":
            body_rows += count
        else:
            # All other migration tables (sync_events, etc.) are event-class.
            event_rows += count
    return event_rows, body_rows


def _build_legacy_scope(
    foreground: ForegroundIdentity,
    build_queue_scope: Callable[[str, str, str], str],
) -> str:
    """Build the scope string used for legacy-queue inspection."""
    if not foreground.server_url or not foreground.team_or_user:
        return ""

    if "/" in foreground.team_or_user:
        principal, team = foreground.team_or_user.split("/", 1)
    else:
        principal, team = foreground.team_or_user, "no-team"
    return build_queue_scope(foreground.server_url, principal, team)


# ---------------------------------------------------------------------------
# Single-source-of-truth failure set (WP03 T010)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundaryFailureSet:
    """Structured failure set computed from the foreground / daemon boundary.

    This is the single source of truth consumed by both ``sync status
    --check`` (in ``sync.py``) and :func:`run_preflight`. The two
    surfaces previously computed mismatches independently and could drift;
    after WP03 they share this builder.

    Fields:

    - ``foreground``: the :class:`ForegroundIdentity` used to build the
      comparison.
    - ``daemon_record``: the on-disk daemon owner record, or ``None`` when
      no record is present.
    - ``mismatches``: canonical-field disagreements between foreground
      and daemon (empty when no daemon record or daemon is orphaned).
    - ``orphan_records``: orphan owner records currently on disk.
    - ``legacy_event_rows`` / ``legacy_body_upload_rows``: subtotals
      reported by :func:`detect_legacy_rows_for_scope`.

    The set is *ok* (boundary coherent) iff all three lists are empty.
    """

    foreground: ForegroundIdentity
    daemon_record: DaemonOwnerRecord | None
    mismatches: tuple[OwnerMismatch, ...] = ()
    orphan_records: tuple[DaemonOwnerRecord, ...] = ()
    legacy_event_rows: int = 0
    legacy_body_upload_rows: int = 0

    @property
    def legacy_rows_for_scope(self) -> int:
        return self.legacy_event_rows + self.legacy_body_upload_rows

    @property
    def ok(self) -> bool:
        return (
            not self.mismatches
            and not self.orphan_records
            and self.legacy_rows_for_scope == 0
        )

    @property
    def daemon_status(self) -> Literal["present", "absent", "orphan"]:
        """Render the daemon owner record's lifecycle state."""
        if self.daemon_record is None:
            return "absent"
        if is_orphan(self.daemon_record):
            return "orphan"
        return "present"


def build_boundary_failure_set(
    *,
    foreground: ForegroundIdentity | None = None,
    repo_root: Path | None = None,
) -> BoundaryFailureSet:
    """Compute the boundary failure set from current process and disk state.

    This is the canonical builder consumed by both ``sync status --check``
    and :func:`run_preflight`. When *foreground* is omitted, the helper
    constructs one via :func:`collect_foreground_identity`.

    Read-only: no SaaS round-trip, no queue mutation, no owner-record
    write. The on-disk daemon record is read; that's it.
    """
    # ``collect_foreground_identity`` doesn't actually use repo_root today; we
    # pass through what we have so a future refactor can read repo-relative config.
    if foreground is None:
        repo_root_for_identity = repo_root if repo_root is not None else Path.cwd()
        fg = collect_foreground_identity(repo_root_for_identity)
    else:
        fg = foreground

    # 1. Owner record lookup.
    record: DaemonOwnerRecord | None = (
        read_owner_record() if owner_record_path().exists() else None
    )

    # 2. Mismatches: only when a record exists AND the daemon process is
    #    not itself orphaned (an orphan is surfaced via ``orphan_records``
    #    instead, so we don't double-count).
    mismatches: tuple[OwnerMismatch, ...] = ()
    if record is not None and not is_orphan(record):
        mismatches = _build_mismatches(fg, record)

    # 3. Orphan records currently on disk.
    orphan_records = tuple(list_orphan_records())

    # 4. Legacy-row counts for the current scope.
    legacy_event_rows, legacy_body_upload_rows = _count_legacy_rows_for_scope(fg)

    return BoundaryFailureSet(
        foreground=fg,
        daemon_record=record,
        mismatches=mismatches,
        orphan_records=orphan_records,
        legacy_event_rows=legacy_event_rows,
        legacy_body_upload_rows=legacy_body_upload_rows,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_preflight(
    *,
    repo_root: Path,
    foreground: ForegroundIdentity | None = None,
    require_auth: bool = True,
) -> PreflightResult:
    """Run the sync boundary preflight gate.

    Read-only composition of the existing daemon-owner and queue-detection
    helpers via :func:`build_boundary_failure_set`. Returns a structured
    :class:`PreflightResult` whose :attr:`PreflightResult.ok` invariant
    is::

        ok == (
            no mismatches
            and no orphan_records
            and legacy_rows_for_scope == 0
            and (auth_present or not auth_required)
        )

    Never mutates state; never makes a SaaS HTTP round-trip.
    """
    failure_set = build_boundary_failure_set(
        foreground=foreground,
        repo_root=repo_root,
    )

    fg = failure_set.foreground

    # Auth presence is layered on top of the structural failure set.
    auth_present = fg.server_url is not None and fg.team_or_user is not None

    ok = failure_set.ok and (auth_present or not require_auth)

    return PreflightResult(
        ok=ok,
        mismatches=failure_set.mismatches,
        orphan_records=failure_set.orphan_records,
        legacy_event_rows=failure_set.legacy_event_rows,
        legacy_body_upload_rows=failure_set.legacy_body_upload_rows,
        auth_present=auth_present,
        auth_required=require_auth,
    )
