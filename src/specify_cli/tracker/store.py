"""CLI-owned SQLite cache/checkpoint storage for tracker sync."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


def _spec_kitty_dir() -> Path:
    return Path.home() / ".spec-kitty"


def _trackers_dir() -> Path:
    return _spec_kitty_dir() / "trackers"


_TRACKER_MODELS: dict[str, Any] | None | bool = False


def _get_tracker_models() -> dict[str, Any] | None:
    global _TRACKER_MODELS
    if _TRACKER_MODELS is False:
        try:
            from spec_kitty_tracker.models import (
                CanonicalIssue,
                CanonicalIssueType,
                CanonicalLink,
                CanonicalStatus,
                ExternalRef,
                LinkType,
                SyncCheckpoint,
            )

            _TRACKER_MODELS = {
                "CanonicalIssue": CanonicalIssue,
                "CanonicalIssueType": CanonicalIssueType,
                "CanonicalLink": CanonicalLink,
                "CanonicalStatus": CanonicalStatus,
                "ExternalRef": ExternalRef,
                "LinkType": LinkType,
                "SyncCheckpoint": SyncCheckpoint,
            }
        except Exception:
            _TRACKER_MODELS = None

    return _TRACKER_MODELS if isinstance(_TRACKER_MODELS, dict) else None


def _read_attr(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _enum_value(value: Any, default: str) -> str:
    if value is None:
        return default
    enum_val = getattr(value, "value", None)
    if enum_val is not None:
        return str(enum_val)
    return str(value)


def _ref_identity(ref: Any) -> str:
    identity = _read_attr(ref, "identity")
    if isinstance(identity, str) and identity.strip():
        return identity

    system = str(_read_attr(ref, "system", "")).strip()
    workspace = str(_read_attr(ref, "workspace", "")).strip()
    issue_id = str(_read_attr(ref, "id", "")).strip()
    if not (system and workspace and issue_id):
        raise ValueError("External reference must include system, workspace, and id")
    return f"{system}:{workspace}:{issue_id}"


def build_tracker_scope(
    *,
    provider: str,
    workspace: str,
    server_url: str | None,
    username: str | None,
    team_slug: str | None,
) -> str:
    server = (server_url or "local").strip().lower()
    user = (username or "anonymous").strip().lower()
    team = (team_slug or "no-team").strip().lower()
    identity = f"{provider.strip().lower()}|{workspace.strip().lower()}|{server}|{user}|{team}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def default_tracker_db_path(
    *,
    provider: str,
    workspace: str,
    server_url: str | None = None,
    username: str | None = None,
    team_slug: str | None = None,
) -> Path:
    scope = build_tracker_scope(
        provider=provider,
        workspace=workspace,
        server_url=server_url,
        username=username,
        team_slug=team_slug,
    )
    return _trackers_dir() / f"{scope}.db"


def _serialize_ref(ref: Any) -> dict[str, Any]:
    if isinstance(ref, dict):
        payload = ref
    else:
        payload = {
            "system": _read_attr(ref, "system"),
            "workspace": _read_attr(ref, "workspace"),
            "id": _read_attr(ref, "id"),
            "key": _read_attr(ref, "key"),
            "url": _read_attr(ref, "url"),
        }

    return {
        "system": str(payload.get("system") or ""),
        "workspace": str(payload.get("workspace") or ""),
        "id": str(payload.get("id") or ""),
        "key": str(payload["key"]) if payload.get("key") is not None else None,
        "url": str(payload["url"]) if payload.get("url") is not None else None,
    }


def _deserialize_ref(payload: dict[str, Any]) -> Any:
    models = _get_tracker_models()
    if models is None:
        return {
            "system": str(payload.get("system") or ""),
            "workspace": str(payload.get("workspace") or ""),
            "id": str(payload.get("id") or ""),
            "key": str(payload["key"]) if payload.get("key") is not None else None,
            "url": str(payload["url"]) if payload.get("url") is not None else None,
            "identity": f"{payload.get('system','')}:{payload.get('workspace','')}:{payload.get('id','')}",
        }

    ExternalRef = models["ExternalRef"]
    return ExternalRef(
        system=str(payload.get("system") or ""),
        workspace=str(payload.get("workspace") or ""),
        id=str(payload.get("id") or ""),
        key=str(payload["key"]) if payload.get("key") is not None else None,
        url=str(payload["url"]) if payload.get("url") is not None else None,
    )


def _serialize_issue(issue: Any) -> dict[str, Any]:
    ref = _serialize_ref(_read_attr(issue, "ref", {}))

    links: list[dict[str, Any]] = []
    for link in list(_read_attr(issue, "links", []) or []):
        links.append(
            {
                "type": _enum_value(_read_attr(link, "type"), "relates_to"),
                "target": _serialize_ref(_read_attr(link, "target", {})),
            }
        )

    parent_raw = _read_attr(issue, "parent")
    parent = _serialize_ref(parent_raw) if parent_raw is not None else None

    created_at = _read_attr(issue, "created_at")
    updated_at = _read_attr(issue, "updated_at")

    return {
        "ref": ref,
        "title": str(_read_attr(issue, "title", "Untitled")),
        "body": _read_attr(issue, "body"),
        "status": _enum_value(_read_attr(issue, "status"), "todo"),
        "issue_type": _enum_value(_read_attr(issue, "issue_type"), "task"),
        "priority": _read_attr(issue, "priority"),
        "assignees": [str(item) for item in list(_read_attr(issue, "assignees", []) or [])],
        "labels": [str(item) for item in list(_read_attr(issue, "labels", []) or [])],
        "parent": parent,
        "links": links,
        "custom_fields": dict(_read_attr(issue, "custom_fields", {}) or {}),
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else None,
        "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
        "raw": _read_attr(issue, "raw"),
    }


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _deserialize_issue(payload: dict[str, Any]) -> Any:
    models = _get_tracker_models()
    if models is None:
        return payload

    CanonicalIssue = models["CanonicalIssue"]
    CanonicalIssueType = models["CanonicalIssueType"]
    CanonicalLink = models["CanonicalLink"]
    CanonicalStatus = models["CanonicalStatus"]
    LinkType = models["LinkType"]

    def safe_enum(enum_cls: Any, value: str, fallback: Any) -> Any:
        try:
            return enum_cls(value)
        except Exception:
            return fallback

    links_payload = payload.get("links")
    links: list[Any] = []
    if isinstance(links_payload, list):
        for entry in links_payload:
            if not isinstance(entry, dict):
                continue
            target_payload = entry.get("target")
            if not isinstance(target_payload, dict):
                continue
            links.append(
                CanonicalLink(
                    type=safe_enum(LinkType, str(entry.get("type", LinkType.RELATES_TO.value)), LinkType.RELATES_TO),
                    target=_deserialize_ref(target_payload),
                )
            )

    parent_payload = payload.get("parent")
    parent = _deserialize_ref(parent_payload) if isinstance(parent_payload, dict) else None

    custom_fields = payload.get("custom_fields")
    raw = payload.get("raw")

    priority_raw = payload.get("priority")
    priority = int(priority_raw) if isinstance(priority_raw, int) or str(priority_raw).isdigit() else None

    return CanonicalIssue(
        ref=_deserialize_ref(payload["ref"]),
        title=str(payload.get("title") or "Untitled"),
        body=str(payload["body"]) if payload.get("body") is not None else None,
        status=safe_enum(CanonicalStatus, str(payload.get("status", CanonicalStatus.TODO.value)), CanonicalStatus.TODO),
        issue_type=safe_enum(
            CanonicalIssueType,
            str(payload.get("issue_type", CanonicalIssueType.TASK.value)),
            CanonicalIssueType.TASK,
        ),
        priority=priority,
        assignees=[str(item) for item in payload.get("assignees", [])],
        labels=[str(item) for item in payload.get("labels", [])],
        parent=parent,
        links=links,
        custom_fields=dict(custom_fields) if isinstance(custom_fields, dict) else {},
        created_at=_parse_datetime(payload.get("created_at")),
        updated_at=_parse_datetime(payload.get("updated_at")),
        raw=dict(raw) if isinstance(raw, dict) else None,
    )


class TrackerSqliteStore:
    """SQLite-backed issue cache/checkpoint/mapping store for CLI."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tracker_issues (
                    identity TEXT PRIMARY KEY,
                    system TEXT NOT NULL,
                    workspace TEXT NOT NULL,
                    issue_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tracker_checkpoints (
                    checkpoint_key TEXT PRIMARY KEY,
                    cursor TEXT,
                    updated_since TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tracker_mappings (
                    wp_id TEXT NOT NULL,
                    system TEXT NOT NULL,
                    workspace TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    external_key TEXT,
                    external_url TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (wp_id, system),
                    UNIQUE (system, workspace, external_id)
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    async def list_issues(self, *, system: str | None = None) -> Sequence[Any]:
        conn = self._connect()
        try:
            if system is None:
                cursor = conn.execute("SELECT payload FROM tracker_issues ORDER BY identity ASC")
            else:
                cursor = conn.execute(
                    "SELECT payload FROM tracker_issues WHERE system = ? ORDER BY identity ASC",
                    (system,),
                )
            rows = cursor.fetchall()
        finally:
            conn.close()

        results: list[Any] = []
        for row in rows:
            payload = json.loads(str(row["payload"]))
            results.append(_deserialize_issue(payload))
        return results

    async def get_issue(self, ref: Any) -> Any | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT payload FROM tracker_issues WHERE identity = ?",
                (_ref_identity(ref),),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None
        payload = json.loads(str(row["payload"]))
        return _deserialize_issue(payload)

    async def upsert_issue(self, issue: Any) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(_serialize_issue(issue), separators=(",", ":"))
        ref = _read_attr(issue, "ref", {})

        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO tracker_issues(identity, system, workspace, issue_id, payload, updated_at)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(identity) DO UPDATE SET
                    system = excluded.system,
                    workspace = excluded.workspace,
                    issue_id = excluded.issue_id,
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    _ref_identity(ref),
                    str(_read_attr(ref, "system", "")),
                    str(_read_attr(ref, "workspace", "")),
                    str(_read_attr(ref, "id", "")),
                    payload,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    async def delete_issue(self, ref: Any) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM tracker_issues WHERE identity = ?", (_ref_identity(ref),))
            conn.commit()
        finally:
            conn.close()

    def get_checkpoint(self, checkpoint_key: str = "default") -> Any | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT cursor, updated_since FROM tracker_checkpoints WHERE checkpoint_key = ?",
                (checkpoint_key,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        cursor = str(row["cursor"]) if row["cursor"] is not None else None
        updated_since = _parse_datetime(row["updated_since"])

        models = _get_tracker_models()
        if models is None:
            return {
                "cursor": cursor,
                "updated_since": updated_since,
            }

        SyncCheckpoint = models["SyncCheckpoint"]
        return SyncCheckpoint(
            cursor=cursor,
            updated_since=updated_since,
        )

    def set_checkpoint(self, checkpoint: Any, checkpoint_key: str = "default") -> None:
        cursor = _read_attr(checkpoint, "cursor")
        updated_since = _read_attr(checkpoint, "updated_since")

        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO tracker_checkpoints(checkpoint_key, cursor, updated_since)
                VALUES(?, ?, ?)
                ON CONFLICT(checkpoint_key) DO UPDATE SET
                    cursor = excluded.cursor,
                    updated_since = excluded.updated_since
                """,
                (
                    checkpoint_key,
                    str(cursor) if cursor is not None else None,
                    updated_since.isoformat() if isinstance(updated_since, datetime) else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def upsert_mapping(self, *, wp_id: str, ref: Any) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO tracker_mappings(
                    wp_id, system, workspace, external_id, external_key, external_url, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(wp_id, system) DO UPDATE SET
                    workspace = excluded.workspace,
                    external_id = excluded.external_id,
                    external_key = excluded.external_key,
                    external_url = excluded.external_url,
                    updated_at = excluded.updated_at
                """,
                (
                    wp_id,
                    str(_read_attr(ref, "system", "")),
                    str(_read_attr(ref, "workspace", "")),
                    str(_read_attr(ref, "id", "")),
                    str(_read_attr(ref, "key")) if _read_attr(ref, "key") is not None else None,
                    str(_read_attr(ref, "url")) if _read_attr(ref, "url") is not None else None,
                    now,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_mappings(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT wp_id, system, workspace, external_id, external_key, external_url, created_at, updated_at
                FROM tracker_mappings
                ORDER BY wp_id ASC, system ASC
                """
            ).fetchall()
        finally:
            conn.close()

        return [
            {
                "wp_id": str(row["wp_id"]),
                "system": str(row["system"]),
                "workspace": str(row["workspace"]),
                "external_id": str(row["external_id"]),
                "external_key": str(row["external_key"]) if row["external_key"] is not None else None,
                "external_url": str(row["external_url"]) if row["external_url"] is not None else None,
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
            }
            for row in rows
        ]
