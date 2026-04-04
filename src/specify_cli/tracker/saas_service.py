"""Service layer for SaaS-backed tracker providers (linear, jira, github, gitlab).

Delegates all tracker operations to ``SaaSTrackerClient`` and hard-fails
operations that are not supported for SaaS-backed providers.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    clear_tracker_config,
    save_tracker_config,
)
from specify_cli.tracker.saas_client import SaaSTrackerClient, SaaSTrackerClientError
from specify_cli.tracker.service import StaleBindingError, TrackerServiceError

logger = logging.getLogger(__name__)

_STALE_BINDING_CODES: frozenset[str] = frozenset(
    {"binding_not_found", "mapping_disabled", "project_mismatch"}
)


class SaaSTrackerService:
    """Service wrapper for SaaS-backed tracker providers.

    This class never holds provider-native credentials.  It reads
    ``binding_ref`` (preferred) or ``project_slug`` from config and
    derives ``team_slug`` from the auth credential store at call time
    (via the SaaS client).
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
    # Routing resolution
    # ------------------------------------------------------------------

    def _resolve_routing_params(self) -> dict[str, str]:
        """Resolve which routing key to send to the client.

        Returns dict with either ``binding_ref`` or ``project_slug`` key.
        ``binding_ref`` takes precedence when both are present.
        Raises ``TrackerServiceError`` if neither is available.
        """
        if self._config.binding_ref:
            return {"binding_ref": self._config.binding_ref}
        if self._config.project_slug:
            return {"project_slug": self._config.project_slug}
        raise TrackerServiceError(
            "No tracker binding configured. Run `spec-kitty tracker bind` first."
        )

    # ------------------------------------------------------------------
    # Opportunistic upgrade
    # ------------------------------------------------------------------

    def _maybe_upgrade_binding_ref(self, response: dict[str, Any]) -> None:
        """Opportunistically persist binding_ref from response if available.

        Silent on failure (debug log only).  Never modifies config if
        response doesn't contain binding_ref.

        Atomicity: builds a *new* config object and persists it before
        updating ``self._config``.  If the save fails, the in-memory
        state remains unchanged.
        """
        binding_ref = response.get("binding_ref")
        if not binding_ref:
            return
        if self._config.binding_ref == binding_ref:
            return  # Already up to date

        try:
            # Build updated config WITHOUT mutating self._config yet
            updated = TrackerProjectConfig(
                provider=self._config.provider,
                binding_ref=binding_ref,
                project_slug=self._config.project_slug,
                display_label=response.get("display_label") or self._config.display_label,
                provider_context=(
                    response.get("provider_context")
                    if isinstance(response.get("provider_context"), dict)
                    else self._config.provider_context
                ),
                workspace=self._config.workspace,
                doctrine_mode=self._config.doctrine_mode,
                doctrine_field_owners=self._config.doctrine_field_owners,
                _extra=self._config._extra,
            )
            save_tracker_config(self._repo_root, updated)
            # Only update in-memory state AFTER successful save
            self._config = updated
            logger.debug("Opportunistically upgraded binding_ref to %s", binding_ref)
        except Exception:
            logger.debug("Failed to upgrade binding_ref", exc_info=True)

    # ------------------------------------------------------------------
    # Stale-binding detection
    # ------------------------------------------------------------------

    def _call_with_stale_detection(
        self,
        method: Callable[..., dict[str, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Invoke a client method, translating stale-binding errors.

        When routing by ``binding_ref`` and the server responds with a
        known stale-binding error code, raises ``StaleBindingError``
        instead of the raw client error.
        """
        try:
            return method(*args, **kwargs)
        except SaaSTrackerClientError as e:
            if (
                e.error_code in _STALE_BINDING_CODES
                and self._config.binding_ref
            ):
                raise StaleBindingError(
                    f"Tracker binding is stale: {e}. "
                    f"Run `spec-kitty tracker bind --provider {self.provider}` to rebind.",
                    binding_ref=self._config.binding_ref,
                    error_code=e.error_code or "unknown",
                ) from e
            raise

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
        routing = self._resolve_routing_params()
        result = self._call_with_stale_detection(
            self._client.status, self.provider, **routing,
        )
        self._maybe_upgrade_binding_ref(result)
        return result

    def sync_pull(self, *, limit: int = 100) -> dict[str, Any]:
        """Pull items from the external tracker via the SaaS control plane."""
        routing = self._resolve_routing_params()
        result = self._call_with_stale_detection(
            self._client.pull, self.provider, limit=limit, **routing,
        )
        self._maybe_upgrade_binding_ref(result)
        return result

    def sync_push(self, *, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Push items to the external tracker via the SaaS control plane.

        ``items`` is a list of ``PushItem`` dicts as defined by the PRI-12
        ``TrackerPushRequest`` contract.  Each item carries a ``ref``,
        ``action``, and optional ``patch`` / ``target_status``.
        """
        routing = self._resolve_routing_params()
        result = self._call_with_stale_detection(
            self._client.push, self.provider, items=items or [], **routing,
        )
        self._maybe_upgrade_binding_ref(result)
        return result

    def sync_run(self, *, limit: int = 100) -> dict[str, Any]:
        """Run a full sync cycle via the SaaS control plane."""
        routing = self._resolve_routing_params()
        result = self._call_with_stale_detection(
            self._client.run, self.provider, limit=limit, **routing,
        )
        self._maybe_upgrade_binding_ref(result)
        return result

    def map_list(self) -> list[dict[str, Any]]:
        """List field mappings from the SaaS control plane."""
        routing = self._resolve_routing_params()
        result = self._call_with_stale_detection(
            self._client.mappings, self.provider, **routing,
        )
        self._maybe_upgrade_binding_ref(result)
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
