"""Pure data helpers for tracker binding discovery.

This module owns dataclasses for API response parsing and a candidate
lookup function.  It does NOT import rich, typer, or any terminal I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# BindableResource — a discovered tracker resource from the inventory API
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BindableResource:
    """A single resource from ``GET /api/v1/tracker/resources/``."""

    candidate_token: str
    display_label: str
    provider: str
    provider_context: dict[str, str]
    binding_ref: str | None = None
    bound_project_slug: str | None = None
    bound_at: str | None = None

    @property
    def is_bound(self) -> bool:
        return self.binding_ref is not None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BindableResource:
        return cls(
            candidate_token=data["candidate_token"],
            display_label=data["display_label"],
            provider=data["provider"],
            provider_context=data.get("provider_context", {}),
            binding_ref=data.get("binding_ref"),
            bound_project_slug=data.get("bound_project_slug"),
            bound_at=data.get("bound_at"),
        )


# ---------------------------------------------------------------------------
# BindCandidate — a ranked candidate from the bind-resolve API
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BindCandidate:
    """A single candidate from ``POST /api/v1/tracker/bind-resolve/``."""

    candidate_token: str
    display_label: str
    confidence: str  # "high", "medium", "low"
    match_reason: str
    sort_position: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BindCandidate:
        return cls(
            candidate_token=data["candidate_token"],
            display_label=data["display_label"],
            confidence=data["confidence"],
            match_reason=data["match_reason"],
            sort_position=data["sort_position"],
        )


# ---------------------------------------------------------------------------
# BindResult — response from bind-confirm
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BindResult:
    """Response from ``POST /api/v1/tracker/bind-confirm/``."""

    binding_ref: str
    display_label: str
    provider: str
    provider_context: dict[str, str]
    bound_at: str
    project_slug: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BindResult:
        return cls(
            binding_ref=data["binding_ref"],
            display_label=data["display_label"],
            provider=data["provider"],
            provider_context=data.get("provider_context", {}),
            bound_at=data["bound_at"],
            project_slug=data.get("project_slug") or None,
        )


# ---------------------------------------------------------------------------
# ValidationResult — response from bind-validate
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Response from ``POST /api/v1/tracker/bind-validate/``."""

    valid: bool
    binding_ref: str
    reason: str | None = None
    guidance: str | None = None
    display_label: str | None = None
    provider: str | None = None
    provider_context: dict[str, str] | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ValidationResult:
        return cls(
            valid=data["valid"],
            binding_ref=data["binding_ref"],
            reason=data.get("reason"),
            guidance=data.get("guidance"),
            display_label=data.get("display_label"),
            provider=data.get("provider"),
            provider_context=data.get("provider_context"),
        )


# ---------------------------------------------------------------------------
# ResolutionResult — response from bind-resolve
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    """Response from ``POST /api/v1/tracker/bind-resolve/``."""

    match_type: str  # "exact", "candidates", "none"
    candidate_token: str | None = None
    binding_ref: str | None = None
    display_label: str | None = None
    project_slug: str | None = None
    candidates: list[BindCandidate] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ResolutionResult:
        candidates = [
            BindCandidate.from_api(c) for c in data.get("candidates", [])
        ]
        return cls(
            match_type=data["match_type"],
            candidate_token=data.get("candidate_token"),
            binding_ref=data.get("binding_ref"),
            display_label=data.get("display_label"),
            project_slug=data.get("project_slug") or None,
            candidates=candidates,
        )


# ---------------------------------------------------------------------------
# Pure helper: candidate lookup by 1-based user selection
# ---------------------------------------------------------------------------


def find_candidate_by_position(
    candidates: list[BindCandidate], select_n: int
) -> BindCandidate | None:
    """Find candidate by 1-based selection number (maps to sort_position = N-1).

    Returns ``None`` if out of range or *candidates* is empty.
    """
    position = select_n - 1
    for candidate in candidates:
        if candidate.sort_position == position:
            return candidate
    return None
