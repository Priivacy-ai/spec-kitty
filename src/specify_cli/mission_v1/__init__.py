"""``specify_cli.mission_v1`` -- the surviving mission-event observability module.

Only :mod:`specify_cli.mission_v1.events` lives here now. Its two functions,
:func:`emit_event` and :func:`read_events`, are the provisional JSONL mission
event log consumed by the runtime loop:

* ``runtime/next/next_invocation_lifecycle.py`` emits the ``MissionNextInvoked``
  observability event through :func:`emit_event`;
* ``runtime/next/decision.py`` reads the log through :func:`read_events`.

The mission-DSL v1 state machine that used to share this package
(``compat`` / ``runner`` / ``guards`` / ``schema``, backed by the
``transitions`` library) was retired in mission
``dead-port-disposition-01M1TZVN``; git history before that mission carries
the full implementation. The package name is kept (decision OD4 of that
mission) because relocating ``events`` would touch the runtime consumers
above, their seam test, and the runtime import ledger for no behavioural
gain.

Importing this package must stay side-effect free and must never pull the
retired stack (or its transitive ``six``) back in --
``tests/specify_cli/mission_v1/test_import_hygiene.py`` pins that invariant.
"""

from specify_cli.mission_v1.events import emit_event, read_events

__all__ = ["emit_event", "read_events"]
