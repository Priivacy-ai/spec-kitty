"""SaaS client package for the Widen Mode feature.

Provides a thin, mockable HTTP client (``SaasClient``) for calling
spec-kitty-saas endpoints used by the widen flow and prereq checker:

- ``GET /a/{team_slug}/collaboration/missions/{id}/audience-default``
- ``POST /a/{team_slug}/collaboration/decision-points/{id}/widen``
- ``GET /a/{team_slug}/collaboration/decision-points/{id}/discussion/``
- ``GET /a/{team_slug}/collaboration/integrations/``
- ``GET /api/v1/health``

All failures surface as ``SaasClientError`` or a typed subclass.  Callers
should use ``contextlib.suppress(SaasClientError)`` for non-fatal paths
(C-007 local-first).

Example::

    import contextlib
    from specify_cli.saas_client import SaasClient, SaasClientError

    client = SaasClient.from_env()
    members = []
    with contextlib.suppress(SaasClientError):
        members = client.get_audience_default(mission_id)
"""

from __future__ import annotations

from specify_cli.saas_client.auth import AuthContext, load_auth_context
from specify_cli.saas_client.client import SaasClient
from specify_cli.saas_client.endpoints import AudienceMember, DiscussionData, DiscussionMessage, WidenResponse
from specify_cli.saas_client.errors import (
    SaasAuthError,
    SaasClientError,
    SaasNotFoundError,
    SaasTimeoutError,
)

__all__ = [
    # Client
    "SaasClient",
    # Auth
    "AuthContext",
    "load_auth_context",
    # Errors
    "SaasClientError",
    "SaasTimeoutError",
    "SaasAuthError",
    "SaasNotFoundError",
    # Response shapes
    "WidenResponse",
    "AudienceMember",
    "DiscussionData",
    "DiscussionMessage",
]
