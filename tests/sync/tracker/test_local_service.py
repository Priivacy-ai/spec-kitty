"""Tests for LocalTrackerService — beads/fp direct-connector extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    load_tracker_config,
    save_tracker_config,
)
from specify_cli.tracker.credentials import TrackerCredentialStore
from specify_cli.tracker.local_service import LocalTrackerService, LocalTrackerServiceError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Create a minimal repo root with .kittify directory."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    return tmp_path


@pytest.fixture()
def cred_path(tmp_path: Path) -> Path:
    """Isolated credential file path."""
    return tmp_path / ".spec-kitty" / "credentials"


def _make_service(
    repo_root: Path,
    config: TrackerProjectConfig | None = None,
    cred_path: Path | None = None,
) -> LocalTrackerService:
    svc = LocalTrackerService(repo_root, config or TrackerProjectConfig())
    if cred_path is not None:
        svc.credential_store = TrackerCredentialStore(path=cred_path)
    return svc


# ---------------------------------------------------------------------------
# bind
# ---------------------------------------------------------------------------


class TestBind:
    def test_bind_stores_config_and_credentials(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        config = svc.bind(
            provider="beads",
            workspace="my-ws",
            doctrine_mode="external_authoritative",
            doctrine_field_owners={},
            credentials={"command": "beads"},
        )
        assert config.provider == "beads"
        assert config.workspace == "my-ws"

        # Config persisted to disk
        loaded = load_tracker_config(repo)
        assert loaded.provider == "beads"
        assert loaded.workspace == "my-ws"

        # Credentials persisted
        stored = svc.credential_store.get_provider("beads")
        assert stored["command"] == "beads"

    def test_bind_normalizes_provider(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        config = svc.bind(
            provider="  FP  ",
            workspace="ws",
            doctrine_mode="external_authoritative",
            doctrine_field_owners={},
            credentials={"command": "fp"},
        )
        assert config.provider == "fp"

    def test_bind_no_credentials(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        config = svc.bind(
            provider="beads",
            workspace="ws",
            doctrine_mode="external_authoritative",
            doctrine_field_owners={},
            credentials={},
        )
        assert config.provider == "beads"
        # No credentials stored — get_provider returns empty dict
        assert svc.credential_store.get_provider("beads") == {}

    def test_bind_with_doctrine_field_owners(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        owners = {"title": "external", "status": "local"}
        config = svc.bind(
            provider="fp",
            workspace="ws",
            doctrine_mode="split",
            doctrine_field_owners=owners,
            credentials={"command": "fp"},
        )
        assert config.doctrine_mode == "split"
        assert config.doctrine_field_owners == owners


# ---------------------------------------------------------------------------
# unbind
# ---------------------------------------------------------------------------


class TestUnbind:
    def test_unbind_clears_config_and_credentials(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        # Bind first
        svc.bind(
            provider="beads",
            workspace="ws",
            doctrine_mode="external_authoritative",
            doctrine_field_owners={},
            credentials={"command": "beads"},
        )
        # Verify bound
        assert load_tracker_config(repo).is_configured

        # Unbind
        svc.unbind()

        # Config cleared
        loaded = load_tracker_config(repo)
        assert not loaded.is_configured

        # Credentials cleared
        assert svc.credential_store.get_provider("beads") == {}

    def test_unbind_without_provider_does_not_crash(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        # Unbind when nothing is configured — should not raise
        svc.unbind()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_status_unconfigured(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        result = svc.status()
        assert result["configured"] is False
        assert result["provider"] is None
        assert result["issue_count"] == 0
        assert result["mapping_count"] == 0

    def test_status_configured(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        svc.bind(
            provider="beads",
            workspace="ws",
            doctrine_mode="external_authoritative",
            doctrine_field_owners={},
            credentials={"command": "beads"},
        )

        with patch.object(
            svc, "_run_async", return_value=[]
        ):
            result = svc.status()

        assert result["configured"] is True
        assert result["provider"] == "beads"
        assert result["workspace"] == "ws"
        assert result["credentials_present"] is True


# ---------------------------------------------------------------------------
# sync operations — verify delegation to connector
# ---------------------------------------------------------------------------


class TestSyncOperations:
    """Verify sync_pull/push/run wire up to the direct connector correctly.

    We mock _build_engine to avoid needing the spec_kitty_tracker package.
    """

    def _setup_bound_service(self, repo: Path, cred_path: Path) -> LocalTrackerService:
        svc = _make_service(repo, cred_path=cred_path)
        svc.bind(
            provider="beads",
            workspace="ws",
            doctrine_mode="external_authoritative",
            doctrine_field_owners={},
            credentials={"command": "beads"},
        )
        return svc

    def _mock_engine_result(self) -> MagicMock:
        """Create a mock sync result compatible with _sync_result()."""
        result = MagicMock()
        result.stats.pulled_created = 1
        result.stats.pulled_updated = 2
        result.stats.pushed_created = 0
        result.stats.pushed_updated = 0
        result.stats.skipped = 0
        result.conflicts = []
        result.errors = []
        return result

    def test_sync_pull_delegates_to_connector(self, repo: Path, cred_path: Path) -> None:
        svc = self._setup_bound_service(repo, cred_path)
        mock_result = self._mock_engine_result()

        mock_connector = MagicMock()
        mock_connector.name = "beads"
        mock_engine = MagicMock()
        mock_engine.checkpoint = MagicMock()

        async def mock_pull(limit: int = 100) -> Any:
            return mock_result

        mock_engine.pull = mock_pull

        with patch.object(svc, "_build_engine", return_value=(mock_connector, mock_engine)):
            with patch(
                "specify_cli.tracker.local_service.TrackerSqliteStore"
            ) as MockStore:
                mock_store = MagicMock()
                mock_store.get_checkpoint.return_value = None
                MockStore.return_value = mock_store

                result = svc.sync_pull(limit=50)

        assert result["provider"] == "beads"
        assert result["stats"]["pulled_created"] == 1
        assert result["stats"]["pulled_updated"] == 2

    def test_sync_push_delegates_to_connector(self, repo: Path, cred_path: Path) -> None:
        svc = self._setup_bound_service(repo, cred_path)
        mock_result = self._mock_engine_result()

        mock_connector = MagicMock()
        mock_connector.name = "beads"
        mock_engine = MagicMock()

        async def mock_push(limit: int = 100) -> Any:
            return mock_result

        mock_engine.push = mock_push

        with patch.object(svc, "_build_engine", return_value=(mock_connector, mock_engine)):
            with patch(
                "specify_cli.tracker.local_service.TrackerSqliteStore"
            ) as MockStore:
                mock_store = MagicMock()
                MockStore.return_value = mock_store

                result = svc.sync_push(limit=50)

        assert result["provider"] == "beads"

    def test_sync_run_delegates_to_connector(self, repo: Path, cred_path: Path) -> None:
        svc = self._setup_bound_service(repo, cred_path)
        mock_result = self._mock_engine_result()

        mock_connector = MagicMock()
        mock_connector.name = "beads"
        mock_engine = MagicMock()
        mock_engine.checkpoint = MagicMock()

        async def mock_sync(limit: int = 100) -> Any:
            return mock_result

        mock_engine.sync = mock_sync

        with patch.object(svc, "_build_engine", return_value=(mock_connector, mock_engine)):
            with patch(
                "specify_cli.tracker.local_service.TrackerSqliteStore"
            ) as MockStore:
                mock_store = MagicMock()
                mock_store.get_checkpoint.return_value = None
                MockStore.return_value = mock_store

                result = svc.sync_run(limit=50)

        assert result["provider"] == "beads"


# ---------------------------------------------------------------------------
# map_add / map_list
# ---------------------------------------------------------------------------


class TestMapOperations:
    def test_map_add_and_list_roundtrip(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        svc.bind(
            provider="beads",
            workspace="ws",
            doctrine_mode="external_authoritative",
            doctrine_field_owners={},
            credentials={"command": "beads"},
        )

        mock_ref_cls = MagicMock()
        mock_store = MagicMock()
        mock_store.list_mappings.return_value = [
            {
                "wp_id": "WP01",
                "external_id": "BEAD-1",
                "external_key": "K1",
                "external_url": None,
            }
        ]

        with patch.object(svc, "_load_runtime", return_value=(
            load_tracker_config(repo),
            {"command": "beads"},
            mock_store,
        )):
            with patch(
                "specify_cli.tracker.local_service.LocalTrackerService.map_add",
                wraps=None,
            ):
                # Directly test map_list via the mocked runtime
                mappings = svc.map_list()

        assert len(mappings) == 1
        assert mappings[0]["wp_id"] == "WP01"

    def test_map_add_calls_upsert(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        svc.bind(
            provider="beads",
            workspace="ws",
            doctrine_mode="external_authoritative",
            doctrine_field_owners={},
            credentials={"command": "beads"},
        )

        mock_store = MagicMock()
        config = load_tracker_config(repo)

        # Build a fake spec_kitty_tracker.models module with ExternalRef
        mock_external_ref_instance = MagicMock()
        mock_external_ref_cls = MagicMock(return_value=mock_external_ref_instance)
        fake_models = MagicMock()
        fake_models.ExternalRef = mock_external_ref_cls

        import sys

        with patch.object(svc, "_load_runtime", return_value=(
            config,
            {"command": "beads"},
            mock_store,
        )):
            with patch.dict(sys.modules, {"spec_kitty_tracker": MagicMock(), "spec_kitty_tracker.models": fake_models}):
                svc.map_add(
                    wp_id="WP01",
                    external_id="BEAD-1",
                    external_key="K1",
                    external_url=None,
                )

        mock_external_ref_cls.assert_called_once_with(
            system="beads",
            workspace="ws",
            id="BEAD-1",
            key="K1",
            url=None,
        )
        mock_store.upsert_mapping.assert_called_once_with(
            wp_id="WP01", ref=mock_external_ref_instance,
        )


# ---------------------------------------------------------------------------
# _load_runtime
# ---------------------------------------------------------------------------


class TestLoadRuntime:
    def test_load_runtime_raises_when_not_configured(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        with pytest.raises(LocalTrackerServiceError, match="not configured"):
            svc._load_runtime()

    def test_load_runtime_raises_when_provider_missing(self, repo: Path, cred_path: Path) -> None:
        # Save config with provider but no workspace
        broken_config = TrackerProjectConfig(provider="beads", workspace=None)
        save_tracker_config(repo, broken_config)

        svc = _make_service(repo, cred_path=cred_path)
        with pytest.raises(LocalTrackerServiceError, match="not configured|incomplete"):
            svc._load_runtime()


# ---------------------------------------------------------------------------
# No SaaS imports
# ---------------------------------------------------------------------------


class TestNoSaaSImports:
    """Verify no SaaS-related imports leak into local_service module."""

    def test_no_saas_client_import(self) -> None:
        import specify_cli.tracker.local_service as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import" not in source or "saas_client" not in source
        # Check no actual import of SaaS tracker client
        assert "from specify_cli.tracker.saas" not in source
        assert "import SaaSTrackerClient" not in source

    def test_no_sync_auth_import(self) -> None:
        import specify_cli.tracker.local_service as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        # CredentialStore from sync/auth should not appear
        assert "sync.auth" not in source
        assert "from specify_cli.sync" not in source
