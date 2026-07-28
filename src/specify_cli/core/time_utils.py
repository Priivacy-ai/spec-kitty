"""Canonical clock helper for ISO-8601 UTC timestamps.

This module hosts the single canonical `now_utc_iso()` helper.

**The semantic clock contract**: every "now"-stamp in `specify_cli` that
serializes an *aware-UTC* instant at `isoformat()`'s native precision routes
through this helper. `now_utc_iso()` is the sole permitted producer of that
form; a local `datetime.now(UTC).isoformat()` copy is a contract violation.
This is enforced structurally rather than by inventory: an AST gate
(`tests/specify_cli/test_clock_consolidation.py`) scans the whole
`src/specify_cli` tree for the raw form and fails on any occurrence outside
the exception families below, so a newly added module is covered the moment
it lands. (A count of migrated copies is deliberately NOT recorded here — it
decays on every migration.)

Allowed exception families (each a genuinely *distinct contract*, not an
escape hatch):

- **This module itself** — the canonical implementation.
- The **stamp** family and the **datetime-returning** family, below.

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

    The canonical producer of the aware-UTC ``isoformat()`` form: a local
    ``datetime.now(UTC).isoformat()`` copy anywhere in ``specify_cli`` is a
    violation of the module's clock contract and is caught by the AST gate.
    Do not use this for the second-precision ``%Y-%m-%dT%H:%M:%SZ`` stamp
    format (see ``task_utils.support.now_utc``) or for callers that need a
    ``datetime`` object back.
    """
    return datetime.now(UTC).isoformat()
