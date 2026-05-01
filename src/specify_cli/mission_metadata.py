"""Single metadata writer API for all meta.json operations.

This module is the canonical entry point for reading, validating, and writing
mission metadata (``meta.json``).  All mutation helpers go through
:func:`write_meta`, which enforces validation, a standard serialization
format, and atomic writes.

Standard format::

    json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\\n"

Atomic writes use ``tempfile.mkstemp`` + ``os.replace`` so the file is
always either the old version or the new version, never a partial write.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from specify_cli.core.atomic import atomic_write


# ---------------------------------------------------------------------------
# TypedDict definitions (for static type checking / documentation only)
# ---------------------------------------------------------------------------


class MissionMetaRequired(TypedDict):
    """Required fields -- always present in a valid meta.json.

    Note: ``mission_number`` is stored as ``int | null`` in meta.json
    (per FR-044).  This TypedDict uses ``str`` for backward-compatibility
    documentation only; the actual runtime type is ``int | None``.
    """

    slug: str
    mission_slug: str
    friendly_name: str
    mission_type: str
    target_branch: str
    created_at: str


class MissionMetaOptional(TypedDict, total=False):
    """Optional fields -- present only after specific operations."""

    purpose_tldr: str
    purpose_context: str
    vcs: str
    vcs_locked_at: str
    accepted_at: str
    accepted_by: str
    acceptance_mode: str
    accepted_from_commit: str
    accept_commit: str
    acceptance_history: list[dict[str, Any]]
    merged_at: str
    merged_by: str
    merged_into: str
    merged_strategy: str
    merged_push: bool
    merged_commit: str
    merge_history: list[dict[str, Any]]
    documentation_state: dict[str, Any]
    origin_ticket: dict[str, Any]
    source_description: str
    mission_branch: str
    change_mode: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: frozenset[str] = frozenset(MissionMetaRequired.__annotations__)
HISTORY_CAP: int = 20
VALID_CHANGE_MODES: frozenset[str] = frozenset({"bulk_edit"})
_MISSION_NUMBER_PATTERN = re.compile(r"^(?P<number>\d+)-")
_PURPOSE_FIELDS: tuple[str, str] = ("purpose_tldr", "purpose_context")


@dataclass(frozen=True, slots=True)
class MissionIdentity:
    """Canonical machine-facing mission identity fields.

    ``mission_number`` is ``int | None``:
    - ``None``  — pre-merge mission (no number assigned yet; FR-044)
    - ``int``   — post-merge mission (dense display number assigned at merge)

    Legacy missions stored as strings (``"042"``) are coerced to ``int`` by
    the reader (``resolve_mission_identity``).  The write path always emits
    ``null`` or an integer, never a string sentinel (FR-044, T008).
    """

    mission_slug: str
    mission_number: int | None
    mission_type: str
    mission_id: str | None = None  # Canonical identity per ADR b85116ed. None only for pre-3.1.1 missions.


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Current UTC time in ISO 8601."""
    return _dt.datetime.now(_dt.UTC).isoformat()


def mission_number_from_slug(mission_slug: str) -> int | None:
    """Extract the numeric mission prefix from a mission slug when present.

    Returns the prefix as an ``int`` if the slug starts with ``NNN-``,
    or ``None`` if no numeric prefix is found.

    Examples:
        "083-foo-bar" -> 83
        "foo-bar"     -> None
    """
    match = _MISSION_NUMBER_PATTERN.match(str(mission_slug).strip())
    if match is None:
        return None
    raw = match.group("number")
    try:
        return int(raw.lstrip("0") or "0") or int(raw)
    except ValueError:
        return None


def _coerce_mission_number(raw: object) -> int | None:
    """Coerce a raw meta.json ``mission_number`` value to ``int | None``.

    Canonical coercion matrix (T008 / FR-044):

    - ``None``, ``""`` (missing or empty)   → ``None``
    - ``int``                                → pass through
    - ``str`` that parses as positive int    → ``int`` (leading zeros stripped)
    - ``str`` "pending", "unassigned", "TBD" → ``ValueError``
    - ``str`` not parseable as int           → ``ValueError``
    - ``float``, ``list``, etc.              → ``TypeError``
    """
    _SENTINEL_STRINGS = frozenset({"pending", "unassigned", "TBD"})

    if raw is None:
        return None
    if isinstance(raw, bool):
        # bool is a subclass of int, but a bool mission_number is a bug
        raise TypeError(
            f"meta.json mission_number must be int or null, got bool {raw!r}."
        )
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        if not raw.strip():
            # empty or whitespace-only string → None
            return None
        if raw.strip() in _SENTINEL_STRINGS:
            raise ValueError(
                f"meta.json mission_number must be int or null, got {raw!r}. "
                "Run `spec-kitty migrate backfill-identity` to migrate."
            )
        try:
            stripped = raw.strip().lstrip("0")
            return int(stripped) if stripped else 0
        except ValueError:
            raise ValueError(
                f"meta.json mission_number must be int or null, got {raw!r}. "
                "Run `spec-kitty migrate backfill-identity` to migrate."
            ) from None
    raise TypeError(
        f"meta.json mission_number must be int, str, or null, got {type(raw).__name__!r}."
    )


def mission_identity_fields(
    mission_slug: str,
    mission_number: int | str | None = None,
    mission_type: str | None = None,
) -> dict[str, str]:
    """Normalize canonical mission identity fields for machine-facing payloads.

    Converts ``mission_number`` to a display string at the payload boundary.
    ``None`` becomes ``""``; integers are formatted as their decimal string
    representation (no leading-zero padding — that is display-layer choice).
    """
    resolved_slug = str(mission_slug).strip()
    # Stringify mission_number at the display boundary
    if isinstance(mission_number, int):
        resolved_number: str = str(mission_number)
    else:
        resolved_number = str(mission_number or "").strip()
    # Fall back to slug-derived prefix if no number provided
    if not resolved_number:
        slug_number = mission_number_from_slug(resolved_slug)
        resolved_number = str(slug_number) if slug_number is not None else ""
    resolved_type = str(mission_type or "").strip() or "software-dev"
    return {
        "mission_slug": resolved_slug,
        "mission_number": resolved_number,
        "mission_type": resolved_type,
    }


def resolve_mission_identity(feature_dir: Path) -> MissionIdentity:
    """Resolve canonical mission identity fields from a mission directory.

    Reads ``meta.json`` and coerces ``mission_number`` to ``int | None``
    using the legacy coercion rule (T008):

    - Stored as JSON null   → ``None``
    - Stored as JSON int    → ``int``
    - Stored as string "042" → ``42`` (leading zeros stripped)
    - Stored as "pending" / sentinel → raises ``ValueError``
    """
    meta = load_meta(feature_dir) or {}
    raw_number = meta.get("mission_number")
    mission_number: int | None = _coerce_mission_number(raw_number)

    resolved_slug = str(meta.get("mission_slug") or meta.get("slug") or feature_dir.name)
    resolved_type = str(meta.get("mission_type") or meta.get("mission") or "").strip() or "software-dev"

    return MissionIdentity(
        mission_slug=resolved_slug,
        mission_number=mission_number,
        mission_type=resolved_type,
        mission_id=meta.get("mission_id"),  # None if not present (legacy mission)
    )


# ---------------------------------------------------------------------------
# Core read / validate / write
# ---------------------------------------------------------------------------


def load_meta(feature_dir: Path) -> dict[str, Any] | None:
    """Load ``meta.json`` from *feature_dir*.  Returns ``None`` if missing.

    Raises :class:`ValueError` when the file exists but contains malformed
    JSON.
    """
    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        return None
    text = meta_path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {meta_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {meta_path}, got {type(data).__name__}")
    return data


def validate_meta(meta: dict[str, Any]) -> list[str]:
    """Validate *meta* content.  Returns a list of error messages (empty = valid).

    Only required fields are checked.  Unknown fields are silently
    preserved for forward compatibility.
    """
    errors: list[str] = []
    for field in sorted(REQUIRED_FIELDS):
        if field not in meta or not meta[field]:
            errors.append(f"Missing or empty required field: {field}")
    for field in _PURPOSE_FIELDS:
        if field in meta:
            value = meta[field]
            if not isinstance(value, str):
                errors.append(f"Field {field} must be a string when present")
            elif not " ".join(value.split()):
                errors.append(f"Field {field} must not be empty when present")
    if "change_mode" in meta and meta["change_mode"] not in VALID_CHANGE_MODES:
        errors.append(
            f"Invalid change_mode {meta['change_mode']!r}; "
            f"valid values: {sorted(VALID_CHANGE_MODES)}"
        )
    return errors


def validate_purpose_summary(
    purpose_tldr: str | None,
    purpose_context: str | None,
) -> list[str]:
    """Validate required mission-purpose summary fields for new missions."""
    errors: list[str] = []

    if not isinstance(purpose_tldr, str) or not " ".join(purpose_tldr.split()):
        errors.append("purpose_tldr is required and must be a non-empty string")
    elif "\n" in purpose_tldr.strip():
        errors.append("purpose_tldr must be a single line")

    if not isinstance(purpose_context, str) or not " ".join(purpose_context.split()):
        errors.append("purpose_context is required and must be a non-empty string")

    return errors


def write_meta(
    feature_dir: Path,
    meta: dict[str, Any],
    *,
    validate: bool = True,
) -> None:
    """Write ``meta.json`` with standard formatting and atomic write.

    Standard format: sorted keys, 2-space indent, Unicode preserved,
    trailing newline.

    Args:
        feature_dir: Directory containing meta.json.
        meta: Metadata dict to write.
        validate: If True (default), validate required fields before writing.
            Set to False for tolerant writes (e.g., doc_state writes to
            meta.json files that may lack required top-level fields).

    Raises :class:`ValueError` if *validate* is True and validation fails.
    """
    if validate:
        errors = validate_meta(meta)
        if errors:
            raise ValueError(f"Invalid meta.json for {feature_dir.name}: {'; '.join(errors)}")
    content = json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    meta_path = feature_dir / "meta.json"
    atomic_write(meta_path, content)


# ---------------------------------------------------------------------------
# Mutation helpers
# ---------------------------------------------------------------------------


def record_acceptance(
    feature_dir: Path,
    *,
    accepted_by: str,
    mode: str,
    from_commit: str | None = None,
    accept_commit: str | None = None,
) -> dict[str, Any]:
    """Record acceptance metadata.  Appends to bounded history."""
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")

    now = _now_iso()
    entry: dict[str, Any] = {
        "accepted_at": now,
        "accepted_by": accepted_by,
        "acceptance_mode": mode,
    }
    if from_commit is not None:
        entry["accepted_from_commit"] = from_commit
    if accept_commit is not None:
        entry["accept_commit"] = accept_commit

    # Set top-level fields — always clear stale commit fields first
    meta["accepted_at"] = now
    meta["accepted_by"] = accepted_by
    meta["acceptance_mode"] = mode
    meta.pop("accepted_from_commit", None)
    meta.pop("accept_commit", None)
    if from_commit is not None:
        meta["accepted_from_commit"] = from_commit
    if accept_commit is not None:
        meta["accept_commit"] = accept_commit

    # Bounded history
    history: list[dict[str, Any]] = meta.get("acceptance_history", [])
    history.append(entry)
    if len(history) > HISTORY_CAP:
        history = history[-HISTORY_CAP:]
    meta["acceptance_history"] = history

    write_meta(feature_dir, meta)
    return meta


def record_merge(
    feature_dir: Path,
    *,
    merged_by: str,
    merged_into: str,
    strategy: str,
    push: bool,
) -> dict[str, Any]:
    """Record merge metadata.  Appends to bounded history."""
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")

    now = _now_iso()
    meta["merged_at"] = now
    meta["merged_by"] = merged_by
    meta["merged_into"] = merged_into
    meta["merged_strategy"] = strategy
    meta["merged_push"] = push
    # Clear merged_commit since this is a new merge (not yet finalized)
    meta.pop("merged_commit", None)

    entry: dict[str, Any] = {
        "merged_at": now,
        "merged_by": merged_by,
        "merged_into": merged_into,
        "merged_strategy": strategy,
        "merged_push": push,
        "merged_commit": None,
    }
    history: list[dict[str, Any]] = meta.get("merge_history", [])
    history.append(entry)
    if len(history) > HISTORY_CAP:
        history = history[-HISTORY_CAP:]
    meta["merge_history"] = history

    write_meta(feature_dir, meta)
    return meta


def finalize_merge(
    feature_dir: Path,
    *,
    merged_commit: str,
) -> dict[str, Any]:
    """Set final merge commit hash.  Updates both top-level and latest history entry."""
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")

    meta["merged_commit"] = merged_commit
    history: list[dict[str, Any]] = meta.get("merge_history", [])
    if history:
        history[-1]["merged_commit"] = merged_commit
    meta["merge_history"] = history

    write_meta(feature_dir, meta)
    return meta


def set_vcs_lock(
    feature_dir: Path,
    *,
    vcs_type: str,
    locked_at: str | None = None,
) -> dict[str, Any]:
    """Set VCS type and lock timestamp."""
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")

    meta["vcs"] = vcs_type
    if locked_at is not None:
        meta["vcs_locked_at"] = locked_at

    write_meta(feature_dir, meta)
    return meta


def set_documentation_state(
    feature_dir: Path,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Set or replace ``documentation_state`` subtree."""
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")

    meta["documentation_state"] = state

    write_meta(feature_dir, meta)
    return meta


def set_origin_ticket(
    feature_dir: Path,
    origin_ticket: dict[str, Any],
) -> dict[str, Any]:
    """Set or replace ``origin_ticket`` subtree in meta.json.

    The *origin_ticket* dict must contain all required keys:
    ``provider``, ``resource_type``, ``resource_id``,
    ``external_issue_id``, ``external_issue_key``,
    ``external_issue_url``, ``title``.

    Raises:
        FileNotFoundError: If meta.json does not exist in *feature_dir*.
        ValueError: If any required key is missing from *origin_ticket*.
    """
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")

    required_keys = {
        "provider",
        "resource_type",
        "resource_id",
        "external_issue_id",
        "external_issue_key",
        "external_issue_url",
        "title",
    }
    missing = required_keys - set(origin_ticket.keys())
    if missing:
        raise ValueError(f"origin_ticket missing required keys: {sorted(missing)}")

    meta["origin_ticket"] = origin_ticket
    write_meta(feature_dir, meta)
    return meta


def set_target_branch(
    feature_dir: Path,
    branch: str,
) -> dict[str, Any]:
    """Set ``target_branch`` field."""
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")

    meta["target_branch"] = branch

    write_meta(feature_dir, meta)
    return meta


def set_purpose_summary(
    feature_dir: Path,
    *,
    purpose_tldr: str,
    purpose_context: str,
) -> dict[str, Any]:
    """Set mission-purpose summary fields in ``meta.json``."""
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")

    errors = validate_purpose_summary(purpose_tldr, purpose_context)
    if errors:
        raise ValueError("; ".join(errors))

    meta["purpose_tldr"] = " ".join(purpose_tldr.split())
    meta["purpose_context"] = " ".join(purpose_context.split())
    write_meta(feature_dir, meta)
    return meta


def set_change_mode(
    feature_dir: Path,
    mode: str,
) -> dict[str, Any]:
    """Set ``change_mode`` field.

    Validates *mode* is in :data:`VALID_CHANGE_MODES` before writing.

    Raises:
        ValueError: If *mode* is not a recognized change mode.
        FileNotFoundError: If meta.json does not exist in *feature_dir*.
    """
    if mode not in VALID_CHANGE_MODES:
        raise ValueError(
            f"Invalid change_mode {mode!r}; valid values: {sorted(VALID_CHANGE_MODES)}"
        )
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")

    meta["change_mode"] = mode
    write_meta(feature_dir, meta)
    return meta


def get_change_mode(feature_dir: Path) -> str | None:
    """Read ``change_mode`` from meta.json.

    Returns ``None`` if meta.json is missing or the field is absent.
    """
    meta = load_meta(feature_dir)
    if meta is None:
        return None
    return meta.get("change_mode")
