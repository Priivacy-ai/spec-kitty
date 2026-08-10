"""Atomic daemon discovery hints that can narrow work but never grant it."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final

from specify_cli.core.atomic import atomic_write
from specify_cli.paths import get_runtime_root

from .project_identity import CanonicalProjectUUID


class DenyHintAction(StrEnum):
    """Only representable hint actions; there is deliberately no grant value."""

    DENY = "deny"
    REVOKE = "revoke"


class DenyHintStatus(StrEnum):
    """Discovery outcome; only VALID_DENY permits skipping store authority."""

    VALID_DENY = "valid_deny"
    AUTHORITY_REQUIRED = "authority_required"
    STALE_DENY = "stale_deny"


@dataclass(frozen=True, slots=True)
class DaemonDenyHint:
    """Integrity-checked, payload-free denial cached for one project UUID."""

    action: DenyHintAction
    authority_generation: int
    expires_at: datetime
    reason_category: str
    layout_version: int
    checksum: str


@dataclass(frozen=True, slots=True)
class DenyHintProbe:
    """Typed hint read that explicitly tells discovery whether to open authority."""

    status: DenyHintStatus
    hint: DaemonDenyHint | None
    diagnostic: str

    @property
    def requires_authority(self) -> bool:
        return self.status is not DenyHintStatus.VALID_DENY


_DEFAULT_TTL: Final[timedelta] = timedelta(minutes=5)
_LAYOUT_VERSION: Final[int] = 1
_REASON_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "absent",
        "explicit_opt_out",
        "migrated_refusal",
        "remote_revocation_pending",
        "store_incompatible",
        "store_unreadable",
    }
)


def deny_hint_directory() -> Path:
    """Resolve the physical hint directory without creating it."""
    return Path(get_runtime_root().base) / "projects" / ".deny-hints"


def deny_hint_path(project_uuid: CanonicalProjectUUID | str) -> Path:
    """Resolve one canonical hint filename without filesystem side effects."""
    canonical = CanonicalProjectUUID.parse(project_uuid)
    return deny_hint_directory() / f"{canonical.storage_token}.json"


def _canonical_content(fields: dict[str, object]) -> bytes:
    return json.dumps(
        fields,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def _checksum(fields: dict[str, object]) -> str:
    # WP03 requires a SHA-256 integrity checksum for the atomic deny-hint file.
    return hashlib.sha256(_canonical_content(fields)).hexdigest()  # noqa: TID251


def publish_deny_hint(
    project_uuid: CanonicalProjectUUID | str,
    *,
    action: DenyHintAction,
    authority_generation: int,
    reason_category: str,
    now: datetime | None = None,
    ttl: timedelta = _DEFAULT_TTL,
) -> DaemonDenyHint:
    """Atomically publish a bounded denial after authority has committed."""
    if not isinstance(action, DenyHintAction):
        raise TypeError("deny hints can represent only DenyHintAction values")
    if not isinstance(authority_generation, int) or isinstance(authority_generation, bool) or authority_generation < 1:
        raise ValueError("deny-hint authority generation must be positive")
    if reason_category not in _REASON_CATEGORIES:
        raise ValueError("deny-hint reason must be a payload-free category")
    if ttl <= timedelta(0):
        raise ValueError("deny-hint expiration must be in the future")
    observed_at = now or datetime.now(UTC)
    if observed_at.tzinfo is None:
        raise ValueError("deny-hint clock must be timezone-aware")
    expires_at = observed_at + ttl
    fields: dict[str, object] = {
        "action": action.value,
        "authority_generation": authority_generation,
        "expires_at": expires_at.isoformat(),
        "layout_version": _LAYOUT_VERSION,
        "reason_category": reason_category,
    }
    checksum = _checksum(fields)
    document = {**fields, "checksum": checksum}
    atomic_write(
        deny_hint_path(project_uuid),
        _canonical_content(document) + b"\n",
        mkdir=True,
    )
    return DaemonDenyHint(
        action=action,
        authority_generation=authority_generation,
        expires_at=expires_at,
        reason_category=reason_category,
        layout_version=_LAYOUT_VERSION,
        checksum=checksum,
    )


def remove_deny_hint(project_uuid: CanonicalProjectUUID | str) -> None:
    """Remove denial only after explicit opt-in has committed."""
    path = deny_hint_path(project_uuid)
    try:
        path.unlink()
    except FileNotFoundError:
        return


def read_deny_hint(
    project_uuid: CanonicalProjectUUID | str,
    *,
    expected_generation: int,
    now: datetime | None = None,
) -> DenyHintProbe:
    """Read a hint; every non-current state directs discovery to authority."""
    path = deny_hint_path(project_uuid)
    try:
        raw = path.read_text(encoding="utf-8")
        document = json.loads(raw)
    except FileNotFoundError:
        return DenyHintProbe(
            DenyHintStatus.AUTHORITY_REQUIRED,
            None,
            "deny hint is missing; read project authority",
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        return DenyHintProbe(
            DenyHintStatus.AUTHORITY_REQUIRED,
            None,
            "deny hint is unreadable or malformed; read project authority",
        )
    if not isinstance(document, dict):
        return DenyHintProbe(
            DenyHintStatus.AUTHORITY_REQUIRED,
            None,
            "deny hint has an incompatible shape; read project authority",
        )
    expected_fields = {
        "action",
        "authority_generation",
        "expires_at",
        "layout_version",
        "reason_category",
        "checksum",
    }
    if set(document) != expected_fields:
        return DenyHintProbe(
            DenyHintStatus.AUTHORITY_REQUIRED,
            None,
            "deny hint contains unsupported fields; read project authority",
        )
    raw_generation = document["authority_generation"]
    raw_layout_version = document["layout_version"]
    if (
        not isinstance(raw_generation, int)
        or isinstance(raw_generation, bool)
        or raw_generation < 1
        or not isinstance(raw_layout_version, int)
        or isinstance(raw_layout_version, bool)
    ):
        return DenyHintProbe(
            DenyHintStatus.AUTHORITY_REQUIRED,
            None,
            "deny hint values are incompatible; read project authority",
        )
    try:
        action = DenyHintAction(document["action"])
        authority_generation = raw_generation
        expires_at = datetime.fromisoformat(str(document["expires_at"]))
        layout_version = raw_layout_version
        reason_category = str(document["reason_category"])
        checksum = str(document["checksum"])
    except (TypeError, ValueError):
        return DenyHintProbe(
            DenyHintStatus.AUTHORITY_REQUIRED,
            None,
            "deny hint values are incompatible; read project authority",
        )
    unsigned = {key: document[key] for key in expected_fields - {"checksum"}}
    if checksum != _checksum(unsigned):
        return DenyHintProbe(
            DenyHintStatus.AUTHORITY_REQUIRED,
            None,
            "deny hint integrity check failed; read project authority",
        )
    hint = DaemonDenyHint(
        action=action,
        authority_generation=authority_generation,
        expires_at=expires_at,
        reason_category=reason_category,
        layout_version=layout_version,
        checksum=checksum,
    )
    observed_at = now or datetime.now(UTC)
    if expires_at.tzinfo is None or observed_at.tzinfo is None:
        return DenyHintProbe(
            DenyHintStatus.AUTHORITY_REQUIRED,
            hint,
            "deny hint timestamp is incompatible; read project authority",
        )
    if expires_at <= observed_at:
        return DenyHintProbe(
            DenyHintStatus.STALE_DENY,
            hint,
            "deny hint expired and may delay liveness; read project authority",
        )
    if authority_generation != expected_generation:
        return DenyHintProbe(
            DenyHintStatus.STALE_DENY,
            hint,
            "deny hint generation is stale; read project authority",
        )
    if layout_version != _LAYOUT_VERSION or reason_category not in _REASON_CATEGORIES:
        return DenyHintProbe(
            DenyHintStatus.AUTHORITY_REQUIRED,
            hint,
            "deny hint schema is incompatible; read project authority",
        )
    return DenyHintProbe(
        DenyHintStatus.VALID_DENY,
        hint,
        "current denial permits discovery to skip project payload state",
    )


def enumerate_deny_hint_project_uuids() -> tuple[CanonicalProjectUUID, ...]:
    """Enumerate hint filenames without creating a project store or decision."""
    directory = deny_hint_directory()
    if not directory.is_dir():
        return ()
    project_uuids: list[CanonicalProjectUUID] = []
    for path in directory.iterdir():
        if not path.is_file() or path.suffix != ".json":
            continue
        try:
            canonical = CanonicalProjectUUID.parse(path.stem)
        except (TypeError, ValueError):
            continue
        if path.name == f"{canonical.storage_token}.json":
            project_uuids.append(canonical)
    return tuple(sorted(project_uuids))


__all__ = [
    "DaemonDenyHint",
    "DenyHintAction",
    "DenyHintProbe",
    "DenyHintStatus",
    "deny_hint_directory",
    "deny_hint_path",
    "enumerate_deny_hint_project_uuids",
    "publish_deny_hint",
    "read_deny_hint",
    "remove_deny_hint",
]
