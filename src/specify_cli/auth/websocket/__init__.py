"""WebSocket pre-connect token provisioning for spec-kitty SaaS.

This package exposes the narrow surface used by ``sync/client.py`` (WP08) to
obtain an ephemeral WebSocket token from the SaaS ``/api/v1/ws-token``
endpoint before opening a WS upgrade. Per spec 080 FR-016 the CLI never
connects directly with the long-lived access token; instead it exchanges it
for a short-lived ``ws_token`` and passes that on the WS URL.

Only the public wrapper, the provisioner class, and the error type are
re-exported — callers should not reach into ``token_provisioning`` directly.
"""

from __future__ import annotations

from .token_provisioning import (
    WebSocketProvisioningError,
    WebSocketTokenProvisioner,
    provision_ws_token,
)

__all__ = [
    "provision_ws_token",
    "WebSocketTokenProvisioner",
    "WebSocketProvisioningError",
]
