---
work_package_id: WP01
title: Status Models & Transition Matrix
lane: "for_review"
dependencies: []
base_branch: 2.x
base_commit: 7ba8f245c1d3bbcd59aa08059cc331c708fc1b79
created_at: '2026-02-08T14:27:11.108691+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-opus-reviewer"
shell_pid: "43865"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 -- Status Models & Transition Matrix

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No `--base` flag needed -- this is the foundation work package with no dependencies.

---

## Objectives & Success Criteria

Create the foundational data types and strict 7-lane transition matrix that every other work package depends on. This WP delivers:

1. `Lane` StrEnum with 7 canonical values
2. `StatusEvent` dataclass matching `contracts/event-schema.json`
3. `DoneEvidence`, `ReviewApproval`, `RepoEvidence`, `VerificationResult` dataclasses
4. `StatusSnapshot` dataclass matching `contracts/snapshot-schema.json`
5. Transition matrix with 16 legal `(from_lane, to_lane)` pairs
6. Guard condition functions per transition
7. Alias resolution (`doing` -> `in_progress`)
8. Comprehensive unit tests

**Success**: All model constructors validate correctly. Every legal transition pair returns `ok=True`. Every illegal pair returns `ok=False` with an error message. Aliases resolve before matrix lookup.

---

## Context & Constraints

- **Spec**: `kitty-specs/034-feature-status-state-model-remediation/spec.md` -- FR-001 through FR-011 (event schema, state machine, guard conditions, alias handling)
- **Plan**: `kitty-specs/034-feature-status-state-model-remediation/plan.md` -- AD-1 (Event Schema), AD-3 (Transition Matrix), Section "Integration Points"
- **Data Model**: `kitty-specs/034-feature-status-state-model-remediation/data-model.md` -- Lane, StatusEvent, DoneEvidence, ReviewApproval, RepoEvidence, VerificationResult, StatusSnapshot entities
- **Contracts**: `kitty-specs/034-feature-status-state-model-remediation/contracts/event-schema.json`, `contracts/snapshot-schema.json`, `contracts/transition-matrix.json`
- **Existing ULID usage**: `src/specify_cli/sync/emitter.py` -- import pattern: `import ulid` with `hasattr(ulid, "new")` check

**Key constraints**:
- Python 3.11+ required (StrEnum available natively)
- ULID pattern must match `^[0-9A-HJKMNP-TV-Z]{26}$` (Crockford base32)
- Alias `doing` accepted at input boundaries only -- never persisted in events
- `from_lane` and `to_lane` in events must always be canonical Lane values
- `force=true` requires `actor` (non-empty) and `reason` (non-empty)
- `review_ref` required when transition is `for_review -> in_progress`
- `evidence` required when `to_lane = done` unless `force=true`
- No fallback mechanisms -- fail intentionally on invalid input

---

## Subtasks & Detailed Guidance

### Subtask T001 -- Create `src/specify_cli/status/__init__.py`

**Purpose**: Public API surface for the status package. All consumers import from here.

**Steps**:
1. Create the `src/specify_cli/status/` directory
2. Create `__init__.py` with exports from `models.py` and `transitions.py`
3. Export the following names:
   - From `models`: `Lane`, `StatusEvent`, `StatusSnapshot`, `DoneEvidence`, `ReviewApproval`, `RepoEvidence`, `VerificationResult`
   - From `transitions`: `CANONICAL_LANES`, `LANE_ALIASES`, `ALLOWED_TRANSITIONS`, `validate_transition`, `resolve_lane_alias`

**Files**: `src/specify_cli/status/__init__.py` (new file)

**Validation**: `from specify_cli.status import Lane, StatusEvent, validate_transition` should succeed without error.

**Edge Cases**:
- Circular import prevention: ensure `__init__.py` only imports from submodules, not the reverse
- Keep the `__init__.py` minimal -- no logic, only re-exports

---

### Subtask T002 -- Create `src/specify_cli/status/models.py`

**Purpose**: Define all data types for the canonical status model.

**Steps**:
1. Create the file with these imports:
   ```python
   from __future__ import annotations
   import re
   from dataclasses import dataclass, field
   from enum import StrEnum
   from typing import Any
   ```

2. Define `Lane` as a StrEnum:
   ```python
   class Lane(StrEnum):
       PLANNED = "planned"
       CLAIMED = "claimed"
       IN_PROGRESS = "in_progress"
       FOR_REVIEW = "for_review"
       DONE = "done"
       BLOCKED = "blocked"
       CANCELED = "canceled"
   ```

3. Define `RepoEvidence` dataclass:
   ```python
   @dataclass(frozen=True)
   class RepoEvidence:
       repo: str
       branch: str
       commit: str  # 7-40 hex chars
       files_touched: list[str] = field(default_factory=list)

       def to_dict(self) -> dict[str, Any]:
           d: dict[str, Any] = {"repo": self.repo, "branch": self.branch, "commit": self.commit}
           if self.files_touched:
               d["files_touched"] = list(self.files_touched)
           return d

       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> RepoEvidence:
           return cls(
               repo=data["repo"],
               branch=data["branch"],
               commit=data["commit"],
               files_touched=data.get("files_touched", []),
           )
   ```

4. Define `VerificationResult` dataclass:
   ```python
   @dataclass(frozen=True)
   class VerificationResult:
       command: str
       result: str  # "pass", "fail", or "skip"
       summary: str

       def to_dict(self) -> dict[str, Any]:
           return {"command": self.command, "result": self.result, "summary": self.summary}

       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> VerificationResult:
           return cls(command=data["command"], result=data["result"], summary=data["summary"])
   ```

5. Define `ReviewApproval` dataclass:
   ```python
   @dataclass(frozen=True)
   class ReviewApproval:
       reviewer: str
       verdict: str  # "approved" or "changes_requested"
       reference: str

       def to_dict(self) -> dict[str, Any]:
           return {"reviewer": self.reviewer, "verdict": self.verdict, "reference": self.reference}

       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> ReviewApproval:
           return cls(reviewer=data["reviewer"], verdict=data["verdict"], reference=data["reference"])
   ```

6. Define `DoneEvidence` dataclass:
   ```python
   @dataclass(frozen=True)
   class DoneEvidence:
       review: ReviewApproval
       repos: list[RepoEvidence] = field(default_factory=list)
       verification: list[VerificationResult] = field(default_factory=list)

       def to_dict(self) -> dict[str, Any]:
           d: dict[str, Any] = {"review": self.review.to_dict()}
           if self.repos:
               d["repos"] = [r.to_dict() for r in self.repos]
           if self.verification:
               d["verification"] = [v.to_dict() for v in self.verification]
           return d

       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> DoneEvidence:
           return cls(
               review=ReviewApproval.from_dict(data["review"]),
               repos=[RepoEvidence.from_dict(r) for r in data.get("repos", [])],
               verification=[VerificationResult.from_dict(v) for v in data.get("verification", [])],
           )
   ```

7. Define `StatusEvent` dataclass with ULID validation:
   ```python
   ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

   @dataclass(frozen=True)
   class StatusEvent:
       event_id: str          # ULID
       feature_slug: str      # e.g. "034-feature-name"
       wp_id: str             # e.g. "WP01"
       from_lane: Lane
       to_lane: Lane
       at: str                # ISO 8601 UTC
       actor: str
       force: bool
       execution_mode: str    # "worktree" or "direct_repo"
       reason: str | None = None
       review_ref: str | None = None
       evidence: DoneEvidence | None = None

       def to_dict(self) -> dict[str, Any]: ...
       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> StatusEvent: ...
   ```

8. Define `StatusSnapshot` dataclass matching `contracts/snapshot-schema.json`:
   ```python
   @dataclass
   class StatusSnapshot:
       feature_slug: str
       materialized_at: str
       event_count: int
       last_event_id: str | None
       work_packages: dict[str, dict[str, Any]]  # WP ID -> WPState
       summary: dict[str, int]  # lane -> count

       def to_dict(self) -> dict[str, Any]: ...
       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> StatusSnapshot: ...
   ```

**Files**: `src/specify_cli/status/models.py` (new file)

**Validation**:
- `Lane("in_progress")` returns `Lane.IN_PROGRESS`
- `StatusEvent.to_dict()` followed by `StatusEvent.from_dict()` round-trips perfectly
- ULID_PATTERN matches valid ULIDs, rejects invalid ones
- `DoneEvidence` requires `review` field (ReviewApproval)

**Edge Cases**:
- `Lane("doing")` should raise `ValueError` -- alias resolution happens in transitions, not in the enum itself
- `StatusEvent.from_dict()` must convert string lane values to `Lane` enum instances
- `to_dict()` must serialize `Lane` values as their string values, not enum member names
- `evidence` field serialization: if None, serialize as `null` in JSON; if present, serialize via `DoneEvidence.to_dict()`

---

### Subtask T003 -- Create `src/specify_cli/status/transitions.py`

**Purpose**: Transition matrix, guard conditions, alias resolution, and validation logic.

**Steps**:
1. Define constants matching `contracts/transition-matrix.json`:
   ```python
   CANONICAL_LANES: tuple[str, ...] = (
       "planned", "claimed", "in_progress", "for_review",
       "done", "blocked", "canceled",
   )

   LANE_ALIASES: dict[str, str] = {"doing": "in_progress"}

   TERMINAL_LANES: frozenset[str] = frozenset({"done", "canceled"})

   ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset({
       ("planned", "claimed"),
       ("claimed", "in_progress"),
       ("in_progress", "for_review"),
       ("for_review", "done"),
       ("for_review", "in_progress"),
       ("in_progress", "planned"),
       ("planned", "blocked"),
       ("claimed", "blocked"),
       ("in_progress", "blocked"),
       ("for_review", "blocked"),
       ("blocked", "in_progress"),
       ("planned", "canceled"),
       ("claimed", "canceled"),
       ("in_progress", "canceled"),
       ("for_review", "canceled"),
       ("blocked", "canceled"),
   })
   ```

2. Implement `resolve_lane_alias()`:
   ```python
   def resolve_lane_alias(lane: str) -> str:
       """Resolve alias to canonical lane name. Returns input if not an alias."""
       return LANE_ALIASES.get(lane.strip().lower(), lane.strip().lower())
   ```

3. Implement `validate_transition()`:
   ```python
   def validate_transition(
       from_lane: str,
       to_lane: str,
       *,
       force: bool = False,
       actor: str | None = None,
       reason: str | None = None,
       review_ref: str | None = None,
       evidence: Any = None,
   ) -> tuple[bool, str | None]:
       """Validate a lane transition. Returns (ok, error_message)."""
   ```
   - First resolve aliases on both from_lane and to_lane
   - Check if `(from_lane, to_lane)` is in `ALLOWED_TRANSITIONS`
   - If not allowed and not forced: return `(False, "Illegal transition: {from} -> {to}")`
   - If forced: require actor (non-empty) and reason (non-empty), else return error
   - If allowed: run guard condition functions for this specific transition
   - Return `(True, None)` on success

4. Implement guard condition functions:
   - `_guard_actor_required(actor)` -- for `planned -> claimed`
   - `_guard_workspace_context_required()` -- for `claimed -> in_progress` (placeholder: always passes for now, real check in WP07)
   - `_guard_subtasks_complete_or_force(force)` -- for `in_progress -> for_review` (placeholder: always passes, real check delegated to caller)
   - `_guard_reviewer_approval_required(evidence)` -- for `for_review -> done`
   - `_guard_review_ref_required(review_ref)` -- for `for_review -> in_progress`

5. Implement `is_terminal()`:
   ```python
   def is_terminal(lane: str) -> bool:
       return resolve_lane_alias(lane) in TERMINAL_LANES
   ```

**Files**: `src/specify_cli/status/transitions.py` (new file)

**Validation**:
- `validate_transition("planned", "claimed", actor="agent-1")` returns `(True, None)`
- `validate_transition("planned", "done")` returns `(False, "Illegal transition: planned -> done")`
- `validate_transition("done", "planned", force=True, actor="admin", reason="reopening")` returns `(True, None)`
- `resolve_lane_alias("doing")` returns `"in_progress"`
- `resolve_lane_alias("claimed")` returns `"claimed"` (pass-through)

**Edge Cases**:
- Forced transition from terminal lane (done -> planned): must succeed with actor+reason
- Forced transition without actor: must fail with `"Force transitions require actor and reason"`
- Forced transition without reason: must fail similarly
- `is_terminal("done")` returns `True`; `is_terminal("in_progress")` returns `False`
- Case insensitivity: `resolve_lane_alias("Doing")` should resolve correctly

---

### Subtask T004 -- Unit tests for models

**Purpose**: Verify all data types, serialization, and validation rules.

**Steps**:
1. Create `tests/specify_cli/status/__init__.py` (empty)
2. Create `tests/specify_cli/status/test_models.py`
3. Test cases:
   - `test_lane_enum_has_seven_values` -- verify exactly 7 members
   - `test_lane_enum_string_values` -- each member's string value matches canonical name
   - `test_lane_enum_rejects_alias` -- `Lane("doing")` raises ValueError
   - `test_status_event_creation_valid` -- construct with all required fields
   - `test_status_event_ulid_validation` -- valid ULID matches ULID_PATTERN
   - `test_status_event_to_dict_round_trip` -- to_dict then from_dict produces identical event
   - `test_done_evidence_requires_review` -- from_dict without "review" key raises KeyError
   - `test_done_evidence_with_all_fields` -- repos + verification + review all serialize
   - `test_repo_evidence_commit_format` -- 7-40 hex char SHA values
   - `test_verification_result_valid_results` -- "pass", "fail", "skip"
   - `test_review_approval_verdicts` -- "approved", "changes_requested"
   - `test_status_snapshot_to_dict_round_trip` -- full snapshot serialization
   - `test_status_snapshot_summary_counts` -- summary dict has all 7 lane keys

**Files**: `tests/specify_cli/status/__init__.py` (new), `tests/specify_cli/status/test_models.py` (new)

**Validation**: All tests pass with `python -m pytest tests/specify_cli/status/test_models.py -v`

---

### Subtask T005 -- Unit tests for transitions

**Purpose**: Verify every legal and illegal transition pair, alias resolution, guard conditions, and force override behavior.

**Steps**:
1. Create `tests/specify_cli/status/test_transitions.py`
2. Test cases:
   - `test_all_legal_transitions_accepted` -- parametrize over all 16 ALLOWED_TRANSITIONS pairs, verify `(True, None)`
   - `test_illegal_transitions_rejected` -- parametrize over known illegal pairs (e.g., planned->done, claimed->for_review, done->planned without force), verify `(False, error_msg)`
   - `test_alias_resolution_doing` -- `resolve_lane_alias("doing")` returns `"in_progress"`
   - `test_alias_resolution_passthrough` -- `resolve_lane_alias("planned")` returns `"planned"`
   - `test_alias_resolution_case_insensitive` -- `resolve_lane_alias("Doing")` returns `"in_progress"`
   - `test_force_allows_terminal_exit` -- `validate_transition("done", "planned", force=True, actor="admin", reason="reopen")` returns `(True, None)`
   - `test_force_without_actor_rejected` -- returns `(False, error_msg)`
   - `test_force_without_reason_rejected` -- returns `(False, error_msg)`
   - `test_guard_actor_required_for_claim` -- `planned -> claimed` without actor returns error
   - `test_guard_review_ref_for_rollback` -- `for_review -> in_progress` without review_ref returns error
   - `test_guard_evidence_for_done` -- `for_review -> done` without evidence returns error
   - `test_is_terminal_done` -- `is_terminal("done")` is True
   - `test_is_terminal_canceled` -- `is_terminal("canceled")` is True
   - `test_is_terminal_in_progress` -- `is_terminal("in_progress")` is False
   - `test_canonical_lanes_count` -- `len(CANONICAL_LANES)` is 7
   - `test_allowed_transitions_count` -- `len(ALLOWED_TRANSITIONS)` is 16

**Files**: `tests/specify_cli/status/test_transitions.py` (new)

**Validation**: All tests pass with `python -m pytest tests/specify_cli/status/test_transitions.py -v`

---

## Test Strategy

**Required per user requirements**: Unit tests for transitions/reducer.

- **Coverage target**: 100% of models.py and transitions.py
- **Test runner**: `python -m pytest tests/specify_cli/status/ -v`
- **Parametrized tests**: Use `@pytest.mark.parametrize` for transition matrix exhaustive testing
- **Fixtures**: Create a `conftest.py` in `tests/specify_cli/status/` with factory functions for `StatusEvent`, `DoneEvidence`, etc.
- **Negative tests**: Every guard condition must have a test that triggers its error path

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| StrEnum requires Python 3.11+ | Import error on older Python | Already enforced by project constitution |
| ULID import path differs between packages | Runtime error | Use same pattern as `sync/emitter.py`: `import ulid; hasattr(ulid, "new")` |
| Lane enum JSON serialization | Enum value vs name confusion | Use `StrEnum` which serializes to string value natively |
| Alias leaking into persisted events | Data corruption | Validation in `validate_transition` resolves aliases before checking matrix |
| Guard conditions as placeholders | False sense of completeness | Document which guards are placeholder vs enforced; real enforcement wired in WP07 |

---

## Review Guidance

- **Check Lane enum**: Exactly 7 values matching `contracts/event-schema.json` `$defs.Lane.enum`
- **Check StatusEvent fields**: All required fields from `contracts/event-schema.json` present
- **Check ALLOWED_TRANSITIONS**: Exactly 16 pairs matching `contracts/transition-matrix.json` `transitions` array
- **Check alias resolution**: `doing` resolved to `in_progress`, never persisted as-is
- **Check force validation**: `force=True` requires both actor and reason (non-empty strings)
- **Check guard conditions**: Each transition with a named guard in the matrix has a corresponding function
- **Check serialization**: `to_dict()` / `from_dict()` round-trip for all dataclasses
- **No fallback mechanisms**: Invalid input causes explicit errors, not silent defaults

---

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T14:27:12Z – claude-opus – shell_pid=41824 – lane=doing – Assigned agent via workflow command
- 2026-02-08T14:30:27Z – claude-opus – shell_pid=41824 – lane=for_review – Ready for review: Lane enum, StatusEvent/StatusSnapshot models, 16-pair transition matrix with guards, alias resolution, force-override. 101 tests all passing.
- 2026-02-08T14:30:51Z – claude-opus-reviewer – shell_pid=42336 – lane=doing – Started review via workflow command
- 2026-02-08T14:31:16Z – claude-opus-reviewer – shell_pid=42336 – lane=done – Review passed: All models match contracts, 16 transitions correct, guards enforced, alias resolution working, 101 tests pass. No issues found.
- 2026-02-08T14:33:32Z – claude-opus-reviewer – shell_pid=43865 – lane=doing – Started review via workflow command
- 2026-02-08T14:45:08Z – claude-opus-reviewer – shell_pid=43865 – lane=for_review – Moved to for_review
