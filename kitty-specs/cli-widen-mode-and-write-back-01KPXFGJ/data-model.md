# Data Model — CLI Widen Mode & Decision Write-Back

**Mission:** `cli-widen-mode-and-write-back-01KPXFGJ`

All models are CLI-side only. SaaS-side schemas are owned by spec-kitty-saas #110 and #111.

---

## 1. `PrereqState` (in-memory only)

Produced by `specify_cli.widen.prereq.check_prereqs()`. Not persisted; recomputed at interview start and cached for the session.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PrereqState:
    teamspace_ok: bool      # User is a member of at least one Teamspace
    slack_ok: bool          # Team has Slack integration configured
    saas_reachable: bool    # SaaS health probe succeeded

    @property
    def all_satisfied(self) -> bool:
        return self.teamspace_ok and self.slack_ok and self.saas_reachable
```

**Usage:** `[w]` is shown in the prompt iff `prereq_state.all_satisfied is True` (FR-003, C-009).

---

## 2. `WidenPendingEntry` (in-memory + sidecar JSONL)

Represents a single widened DecisionPoint that is in `pending-external-input` state: the owner chose `[c]`ontinue and the interview moved past this question (FR-009).

```python
from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict

class WidenPendingEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = 1
    decision_id: str                        # ULID of the DecisionPoint
    mission_slug: str                       # e.g. "cli-widen-mode-and-write-back-01KPXFGJ"
    question_id: str                        # e.g. "charter.project_name"
    question_text: str                      # Human-readable question
    entered_pending_at: datetime            # When user pressed [c]
    widen_endpoint_response: dict[str, Any] # Raw response from POST /widen (for debug)
```

### Sidecar File Format

**Path:** `kitty-specs/<mission_slug>/widen-pending.jsonl`

One `WidenPendingEntry` serialized to JSON per line. Lines are appended when entries are added and the file is rewritten (compact) when entries are removed. Empty file = no pending entries.

**Example line:**
```json
{"schema_version": 1, "decision_id": "01KPXFGJXXCV25X3T9DWGME5V1", "mission_slug": "my-mission-01ABC", "question_id": "charter.technical_constraints", "question_text": "What are the technical constraints?", "entered_pending_at": "2026-04-23T16:00:00+00:00", "widen_endpoint_response": {"widened_at": "2026-04-23T16:00:01+00:00", "slack_thread_url": "https://..."}}
```

**Invariants:**
- `decision_id` is unique per file (duplicate widen on same decision is disallowed — C-010).
- Entries are removed after successful resolution or explicit defer.
- A missing file is equivalent to an empty file (no pending entries).

---

## 3. `CandidateReview` (in-memory during review)

Produced by `specify_cli.widen.review.run_candidate_review()` after the active LLM session returns the summarization JSON block (R-7). Passed to the `[a/e/d]` handler.

```python
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from specify_cli.widen.models import SummarySource

class DiscussionFetch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    participants: list[str]
    message_count: int
    thread_url: str | None
    messages: list[str]         # Compact message list (capped at 50 for V1)
    truncated: bool = False     # True if >50 messages were truncated

class CandidateReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str
    discussion_fetch: DiscussionFetch
    candidate_summary: str          # Produced by local LLM (or empty on fallback)
    candidate_answer: str           # Produced by local LLM (or empty on fallback)
    source_hint: SummarySource      # "slack_extraction" | "manual"
    llm_timed_out: bool = False     # True if fallback was triggered
```

**Note:** `source_hint` is the initial hint from the LLM. The actual `summary_json.source` written on resolve may differ based on owner editing (see §4 provenance rules).

---

## 4. `SummarySource` Enum (provenance)

Restricted to three values per C-005. These are the values written to `summary_json.source` when calling `decision resolve`.

```python
from enum import StrEnum

class SummarySource(StrEnum):
    SLACK_EXTRACTION = "slack_extraction"
    # Owner accepted the LLM-produced candidate summary and answer as-is,
    # or made only minor non-material edits.

    MISSION_OWNER_OVERRIDE = "mission_owner_override"
    # Owner pressed [e] and materially changed the LLM-produced candidate
    # (Levenshtein distance above threshold, or key fields changed).

    MANUAL = "manual"
    # Owner wrote the summary/answer from scratch:
    # - Discussion fetch failed (edge case from spec.md)
    # - LLM summarization timed out (edge case)
    # - Owner deleted the candidate pre-fill entirely and typed fresh
    # - Owner used plain-text local answer at blocked prompt (FR-018)
```

### Provenance Assignment Rules

| Scenario | `summary_json.source` |
|---|---|
| `[a]ccept` — candidate accepted unchanged | `slack_extraction` |
| `[e]dit` — minor formatting change only | `slack_extraction` |
| `[e]dit` — material content change (>threshold) | `mission_owner_override` |
| `[e]dit` — owner deleted all pre-fill and wrote fresh | `manual` |
| LLM timed out, editor blank → owner typed fresh | `manual` |
| Discussion fetch failed, editor blank → owner typed | `manual` |
| Plain-text answer at blocked prompt (FR-018) | `manual` (with empty `summary_json.text`) |

Material edit threshold (implementation detail): normalized edit distance > 30% of the candidate length, OR the edit result is empty (user deleted everything). This threshold may be tuned.

**C-006 constraint:** `rationale` is always owner-authored. The CLI never auto-populates `rationale` from a discussion summary, even if the candidate summary is accepted unchanged.

---

## 5. `WidenFlowResult` (in-memory)

Returned by `specify_cli.widen.flow.WidenFlow.run_widen_mode()` to the interview loop.

```python
from enum import StrEnum
from dataclasses import dataclass

class WidenAction(StrEnum):
    BLOCK = "block"         # User chose [b]; interview paused at this question
    CONTINUE = "continue"   # User chose [c]; question parked as pending-external-input
    CANCEL = "cancel"       # User canceled mid-Widen Mode; no widen call made

@dataclass(frozen=True)
class WidenFlowResult:
    action: WidenAction
    decision_id: str | None = None   # Set if widen POST succeeded (BLOCK or CONTINUE)
    invited: list[str] | None = None # Trimmed invite list sent to SaaS
```

---

## 6. `WidenResponse` (SaaS response, in-memory)

Thin wrapper around the `POST /api/v1/decision-points/{id}/widen` response from spec-kitty-saas #110. Stored in `WidenPendingEntry.widen_endpoint_response` for debug purposes.

```python
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class WidenResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")  # extra=allow for future fields

    decision_id: str
    widened_at: datetime
    slack_thread_url: str | None = None
    invited_count: int | None = None
```

---

## 7. Sidecar File Schema Summary

| File | Format | Location | Owned by |
|---|---|---|---|
| `widen-pending.jsonl` | JSONL (`WidenPendingEntry` per line) | `kitty-specs/<slug>/` | `specify_cli.widen.state.WidenPendingStore` |

No other new persistent files. The existing `kitty-specs/<slug>/decisions/` artifacts (from #757) are unchanged.
