"""Service layer for SaaS-backed tracker providers (linear, jira, github, gitlab).

Delegates all tracker operations to ``SaaSTrackerClient`` and hard-fails
operations that are not supported for SaaS-backed providers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    clear_tracker_config,
    save_tracker_config,
)
from specify_cli.tracker.saas_client import SaaSTrackerClient
from specify_cli.tracker.service import TrackerServiceError


class SaaSTrackerService:
    """Service wrapper for SaaS-backed tracker providers.

    This class never holds provider-native credentials.  It reads
    ``project_slug`` from config and derives ``team_slug`` from the auth
    credential store at call time (via the SaaS client).
    """

    def __init__(
        self,
        repo_root: Path,
        config: TrackerProjectConfig,
        *,
        client: SaaSTrackerClient | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._config = config
        self._client = client or SaaSTrackerClient()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def provider(self) -> str:
        assert self._config.provider is not None  # noqa: S101
        return self._config.provider

    @property
    def project_slug(self) -> str:
        assert self._config.project_slug is not None  # noqa: S101
        return self._config.project_slug

    # ------------------------------------------------------------------
    # bind / unbind
    # ------------------------------------------------------------------

    def bind(self, *, provider: str, project_slug: str) -> TrackerProjectConfig:
        """Bind a SaaS-backed tracker provider.

        Stores provider + project_slug only.  No credentials are accepted
        because SaaS-backed providers authenticate through the Spec Kitty
        SaaS control plane.
        """
        config = TrackerProjectConfig(
            provider=provider,
            project_slug=project_slug,
        )
        save_tracker_config(self._repo_root, config)
        self._config = config
        return config

    def unbind(self) -> None:
        """Clear tracker configuration.

        Does NOT touch ``TrackerCredentialStore`` because SaaS-backed
        providers never store provider-native secrets locally.
        """
        clear_tracker_config(self._repo_root)
        self._config = TrackerProjectConfig()

    # ------------------------------------------------------------------
    # Operations delegated to SaaSTrackerClient
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Retrieve connection / sync status from the SaaS control plane."""
        return self._client.status(self.provider, self.project_slug)

    def sync_pull(self, *, limit: int = 100) -> dict[str, Any]:
        """Pull items from the external tracker via the SaaS control plane."""
        return self._client.pull(self.provider, self.project_slug, limit=limit)

    def sync_push(self, *, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Push items to the external tracker via the SaaS control plane.

        ``items`` is a list of ``PushItem`` dicts as defined by the PRI-12
        ``TrackerPushRequest`` contract.  Each item carries a ``ref``,
        ``action``, and optional ``patch`` / ``target_status``.
        """
        return self._client.push(
            self.provider, self.project_slug, items=items or [],
        )

    def sync_run(self, *, limit: int = 100) -> dict[str, Any]:
        """Run a full sync cycle via the SaaS control plane."""
        return self._client.run(self.provider, self.project_slug, limit=limit)

    def map_list(self) -> list[dict[str, Any]]:
        """List field mappings from the SaaS control plane."""
        result = self._client.mappings(self.provider, self.project_slug)
        mappings: list[dict[str, Any]] = result.get("mappings", [])
        return mappings

    # ------------------------------------------------------------------
    # Hard-fails: operations not supported for SaaS-backed providers
    # ------------------------------------------------------------------

    def map_add(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Always fails -- mappings for SaaS providers are dashboard-managed."""
        raise TrackerServiceError(
            "Mappings for SaaS-backed providers are managed in the Spec Kitty dashboard. "
            "Use the web interface to create or edit mappings."
        )

    def sync_publish(self, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG002
        """Always fails -- snapshot publish is not supported for SaaS providers."""
        raise TrackerServiceError(
            "Snapshot publish is not supported for SaaS-backed providers. "
            "Use `spec-kitty tracker sync push` to push changes through the SaaS control plane."
        )
