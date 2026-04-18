"""High-level tracker orchestration for CLI commands.

Thin facade that dispatches to ``SaaSTrackerService`` (linear, jira,
github, gitlab) or ``LocalTrackerService`` (beads, fp) based on the
bound provider in project config.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specify_cli.tracker.config import (
    ALL_SUPPORTED_PROVIDERS,
    LOCAL_PROVIDERS,
    REMOVED_PROVIDERS,
    SAAS_PROVIDERS,
    TrackerProjectConfig,
    load_tracker_config,
)


class TrackerServiceError(RuntimeError):
    """Raised when tracker service operations fail."""


class StaleBindingError(TrackerServiceError):
    """Raised when binding_ref is stale (deleted/disabled on host).

    The caller should prompt the user to rebind via
    ``spec-kitty tracker bind --provider <provider>``.
    """

    def __init__(self, message: str, *, binding_ref: str, error_code: str) -> None:
        super().__init__(message)
        self.binding_ref = binding_ref
        self.error_code = error_code


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
    """Facade dispatching to SaaS or local backend by provider."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    # ------------------------------------------------------------------
    # Backend resolution
    # ------------------------------------------------------------------

    def _resolve_backend(self) -> Any:
        """Load config and return the appropriate service backend."""
        from specify_cli.tracker.local_service import LocalTrackerService
        from specify_cli.tracker.saas_service import SaaSTrackerService

        config = load_tracker_config(self._repo_root)
        if not config.provider:
            raise TrackerServiceError("No tracker bound. Run `spec-kitty tracker bind` first.")
        if config.provider in SAAS_PROVIDERS:
            return SaaSTrackerService(self._repo_root, config)
        if config.provider in LOCAL_PROVIDERS:
            return LocalTrackerService(self._repo_root, config)
        if config.provider in REMOVED_PROVIDERS:
            raise TrackerServiceError(
                f"Provider '{config.provider}' is no longer supported. "
                "See the Spec Kitty documentation for supported providers."
            )
        raise TrackerServiceError(f"Unknown provider: {config.provider}")

    def _resolve_saas_backend_for_provider(self, provider: str) -> Any:
        from specify_cli.tracker.saas_service import SaaSTrackerService

        if provider in LOCAL_PROVIDERS:
            raise TrackerServiceError(
                f"Provider-scoped hosted reads are not available for local provider '{provider}'."
            )
        if provider in REMOVED_PROVIDERS:
            raise TrackerServiceError(f"Provider '{provider}' is no longer supported.")
        if provider not in SAAS_PROVIDERS:
            raise TrackerServiceError(f"Unknown provider: {provider}")

        config = load_tracker_config(self._repo_root)
        if config.provider != provider:
            config = TrackerProjectConfig(provider=provider)
        return SaaSTrackerService(self._repo_root, config)

    @staticmethod
    def supported_providers() -> tuple[str, ...]:
        """Return all currently supported provider names, sorted."""
        return tuple(sorted(ALL_SUPPORTED_PROVIDERS))

    # ------------------------------------------------------------------
    # discover (SaaS-only)
    # ------------------------------------------------------------------

    def discover(self, *, provider: str) -> list:
        """List bindable resources for the given provider (SaaS only)."""
        if provider in LOCAL_PROVIDERS:
            raise TrackerServiceError(
                f"Discovery is not available for local provider '{provider}'."
            )
        if provider in REMOVED_PROVIDERS:
            raise TrackerServiceError(f"Provider '{provider}' is no longer supported.")
        if provider not in SAAS_PROVIDERS:
            raise TrackerServiceError(f"Unknown provider: {provider}")

        from specify_cli.tracker.saas_service import SaaSTrackerService

        config = load_tracker_config(self._repo_root)
        service = SaaSTrackerService(self._repo_root, config)
        return service.discover(provider)

    # ------------------------------------------------------------------
    # bind (pre-dispatch by provider kwarg)
    # ------------------------------------------------------------------

    def bind(self, **kwargs: Any) -> Any:
        """Bind a tracker provider -- dispatches to the correct backend.

        For SaaS providers, accepts ``bind_ref``, ``select_n``, and
        ``project_identity`` kwargs to drive the discovery-bind flow.
        """
        from specify_cli.tracker.local_service import LocalTrackerService
        from specify_cli.tracker.saas_service import SaaSTrackerService

        provider: str = kwargs.get("provider", "")
        if provider in SAAS_PROVIDERS:
            service = SaaSTrackerService(
                self._repo_root,
                load_tracker_config(self._repo_root),
            )
            bind_ref = kwargs.get("bind_ref")
            select_n = kwargs.get("select_n")
            project_identity = kwargs.get("project_identity")

            if bind_ref:
                return service.validate_and_bind(
                    provider=provider,
                    bind_ref=bind_ref,
                    project_identity=project_identity,
                )

            return service.resolve_and_bind(
                provider=provider,
                project_identity=project_identity,
                select_n=select_n,
            )
        if provider in LOCAL_PROVIDERS:
            return LocalTrackerService(self._repo_root, TrackerProjectConfig()).bind(**kwargs)
        if provider in REMOVED_PROVIDERS:
            raise TrackerServiceError(f"Provider '{provider}' is no longer supported.")
        raise TrackerServiceError(f"Unknown provider: {provider}")

    # ------------------------------------------------------------------
    # Delegating methods
    # ------------------------------------------------------------------

    def unbind(self) -> None:
        return self._resolve_backend().unbind()

    def status(self, *, all: bool = False) -> dict[str, Any]:  # noqa: A002
        """Retrieve tracker status.

        When *all* is ``True``, return installation-wide status across all
        bindings (SaaS-only).  Otherwise return project-scoped status.
        """
        if all:
            config = load_tracker_config(self._repo_root)
            if not config.provider or config.provider not in SAAS_PROVIDERS:
                raise TrackerServiceError(
                    "Installation-wide status (--all) is only available for SaaS providers."
                )
            from specify_cli.tracker.saas_service import SaaSTrackerService

            service = SaaSTrackerService(self._repo_root, config)
            return service._client.status(config.provider, installation_wide=True)
        return self._resolve_backend().status()

    def sync_pull(self, **kwargs: Any) -> dict[str, Any]:
        return self._resolve_backend().sync_pull(**kwargs)

    def sync_push(self, **kwargs: Any) -> dict[str, Any]:
        return self._resolve_backend().sync_push(**kwargs)

    def sync_run(self, **kwargs: Any) -> dict[str, Any]:
        return self._resolve_backend().sync_run(**kwargs)

    def sync_publish(self, **kwargs: Any) -> dict[str, Any]:
        return self._resolve_backend().sync_publish(**kwargs)

    def map_add(self, **kwargs: Any) -> None:
        return self._resolve_backend().map_add(**kwargs)

    def map_list(self, *, provider: str | None = None) -> list[dict[str, Any]]:
        if provider is not None:
            return self._resolve_saas_backend_for_provider(provider).map_list(provider=provider)
        return self._resolve_backend().map_list()

    def issue_search(self, *, provider: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._resolve_saas_backend_for_provider(provider).issue_search(
            provider=provider,
            query=query,
            limit=limit,
        )

    def list_tickets(self, *, provider: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._resolve_saas_backend_for_provider(provider).list_tickets(
            provider=provider,
            limit=limit,
        )
