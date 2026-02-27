"""High-level tracker orchestration for CLI commands."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import httpx
from ruamel.yaml import YAML

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    clear_tracker_config,
    load_tracker_config,
    save_tracker_config,
)
from specify_cli.tracker.credentials import TrackerCredentialStore
from specify_cli.tracker.factory import SUPPORTED_PROVIDERS, build_connector, normalize_provider
from specify_cli.tracker.store import TrackerSqliteStore, default_tracker_db_path


class TrackerServiceError(RuntimeError):
    """Raised when tracker service operations fail."""


def parse_kv_pairs(entries: list[str]) -> dict[str, str]:
    """Parse repeated key=value CLI arguments into a dictionary."""
    parsed: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise TrackerServiceError(f"Invalid --credential value '{entry}'. Expected key=value.")
        key, value = entry.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise TrackerServiceError(f"Invalid --credential value '{entry}'. Expected key=value.")
        parsed[key] = value
    return parsed


class TrackerService:
    """Service wrapper around config, credentials, store and connector sync."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.credential_store = TrackerCredentialStore()

    @staticmethod
    def supported_providers() -> tuple[str, ...]:
        return SUPPORTED_PROVIDERS

    def bind(
        self,
        *,
        provider: str,
        workspace: str,
        doctrine_mode: str,
        doctrine_field_owners: dict[str, str],
        credentials: dict[str, str],
    ) -> TrackerProjectConfig:
        normalized_provider = normalize_provider(provider)
        config = TrackerProjectConfig(
            provider=normalized_provider,
            workspace=workspace,
            doctrine_mode=doctrine_mode,
            doctrine_field_owners=dict(doctrine_field_owners),
        )
        save_tracker_config(self.repo_root, config)

        if credentials:
            self.credential_store.set_provider(normalized_provider, credentials)

        return config

    def unbind(self) -> None:
        config = load_tracker_config(self.repo_root)
        if config.provider:
            self.credential_store.clear_provider(config.provider)
        clear_tracker_config(self.repo_root)

    def status(self) -> dict[str, Any]:
        config = load_tracker_config(self.repo_root)
        if not config.is_configured:
            return {
                "configured": False,
                "provider": None,
                "workspace": None,
                "db_path": None,
                "issue_count": 0,
                "mapping_count": 0,
            }

        credentials = self.credential_store.get_provider(config.provider or "")
        db_path = self._resolve_db_path(config, credentials)
        store = TrackerSqliteStore(db_path)

        issues = self._run_async(store.list_issues(system=config.provider))
        mappings = store.list_mappings()

        return {
            "configured": True,
            "provider": config.provider,
            "workspace": config.workspace,
            "doctrine_mode": config.doctrine_mode,
            "field_owners": config.doctrine_field_owners,
            "db_path": str(db_path),
            "issue_count": len(issues),
            "mapping_count": len(mappings),
            "credentials_present": bool(credentials),
        }

    def map_add(
        self,
        *,
        wp_id: str,
        external_id: str,
        external_key: str | None,
        external_url: str | None,
    ) -> None:
        try:
            from spec_kitty_tracker.models import ExternalRef
        except Exception as exc:  # pragma: no cover - dependency boundary
            raise TrackerServiceError(
                "spec-kitty-tracker is not installed. Install it to use tracker commands."
            ) from exc

        config, credentials, store = self._load_runtime()
        ref = ExternalRef(
            system=str(config.provider),
            workspace=str(config.workspace),
            id=external_id,
            key=external_key,
            url=external_url,
        )
        store.upsert_mapping(wp_id=wp_id, ref=ref)

    def map_list(self) -> list[dict[str, Any]]:
        _, _, store = self._load_runtime()
        return store.list_mappings()

    def sync_pull(self, *, limit: int = 100) -> dict[str, Any]:
        config, credentials, store = self._load_runtime()

        async def _run() -> dict[str, Any]:
            connector, engine = self._build_engine(config, credentials, store)
            checkpoint = store.get_checkpoint(checkpoint_key=f"{config.provider}:{config.workspace}")
            if checkpoint is not None:
                setattr(engine, "_checkpoint", checkpoint)

            result = await engine.pull(limit=limit)
            store.set_checkpoint(engine.checkpoint, checkpoint_key=f"{config.provider}:{config.workspace}")
            return self._sync_result(result, connector.name)

        return self._run_async(_run())

    def sync_push(self, *, limit: int = 100) -> dict[str, Any]:
        config, credentials, store = self._load_runtime()

        async def _run() -> dict[str, Any]:
            connector, engine = self._build_engine(config, credentials, store)
            result = await engine.push(limit=limit)
            return self._sync_result(result, connector.name)

        return self._run_async(_run())

    def sync_run(self, *, limit: int = 100) -> dict[str, Any]:
        config, credentials, store = self._load_runtime()

        async def _run() -> dict[str, Any]:
            connector, engine = self._build_engine(config, credentials, store)
            checkpoint = store.get_checkpoint(checkpoint_key=f"{config.provider}:{config.workspace}")
            if checkpoint is not None:
                setattr(engine, "_checkpoint", checkpoint)

            result = await engine.sync(limit=limit)
            store.set_checkpoint(engine.checkpoint, checkpoint_key=f"{config.provider}:{config.workspace}")
            return self._sync_result(result, connector.name)

        return self._run_async(_run())

    def sync_publish(
        self,
        *,
        server_url: str,
        auth_token: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> dict[str, Any]:
        config, credentials, store = self._load_runtime()

        provider = str(config.provider)
        workspace = str(config.workspace)
        issues = self._run_async(store.list_issues(system=provider))
        mappings = store.list_mappings()
        checkpoint = store.get_checkpoint(checkpoint_key=f"{provider}:{workspace}")

        project_identity = self._project_identity()

        payload = {
            "provider": provider,
            "workspace": workspace,
            "doctrine_mode": config.doctrine_mode,
            "doctrine_field_owners": dict(config.doctrine_field_owners),
            "project_uuid": project_identity.get("uuid"),
            "project_slug": project_identity.get("slug"),
            "issues": [self._issue_snapshot(issue) for issue in issues],
            "mappings": mappings,
            "checkpoint": {
                "cursor": checkpoint.cursor if checkpoint else None,
                "updated_since": checkpoint.updated_since.isoformat() if checkpoint and checkpoint.updated_since else None,
            },
        }

        endpoint = server_url.rstrip("/") + "/api/v1/connectors/trackers/snapshots/"
        idempotency_key = hashlib.sha256(
            f"{provider}|{workspace}|{len(issues)}|{len(mappings)}|{payload['checkpoint']['cursor']}".encode("utf-8")
        ).hexdigest()

        token = auth_token or str(credentials.get("access_token") or credentials.get("token") or "").strip()
        headers = {
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(endpoint, json=payload, headers=headers)

        content_type = response.headers.get("content-type", "")
        body: Any
        if "application/json" in content_type:
            body = response.json()
        else:
            body = response.text

        return {
            "endpoint": endpoint,
            "status_code": response.status_code,
            "ok": response.is_success,
            "body": body,
            "idempotency_key": idempotency_key,
        }

    def _load_runtime(self) -> tuple[TrackerProjectConfig, dict[str, Any], TrackerSqliteStore]:
        config = load_tracker_config(self.repo_root)
        if not config.is_configured:
            raise TrackerServiceError("Tracker is not configured. Run 'spec-kitty tracker bind' first.")

        if config.provider is None or config.workspace is None:
            raise TrackerServiceError("Tracker provider/workspace configuration is incomplete.")

        credentials = self.credential_store.get_provider(config.provider)
        db_path = self._resolve_db_path(config, credentials)
        store = TrackerSqliteStore(db_path)
        return config, credentials, store

    def _resolve_db_path(self, config: TrackerProjectConfig, credentials: dict[str, Any]) -> Path:
        server_url = str(credentials.get("server_url") or credentials.get("base_url") or "")
        username = str(credentials.get("username") or credentials.get("email") or "")
        team_slug = str(credentials.get("team_slug") or "")
        return default_tracker_db_path(
            provider=str(config.provider),
            workspace=str(config.workspace),
            server_url=server_url,
            username=username,
            team_slug=team_slug,
        )

    def _build_engine(self, config: TrackerProjectConfig, credentials: dict[str, Any], store: TrackerSqliteStore) -> Any:
        try:
            from spec_kitty_tracker import FieldOwner, OwnershipMode, OwnershipPolicy, SyncEngine
        except Exception as exc:  # pragma: no cover - dependency boundary
            raise TrackerServiceError(
                "spec-kitty-tracker is not installed. Install it to use tracker commands."
            ) from exc

        connector = build_connector(
            provider=str(config.provider),
            workspace=str(config.workspace),
            credentials=credentials,
        )

        mode_name = (config.doctrine_mode or "external_authoritative").strip().lower()
        if mode_name == OwnershipMode.EXTERNAL_AUTHORITATIVE.value:
            policy = OwnershipPolicy.external_authoritative()
        elif mode_name == OwnershipMode.SPEC_KITTY_AUTHORITATIVE.value:
            policy = OwnershipPolicy.local_authoritative()
        else:
            field_owners = {
                field: FieldOwner(owner)
                for field, owner in config.doctrine_field_owners.items()
                if owner in {item.value for item in FieldOwner}
            }
            policy = OwnershipPolicy.split(field_owners=field_owners, default_owner=FieldOwner.SHARED)

        engine = SyncEngine(connector=connector, store=store, policy=policy)
        return connector, engine

    @staticmethod
    def _issue_snapshot(issue: Any) -> dict[str, Any]:
        return {
            "ref": {
                "system": issue.ref.system,
                "workspace": issue.ref.workspace,
                "id": issue.ref.id,
                "key": issue.ref.key,
                "url": issue.ref.url,
            },
            "title": issue.title,
            "body": issue.body,
            "status": issue.status.value,
            "issue_type": issue.issue_type.value,
            "priority": issue.priority,
            "assignees": list(issue.assignees),
            "labels": list(issue.labels),
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
        }

    @staticmethod
    def _sync_result(result: Any, provider_name: str) -> dict[str, Any]:
        return {
            "provider": provider_name,
            "stats": {
                "pulled_created": result.stats.pulled_created,
                "pulled_updated": result.stats.pulled_updated,
                "pushed_created": result.stats.pushed_created,
                "pushed_updated": result.stats.pushed_updated,
                "skipped": result.stats.skipped,
            },
            "conflicts": [
                {
                    "field_name": conflict.field_name,
                    "strategy": conflict.strategy.value,
                    "manual_review_required": conflict.manual_review_required,
                }
                for conflict in result.conflicts
            ],
            "errors": list(result.errors),
        }

    def _project_identity(self) -> dict[str, str | None]:
        config_path = self.repo_root / ".kittify" / "config.yaml"
        if not config_path.exists():
            return {"uuid": None, "slug": None}

        yaml = YAML()
        try:
            with config_path.open("r", encoding="utf-8") as handle:
                payload = yaml.load(handle) or {}
        except Exception:
            return {"uuid": None, "slug": None}

        project = payload.get("project") if isinstance(payload, dict) else None
        if not isinstance(project, dict):
            return {"uuid": None, "slug": None}

        uuid = project.get("uuid")
        slug = project.get("slug")
        return {
            "uuid": str(uuid) if uuid is not None else None,
            "slug": str(slug) if slug is not None else None,
        }

    @staticmethod
    def _run_async(awaitable: Any) -> Any:
        import asyncio

        return asyncio.run(awaitable)
