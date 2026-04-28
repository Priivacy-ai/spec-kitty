---
work_package_id: WP05
title: next writes paired profile-invocation lifecycle records (#843)
dependencies: []
requirement_refs:
- FR-011
- FR-012
planning_base_branch: release/3.2.0a6-tranche-2
merge_target_branch: release/3.2.0a6-tranche-2
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a6-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a6-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
agent: "claude:opus-4-7:default:reviewer"
shell_pid: "47745"
history:
- at: '2026-04-28T09:30:00Z'
  by: spec-kitty.tasks
  note: Created as part of tranche-2 specify→plan→tasks pipeline
authoritative_surface: src/specify_cli/invocation/
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/record.py
- src/specify_cli/invocation/writer.py
- src/specify_cli/invocation/executor.py
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/cli/commands/advise.py
- tests/specify_cli/invocation/test_lifecycle_pairing.py
- tests/integration/test_next_lifecycle_records.py
tags: []
---

# WP05 — `next` writes paired profile-invocation lifecycle records (#843)

## Branch Strategy

- **Planning/base branch**: `release/3.2.0a6-tranche-2`
- **Final merge target**: `release/3.2.0a6-tranche-2`
- Lane D (independent). Implementation command: `spec-kitty agent action implement WP05 --agent claude`.

## Objective

When `spec-kitty next --agent <name>` issues a public action, write a `started` profile-invocation lifecycle record. When the same action subsequently advances (success or explicit failure), write a paired `completed` or `failed` record. Both records share the same canonical action identifier — derived from the mission step/action `next` actually issued.

## Context

GitHub issue #843. Public `next` cycles currently produce no observable lifecycle trace, so it is impossible to correlate what `next` issued against what an agent actually executed. Adding paired records makes mid-cycle agent crashes observable and gives the doctor surface a real signal.

**FRs**: FR-011, FR-012 · **NFR**: NFR-006 · **SC**: SC-005 · **Spec sections**: Scenario 5, Domain Language ("Profile-invocation lifecycle record") · **Contract**: [contracts/invocation-lifecycle.md](../contracts/invocation-lifecycle.md) · **Data shape**: [data-model.md §4](../data-model.md)

## Always-true rules

- Every `started` record SHOULD eventually have exactly one paired `completed` or `failed` record sharing the same `canonical_action_id`.
- `canonical_action_id` on `started` MUST equal what `next` issued — no rewriting at completion time.
- Orphan `started` records are observable, not silently overwritten.

---

## Subtask T023 — Define `ProfileInvocationRecord` shape

**Purpose**: One canonical record schema across writers and readers.

**Steps**:

1. In `src/specify_cli/invocation/record.py`, define (or extend) `ProfileInvocationRecord` matching [data-model.md §4](../data-model.md):
   ```python
   @dataclass(frozen=True)
   class ProfileInvocationRecord:
       canonical_action_id: str
       phase: Literal["started", "completed", "failed"]
       at: datetime  # UTC, ISO-8601 on the wire
       agent: str
       mission_id: str
       wp_id: str | None = None
       reason: str | None = None
   ```
2. Provide `to_dict()` / `from_dict()` matching the on-disk shape (JSON with sorted keys for stability).
3. If a similar dataclass already exists, extend it rather than adding a new one.

**Files to edit**:
- `src/specify_cli/invocation/record.py`

---

## Subtask T024 — Hook `started` write into the next issuance path

**Purpose**: Emit the `started` record at the moment `next` exposes a public action to the agent.

**Steps**:

1. In `src/specify_cli/cli/commands/next_cmd.py` (and any helper in `src/specify_cli/cli/commands/advise.py` if `advise` shares the issuance path), locate the call site that emits the action to the calling agent.
2. Compute the canonical action identifier:
   ```python
   canonical_action_id = f"{mission_step}::{action_name}"
   ```
   Use the mission step + action that the runtime actually issued — do not synthesize one from the agent's input.
3. Before returning to the agent, write the `started` record via `invocation.writer.append(record)`.
4. Use the helper in `src/specify_cli/invocation/writer.py` (which presumably handles the local store path); extend it if necessary to support the new phase value.

**Files to edit**:
- `src/specify_cli/cli/commands/next_cmd.py`
- `src/specify_cli/cli/commands/advise.py` (if it shares the issuance path)
- `src/specify_cli/invocation/writer.py` (if extending)

---

## Subtask T025 — Hook `completed` / `failed` write into the advance path

**Purpose**: Pair the lifecycle.

**Steps**:

1. Locate the path that runs when an action advances. This may be:
   - A second `next` call that consumes the previous issuance, or
   - A success/failure handler in `executor.py`.
2. At advancement, write a `completed` record with the **same** `canonical_action_id` as the `started` record. On explicit failure, write a `failed` record with `reason` populated.
3. The action ID lookup must come from the in-flight runtime context (e.g., the `next` command's known issuance), not from a guess.

**Files to edit**:
- `src/specify_cli/cli/commands/next_cmd.py`
- `src/specify_cli/invocation/executor.py`

---

## Subtask T026 — Surface orphan `started` records via doctor

**Purpose**: Make mid-cycle crashes observable.

**Steps**:

1. Locate the doctor surface (likely `src/specify_cli/cli/commands/doctor.py` or a sub-helper in `src/specify_cli/invocation/`).
2. Add a check that scans the local invocation store, groups records by `canonical_action_id`, and lists groups containing exactly one `started` (no pair).
3. Add the orphan section to the doctor's existing JSON output (under e.g. `invocation_orphans`) and to its human-readable rendering.
4. Do not auto-remediate; just observe.

**Files to edit**:
- `src/specify_cli/invocation/` (helper, exact module per existing layout)
- The doctor command file (if a wiring change is needed there)

**Note**: if doctor lives in a file outside this WP's `owned_files`, scope the change to the helper inside `invocation/` and have doctor call into it. Keep the wiring change in doctor minimal.

---

## Subtask T027 — Unit tests: pair-matching, orphan observability  [P]

**Purpose**: Lock in the pairing rule.

**Steps**:

1. Create `tests/specify_cli/invocation/test_lifecycle_pairing.py`.
2. Tests:
   - `test_started_then_completed_pairs`: write `started` then `completed` with same id; assert pair found.
   - `test_started_then_failed_pairs`: same with `failed`; assert pair found.
   - `test_orphan_started_listed`: write only `started`; assert pair-matching surface lists it as orphan.
   - `test_started_not_overwritten_by_second_started`: write `started` twice for the same id; assert both records persist (or, if dedup is intentional, document that and assert orphan still observable).
   - `test_canonical_action_id_matches_issued`: assert `started.canonical_action_id` equals the mission step::action format.

**Files to create**:
- `tests/specify_cli/invocation/test_lifecycle_pairing.py` (~150 lines)

---

## Subtask T028 — Integration test: ≥5 issuances yield ≥95% pairing

**Purpose**: NFR-006 floor.

**Steps**:

1. Create `tests/integration/test_next_lifecycle_records.py`.
2. Test body:
   - Set up a mission + 6 WPs (or use the existing fixture for a multi-WP mission).
   - Drive `next` to issue and advance ≥ 5 actions, simulating one mid-cycle stop to produce one orphan.
   - Read the local invocation store, compute pairing rate, assert ≥ 95% over the non-orphan set.
   - Assert the orphan is listed by the doctor surface.

**Files to create**:
- `tests/integration/test_next_lifecycle_records.py` (~140 lines)

---

## Test Strategy

- **Unit**: T027 covers each pair shape and the orphan path.
- **Integration**: T028 covers the NFR-006 pairing rate end-to-end.
- **Coverage**: ≥ 90% on changed code (NFR-002).
- **Type safety**: `mypy --strict` clean.

## Definition of Done

- [ ] T023 — `ProfileInvocationRecord` shape defined and JSON-serialisable.
- [ ] T024 — `started` written at issuance.
- [ ] T025 — `completed` / `failed` written at advancement, with matching id.
- [ ] T026 — orphans visible via doctor surface.
- [ ] T027 — unit tests pass.
- [ ] T028 — integration test passes (≥ 95% pairing).
- [ ] `mypy --strict` clean.
- [ ] No SaaS dependency (records are local).

## Risks

- **Risk**: Writing `started` before issuance commits creates a record for an action that never exposed.
  **Mitigation**: Write `started` immediately before the return-to-caller boundary so the record exists iff the agent saw the action.
- **Risk**: `canonical_action_id` rewriting drifts started↔completed.
  **Mitigation**: Read the id once at issuance; pass it through the runtime context to the advancement handler.
- **Risk**: Orphan flood from agent crashes.
  **Mitigation**: Observability via doctor is the explicit goal; floods are visible, not silent.

## Reviewer guidance

- Confirm `canonical_action_id` on the `started` record equals what `next` issued — read the test assertion specifically.
- Confirm no `started` record is silently overwritten by a subsequent unrelated `started` for the same id.
- Confirm doctor exposes orphans in both JSON and human modes.
- Verify pair-matching logic handles `failed` as a legitimate completion — it pairs, it isn't an orphan.

## Out of scope

- SaaS-side syncing of these records (independent; governed by `SPEC_KITTY_ENABLE_SAAS_SYNC`).
- A migration for legacy single-shot records (a deprecation tolerance window in the doctor surface is sufficient).
- Auto-remediation of orphans.

## Activity Log

- 2026-04-28T10:09:09Z – claude:opus-4-7:default:implementer – shell_pid=41311 – Started implementation via action command
- 2026-04-28T10:21:33Z – claude:opus-4-7:default:implementer – shell_pid=41311 – WP05 ready: started/completed/failed pairing on next, orphan observability via doctor invocation-pairing, 29 unit+integration tests passing, mypy --strict clean
- 2026-04-28T10:22:20Z – claude:opus-4-7:default:reviewer – shell_pid=47745 – Started review via action command
