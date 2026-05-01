"""Service layer for SaaS-backed tracker providers (linear, jira, github, gitlab).

Delegates all tracker operations to ``SaaSTrackerClient`` and hard-fails
operations that are not supported for SaaS-backed providers.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    clear_tracker_config,
    save_tracker_config,
)
from specify_cli.tracker.discovery import (
    BindableResource,
    BindResult,
    ResolutionResult,
    find_candidate_by_position,
)
from specify_cli.tracker.saas_client import SaaSTrackerClient, SaaSTrackerClientError
from specify_cli.tracker.service import StaleBindingError, TrackerServiceError

logger = logging.getLogger(__name__)

_ISSUE_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*-\d+$")

_STALE_BINDING_CODES: frozenset[str] = frozenset({"binding_not_found", "mapping_disabled", "project_mismatch"})


def _normalize_ticket_item(item: dict[str, Any]) -> dict[str, Any]:
    state = item.get("state")
    if not isinstance(state, dict):
        state_name = item.get("status")
        state = {"name": state_name} if state_name is not None else {"name": None}

    team = item.get("team")
    if team is not None and not isinstance(team, dict):
        team = None

    assignee = item.get("assignee")
    if assignee is not None and not isinstance(assignee, dict):
        assignee = {"id": assignee, "name": None}

    return {
        "identifier": item.get("identifier") or item.get("external_issue_key") or item.get("external_issue_id"),
        "external_issue_id": item.get("external_issue_id") or item.get("id"),
        "title": item.get("title") or "",
        "url": item.get("url") or "",
        "state": {"name": state.get("name") if isinstance(state, dict) else None},
        "team": team,
        "assignee": assignee,
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "body": item.get("body"),
    }


def _normalize_ticket_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_normalize_ticket_item(item) for item in items]


def _looks_like_issue_identifier(query: str) -> bool:
    return bool(_ISSUE_IDENTIFIER_RE.match(query.strip()))


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
    def project_slug(self) -> str | None:
        """Legacy project_slug — may be None for binding_ref-only configs."""
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
        raise TrackerServiceError("No tracker binding configured. Run `spec-kitty tracker bind` first.")

    def _routing_for_provider(self, provider: str) -> dict[str, str]:
        """Return bound routing only when this service is already bound to *provider*."""
        if self._config.provider != provider:
            return {}
        if self._config.binding_ref:
            return {"binding_ref": self._config.binding_ref}
        if self._config.project_slug:
            return {"project_slug": self._config.project_slug}
        return {}

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
                provider_context=(response.get("provider_context") if isinstance(response.get("provider_context"), dict) else self._config.provider_context),
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
            if e.error_code in _STALE_BINDING_CODES and self._config.binding_ref:
                raise StaleBindingError(
                    f"Tracker binding '{self._config.binding_ref}' is stale: {e}. Run `spec-kitty tracker bind --provider {self.provider}` to rebind.",
                    binding_ref=self._config.binding_ref,
                    error_code=e.error_code or "unknown",
                ) from e
            raise

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
    # Discovery & binding
    # ------------------------------------------------------------------

    def discover(self, provider: str) -> list[BindableResource]:
        """List all bindable resources for the given provider."""
        result = self._client.resources(provider)
        return [BindableResource.from_api(r) for r in result.get("resources", [])]

    def _persist_binding(
        self,
        provider: str,
        binding_ref: str,
        display_label: str | None,
        provider_context: dict[str, str] | None,
        project_slug: str | None = None,
    ) -> None:
        """Write binding config to disk and update in-memory state."""
        same_provider = self._config.provider == provider
        resolved_slug = project_slug or (self._config.project_slug if same_provider else None)
        updated = TrackerProjectConfig(
            provider=provider,
            binding_ref=binding_ref,
            project_slug=resolved_slug,
            display_label=(display_label if display_label is not None else self._config.display_label if same_provider else None),
            provider_context=provider_context,
            workspace=self._config.workspace if same_provider else None,
            doctrine_mode=self._config.doctrine_mode,
            doctrine_field_owners=dict(self._config.doctrine_field_owners),
            _extra=dict(self._config._extra),
        )
        save_tracker_config(self._repo_root, updated)
        self._config = updated

    def _confirm_and_persist(
        self,
        provider: str,
        candidate_token: str,
        project_identity: dict[str, Any],
        *,
        select_n: int | None = None,
        allow_retry: bool = True,
    ) -> BindResult:
        """Confirm a candidate token and persist the binding."""
        try:
            result = BindResult.from_api(self._client.bind_confirm(provider, candidate_token, project_identity))
        except SaaSTrackerClientError as e:
            if e.error_code == "invalid_candidate_token":
                if allow_retry:
                    return self._retry_after_candidate_expiry(
                        provider,
                        project_identity,
                        select_n=select_n,
                    )
                raise TrackerServiceError("Candidate token expired. Please retry the bind operation.") from e
            raise
        self._persist_binding(
            provider,
            result.binding_ref,
            result.display_label,
            result.provider_context,
            project_slug=result.project_slug,
        )
        return result

    def _resolve_binding(
        self,
        provider: str,
        project_identity: dict[str, Any],
    ) -> ResolutionResult:
        """Resolve the local project identity to a host binding result."""
        return ResolutionResult.from_api(self._client.bind_resolve(provider, project_identity))

    def _retry_after_candidate_expiry(
        self,
        provider: str,
        project_identity: dict[str, Any],
        *,
        select_n: int | None,
    ) -> BindResult:
        """Re-resolve once after token expiry and retry the bind flow."""
        resolution = self._resolve_binding(provider, project_identity)

        if resolution.match_type == "none":
            raise TrackerServiceError("Candidate token expired and retry could not rediscover a bindable resource. Please retry the bind operation.")

        if resolution.match_type == "candidates" and select_n is None:
            raise TrackerServiceError("Candidate token expired and retry found multiple candidates. Please retry the bind operation.")

        retried = self._bind_from_resolution(
            provider,
            project_identity,
            resolution,
            select_n=select_n,
            allow_retry=False,
        )
        if isinstance(retried, ResolutionResult):
            raise TrackerServiceError("Candidate token expired and retry still requires manual selection. Please retry the bind operation.")
        return retried

    def _bind_from_resolution(
        self,
        provider: str,
        project_identity: dict[str, Any],
        resolution: ResolutionResult,
        *,
        select_n: int | None,
        allow_retry: bool,
    ) -> BindResult | ResolutionResult:
        """Complete the bind flow from a previously fetched resolution result."""
        if resolution.match_type == "exact":
            if resolution.binding_ref:
                # Existing mapping -- persist directly
                self._persist_binding(
                    provider,
                    resolution.binding_ref,
                    resolution.display_label,
                    None,
                    project_slug=resolution.project_slug,
                )
                return BindResult(
                    binding_ref=resolution.binding_ref,
                    display_label=resolution.display_label or "",
                    provider=provider,
                    provider_context={},
                    bound_at="",
                    project_slug=resolution.project_slug,
                )
            # Need to confirm
            assert resolution.candidate_token is not None  # noqa: S101
            return self._confirm_and_persist(
                provider,
                resolution.candidate_token,
                project_identity,
                select_n=select_n,
                allow_retry=allow_retry,
            )

        if resolution.match_type == "candidates":
            if select_n is not None:
                candidate = find_candidate_by_position(resolution.candidates, select_n)
                if candidate is None:
                    raise TrackerServiceError(f"Selection {select_n} is out of range. Valid range: 1-{len(resolution.candidates)}.")
                return self._confirm_and_persist(
                    provider,
                    candidate.candidate_token,
                    project_identity,
                    select_n=select_n,
                    allow_retry=allow_retry,
                )
            # Return resolution for CLI to handle interactive selection
            return resolution

        raise TrackerServiceError(f"No bindable resources found for provider '{provider}'. Verify the tracker is connected in the SaaS dashboard.")

    def resolve_and_bind(
        self,
        *,
        provider: str,
        project_identity: dict[str, Any] | None = None,
        select_n: int | None = None,
    ) -> BindResult | ResolutionResult:
        """Orchestrate the discovery-bind flow.

        Returns ``BindResult`` on success (auto-bind or confirmed selection).
        Returns ``ResolutionResult`` with candidates if user selection needed.
        Raises ``TrackerServiceError`` on no-match or validation failure.
        """
        identity = project_identity or {}
        resolution = self._resolve_binding(provider, identity)
        return self._bind_from_resolution(
            provider,
            identity,
            resolution,
            select_n=select_n,
            allow_retry=True,
        )

    def validate_and_bind(
        self,
        *,
        provider: str,
        bind_ref: str,
        project_identity: dict[str, Any] | None = None,
    ) -> TrackerProjectConfig:
        """Validate a known binding_ref and persist if valid.

        Used when the caller already has a binding_ref (e.g., from
        a previous session or from ``--bind-ref`` CLI flag).
        """
        from specify_cli.tracker.discovery import ValidationResult

        identity = project_identity or {}
        validation = ValidationResult.from_api(self._client.bind_validate(provider, bind_ref, identity))
        if not validation.valid:
            raise TrackerServiceError(f"Binding ref '{bind_ref}' is not valid: {validation.reason or 'unknown reason'}. {validation.guidance or ''}")
        self._persist_binding(
            provider,
            bind_ref,
            validation.display_label,
            validation.provider_context,
        )
        return self._config

    # ------------------------------------------------------------------
    # Operations delegated to SaaSTrackerClient
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Retrieve connection / sync status from the SaaS control plane."""
        routing = self._resolve_routing_params()
        result = self._call_with_stale_detection(
            self._client.status,
            self.provider,
            **routing,
        )
        self._maybe_upgrade_binding_ref(result)
        return result

    def sync_pull(self, *, limit: int = 100) -> dict[str, Any]:
        """Pull items from the external tracker via the SaaS control plane."""
        routing = self._resolve_routing_params()
        result = self._call_with_stale_detection(
            self._client.pull,
            self.provider,
            limit=limit,
            **routing,
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
            self._client.push,
            self.provider,
            items=items or [],
            **routing,
        )
        self._maybe_upgrade_binding_ref(result)
        return result

    def sync_run(self, *, limit: int = 100) -> dict[str, Any]:
        """Run a full sync cycle via the SaaS control plane."""
        routing = self._resolve_routing_params()
        result = self._call_with_stale_detection(
            self._client.run,
            self.provider,
            limit=limit,
            **routing,
        )
        self._maybe_upgrade_binding_ref(result)
        return result

    def map_list(self, *, provider: str | None = None) -> list[dict[str, Any]]:
        """List field mappings from the SaaS control plane."""
        resolved_provider = provider or self.provider
        if provider is None:
            routing = self._resolve_routing_params()
            result = self._call_with_stale_detection(
                self._client.mappings,
                resolved_provider,
                **routing,
            )
            self._maybe_upgrade_binding_ref(result)
        else:
            result = self._client.mappings(resolved_provider)
        mappings: list[dict[str, Any]] = result.get("mappings", [])
        return mappings

    def issue_search(self, *, provider: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search issues and return the normalized CLI ticket shape."""
        routing = self._routing_for_provider(provider)
        query_text = query
        query_key = query if _looks_like_issue_identifier(query) else None
        result = self._client.search_issues(
            provider,
            query_text=query_text,
            query_key=query_key,
            limit=limit,
            **routing,
        )
        candidates = result.get("candidates", [])
        if not isinstance(candidates, list):
            return []
        return _normalize_ticket_items([item for item in candidates if isinstance(item, dict)])

    def list_tickets(self, *, provider: str, limit: int = 20) -> list[dict[str, Any]]:
        """Browse visible tickets and return the normalized CLI ticket shape."""
        routing = self._routing_for_provider(provider)
        result = self._client.list_tickets(provider, limit=limit, **routing)
        tickets = result.get("tickets", [])
        if not isinstance(tickets, list):
            return []
        return _normalize_ticket_items([item for item in tickets if isinstance(item, dict)])

    # ------------------------------------------------------------------
    # Hard-fails: operations not supported for SaaS-backed providers
    # ------------------------------------------------------------------

    def map_add(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Always fails -- mappings for SaaS providers are dashboard-managed."""
        raise TrackerServiceError("Mappings for SaaS-backed providers are managed in the Spec Kitty dashboard. Use the web interface to create or edit mappings.")

    def sync_publish(self, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG002
        """Always fails -- snapshot publish is not supported for SaaS providers."""
        raise TrackerServiceError(
            "Snapshot publish is not supported for SaaS-backed providers. Use `spec-kitty tracker sync push` to push changes through the SaaS control plane."
        )
