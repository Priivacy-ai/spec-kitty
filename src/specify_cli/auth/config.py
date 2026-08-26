"""Configuration helpers for the spec-kitty auth subsystem (feature 080).

Single source of truth for the *hosted SaaS opt-in* base URL. Per
architectural decision D-5, :func:`get_saas_base_url` never falls back to a
default — callers must set ``SPEC_KITTY_SAAS_URL`` in the environment to opt
a machine into hosted SaaS flows (mirrored by the "D-5 opt-in gate" in
:func:`specify_cli.tracker.saas_readiness._probe_host_config`).

D-5 scopes this opt-in gate, not every SaaS-domain literal in the codebase:
:data:`specify_cli.auth.server_target.DEFAULT_SERVER_URL` is a separate,
documented default used only for descriptive resolution when neither the
env var nor ``config.toml`` supplies a target. That default never opens a
network connection and never bypasses this function's opt-in gate.
"""

from __future__ import annotations

import os

from .errors import ConfigurationError

_ENV_VAR = "SPEC_KITTY_SAAS_URL"

#: Illustrative hosted-SaaS URL, used only in operator-facing *examples* (error
#: hints, remediation notes). This is NOT a functional default: per
#: architectural decision D-5 (see module docstring) hosted activation has no
#: hardcoded fallback — callers must set ``SPEC_KITTY_SAAS_URL``. It is shared so
#: the example does not drift across the auth and sync surfaces that cite it
#: (#3441). D-5 scopes the opt-in gate, not example literals like this one.
EXAMPLE_HOSTED_SAAS_URL = "https://app.spec-kitty.ai"


def get_saas_base_url() -> str:
    """Return the SaaS base URL from the ``SPEC_KITTY_SAAS_URL`` environment variable.

    Target authority (WP02, contract §1): this is a **low-level env accessor**
    that the canonical resolver
    (:func:`specify_cli.auth.server_target.resolve_server_target`) consumes for
    its ``env_server_url`` field. It is intentionally *not* the live-target
    surface — higher-level callers asking "what target are we hitting?" must read
    ``ResolvedServerTarget.resolved_server_url`` (which folds in ``config.toml``
    precedence) rather than calling this directly.

    Raises:
        ConfigurationError: If the env var is not set or is empty. There is NO
            fallback to a hardcoded domain; callers must explicitly opt in to
            either the hosted service or a self-hosted instance.

    Returns:
        The SaaS base URL with any trailing slashes stripped.
    """
    url = os.environ.get(_ENV_VAR)
    if not url:
        raise ConfigurationError(
            f"{_ENV_VAR} environment variable is not set. "
            f"Set it to your spec-kitty-saas instance URL (e.g. "
            f"{EXAMPLE_HOSTED_SAAS_URL}) and try again."
        )
    return url.rstrip("/")
