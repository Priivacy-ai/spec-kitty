"""Auth context loading for the SaaS client.

Reads ``SPEC_KITTY_SAAS_URL``, ``SPEC_KITTY_SAAS_TOKEN``, and optional
``SPEC_KITTY_TEAM_SLUG`` from the
environment, falling back to ``.kittify/saas-auth.json`` when env vars are
absent.  Raises ``SaasAuthError`` if no token can be resolved.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from specify_cli.saas_client.errors import SaasAuthError

_DEFAULT_SAAS_URL = "https://api.spec-kitty.io"


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
    3. Raises ``SaasAuthError`` if no token is found.

    Args:
        repo_root: Optional path to the repository root.  Used to locate
            ``.kittify/saas-auth.json`` when env vars are absent.

    Returns:
        Resolved :class:`AuthContext`.

    Raises:
        SaasAuthError: If no token can be resolved.
    """
    url = os.environ.get("SPEC_KITTY_SAAS_URL", "").strip()
    token = os.environ.get("SPEC_KITTY_SAAS_TOKEN", "").strip()
    team_slug = os.environ.get("SPEC_KITTY_TEAM_SLUG", "").strip() or None

    if not token and repo_root is not None:
        auth_file = repo_root / ".kittify" / "saas-auth.json"
        if auth_file.exists():
            try:
                data = json.loads(auth_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise SaasAuthError(f"Failed to read .kittify/saas-auth.json: {exc}") from exc
            token = data.get("token", "").strip()
            url = url or data.get("saas_url", "").strip()
            team_slug = team_slug or data.get("team_slug") or None

    if not token:
        raise SaasAuthError("SPEC_KITTY_SAAS_TOKEN not set and .kittify/saas-auth.json not found")

    if not url:
        url = _DEFAULT_SAAS_URL

    return AuthContext(saas_url=url, token=token, team_slug=team_slug)
