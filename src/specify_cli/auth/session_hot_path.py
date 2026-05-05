"""Token-free local session hot path for short-lived CLI processes.

The encrypted file store remains the durable root of trust. This module writes
only a bounded, redacted auth summary tied to the current encrypted session
file's metadata. Missing, stale, malformed, or mismatched summaries are normal
cache misses and callers must fall back to encrypted storage.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .session import StoredSession

_SCHEMA_VERSION = 1
_HANDOFF_NAME = "session.hot-path.json"
_DISABLE_ENV = "SPEC_KITTY_DISABLE_SESSION_HOT_PATH"
_MAX_AGE_SECONDS = 30.0


@dataclass(frozen=True)
class SessionHotPathSummary:
    """Token-free session presence summary derived from encrypted storage."""

    refresh_token_expires_at: datetime | None
    not_after_monotonic: float

    def is_fresh(self) -> bool:
        return time.monotonic() <= self.not_after_monotonic

    def is_authenticated(self) -> bool:
        if not self.is_fresh():
            return False
        if self.refresh_token_expires_at is None:
            return True
        return self.refresh_token_expires_at > datetime.now(UTC)


def hot_path_disabled() -> bool:
    """Return True when the session hot path should be bypassed."""
    return os.environ.get(_DISABLE_ENV) == "1"


def handoff_path_for_store(store_dir: Path) -> Path:
    """Return the redacted handoff file path for ``store_dir``."""
    return Path(store_dir) / _HANDOFF_NAME


def load_session_hot_path(store_dir: Path) -> SessionHotPathSummary | None:
    """Return a fresh redacted auth summary, or ``None`` on any cache miss."""
    if hot_path_disabled():
        return None

    store_dir = Path(store_dir)
    cred_file = store_dir / "session.json"
    if not cred_file.exists():
        return None

    handoff_file = handoff_path_for_store(store_dir)
    try:
        raw = handoff_file.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != _SCHEMA_VERSION:
        return None

    try:
        generated_at = float(payload["generated_at"])
        max_age = float(payload["max_age_seconds"])
        fingerprint = dict(payload["durable_fingerprint"])
    except (KeyError, TypeError, ValueError):
        return None
    now = time.time()
    if now < generated_at or now - generated_at > min(max_age, _MAX_AGE_SECONDS):
        return None
    try:
        durable_fingerprint = _durable_fingerprint(cred_file)
    except OSError:
        return None
    if fingerprint != durable_fingerprint:
        return None

    refresh_raw = payload.get("refresh_token_expires_at")
    try:
        refresh_expires_at = (
            datetime.fromisoformat(refresh_raw) if refresh_raw else None
        )
    except (TypeError, ValueError):
        return None
    if refresh_expires_at is not None:
        if refresh_expires_at.tzinfo is None:
            return None
        refresh_expires_at = refresh_expires_at.astimezone(UTC)
    return SessionHotPathSummary(
        refresh_token_expires_at=refresh_expires_at,
        not_after_monotonic=time.monotonic()
        + min(_MAX_AGE_SECONDS, max_age - (now - generated_at)),
    )


def publish_session_hot_path(store_dir: Path, session: StoredSession) -> None:
    """Publish a redacted handoff derived from ``session`` and encrypted state."""
    if hot_path_disabled():
        return

    store_dir = Path(store_dir)
    cred_file = store_dir / "session.json"
    if not cred_file.exists():
        return
    tmp: Path | None = None
    try:
        now = time.time()
        payload: dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "generated_at": now,
            "max_age_seconds": _MAX_AGE_SECONDS,
            "durable_fingerprint": _durable_fingerprint(cred_file),
            "refresh_token_expires_at": (
                session.refresh_token_expires_at.isoformat()
                if session.refresh_token_expires_at is not None
                else None
            ),
        }
        handoff_file = handoff_path_for_store(store_dir)
        tmp = handoff_file.with_suffix(handoff_file.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        with suppress(OSError):
            os.chmod(tmp, 0o600)
        tmp.replace(handoff_file)
    except OSError:
        if tmp is not None:
            with suppress(OSError):
                tmp.unlink()


def invalidate_session_hot_path(store_dir: Path) -> None:
    """Remove the redacted handoff if it exists."""
    handoff_file = handoff_path_for_store(Path(store_dir))
    try:
        handoff_file.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def _durable_fingerprint(cred_file: Path) -> dict[str, int]:
    stat_result = cred_file.stat()
    return {
        "mtime_ns": stat_result.st_mtime_ns,
        "size": stat_result.st_size,
        "inode": getattr(stat_result, "st_ino", 0),
    }
