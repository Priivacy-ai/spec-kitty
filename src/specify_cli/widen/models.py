"""Data models for the CLI Widen Mode feature.

All shapes are CLI-side only. SaaS-side schemas are owned by spec-kitty-saas.
Every Pydantic model uses ConfigDict(frozen=True, extra="forbid") unless
noted otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# T007 — SummarySource enum + PrereqState dataclass
# ---------------------------------------------------------------------------


class SummarySource(StrEnum):
    """Provenance of a candidate summary.

    Restricted to exactly three values per C-005.
    """

    SLACK_EXTRACTION = "slack_extraction"
    """Owner accepted LLM-produced candidate summary/answer (as-is or minor edit)."""

    MISSION_OWNER_OVERRIDE = "mission_owner_override"
    """Owner pressed [e] and made a material content change."""

    MANUAL = "manual"
    """Owner wrote summary/answer from scratch (timeout, failed fetch, or fresh)."""


@dataclass(frozen=True)
class PrereqState:
    """Result of the three-condition prereq check.

    Produced by ``check_prereqs()``.  Not persisted; recomputed at interview
    start and cached for the session.
    """

    teamspace_ok: bool
    """User is a member of at least one Teamspace."""

    slack_ok: bool
    """Team has Slack integration configured."""

    saas_reachable: bool
    """SaaS health probe succeeded."""

    @property
    def all_satisfied(self) -> bool:
        """``True`` iff all three prereqs are met (FR-003, C-009)."""
        return self.teamspace_ok and self.slack_ok and self.saas_reachable


# ---------------------------------------------------------------------------
# T008 — WidenAction enum + WidenFlowResult dataclass
# ---------------------------------------------------------------------------


class WidenAction(StrEnum):
    """Outcome of a single widen-mode interaction."""

    BLOCK = "block"
    """User chose [b]; interview paused at this question."""

    CONTINUE = "continue"
    """User chose [c]; question parked as pending-external-input."""

    CANCEL = "cancel"
    """User canceled mid-Widen Mode; no widen call made."""


@dataclass(frozen=True)
class AudienceSelection:
    """Mission-owner-confirmed audience after review/trim.

    ``display_names`` are used for CLI rendering and paper trail text.
    ``user_ids`` are the SaaS wire payload for POST /widen.
    """

    display_names: list[str]
    user_ids: list[int]


@dataclass(frozen=True)
class WidenFlowResult:
    """Return type for ``WidenFlow.run_widen_mode()``.

    Communicates the widen outcome back to the interview loop.
    """

    action: WidenAction
    decision_id: str | None = None
    """Set if widen POST succeeded (BLOCK or CONTINUE)."""

    invited: list[str] | None = None
    """Trimmed invite list sent to SaaS."""


# ---------------------------------------------------------------------------
# T009 — WidenPendingEntry Pydantic model
# ---------------------------------------------------------------------------


class WidenPendingEntry(BaseModel):
    """Shape of each line in ``widen-pending.jsonl``.

    Sidecar file path: ``kitty-specs/<mission_slug>/widen-pending.jsonl``.

    Serialization: ``entry.model_dump_json()`` writes one JSON line.
    Deserialization: ``WidenPendingEntry.model_validate_json(line)``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = 1
    decision_id: str
    """ULID of the DecisionPoint."""

    mission_slug: str
    """e.g. 'cli-widen-mode-and-write-back-01KPXFGJ'."""

    question_id: str
    """e.g. 'charter.project_name'."""

    question_text: str
    """Human-readable question."""

    entered_pending_at: datetime
    """When user pressed [c]."""

    widen_endpoint_response: dict[str, Any]
    """Raw response from POST /widen (for debug)."""


# ---------------------------------------------------------------------------
# T010 — DiscussionFetch + CandidateReview + WidenResponse Pydantic models
# ---------------------------------------------------------------------------


class DiscussionFetch(BaseModel):
    """Fetched Slack discussion thread for a widened decision point.

    In-memory only — not persisted to disk.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    participants: list[str]
    message_count: int
    thread_url: str | None
    messages: list[str]
    """Compact message list (capped at 50 for V1 — context-window limit)."""

    truncated: bool = False
    """True if >50 messages were truncated."""


class CandidateReview(BaseModel):
    """LLM-produced candidate review for a widened decision point.

    Produced after the active LLM session returns the summarization JSON block.
    Passed to the ``[a/e/d]`` handler.  In-memory only — not persisted.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str
    discussion_fetch: DiscussionFetch
    candidate_summary: str
    """Produced by local LLM (or empty on fallback)."""

    candidate_answer: str
    """Produced by local LLM (or empty on fallback)."""

    source_hint: SummarySource
    """Initial hint from the LLM: 'slack_extraction' or 'manual'."""

    llm_timed_out: bool = False
    """True if fallback was triggered."""


class WidenResponse(BaseModel):
    """Thin wrapper around the ``POST /api/v1/decision-points/{id}/widen`` response.

    Stored in ``WidenPendingEntry.widen_endpoint_response`` for debug.
    Uses ``extra='allow'`` to accommodate future SaaS fields.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    decision_id: str
    widened_at: datetime
    slack_thread_url: str | None = None
    invited_count: int | None = None
