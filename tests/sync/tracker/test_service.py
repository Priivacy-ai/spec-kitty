"""Tests for TrackerService facade dispatch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    save_tracker_config,
)
from specify_cli.tracker.service import TrackerService, TrackerServiceError

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# _resolve_backend dispatch tests
# ---------------------------------------------------------------------------


class TestResolveBackendSaaS:
    """SaaS providers dispatch to SaaSTrackerService."""

    @pytest.mark.parametrize("provider", ["linear", "jira", "github", "gitlab"])
    def test_saas_provider_returns_saas_service(self, tmp_path: Path, provider: str) -> None:
        from specify_cli.tracker.saas_service import SaaSTrackerService

        _setup_config(tmp_path, provider=provider, project_slug="my-proj")
        service = TrackerService(tmp_path)
        backend = service._resolve_backend()
        assert isinstance(backend, SaaSTrackerService)


class TestResolveBackendLocal:
    """Local providers dispatch to LocalTrackerService."""

    @pytest.mark.parametrize("provider", ["beads", "fp"])
    def test_local_provider_returns_local_service(self, tmp_path: Path, provider: str) -> None:
        from specify_cli.tracker.local_service import LocalTrackerService

        _setup_config(tmp_path, provider=provider, workspace="my-ws")
        service = TrackerService(tmp_path)
        backend = service._resolve_backend()
        assert isinstance(backend, LocalTrackerService)


class TestResolveBackendRemoved:
    """Removed providers raise immediately."""

    def test_azure_devops_raises(self, tmp_path: Path) -> None:
        _setup_config(tmp_path, provider="azure_devops", workspace="org/proj")
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="no longer supported"):
            service._resolve_backend()


class TestResolveBackendNoBinding:
    """No binding raises immediately."""

    def test_no_config_raises(self, tmp_path: Path) -> None:
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="No tracker bound"):
            service._resolve_backend()

    def test_empty_provider_raises(self, tmp_path: Path) -> None:
        # Config file exists but provider is empty
        _setup_config(tmp_path, provider=None)
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="No tracker bound"):
            service._resolve_backend()


class TestResolveBackendUnknown:
    """Unknown providers raise immediately."""

    def test_unknown_provider_raises(self, tmp_path: Path) -> None:
        _setup_config(tmp_path, provider="notion", workspace="ws")
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="Unknown provider"):
            service._resolve_backend()


# ---------------------------------------------------------------------------
# supported_providers()
# ---------------------------------------------------------------------------


class TestSupportedProviders:
    """supported_providers() returns all active providers."""

    def test_includes_saas_providers(self) -> None:
        providers = TrackerService.supported_providers()
        for p in ("linear", "jira", "github", "gitlab"):
            assert p in providers

    def test_includes_local_providers(self) -> None:
        providers = TrackerService.supported_providers()
        for p in ("beads", "fp"):
            assert p in providers

    def test_excludes_removed_providers(self) -> None:
        providers = TrackerService.supported_providers()
        assert "azure_devops" not in providers

    def test_returns_sorted_tuple(self) -> None:
        providers = TrackerService.supported_providers()
        assert isinstance(providers, tuple)
        assert providers == tuple(sorted(providers))


# ---------------------------------------------------------------------------
# bind dispatch tests
# ---------------------------------------------------------------------------


class TestBindDispatch:
    """bind() dispatches to the correct backend based on provider kwarg."""

    def test_bind_saas_provider_dispatches_to_saas(self, tmp_path: Path) -> None:
        from specify_cli.tracker.discovery import BindResult
        from specify_cli.tracker.saas_service import SaaSTrackerService

        service = TrackerService(tmp_path)
        mock_return = BindResult(
            binding_ref="br-1",
            display_label="Linear Eng",
            provider="linear",
            provider_context={},
            bound_at="2026-01-01T00:00:00Z",
        )
        with patch.object(
            SaaSTrackerService, "resolve_and_bind", return_value=mock_return
        ) as mock_rab:
            result = service.bind(provider="linear", project_identity={"slug": "my-proj"})
            mock_rab.assert_called_once_with(
                provider="linear",
                project_identity={"slug": "my-proj"},
                select_n=None,
            )
            assert result.binding_ref == "br-1"

    def test_bind_local_provider_dispatches_to_local(self, tmp_path: Path) -> None:
        from specify_cli.tracker.local_service import LocalTrackerService

        service = TrackerService(tmp_path)
        with patch.object(
            LocalTrackerService,
            "bind",
            return_value=TrackerProjectConfig(provider="beads", workspace="ws"),
        ) as mock_bind:
            result = service.bind(
                provider="beads",
                workspace="ws",
                doctrine_mode="external_authoritative",
                doctrine_field_owners={},
                credentials={},
            )
            mock_bind.assert_called_once_with(
                provider="beads",
                workspace="ws",
                doctrine_mode="external_authoritative",
                doctrine_field_owners={},
                credentials={},
            )
            assert result.provider == "beads"

    def test_bind_removed_provider_raises(self, tmp_path: Path) -> None:
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="no longer supported"):
            service.bind(provider="azure_devops", workspace="org/proj")

    def test_bind_unknown_provider_raises(self, tmp_path: Path) -> None:
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="Unknown provider"):
            service.bind(provider="notion", workspace="ws")


# ---------------------------------------------------------------------------
# Delegation tests (verify methods call through to backend)
# ---------------------------------------------------------------------------


class TestDelegation:
    """Verify delegating methods call _resolve_backend()."""

    def test_unbind_delegates(self, tmp_path: Path) -> None:
        from specify_cli.tracker.local_service import LocalTrackerService

        _setup_config(tmp_path, provider="beads", workspace="ws")
        service = TrackerService(tmp_path)
        with patch.object(LocalTrackerService, "unbind") as mock_unbind:
            service.unbind()
            mock_unbind.assert_called_once()

    def test_status_delegates(self, tmp_path: Path) -> None:
        from specify_cli.tracker.local_service import LocalTrackerService

        _setup_config(tmp_path, provider="beads", workspace="ws")
        service = TrackerService(tmp_path)
        with patch.object(LocalTrackerService, "status", return_value={"configured": True}) as mock_status:
            result = service.status()
            mock_status.assert_called_once()
            assert result == {"configured": True}


# ---------------------------------------------------------------------------
# parse_kv_pairs preserved
# ---------------------------------------------------------------------------


class TestParseKvPairsPreserved:
    """parse_kv_pairs must still be importable from service module."""

    def test_importable(self) -> None:
        from specify_cli.tracker.service import parse_kv_pairs

        result = parse_kv_pairs(["key=value", "a=b"])
        assert result == {"key": "value", "a": "b"}

    def test_invalid_entry_raises(self) -> None:
        from specify_cli.tracker.service import parse_kv_pairs

        with pytest.raises(TrackerServiceError, match="Invalid"):
            parse_kv_pairs(["noequals"])


# ---------------------------------------------------------------------------
# discover() facade tests (T042, T045)
# ---------------------------------------------------------------------------


class TestDiscoverFacade:
    """discover() on facade dispatches to SaaSTrackerService and guards locals."""

    def test_discover_saas_delegates(self, tmp_path: Path) -> None:
        """SaaS provider delegates to SaaSTrackerService.discover()."""
        from specify_cli.tracker.discovery import BindableResource
        from specify_cli.tracker.saas_service import SaaSTrackerService

        service = TrackerService(tmp_path)
        fake_resource = BindableResource(
            candidate_token="tok-1",
            display_label="My Project",
            provider="linear",
            provider_context={"team": "eng"},
        )
        with patch.object(
            SaaSTrackerService, "discover", return_value=[fake_resource]
        ) as mock_discover:
            result = service.discover(provider="linear")
            mock_discover.assert_called_once_with("linear")
            assert len(result) == 1
            assert result[0].display_label == "My Project"

    @pytest.mark.parametrize("provider", ["beads", "fp"])
    def test_discover_local_raises(self, tmp_path: Path, provider: str) -> None:
        """Local providers raise TrackerServiceError."""
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="not available for local"):
            service.discover(provider=provider)

    def test_discover_removed_raises(self, tmp_path: Path) -> None:
        """Removed providers raise TrackerServiceError."""
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="no longer supported"):
            service.discover(provider="azure_devops")

    def test_discover_unknown_raises(self, tmp_path: Path) -> None:
        """Unknown providers raise TrackerServiceError."""
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="Unknown provider"):
            service.discover(provider="notion")


# ---------------------------------------------------------------------------
# bind() SaaS discovery flow tests (T043)
# ---------------------------------------------------------------------------


class TestBindSaaSDiscoveryFlow:
    """bind() SaaS path delegates to resolve_and_bind / validate_and_bind."""

    def test_bind_saas_delegates_to_resolve_and_bind(self, tmp_path: Path) -> None:
        """SaaS bind without bind_ref calls resolve_and_bind."""
        from specify_cli.tracker.discovery import BindResult
        from specify_cli.tracker.saas_service import SaaSTrackerService

        service = TrackerService(tmp_path)
        fake_result = BindResult(
            binding_ref="br-123",
            display_label="Linear - Eng",
            provider="linear",
            provider_context={"team": "eng"},
            bound_at="2026-04-04T12:00:00Z",
        )
        with patch.object(
            SaaSTrackerService, "resolve_and_bind", return_value=fake_result
        ) as mock_rab:
            result = service.bind(
                provider="linear",
                project_identity={"repo": "my-repo"},
            )
            mock_rab.assert_called_once_with(
                provider="linear",
                project_identity={"repo": "my-repo"},
                select_n=None,
            )
            assert result.binding_ref == "br-123"

    def test_bind_saas_with_select_n(self, tmp_path: Path) -> None:
        """SaaS bind with select_n passes it through to resolve_and_bind."""
        from specify_cli.tracker.discovery import BindResult
        from specify_cli.tracker.saas_service import SaaSTrackerService

        service = TrackerService(tmp_path)
        fake_result = BindResult(
            binding_ref="br-456",
            display_label="Linear - Prod",
            provider="linear",
            provider_context={},
            bound_at="2026-04-04T12:00:00Z",
        )
        with patch.object(
            SaaSTrackerService, "resolve_and_bind", return_value=fake_result
        ) as mock_rab:
            result = service.bind(
                provider="linear",
                select_n=2,
                project_identity={"repo": "my-repo"},
            )
            mock_rab.assert_called_once_with(
                provider="linear",
                project_identity={"repo": "my-repo"},
                select_n=2,
            )
            assert result.binding_ref == "br-456"

    def test_bind_saas_with_bind_ref(self, tmp_path: Path) -> None:
        """SaaS bind with bind_ref calls validate_and_bind."""
        from specify_cli.tracker.saas_service import SaaSTrackerService

        service = TrackerService(tmp_path)
        fake_config = TrackerProjectConfig(
            provider="linear",
            binding_ref="br-known",
        )
        with patch.object(
            SaaSTrackerService, "validate_and_bind", return_value=fake_config
        ) as mock_vab:
            result = service.bind(
                provider="linear",
                bind_ref="br-known",
                project_identity={"repo": "my-repo"},
            )
            mock_vab.assert_called_once_with(
                provider="linear",
                bind_ref="br-known",
                project_identity={"repo": "my-repo"},
            )
            assert result.binding_ref == "br-known"

    def test_bind_local_provider_still_dispatches_to_local(self, tmp_path: Path) -> None:
        """Local providers still dispatch to LocalTrackerService.bind()."""
        from specify_cli.tracker.local_service import LocalTrackerService

        service = TrackerService(tmp_path)
        with patch.object(
            LocalTrackerService,
            "bind",
            return_value=TrackerProjectConfig(provider="beads", workspace="ws"),
        ) as mock_bind:
            result = service.bind(
                provider="beads",
                workspace="ws",
                doctrine_mode="external_authoritative",
                doctrine_field_owners={},
                credentials={},
            )
            mock_bind.assert_called_once()
            assert result.provider == "beads"


# ---------------------------------------------------------------------------
# status(all=) tests (T044, T045)
# ---------------------------------------------------------------------------


class TestStatusAll:
    """status(all=True) returns installation-wide status for SaaS only."""

    def test_status_all_saas(self, tmp_path: Path) -> None:
        """SaaS provider + all=True calls client.status without routing params."""
        _setup_config(tmp_path, provider="linear", project_slug="my-proj")
        service = TrackerService(tmp_path)

        mock_client = MagicMock()
        mock_client.status.return_value = {
            "bindings": [{"provider": "linear", "binding_ref": "br-1"}],
        }
        with patch(
            "specify_cli.tracker.saas_service.SaaSTrackerClient",
            return_value=mock_client,
        ):
            result = service.status(all=True)
            mock_client.status.assert_called_once_with("linear")
            assert "bindings" in result

    def test_status_all_local_raises(self, tmp_path: Path) -> None:
        """Local provider + all=True raises TrackerServiceError."""
        _setup_config(tmp_path, provider="beads", workspace="ws")
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="only available for SaaS"):
            service.status(all=True)

    def test_status_all_no_provider_raises(self, tmp_path: Path) -> None:
        """No provider + all=True raises TrackerServiceError."""
        service = TrackerService(tmp_path)
        with pytest.raises(TrackerServiceError, match="only available for SaaS"):
            service.status(all=True)

    def test_status_without_all_delegates_normally(self, tmp_path: Path) -> None:
        """status() without all=True still delegates to _resolve_backend()."""
        from specify_cli.tracker.local_service import LocalTrackerService

        _setup_config(tmp_path, provider="beads", workspace="ws")
        service = TrackerService(tmp_path)
        with patch.object(
            LocalTrackerService, "status", return_value={"configured": True}
        ) as mock_status:
            result = service.status()
            mock_status.assert_called_once()
            assert result == {"configured": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_config(
    repo_root: Path,
    *,
    provider: str | None = None,
    workspace: str | None = None,
    project_slug: str | None = None,
) -> None:
    """Create a minimal tracker config for testing."""
    config = TrackerProjectConfig(
        provider=provider,
        workspace=workspace,
        project_slug=project_slug,
    )
    save_tracker_config(repo_root, config)
