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

from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.frontmatter import FrontmatterError
from specify_cli.mission_metadata import load_meta_or_empty

# Access the status subsystem only through its package facade (the
# status-module-boundary gate forbids new deep submodule imports).
from specify_cli.status import (
    LOCAL_ONLY_LIFECYCLE_EVENT_TYPES,
    MISSION_CREATED,
    WP_CREATED,
    StatusEvent,
    StoreError,
    mission_event_log_path,
    read_authored_wp_frontmatter_lenient,
    read_events,
    read_lifecycle_events,
)

logger = logging.getLogger(__name__)

_TASKS_DIRNAME = "tasks"
_DEFAULT_MISSION_TYPE = "software-dev"

# The lifecycle event types kept OFF the SaaS strict-validation path — bound from
# the single public owner in the status package (#2884) rather than a
# hand-mirrored frozenset. (Deliberately NOT the installed
# ``spec_kitty_events.LOCAL_ONLY_EVENT_TYPES``, which is empty while both types
# ARE in its model map — trusting it would let these reach strict validation and
# reject the whole batch; the public owner documents that rationale.)
_LOCAL_ONLY_EVENT_TYPES = LOCAL_ONLY_LIFECYCLE_EVENT_TYPES


class MissionScanError(RuntimeError):
    """A mission's on-disk state could not be read (e.g. a corrupt status log).

    Fail-closed: raised so the CLI/pipeline can name the offending mission and
    abort without uploading, rather than surfacing a raw ``StoreError`` traceback.
    """

    def __init__(self, mission_slug: str, detail: str) -> None:
        self.mission_slug = mission_slug
        super().__init__(f"{mission_slug}: {detail}")


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
    # WP files skipped for malformed/unreadable frontmatter (file names).
    # Fail-loud, not fail-closed: the scan survives, but the skips MUST reach
    # the operator-facing report so a partial import never reads as clean.
    skipped_wp_files: tuple[str, ...] = ()
    # Malformed/unrecoverable rows dropped from the on-disk lifecycle prefix
    # (status.events.jsonl): raw lines `read_lifecycle_events` silently skips
    # (bad JSON, non-dict, or missing `event_type`) plus `WPCreated` payloads
    # with no `wp_id`. Counted (not just logged) so a truncated prefix line
    # surfaces here the same way a malformed WP file surfaces in
    # `skipped_wp_files` — never a silent drop (#2884 finding A).
    skipped_event_rows: int = 0


# ── public API ───────────────────────────────────────────────────────────────


def scan_mission(mission_dir: Path) -> MissionScan:
    """Scan one mission directory into a normalized :class:`MissionScan`."""
    meta = load_meta_or_empty(mission_dir)
    lifecycle = _read_importable_lifecycle(mission_dir)
    skipped_event_rows = _count_malformed_lifecycle_rows(mission_event_log_path(mission_dir))

    mc_payload = _first_payload(lifecycle, MISSION_CREATED)
    wp_payloads = _payloads(lifecycle, WP_CREATED)

    prefix_source = PrefixSource.ON_DISK if mc_payload is not None else PrefixSource.SYNTHESIZED
    fields = _resolve_mission_fields(mission_dir, meta, mc_payload)

    skipped_wp_files: tuple[str, ...] = ()
    if wp_payloads:
        work_packages, wp_created_skipped = _wps_from_prefix(wp_payloads)
        skipped_event_rows += wp_created_skipped
    else:
        work_packages, skipped_wp_files = _wps_from_task_files(mission_dir)

    try:
        lane_transitions = tuple(read_events(mission_dir))
    except StoreError as exc:
        # A corrupt status.events.jsonl must fail closed with the mission named,
        # not surface as a raw traceback (matches the graceful WP-frontmatter skip).
        raise MissionScanError(fields["mission_slug"], f"corrupt status log: {exc}") from exc
    work_packages = _ensure_wp_coverage(work_packages, lane_transitions)

    return MissionScan(
        prefix_source=prefix_source,
        work_packages=work_packages,
        lane_transitions=lane_transitions,
        skipped_wp_files=skipped_wp_files,
        skipped_event_rows=skipped_event_rows,
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


def _wps_from_prefix(
    wp_payloads: Sequence[Mapping[str, Any]],
) -> tuple[tuple[ScannedWorkPackage, ...], int]:
    """Build WPs from on-disk ``WPCreated`` payloads.

    Returns ``(work_packages, skipped_count)``. A payload with no ``wp_id`` is
    unusable (there is no aggregate to create), but dropping it silently would
    let one truncated ``WPCreated`` line vanish the WP from the import while
    the plan still reports clean — the skip is counted here so it reaches
    ``MissionScan.skipped_event_rows`` (#2884 finding A).
    """
    wps: list[ScannedWorkPackage] = []
    skipped = 0
    for payload in wp_payloads:
        wp_id = payload.get("wp_id")
        if not wp_id:
            logger.warning(
                "import-history: skipping WPCreated payload with no wp_id: %r",
                payload,
            )
            skipped += 1
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
    return tuple(wps), skipped


def _wps_from_task_files(mission_dir: Path) -> tuple[tuple[ScannedWorkPackage, ...], tuple[str, ...]]:
    """Synthesize WPs from ``tasks/WP*.md`` frontmatter (canonical, §3.4/§6).

    Returns ``(work_packages, skipped_wp_files)``. Files with unreadable or
    invalid frontmatter are skipped — but never silently: the skipped file
    names are returned so the scan result carries them into the operator-facing
    report (fail-loud, the #2884 review's chosen design over fail-closed). Any
    WP a lane transition still references is back-filled minimally by
    :func:`_ensure_wp_coverage`, so INV-3 coverage holds regardless.
    """
    tasks_dir = mission_dir / _TASKS_DIRNAME
    if not tasks_dir.is_dir():
        return (), ()
    wps: list[ScannedWorkPackage] = []
    skipped: list[str] = []
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        try:
            # Historical import tolerates retired frontmatter fields (FR-011,
            # #3406): a legacy WP carrying e.g. `estimated_lines` must import as
            # a real WP, not degrade to a bare back-fill. The lenient reader
            # drops unknown keys but still raises on genuinely-malformed docs, so
            # the fail-loud skip below is unchanged for real corruption.
            metadata, _ = read_authored_wp_frontmatter_lenient(wp_file)
        except (FrontmatterError, ValidationError, ValueError, TypeError, KeyError, OSError) as exc:
            # A malformed WP doc (bad YAML, non-dict frontmatter, invalid schema)
            # must never abort the whole scan. The catch is broadened past the
            # frontmatter/validation errors to the structural ones a malformed
            # doc can raise before validation (e.g. a YAML-list frontmatter →
            # TypeError) — the #2883 items 3/4 concern, applied to this reader.
            # Skip here (recorded, surfaced in the report); _ensure_wp_coverage
            # back-fills any WP a lane transition still references, so INV-3
            # coverage holds.
            logger.warning("import-history: skipping unreadable WP file %s: %s", wp_file, exc)
            skipped.append(wp_file.name)
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
    return tuple(wps), tuple(skipped)


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
    if KITTY_SPECS_DIR in parts:
        return "/".join(parts[parts.index(KITTY_SPECS_DIR) :])
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


def _count_malformed_lifecycle_rows(log_path: Path) -> int:
    """Count raw JSONL rows ``read_lifecycle_events`` silently drops.

    ``read_lifecycle_events`` (the status package's public accessor) tolerates
    missing files, blank lines, and corrupted lines — it only returns rows
    that parse as a JSON object carrying a top-level *string* ``event_type``,
    logging a debug line for anything else and moving on. That is the right
    behavior for its other callers, but for import-history a dropped
    ``WPCreated``/``MissionCreated`` row must not vanish quietly. The sharpest
    case (#2884 finding A) is genuinely silent: a row with ``event_type: null``
    is valid JSON, so ``read_events`` (the lane-transition reader sharing this
    same file) treats it as a skippable non-lane row and does NOT fail the
    whole scan closed — but ``read_lifecycle_events`` also drops it (its
    ``event_type`` isn't a ``str``), so the row vanishes from BOTH readers
    with no signal at all.

    This reads the same file independently (mirroring, not importing, the
    private skip conditions in ``status.lifecycle_events._read_lifecycle_lines``)
    so the count can be surfaced at the scan layer without modifying the
    status package. A row with NO ``event_type`` key at all is the common
    lane-transition (``StatusEvent``) shape sharing this file — not malformed,
    just a sibling format read by ``read_events`` instead; only a row that
    carries ``event_type`` but as a non-string value (or fails to parse as a
    JSON object at all) counts as malformed here.
    """
    if not log_path.exists():
        return 0
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return 0
    malformed = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(obj, dict):
            malformed += 1
            continue
        if "event_type" not in obj:
            continue  # a lane-transition (StatusEvent) row — not malformed, a sibling format
        if not isinstance(obj["event_type"], str):
            malformed += 1
    return malformed


def _payloads(lifecycle: Sequence[Mapping[str, Any]], event_type: str) -> list[dict[str, Any]]:
    return [dict(event.get("payload") or {}) for event in lifecycle if event.get("event_type") == event_type]


def _first_payload(lifecycle: Sequence[Mapping[str, Any]], event_type: str) -> dict[str, Any] | None:
    payloads = _payloads(lifecycle, event_type)
    return payloads[0] if payloads else None
