"""JSONL event store for status events.

Provides append-only persistence of StatusEvent records to a JSONL file
(status.events.jsonl). Each line is a JSON object with deterministic
(sorted) key ordering.

Back-compat reader (T024, FR-023):
    Events written before WP05 carry only ``mission_slug`` for mission
    identity. Events written after WP05 carry both ``mission_slug`` AND
    ``mission_id`` (a ULID from meta.json).

    The :func:`read_events` reader tolerates both shapes and resolves the
    ``mission_id`` for legacy events by reading the corresponding
    ``meta.json`` file. The slug→mission_id mapping is cached per call
    inside ``_SlugResolver`` to avoid repeated disk reads.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from .models import StatusEvent

logger = logging.getLogger(__name__)

EVENTS_FILENAME = "status.events.jsonl"

# Regex patterns for identity classification (T024)
_ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
_MISSION_SLUG_PATTERN = re.compile(r"^\d{3}-[a-z0-9-]+$")
_WP_ID_PATTERN = re.compile(r"^WP\d+$")


class StoreError(Exception):
    """Raised when the event store encounters corruption or I/O errors."""


def _events_path(feature_dir: Path) -> Path:
    """Return the canonical path to the events JSONL file."""
    return feature_dir / EVENTS_FILENAME


class _SlugResolver:
    """Cache-backed slug → mission_id resolver.

    Reads ``meta.json`` from the kitty-specs directory alongside the
    event log to resolve a legacy ``mission_slug`` to its canonical
    ``mission_id`` (ULID).  Results are cached in memory to avoid
    repeated disk reads within a single :func:`read_events` call.

    Orphaned slugs (whose meta.json does not exist or does not contain
    a ``mission_id``) are logged as a warning and return ``None``.
    """

    def __init__(self, feature_dir: Path) -> None:
        # feature_dir is the directory that owns status.events.jsonl.
        # The slug→dir mapping uses sibling kitty-specs directories.
        self._feature_dir = feature_dir
        self._kitty_specs_root: Path | None = self._find_kitty_specs_root()
        self._cache: dict[str, str | None] = {}

    def _find_kitty_specs_root(self) -> Path | None:
        """Walk up from feature_dir to find the kitty-specs root."""
        candidate = self._feature_dir.parent
        # feature_dir is typically kitty-specs/<slug>/ — so parent is kitty-specs/
        if candidate.name == "kitty-specs":
            return candidate
        # In case we're already inside a deeper structure, try two levels up
        two_up = candidate.parent
        if two_up.name == "kitty-specs":
            return two_up
        # Otherwise, fall back to the parent (best effort)
        return candidate

    def resolve(self, mission_slug: str) -> str | None:
        """Return the mission_id for *mission_slug*, or None if unresolvable.

        Reads ``<kitty_specs_root>/<mission_slug>/meta.json`` and extracts
        the ``mission_id`` field.  Returns None if the file is missing,
        the field is absent, or JSON is malformed (logs a warning).
        """
        if mission_slug in self._cache:
            return self._cache[mission_slug]

        mission_id: str | None = None
        if self._kitty_specs_root is not None:
            meta_path = self._kitty_specs_root / mission_slug / "meta.json"
            if meta_path.exists():
                try:
                    data = json.loads(meta_path.read_text(encoding="utf-8"))
                    mission_id = data.get("mission_id") or None
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning(
                        "Could not read meta.json for slug %r: %s",
                        mission_slug,
                        exc,
                    )
            else:
                logger.warning(
                    "No meta.json found for mission_slug %r (orphaned event); mission_id will be None for these events",
                    mission_slug,
                )

        self._cache[mission_slug] = mission_id
        return mission_id


def _resolve_mission_id_from_dict(
    raw: dict[str, Any],
    resolver: _SlugResolver,
) -> str | None:
    """Resolve the canonical mission_id from a raw event dict.

    Strategy (T024):
    1. If the event already carries ``mission_id`` (new-format), use it.
    2. If ``aggregate_id`` looks like a ULID, treat it as ``mission_id``.
    3. If ``mission_slug`` / ``feature_slug`` is present, resolve via meta.json.
    4. Return None for unresolvable events (caller logs/skips as appropriate).
    """
    # New-format event: mission_id field present directly
    if raw.get("mission_id"):
        return str(raw["mission_id"])

    # Legacy path: try to resolve from mission_slug
    slug = raw.get("mission_slug") or raw.get("feature_slug") or ""
    if slug:
        return resolver.resolve(slug)

    return None


def append_event(feature_dir: Path, event: StatusEvent) -> None:
    """Atomically append a StatusEvent as a single JSON line.

    Creates parent directories and the file if they do not exist.
    Uses ``sort_keys=True`` for deterministic key ordering.
    """
    path = _events_path(feature_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event.to_dict(), sort_keys=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_events_raw(feature_dir: Path) -> list[dict[str, Any]]:
    """Read raw JSON dicts from the events file.

    Returns an empty list when the file does not exist.
    Blank lines are silently skipped.
    Raises :class:`StoreError` on invalid JSON, including the 1-based
    line number in the message.
    """
    path = _events_path(feature_dir)
    if not path.exists():
        return []

    results: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, raw_line in enumerate(fh, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise StoreError(f"Invalid JSON on line {line_number}: {exc}") from exc
            results.append(obj)
    return results


def _should_skip_status_event(obj: dict[str, Any]) -> bool:
    """Return True for non-lane events that intentionally share the JSONL file."""
    event_name = obj.get("event_name")
    if isinstance(event_name, str) and event_name.startswith("retrospective."):
        return True

    # Why: Skip mission-level events (DecisionPointOpened,
    # DecisionPointResolved, DecisionPointDeferred,
    # DecisionPointCanceled, DecisionPointWidened, and any future
    # event-type written by a non-status-emitter subsystem) that
    # share status.events.jsonl with lane-transition events.
    # Two cooperating subsystems write to this file with incompatible
    # schemas: the status emitter writes lane-transition events
    # (carrying wp_id, from_lane, to_lane), while the Decision Moment
    # Protocol writes mission-level events that carry a top-level
    # `event_type` field instead. Discriminating on event_type
    # PRESENCE (not a specific value allowlist) is future-proof AND
    # preserves the existing fail-loud contract for malformed
    # lane-transition events: a corrupted lane event missing wp_id
    # but ALSO missing event_type still hits StatusEvent.from_dict
    # below and raises as today. See FR-010.
    return "event_type" in obj


def read_events(feature_dir: Path) -> list[StatusEvent]:
    """Read and deserialize StatusEvent objects from the events file.

    Handles both legacy events (``mission_slug`` only) and new events
    (``mission_slug`` + ``mission_id``).  For legacy events, the
    ``mission_id`` is resolved from the corresponding ``meta.json`` via
    the slug resolver (cached per call).

    Returns an empty list when the file does not exist.
    Blank lines are silently skipped.
    Raises :class:`StoreError` on invalid JSON **or** invalid event
    structure, including the 1-based line number in the message.
    """
    path = _events_path(feature_dir)
    if not path.exists():
        return []

    resolver = _SlugResolver(feature_dir)
    results: list[StatusEvent] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, raw_line in enumerate(fh, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise StoreError(f"Invalid JSON on line {line_number}: {exc}") from exc
            if _should_skip_status_event(obj):
                continue

            try:
                # Resolve mission_id from the raw dict before parsing,
                # so that from_dict() receives it even for legacy events.
                resolved_mission_id = _resolve_mission_id_from_dict(obj, resolver)
                if resolved_mission_id is not None and "mission_id" not in obj:
                    # Inject resolved value so from_dict() populates the field
                    obj = {**obj, "mission_id": resolved_mission_id}
                event = StatusEvent.from_dict(obj)
            except (KeyError, ValueError, TypeError) as exc:
                raise StoreError(f"Invalid event structure on line {line_number}: {exc}") from exc
            results.append(event)
    return results
