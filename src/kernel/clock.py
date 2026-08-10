"""The single door to wall-clock time.

Every wall-clock read in this codebase routes through this module. It is
the **sanctioned** home for stdlib ``datetime``/``time.time()`` access; a
repo-wide gate (landing in a later work package of this mission) bans the
raw stdlib forms everywhere else, including through this module's own
re-exported types (re-exporting a type never creates a sanctioned ``.now()``
path).

**Distinct from the Lamport logical clock** in
``specify_cli.sync.clock`` -- that module tracks a causal ordering counter
for event synchronization, not the current civil time. The two concepts
must never be conflated: this module owns *wall-clock* time (what a
developer means by "the current timestamp"); ``sync.clock`` owns a
monotonically-increasing logical counter unrelated to the wall clock.

**Distinct from duration clocks** (``time.monotonic()`` / ``time.perf_counter()``)
used for elapsed-time measurement -- those are out of scope for this door
and remain unbanned (only the wall-clock ``time.time()`` call is banned by
the gate).

This module currently hosts (WP01a of mission ``kernel-clock-single-door``):

- :func:`now_utc_iso` -- the aware-UTC ISO-8601 producer, relocated
  verbatim from the former ``specify_cli.core.time_utils``.
- Minimal type re-exports (:data:`__all__`) so consumers can import
  ``datetime``/``date``/``timedelta``/``UTC`` from the door for annotations,
  arithmetic, and parsing rather than importing stdlib ``datetime``
  directly.

The remaining producer family (``now_utc_stamp``, ``now_epoch``, ...), the
parse/format helpers, and the injectable ``Clock`` protocol land in later
work packages of this mission -- see ``kitty-specs/kernel-clock-single-door``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

__all__ = [
    "UTC",
    "date",
    "datetime",
    "now_utc_iso",
    "timedelta",
]


def now_utc_iso() -> str:
    """Return the current UTC time as an ISO 8601 string.

    The canonical producer of the aware-UTC ``isoformat()`` form: a local
    ``datetime.now(UTC).isoformat()`` copy anywhere in the codebase is a
    violation of the single-door contract. Do not use this for the
    second-precision ``%Y-%m-%dT%H:%M:%SZ`` stamp format or for callers
    that need a ``datetime`` object back -- those are distinct producers
    landing in a later work package.
    """
    return datetime.now(UTC).isoformat()
