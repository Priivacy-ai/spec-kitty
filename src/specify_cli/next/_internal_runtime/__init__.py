"""CLI-internal runtime surface (replaces ``spec_kitty_runtime`` in production).

The leading underscore marks this package as CLI-internal. External Python
importers MUST reach the runtime surface only through
``specify_cli.next.runtime_bridge`` and the ``spec-kitty next`` command — never
by importing this module directly.

Internalized from spec-kitty-runtime 0.4.3 as part of
`shared-package-boundary-cutover-01KQ22DS` (mission). See
`runtime-standalone-package-retirement-01KQ20Z8` for the upstream public-API
inventory and `kitty-specs/shared-package-boundary-cutover-01KQ22DS/contracts/
internal_runtime_surface.md` for the frozen public contract.

Forbidden patterns enforced here:
- No ``spec_kitty_runtime`` imports at any layer.
- No ``rich.*`` or ``typer.*`` imports — presentation lives in the CLI layer.
"""

from __future__ import annotations

from specify_cli.next._internal_runtime.discovery import DiscoveryContext
from specify_cli.next._internal_runtime.engine import (
    MissionRunRef,
    next_step,
    provide_decision_answer,
    start_mission_run,
)
from specify_cli.next._internal_runtime.events import NullEmitter
from specify_cli.next._internal_runtime.schema import (
    MissionPolicySnapshot,
    NextDecision,
)

__all__ = [
    "DiscoveryContext",
    "MissionPolicySnapshot",
    "MissionRunRef",
    "NextDecision",
    "NullEmitter",
    "next_step",
    "provide_decision_answer",
    "start_mission_run",
]
