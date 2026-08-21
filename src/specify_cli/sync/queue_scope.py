"""Scope-resolution primitives extracted from the retired-pipeline transport queue.

R3-T1 (M1 legacy-cleanup producer; m1-contract-drafts/R3.md §2.1a) found that
``sync/queue.py`` is not a clean transport-only module: alongside the
project-owned event outbox (``OfflineQueue`` and friends — genuinely legacy,
R2's physical-deletion scope), it also carries the scope-resolution
primitives that ``sync/target_authority.py`` imports **at module level,
unconditionally** — not lazily, not behind ``is_saas_sync_enabled()``.
``target_authority.py`` is in turn imported at module level, with no
rollout-flag gate, by ``cli/commands/_auth_login.py`` — the implementation
module every ``spec-kitty auth login`` invocation reaches. Deleting
``sync/queue.py`` wholesale (R2's own criterion: "sender/receiver/history/
body/external paths are physically absent") would therefore make
``import specify_cli.sync.target_authority`` raise
``ModuleNotFoundError: No module named 'specify_cli.sync.queue'`` and crash
every user's first ``spec-kitty auth login`` call after upgrade.

This module is the fix: a small, pure, retained home for the eight
scope-resolution names (plus the ``LegacyRowCounts`` dataclass and the
``LegacyQueueMigrationRequiredError`` exception they share) with **no
dependency on anything transport-specific** — no ``OfflineQueue``, no
journal writes, no SQLite. ``sync/target_authority.py``, ``sync/preflight.py``,
and ``cli/commands/agent/mission_setup_plan.py`` import from here.
``specify_cli.sync.queue`` keeps re-exporting the same objects (identity, not
copies) so the ~50 existing production/test call sites that still import
scope helpers from the transport module keep working unchanged during the
transition — until R2 lands and deletes the transport module outright, at
which point this re-export naturally goes with it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml

from specify_cli.paths import get_runtime_root


class LegacyQueueMigrationRequiredError(RuntimeError):
    """A retired path-backed queue operation was requested on a live path."""


@dataclass(frozen=True, slots=True)
class LegacyRowCounts:
    event_rows: int = 0
    body_upload_rows: int = 0
    failure_log_rows: int = 0
    per_table: dict[str, int] = field(default_factory=dict)

    @property
    def total_rows(self) -> int:
        return self.event_rows + self.body_upload_rows + self.failure_log_rows

    def __bool__(self) -> bool:
        return bool(self.per_table)

    def __len__(self) -> int:
        return len(self.per_table)

    def __iter__(self) -> Any:
        return iter(self.per_table)

    def __contains__(self, key: object) -> bool:
        return key in self.per_table

    def __getitem__(self, key: str) -> int:
        return self.per_table[key]

    def get(self, key: str, default: int = 0) -> int:
        return self.per_table.get(key, default)

    def items(self) -> Any:
        return self.per_table.items()

    def keys(self) -> Any:
        return self.per_table.keys()

    def values(self) -> Any:
        return self.per_table.values()

    def __hash__(self) -> int:
        return hash((self.event_rows, self.body_upload_rows, self.failure_log_rows))


def _spec_kitty_dir() -> Path:
    return Path(get_runtime_root().base)


def _credentials_path() -> Path:
    return _spec_kitty_dir() / "credentials"


def _auth_session_store_dir() -> Path:
    return _spec_kitty_dir() / "auth"


def _legacy_queue_db_path() -> Path:
    """Named WP10 migration input; never opened by this module."""
    return _spec_kitty_dir() / "queue.db"


def _scoped_queue_dir() -> Path:
    return _spec_kitty_dir() / "queues"


def _active_scope_path() -> Path:
    return _spec_kitty_dir() / "active_queue_scope"


def _normalise_scope_part(value: str) -> str:
    return value.strip().lower()


def build_queue_scope(server_url: str, username: str, team_slug: str) -> str:
    material = "\0".join(_normalise_scope_part(value) for value in (server_url, username, team_slug))
    return hashlib.sha256(material.encode()).hexdigest()  # noqa: TID251 - legacy path identity


def scope_db_path(scope: str) -> Path:
    return _scoped_queue_dir() / f"queue-{scope}.db"


def read_active_scope(path: Path | None = None) -> str | None:
    source = path or _active_scope_path()
    try:
        value = source.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def write_active_scope(scope: str, path: Path | None = None) -> None:
    destination = path or _active_scope_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"{scope.strip()}\n", encoding="utf-8")


def _read_json(path: Path) -> Mapping[str, Any] | None:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return value if isinstance(value, Mapping) else None


def _piped_scope_from_toml_credentials(path: Path) -> str | None:
    """Build the canonical ``server|user|team`` scope from a TOML credentials file.

    This is an **auth/identity signal**, not a physical-store selector: the
    returned string is split back into ``(user, team)`` by
    ``preflight._read_scope_identity_local_only`` (which expects the
    ``server|user|team`` order) and is used by the FR-011 gate purely as a
    truthiness test. It never derives a queue DB path — the authoritative store
    is selected by ProjectSyncStore via ``_derive_queue_scope`` (FR-009 / C-003).

    Defensive by contract: a missing/corrupt/incomplete file yields ``None``
    rather than raising, mirroring the ``_read_json`` posture above.
    """
    try:
        data = toml.load(path)
    except (toml.TomlDecodeError, OSError, TypeError):
        return None
    if not isinstance(data, Mapping):
        return None
    user_data = data.get("user")
    server_data = data.get("server")
    if not isinstance(user_data, Mapping) or not isinstance(server_data, Mapping):
        return None
    username = user_data.get("username")
    server_url = server_data.get("url")
    if not isinstance(username, str) or not username.strip():
        return None
    if not isinstance(server_url, str) or not server_url.strip():
        return None
    team_slug = user_data.get("team_slug")
    team = team_slug if isinstance(team_slug, str) and team_slug.strip() else "no-team"
    return f"{server_url}|{username}|{team}"


def read_queue_scope_from_credentials(credentials_path: Path | None = None) -> str | None:
    """Return a queue-scope **auth signal** from the on-disk credentials, or ``None``.

    Two supported forms, JSON-explicit winning where present (preserves #3293):

    1. JSON with an explicit ``queue_scope`` string — returned verbatim.
    2. The supported TOML credential form (``[user]`` / ``[server]`` tables) —
       parsed back into the canonical ``server|user|team`` piped scope that
       ``preflight._read_scope_identity_local_only`` splits on (preflight.py:479).

    Restoring form (2) fixes the #3425 credential regression (FR-004): a
    genuinely-authenticated host again yields a truthy scope so the FR-011 auth
    gate stops refusing it. This function stays a pure, side-effect-free read: no
    migration, no SaaS round-trip, no path resolution. The value is an auth signal
    only — it must never steer physical-store selection (FR-009 / C-003).
    """
    path = credentials_path or _credentials_path()
    data = _read_json(path)
    if data is not None:
        explicit = data.get("queue_scope")
        if isinstance(explicit, str) and explicit.strip():
            return str(explicit)
    return _piped_scope_from_toml_credentials(path)


def read_queue_scope_from_session(*, allow_rehydrate: bool = True) -> str | None:
    del allow_rehydrate
    active = read_active_scope()
    if active:
        return active
    session = _read_json(_auth_session_store_dir() / "session.json")
    if session is None:
        return None
    explicit = session.get("queue_scope")
    return str(explicit) if isinstance(explicit, str) and explicit.strip() else None


def default_queue_db_path(*_args: object, **_kwargs: object) -> Path:
    raise LegacyQueueMigrationRequiredError(
        "live payload queues are selected by ProjectSyncStore; legacy paths are WP10 migration inputs"
    )


def detect_legacy_rows_for_scope(scope: str) -> LegacyRowCounts:
    del scope
    raise LegacyQueueMigrationRequiredError("inspect legacy rows through the named WP10 read-only migration adapter")


__all__ = [
    "LegacyQueueMigrationRequiredError",
    "LegacyRowCounts",
    "_legacy_queue_db_path",
    "build_queue_scope",
    "default_queue_db_path",
    "detect_legacy_rows_for_scope",
    "read_active_scope",
    "read_queue_scope_from_credentials",
    "read_queue_scope_from_session",
    "scope_db_path",
    "write_active_scope",
]
