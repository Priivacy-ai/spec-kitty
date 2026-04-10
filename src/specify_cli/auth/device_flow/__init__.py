"""RFC 8628 Device Authorization Grant flow (feature 080, WP03).

This package contains the state dataclass and polling loop used by the
headless login flow (WP05). The public surface is:

- :class:`DeviceFlowState`: in-flight flow state (device_code, interval, ...)
- :class:`DeviceFlowPoller`: async polling loop that drives the flow to a
  terminal state (success / denied / expired).
- :func:`format_user_code`: helper that formats an 8-char user code as
  ``ABCD-1234`` for human display.

Downstream modules should import error types from
``specify_cli.auth.errors`` -- never from this package.
"""

from __future__ import annotations

from .poller import DeviceFlowPoller, format_user_code
from .state import DeviceFlowState

__all__ = ["DeviceFlowState", "DeviceFlowPoller", "format_user_code"]
