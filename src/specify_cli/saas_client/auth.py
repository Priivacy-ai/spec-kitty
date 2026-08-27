"""Auth context loading for the SaaS client.

Reads ``SPEC_KITTY_SAAS_URL``, ``SPEC_KITTY_SAAS_TOKEN``, and optional
``SPEC_KITTY_TEAM_SLUG`` from the environment, falling back to
``.kittify/saas-auth.json`` when env vars are absent, and finally to the
OAuth session ``spec-kitty auth login`` persists (spec-kitty#198).  Raises
``SaasAuthError`` if no token — or no SaaS URL — can be resolved. Per
decision D-5 there is no hardcoded SaaS domain fallback.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specify_cli.saas_client.errors import SaasAuthError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthContext:
    """Resolved SaaS authentication context."""

    saas_url: str
    token: str
    team_slug: str | None = None  # extracted from token payload if available


def load_auth_context(repo_root: Path | None = None) -> AuthContext:
    """Load SaaS auth context.

    Resolution order:
    1. ``SPEC_KITTY_SAAS_TOKEN`` / ``SPEC_KITTY_SAAS_URL`` env vars.
    2. ``.kittify/saas-auth.json`` relative to *repo_root* (if provided).
    3. The stored OAuth session written by ``spec-kitty auth login``
       (#198): its access token as the bearer, paired with the canonical
       server target (:func:`specify_cli.auth.server_target.resolve_server_target`)
       — refreshed first through the renewable-session flow when expired.
    4. Raises ``SaasAuthError`` if no token is found, or if no SaaS URL is
       supplied by any source (D-5: no hardcoded domain fallback).

    Args:
        repo_root: Optional path to the repository root.  Used to locate
            ``.kittify/saas-auth.json`` when env vars are absent.

    Returns:
        Resolved :class:`AuthContext`.

    Raises:
        SaasAuthError: If no token can be resolved, or if no SaaS URL is
            supplied by env var, auth file, or the stored session's server
            target (D-5: no hardcoded SaaS domain fallback).
    """
    url = os.environ.get("SPEC_KITTY_SAAS_URL", "").strip()
    token = os.environ.get("SPEC_KITTY_SAAS_TOKEN", "").strip()
    team_slug = os.environ.get("SPEC_KITTY_TEAM_SLUG", "").strip() or None

    if (not token or not url) and repo_root is not None:
        auth_file = repo_root / ".kittify" / "saas-auth.json"
        if auth_file.exists():
            try:
                data = json.loads(auth_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise SaasAuthError(f"Failed to read .kittify/saas-auth.json: {exc}") from exc
            token = token or data.get("token", "").strip()
            url = url or data.get("saas_url", "").strip()
            team_slug = team_slug or data.get("team_slug") or None

    if not token:
        bridged = _oauth_session_context()
        if bridged is not None:
            # Keep the OAuth bearer and SaaS URL inside one trust boundary.
            # A repo-local auth file may name a SaaS URL, but it must not
            # redirect a personal login token to a checkout-controlled host.
            return AuthContext(
                saas_url=bridged.saas_url,
                token=bridged.token,
                team_slug=team_slug,
            )
        raise SaasAuthError("no SaaS token configured: set SPEC_KITTY_SAAS_TOKEN, provide .kittify/saas-auth.json, or run `spec-kitty auth login`")

    # D-5: there is NO hardcoded SaaS domain (see auth/config.get_saas_base_url,
    # which raises when SPEC_KITTY_SAAS_URL is unset). The URL must come from the
    # environment, the auth file, or the stored session's server target; falling
    # back to a baked-in domain silently points the client at the wrong server
    # (#2248 / #2146 canonical target authority). Fail closed instead.
    if not url:
        raise SaasAuthError('SaaS URL not configured: set SPEC_KITTY_SAAS_URL or provide "saas_url" in .kittify/saas-auth.json (D-5: no hardcoded SaaS domain).')

    return AuthContext(saas_url=url, token=token, team_slug=team_slug)


def _oauth_session_context() -> AuthContext | None:
    """The step-3 bridge to the ``spec-kitty auth login`` session (#198).

    A human on the documented path authenticates once with ``auth login``
    and never writes a service token anywhere, so when neither env nor
    ``.kittify/saas-auth.json`` carries a bearer this resolves the persisted
    OAuth session instead — otherwise ``spec-kitty routes``, the relay
    capability mint, and every other consumer of this module would refuse a
    fully authenticated laptop.

    The session's token is paired with :func:`resolve_server_target`'s
    answer — the same env-over-config-over-default resolution ``auth login``
    itself used to pick the server it authenticated against (#3406) — but
    only when that answer matches the session's own ``issuer_url``; a
    session recorded against one server is refused, not paired, when the
    resolved target now names a different one (#234).
    ``resolve_server_target`` still fails closed on an ambiguous split-brain;
    that refusal surfaces here as ``None`` and the caller's own error message
    names what is missing.

    Every *bridge-unavailable* failure degrades to ``None`` plus a debug
    log: for the fire-and-forget status fan-out an unusable session means
    "stay silent". A dead session or an issuer mismatch is different — both
    are refusals that must reach interactive callers as a ``SaasAuthError``
    naming the remedy, not silence. The token is only ever read from the
    store, never written anywhere.
    """
    try:
        manager = _token_manager()
        target = _resolved_server_target()
        session = manager.get_current_session()
    except Exception as exc:  # noqa: BLE001 — any bridge trouble means "not available"
        logger.debug("OAuth session bridge unavailable (%s)", exc)
        return None

    if session is None:
        return None

    # Deliberately outside the guard above: a dead stored session, or one
    # minted for a server other than the one resolved_server_url now names,
    # is a refusal that must reach interactive callers, not a silent "not
    # available" (#234).
    _guard_session_issuer(session, target)

    return AuthContext(
        saas_url=target.resolved_server_url,
        token=_usable_access_token(manager, session),
    )


def _guard_session_issuer(session: Any, target: Any) -> None:
    """Refuse to pair *session* with a server it was not minted for (#234).

    ``spec-kitty auth status`` has warned about this exact mismatch since
    #176 (``format_saas_mismatch_warning``) — the OAuth bridge must refuse
    the same way instead of silently sending a personal bearer to a server
    it never authenticated against. Sessions minted before #176 carry
    ``issuer_url=None``: nothing was recorded to compare, so they keep
    working unchanged.
    """
    issuer_url: str | None = session.issuer_url
    if issuer_url is None:
        return
    if _normalize_endpoint(issuer_url) == _normalize_endpoint(target.resolved_server_url):
        return
    raise SaasAuthError(
        f"Session is for {_normalize_endpoint(issuer_url)}; the resolved server now points at {target.resolved_server_url} — run `spec-kitty auth login --force`"
    )


def _normalize_endpoint(url: str) -> str:
    """Normalize a URL for endpoint comparison.

    Same semantics as ``server_target._normalize_url`` /
    ``_auth_status._normalize_endpoint`` (strip surrounding whitespace, drop
    one trailing slash); kept local so the comparison does not reach into
    another module's private helper.
    """
    return url.strip().rstrip("/")


def _token_manager() -> Any:
    """The process-wide :class:`specify_cli.auth.TokenManager`.

    Imported lazily: the auth package pulls the encrypted-store machinery,
    which nothing else in ``saas_client`` should pay for at import time (and
    which would make this module's import order matter to every CLI start).
    """
    from specify_cli.auth import get_token_manager  # noqa: PLC0415

    return get_token_manager()


def _resolved_server_target() -> Any:
    """The canonical hosted-server target (env over config over default)."""
    from specify_cli.auth.server_target import resolve_server_target  # noqa: PLC0415

    return resolve_server_target()


def _dead_session_errors() -> tuple[type[Exception], ...]:
    """Refresh failures that mean *this session is finished* — as opposed to
    transient transport/lock trouble, which must not log the user out of the
    bridge (Team Kitty will answer 401 to a truly dead held token anyway)."""
    from specify_cli.auth.errors import (  # noqa: PLC0415
        NotAuthenticatedError,
        RefreshTokenExpiredError,
        SessionInvalidError,
    )

    return (NotAuthenticatedError, RefreshTokenExpiredError, SessionInvalidError)


def _usable_access_token(manager: Any, session: Any) -> str:
    """A current access token for *session*, refreshing when it has expired.

    Raises :class:`SaasAuthError` when the renewable-session flow reports the
    stored session dead — that is a refusal, not silence: ``routes`` should
    tell the human to log in again. Transient refresh trouble (network down,
    lock contention) keeps the held token: the gateway call will surface the
    real fault, and resolution caches nothing behind a 401.
    """
    # ``specify_cli.*`` is type-checked with ``follow_imports = skip``, so the
    # cross-package session attributes are seen as ``Any``; bind to a
    # ``str``-typed local to keep the declared return type honest.
    held: str = session.access_token

    if not session.is_access_token_expired():
        return held

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        # A loop owns this thread; asyncio.run would raise. Best effort: hand
        # back what we hold rather than fail an otherwise-working checkout.
        logger.debug("OAuth session expired but an event loop owns this thread; using the held token")
        return held

    try:
        asyncio.run(manager.refresh_if_needed())
    except SaasAuthError:
        raise
    except _dead_session_errors() as exc:
        raise SaasAuthError(f"The stored spec-kitty session is no longer usable ({exc}); run `spec-kitty auth login` again.") from exc
    except Exception as exc:  # noqa: BLE001 — refresh trouble falls back to the held token
        logger.debug("OAuth session refresh failed (%s); using the held token", exc)

    refreshed = manager.get_current_session()
    if refreshed is None:
        raise SaasAuthError("The stored spec-kitty session disappeared while refreshing; run `spec-kitty auth login` again.")
    rotated: str = refreshed.access_token
    return rotated
