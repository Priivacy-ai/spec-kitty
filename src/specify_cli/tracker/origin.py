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

from specify_cli.feature_metadata import load_meta, set_origin_ticket
from specify_cli.tracker.config import load_tracker_config
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
        raise OriginBindingError(
            "No tracker bound. Run `spec-kitty tracker bind` first."
        )

    provider = tracker_config.provider
    project_slug = tracker_config.project_slug

    # 2. Validate provider is jira or linear (C-001)
    if provider not in _ORIGIN_PROVIDERS:
        raise OriginBindingError(
            f"Only Jira and Linear providers support origin binding. "
            f"Current provider: {provider}"
        )

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
    resource_type: str,
    resource_id: str,
    *,
    client: SaaSTrackerClient | None = None,
) -> dict[str, Any]:
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
    dict
        Updated meta.json contents.

    Raises
    ------
    OriginBindingError
        On SaaS failure, missing metadata, or write failure.
    """
    # 1. Load meta.json to get feature_slug (needed for SaaS call)
    meta = load_meta(feature_dir)
    if meta is None:
        raise OriginBindingError(
            f"No meta.json found in {feature_dir}"
        )
    feature_slug = meta.get("feature_slug")
    if not feature_slug:
        raise OriginBindingError(
            f"meta.json in {feature_dir} missing feature_slug"
        )

    # 2. Resolve project_slug from tracker config
    #    Walk up from feature_dir to find .kittify/config.yaml
    repo_root = _resolve_repo_root(feature_dir)
    tracker_config = load_tracker_config(repo_root)
    project_slug = tracker_config.project_slug or ""

    # 3. Call SaaS FIRST — if this fails, STOP. No local state written.
    actual_client = client or SaaSTrackerClient()
    try:
        actual_client.bind_mission_origin(
            provider,
            project_slug,
            feature_slug=feature_slug,
            external_issue_id=candidate.external_issue_id,
            external_issue_key=candidate.external_issue_key,
            external_issue_url=candidate.url,
            title=candidate.title,
        )
    except SaaSTrackerClientError as exc:
        raise OriginBindingError(str(exc)) from exc

    # 4. Build origin_ticket dict from candidate + routing context
    origin_ticket: dict[str, Any] = {
        "provider": provider,
        "resource_type": resource_type,
        "resource_id": resource_id,
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
            feature_slug=feature_slug,
            provider=provider,
            external_issue_id=candidate.external_issue_id,
            external_issue_key=candidate.external_issue_key,
            external_issue_url=candidate.url,
            title=candidate.title,
        )
        event_emitted = True
    except Exception:
        logger.debug("MissionOriginBound event emission failed", exc_info=True)

    _ = event_emitted  # available for callers that care

    # 7. Return updated meta dict
    return updated_meta


# ---------------------------------------------------------------------------
# start_mission_from_ticket
# ---------------------------------------------------------------------------


def start_mission_from_ticket(
    repo_root: Path,
    candidate: OriginCandidate,
    provider: str,
    resource_type: str,
    resource_id: str,
    mission_key: str = "software-dev",
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
    mission_key:
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
    from specify_cli.core.feature_creation import (
        FeatureCreationError,
        create_feature_core,
    )

    # 1. Derive slug from candidate
    slug = _derive_slug_from_ticket(candidate)

    # 2. Create feature
    try:
        creation_result = create_feature_core(
            repo_root, slug, mission=mission_key, target_branch=None,
        )
    except FeatureCreationError as exc:
        raise OriginBindingError(str(exc)) from exc

    # 3. Bind origin (SaaS-first, local-second)
    event_emitted = False
    origin_ticket: dict[str, str] = {}
    try:
        updated_meta = bind_mission_origin(
            creation_result.feature_dir,
            candidate,
            provider,
            resource_type,
            resource_id,
            client=client,
        )
        origin_ticket = updated_meta.get("origin_ticket", {})
        event_emitted = True
    except OriginBindingError:
        # Feature exists but has no origin. Acceptable -- agent can retry
        # the bind separately. Re-raise so caller knows.
        raise

    return MissionFromTicketResult(
        feature_dir=creation_result.feature_dir,
        feature_slug=creation_result.feature_slug,
        origin_ticket=origin_ticket,
        event_emitted=event_emitted,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_repo_root(feature_dir: Path) -> Path:
    """Walk up from feature_dir to find the repo root (.kittify/ parent)."""
    current = feature_dir.resolve()
    for _ in range(20):  # safety bound
        if (current / ".kittify").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    # Fall back: assume feature_dir is inside kitty-specs/<slug>/
    # so repo_root is two levels up
    return feature_dir.parent.parent
