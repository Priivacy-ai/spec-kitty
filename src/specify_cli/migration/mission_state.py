"""Deterministic mission-state repair and TeamSpace dry-run helpers.

This module is the mutating counterpart to ``specify_cli.audit``.  The audit
package remains read-only; this module is only reached from
``doctor mission-state --fix`` or ``--teamspace-dry-run``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from packaging.version import Version

from specify_cli.core.atomic import atomic_write
from specify_cli.mission_metadata import (
    load_meta,
    mission_number_from_slug,
    validate_meta,
    write_meta,
)
from specify_cli.status.models import ULID_PATTERN, Lane, StatusEvent
from specify_cli.status.reducer import materialize_snapshot, materialize_to_json

MIGRATION_SCHEMA_VERSION = "1.0.0"
CANONICAL_ENVELOPE_SCHEMA_VERSION = "3.0.0"
REQUIRED_EVENTS_PACKAGE = Version("5.0.0")

EVENTS_FILENAME = "status.events.jsonl"
STATUS_FILENAME = "status.json"
META_FILENAME = "meta.json"
MANIFEST_ROOT = Path(".kittify/migrations/mission-state")

FORBIDDEN_LEGACY_KEYS = frozenset(
    {
        "feature_slug",
        "feature_number",
        "mission_key",
        "legacy_aggregate_id",
    }
)
STATUS_ROW_ALIASES = {
    "feature_slug": "mission_slug",
    "work_package_id": "wp_id",
}
META_LEGACY_ALIASES = frozenset({"feature_slug", "feature_number", "mission_key", "legacy_aggregate_id", "mission"})
LANE_ALIASES = {"doing": "in_progress"}
VALID_LANES = frozenset(lane.value for lane in Lane)
VALID_EXECUTION_MODES = frozenset({"worktree", "direct_repo"})

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ACTOR_SAFE = re.compile(r"[^a-z0-9_.:-]+")
_MISSION_PREFIX_RE = re.compile(r"^(\d{3})-")
_MID8_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{8}$")
_UUID_HYPHEN_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_UUID_BARE_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)
_REMOTE_URL_SCHEMES = frozenset({"http", "https"})


class MissionStateRepairError(RuntimeError):
    """Raised when mission-state repair cannot proceed safely."""


class MissionStateDryRunError(RuntimeError):
    """Raised when TeamSpace dry-run validation cannot proceed."""


@dataclass(frozen=True)
class FileChange:
    """Digest evidence for a file touched by the repair."""

    path: str
    old_sha256: str | None
    new_sha256: str | None
    old_size: int | None
    new_size: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "old_sha256": self.old_sha256,
            "new_sha256": self.new_sha256,
            "old_size": self.old_size,
            "new_size": self.new_size,
        }


@dataclass(frozen=True)
class RowTransformation:
    """Audit evidence for one status.events.jsonl row transformation."""

    artifact_path: str
    line_number: int
    event_id: str | None
    actions: tuple[str, ...]
    old_sha256: str
    new_sha256: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_path": self.artifact_path,
            "line_number": self.line_number,
            "event_id": self.event_id,
            "actions": list(self.actions),
            "old_sha256": self.old_sha256,
            "new_sha256": self.new_sha256,
        }


@dataclass
class MissionRepairResult:
    """Repair result for a single mission directory."""

    mission_slug: str
    mission_id: str | None
    status: Literal["updated", "unchanged", "error"]
    file_changes: list[FileChange] = field(default_factory=list)
    row_transformations: list[RowTransformation] = field(default_factory=list)
    quarantined_rows: int = 0
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "mission_slug": self.mission_slug,
            "mission_id": self.mission_id,
            "status": self.status,
            "file_changes": [change.to_dict() for change in self.file_changes],
            "row_transformations": [row.to_dict() for row in self.row_transformations],
            "quarantined_rows": self.quarantined_rows,
            "validation_errors": list(self.validation_errors),
        }


@dataclass
class RepairReport:
    """Top-level repair manifest."""

    run_id: str
    repo_head: str | None
    target_missions: list[str]
    manifest_path: str
    missions: list[MissionRepairResult]
    schema_version: str = MIGRATION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "repo_head": self.repo_head,
            "target_missions": list(self.target_missions),
            "manifest_path": self.manifest_path,
            "summary": {
                "missions_total": len(self.missions),
                "missions_updated": sum(1 for m in self.missions if m.status == "updated"),
                "missions_unchanged": sum(1 for m in self.missions if m.status == "unchanged"),
                "missions_error": sum(1 for m in self.missions if m.status == "error"),
                "quarantined_rows": sum(m.quarantined_rows for m in self.missions),
            },
            "missions": [mission.to_dict() for mission in self.missions],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True)
class TeamspaceDryRunRowMapping:
    """Mapping from one local status row to its synthesized TeamSpace event."""

    mission_slug: str
    artifact_path: str
    line_number: int | None
    source_event_id: str
    synthesized_event_id: str
    synthesized_event_type: str
    aggregate_id: str
    row_sha256: str | None
    envelope_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "mission_slug": self.mission_slug,
            "artifact_path": self.artifact_path,
            "line_number": self.line_number,
            "source_event_id": self.source_event_id,
            "synthesized_event_id": self.synthesized_event_id,
            "synthesized_event_type": self.synthesized_event_type,
            "aggregate_id": self.aggregate_id,
            "row_sha256": self.row_sha256,
            "envelope_sha256": self.envelope_sha256,
        }


@dataclass(frozen=True)
class TeamspaceDryRunReport:
    """Validation report for canonical envelopes synthesized from local state."""

    schema_version: str
    events_package_version: str
    envelope_count: int
    valid: bool
    errors: tuple[dict[str, object], ...]
    row_mappings: tuple[TeamspaceDryRunRowMapping, ...] = ()
    context_warnings: tuple[dict[str, object], ...] = ()
    side_logs: tuple[dict[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "events_package_version": self.events_package_version,
            "envelope_count": self.envelope_count,
            "valid": self.valid,
            "errors": list(self.errors),
            "row_mappings": [mapping.to_dict() for mapping in self.row_mappings],
            "context_warnings": list(self.context_warnings),
            "side_logs": list(self.side_logs),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True)
class _RawJsonlRow:
    line_number: int
    text: str
    data: dict[str, Any]


@dataclass(frozen=True)
class _CanonicalRowResult:
    row: dict[str, Any] | None
    actions: tuple[str, ...]
    error: str | None = None


def deterministic_ulid(seed: bytes | str) -> str:
    """Return a deterministic 26-char Crockford identifier from *seed*."""
    raw = seed.encode("utf-8") if isinstance(seed, str) else seed
    value = int.from_bytes(hashlib.sha256(raw).digest()[:16], "big")
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def repair_repo(
    repo_root: Path,
    *,
    scan_root: Path | None = None,
    mission: str | None = None,
    manifest_path: Path | None = None,
    allow_dirty: bool = False,
) -> RepairReport:
    """Canonicalize historical mission state on disk and write a manifest."""
    resolved_repo_root = repo_root.resolve()
    mission_dirs = _select_mission_dirs(resolved_repo_root, scan_root=scan_root, mission=mission)
    if not mission_dirs:
        raise MissionStateRepairError("No mission directories found to repair.")

    run_id = _compute_run_id(resolved_repo_root, mission_dirs)
    manifest_rel = manifest_path or MANIFEST_ROOT / f"{run_id}.json"
    manifest_abs = _resolve_repo_relative(resolved_repo_root, manifest_rel)
    relevant_paths = [_repo_relpath(resolved_repo_root, path) for path in mission_dirs]
    relevant_paths.append(str(MANIFEST_ROOT))

    _assert_git_safe(resolved_repo_root, relevant_paths, allow_dirty=allow_dirty)
    with _git_lock(resolved_repo_root):
        results: list[MissionRepairResult] = []
        for mission_dir in mission_dirs:
            results.append(_repair_mission(resolved_repo_root, mission_dir, run_id=run_id))

        report = RepairReport(
            run_id=run_id,
            repo_head=_git_head(resolved_repo_root),
            target_missions=[p.name for p in mission_dirs],
            manifest_path=_repo_relpath(resolved_repo_root, manifest_abs),
            missions=results,
        )
        atomic_write(manifest_abs, report.to_json(), mkdir=True)
        return report


def teamspace_dry_run(
    repo_root: Path,
    *,
    scan_root: Path | None = None,
    mission: str | None = None,
) -> TeamspaceDryRunReport:
    """Synthesize TeamSpace envelopes from local status logs and validate them."""
    event_cls, validate_event, package_version = _load_events_contract()
    mission_dirs = _select_mission_dirs(repo_root.resolve(), scan_root=scan_root, mission=mission)
    project_uuid = uuid.uuid5(
        uuid.NAMESPACE_URL,
        "spec-kitty:teamspace-dry-run:" + "|".join(path.name for path in mission_dirs),
    )
    errors: list[dict[str, object]] = []
    side_logs: list[dict[str, object]] = []
    count = 0
    repo_slug = _repo_slug(repo_root.resolve())
    project_slug = repo_slug or repo_root.resolve().name
    row_mappings: list[TeamspaceDryRunRowMapping] = []
    context_warnings = _teamspace_context_warnings(repo_root.resolve(), project_uuid)

    from specify_cli.status.store import read_events

    for mission_dir in mission_dirs:
        side_logs.extend(_classify_side_logs(repo_root.resolve(), mission_dir))
        raw_status_errors = _scan_raw_status_rows(repo_root.resolve(), mission_dir)
        errors.extend(raw_status_errors)
        if raw_status_errors:
            continue
        row_locations = _status_row_locations(mission_dir)
        try:
            events = read_events(mission_dir)
        except Exception as exc:
            errors.append(
                {
                    "mission_slug": mission_dir.name,
                    "error": "STATUS_EVENTS_UNREADABLE",
                    "message": str(exc),
                }
            )
            continue
        for index, status_event in enumerate(sorted(events, key=lambda e: (e.at, e.event_id)), start=1):
            count += 1
            envelope = _status_event_to_teamspace_envelope(
                status_event,
                project_uuid=project_uuid,
                lamport_clock=index,
                project_slug=project_slug,
                repo_slug=repo_slug,
            )
            row_location = row_locations.get(status_event.event_id)
            row_mappings.append(
                TeamspaceDryRunRowMapping(
                    mission_slug=status_event.mission_slug,
                    artifact_path=_repo_relpath(repo_root.resolve(), mission_dir / EVENTS_FILENAME),
                    line_number=row_location.line_number if row_location is not None else None,
                    source_event_id=status_event.event_id,
                    synthesized_event_id=envelope["event_id"],
                    synthesized_event_type=envelope["event_type"],
                    aggregate_id=envelope["aggregate_id"],
                    row_sha256=(
                        hashlib.sha256(row_location.text.encode("utf-8")).hexdigest()
                        if row_location is not None
                        else None
                    ),
                    envelope_sha256=hashlib.sha256(
                        json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    ).hexdigest(),
                )
            )
            try:
                event_cls.model_validate(envelope)
            except Exception as exc:
                errors.append(
                    {
                        "mission_slug": status_event.mission_slug,
                        "event_id": status_event.event_id,
                        "error": "ENVELOPE_INVALID",
                        "message": str(exc),
                    }
                )
                continue
            payload_result = validate_event(envelope["payload"], envelope["event_type"])
            if not payload_result.valid:
                errors.append(
                    {
                        "mission_slug": status_event.mission_slug,
                        "event_id": status_event.event_id,
                        "error": "PAYLOAD_INVALID",
                        "model_violations": [
                            {
                                "field": v.field,
                                "message": v.message,
                                "violation_type": v.violation_type,
                            }
                            for v in payload_result.model_violations
                        ],
                    }
                )

    return TeamspaceDryRunReport(
        schema_version=CANONICAL_ENVELOPE_SCHEMA_VERSION,
        events_package_version=package_version,
        envelope_count=count,
        valid=not errors,
        errors=tuple(errors),
        row_mappings=tuple(row_mappings),
        context_warnings=tuple(context_warnings),
        side_logs=tuple(side_logs),
    )


def _teamspace_context_warnings(repo_root: Path, project_uuid: uuid.UUID) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    try:
        from specify_cli.identity.project import load_identity

        identity = load_identity(repo_root / ".kittify" / "config.yaml")
    except Exception:
        identity = None

    if identity is None or identity.project_uuid is None:
        warnings.append(
            {
                "code": "TEAMSPACE_PROJECT_CONTEXT_MISSING",
                "message": (
                    "No persisted project.uuid was found; dry-run used a deterministic "
                    "offline project_uuid for schema validation only."
                ),
                "dry_run_project_uuid": str(project_uuid),
            }
        )

    warnings.append(
        {
            "code": "TEAMSPACE_TEAM_CONTEXT_NOT_VALIDATED",
            "message": "Team/private TeamSpace membership is not checked by offline dry-run.",
        }
    )
    return warnings


def _status_row_locations(mission_dir: Path) -> dict[str, _RawJsonlRow]:
    status_path = mission_dir / EVENTS_FILENAME
    if not status_path.exists():
        return {}
    try:
        rows = _read_jsonl_rows(status_path)
    except Exception:
        return {}

    locations: dict[str, _RawJsonlRow] = {}
    for row in rows:
        event_id = _event_id(row.data)
        if event_id is not None:
            locations.setdefault(event_id, row)
    return locations


def _load_events_contract() -> tuple[type[Any], Any, str]:
    import spec_kitty_events
    from spec_kitty_events import Event
    from spec_kitty_events.conformance import validate_event

    package_version = Version(spec_kitty_events.__version__)
    if package_version < REQUIRED_EVENTS_PACKAGE:
        raise MissionStateDryRunError(
            "TeamSpace dry-run requires spec-kitty-events >= "
            f"{REQUIRED_EVENTS_PACKAGE}; installed {package_version}."
        )
    return Event, validate_event, str(package_version)


def _status_event_to_teamspace_envelope(
    status_event: StatusEvent,
    *,
    project_uuid: uuid.UUID,
    lamport_clock: int,
    project_slug: str,
    repo_slug: str | None,
) -> dict[str, Any]:
    evidence = status_event.evidence.to_dict() if status_event.evidence else None
    if evidence is not None and not evidence.get("repos"):
        # Older done rows only recorded review evidence; the 5.0.0 TeamSpace
        # contract requires at least one repo evidence entry.
        evidence["repos"] = [
            {
                "repo": repo_slug or project_slug,
                "branch": "historical-mission-state-repair",
                "commit": "historical-mission-state-repair",
            }
        ]

    payload = {
        "mission_slug": status_event.mission_slug,
        "wp_id": status_event.wp_id,
        "from_lane": str(status_event.from_lane),
        "to_lane": str(status_event.to_lane),
        "actor": status_event.actor,
        "force": status_event.force,
        "reason": status_event.reason,
        "execution_mode": status_event.execution_mode,
        "review_ref": status_event.review_ref,
        "evidence": evidence,
    }
    return {
        "event_id": status_event.event_id,
        "event_type": "WPStatusChanged",
        "aggregate_id": status_event.wp_id,
        "aggregate_type": "WorkPackage",
        "payload": payload,
        "timestamp": status_event.at,
        "build_id": "mission-state-dry-run",
        "node_id": "mission-state-dry-run",
        "lamport_clock": lamport_clock,
        "causation_id": None,
        "project_uuid": str(project_uuid),
        "project_slug": project_slug,
        "repo_slug": repo_slug,
        "correlation_id": deterministic_ulid(
            f"teamspace-dry-run:{status_event.mission_slug}:{status_event.event_id}"
        ),
        "schema_version": CANONICAL_ENVELOPE_SCHEMA_VERSION,
    }


def _scan_raw_status_rows(repo_root: Path, mission_dir: Path) -> list[dict[str, object]]:
    status_path = mission_dir / EVENTS_FILENAME
    if not status_path.exists():
        return []
    try:
        rows = _read_jsonl_rows(status_path)
    except Exception as exc:
        return [
            {
                "mission_slug": mission_dir.name,
                "artifact_path": _repo_relpath(repo_root, status_path),
                "error": "STATUS_EVENTS_UNREADABLE",
                "message": str(exc),
            }
        ]

    errors: list[dict[str, object]] = []
    rel = _repo_relpath(repo_root, status_path)
    for row in rows:
        if "event_type" in row.data or "event_name" in row.data:
            errors.append(
                {
                    "mission_slug": mission_dir.name,
                    "artifact_path": rel,
                    "line_number": row.line_number,
                    "event_id": _event_id(row.data),
                    "error": "STATUS_ROW_NOT_REPAIRED",
                    "message": "typed side-log row remains in status.events.jsonl; run --fix before dry-run",
                }
            )
        for path, key in _find_forbidden_key_paths(row.data):
            errors.append(
                {
                    "mission_slug": mission_dir.name,
                    "artifact_path": rel,
                    "line_number": row.line_number,
                    "event_id": _event_id(row.data),
                    "error": "FORBIDDEN_LEGACY_KEY",
                    "path": path,
                    "key": key,
                }
            )
    return errors


def _classify_side_logs(repo_root: Path, mission_dir: Path) -> list[dict[str, object]]:
    candidates: list[Path] = [
        mission_dir / "decisions" / "events.jsonl",
        mission_dir / "handoff" / "events.jsonl",
        mission_dir / "mission-events.jsonl",
    ]
    archive = mission_dir / "_archive"
    if archive.exists():
        candidates.extend(sorted(archive.glob("*.events.jsonl")))

    side_logs: list[dict[str, object]] = []
    for path in candidates:
        if not path.exists():
            continue
        side_logs.append(
            {
                "artifact_path": _repo_relpath(repo_root, path),
                "row_count": _count_jsonl_rows(path),
                "disposition": "skipped_local_side_log",
                "reason": "out_of_scope_for_launch_import",
            }
        )

    runtime_root = repo_root / ".kittify" / "runtime"
    if runtime_root.exists():
        for path in sorted(runtime_root.glob("**/run.events.jsonl")):
            side_logs.append(
                {
                    "artifact_path": _repo_relpath(repo_root, path),
                    "row_count": _count_jsonl_rows(path),
                    "disposition": "skipped_runtime_side_log",
                    "reason": "out_of_scope_for_launch_import",
                }
            )
    return side_logs


def _find_forbidden_key_paths(value: Any, *, prefix: str = "$") -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            if key in FORBIDDEN_LEGACY_KEYS:
                findings.append((child_path, str(key)))
            findings.extend(_find_forbidden_key_paths(child, prefix=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_forbidden_key_paths(child, prefix=f"{prefix}[{index}]"))
    return findings


def _count_jsonl_rows(path: Path) -> int:
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0


def _repair_mission(repo_root: Path, mission_dir: Path, *, run_id: str) -> MissionRepairResult:
    mission_slug = mission_dir.name
    mission_id: str | None = None
    file_changes: list[FileChange] = []
    row_changes: list[RowTransformation] = []
    validation_errors: list[str] = []
    quarantined_rows = 0

    try:
        raw_rows = _read_jsonl_rows(mission_dir / EVENTS_FILENAME)
        meta, meta_actions = _canonicalize_meta(mission_dir, raw_rows)
        mission_slug = str(meta.get("mission_slug") or mission_slug)
        mission_id = str(meta.get("mission_id") or "")
        before_meta = _file_fingerprint(mission_dir / META_FILENAME)
        if meta_actions:
            write_meta(mission_dir, meta)
        after_meta = _file_fingerprint(mission_dir / META_FILENAME)
        if before_meta != after_meta:
            file_changes.append(_file_change(repo_root, mission_dir / META_FILENAME, before_meta, after_meta))

        status_path = mission_dir / EVENTS_FILENAME
        if status_path.exists():
            canonical_rows, row_transforms, quarantine_lines, row_errors = _canonicalize_status_rows(
                repo_root,
                mission_dir,
                raw_rows,
                mission_slug=mission_slug,
                mission_id=mission_id,
            )
            row_changes.extend(row_transforms)
            validation_errors.extend(row_errors)
            if row_errors:
                return MissionRepairResult(
                    mission_slug=mission_slug,
                    mission_id=mission_id,
                    status="error",
                    file_changes=file_changes,
                    row_transformations=row_changes,
                    quarantined_rows=len(quarantine_lines),
                    validation_errors=validation_errors,
                )
            before_events = _file_fingerprint(status_path)
            status_text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in canonical_rows)
            if status_path.read_text(encoding="utf-8") != status_text:
                atomic_write(status_path, status_text)
            after_events = _file_fingerprint(status_path)
            if before_events != after_events:
                file_changes.append(_file_change(repo_root, status_path, before_events, after_events))

            if quarantine_lines:
                quarantined_rows = len(quarantine_lines)
                quarantine_path = (
                    repo_root
                    / MANIFEST_ROOT
                    / "quarantine"
                    / run_id
                    / mission_slug
                    / EVENTS_FILENAME
                )
                before_quarantine = _file_fingerprint(quarantine_path)
                quarantine_text = "".join(line.rstrip("\n") + "\n" for line in quarantine_lines)
                atomic_write(quarantine_path, quarantine_text, mkdir=True)
                after_quarantine = _file_fingerprint(quarantine_path)
                if before_quarantine != after_quarantine:
                    file_changes.append(
                        _file_change(repo_root, quarantine_path, before_quarantine, after_quarantine)
                    )

            before_status = _file_fingerprint(mission_dir / STATUS_FILENAME)
            snapshot = materialize_snapshot(mission_dir)
            status_json = materialize_to_json(snapshot)
            if not (mission_dir / STATUS_FILENAME).exists() or (mission_dir / STATUS_FILENAME).read_text(encoding="utf-8") != status_json:
                atomic_write(mission_dir / STATUS_FILENAME, status_json)
            after_status = _file_fingerprint(mission_dir / STATUS_FILENAME)
            if before_status != after_status:
                file_changes.append(_file_change(repo_root, mission_dir / STATUS_FILENAME, before_status, after_status))

        return MissionRepairResult(
            mission_slug=mission_slug,
            mission_id=mission_id,
            status="updated" if file_changes or row_changes or quarantined_rows else "unchanged",
            file_changes=file_changes,
            row_transformations=row_changes,
            quarantined_rows=quarantined_rows,
            validation_errors=validation_errors,
        )
    except Exception as exc:
        validation_errors.append(str(exc))
        return MissionRepairResult(
            mission_slug=mission_slug,
            mission_id=mission_id,
            status="error",
            file_changes=file_changes,
            row_transformations=row_changes,
            quarantined_rows=quarantined_rows,
            validation_errors=validation_errors,
        )


def _canonicalize_meta(
    mission_dir: Path,
    raw_rows: Sequence[_RawJsonlRow],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    loaded = load_meta(mission_dir)
    meta = dict(loaded or {})
    actions: list[str] = []
    mission_slug = str(
        meta.get("mission_slug")
        or meta.get("slug")
        or meta.get("feature_slug")
        or mission_dir.name
    )
    meta["mission_slug"] = mission_slug
    meta.setdefault("slug", mission_slug)
    meta.setdefault("friendly_name", mission_slug)
    meta["mission_type"] = str(meta.get("mission_type") or meta.get("mission") or "software-dev")
    meta.setdefault("target_branch", "main")
    if not meta.get("created_at"):
        meta["created_at"] = _first_event_timestamp(raw_rows) or "1970-01-01T00:00:00+00:00"
        actions.append("created_at_defaulted")

    number_raw = meta.get("mission_number")
    if number_raw is None or number_raw == "":
        number_raw = meta.get("feature_number")
    mission_number = _coerce_mission_number(number_raw)
    if mission_number is None:
        mission_number = mission_number_from_slug(mission_slug)
    meta["mission_number"] = mission_number

    existing_id = meta.get("mission_id")
    if not isinstance(existing_id, str) or not ULID_PATTERN.match(existing_id):
        meta["mission_id"] = deterministic_ulid(_mission_seed(mission_dir, meta, raw_rows))
        actions.append("mission_id_deterministically_backfilled")

    for key in sorted(META_LEGACY_ALIASES):
        if key in meta:
            meta.pop(key, None)
            actions.append(f"removed_meta_key:{key}")

    errors = validate_meta(meta)
    if errors:
        raise ValueError(f"Invalid canonical meta.json for {mission_dir.name}: {'; '.join(errors)}")
    return meta, tuple(actions)


def _canonicalize_status_rows(
    repo_root: Path,
    mission_dir: Path,
    rows: Sequence[_RawJsonlRow],
    *,
    mission_slug: str,
    mission_id: str,
) -> tuple[list[dict[str, Any]], list[RowTransformation], list[str], list[str]]:
    canonical_rows: list[dict[str, Any]] = []
    row_changes: list[RowTransformation] = []
    quarantine_lines: list[str] = []
    errors: list[str] = []
    seen_event_ids: set[str] = set()
    rel = _repo_relpath(repo_root, mission_dir / EVENTS_FILENAME)

    for row in rows:
        result = _canonicalize_status_row(row.data, mission_slug=mission_slug, mission_id=mission_id, line_number=row.line_number)
        old_sha = _sha256_text(row.text)
        if result.error is not None:
            errors.append(f"{rel}:{row.line_number}: {result.error}")
            continue
        if result.row is None:
            quarantine_lines.append(row.text)
            row_changes.append(
                RowTransformation(
                    artifact_path=rel,
                    line_number=row.line_number,
                    event_id=_event_id(row.data),
                    actions=result.actions,
                    old_sha256=old_sha,
                    new_sha256=None,
                )
            )
            continue

        event_id = _event_id(result.row)
        actions = list(result.actions)
        if event_id in seen_event_ids:
            actions.append("duplicate_event_id_dropped")
            row_changes.append(
                RowTransformation(
                    artifact_path=rel,
                    line_number=row.line_number,
                    event_id=event_id,
                    actions=tuple(actions),
                    old_sha256=old_sha,
                    new_sha256=None,
                )
            )
            continue
        seen_event_ids.add(event_id or "")
        canonical_rows.append(result.row)
        new_text = json.dumps(result.row, sort_keys=True)
        if new_text != row.text.strip() or actions:
            row_changes.append(
                RowTransformation(
                    artifact_path=rel,
                    line_number=row.line_number,
                    event_id=event_id,
                    actions=tuple(actions),
                    old_sha256=old_sha,
                    new_sha256=_sha256_text(new_text),
                )
            )

    sorted_rows = sorted(canonical_rows, key=lambda item: (str(item.get("at", "")), str(item.get("event_id", ""))))
    return sorted_rows, row_changes, quarantine_lines, errors


def _canonicalize_status_row(  # noqa: C901
    data: Mapping[str, Any],
    *,
    mission_slug: str,
    mission_id: str,
    line_number: int,
) -> _CanonicalRowResult:
    if "event_type" in data or "event_name" in data:
        return _CanonicalRowResult(row=None, actions=("quarantined_non_status_event",))

    row = dict(data)
    actions: list[str] = []
    for old, new in STATUS_ROW_ALIASES.items():
        if old in row:
            if new not in row or not row.get(new):
                row[new] = row[old]
            row.pop(old, None)
            actions.append(f"renamed_key:{old}->{new}")
    for key in sorted(FORBIDDEN_LEGACY_KEYS - {"feature_slug"}):
        if key in row:
            row.pop(key, None)
            actions.append(f"removed_key:{key}")

    row["mission_slug"] = str(row.get("mission_slug") or mission_slug)
    row["mission_id"] = mission_id
    if not _valid_event_id(row.get("event_id")):
        row["event_id"] = deterministic_ulid(
            json.dumps(row, sort_keys=True, default=str) + f":line:{line_number}"
        )
        actions.append("event_id_deterministically_backfilled")
    if not row.get("at"):
        row["at"] = "1970-01-01T00:00:00+00:00"
        actions.append("at_defaulted")
    if row.get("from_lane") is None:
        row["from_lane"] = "planned"
        actions.append("from_lane_defaulted")
    if not row.get("to_lane"):
        return _CanonicalRowResult(row=None, actions=tuple(actions), error="missing required to_lane")
    if not row.get("wp_id"):
        return _CanonicalRowResult(row=None, actions=tuple(actions), error="missing required wp_id")

    for key in ("from_lane", "to_lane"):
        lane = str(row[key])
        normalized = LANE_ALIASES.get(lane, lane)
        if normalized not in VALID_LANES:
            return _CanonicalRowResult(
                row=None,
                actions=tuple(actions),
                error=f"unknown {key} {lane!r}",
            )
        if normalized != lane:
            actions.append(f"lane_alias:{key}:{lane}->{normalized}")
            row[key] = normalized

    actor = row.get("actor")
    if isinstance(actor, Mapping):
        metadata = dict(row.get("policy_metadata") or {})
        metadata.setdefault("migration_original_actor", actor)
        row["policy_metadata"] = metadata
        row["actor"] = _actor_label(actor)
        actions.append("actor_dict_labelled")
    elif not isinstance(actor, str) or not actor.strip():
        row["actor"] = "migration"
        actions.append("actor_defaulted")
    else:
        normalized_actor = _normalize_actor(actor)
        if normalized_actor != actor:
            row["actor"] = normalized_actor
            actions.append("actor_normalized")

    if "force" not in row:
        row["force"] = False
        actions.append("force_defaulted")
    if row.get("execution_mode") not in VALID_EXECUTION_MODES:
        row["execution_mode"] = "direct_repo"
        actions.append("execution_mode_defaulted")

    canonical = {
        "event_id": str(row["event_id"]),
        "mission_slug": str(row["mission_slug"]),
        "wp_id": str(row.get("wp_id") or ""),
        "from_lane": str(row["from_lane"]),
        "to_lane": str(row["to_lane"]),
        "at": str(row["at"]),
        "actor": str(row["actor"]),
        "force": bool(row["force"]),
        "execution_mode": str(row["execution_mode"]),
        "reason": row.get("reason"),
        "review_ref": row.get("review_ref"),
        "evidence": row.get("evidence"),
        "policy_metadata": row.get("policy_metadata"),
        "mission_id": mission_id,
    }
    try:
        StatusEvent.from_dict(canonical)
    except Exception as exc:
        return _CanonicalRowResult(row=None, actions=tuple(actions), error=str(exc))
    return _CanonicalRowResult(row=canonical, actions=tuple(actions))


def _select_mission_dirs(repo_root: Path, *, scan_root: Path | None, mission: str | None) -> list[Path]:
    root = (scan_root or repo_root / "kitty-specs").resolve()
    if not root.exists():
        return []
    all_dirs = sorted(path for path in root.iterdir() if path.is_dir())
    if mission is None:
        return all_dirs
    matches = [path for path in all_dirs if _mission_handle_matches(path, mission)]
    if not matches:
        raise MissionStateRepairError(f"Mission not found: {mission!r}")
    if len(matches) > 1:
        candidates = ", ".join(path.name for path in matches)
        raise MissionStateRepairError(f"Ambiguous mission handle {mission!r}: {candidates}")
    return matches


def _mission_handle_matches(path: Path, handle: str) -> bool:
    if path.name == handle:
        return True
    prefix = _MISSION_PREFIX_RE.match(path.name)
    if prefix and prefix.group(1) == handle:
        return True
    stripped = path.name[4:] if prefix else path.name
    if stripped == handle:
        return True
    try:
        meta = load_meta(path) or {}
    except Exception:
        meta = {}
    mission_id = meta.get("mission_id")
    if isinstance(mission_id, str):
        if mission_id == handle:
            return True
        if _MID8_RE.match(handle) and mission_id.startswith(handle):
            return True
    return False


def _read_jsonl_rows(path: Path) -> list[_RawJsonlRow]:
    if not path.exists():
        return []
    rows: list[_RawJsonlRow] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
            if not isinstance(data, dict):
                raise ValueError(f"Invalid JSONL row on line {line_number}: expected object")
            rows.append(_RawJsonlRow(line_number=line_number, text=stripped, data=data))
    return rows


def _first_event_timestamp(rows: Sequence[_RawJsonlRow]) -> str | None:
    values = sorted(str(row.data["at"]) for row in rows if row.data.get("at"))
    return values[0] if values else None


def _mission_seed(mission_dir: Path, meta: Mapping[str, Any], rows: Sequence[_RawJsonlRow]) -> str:
    stable_meta = {
        "mission_slug": meta.get("mission_slug") or mission_dir.name,
        "slug": meta.get("slug"),
        "friendly_name": meta.get("friendly_name"),
        "created_at": meta.get("created_at"),
        "target_branch": meta.get("target_branch"),
        "mission_type": meta.get("mission_type"),
    }
    first_event = rows[0].data if rows else {}
    return json.dumps(
        {
            "meta": stable_meta,
            "first_event_id": first_event.get("event_id"),
            "first_event_at": first_event.get("at"),
        },
        sort_keys=True,
        default=str,
    )


def _coerce_mission_number(value: object) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError(f"mission_number must be int or null, got bool {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.isdigit():
            return int(stripped.lstrip("0") or "0")
    raise ValueError(f"mission_number must be int or numeric string, got {value!r}")


def _normalize_actor(value: str) -> str:
    actor = _ACTOR_SAFE.sub("-", value.strip().lower()).strip("-_.:")
    return actor or "migration"


def _actor_label(actor: Mapping[str, Any]) -> str:
    for key in ("profile", "role", "display_name", "actor_id", "name"):
        value = actor.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_actor(value)
    return "structured-actor"


def _event_id(row: Mapping[str, Any]) -> str | None:
    value = row.get("event_id")
    return str(value) if value is not None else None


def _valid_event_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return bool(ULID_PATTERN.match(value) or _UUID_HYPHEN_RE.match(value) or _UUID_BARE_RE.match(value))


def _compute_run_id(repo_root: Path, mission_dirs: Sequence[Path]) -> str:
    digest = hashlib.sha256()
    digest.update(b"spec-kitty:mission-state:v1\n")
    for mission_dir in mission_dirs:
        for name in (META_FILENAME, EVENTS_FILENAME, STATUS_FILENAME):
            path = mission_dir / name
            rel = _repo_relpath(repo_root, path)
            digest.update(rel.encode("utf-8") + b"\0")
            if path.exists():
                digest.update(path.read_bytes())
            else:
                digest.update(b"<missing>")
            digest.update(b"\0")
    return digest.hexdigest()[:16]


def _file_fingerprint(path: Path) -> tuple[str | None, int | None]:
    if not path.exists():
        return None, None
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def _file_change(
    repo_root: Path,
    path: Path,
    old: tuple[str | None, int | None],
    new: tuple[str | None, int | None],
) -> FileChange:
    return FileChange(
        path=_repo_relpath(repo_root, path),
        old_sha256=old[0],
        new_sha256=new[0],
        old_size=old[1],
        new_size=new[1],
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _repo_relpath(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _resolve_repo_relative(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return repo_root / path


def _is_remote_url(slug: str) -> bool:
    """Return True when *slug* is an HTTP(S) remote URL."""
    return urlsplit(slug).scheme in _REMOTE_URL_SCHEMES


def _repo_slug(repo_root: Path) -> str | None:
    result = _git(repo_root, "config", "--get", "remote.origin.url", check=False)
    remote = result.stdout.strip()
    if not remote:
        return repo_root.name
    slug = remote.removesuffix(".git").rstrip("/")
    if ":" in slug and not _is_remote_url(slug):
        slug = slug.rsplit(":", 1)[1]
    elif "/" in slug:
        parts = slug.split("/")
        slug = "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]
    return slug or repo_root.name


def _git_head(repo_root: Path) -> str | None:
    result = _git(repo_root, "rev-parse", "HEAD", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _assert_git_safe(repo_root: Path, rel_paths: Sequence[str], *, allow_dirty: bool) -> None:
    if allow_dirty or not _is_git_repo(repo_root):
        return
    dirty: list[str] = []
    for worktree in _git_worktrees(repo_root):
        result = _git(worktree, "status", "--porcelain", "--", *rel_paths, check=False)
        if result.stdout.strip():
            dirty.append(f"{worktree}: {result.stdout.strip()}")
    if dirty:
        raise MissionStateRepairError(
            "Refusing mission-state repair with dirty relevant paths. "
            "Commit/stash them first or pass --allow-dirty.\n" + "\n".join(dirty)
        )


def _is_git_repo(repo_root: Path) -> bool:
    return _git(repo_root, "rev-parse", "--is-inside-work-tree", check=False).returncode == 0


def _git_worktrees(repo_root: Path) -> list[Path]:
    result = _git(repo_root, "worktree", "list", "--porcelain", check=False)
    if result.returncode != 0:
        return [repo_root]
    worktrees: list[Path] = []
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            worktrees.append(Path(line.removeprefix("worktree ")))
    return worktrees or [repo_root]


class _git_lock:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root
        self._path: Path | None = None
        self._fd: int | None = None

    def __enter__(self) -> None:
        if not _is_git_repo(self._repo_root):
            return
        result = _git(self._repo_root, "rev-parse", "--git-common-dir", check=False)
        if result.returncode != 0:
            return
        common = Path(result.stdout.strip())
        if not common.is_absolute():
            common = self._repo_root / common
        common.mkdir(parents=True, exist_ok=True)
        self._path = common / "spec-kitty-mission-state.lock"
        try:
            self._fd = os.open(str(self._path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self._fd, str(os.getpid()).encode("ascii"))
        except FileExistsError as exc:
            raise MissionStateRepairError(
                f"Another mission-state repair appears to be running: {self._path}"
            ) from exc

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
        if self._path is not None:
            with suppress(FileNotFoundError):
                self._path.unlink()


def _git(repo_root: Path, *args: str, check: bool) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=check,
        text=True,
        capture_output=True,
    )


__all__ = [
    "CANONICAL_ENVELOPE_SCHEMA_VERSION",
    "MIGRATION_SCHEMA_VERSION",
    "MissionStateDryRunError",
    "MissionStateRepairError",
    "RepairReport",
    "TeamspaceDryRunRowMapping",
    "TeamspaceDryRunReport",
    "deterministic_ulid",
    "repair_repo",
    "teamspace_dry_run",
]
