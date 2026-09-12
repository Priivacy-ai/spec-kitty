"""Configuration helpers for the spec-kitty auth subsystem (feature 080).

Single source of truth for the *hosted SaaS target* URL. D-5 revised
(#3980, Team Kitty launch defaults): the packaged default
:data:`DEFAULT_HOSTED_SAAS_URL` IS the target — ``SPEC_KITTY_SAAS_URL`` is a
dev/self-host override of it and ``config.toml [sync].server_url`` a
per-machine configured target, with precedence resolved once by
:func:`specify_cli.auth.server_target.resolve_server_target` (env over
config over packaged default). The pre-launch "never fall back to a default"
reading died with the opt-in era: an unconfigured machine now resolves to the
packaged launch host instead of failing closed. #179's fail-closed survives
for a genuinely ambiguous env/config split-brain, which the resolver guards
before any network call.
"""

from __future__ import annotations

import os

_ENV_VAR = "SPEC_KITTY_SAAS_URL"

#: The packaged default hosted target — the Team Kitty launch host (#3980,
#: D-5 revised). Promoted from the former example-only literal
#: ``EXAMPLE_HOSTED_SAAS_URL``: it is now a functional default that
#: :func:`specify_cli.auth.server_target.resolve_server_target` falls back to
#: when neither ``SPEC_KITTY_SAAS_URL`` nor ``config.toml [sync].server_url``
#: names a target.
DEFAULT_HOSTED_SAAS_URL = "https://team.spec-kitty.ai"


def get_saas_url_env_override() -> str | None:
    """Return the ``SPEC_KITTY_SAAS_URL`` override (normalized), or ``None``.

    The env-only read the canonical resolver consumes for its
    ``env_server_url`` field: a dev/self-host override of the packaged
    default. An unset or blank variable is *no opinion* — never the default
    itself — so a configured ``config.toml`` target wins without tripping the
    split-brain guard.
    """
    raw = os.environ.get(_ENV_VAR)
    if raw is None:
        return None
    normalized = raw.strip().rstrip("/")
    return normalized or None


def get_saas_base_url() -> str:
    """Return the hosted target: the env override, else the packaged default.

    Never raises for a missing URL (D-5 revised, #3980) — the packaged default
    is the target. This accessor deliberately answers only "env override or
    packaged default"; callers that need ``config.toml`` precedence must read
    ``resolve_server_target().resolved_server_url``
    (:func:`specify_cli.auth.server_target.resolve_server_target`) instead.

    Returns:
        The hosted base URL with any trailing slashes stripped.
    """
    override = get_saas_url_env_override()
    if override is not None:
        return override
    return DEFAULT_HOSTED_SAAS_URL
