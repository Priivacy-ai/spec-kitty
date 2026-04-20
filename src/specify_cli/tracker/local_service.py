"""Local (beads/fp) tracker service — direct-connector execution path.

This is a **mechanical extraction** from the original ``TrackerService`` in
``service.py``.  Every public method preserves its original signature so that
the facade layer (WP05) can dispatch to either the local service or the
SaaS service transparently.

No SaaS imports live here — only local connector infrastructure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    clear_tracker_config,
    load_tracker_config,
    save_tracker_config,
)
from specify_cli.tracker.credentials import TrackerCredentialStore
from specify_cli.tracker.factory import build_connector, normalize_provider
from specify_cli.tracker.store import TrackerSqliteStore, default_tracker_db_path


class LocalTrackerServiceError(RuntimeError):
    """Raised when a local tracker operation fails."""


class LocalTrackerService:
    """Service wrapper for beads/fp direct-connector sync operations.

    Mirrors the public method surface of the original ``TrackerService`` so
    that the facade in WP05 can delegate without transformation.
    """

    def __init__(self, repo_root: Path, config: TrackerProjectConfig) -> None:
        self._repo_root = repo_root
        self._config = config
        self.credential_store = TrackerCredentialStore()

    # ------------------------------------------------------------------
    # bind / unbind
    # ------------------------------------------------------------------

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
        save_tracker_config(self._repo_root, config)

        if credentials:
            self.credential_store.set_provider(normalized_provider, credentials)

        return config

    def unbind(self) -> None:
        config = load_tracker_config(self._repo_root)
        if config.provider:
            self.credential_store.clear_provider(config.provider)
        clear_tracker_config(self._repo_root)

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        config = load_tracker_config(self._repo_root)
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

    # ------------------------------------------------------------------
    # sync operations
    # ------------------------------------------------------------------

    def sync_pull(self, *, limit: int = 100) -> dict[str, Any]:
        config, credentials, store = self._load_runtime()

        async def _run() -> dict[str, Any]:
            connector, engine = self._build_engine(config, credentials, store)
            checkpoint = store.get_checkpoint(checkpoint_key=f"{config.provider}:{config.workspace}")
            if checkpoint is not None:
                engine._checkpoint = checkpoint

            result = await engine.pull(limit=limit)
            store.set_checkpoint(engine.checkpoint, checkpoint_key=f"{config.provider}:{config.workspace}")
            return self._sync_result(result, connector.name)

        return cast(dict[str, Any], self._run_async(_run()))

    def sync_push(self, *, limit: int = 100) -> dict[str, Any]:
        config, credentials, store = self._load_runtime()

        async def _run() -> dict[str, Any]:
            connector, engine = self._build_engine(config, credentials, store)
            result = await engine.push(limit=limit)
            return self._sync_result(result, connector.name)

        return cast(dict[str, Any], self._run_async(_run()))

    def sync_run(self, *, limit: int = 100) -> dict[str, Any]:
        config, credentials, store = self._load_runtime()

        async def _run() -> dict[str, Any]:
            connector, engine = self._build_engine(config, credentials, store)
            checkpoint = store.get_checkpoint(checkpoint_key=f"{config.provider}:{config.workspace}")
            if checkpoint is not None:
                engine._checkpoint = checkpoint

            result = await engine.sync(limit=limit)
            store.set_checkpoint(engine.checkpoint, checkpoint_key=f"{config.provider}:{config.workspace}")
            return self._sync_result(result, connector.name)

        return cast(dict[str, Any], self._run_async(_run()))

    # ------------------------------------------------------------------
    # mapping operations
    # ------------------------------------------------------------------

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
            raise LocalTrackerServiceError(
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

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _load_runtime(self) -> tuple[TrackerProjectConfig, dict[str, Any], TrackerSqliteStore]:
        config = load_tracker_config(self._repo_root)
        if not config.is_configured:
            raise LocalTrackerServiceError("Tracker is not configured. Run 'spec-kitty tracker bind' first.")

        if config.provider is None or config.workspace is None:
            raise LocalTrackerServiceError("Tracker provider/workspace configuration is incomplete.")

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
            raise LocalTrackerServiceError(
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

    @staticmethod
    def _run_async(awaitable: Any) -> Any:
        import asyncio

        return asyncio.run(awaitable)
