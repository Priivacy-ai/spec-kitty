---
work_package_id: WP02
title: Widen Data Models + Prereq Checker
dependencies:
- WP01
requirement_refs:
- C-005
- C-007
- C-009
- FR-003
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T015
agent: "claude:sonnet-4-7:python-reviewer:reviewer"
shell_pid: "70540"
history:
- date: '2026-04-23T15:43:52Z'
  event: created
agent_profile: python-implementer
authoritative_surface: src/specify_cli/widen/
execution_mode: code_change
mission_slug: cli-widen-mode-and-write-back-01KPXFGJ
model: claude-sonnet-4-7
owned_files:
- src/specify_cli/widen/__init__.py
- src/specify_cli/widen/models.py
- src/specify_cli/widen/prereq.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-implementer
```

---

## Objective

Create the `src/specify_cli/widen/` package skeleton and define all shared data models (enums, dataclasses, Pydantic models) plus the `check_prereqs()` function that determines whether `[w]iden` is shown to the user.

---

## Context

All shapes are CLI-side only. SaaS-side schemas are owned by spec-kitty-saas #110 and #111. Every Pydantic model uses:
```python
from pydantic import BaseModel, ConfigDict
model_config = ConfigDict(frozen=True, extra="forbid")
```
All modules use `from __future__ import annotations`.

The `check_prereqs()` function must be fast (three parallel or sequential 500ms probes), non-fatal (catches all `SaasClientError`), and must return `PrereqState(all_satisfied=False)` when `SPEC_KITTY_SAAS_TOKEN` is absent — silently, no error banner (C-009).

---

## Branch Strategy

Depends on WP01. Implementation command:
```bash
spec-kitty agent action implement WP02 --agent claude
```

---

## Subtask T006 — Create `widen/` Package Skeleton

**Purpose:** Establish package init with clean public API re-exports.

**Files to create:**
- `src/specify_cli/widen/__init__.py`
- `src/specify_cli/widen/models.py` (stub)
- `src/specify_cli/widen/prereq.py` (stub)
- `src/specify_cli/widen/audience.py` (stub — implemented in WP04)
- `src/specify_cli/widen/review.py` (stub — implemented in WP07)
- `src/specify_cli/widen/state.py` (stub — implemented in WP03)
- `src/specify_cli/widen/flow.py` (stub — implemented in WP05)

**`__init__.py` re-exports:**
```python
from specify_cli.widen.models import (
    SummarySource,
    PrereqState,
    WidenAction,
    WidenFlowResult,
    WidenPendingEntry,
    DiscussionFetch,
    CandidateReview,
    WidenResponse,
)
from specify_cli.widen.prereq import check_prereqs

__all__ = [
    "SummarySource", "PrereqState", "WidenAction", "WidenFlowResult",
    "WidenPendingEntry", "DiscussionFetch", "CandidateReview", "WidenResponse",
    "check_prereqs",
]
```

---

## Subtask T007 — `SummarySource` Enum + `PrereqState` Dataclass

**Purpose:** Define the two foundational non-Pydantic types used throughout the widen flow.

**File:** `src/specify_cli/widen/models.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum

class SummarySource(StrEnum):
    SLACK_EXTRACTION = "slack_extraction"
    MISSION_OWNER_OVERRIDE = "mission_owner_override"
    MANUAL = "manual"

@dataclass(frozen=True)
class PrereqState:
    teamspace_ok: bool
    slack_ok: bool
    saas_reachable: bool

    @property
    def all_satisfied(self) -> bool:
        return self.teamspace_ok and self.slack_ok and self.saas_reachable
```

**Constraint C-005:** `SummarySource` contains exactly three values. No additions without a spec change.

---

## Subtask T008 — `WidenAction` Enum + `WidenFlowResult` Dataclass

**Purpose:** Return type for `WidenFlow.run_widen_mode()` — communicates outcome back to the interview loop.

**File:** `src/specify_cli/widen/models.py` (same file, add below T007 shapes)

```python
class WidenAction(StrEnum):
    BLOCK = "block"       # User chose [b]; interview paused at this question
    CONTINUE = "continue" # User chose [c]; question parked as pending-external-input
    CANCEL = "cancel"     # User canceled mid-Widen Mode; no widen call made

@dataclass(frozen=True)
class WidenFlowResult:
    action: WidenAction
    decision_id: str | None = None   # Set if widen POST succeeded (BLOCK or CONTINUE)
    invited: list[str] | None = None # Trimmed invite list sent to SaaS
```

---

## Subtask T009 — `WidenPendingEntry` Pydantic Model

**Purpose:** The shape of each line in `widen-pending.jsonl`. Frozen, strict, with `schema_version=1`.

**File:** `src/specify_cli/widen/models.py`

```python
from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict

class WidenPendingEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = 1
    decision_id: str
    mission_slug: str
    question_id: str
    question_text: str
    entered_pending_at: datetime
    widen_endpoint_response: dict[str, Any]
```

**Sidecar file path:** `kitty-specs/<mission_slug>/widen-pending.jsonl`.
Serialization: `entry.model_dump_json()` writes one JSON line. Deserialization: `WidenPendingEntry.model_validate_json(line)`.

---

## Subtask T010 — `DiscussionFetch` + `CandidateReview` Pydantic Models

**Purpose:** In-memory shapes used during the candidate review step. Not persisted to disk.

**File:** `src/specify_cli/widen/models.py`

```python
class DiscussionFetch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    participants: list[str]
    message_count: int
    thread_url: str | None
    messages: list[str]   # Capped at 50 for V1 (context-window limit)
    truncated: bool = False

class CandidateReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str
    discussion_fetch: DiscussionFetch
    candidate_summary: str
    candidate_answer: str
    source_hint: SummarySource
    llm_timed_out: bool = False

class WidenResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")  # extra=allow for future #110 fields

    decision_id: str
    widened_at: datetime
    slack_thread_url: str | None = None
    invited_count: int | None = None
```

**`CandidateReview` validation:** `source_hint` must be one of the two LLM-emitted values (`slack_extraction` or `manual`). The final `summary_json.source` written on resolve may differ based on owner editing (see data-model.md §4 provenance rules).

---

## Subtask T015 — Implement `check_prereqs()`

**Purpose:** The three-condition prereq check that determines whether `[w]iden` is shown. Must complete in ≤300ms combined at p95 (NFR-001).

**File:** `src/specify_cli/widen/prereq.py`

```python
from __future__ import annotations
import contextlib
from specify_cli.saas_client import SaasClient, SaasClientError
from specify_cli.widen.models import PrereqState

def check_prereqs(saas_client: SaasClient, team_slug: str) -> PrereqState:
    """Check all three prereqs synchronously with short timeouts.

    Returns PrereqState. Never raises — all failures produce False flags.
    """
    teamspace_ok = _check_teamspace(saas_client)
    slack_ok = _check_slack(saas_client, team_slug) if teamspace_ok else False
    saas_reachable = _check_health(saas_client)
    return PrereqState(
        teamspace_ok=teamspace_ok,
        slack_ok=slack_ok,
        saas_reachable=saas_reachable,
    )

def _check_teamspace(client: SaasClient) -> bool:
    """Teamspace membership derived from token presence (auth context check).
    If token is present and valid, the user is considered a Teamspace member.
    Returns False if SaasAuthError or any error."""
    with contextlib.suppress(SaasClientError, Exception):
        # A non-raising health probe + presence of a valid token = teamspace_ok
        return bool(client._token)
    return False

def _check_slack(client: SaasClient, team_slug: str) -> bool:
    """GET /api/v1/teams/{slug}/integrations. Returns True if 'slack' in list."""
    with contextlib.suppress(SaasClientError, Exception):
        integrations = client.get_team_integrations(team_slug)
        return "slack" in integrations
    return False

def _check_health(client: SaasClient) -> bool:
    """GET /api/v1/health. Returns True if reachable."""
    return client.health_probe()
```

**Important:** Call site in charter.py wraps this in a broad try/except with a fallback `PrereqState(False, False, False)` to handle import errors or unexpected exceptions. The interview must never crash due to a prereq check failure (C-007).

**`team_slug` source:** extracted from `AuthContext.team_slug` (decoded from token payload or from saas-auth.json). If `team_slug` is `None`, pass an empty string — `_check_slack` will catch `SaasNotFoundError` and return `False`.

---

## Definition of Done

- [ ] `src/specify_cli/widen/` package with 7 files exists (5 stubs + `models.py` + `prereq.py` implemented).
- [ ] All models match `data-model.md` exactly (field names, types, frozen=True).
- [ ] `SummarySource` has exactly 3 values (C-005).
- [ ] `check_prereqs()` returns `PrereqState(all_satisfied=False)` when token absent.
- [ ] `tests/specify_cli/widen/test_prereq.py` has stubs (full tests in WP10).
- [ ] `mypy src/specify_cli/widen/models.py src/specify_cli/widen/prereq.py` exits 0.
- [ ] `ruff check src/specify_cli/widen/` exits 0.

## Risks

- **`StrEnum` availability:** Python 3.11+ only. The codebase targets 3.11+ (plan.md §1) so this is fine. If a 3.10 CI runner exists, use `str, Enum` base instead.
- **Circular imports:** `widen/models.py` must not import from `saas_client` (use forward references or TypedDicts for SaaS response shapes). Keep models self-contained.

## Reviewer Guidance

Check that `PrereqState.all_satisfied` is a `@property` not a field. Verify `WidenPendingEntry` is consistent with `contracts/widen-state.schema.json`. Verify `CandidateReview.source_hint` only accepts `slack_extraction` and `manual` (not `mission_owner_override` which is a resolved provenance, not an LLM-emitted hint).

## Activity Log

- 2026-04-23T16:14:55Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=70011 – Started implementation via action command
- 2026-04-23T16:18:00Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=70011 – Ready for review: widen/ package skeleton with data models (SummarySource, PrereqState, WidenAction, WidenFlowResult, WidenPendingEntry, DiscussionFetch, CandidateReview, WidenResponse) and prereq checker; ruff/mypy clean; 7 tests passing
- 2026-04-23T16:18:46Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=70540 – Started review via action command
- 2026-04-23T16:20:37Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=70540 – Review passed: all models match data-model.md exactly; PrereqState.all_satisfied is @property not field; WidenResponse uses extra=allow; _check_health correctly delegates to health_probe() which is never-raise per WP01 contract; 7 active tests cover all 4 prereq failure shapes + both all_satisfied paths + property invariant; stub modules are inert; ruff/mypy clean.
