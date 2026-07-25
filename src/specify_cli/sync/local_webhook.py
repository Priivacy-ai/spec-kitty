"""Opt-in local event webhook.

When ``SPEC_KITTY_EVENT_WEBHOOK`` names an http(s) URL, every event envelope
emitted through the module-level ``emit_*`` functions in
:mod:`specify_cli.sync.events` is additionally POSTed to that URL as JSON.

This is a generic, best-effort observability seam for external *local* tools.
It is independent of the SaaS sync flag (``is_saas_sync_enabled()``) - it fires
even when hosted sync is disabled, which is the point. When the env var is
unset the hot path is a single cheap check with zero network cost.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

EVENT_WEBHOOK_ENV = "SPEC_KITTY_EVENT_WEBHOOK"


def forward_event(event: dict[str, Any]) -> None:
    """Best-effort POST of ``event`` to the configured local webhook URL.

    Reads ``SPEC_KITTY_EVENT_WEBHOOK`` at call time so tests and long-lived
    processes observe env changes. Returns immediately when unset. Only
    http/https URLs are honoured; any other scheme is ignored. Failures are
    swallowed and debug-logged - a webhook must never break or meaningfully
    slow the CLI.
    """
    url = os.environ.get(EVENT_WEBHOOK_ENV)
    if not url:
        return

    if not url.startswith(("http://", "https://")):
        logger.debug("Ignoring non-http(s) event webhook URL: %s", url)
        return

    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(event).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=0.5) as response:  # nosec B310 - scheme restricted to http(s) above
            if response.status not in {200, 201, 202, 204}:
                logger.debug("Event webhook returned HTTP %s", response.status)
    except Exception as exc:
        logger.debug("Event webhook POST skipped: %s", exc)
