"""CLI-internal runtime emitter surface.

Internalized from spec-kitty-runtime 0.4.3 as part of
`shared-package-boundary-cutover-01KQ22DS` (mission). See
`runtime-standalone-package-retirement-01KQ20Z8` for the upstream public-API
inventory.

`NullEmitter` and the `RuntimeEventEmitter` Protocol are defined in
``events.py``; this module re-exports them under the per-task-layout name.
"""

from __future__ import annotations

from specify_cli.next._internal_runtime.events import (
    NullEmitter,
    RuntimeEventEmitter,
)

__all__ = ["NullEmitter", "RuntimeEventEmitter"]
