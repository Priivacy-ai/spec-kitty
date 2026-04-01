"""Data models for ticket-first mission origin binding.

Provides three frozen/mutable dataclasses that represent external issue
candidates, search results, and the outcome of creating a mission from
an external ticket.  These models form the data foundation that downstream
work packages (WP02-WP05) depend on.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class OriginCandidate:
    """A candidate external issue returned by ticket search.

    All fields are non-empty strings.  ``match_type`` is ``"exact"`` when
    the candidate matched by ID/key, or ``"text"`` when matched by title
    similarity.
    """

    external_issue_id: str
    external_issue_key: str
    title: str
    status: str
    url: str
    match_type: str  # "exact" or "text"


@dataclass(frozen=True, slots=True)
class SearchOriginResult:
    """Result of an origin candidate search.

    Bundles the list of :class:`OriginCandidate` objects together with the
    routing context (provider, resource, query) that produced them.
    """

    candidates: list[OriginCandidate]
    provider: str  # "jira" or "linear"
    resource_type: str  # e.g., "linear_team", "jira_project"
    resource_id: str
    query_used: str


@dataclass(slots=True)
class MissionFromTicketResult:
    """Result of creating a mission from an external ticket.

    Not frozen because ``Path`` objects and the mutable nature of the
    result dict make immutability impractical.
    """

    feature_dir: Path
    feature_slug: str
    origin_ticket: dict[str, str]
    event_emitted: bool
