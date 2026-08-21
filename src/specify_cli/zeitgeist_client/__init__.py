"""Z1: the bundled Zeitgeist client (spec-kitty side).

One typed client service (``transport.ZeitgeistClient``) speaking F3's
``ControlEnvelope``/``LiveFrame`` wire shapes over a local, self-hosted or
managed-profile Zeitgeist relay named by a project/user config value — never
a hosted/cloud URL. See ``m1-contract-drafts/Z1.md`` (the contract-freeze
draft this subpackage implements) for the full scope statement, negative
matrix, and agent-owned decisions.

This package introduces no team/identity/permission logic (Z2a), no
filtering/selectors (Z4-C), no prose (Z8), and no managed-runtime deployment
(Z3). It is the *client*, not the relay.
"""

from __future__ import annotations
