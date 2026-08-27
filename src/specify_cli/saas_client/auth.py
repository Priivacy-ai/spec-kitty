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
    1. ``SPEC_KITTY_SAAS_TOKEN`` env var. Its URL comes from
       ``SPEC_KITTY_SAAS_URL`` if set, else the canonical server target
       (:func:`specify_cli.auth.server_target.resolve_server_target`) —
       never from ``.kittify/saas-auth.json``, which a checkout controls
       (#237: a repo-local URL must not redirect an env-supplied token).
       Its ``team_slug`` comes only from ``SPEC_KITTY_TEAM_SLUG``, for the
       same reason: the file must not override the scope of an env-resolved
       token. ``.kittify/saas-auth.json`` is not read at all when both
       ``SPEC_KITTY_SAAS_TOKEN`` and ``SPEC_KITTY_SAAS_URL`` are already set.
    2. ``.kittify/saas-auth.json`` relative to *repo_root* (if provided) —
       its ``token`` paired with its own ``saas_url`` and ``team_slug``
       (falling back to ``SPEC_KITTY_SAAS_URL`` / ``SPEC_KITTY_TEAM_SLUG``
       only when the file omits them).
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
    env_url = os.environ.get("SPEC_KITTY_SAAS_URL", "").strip()
    env_token = os.environ.get("SPEC_KITTY_SAAS_TOKEN", "").strip()
    env_team_slug = os.environ.get("SPEC_KITTY_TEAM_SLUG", "").strip() or None
    team_slug = env_team_slug

    file_url = ""
    file_token = ""
    file_team_slug: str | None = None
    # Only touch the file when env hasn't already fully resolved token+url —
    # a fully-env-configured caller never needed the file before #237 either
    # (main:66-72), and reading it anyway both risks the same
    # checkout-controls-a-trusted-session hazard for team_slug below and
    # turns a merely-present malformed file into a hard failure for a caller
    # who never needed it.
    if repo_root is not None and not (env_token and env_url):
        auth_file = repo_root / ".kittify" / "saas-auth.json"
        if auth_file.exists():
            try:
                data = json.loads(auth_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise SaasAuthError(f"Failed to read .kittify/saas-auth.json: {exc}") from exc
            file_token = data.get("token", "").strip()
            file_url = data.get("saas_url", "").strip()
            file_team_slug = data.get("team_slug") or None

    # Trust boundary (#237): the URL and the bearer must come from the same
    # source. A checkout-controlled .kittify/saas-auth.json may name a
    # saas_url, but only alongside its own token — never paired with the
    # env-supplied service token, which is typically longer-lived and more
    # broadly scoped than what a checkout should be able to redirect. The
    # same invariant applies to team_slug: it is a per-request scope selector
    # (zeitgeist_client/resolution.py), so the file may only supply it
    # alongside its own token, never as an override of an env-resolved token.
    if env_token:
        token = env_token
        url = env_url or _server_target_url()
    elif file_token:
        token = file_token
        url = file_url or env_url
        team_slug = team_slug or file_team_slug
    else:
        token = ""
        url = env_url or file_url
        team_slug = team_slug or file_team_slug

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
    itself used to pick the server it authenticated against (#3406), so the
    pair names the server the token belongs to even when nothing is set in
    the current environment. ``resolve_server_target`` still fails closed on
    an ambiguous split-brain; that refusal surfaces here as ``None`` and the
    caller's own error message names what is missing.

    Every failure inside the bridge degrades to ``None`` plus a debug log:
    for the fire-and-forget status fan-out an unusable session means "stay
    silent", and for interactive callers the surrounding ``SaasAuthError``
    already says what to do. The token is only ever read from the store,
    never written anywhere.
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

    # Deliberately outside the guard above: a dead stored session is a refusal
    # that must reach interactive callers, not a silent "not available".
    return AuthContext(
        saas_url=target.resolved_server_url,
        token=_usable_access_token(manager, session),
    )


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


def _server_target_url() -> str:
    """Best-effort canonical server target URL, for pairing with an
    env-supplied token when ``SPEC_KITTY_SAAS_URL`` itself is unset (#237).

    This is a trusted source (env or ``config.toml``, never a checkout), unlike
    ``.kittify/saas-auth.json``'s ``saas_url``, which must not be honoured
    alongside an env token. Any resolution trouble (nothing configured,
    split-brain) degrades to ``""`` — the caller's own "SaaS URL not
    configured" refusal already says what to do.
    """
    try:
        return _resolved_server_target().resolved_server_url
    except Exception as exc:  # noqa: BLE001 — any resolution trouble means "no url from this source"
        logger.debug("Server target resolution unavailable for env-token pairing (%s)", exc)
        return ""


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
