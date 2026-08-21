"""Canonical runtime sync-target authority resolver (WP01, contract §1).

This module produces the single :class:`ResolvedSyncTarget` that every hosted
and sync surface keys off: auth/readiness, WebSocket, tracker, batch posts, the
offline queue scope, and the delivery ledger. It is the core of plan concern
IC-00 (#2146) and the prerequisite every later WP depends on.

The resolver is **purely descriptive**. It:

* never opens a network connection,
* never mutates ``config.toml`` or any other file,
* never selects, opens, or migrates a queue.

It only reads ``[sync].server_url`` from ``~/.spec-kitty/config.toml`` and the
``SPEC_KITTY_SAAS_URL`` environment variable, classifies the resolution as an
:class:`OverrideMode`, and *derives* the queue scope and DB path from the
resolved target. ``derived_queue_scope`` / ``queue_db_path`` are **always**
derived from the resolved URL + identity — there is no public parameter that
injects a scope or DB path (contract §1 rule, C-002). The cached
``active_queue_scope`` is read only to produce a diagnostic status; it is never
used as authority.

Wiring the resolver into the live surfaces happens in WP02; this module just
exposes a small, stable surface: :class:`ResolvedSyncTarget` and
:func:`resolve_sync_target`.
"""

from __future__ import annotations

import logging
import hashlib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import toml

from specify_cli.auth.config import get_saas_base_url
from specify_cli.auth.errors import ConfigurationError
from specify_cli.sync.config import SyncConfig
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.queue_scope import (
    build_queue_scope,
    read_active_scope,
    read_queue_scope_from_credentials,
    read_queue_scope_from_session,
    scope_db_path,
)

# Documented default target when neither config nor env supplies one. Mirrors
# the historical default in ``SyncConfig.get_server_url`` and the queue-scope
# read in ``sync/queue.py`` so a missing config resolves byte-identically.
DEFAULT_SERVER_URL = "https://spec-kitty-dev.fly.dev"

# Mirrors ``specify_cli.auth.config._ENV_VAR``; named here so the split-brain
# message and env read share one literal (Sonar S1192).
SAAS_URL_ENV_VAR = "SPEC_KITTY_SAAS_URL"

_SPLIT_BRAIN_MESSAGE = (
    "Sync target split-brain detected before any network call: config.toml "
    "[sync].server_url={config!r} disagrees with environment "
    "{env_var}={env!r}. Either set {env_var} as an explicit whole-process "
    "override so hosted calls, queue scope, WebSocket, tracker and the "
    "delivery ledger all resolve to a single target, or remove {env_var}."
)

_LOG = logging.getLogger(__name__)


class OverrideMode(StrEnum):
    """How the env var relates to the configured target.

    Token strings are literal so JSON serialization (WP11/FR-019) round-trips.
    """

    NONE = "none"
    SETUP_ONLY = "setup_only"
    PROCESS_OVERRIDE = "process_override"


class QueueScopeStatus(StrEnum):
    """Diagnostic relationship between any cached scope and the derived scope.

    Never used as authority — the resolver always trusts the recomputed
    ``derived_queue_scope`` (contract §1 rule).
    """

    ABSENT = "absent"
    MATCHES = "matches"
    STALE_NON_AUTHORITATIVE = "stale_non_authoritative"


class SyncTargetSplitBrainError(RuntimeError):
    """Raised when env and config disagree without a clean whole-process override.

    Decided purely over strings during resolution — *before* any
    auth/readiness/WebSocket/tracker/sync call could open a connection
    (contract §1, SC-008). The message names both URLs and the source so an
    operator can reconcile ``config.toml`` and ``SPEC_KITTY_SAAS_URL``.
    """

    def __init__(self, *, configured_server_url: str | None, env_server_url: str | None) -> None:
        super().__init__(
            _SPLIT_BRAIN_MESSAGE.format(
                config=configured_server_url,
                env=env_server_url,
                env_var=SAAS_URL_ENV_VAR,
            )
        )
        self.configured_server_url = configured_server_url
        self.env_server_url = env_server_url


@dataclass(frozen=True, slots=True)
class AdmissionAudience:
    """Exact remote-admission authority tuple derived from trusted auth state."""

    normalized_server_origin: str
    account_identity: str
    private_teamspace_id: str
    project_uuid: CanonicalProjectUUID
    configuration_generation: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "project_uuid",
            CanonicalProjectUUID.parse(self.project_uuid),
        )
        if not self.normalized_server_origin.strip():
            raise ValueError("normalized server origin is required")
        if not self.account_identity.strip():
            raise ValueError("authenticated account identity is required")
        if not self.private_teamspace_id.strip():
            raise ValueError("canonical Private Teamspace identity is required")
        if self.configuration_generation < 1:
            raise ValueError("target configuration generation must be positive")

    @property
    def target_identity(self) -> str:
        """Store-facing spelling shared with :class:`TargetAudience`."""
        return self.normalized_server_origin

    def to_diagnostics_dict(self) -> dict[str, str | int]:
        """Return only pseudonymous identifiers and non-sensitive categories."""

        def pseudonym(value: str) -> str:
            return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]  # noqa: TID251 - admission-audience diagnostic pseudonym, not charter freshness

        return {
            "category": "project_sync_admission_audience",
            "origin_id": pseudonym(self.normalized_server_origin),
            "account_id": pseudonym(self.account_identity),
            "private_teamspace_id": pseudonym(self.private_teamspace_id),
            "project_id": pseudonym(self.project_uuid.storage_token),
            "configuration_generation": self.configuration_generation,
        }


def _normalize_server_origin(raw_url: str) -> str:
    """Canonicalize scheme/host/port and deliberately discard route aliases."""
    parts = urlsplit(raw_url.strip())
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("admission server URL requires an http(s) scheme and host")
    try:
        host = parts.hostname.encode("idna").decode("ascii").lower()
        port = parts.port
    except (UnicodeError, ValueError) as exc:
        raise ValueError("admission server URL has an invalid host or port") from exc
    default_port = 443 if scheme == "https" else 80
    netloc = host if port is None or port == default_port else f"{host}:{port}"
    return urlunsplit((scheme, netloc, "", "", ""))


def build_admission_audience(
    resolved_target: ResolvedSyncTarget,
    *,
    account_identity: str,
    private_teamspace_id: str,
    project_uuid: CanonicalProjectUUID | str,
    configuration_generation: int,
) -> AdmissionAudience:
    """Bind resolved origin to trusted account and canonical Teamspace metadata.

    The signature intentionally has no token, display team selector, repository
    slug, active checkout, or route-alias parameter. Those values cannot grant
    or mutate hosted admission authority.
    """
    return AdmissionAudience(
        normalized_server_origin=_normalize_server_origin(resolved_target.resolved_server_url),
        account_identity=account_identity,
        private_teamspace_id=private_teamspace_id,
        project_uuid=CanonicalProjectUUID.parse(project_uuid),
        configuration_generation=configuration_generation,
    )


@dataclass(frozen=True)
class ResolvedSyncTarget:
    """Immutable description of the single canonical sync target (contract §1).

    Every field is observable state; no method opens a network connection,
    mutates config, or selects a queue. ``derived_queue_scope`` and
    ``queue_db_path`` are derived from ``resolved_server_url`` + identity and
    are never supplied by a caller (C-002).
    """

    configured_server_url: str | None
    env_server_url: str | None
    override_mode: OverrideMode
    resolved_server_url: str
    user_id: str | None
    team_slug: str | None
    derived_queue_scope: str
    queue_db_path: Path
    active_queue_scope_status: QueueScopeStatus

    def to_diagnostics_dict(self) -> dict[str, Any]:
        """Return a JSON-safe ``target_authority`` section (WP11, contract §6).

        Enums render as their literal token strings and ``Path`` as ``str`` so
        the dict round-trips through :func:`json.dumps`.
        """
        return {
            "configured_server_url": self.configured_server_url,
            "env_server_url": self.env_server_url,
            "override_mode": self.override_mode.value,
            "resolved_server_url": self.resolved_server_url,
            "user_id": self.user_id,
            "team_slug": self.team_slug,
            "derived_queue_scope": self.derived_queue_scope,
            "queue_db_path": str(self.queue_db_path),
            "active_queue_scope_status": self.active_queue_scope_status.value,
        }


# ---------------------------------------------------------------------------
# Phase 1 — read the two target sources (T002)
# ---------------------------------------------------------------------------


def _normalize_url(url: str) -> str:
    """Normalize a URL for comparison and resolution: strip + drop trailing ``/``."""
    return url.strip().rstrip("/")


def _read_configured_server_url() -> str | None:
    """Read the raw ``[sync].server_url`` key, ``None`` when the key is absent.

    Reuses :class:`SyncConfig` for ``SPEC_KITTY_HOME``-aware path resolution but
    reads the raw key (not the defaulted value) so the "configured vs default"
    distinction survives (T002).
    """
    config_file = SyncConfig().config_file
    if not config_file.exists():
        return None
    try:
        data = toml.load(config_file)
    except (toml.TomlDecodeError, OSError):
        return None
    sync_table = data.get("sync")
    if not isinstance(sync_table, dict):
        return None
    value = sync_table.get("server_url")
    return None if value is None else str(value)


def _read_env_server_url() -> str | None:
    """Read ``SPEC_KITTY_SAAS_URL``, normalizing blank/whitespace to ``None``.

    Reuses ``auth.config.get_saas_base_url`` (and its trailing-slash stripping);
    its unset/blank :class:`ConfigurationError` maps to ``None``.
    """
    try:
        raw = get_saas_base_url()
    except ConfigurationError:
        return None
    normalized = _normalize_url(str(raw))
    return normalized or None


# ---------------------------------------------------------------------------
# Phase 2 — classify the override and choose the resolved URL (T002)
# ---------------------------------------------------------------------------


def _classify_override(
    configured_server_url: str | None,
    env_server_url: str | None,
    *,
    process_wide_override: bool,
) -> tuple[OverrideMode, str]:
    """Decide ``(override_mode, resolved_server_url)`` — pure, no I/O, no network.

    Precedence matches ``saas/readiness.py::_probe_host_config`` (env first,
    then config, then the documented default). A missing config key compares
    against :data:`DEFAULT_SERVER_URL` so env-equal-to-default is *not* an
    override and env-differs-from-default *is* an explicit override.
    """
    effective_config = _normalize_url(configured_server_url or DEFAULT_SERVER_URL)
    if env_server_url is None:
        return OverrideMode.NONE, effective_config
    env_normalized = _normalize_url(env_server_url)
    if env_normalized == effective_config:
        return OverrideMode.NONE, effective_config
    if process_wide_override:
        # Whole-process override: env wins everywhere; scope is derived from
        # this same resolved URL, so no split is possible (SC-008).
        return OverrideMode.PROCESS_OVERRIDE, env_normalized
    # Disagreement scoped to a setup/diagnostic context — the guard fails-closed.
    return OverrideMode.SETUP_ONLY, effective_config


def _guard_split_brain(
    override_mode: OverrideMode,
    configured_server_url: str | None,
    env_server_url: str | None,
) -> None:
    """Fail-closed for an ambiguous env/config disagreement (T005, SC-008).

    Pure string decision; runs during resolution before any caller could open
    a connection. ``process_override`` is allowed (consistent whole-process
    target); ``setup_only`` raises :class:`SyncTargetSplitBrainError`.
    """
    if override_mode is OverrideMode.SETUP_ONLY:
        raise SyncTargetSplitBrainError(
            configured_server_url=configured_server_url,
            env_server_url=env_server_url,
        )


# ---------------------------------------------------------------------------
# Phase 3 — derive the queue scope + DB path from the resolved target (T003)
# ---------------------------------------------------------------------------


def _ascii_token(value: str) -> str:
    """Return an ASCII-only, deterministic rendering of *value*.

    Pure-ASCII input passes through unchanged so the derived scope mirrors
    ``build_queue_scope`` byte-for-byte in the common case (no queue drift vs
    WP10's ``queue.py``); any non-ASCII code point is hex-escaped (``_uXXXX_``)
    so the produced identifier satisfies the charter Identifier Safety rule
    (``.isascii()`` is always ``True``).
    """
    if value.isascii():
        return value
    return "".join(ch if ch.isascii() else f"_u{ord(ch):04x}_" for ch in value)


def _derive_queue_scope(resolved_server_url: str, user_id: str | None, team_slug: str | None) -> str:
    """Derive the deterministic, ASCII-safe queue scope from the resolved target.

    Mirrors ``sync/queue.py::build_queue_scope`` composition exactly (server |
    user | team, normalized) so WP02/WP10 line up. Unknown identity yields a
    stable unauthenticated scope rather than failing, so capture-first local
    durability still works pre-auth (T003).
    """
    scope = build_queue_scope(
        server_url=_ascii_token(resolved_server_url),
        username=_ascii_token(user_id or ""),
        team_slug=_ascii_token(team_slug or ""),
    )
    return str(scope)


# ---------------------------------------------------------------------------
# Phase 4 — diagnose the cached scope status (T004)
# ---------------------------------------------------------------------------


def _read_session_scope() -> str | None:
    """Read the cached scope from the encrypted auth session, never raising.

    ``allow_rehydrate=False`` keeps this strictly local — no ``/api/v1/me``
    probe — so scope diagnostics stay network-free (contract §1). Any failure
    to read the session store is translated to ``None`` so a corrupt cache can
    never raise into target authority (T004 edge case).
    """
    try:
        scope = read_queue_scope_from_session(allow_rehydrate=False)
    except Exception as exc:  # translate any cache-read failure → absent
        _LOG.debug("target_authority: session scope read failed: %s", exc)
        return None
    return str(scope) if scope else None


def _read_cached_scope() -> str | None:
    """Read any persisted/cached queue scope read-only; ``None`` when absent.

    Consults, in order, the persisted ``active_queue_scope`` marker, the
    credentials file, then the encrypted session — all read-only and defensive
    (a corrupt/missing source contributes ``None``, never an exception).
    """
    marker = read_active_scope()
    if marker:
        return str(marker)
    credentials_scope = read_queue_scope_from_credentials()
    if credentials_scope:
        return str(credentials_scope)
    return _read_session_scope()


def _diagnose_scope_status(derived_queue_scope: str) -> QueueScopeStatus:
    """Classify the cached scope against the freshly derived one (pure diagnostic).

    The cached value is reported but never used to pick a queue or DB path; the
    derived value is always authoritative.
    """
    cached = _read_cached_scope()
    if cached is None:
        return QueueScopeStatus.ABSENT
    if cached == derived_queue_scope:
        return QueueScopeStatus.MATCHES
    return QueueScopeStatus.STALE_NON_AUTHORITATIVE


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def resolve_sync_target(
    *,
    user_id: str | None = None,
    team_slug: str | None = None,
    process_wide_override: bool = True,
) -> ResolvedSyncTarget:
    """Resolve the single canonical sync target (contract §1, FR-016).

    Reads ``[sync].server_url`` and ``SPEC_KITTY_SAAS_URL``, classifies the
    :class:`OverrideMode`, fails-closed on an ambiguous split-brain *before any
    network call* (SC-008), then derives the queue scope and DB path from the
    resolved URL + identity. The returned :class:`ResolvedSyncTarget` is purely
    descriptive — no network, no config mutation, no queue selection.

    Args:
        user_id: Authenticated user identity when known (an email in practice);
            ``None`` pre-auth yields a stable unauthenticated scope.
        team_slug: Authenticated team identity when known; ``None`` pre-auth.
        process_wide_override: When ``True`` (default), an env target that
            differs from config is treated as an explicit whole-process
            override (env wins everywhere, scope follows). When ``False``, the
            same disagreement is treated as a setup-only/ambiguous case and the
            split-brain guard raises :class:`SyncTargetSplitBrainError`.

    Returns:
        The resolved target with all contract §1 fields populated.

    Raises:
        SyncTargetSplitBrainError: Env disagrees with config and the override
            is not a clean whole-process one (decided before any network call).
    """
    configured_server_url = _read_configured_server_url()
    env_server_url = _read_env_server_url()
    override_mode, resolved_server_url = _classify_override(
        configured_server_url,
        env_server_url,
        process_wide_override=process_wide_override,
    )
    _guard_split_brain(override_mode, configured_server_url, env_server_url)
    derived_queue_scope = _derive_queue_scope(resolved_server_url, user_id, team_slug)
    queue_db_path = Path(scope_db_path(derived_queue_scope))
    active_queue_scope_status = _diagnose_scope_status(derived_queue_scope)
    return ResolvedSyncTarget(
        configured_server_url=configured_server_url,
        env_server_url=env_server_url,
        override_mode=override_mode,
        resolved_server_url=resolved_server_url,
        user_id=user_id,
        team_slug=team_slug,
        derived_queue_scope=derived_queue_scope,
        queue_db_path=queue_db_path,
        active_queue_scope_status=active_queue_scope_status,
    )
