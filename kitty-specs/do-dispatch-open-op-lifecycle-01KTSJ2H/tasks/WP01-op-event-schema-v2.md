---
work_package_id: WP01
title: Op Event Schema v2
dependencies: []
requirement_refs:
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:fable:reviewer-renata:reviewer"
shell_pid: "31238"
history:
- '2026-06-10T20:15:38Z: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/invocation/
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/record.py
- src/specify_cli/invocation/writer.py
- src/specify_cli/cli/commands/invocations_cmd.py
- tests/specify_cli/invocation/test_record_v2.py
- tests/specify_cli/invocation/test_writer_v2.py
- tests/specify_cli/invocation/cli/test_invocations.py
role: implementer
tags: []
---

# WP01 — Op Event Schema v2

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries for the remainder of this work package.

## Objective

Split the dual-purpose frozen `InvocationRecord` (`src/specify_cli/invocation/record.py:20-46`) into two distinct Pydantic v2 frozen models — `OpStartedEvent` and `OpCompletedEvent` — so that a completed event **requires** a non-null `outcome` and a `closed_by` discriminator, and **cannot** carry started-only fields defaulted to `""`/`"unknown"`. Update the writer and all readers accordingly. This is the foundation WP: WP02, WP03, and WP05 build on these models.

## Context

- Spec: FR-004 (schema split), FR-005 (file readable alone). Contracts: `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/op-record-events.md`. Data model: `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/data-model.md` (field tables + invariants).
- Today one model serves both events via `event: Literal["started","completed"]` with everything defaulting; real completed lines in the wild look like `{"event":"completed", "action":"", "actor":"unknown", "outcome":null, ...}` — the #1810 "unreadable record" complaint, valid by construction.
- The JSONL file (`kitty-ops/<ulid>.jsonl`) stays append-only: started written with exclusive create (`"x"`), completed appended (`"a"`). `artifact_link`, `commit_link`, `glossary_checked` event shapes are **unchanged**.
- Do NOT change `do`/`ask`/`advise` command behavior in this WP (that's WP02/WP03). Keep `executor.py` compiling by adapting its call sites minimally to the new constructors — but the `closed_by` parameter plumbing through `complete_invocation` belongs to WP03; here, hardcode `closed_by="agent"` at the executor's single construction site with a `# WP03 threads the real value` note.

## Subtasks

### T001 — Define `OpStartedEvent`

**Purpose**: A started event whose required fields make blank records unrepresentable.

**Steps**:
1. In `src/specify_cli/invocation/record.py`, add `OpStartedEvent(BaseModel)` with `model_config = {"frozen": True}` and fields per the data-model table:
   - `event: Literal["started"] = "started"`
   - `invocation_id: str` (validate 26-char ULID via existing pattern/validator if present)
   - `profile_id: str`, `action: str` — both `min_length=1`
   - `request_text: str` (may be empty only in query mode — no model-level gate, executor enforces)
   - `actor: str` (`min_length=1`)
   - `mode_of_work: str` (`min_length=1`)
   - `governance_context_hash: str`, `governance_context_available: bool`
   - `router_confidence: str | None = None`
   - `started_at: str` (`min_length=1`, ISO-8601 — reuse any existing timestamp validator)
   - `mission_id: str | None = None`, `wp_id: str | None = None`
2. Serialization: `to_jsonl_line()` (or align with the writer's existing dump helper) omitting `None` fields, matching the contract example byte-for-byte in field naming.

**Validation**: constructing without `action` or with `action=""` raises; round-trip parse of the contract's started example succeeds.

### T002 — Define `OpCompletedEvent`

**Purpose**: A completed event that is meaningful in isolation.

**Steps**:
1. Add `OpCompletedEvent(BaseModel)`, frozen, fields exactly:
   - `event: Literal["completed"] = "completed"`
   - `invocation_id: str` (ULID)
   - `completed_at: str` (`min_length=1`)
   - `outcome: Literal["done", "failed", "abandoned"]` — **required, no default**
   - `closed_by: Literal["agent", "doctor_sweep"]` — **required, no default**
   - `evidence_ref: str | None = None`
2. There must be NO `action`, `request_text`, `actor`, `started_at`, etc. on this model.
3. Keep (or add) a parse helper that, given a dict from a JSONL line, dispatches on `event` to the right model — used by readers in T004. Legacy dicts (no `closed_by`) must raise a distinct, catchable error (`LegacyRecordError` or similar) so the WP05 migration and readers can identify them deliberately rather than crash.
4. Decide the fate of the old `InvocationRecord` class: delete it if nothing outside `invocation/` imports it (grep first: `grep -rn "InvocationRecord" src tests`); if the WP05 migration needs the legacy shape, keep a clearly-named `LegacyInvocationRecord` parse-only helper.

**Validation**: `OpCompletedEvent(invocation_id=..., completed_at=..., outcome=None, ...)` is a type/validation error; mypy --strict passes.

### T003 — Update `InvocationWriter`

**Purpose**: Writer accepts the v2 models and preserves the append-only contract.

**Steps**:
1. `write_started(record: OpStartedEvent)` — exclusive create unchanged; index append (`ops-index.jsonl`) unchanged.
2. `write_completed(record: OpCompletedEvent)` — append mode; the already-closed guard (scan for an existing `"completed"` line → `AlreadyClosedError`) unchanged.
3. Serialization through the models' dump (None fields omitted). `artifact_link` / `commit_link` / `glossary_checked` writers untouched.

**Validation**: existing writer tests adapted; new test proves a written completed line contains exactly the v2 fields and nothing else.

### T004 — Update readers

**Purpose**: Everything that parses Op JSONL understands v2 and fails informatively on legacy.

**Steps**:
1. Grep all consumers: `grep -rn "InvocationRecord\|kitty-ops" src/specify_cli --include="*.py"`. Known readers: `invocations list` (`src/specify_cli/cli/commands/invocations_cmd.py`), doctor orphan scan (`src/specify_cli/doctor/ops.py` — reads raw dicts; verify it keys only on `event` values and adjust if it touches removed fields), executor's `_read_started_event`/`_read_started_mode` (`src/specify_cli/invocation/executor.py`), evidence promotion (`promote_to_evidence` in record.py).
2. Update each to the dispatch-parse helper from T002. For `invocations list`, display `outcome` and `closed_by` for closed Ops.
3. On encountering a legacy line, readers emit a single warning naming `spec-kitty upgrade` (the WP05 migration) and skip the record — never a traceback.

**Validation**: `invocations list` integration test over a fixture dir containing v2 open + v2 closed records; a legacy record produces the warning path.

### T005 — Unit tests

**Purpose**: Pin the schema contract.

**Steps**: Create `tests/specify_cli/invocation/test_record_v2.py` and `test_writer_v2.py` covering: required-field enforcement (outcome, closed_by, action), None-field omission in serialization, round-trip of both contract examples, exclusive-create collision, `AlreadyClosedError` on second completed append, legacy-line detection error. Adapt `tests/specify_cli/invocation/cli/test_invocations.py` for the new list output.

**Validation**: `.venv/bin/pytest tests/specify_cli/invocation -q` green; `.venv/bin/mypy src/specify_cli/invocation` clean; `.venv/bin/ruff check src/specify_cli/invocation` clean.

## Branch Strategy

Planning base branch: `main`. Final merge target: `main`. Execution worktrees are allocated per computed lane from `lanes.json` (e.g. `.worktrees/do-dispatch-open-op-lifecycle-01KTSJ2H-lane-a/`); do not hand-create branches. Implement via `spec-kitty agent action implement WP01 --agent <name>`.

## Definition of Done

- [ ] `OpStartedEvent` / `OpCompletedEvent` exist, frozen, with required fields per data-model.md; invalid states unconstructible.
- [ ] Writer writes v2 shapes; append-only invariants and `AlreadyClosedError` preserved.
- [ ] All readers handle v2; legacy lines warn-and-skip with migration pointer.
- [ ] Other event shapes (`artifact_link`, `commit_link`, `glossary_checked`) byte-identical to before.
- [ ] ≥90% coverage on changed code; mypy --strict and ruff clean, zero suppressions.

## Risks & Reviewer Guidance

- **Hidden readers**: the grep in T004 is load-bearing — a missed consumer crashes at runtime on the new shape. Reviewer: re-run the grep and check each hit.
- **executor.py scope creep**: only constructor-adaptation here; lifecycle semantics (auto-close removal, closed_by threading) belong to WP02/WP03. Reviewer: reject behavior changes to `invoke()`/`complete_invocation()` flow beyond compilation.
- **Serialization drift**: the SaaS propagator (WP02 scope) builds envelopes from these models; field renames beyond the contract will ripple. Stick to the contract names exactly.

## Activity Log

- 2026-06-10T20:36:34Z – claude:fable:python-pedro:implementer – shell_pid=23900 – Assigned agent via action command
- 2026-06-10T21:02:43Z – claude:fable:python-pedro:implementer – shell_pid=23900 – WP01 implementation complete: v2 op event schema, writer, readers, tests; gates green (339 passed, mypy clean, ruff clean)
- 2026-06-10T21:03:37Z – claude:fable:python-pedro:implementer – shell_pid=23900 – Deviation: T005's specified test_record_v2.py/test_writer_v2.py were consolidated into test_record.py/test_writer.py (classes TestOpStartedEvent/TestOpCompletedEvent/TestParseOpEvent, TestWrittenLineShapes) — transitional version labels must not live in permanent filenames. Coverage unchanged; suite 339 passed, mypy and ruff clean.
- 2026-06-10T21:04:06Z – claude:fable:reviewer-renata:reviewer – shell_pid=31238 – Started review via action command
- 2026-06-10T21:04:18Z – user – shell_pid=31238 – Ready for review: schema v2 split, writer+readers updated, tests green, mypy/ruff clean
- 2026-06-10T21:09:17Z – user – shell_pid=31238 – Review passed: v2 OpStartedEvent/OpCompletedEvent frozen models match contract exactly; outcome/closed_by required with no defaults; writer append-only invariants and AlreadyClosedError preserved; all readers handle v2 with warn-and-skip legacy lines; gates green (339 passed, ruff, mypy clean)
