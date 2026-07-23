"""Hybrid SCAN stage for ``sync import-history`` (WP-Y2, #2262).

Produces a normalized, source-agnostic view of one mission's importable
history: the mission-creation facts, the work-package definitions, and the
lane transitions — with local-only lifecycle events dropped so they never
reach the SaaS strict-validation path.

The stage is *hybrid* (issue #2262 §3.4). Both shapes were adjudicated against
real event logs:

* **Prefixed missions** carry a ``MissionCreated``/``WPCreated`` prefix in
  ``status.events.jsonl`` — read it from disk.
* **Legacy missions** carry only lane transitions — synthesize the prefix from
  ``meta.json`` + ``tasks/WP*.md`` frontmatter.

This module reads only; it never writes, uploads, or mints envelopes. WP-Y3
turns a :class:`MissionScan` into the ordered, deterministic envelope stream
(INV-3 / INV-4).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from specify_cli.frontmatter import FrontmatterError
from specify_cli.status import read_events
from specify_cli.status.lifecycle_events import (
    FOLLOW_UP_RECORDED,
    MISSION_CREATED,
    MISSION_REOPENED,
    WP_CREATED,
    mission_event_log_path,
    read_lifecycle_events,
)
from specify_cli.status.models import StatusEvent
from specify_cli.status.wp_metadata import read_authored_wp_frontmatter

logger = logging.getLogger(__name__)

_META_FILENAME = "meta.json"
_TASKS_DIRNAME = "tasks"
_DEFAULT_MISSION_TYPE = "software-dev"
_KITTY_SPECS_ANCHOR = "kitty-specs"

# The lifecycle event types that are deliberately local-only and MUST be kept
# off the SaaS strict-validation path (status/lifecycle.py:165). We mirror that
# set from the public constants rather than trusting
# ``spec_kitty_events.LOCAL_ONLY_EVENT_TYPES``, which is empty in the installed
# package while both types ARE in its model map — so relying on it would let
# these hit strict validation and reject the whole batch.
_LOCAL_ONLY_EVENT_TYPES = frozenset({MISSION_REOPENED, FOLLOW_UP_RECORDED})


class PrefixSource(StrEnum):
    """Where a mission's (or WP's) creation prefix was resolved from."""

    ON_DISK = "on_disk"
    SYNTHESIZED = "synthesized"


@dataclass(frozen=True)
class ScannedWorkPackage:
    """A work package to be created in the projection, source-tagged."""

    wp_id: str
    wp_title: str
    depends_on: tuple[str, ...]
    wp_path: str | None
    created_at: str | None
    source: PrefixSource


@dataclass(frozen=True)
class MissionScan:
    """Normalized importable history for one mission.

    ``work_packages`` is guaranteed to cover every ``wp_id`` referenced by
    ``lane_transitions`` (a minimal synthesized WP is added for any gap), so a
    downstream ``WPStatusChanged`` can never precede its ``WPCreated`` (INV-3).
    """

    mission_slug: str
    canonical_mission_id: str | None
    mission_number: int | None
    name: str
    mission_type: str
    purpose_tldr: str | None
    purpose_context: str | None
    target_branch: str | None
    created_at: str | None
    prefix_source: PrefixSource
    work_packages: tuple[ScannedWorkPackage, ...]
    lane_transitions: tuple[StatusEvent, ...]


# ── public API ───────────────────────────────────────────────────────────────


def scan_mission(mission_dir: Path) -> MissionScan:
    """Scan one mission directory into a normalized :class:`MissionScan`."""
    meta = _load_meta(mission_dir)
    lifecycle = _read_importable_lifecycle(mission_dir)

    mc_payload = _first_payload(lifecycle, MISSION_CREATED)
    wp_payloads = _payloads(lifecycle, WP_CREATED)

    prefix_source = PrefixSource.ON_DISK if mc_payload is not None else PrefixSource.SYNTHESIZED
    fields = _resolve_mission_fields(mission_dir, meta, mc_payload)

    work_packages = _wps_from_prefix(wp_payloads) if wp_payloads else _wps_from_task_files(mission_dir)

    lane_transitions = tuple(read_events(mission_dir))
    work_packages = _ensure_wp_coverage(work_packages, lane_transitions)

    return MissionScan(
        prefix_source=prefix_source,
        work_packages=work_packages,
        lane_transitions=lane_transitions,
        **fields,
    )


def scan_missions(mission_dirs: Sequence[Path]) -> list[MissionScan]:
    """Scan several mission directories, preserving input order."""
    return [scan_mission(mission_dir) for mission_dir in mission_dirs]


# ── mission-level resolution ──────────────────────────────────────────────────


def _resolve_mission_fields(
    mission_dir: Path,
    meta: Mapping[str, Any],
    mc_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Resolve the ``MissionCreated`` fields, preferring the on-disk payload.

    Falls back to ``meta.json`` per the issue #2262 §3.4 field map; a legacy
    ``source_description`` back-fills ``purpose_tldr`` when no richer purpose
    text is present.
    """
    mission_slug = _coalesce(mc_payload, meta, "mission_slug") or mission_dir.name
    name = _coalesce(mc_payload, meta, "friendly_name") or mission_slug
    mission_type = _coalesce(mc_payload, meta, "mission_type") or _DEFAULT_MISSION_TYPE
    purpose_tldr = _coalesce(mc_payload, meta, "purpose_tldr") or meta.get("source_description")
    return {
        "mission_slug": mission_slug,
        "canonical_mission_id": _coalesce(mc_payload, meta, "mission_id"),
        "mission_number": _coalesce(mc_payload, meta, "mission_number"),
        "name": name,
        "mission_type": mission_type,
        "purpose_tldr": purpose_tldr,
        "purpose_context": _coalesce(mc_payload, meta, "purpose_context"),
        "target_branch": _coalesce(mc_payload, meta, "target_branch"),
        "created_at": _coalesce(mc_payload, meta, "created_at"),
    }


def _coalesce(payload: Mapping[str, Any] | None, meta: Mapping[str, Any], key: str) -> Any:
    """Return ``payload[key]`` if present and non-null, else ``meta[key]``."""
    if payload is not None:
        value = payload.get(key)
        if value is not None:
            return value
    return meta.get(key)


# ── work-package resolution ───────────────────────────────────────────────────


def _wps_from_prefix(wp_payloads: Sequence[Mapping[str, Any]]) -> tuple[ScannedWorkPackage, ...]:
    """Build WPs from on-disk ``WPCreated`` payloads."""
    wps: list[ScannedWorkPackage] = []
    for payload in wp_payloads:
        wp_id = payload.get("wp_id")
        if not wp_id:
            continue
        wps.append(
            ScannedWorkPackage(
                wp_id=str(wp_id),
                wp_title=str(payload.get("wp_title") or wp_id),
                depends_on=tuple(payload.get("depends_on") or ()),
                wp_path=payload.get("wp_path"),
                created_at=payload.get("created_at"),
                source=PrefixSource.ON_DISK,
            )
        )
    return tuple(wps)


def _wps_from_task_files(mission_dir: Path) -> tuple[ScannedWorkPackage, ...]:
    """Synthesize WPs from ``tasks/WP*.md`` frontmatter (canonical, §3.4/§6).

    Files with unreadable or invalid frontmatter are skipped here; any WP a
    lane transition still references is back-filled minimally by
    :func:`_ensure_wp_coverage`, so INV-3 coverage holds regardless.
    """
    tasks_dir = mission_dir / _TASKS_DIRNAME
    if not tasks_dir.is_dir():
        return ()
    wps: list[ScannedWorkPackage] = []
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        try:
            metadata, _ = read_authored_wp_frontmatter(wp_file)
        except (FrontmatterError, ValidationError, ValueError, TypeError, KeyError) as exc:
            # A malformed WP doc (bad YAML, non-dict frontmatter, invalid schema)
            # must never abort the whole scan. The catch is broadened past the
            # frontmatter/validation errors to the structural ones a malformed
            # doc can raise before validation (e.g. a YAML-list frontmatter →
            # TypeError) — the #2883 items 3/4 concern, applied to this reader.
            # Skip here; _ensure_wp_coverage back-fills any WP a lane transition
            # still references, so INV-3 coverage holds.
            logger.warning("import-history: skipping unreadable WP file %s: %s", wp_file, exc)
            continue
        wps.append(
            ScannedWorkPackage(
                wp_id=metadata.work_package_id,
                wp_title=metadata.display_title,
                depends_on=tuple(metadata.dependencies),
                wp_path=_repo_relative_path(wp_file),
                created_at=None,
                source=PrefixSource.SYNTHESIZED,
            )
        )
    return tuple(wps)


def _ensure_wp_coverage(
    work_packages: Sequence[ScannedWorkPackage],
    lane_transitions: Sequence[StatusEvent],
) -> tuple[ScannedWorkPackage, ...]:
    """Guarantee a WP exists for every ``wp_id`` in the lane transitions.

    A legacy task file may have been deleted after the mission ran, leaving a
    lane transition whose WP has no create source. Synthesize a minimal WP for
    each such gap so ``WPStatusChanged`` never precedes ``WPCreated`` (the
    ``wp_status_event_without_create`` anomaly). Result is sorted by ``wp_id``
    for a deterministic create order.
    """
    known = {wp.wp_id for wp in work_packages}
    backfilled: list[ScannedWorkPackage] = []
    for event in lane_transitions:
        wp_id = event.wp_id
        if wp_id and wp_id not in known:
            known.add(wp_id)
            backfilled.append(
                ScannedWorkPackage(
                    wp_id=wp_id,
                    wp_title=wp_id,
                    depends_on=(),
                    wp_path=None,
                    created_at=None,
                    source=PrefixSource.SYNTHESIZED,
                )
            )
    return tuple(sorted([*work_packages, *backfilled], key=lambda wp: wp.wp_id))


def _repo_relative_path(path: Path) -> str | None:
    """Return the POSIX ``kitty-specs/...`` path, matching the on-disk shape."""
    parts = path.parts
    if _KITTY_SPECS_ANCHOR in parts:
        return "/".join(parts[parts.index(_KITTY_SPECS_ANCHOR) :])
    return None


# ── lifecycle-prefix reading ──────────────────────────────────────────────────


def _read_importable_lifecycle(mission_dir: Path) -> list[dict[str, Any]]:
    """Read on-disk lifecycle-prefix events, dropping local-only types.

    ``read_lifecycle_events`` returns only rows carrying a top-level
    ``event_type`` (skipping malformed lines); we then strip the local-only
    types so they never propagate toward the SaaS strict validator.
    """
    events = read_lifecycle_events(mission_event_log_path(mission_dir))
    return [event for event in events if event.get("event_type") not in _LOCAL_ONLY_EVENT_TYPES]


def _payloads(lifecycle: Sequence[Mapping[str, Any]], event_type: str) -> list[dict[str, Any]]:
    return [dict(event.get("payload") or {}) for event in lifecycle if event.get("event_type") == event_type]


def _first_payload(lifecycle: Sequence[Mapping[str, Any]], event_type: str) -> dict[str, Any] | None:
    payloads = _payloads(lifecycle, event_type)
    return payloads[0] if payloads else None


# ── meta.json ─────────────────────────────────────────────────────────────────


def _load_meta(mission_dir: Path) -> dict[str, Any]:
    """Read ``meta.json``; a missing or unreadable file yields ``{}``."""
    meta_path = mission_dir / _META_FILENAME
    try:
        raw = meta_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
