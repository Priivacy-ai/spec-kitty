"""In-process diagnostic dedup + atexit success flag.

Why this module exists
----------------------
The CLI prints noisy diagnostics from multiple cooperating subsystems
(sync, auth, atexit shutdown handlers). Without coordination they:

- Repeat the same warning N times within one CLI invocation (#717).
- Print red shutdown errors AFTER a successful JSON payload (#735).

This module is the smallest-blast-radius coordination point. It provides:

- ``report_once(cause_key)`` — a process-wide, lock-backed gate that allows
  each distinct diagnostic cause to print at most once per CLI invocation,
  including diagnostics emitted from timer/final-sync threads.
- ``mark_invocation_succeeded()`` / ``invocation_succeeded()`` — a
  process-state flag that JSON-emitting commands set after their final
  payload write so atexit handlers can downgrade or skip their warnings.

Future authors of new JSON-emitting commands should call
``mark_invocation_succeeded()`` immediately after their final payload
write so atexit handlers know the invocation succeeded.
"""

from __future__ import annotations

import threading
from typing import Final

_REPORTED_LOCK: Final[threading.Lock] = threading.Lock()
_REPORTED: set[str] = set()

_SUCCESS_FLAG_LOCK: Final[threading.Lock] = threading.Lock()
_SUCCESS_FLAG: list[bool] = [False]


def report_once(cause_key: str) -> bool:
    """Return True iff ``cause_key`` has not been reported in this invocation.

    Safe across asyncio tasks and background threads. Caller pattern::

        if report_once("sync.unauthenticated"):
            logger.warning("Not authenticated, skipping sync")
    """
    with _REPORTED_LOCK:
        if cause_key in _REPORTED:
            return False
        _REPORTED.add(cause_key)
        return True


def reset_for_invocation() -> None:
    """Reset both dedup state and success flag.

    Production code should NOT call this. Tests call it from a fixture so
    state does not leak between test runs.
    """
    with _REPORTED_LOCK:
        _REPORTED.clear()
    with _SUCCESS_FLAG_LOCK:
        _SUCCESS_FLAG[0] = False


def mark_invocation_succeeded() -> None:
    """Called by JSON-payload-emitting commands AFTER their final write.

    Atexit handlers consult ``invocation_succeeded()`` to decide whether
    to log shutdown warnings (when False) or skip them (when True).
    """
    with _SUCCESS_FLAG_LOCK:
        _SUCCESS_FLAG[0] = True


def invocation_succeeded() -> bool:
    """Read by atexit handlers to gate their warning output."""
    with _SUCCESS_FLAG_LOCK:
        return _SUCCESS_FLAG[0]
