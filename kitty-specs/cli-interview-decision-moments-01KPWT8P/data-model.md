# Data Model — CLI Interview Decision Moments

Phase 1 output for mission `cli-interview-decision-moments-01KPWT8P`.

## 1. Runtime models (`src/specify_cli/decisions/models.py`)

### 1.1 Enums

```python
class OriginFlow(str, Enum):
    CHARTER = "charter"
    SPECIFY = "specify"
    PLAN = "plan"


class DecisionStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    CANCELED = "canceled"


class DecisionErrorCode(str, Enum):
    MISSING_STEP_OR_SLOT = "DECISION_MISSING_STEP_OR_SLOT"
    ALREADY_CLOSED = "DECISION_ALREADY_CLOSED"
    TERMINAL_CONFLICT = "DECISION_TERMINAL_CONFLICT"
    NOT_FOUND = "DECISION_NOT_FOUND"
    MISSION_NOT_FOUND = "MISSION_NOT_FOUND"
    VERIFY_DRIFT = "DECISION_VERIFY_DRIFT"
```

### 1.2 Pydantic models (or dataclasses; choose the pattern consistent with adjacent `src/specify_cli/status/models.py`)

```python
class IndexEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str  # ULID
    origin_flow: OriginFlow
    step_id: Optional[str] = None
    slot_key: Optional[str] = None
    input_key: str
    question: str
    options: Tuple[str, ...] = ()
    status: DecisionStatus
    final_answer: Optional[str] = None
    rationale: Optional[str] = None
    other_answer: bool = False
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    mission_id: str
    mission_slug: str

    @model_validator(mode="after")
    def _step_or_slot(self):
        if not self.step_id and not self.slot_key:
            raise ValueError("step_id or slot_key required")
        return self


class DecisionIndex(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = 1
    mission_id: str
    entries: Tuple[IndexEntry, ...] = ()
```

## 2. On-disk formats

### 2.1 `kitty-specs/<mission>/decisions/index.json`

Deterministic JSON (sorted keys, LF line endings, trailing newline):
```json
{
  "version": 1,
  "mission_id": "01KPWT8PNY8683QX3WBW6VXYM7",
  "entries": [
    {
      "decision_id": "01J2A...",
      "origin_flow": "specify",
      "step_id": null,
      "slot_key": "specify.intent-summary.q1",
      "input_key": "auth_strategy",
      "question": "Which auth strategy should we use?",
      "options": ["session", "oauth2", "oidc", "Other"],
      "status": "resolved",
      "final_answer": "oauth2",
      "rationale": null,
      "other_answer": false,
      "created_at": "2026-04-23T10:00:00+00:00",
      "resolved_at": "2026-04-23T10:01:00+00:00",
      "resolved_by": "robert@robshouse.net",
      "mission_id": "01KPWT8PNY8683QX3WBW6VXYM7",
      "mission_slug": "cli-interview-decision-moments-01KPWT8P"
    }
  ]
}
```

Entries sorted by `created_at` ASC then `decision_id` ASC (lexicographic). Write pattern: atomic `tmp` + `os.replace()`.

### 2.2 `kitty-specs/<mission>/decisions/DM-<decision_id>.md`

Human-readable, with change log:

```markdown
# Decision Moment `01J2A...`

- **Mission:** `cli-interview-decision-moments-01KPWT8P`
- **Origin flow:** `specify`
- **Slot key:** `specify.intent-summary.q1`
- **Input key:** `auth_strategy`
- **Status:** `resolved`
- **Created:** `2026-04-23T10:00:00+00:00`
- **Resolved:** `2026-04-23T10:01:00+00:00`
- **Resolved by:** `robert@robshouse.net`
- **Other answer:** `false`

## Question

Which auth strategy should we use?

## Options

- session
- oauth2
- oidc
- Other

## Final answer

oauth2

## Rationale

_(none)_

## Change log

- `2026-04-23T10:00:00+00:00` — opened
- `2026-04-23T10:01:00+00:00` — resolved (final_answer="oauth2")
```

### 2.3 Event emission to `kitty-specs/<mission>/status.events.jsonl`

On `decision open`: append one `DecisionPointOpened` event (interview variant) using the 4.0.0 envelope. The payload model is `DecisionPointOpenedInterviewPayload` from `spec_kitty_events.decisionpoint` (vendored).

On `decision resolve|defer|cancel`: append one `DecisionPointResolved` event (interview variant) with `terminal_outcome ∈ {resolved, deferred, canceled}`.

Events carry the identity/origin/question/options fields mirrored from the index entry. `step_id` on the wire is populated from either `step_id` (preferred) or `slot_key` (if caller passed slot_key instead). The wire field name remains `step_id` for 4.0.0 compat.

## 3. Idempotency key

Logical key = `(mission_id, origin_flow, step_id or slot_key, input_key)`. The store looks up the most recent entry matching that key. If found and non-terminal, return. If found and terminal, raise `ALREADY_CLOSED`.

## 4. CLI surfaces

See `contracts/cli-contracts.md`.

## 5. Sentinel marker format (LLM-authored in spec.md / plan.md)

Single inline form the verifier recognizes:
```
[NEEDS CLARIFICATION: <text>] <!-- decision_id: <decision_id> -->
```

Verifier regex (sketch): `\[NEEDS CLARIFICATION: [^\]]*\]\s*<!--\s*decision_id:\s*(\S+?)\s*-->`.

## 6. Verifier behavior

Inputs: `--mission <slug>`. Loads the index, identifies decisions with `status=deferred`. Scans `spec.md` and `plan.md` (if they exist) for markers.

Rules:
- Every deferred decision must have ≥1 inline marker with matching `decision_id`.
- Every inline marker must reference a `decision_id` that exists in the index and is in `status=deferred`.
- A marker referencing a decision that has moved out of deferred state is a stale-marker finding.

Returns: JSON report of findings. Exit code: 0 on clean, non-zero on any finding.

## 7. Charter integration

In `src/specify_cli/cli/commands/charter.py`, find the existing interview loop (around `charter interview` command). Before each question is displayed, call the new `decisions.service.open(...)` API with `origin_flow=charter`, `step_id=charter.<question_id>`. After the answer, call `resolve` / `defer` / `cancel`. Preserve `answers.yaml` writes.

## 8. Template updates

`src/specify_cli/missions/software-dev/command-templates/specify.md` and `plan.md` gain an explicit instruction block:

> Before asking any interview question, you MUST run `spec-kitty agent decision open --mission <slug> --flow specify --slot-key <slot> --input-key <key> --question "<q>" [--options '["a","b",...]']` and use the returned `decision_id` for any subsequent terminal command. After the user answers, run exactly one of:
> - `spec-kitty agent decision resolve <decision_id> --final-answer "<answer>" [--other-answer]`
> - `spec-kitty agent decision defer <decision_id> --rationale "<why>"`
> - `spec-kitty agent decision cancel <decision_id> --rationale "<why>"`
>
> When deferring, write the inline marker `[NEEDS CLARIFICATION: <text>] <!-- decision_id: <decision_id> -->` in the target doc (spec.md for specify, plan.md for plan). Before finishing this command, run `spec-kitty agent decision verify --mission <slug>` and address any findings before declaring interview complete.

## 9. Dep/version changes

- `pyproject.toml`: `"spec-kitty-events==4.0.0"` (was 3.3.0).
- `src/specify_cli/spec_kitty_events/`: replace with copy of `spec-kitty-events/src/spec_kitty_events/` at 4.0.0.
- Any CLI code that already imports from `spec_kitty_events` and emits DecisionPoint events is checked and updated to satisfy 4.0.0 (add `origin_surface="adr"` if it emits ADR-style).
