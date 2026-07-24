"""The deliberate shared surface between migration replay and history import.

``migration.mission_state`` owns the TeamSpace envelope machinery — the
canonical schema version, deterministic id minting, the envelope body
checksum, the ``WPStatusChanged`` envelope builder, and the mission
selection / fail-closed audit seams. Its ``__all__`` deliberately demoted
those names as migration-internal ("no cross-module src/ from-import
callers", WP01 harden-dead-symbol-gate-01KW0RJR).

Two src/ consumers now share that machinery:

* :mod:`specify_cli.migration` itself — the ``doctor mission-state``
  teamspace dry-run (the original owner; it calls the underscore internals
  in-module and is unaffected by this seam).
* :mod:`specify_cli.sync.history_import` — the ``sync import-history``
  pipeline (#2262), which replays the exact same envelope shapes for
  historical import and reuses the same selection/audit gates.

This module is the ONE sanctioned exception to the demotion: it hoists
exactly the shared subset under public names, so the cross-module surface is
explicit, declared in ``__all__``, and ratcheted by the dead-symbol gate —
instead of scattered underscore imports reaching into mission_state
(the #2884 review's A1). Tests that need to stub the selection/audit seams
patch them HERE (the import-history pipeline binds them lazily from this
module at call time).
"""

from __future__ import annotations

from specify_cli.migration.mission_state import (
    CANONICAL_ENVELOPE_SCHEMA_VERSION,
    _select_mission_dirs as select_mission_dirs,
    _status_event_to_teamspace_envelope as status_event_to_teamspace_envelope,
    _teamspace_audit_blockers as teamspace_audit_blockers,
    deterministic_ulid,
    envelope_sha256,
)

__all__ = [
    "CANONICAL_ENVELOPE_SCHEMA_VERSION",
    "deterministic_ulid",
    "envelope_sha256",
    "select_mission_dirs",
    "status_event_to_teamspace_envelope",
    "teamspace_audit_blockers",
]
