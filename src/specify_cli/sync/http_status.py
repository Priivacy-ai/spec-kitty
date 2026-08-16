"""Canonical HTTP status classes shared across the sync subsystem.

Numeric status sets for *numeric* ``status_code in {...}`` checks. Kept here —
not in :mod:`specify_cli.sync.batch` — because ``batch.py`` classifies failures
by *string* keyword-matching over response text (its ``server_error`` bucket
also matches ``"500"``, ``"internal"`` and ``"server error"``), a deliberately
broader, differently-typed net than this numeric gateway class. The two are
intentionally separate; see #3441.
"""

from __future__ import annotations

#: Gateway-class HTTP statuses (502/503/504). A response carrying one of these
#: came from the edge — a load balancer or reverse proxy — rather than the
#: application, so it signals the endpoint is *unavailable* (a transient outage
#: such as a rolling deploy or maintenance window, or a genuinely decommissioned
#: host) rather than an application-level error. Note 500 is deliberately
#: excluded: it is an application-level error, not an edge signal.
#:
#: The offline queue treats these as *transient* (``failed_transient`` — the
#: queue row is left untouched, never dead-lettered; see
#: :mod:`specify_cli.sync.queue` and :mod:`specify_cli.sync.batch`, issue #889),
#: so any consumer that surfaces a gateway status to an operator must not imply
#: that queued events are lost.
GATEWAY_STATUSES: frozenset[int] = frozenset({502, 503, 504})
