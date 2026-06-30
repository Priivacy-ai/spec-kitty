"""Pending-origin consumer implementation for the tracker integration package.

This module holds ``consume_pending_origin_impl`` — the concrete
``PendingOriginConsumer`` that was originally inlined in
``core/mission_creation.py::_consume_pending_origin_if_present``.

Moving it here inverts the dependency direction (FR-006):
- BEFORE: ``core/mission_creation.py`` lazy-imported ``tracker.origin``,
  ``tracker.origin_models``, and ``tracker.ticket_context`` directly.
- AFTER: the INTEGRATION side (``tracker/``) owns this logic and
  registers itself with the CORE adapter registry at startup.

``consume_pending_origin_impl`` is registered with
``core.adapters.register_pending_origin_consumer`` by ``tracker/__init__.py``
at tracker package startup so that ``core.adapters.consume_pending_origin``
can dispatch here without any direct CORE→INTEGRATION import.

Registration site: ``src/specify_cli/tracker/__init__.py``.
Startup ordering: the ``mission_create`` CLI command body imports
``specify_cli.tracker`` (inside ``create_mission()``, before the core phase) so
registration runs before ``create_mission_core`` is called. That in-function
import is the sole registration trigger for the CLI path — do not remove it.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def consume_pending_origin_impl(
    repo_root: Path,
    feature_dir: Path,
    meta: dict[str, Any],
) -> tuple[bool, bool, str | None, dict[str, Any]]:
    """Concrete PendingOriginConsumer implementation.

    Kept in ``tracker/`` so all tracker imports remain on the INTEGRATION
    side (FR-006).  Registered with ``core/adapters.py`` at tracker startup.

    Returns a 4-tuple ``(attempted, succeeded, error_msg, updated_meta)``:

    * ``attempted``   (bool) — ``True`` if a pending origin was found.
    * ``succeeded``   (bool) — ``True`` if binding completed without error.
    * ``error_msg``   (str | None) — failure description or ``None``.
    * ``updated_meta`` (dict) — meta dict, possibly updated with binding data.

    Safe-degrade: when no pending origin is present, returns
    ``(False, False, None, meta)`` unchanged — the same no-op the
    pre-WP02 code returned.
    """
    from specify_cli.tracker.origin import OriginBindingError, bind_mission_origin
    from specify_cli.tracker.origin_models import OriginCandidate
    from specify_cli.tracker.ticket_context import clear_pending_origin, read_pending_origin

    pending = read_pending_origin(repo_root)
    if not pending:
        return False, False, None, meta

    provider = str(pending.get("provider") or "").strip().lower()
    issue_id = str(pending.get("issue_id") or "").strip()
    issue_key = str(pending.get("issue_key") or "").strip()

    if not provider or not issue_id or not issue_key:
        return (
            True,
            False,
            "Pending origin is missing required provider/issue identifiers.",
            meta,
        )

    candidate = OriginCandidate(
        external_issue_id=issue_id,
        external_issue_key=issue_key,
        title=str(pending.get("title") or "").strip(),
        status=str(pending.get("status") or "").strip(),
        url=str(pending.get("url") or "").strip(),
        match_type="pending_origin",
        body=str(pending.get("body") or "").strip() or None,
    )

    try:
        updated_meta, _ = bind_mission_origin(
            feature_dir=feature_dir,
            candidate=candidate,
            provider=provider,
            resource_type=None,
            resource_id=None,
        )
    except OriginBindingError as exc:
        logger.warning("Pending origin bind failed for %s: %s", feature_dir, exc)
        return True, False, str(exc), meta
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Pending origin bind failed unexpectedly for %s: %s",
            feature_dir,
            exc,
        )
        return True, False, str(exc), meta

    clear_pending_origin(repo_root)
    return True, True, None, updated_meta
