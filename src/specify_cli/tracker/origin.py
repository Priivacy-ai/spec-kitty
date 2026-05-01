"""Service-layer orchestration for ticket-first mission origin binding.

Provides three public entry points consumed by ``/spec-kitty.specify``
and agent workflows:

* :func:`search_origin_candidates` -- search for candidate external issues
* :func:`bind_mission_origin` -- persist origin binding (SaaS-first, local-second)
* :func:`start_mission_from_ticket` -- create a mission from a confirmed ticket

All errors surface as :class:`OriginBindingError`.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from specify_cli.core.paths import locate_project_root
from specify_cli.mission_metadata import load_meta, set_origin_ticket
from specify_cli.tracker.config import TrackerProjectConfig, load_tracker_config
from specify_cli.tracker.origin_models import (
    MissionFromTicketResult,
    OriginCandidate,
    SearchOriginResult,
)
from specify_cli.tracker.saas_client import SaaSTrackerClient, SaaSTrackerClientError

logger = logging.getLogger(__name__)

# Re-export dataclasses for public API surface
__all__ = [
    "MissionFromTicketResult",
    "OriginBindingError",
    "OriginCandidate",
    "SearchOriginResult",
    "bind_mission_origin",
    "search_origin_candidates",
    "start_mission_from_ticket",
]

# Providers that support origin binding (C-001: only Jira and Linear in v1)
_ORIGIN_PROVIDERS: frozenset[str] = frozenset({"jira", "linear"})


class OriginBindingError(RuntimeError):
    """Raised when origin binding operations fail."""


# ---------------------------------------------------------------------------
# Slug derivation
# ---------------------------------------------------------------------------

_SLUG_SANITIZE_RE = re.compile(r"[^a-z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _derive_slug_from_ticket(candidate: OriginCandidate) -> str:
    """Derive a kebab-case feature slug from the ticket key.

    Rules (per research R5):
    - Use ``external_issue_key`` lowercased as the slug base
    - Sanitize to kebab-case: replace non-alphanumeric with hyphens,
      collapse consecutive hyphens, strip leading/trailing hyphens
    - Fall back to sanitized title (first 5 words) if key sanitizes empty
    """
    raw = candidate.external_issue_key.lower()
    slug = _SLUG_SANITIZE_RE.sub("-", raw).strip("-")

    if not slug:
        # Fall back to sanitized title (first 5 words)
        words = candidate.title.lower().split()[:5]
        raw_title = " ".join(words)
        slug = _SLUG_SANITIZE_RE.sub("-", raw_title).strip("-")

    if not slug:
        slug = "untitled"

    return slug


def _normalize_summary_text(value: str) -> str:
    """Collapse whitespace into a stable single-paragraph representation."""
    return _WHITESPACE_RE.sub(" ", value or "").strip()


def _derive_ticket_summary(candidate: OriginCandidate) -> tuple[str, str, str]:
    """Return mission presentation fields derived deterministically from a ticket."""
    friendly_name = _normalize_summary_text(candidate.title)
    if not friendly_name:
        raise OriginBindingError("Ticket-first mission creation requires a non-empty ticket title.")

    purpose_tldr = friendly_name

    body = candidate.body or ""
    paragraphs = [
        _normalize_summary_text(chunk)
        for chunk in re.split(r"\n\s*\n", body)
        if _normalize_summary_text(chunk)
    ]
    purpose_context = next((paragraph for paragraph in paragraphs if len(paragraph) >= 24), "")
    if not purpose_context:
        raise OriginBindingError(
            "Ticket-first mission creation requires ticket body text with at least one non-empty explanatory paragraph."
        )

    return friendly_name, purpose_tldr, purpose_context


# ---------------------------------------------------------------------------
# search_origin_candidates
# ---------------------------------------------------------------------------


def search_origin_candidates(
    repo_root: Path,
    query_text: str | None = None,
    query_key: str | None = None,
    limit: int = 10,
    *,
    client: SaaSTrackerClient | None = None,
) -> SearchOriginResult:
    """Search for candidate external issues to use as mission origin.

    Parameters
    ----------
    repo_root:
        Project root containing ``.kittify/config.yaml``.
    query_text:
        Free-text search query.
    query_key:
        Explicit ticket key (e.g. ``"WEB-123"``).  Takes precedence
        over *query_text* when both are provided.
    limit:
        Maximum number of candidates to return.
    client:
        Optional injected client for testability.  Defaults to a new
        ``SaaSTrackerClient()``.

    Returns
    -------
    SearchOriginResult
        Structured search result with candidates and routing context.

    Raises
    ------
    OriginBindingError
        On any configuration, transport, or authorization failure.
    """
    # 1. Load tracker config
    tracker_config = load_tracker_config(repo_root)
    if not tracker_config.provider or not tracker_config.project_slug:
        raise OriginBindingError("No tracker bound. Run `spec-kitty tracker bind` first.")

    provider = tracker_config.provider
    project_slug = tracker_config.project_slug

    # 2. Validate provider is jira or linear (C-001)
    if provider not in _ORIGIN_PROVIDERS:
        raise OriginBindingError(f"Only Jira and Linear providers support origin binding. Current provider: {provider}")

    # 3. Call SaaS
    actual_client = client or SaaSTrackerClient()
    try:
        response = actual_client.search_issues(
            provider,
            project_slug,
            query_text=query_text,
            query_key=query_key,
            limit=limit,
        )
    except SaaSTrackerClientError as exc:
        raise OriginBindingError(str(exc)) from exc

    # 4. Convert response to SearchOriginResult
    candidates = [
        OriginCandidate(
            external_issue_id=c["external_issue_id"],
            external_issue_key=c["external_issue_key"],
            title=c["title"],
            status=c["status"],
            url=c["url"],
            match_type=c.get("match_type", "text"),
            body=c.get("body"),
        )
        for c in response.get("candidates", [])
    ]

    query_used = query_key or query_text or ""

    return SearchOriginResult(
        candidates=candidates,
        provider=provider,
        resource_type=response.get("resource_type", ""),
        resource_id=response.get("resource_id", ""),
        query_used=query_used,
    )


# ---------------------------------------------------------------------------
# bind_mission_origin
# ---------------------------------------------------------------------------


def bind_mission_origin(
    feature_dir: Path,
    candidate: OriginCandidate,
    provider: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    *,
    client: SaaSTrackerClient | None = None,
) -> tuple[dict[str, Any], bool]:
    """Bind an origin ticket to a mission. SaaS-first, local-second.

    **CRITICAL**: The SaaS call is the authoritative write. If it fails,
    no local state is written. The service MUST NOT inspect local
    meta.json to short-circuit the SaaS bind.

    Parameters
    ----------
    feature_dir:
        Path to the feature directory containing ``meta.json``.
    candidate:
        The confirmed origin candidate.
    provider:
        Tracker provider (``"jira"`` or ``"linear"``).
    resource_type:
        Resource type (e.g. ``"linear_team"``, ``"jira_project"``).
    resource_id:
        Resource identifier.
    client:
        Optional injected client for testability.

    Returns
    -------
    tuple[dict, bool]
        (Updated meta.json contents, whether MissionOriginBound event was emitted).

    Raises
    ------
    OriginBindingError
        On SaaS failure, missing metadata, or write failure.
    """
    # 1. Load meta.json to get mission identity (needed for SaaS call)
    meta = load_meta(feature_dir)
    if meta is None:
        raise OriginBindingError(f"No meta.json found in {feature_dir}")
    mission_id = str(meta.get("mission_id") or "").strip()
    mission_slug = meta.get("mission_slug")
    if not mission_id:
        raise OriginBindingError(f"meta.json in {feature_dir} missing mission_id")
    if not mission_slug:
        raise OriginBindingError(f"meta.json in {feature_dir} missing mission_slug")

    # 2. Resolve routing + local resource context from tracker config
    #    Walk up from feature_dir to find .kittify/config.yaml
    repo_root = _resolve_repo_root(feature_dir)
    actual_client = client or SaaSTrackerClient()
    tracker_config = _resolve_tracker_config_for_origin(
        repo_root=repo_root,
        provider=provider,
        client=actual_client,
    )
    project_slug = tracker_config.project_slug
    binding_ref = tracker_config.binding_ref
    resolved_resource_type, resolved_resource_id = _resolve_origin_resource_context(
        provider=provider,
        tracker_config=tracker_config,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    # 3. Call SaaS FIRST — if this fails, STOP. No local state written.
    try:
        actual_client.bind_mission_origin(
            provider,
            project_slug,
            binding_ref=binding_ref,
            mission_id=mission_id,
            mission_slug=mission_slug,
            external_issue_id=candidate.external_issue_id,
            external_issue_key=candidate.external_issue_key,
            external_issue_url=candidate.url,
            title=candidate.title,
            external_status=candidate.status,
        )
    except SaaSTrackerClientError as exc:
        raise OriginBindingError(str(exc)) from exc

    # 4. Build origin_ticket dict from candidate + routing context
    origin_ticket: dict[str, Any] = {
        "provider": provider,
        "resource_type": resolved_resource_type,
        "resource_id": resolved_resource_id,
        "external_issue_id": candidate.external_issue_id,
        "external_issue_key": candidate.external_issue_key,
        "external_issue_url": candidate.url,
        "title": candidate.title,
    }

    # 5. Write to meta.json (local-second)
    updated_meta = set_origin_ticket(feature_dir, origin_ticket)

    # 6. Emit MissionOriginBound event (fire-and-forget, lazy import)
    event_emitted = False
    try:
        from specify_cli.sync.events import get_emitter

        emitter = get_emitter()
        emitter.emit_mission_origin_bound(
            mission_slug=mission_slug,
            provider=provider,
            external_issue_id=candidate.external_issue_id,
            external_issue_key=candidate.external_issue_key,
            external_issue_url=candidate.url,
            title=candidate.title,
            mission_id=meta.get("mission_id"),
        )
        event_emitted = True
    except Exception:
        logger.debug("MissionOriginBound event emission failed", exc_info=True)

    # 7. Return updated meta dict and event status
    return updated_meta, event_emitted


# ---------------------------------------------------------------------------
# start_mission_from_ticket
# ---------------------------------------------------------------------------


def start_mission_from_ticket(
    repo_root: Path,
    candidate: OriginCandidate,
    provider: str,
    resource_type: str,
    resource_id: str,
    mission_type: str = "software-dev",
    *,
    client: SaaSTrackerClient | None = None,
) -> MissionFromTicketResult:
    """Create a mission from a confirmed external ticket.

    Parameters
    ----------
    repo_root:
        Project root.
    candidate:
        Confirmed origin candidate.
    provider:
        Tracker provider.
    resource_type:
        Resource type.
    resource_id:
        Resource identifier.
    mission_type:
        Mission key (default ``"software-dev"``).
    client:
        Optional injected client for testability.

    Returns
    -------
    MissionFromTicketResult
        Structured result with feature_dir, slug, origin metadata,
        and event emission status.

    Raises
    ------
    OriginBindingError
        On creation or binding failure.
    """
    from specify_cli.core.mission_creation import (
        MissionCreationError,
        create_mission_core,
    )

    # 1. Derive slug from candidate
    slug = _derive_slug_from_ticket(candidate)
    friendly_name, purpose_tldr, purpose_context = _derive_ticket_summary(candidate)

    # 2. Create feature
    try:
        creation_result = create_mission_core(
            repo_root,
            slug,
            mission=mission_type,
            target_branch=None,
            friendly_name=friendly_name,
            purpose_tldr=purpose_tldr,
            purpose_context=purpose_context,
        )
    except MissionCreationError as exc:
        raise OriginBindingError(str(exc)) from exc

    # 3. Bind origin (SaaS-first, local-second)
    try:
        updated_meta, event_emitted = bind_mission_origin(
            creation_result.feature_dir,
            candidate,
            provider,
            resource_type,
            resource_id,
            client=client,
        )
        origin_ticket: dict[str, str] = updated_meta.get("origin_ticket", {})
    except OriginBindingError:
        # Feature exists but has no origin. Acceptable -- agent can retry
        # the bind separately. Re-raise so caller knows.
        raise

    return MissionFromTicketResult(
        feature_dir=creation_result.feature_dir,
        mission_slug=creation_result.mission_slug,
        origin_ticket=origin_ticket,
        event_emitted=event_emitted,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_repo_root(feature_dir: Path) -> Path:
    """Walk up from feature_dir to find the repo root (.kittify/ parent)."""
    resolved = feature_dir.resolve()

    for parent in [resolved.parent, *resolved.parents]:
        if parent.name == "kitty-specs":
            repo_root = parent.parent
            if (repo_root / ".kittify").is_dir():
                return repo_root

    # Feature directories also contain a local ``.kittify`` directory, so
    # prefer the real project root resolver before falling back to heuristics.
    project_root = locate_project_root(resolved)
    if project_root is not None:
        return project_root

    # Fall back: assume feature_dir is inside kitty-specs/<slug>/
    # so repo_root is two levels up
    return resolved.parent.parent


def _project_identity_payload(repo_root: Path) -> dict[str, Any]:
    """Build the SaaS project-identity payload for bind resolution calls."""
    from specify_cli.identity.project import ensure_identity

    identity = ensure_identity(repo_root)
    return {
        "uuid": str(identity.project_uuid),
        "slug": identity.project_slug,
        "node_id": identity.node_id,
        "repo_slug": identity.repo_slug,
        "build_id": identity.build_id,
    }


def _resolve_tracker_config_for_origin(
    *,
    repo_root: Path,
    provider: str,
    client: SaaSTrackerClient,
) -> TrackerProjectConfig:
    """Resolve hosted routing for mission-origin binding.

    Preference order:
    1. Local tracker config when it already routes to the requested provider.
    2. Hosted bind-resolve/bind-validate for the current project identity.

    This lets ticket-origin flows work from repos that are remotely mapped in
    SaaS but have not yet persisted a local ``tracker:`` block in
    ``.kittify/config.yaml``.
    """
    tracker_config = load_tracker_config(repo_root)
    if tracker_config.provider and tracker_config.provider != provider:
        raise OriginBindingError(
            f"This repo is bound to '{tracker_config.provider}', not '{provider}'. "
            f"Run `spec-kitty tracker bind --provider {provider}`."
        )
    if tracker_config.provider == provider and (
        tracker_config.binding_ref or tracker_config.project_slug
    ):
        return tracker_config

    project_identity = _project_identity_payload(repo_root)
    try:
        resolution = client.bind_resolve(provider, project_identity)
    except SaaSTrackerClientError as exc:
        raise OriginBindingError(str(exc)) from exc

    binding_ref = resolution.get("binding_ref")
    project_slug = resolution.get("project_slug")
    if resolution.get("match_type") != "exact" or not (binding_ref or project_slug):
        raise OriginBindingError("No tracker bound. Run `spec-kitty tracker bind` first.")

    provider_context: dict[str, str] | None = None
    display_label = resolution.get("display_label")
    if binding_ref:
        try:
            validation = client.bind_validate(provider, binding_ref, project_identity)
        except SaaSTrackerClientError as exc:
            raise OriginBindingError(str(exc)) from exc
        validation_context = validation.get("provider_context")
        if isinstance(validation_context, dict):
            provider_context = {
                str(key): str(value)
                for key, value in validation_context.items()
            }
        if validation.get("display_label"):
            display_label = validation["display_label"]

    return TrackerProjectConfig(
        provider=provider,
        binding_ref=str(binding_ref).strip() if binding_ref else None,
        project_slug=str(project_slug).strip() if project_slug else None,
        display_label=str(display_label).strip() if isinstance(display_label, str) and display_label.strip() else None,
        provider_context=provider_context,
    )


def _resolve_origin_resource_context(
    *,
    provider: str,
    tracker_config: TrackerProjectConfig,
    resource_type: str | None,
    resource_id: str | None,
) -> tuple[str, str]:
    """Resolve local origin_ticket routing context.

    The authoritative SaaS bind call routes by ``binding_ref`` or ``project_slug``.
    ``resource_type`` / ``resource_id`` are kept locally for provenance and may need
    to be derived from the persisted tracker config when the caller does not have an
    explicit discovery response in hand.
    """
    explicit_type = (resource_type or "").strip()
    explicit_id = (resource_id or "").strip()
    if explicit_type and explicit_id:
        return explicit_type, explicit_id

    provider_context = tracker_config.provider_context or {}

    if provider == "linear":
        return (
            explicit_type or "linear_team",
            explicit_id
            or provider_context.get("workspace_id")
            or provider_context.get("team_id")
            or tracker_config.binding_ref
            or tracker_config.project_slug
            or "",
        )

    if provider == "jira":
        return (
            explicit_type or "jira_project",
            explicit_id
            or provider_context.get("project_key")
            or provider_context.get("key")
            or tracker_config.binding_ref
            or tracker_config.project_slug
            or "",
        )

    if provider == "github":
        return (
            explicit_type or "github_repo",
            explicit_id
            or provider_context.get("repository")
            or provider_context.get("repo")
            or tracker_config.binding_ref
            or tracker_config.project_slug
            or "",
        )

    if provider == "gitlab":
        return (
            explicit_type or "gitlab_project",
            explicit_id
            or provider_context.get("project_path")
            or provider_context.get("project_id")
            or tracker_config.binding_ref
            or tracker_config.project_slug
            or "",
        )

    return explicit_type, explicit_id
