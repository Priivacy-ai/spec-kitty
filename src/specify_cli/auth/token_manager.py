"""Central token gateway for the spec-kitty auth subsystem.

Every WP that needs a bearer token awaits ``get_access_token()`` from the
process-wide :class:`TokenManager` returned by
:func:`specify_cli.auth.get_token_manager`. The manager owns the loaded
:class:`StoredSession`, persists updates via the injected
:class:`SecureStorage`, and serializes refresh attempts with a single-flight
``asyncio.Lock`` so a burst of concurrent callers produces exactly one
network refresh.

Per decision D-9 the client never hardcodes a refresh-token TTL; the
:class:`StoredSession` may carry ``refresh_token_expires_at = None`` and
``refresh_if_needed`` only treats the refresh token as expired when the
session explicitly says so.

WP02 (cli-session-survival-daemon-singleton mission) introduces a
machine-wide lock around the refresh transaction. The in-process
``asyncio.Lock`` is preserved as the same-process fast path (FR-003); the
machine-wide ``MachineFileLock`` (WP01) serialises across processes
(FR-002). Inside the machine lock,
:func:`specify_cli.auth.refresh_transaction.run_refresh_transaction`
implements the read-decide-refresh-reconcile sequence that distinguishes
stale-token rejection (preserve local session, FR-006) from current-token
rejection (clear local session, FR-005). That guard is the actual incident
fix.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import sys
import threading
from pathlib import Path

from .errors import (
    NotAuthenticatedError,
    RefreshTokenExpiredError,
    SessionInvalidError,
)
from .refresh_transaction import (
    RefreshLockTimeoutError,
    RefreshOutcome,
    RefreshRejectionCause,
    run_refresh_transaction,
)
from .secure_storage import SecureStorage
from .session import (
    StoredSession,
    Team,
    get_private_team_id,
    pick_default_team_id,
)

log = logging.getLogger(__name__)

# Refresh when the access token is within this window of expiry.
_REFRESH_BUFFER_SECONDS = 5

# Hard ceiling for the bounded refresh transaction (NFR-002).
_REFRESH_MAX_HOLD_S = 10.0

_SPEC_KITTY_DIRNAME = ".spec-kitty"


def _refresh_lock_path() -> Path:
    """Return the machine-wide refresh-lock file path.

    Mirrors the ``_daemon_root()`` pattern from ``sync/daemon.py``. On
    POSIX the file lives at ``~/.spec-kitty/auth/refresh.lock``; on Windows
    it is routed through :class:`specify_cli.paths.RuntimeRoot.auth_dir`
    so it lands beside the platform's encrypted session file.
    """
    if sys.platform == "win32":  # pragma: no cover - platform-specific
        from specify_cli.paths import get_runtime_root  # noqa: PLC0415

        return get_runtime_root().auth_dir / "refresh.lock"
    return Path.home() / _SPEC_KITTY_DIRNAME / "auth" / "refresh.lock"


class TokenManager:
    """Centralized token provisioning with single-flight refresh.

    Not a singleton: construct via the ``get_token_manager()`` factory in
    ``specify_cli.auth``. That factory guarantees process-wide sharing with
    thread-safe lazy initialization.
    """

    def __init__(
        self,
        storage: SecureStorage,
        saas_base_url: str | None = None,
    ) -> None:
        self._storage = storage
        self._session: StoredSession | None = None
        self._refresh_lock: asyncio.Lock | None = None
        # WP02 (private-teamspace-ingress-safeguards): sync rehydrate state.
        # The threading.Lock serializes sync rehydrate callers (batch.py /
        # queue.py / emitter.py) so a thundering herd produces exactly one
        # /api/v1/me GET. The negative cache is process-scoped only — never
        # persisted to disk. ``_saas_base_url`` is optional at construction
        # time; when ``None`` we resolve it lazily via ``get_saas_base_url()``
        # so existing call sites that pass only ``storage`` keep working.
        self._saas_base_url: str | None = saas_base_url
        self._membership_negative_cache: bool = False
        self._membership_lock: threading.Lock = threading.Lock()

    # ---- lock lifecycle --------------------------------------------------

    def _get_lock(self) -> asyncio.Lock:
        """Lazy-create the refresh lock inside the current event loop.

        ``asyncio.Lock`` binds to the running loop on creation, so we defer
        construction until the first ``refresh_if_needed`` call. Creating the
        lock in ``__init__`` would bind it to whatever loop happened to be
        active at import time — which is typically not the CLI's loop.
        """
        if self._refresh_lock is None:
            self._refresh_lock = asyncio.Lock()
        return self._refresh_lock

    # ---- session lifecycle ----------------------------------------------

    def load_from_storage_sync(self) -> None:
        """Synchronous load, called once at process startup by the factory.

        Storage read errors are logged and the session is left unset — the
        user can still ``spec-kitty auth login`` to re-establish a session.
        """
        try:
            self._session = self._storage.read()
        except Exception as exc:  # noqa: BLE001 — never crash on stale credentials
            log.warning("Could not load session from storage: %s", exc)
            self._session = None

    def set_session(self, session: StoredSession) -> None:
        """Persist a new session (called by AuthorizationCodeFlow / DeviceCodeFlow).

        WP02 (private-teamspace-ingress-safeguards) T007: every login / repair /
        identity-change boundary that flows through ``set_session`` resets the
        membership negative cache unconditionally. Same-user re-login also clears
        the cache — checking ``prior.email != new.email`` would miss that case.
        """
        # Clear the negative cache BEFORE persistence so a concurrent reader
        # that wakes up post-write sees a fresh-cache state.
        self._membership_negative_cache = False
        self._session = session
        self._storage.write(session)

    def clear_session(self) -> None:
        """Delete the current session (called by logout or on session-invalid).

        Raises whatever ``storage.delete()`` raises so that callers (e.g.
        ``_auth_logout.py``) can surface the failure to the user.
        """
        self._session = None
        self._storage.delete()

    def get_current_session(self) -> StoredSession | None:
        """Return the in-memory session (for ``auth status`` and diagnostics)."""
        return self._session

    @property
    def is_authenticated(self) -> bool:
        """Return True when a session exists and its refresh token is not known-expired.

        When ``refresh_token_expires_at`` is ``None`` (SaaS amendment not
        landed, per C-012), the CLI cannot decide expiry proactively and
        treats the session as still authenticated — the next refresh attempt
        will reveal any server-side expiry via ``400 invalid_grant``.
        """
        if self._session is None:
            return False
        return not self._session.is_refresh_token_expired()

    # ---- token provisioning ---------------------------------------------

    async def get_access_token(self) -> str:
        """Return a valid access token, refreshing if near expiry.

        Raises:
            NotAuthenticatedError: No session is loaded.
            RefreshTokenExpiredError: Refresh token is known-expired.
            SessionInvalidError: SaaS reported ``session_invalid`` during refresh.
            RefreshLockTimeoutError: Lock contention exceeded the bounded
                wait and persisted material is unusable. The caller should
                retry once the holding process completes.
        """
        if self._session is None:
            raise NotAuthenticatedError(
                "No active session. Run `spec-kitty auth login` to authenticate."
            )
        if self._session.is_access_token_expired(buffer_seconds=_REFRESH_BUFFER_SECONDS):
            await self.refresh_if_needed()
        # After refresh, _session is still non-None (refresh_if_needed raises on failure).
        assert self._session is not None
        token: str = self._session.access_token
        return token

    # ---- membership rehydrate (WP02) ------------------------------------

    def _resolve_saas_base_url(self) -> str:
        """Return the SaaS base URL, resolving lazily from config if unset.

        Lazy resolution lets existing call sites that pass only ``storage`` to
        ``TokenManager(...)`` continue to work; the URL is needed only on the
        rehydrate code path.
        """
        if self._saas_base_url is not None:
            return self._saas_base_url
        from .config import get_saas_base_url  # noqa: PLC0415

        url: str = get_saas_base_url()
        return url

    def rehydrate_membership_if_needed(self, *, force: bool = False) -> bool:
        """Sync one-shot ``/api/v1/me`` rehydrate.

        Returns ``True`` iff the in-memory session ends with a Private
        Teamspace membership. Returns ``False`` for: no session loaded,
        negative-cache hit (without ``force=True``), HTTP failure, or a
        successful fetch that still contained no Private Teamspace.

        Contract (see contracts/api.md §3):

        - Early-return ``True`` when the current session already exposes a
          Private Teamspace.
        - Honor the process-scoped negative cache as a fast path; ``force=True``
          bypasses it (refresh hook + explicit caller-driven retries).
        - Single-flight via ``threading.Lock``: concurrent threads that race
          on a shared-only session produce exactly one HTTP GET.
        - Recompute ``default_team_id`` via ``pick_default_team_id(teams)`` —
          the SaaS does NOT return ``default_team_id`` in ``/api/v1/me``, mirroring
          ``auth/flows/authorization_code.py:281``.
        - Persist via ``set_session`` (which also clears the negative cache).
        - Transient HTTP errors return ``False`` and DO NOT poison the cache;
          only an authoritative empty-private response sets the negative cache.
        """
        with self._membership_lock:
            session = self._session
            if session is None:
                return False
            if get_private_team_id(session.teams) is not None:
                return True
            if self._membership_negative_cache and not force:
                return False

            # Lazy import: ``auth.http.transport`` imports from
            # ``specify_cli.auth`` (for ``get_token_manager``), which would
            # circularly import this module if ``me_fetch`` were imported at
            # module load time.
            from .http.me_fetch import fetch_me_payload  # noqa: PLC0415

            try:
                payload = fetch_me_payload(
                    self._resolve_saas_base_url(),
                    session.access_token,
                )
            except Exception as exc:  # noqa: BLE001 — explicit log-and-skip boundary
                log.warning(
                    "rehydrate_membership_if_needed: /api/v1/me fetch failed: %s",
                    exc,
                )
                return False

            raw_teams = payload.get("teams", [])
            teams = [Team.from_dict(t) for t in raw_teams]
            if get_private_team_id(teams) is None:
                # Authoritative: SaaS confirmed no Private Teamspace exists for
                # this user. Set the process-scoped negative cache so direct
                # ingress paths fail fast without re-issuing the GET.
                self._membership_negative_cache = True
                return False

            # Recompute default_team_id from fresh teams (mirrors auth login at
            # auth/flows/authorization_code.py:281; SaaS does NOT return this
            # field in /api/v1/me).
            new_default_team_id = pick_default_team_id(teams)
            new_session = dataclasses.replace(
                session,
                teams=teams,
                default_team_id=new_default_team_id,
            )
            # set_session clears _membership_negative_cache unconditionally (T007).
            self.set_session(new_session)
            return True

    def _apply_post_refresh_membership_hook(self, session: StoredSession) -> None:
        """T011: rehydrate membership when a just-adopted session lacks a private team.

        Runs after every ``RefreshOutcome`` adoption branch in
        ``refresh_if_needed``. ``force=True`` because token refresh is a
        state-change boundary; the negative cache from earlier in this
        process must not block recovery.

        Sync call from inside an async method is intentional: the threading
        lock window covers only the sync HTTP GET (which has its own
        transport-level timeout), and the threading.Lock and asyncio.Lock
        protect different state.
        """
        if get_private_team_id(session.teams) is None:
            self.rehydrate_membership_if_needed(force=True)

    async def refresh_if_needed(self) -> bool:
        """Refresh the access token if it's near expiry. Single-flight.

        WP02: the body delegates to
        :func:`specify_cli.auth.refresh_transaction.run_refresh_transaction`,
        which acquires the machine-wide :class:`MachineFileLock`, reloads
        persisted material, performs the network refresh inside the lock,
        and reconciles any rejection against freshly persisted state.

        The in-process ``asyncio.Lock`` is preserved (FR-003) so a burst of
        concurrent callers in one process still produces a single transaction.

        Returns:
            True if a network refresh was performed, False if persisted
            material was adopted, no refresh was needed, or another caller
            already refreshed inside this process.

        Raises:
            NotAuthenticatedError: The session was cleared before we acquired
                the lock.
            RefreshTokenExpiredError: SaaS rejected the **current** persisted
                refresh token (FR-005). Local session is cleared.
            SessionInvalidError: SaaS reports ``session_invalid`` against the
                **current** persisted session (FR-005). Local session is cleared.
            RefreshLockTimeoutError: Could not acquire the machine-wide lock
                within the bounded wait and persisted material is unusable.
        """
        lock = self._get_lock()
        async with lock:
            # Double-check inside the lock: another task may have refreshed
            # while we were waiting for our turn.
            if self._session is None:
                raise NotAuthenticatedError("No session to refresh")
            if not self._session.is_access_token_expired(
                buffer_seconds=_REFRESH_BUFFER_SECONDS
            ):
                return False  # already refreshed by a previous caller
            if self._session.is_refresh_token_expired():
                raise RefreshTokenExpiredError(
                    "Refresh token expired. Run `spec-kitty auth login` to log in again."
                )

            # Lazy import to avoid circular dependencies: auth.flows.refresh
            # imports from specify_cli.auth (session/errors/config).
            from .flows.refresh import TokenRefreshFlow  # noqa: PLC0415

            flow = TokenRefreshFlow()
            current_session = self._session
            result = await run_refresh_transaction(
                storage=self._storage,
                in_memory_session=current_session,
                refresh_flow=flow,
                lock_path=_refresh_lock_path(),
                max_hold_s=_REFRESH_MAX_HOLD_S,
            )
            log.info(
                "refresh_transaction outcome=%s network_call=%s",
                result.outcome.value,
                result.network_call_made,
            )

            outcome = result.outcome
            if outcome is RefreshOutcome.REFRESHED:
                # storage.write happened inside the transaction.
                assert result.session is not None
                self._session = result.session
                self._apply_post_refresh_membership_hook(result.session)
                return True
            if outcome is RefreshOutcome.ADOPTED_NEWER:
                assert result.session is not None
                self._session = result.session
                self._apply_post_refresh_membership_hook(result.session)
                return False
            if outcome is RefreshOutcome.LOCK_TIMEOUT_ADOPTED:
                assert result.session is not None
                self._session = result.session
                self._apply_post_refresh_membership_hook(result.session)
                return False
            if outcome is RefreshOutcome.STALE_REJECTION_PRESERVED:
                # FR-006: another process rotated; preserve the freshly
                # persisted session, do NOT clear.
                assert result.session is not None
                self._session = result.session
                self._apply_post_refresh_membership_hook(result.session)
                return False
            if outcome is RefreshOutcome.CURRENT_REJECTION_CLEARED:
                # FR-005: storage.delete already happened inside the
                # transaction. Surface to existing callers in transport.py
                # by re-raising the canonical exception that matches the
                # original rejection — preserves FR-020 (auth status output
                # unchanged) and the existing pattern at auth/transport.py.
                self._session = None
                if result.rejection_cause is RefreshRejectionCause.SESSION_INVALID:
                    raise SessionInvalidError(
                        "Session has been invalidated server-side. "
                        "Run `spec-kitty auth login` to re-authenticate."
                    )
                raise RefreshTokenExpiredError(
                    "Refresh token expired. Run `spec-kitty auth login` to log in again."
                )
            # outcome is RefreshOutcome.LOCK_TIMEOUT_ERROR
            if result.lock_timeout_message is not None:
                raise RefreshLockTimeoutError(result.lock_timeout_message)
            raise RefreshLockTimeoutError()
