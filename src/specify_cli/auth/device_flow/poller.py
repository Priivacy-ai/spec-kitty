"""Async polling loop for the RFC 8628 device authorization flow (WP03).

The poller takes a :class:`DeviceFlowState` (built from a SaaS
``/oauth/device`` response) and a caller-supplied ``token_request`` coroutine
that POSTs to ``/oauth/token``. It drives the flow to a terminal state:

- success → returns the token response dict
- ``access_denied`` → raises :class:`DeviceFlowDenied`
- ``expired_token`` or local expiry → raises :class:`DeviceFlowExpired`
- transient :class:`NetworkError` → logged and retried on the next tick

FR-018: the poller caps its polling interval at 10 seconds even when SaaS
suggests a larger value (or sends a ``slow_down`` error). SaaS cannot push
the CLI below the user-experience floor for device flow feedback.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from collections.abc import Awaitable, Callable

from ..errors import DeviceFlowDenied, DeviceFlowExpired, NetworkError
from .state import DeviceFlowState

log = logging.getLogger(__name__)

# FR-018: even if SaaS sends a larger `interval`, the CLI never polls slower
# than every 10 seconds. A higher ceiling would degrade the headless login UX.
_MAX_INTERVAL_SECONDS = 10

# Per RFC 8628 §3.5, a ``slow_down`` error mandates a 5-second backoff bump.
_SLOW_DOWN_BACKOFF = 5


def format_user_code(user_code: str) -> str:
    """Format a device flow user code as chunks of 4 for human display.

    The SaaS device endpoint returns a short user code like ``ABCD1234``.
    Humans type this into a browser, so we hyphenate it in 4-character
    chunks. Any existing hyphens or spaces are stripped first so the helper
    is idempotent.

    Args:
        user_code: Raw user code from the SaaS response. May already
            contain hyphens (``"ABCD-1234"``) or spaces.

    Returns:
        The user code chunked by 4 and joined with ``-``. Codes of 4 or
        fewer characters are returned as-is (after normalization).

    Examples:
        >>> format_user_code("ABCD1234")
        'ABCD-1234'
        >>> format_user_code("ABCD-1234")
        'ABCD-1234'
        >>> format_user_code("ABCD12345678")
        'ABCD-1234-5678'
        >>> format_user_code("ABCD")
        'ABCD'
    """
    cleaned = user_code.replace("-", "").replace(" ", "")
    if len(cleaned) <= 4:
        return cleaned
    chunks = [cleaned[i : i + 4] for i in range(0, len(cleaned), 4)]
    return "-".join(chunks)


class DeviceFlowPoller:
    """Polls the OAuth token endpoint until the device flow reaches a terminal state.

    The poller is stateful only by way of the :class:`DeviceFlowState` it
    wraps; each poll attempt mutates the state's ``poll_count`` and
    ``last_polled_at`` fields. Progress display is delegated to the optional
    ``on_pending`` callback supplied to :meth:`poll`, so callers (e.g. WP05)
    can render to stderr or a Rich console without coupling the poller to
    any particular output format.
    """

    def __init__(self, state: DeviceFlowState) -> None:
        self._state = state

    @property
    def state(self) -> DeviceFlowState:
        """Return the wrapped :class:`DeviceFlowState`."""
        return self._state

    async def poll(
        self,
        token_request: Callable[[str], Awaitable[dict[str, Any]]],
        on_pending: Callable[[DeviceFlowState], None] | None = None,
    ) -> dict[str, Any]:
        """Poll the token endpoint until success, denial, or expiry.

        The loop waits for the (capped) polling interval BEFORE each poll so
        the user has time to open the browser and approve the request. After
        each attempt the SaaS response is classified:

        - no ``error`` key → success, return the response
        - ``authorization_pending`` → continue, call ``on_pending`` if supplied
        - ``slow_down`` → bump the interval by 5 seconds (still capped at 10)
        - ``access_denied`` → raise :class:`DeviceFlowDenied`
        - ``expired_token`` → raise :class:`DeviceFlowExpired`
        - any other error → raise :class:`DeviceFlowDenied` with description

        Local expiry is checked at the top of every iteration: if
        :meth:`DeviceFlowState.is_expired` returns True the loop raises
        :class:`DeviceFlowExpired` without making another token request.

        Args:
            token_request: Async callable that takes the device_code and
                POSTs to ``/oauth/token``. Must return the parsed SaaS JSON
                response dict (either success tokens or an ``error`` dict).
                Transport failures should raise
                :class:`~specify_cli.auth.errors.NetworkError`.
            on_pending: Optional callback invoked after each
                ``authorization_pending`` response. Receives the current
                :class:`DeviceFlowState` so the caller can render progress.

        Returns:
            The token response dict on success (contains ``access_token``,
            ``refresh_token``, etc.).

        Raises:
            DeviceFlowDenied: SaaS returned ``access_denied`` or an unknown
                error.
            DeviceFlowExpired: SaaS returned ``expired_token`` or the local
                state passed its expiry deadline.
        """
        interval = min(self._state.interval, _MAX_INTERVAL_SECONDS)

        while True:
            if self._state.is_expired():
                raise DeviceFlowExpired(
                    f"Device authorization expired after {self._state.expires_in} seconds. "
                    "Run `spec-kitty auth login --headless` again."
                )

            # Sleep BEFORE the first poll too -- gives the user time to open
            # the browser and approve. This is intentional UX, not a bug.
            await asyncio.sleep(interval)
            self._state.record_poll()

            try:
                response = await token_request(self._state.device_code)
            except NetworkError as exc:
                # Transient transport failure -- log and retry on the next
                # iteration. The local expiry check will eventually stop us.
                log.warning("Network error during device flow poll: %s", exc)
                continue

            error = response.get("error")
            if error is None:
                # Success: response contains access_token, refresh_token, etc.
                return response

            if error == "authorization_pending":
                if on_pending is not None:
                    on_pending(self._state)
                continue

            if error == "slow_down":
                # RFC 8628 §3.5: bump interval, but still cap at 10s (FR-018).
                interval = min(interval + _SLOW_DOWN_BACKOFF, _MAX_INTERVAL_SECONDS)
                continue

            if error == "access_denied":
                raise DeviceFlowDenied(
                    "User denied the authorization request. "
                    "Run `spec-kitty auth login --headless` to try again."
                )

            if error == "expired_token":
                raise DeviceFlowExpired(
                    "Device code expired before approval. "
                    "Run `spec-kitty auth login --headless` to try again."
                )

            # Unknown error -- propagate with whatever description SaaS gave us.
            desc = response.get("error_description", error)
            raise DeviceFlowDenied(f"Unexpected device flow error: {desc}")
