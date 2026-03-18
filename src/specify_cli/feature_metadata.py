"""Single metadata writer API for all meta.json operations.

This module is the canonical entry point for reading, validating, and writing
feature metadata (``meta.json``).  All mutation helpers go through
:func:`write_meta`, which enforces validation, a standard serialization
format, and atomic writes.

Standard format::

    json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\\n"

Atomic writes use ``tempfile.mkstemp`` + ``os.replace`` so the file is
always either the old version or the new version, never a partial write.
"""

from __future__ import annotations

import json
import os
import tempfile
import contextlib
import datetime as _dt
from pathlib import Path
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# TypedDict definitions (for static type checking / documentation only)
# ---------------------------------------------------------------------------


class FeatureMetaRequired(TypedDict):
    """Required fields -- always present in a valid meta.json."""

    feature_number: str
    slug: str
    feature_slug: str
    friendly_name: str
    mission: str
    target_branch: str
    created_at: str


class FeatureMetaOptional(TypedDict, total=False):
    """Optional fields -- present only after specific operations."""

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
    source_description: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: frozenset[str] = frozenset(FeatureMetaRequired.__annotations__)
HISTORY_CAP: int = 20


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Current UTC time in ISO 8601."""
    return _dt.datetime.now(_dt.UTC).isoformat()


def _atomic_write(path: Path, content: str) -> None:
    """Write *content* atomically.  File is either old or new, never partial.

    Uses :func:`os.fdopen` to wrap the raw file descriptor in a Python file
    object whose ``.write()`` method handles short writes internally, so the
    full payload is always flushed before the atomic rename.
    """
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".meta-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content.encode("utf-8"))
        # fd is now closed by the context manager
        os.replace(tmp_path, str(path))
    except BaseException:
        # fd may already be closed by the context manager; suppress errors
        with contextlib.suppress(OSError):
            os.close(fd)
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


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
        raise ValueError(
            f"Malformed JSON in {meta_path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected JSON object in {meta_path}, got {type(data).__name__}"
        )
    return data  # type: ignore[no-any-return]


def validate_meta(meta: dict[str, Any]) -> list[str]:
    """Validate *meta* content.  Returns a list of error messages (empty = valid).

    Only required fields are checked.  Unknown fields are silently
    preserved for forward compatibility.
    """
    errors: list[str] = []
    for field in sorted(REQUIRED_FIELDS):
        if field not in meta or not meta[field]:
            errors.append(f"Missing or empty required field: {field}")
    return errors


def write_meta(feature_dir: Path, meta: dict[str, Any]) -> None:
    """Write ``meta.json`` with validation, standard formatting, and atomic write.

    Standard format: sorted keys, 2-space indent, Unicode preserved,
    trailing newline.

    Raises :class:`ValueError` if validation fails.
    """
    errors = validate_meta(meta)
    if errors:
        raise ValueError(
            f"Invalid meta.json for {feature_dir.name}: {'; '.join(errors)}"
        )
    content = json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    meta_path = feature_dir / "meta.json"
    _atomic_write(meta_path, content)


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
