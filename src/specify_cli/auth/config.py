"""Configuration helpers for the spec-kitty auth subsystem (feature 080).

Single source of truth for the SaaS base URL. Per architectural decision D-5,
there is NO hardcoded SaaS domain anywhere in the codebase — callers must set
``SPEC_KITTY_SAAS_URL`` in the environment.
"""

from __future__ import annotations

import os

from .errors import ConfigurationError

_ENV_VAR = "SPEC_KITTY_SAAS_URL"


def get_saas_base_url() -> str:
    """Return the SaaS base URL from the ``SPEC_KITTY_SAAS_URL`` environment variable.

    Target authority (WP02, contract §1): this is a **low-level env accessor**
    that the canonical resolver
    (:func:`specify_cli.sync.target_authority.resolve_sync_target`) consumes for
    its ``env_server_url`` field. It is intentionally *not* the live-target
    surface — higher-level callers asking "what target are we hitting?" must read
    ``ResolvedSyncTarget.resolved_server_url`` (which folds in ``config.toml``
    precedence and derives the queue scope) rather than calling this directly.

    Raises:
        ConfigurationError: If the env var is not set or is empty. There is NO
            fallback to a hardcoded domain — fly.io deployments use generated
            hostnames and there is no stable production domain.

    Returns:
        The SaaS base URL with any trailing slashes stripped.
    """
    url = os.environ.get(_ENV_VAR)
    if not url:
        raise ConfigurationError(
            f"{_ENV_VAR} environment variable is not set. "
            f"Set it to your spec-kitty-saas instance URL (e.g. "
            f"https://api.spec-kitty.example.com) and try again."
        )
    return url.rstrip("/")
