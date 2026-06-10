"""Migration: rewrite legacy ``kitty-ops/*.jsonl`` Op records to the v2 event schema.

This is the **sole** sanctioned in-place mutation of Op records (C-004
exception, FR-011). Per the normative mapping table in the mission data model:

- started events with ``invocation_id`` + ``profile_id`` are rewritten to
  ``OpStartedEvent`` (missing ``mode_of_work`` -> ``"task_execution"``;
  missing/empty ``actor`` / ``action`` -> the literal ``"unrecorded"`` —
  never a fabricated plausible value)
- completed events gain ``closed_by="agent"``; a null ``outcome`` (old
  auto-close artifact) becomes ``outcome="abandoned"``; a missing
  ``completed_at`` falls back to the started event's ``started_at`` and is
  flagged in the migration report
- link/glossary lines pass through byte-identical
- files with an unparseable or identity-less started event are deleted and
  reported (operator-visible: count + filenames)
- already-v2 files are skipped untouched (idempotency, NFR-004)

Excluded files (different schemas, never touched): ``ops-index.jsonl``,
``lifecycle.jsonl``, ``propagation-errors.jsonl``.

``ops-index.jsonl`` consistency: deleting a per-op file can leave a dangling
index entry. The index reader (``invocations_cmd._iter_records_from_index``)
tolerates missing files — ``_read_first_line`` / ``_read_completed_record``
catch ``OSError`` and degrade gracefully — so this migration deliberately
leaves the index alone.

Rewrites are atomic: content is written to ``<file>.tmp`` in the same
directory and moved over the original with ``os.replace``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

#: kitty-ops files with different schemas that this migration must never touch.
EXCLUDED_FILES: frozenset[str] = frozenset(
    {
        "ops-index.jsonl",
        "lifecycle.jsonl",
        "propagation-errors.jsonl",
    }
)

_OPS_DIR = "kitty-ops"


def _eligible_files(ops_dir: Path) -> list[Path]:
    """Per-op JSONL files in ``kitty-ops/``, excluding the three special files."""
    if not ops_dir.is_dir():
        return []
    return sorted(p for p in ops_dir.glob("*.jsonl") if p.name not in EXCLUDED_FILES)


def _read_lines(path: Path) -> list[str] | None:
    """Return the non-empty lines of *path*, or ``None`` on read failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return [line for line in text.splitlines() if line.strip()]


class _FilePlan:
    """Disposition for one per-op file: skip, rewrite, or delete."""

    def __init__(
        self,
        action: str,  # "skip" | "rewrite" | "delete"
        new_lines: list[str] | None = None,
        warnings: list[str] | None = None,
        reason: str = "",
    ) -> None:
        self.action = action
        self.new_lines = new_lines or []
        self.warnings = warnings or []
        self.reason = reason


def _is_v2_started(data: dict[str, Any]) -> bool:
    from specify_cli.invocation.record import OpStartedEvent

    try:
        OpStartedEvent.model_validate(data)
    except ValidationError:
        return False
    return True


def _is_v2_completed(data: dict[str, Any]) -> bool:
    from specify_cli.invocation.record import OpCompletedEvent

    try:
        OpCompletedEvent.model_validate(data)
    except ValidationError:
        return False
    return True


def _str_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _map_completed_line(
    data: dict[str, Any],
    file_name: str,
    invocation_id: str,
    started_at: str,
    warnings: list[str],
) -> str | None:
    """Map one legacy completed line to its v2 JSONL line (None = unsalvageable)."""
    from specify_cli.invocation.record import OpCompletedEvent

    completed_at = _str_or_empty(data.get("completed_at"))
    if not completed_at:
        completed_at = started_at
        warnings.append(f"{file_name}: completed_at missing; fell back to started_at")
    outcome = data.get("outcome")
    if outcome not in ("done", "failed", "abandoned"):
        outcome = "abandoned"
    try:
        event = OpCompletedEvent.model_validate(
            {
                "event": "completed",
                "invocation_id": _str_or_empty(data.get("invocation_id")) or invocation_id,
                "completed_at": completed_at,
                "outcome": outcome,
                "closed_by": "agent",
                "evidence_ref": data.get("evidence_ref"),
            }
        )
    except ValidationError:
        return None
    return cast(str, event.to_jsonl_line())


def _plan_file(path: Path) -> _FilePlan:
    """Classify one per-op file per the normative mapping table."""
    from specify_cli.invocation.record import OpStartedEvent

    lines = _read_lines(path)
    if lines is None or not lines:
        return _FilePlan("delete", reason="unreadable or empty file")

    parsed: list[dict[str, Any]] = []
    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return _FilePlan("delete", reason="unparseable JSON line")
        if not isinstance(data, dict):
            return _FilePlan("delete", reason="non-object JSONL line")
        parsed.append(data)

    started_idx = next((i for i, d in enumerate(parsed) if d.get("event") == "started"), None)
    if started_idx is None:
        return _FilePlan("delete", reason="missing started event")
    started = parsed[started_idx]

    invocation_id = _str_or_empty(started.get("invocation_id"))
    profile_id = _str_or_empty(started.get("profile_id"))
    if not invocation_id or not profile_id:
        return _FilePlan("delete", reason="started event lacks invocation_id/profile_id")

    # Already v2? Started has mode_of_work and every completed line has closed_by.
    completed_lines = [d for d in parsed if d.get("event") == "completed"]
    if _is_v2_started(started) and all(_is_v2_completed(d) for d in completed_lines):
        return _FilePlan("skip")

    warnings: list[str] = []
    started_at = _str_or_empty(started.get("started_at"))

    started_payload: dict[str, Any] = {
        "event": "started",
        "invocation_id": invocation_id,
        "profile_id": profile_id,
        "action": _str_or_empty(started.get("action")) or "unrecorded",
        "request_text": _str_or_empty(started.get("request_text")),
        "actor": _str_or_empty(started.get("actor")) or "unrecorded",
        "mode_of_work": _str_or_empty(started.get("mode_of_work")) or "task_execution",
        "governance_context_hash": _str_or_empty(started.get("governance_context_hash")),
        "governance_context_available": bool(started.get("governance_context_available", True)),
        "router_confidence": started.get("router_confidence"),
        "started_at": started_at,
        "mission_id": started.get("mission_id"),
        "wp_id": started.get("wp_id"),
    }
    try:
        started_event = OpStartedEvent.model_validate(started_payload)
    except ValidationError:
        return _FilePlan("delete", reason="started event not representable as v2")

    new_lines: list[str] = []
    for i, (data, original) in enumerate(zip(parsed, lines, strict=True)):
        event = data.get("event")
        if event == "started" and i == started_idx:
            new_lines.append(started_event.to_jsonl_line())
            continue
        if event == "completed":
            if _is_v2_completed(data):
                new_lines.append(original)
                continue
            mapped = _map_completed_line(data, path.name, invocation_id, started_at, warnings)
            if mapped is None:
                return _FilePlan("delete", reason="completed event not representable as v2")
            new_lines.append(mapped)
            continue
        # link/glossary and any other non-lifecycle lines pass through byte-identical
        new_lines.append(original)

    return _FilePlan("rewrite", new_lines=new_lines, warnings=warnings)


def _atomic_rewrite(path: Path, lines: list[str]) -> None:
    """Write *lines* to ``<path>.tmp`` then ``os.replace`` over the original."""
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        tmp_path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@MigrationRegistry.register
class OpRecordSchemaV2Migration(BaseMigration):
    """Rewrite legacy kitty-ops Op records to the v2 event schema."""

    migration_id = "3_3_0_op_record_schema_v2"
    description = "Migrate legacy kitty-ops/*.jsonl Op records to the v2 event schema (rewrite salvageable records, delete unsalvageable files)"
    target_version = "3.2.0rc41"
    runs_on_worktrees = True

    def detect(self, project_path: Path) -> bool:
        """Return ``True`` iff any per-op file needs rewriting or deletion."""
        return any(_plan_file(path).action != "skip" for path in _eligible_files(project_path / _OPS_DIR))

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """The migration only needs a readable ``kitty-ops/`` directory."""
        if not (project_path / _OPS_DIR).is_dir():
            return False, "kitty-ops/ directory does not exist"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Rewrite or delete each eligible legacy file; skip v2 files."""
        changes: list[str] = []
        warnings: list[str] = []
        deleted: list[str] = []

        for path in _eligible_files(project_path / _OPS_DIR):
            plan = _plan_file(path)
            if plan.action == "skip":
                continue
            if plan.action == "delete":
                if dry_run:
                    changes.append(f"Would delete {path.name} ({plan.reason})")
                else:
                    path.unlink(missing_ok=True)
                    deleted.append(path.name)
                    changes.append(f"Deleted unsalvageable {path.name} ({plan.reason})")
                continue
            # rewrite
            if dry_run:
                changes.append(f"Would rewrite {path.name} to v2 schema")
            else:
                _atomic_rewrite(path, plan.new_lines)
                changes.append(f"Rewrote {path.name} to v2 schema")
            warnings.extend(plan.warnings)

        if deleted:
            warnings.append(f"Deleted {len(deleted)} unsalvageable Op record file(s): " + ", ".join(deleted))

        return MigrationResult(success=True, changes_made=changes, warnings=warnings)
