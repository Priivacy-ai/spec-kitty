"""Z1: the bundled Zeitgeist client (spec-kitty side).

One typed client service (``transport.ZeitgeistClient``) speaking F3's
``ControlEnvelope``/``LiveFrame`` wire shapes over a local, self-hosted or
managed-profile Zeitgeist relay named by a project/user config value — never
a hosted/cloud URL. See ``m1-contract-drafts/Z1.md`` (the contract-freeze
draft this subpackage implements) for the full scope statement, negative
matrix, and agent-owned decisions.

This package introduces no team/identity/permission logic (Z2a), no prose
(Z8), and no managed-runtime deployment (Z3). It is the *client*, not the
relay.

Z4-C (``live_frame.py``, ``filtered_stream.py``) adds the client-side
filtered live-stream surfaces: ``filtered_stream.FilteredStream`` — one
SSE subscription per team-bound capability credential against F3's
``GET /managed/stream`` — with ``watch()``/``check()``/``current_focus()``.
It reuses ``budget``/``sanitizer`` from this package but never widens
``transport.ClientConfig`` or the control-envelope ``offer()`` path; the two
halves compose (a caller can hold both a ``transport.ZeitgeistClient`` and
one or more ``filtered_stream.FilteredStream`` instances) without either
depending on the other's internals.
"""

from __future__ import annotations
