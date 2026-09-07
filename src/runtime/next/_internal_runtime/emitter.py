"""CLI-internal runtime emitter surface.

Internalized from spec-kitty-runtime 0.4.3 as part of
`shared-package-boundary-cutover-01KQ22DS` (mission). See
`runtime-standalone-package-retirement-01KQ20Z8` for the upstream public-API
inventory.

`NullEmitter`, the `RuntimeEventEmitter` Protocol and the runtime emitter seam
(`runtime_emitter_for_mission` + its factory registry) are defined in
``events.py``; this module re-exports them under the per-task-layout name.
"""

from __future__ import annotations

from runtime.next._internal_runtime.events import (
    NullEmitter,
    RuntimeEventEmitter,
    register_runtime_emitter_factory,
    reset_runtime_emitter_factory,
    runtime_emitter_for_mission,
)

__all__ = [
    "NullEmitter",
    "RuntimeEventEmitter",
    "runtime_emitter_for_mission",
    "register_runtime_emitter_factory",
    "reset_runtime_emitter_factory",
]
