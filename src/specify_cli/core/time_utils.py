"""Canonical clock helper for ISO-8601 UTC timestamps.

This module hosts the single canonical `now_utc_iso()` helper that replaces
12 byte-identical `datetime.now(UTC).isoformat()` copies scattered across
`event_journal/`, `status/`, `retrospective/`, `delivery/`, and `dossier/`.

Two distinct-contract families are deliberately NOT folded into this helper
(see mission-resolver-port-01KX1C05 research.md D-04, NFR-004):

- The **stamp** family (`task_utils/support.py:now_utc()`,
  `cli/commands/agent/mission_parsing.py`) serializes to
  `%Y-%m-%dT%H:%M:%SZ` (second precision, literal ``Z`` suffix) — a
  different on-disk format. Folding it here would change serialized
  timestamps.
- The **datetime-returning** family (`decisions/emit.py`,
  `decisions/service.py`) returns a `datetime` object, not a string.

Naming note: `task_utils/support.py` already defines `now_utc()` returning
the *stamp* string above. This helper is deliberately named `now_utc_iso()`
(distinct name) to avoid a confusing same-name sibling with a different
contract.
"""

from __future__ import annotations

from datetime import UTC, datetime


def now_utc_iso() -> str:
    """Return the current UTC time as an ISO 8601 string.

    Canonical replacement for the 12 byte-identical
    ``datetime.now(UTC).isoformat()`` copies. Do not use this for the
    second-precision ``%Y-%m-%dT%H:%M:%SZ`` stamp format (see
    ``task_utils.support.now_utc``) or for callers that need a ``datetime``
    object back.
    """
    return datetime.now(UTC).isoformat()
