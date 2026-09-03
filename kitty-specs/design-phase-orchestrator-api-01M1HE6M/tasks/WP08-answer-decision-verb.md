---
work_package_id: WP08
title: answer-decision verb (Mechanism B, full event/lifecycle parity)
dependencies:
- WP02
requirement_refs:
- FR-013
- NFR-001
- NFR-002
- NFR-005
- C-005
planning_base_branch: feat/design-phase-orchestrator-api-3837
merge_target_branch: feat/design-phase-orchestrator-api-3837
branch_strategy: Planning artifacts for this mission were generated on feat/design-phase-orchestrator-api-3837. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/design-phase-orchestrator-api-3837 unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
- T039
- T040
- T041
scope: codebase-wide
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/orchestrator_api/
create_intent:
- tests/specify_cli/orchestrator_api/test_answer_decision.py
- tests/specify_cli/next/test_next_invocation_lifecycle_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/orchestrator_api/test_answer_decision.py
- tests/specify_cli/next/test_next_invocation_lifecycle_seam.py
- tests/specify_cli/orchestrator_api/test_commands_fail_closed.py
- tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py
role: implementer
tags: []
tracker_refs: []
---

# WP08 — answer-decision verb (Mechanism B, full event/lifecycle parity)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: (unset — select at implementation time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ CHOKEPOINT + HARD GATE — read before starting

**Hard gate**: this WP CANNOT START until WP02 has actually landed —
`answer-decision` imports `runtime.next.next_invocation_lifecycle`, which
does not exist until WP02 creates it. Do not begin T036 against a branch
that doesn't have WP02's commits.

**Chokepoint**: per plan.md § (l), this is one of the two WPs (with WP02)
a reviewing squad should read FIRST AND IN ISOLATION. It is the
mission's highest-STAKES WP — SC-007/SC-008's full event-log/lifecycle-
record parity requirement means an implementation that "looks right" (a
correct-looking JSON response) but silently omits the seam calls is
exactly the silent-success failure mode the operator ruling
(SPEC-FRESH2-001) exists to prevent. Its own diff is moderate, but its
correctness depends entirely on WP02 already being correct — read WP02's
task file and the actual `next_invocation_lifecycle.py` it produced before
starting this WP's implementation.

**Independent of WP03-WP06**: this WP's ONLY dependency is WP02. Do not
add a dependency on WP03/WP04/WP05/WP06 even though all five land in
`orchestrator_api/commands.py` — the same-file overlap is handled via
`scope: codebase-wide` (see Write-Scope note below), not via an artificial
dependency edge.

## Objective

Add the `answer-decision` orchestrator-api verb (FR-013), resolving a
`spec-kitty next` control-loop `decision_required` moment (Mechanism B —
a blocking audit checkpoint OR a missing required input) at ANY DAG step,
in ANY mission phase — with FULL parity to what `spec-kitty next --answer
... --result ...` does today, including the three lifecycle/event-log side
effects, reached EXCLUSIVELY through WP02's extracted seam.

## Context

**This is a COMPOSITE verb** matching exactly what the real CLI invocation
`spec-kitty next --answer <value> --decision-id <id> --agent <name>
--result <success|failed|blocked>` does in one pass
(`next_cmd.py:213-269`), never just the first engine call. In order:

1. **Persist the answer** — `runtime_bridge.answer_decision_via_runtime(
   mission_slug, decision_id, answer, agent, repo_root_path)`
   (`runtime_bridge.py:2587-2662`). Returns nothing usable as a response
   payload.
   - **Auto-resolve `--decision-id` when omitted** (`next_cmd.py:975-995`,
     `_handle_answer`): read `_internal_runtime.engine._read_snapshot(
     run_ref.run_dir).pending_decisions`; if `len(pending) == 0` →
     structured `error_code` `NO_PENDING_DECISION` (mirroring the CLI's
     "Error: No pending decisions to answer"); if `len(pending) == 1` →
     auto-resolve to that single id; if `len(pending) > 1` → structured
     `error_code` `AMBIGUOUS_PENDING_DECISION`, `data`/`error` listing the
     sorted pending ids (mirroring the CLI's "Multiple pending decisions
     (...). Use --decision-id to specify which one.").
   - **`--decision-id` provided but not in `pending_decisions`** →
     structured `error_code` `DECISION_NOT_PENDING` (already answered, or
     names a different step) — never silently no-op or answer the wrong
     decision.
2. **Pair the previous issuance's lifecycle record BEFORE the DAG
   advances**: `next_invocation_lifecycle.pair_previous_lifecycle_record(
   agent, mission_slug, result, repo_root, effective_root=...)` — imported
   from WP02's module, called EXACTLY where `next_cmd.py:244` calls it
   (before `decide_next`, never after).
3. **Advance the DAG**: `decide_next(agent, mission_slug, result,
   repo_root, effective_root=...)` — this is `src/runtime/next/decision.py:413`,
   the ENGINE call (`decide_next_via_runtime`), NOT part of WP02's seam —
   import it directly from `runtime.next.decision`, using THIS verb's own
   `--result` value (`success`/`failed`/`blocked`, hard-required alongside
   `--answer`, mirroring `_validate_result_and_answer`,
   `next_cmd.py:743-750` — reject a call with `--answer` but no `--result`
   with a structured `error_code`, e.g. `RESULT_REQUIRED`).
4. **Emit the mission event log entry AFTER the DAG advances**:
   `next_invocation_lifecycle.emit_mission_next_invoked(agent, result,
   mission_slug, repo_root, decision, effective_root=...)` — imported from
   WP02's module, called with the `decision` object step 3 returned.
5. **Write the new issuance lifecycle record, CONDITIONALLY**:
   `next_invocation_lifecycle.write_issuance_lifecycle_record(agent,
   mission_slug, repo_root, decision, effective_root=...)` — ONLY when
   `decision.kind == "step"` (preserve this exact conditional guard from
   `next_cmd.py:263-269` — do not call it unconditionally).

**Per operator ruling SPEC-FRESH2-001 (binding, not optional): steps 2, 4,
and 5 are REQUIRED**, reached ONLY through WP02's
`next_invocation_lifecycle` module — **never inlined, never
reimplemented** inside `orchestrator_api/commands.py`. A verb that
performs only step 1 + steps 3 (the two engine calls) without 2/4/5 is a
SPEC-FRESH2-001 regression, not an acceptable minimal implementation —
this is the exact gap an earlier draft of this mission's spec shipped and
the operator explicitly ruled against.

**Response shape** (spec Key Entities "Run decision" + Clarification 3 +
SPEC-FRESH2-002's resolution — do not re-derive):
- `data` = `decision.to_dict()` from step 3's `decide_next` call (`kind`,
  `step_id`, `decision_id`, `prompt_file`, etc.) — byte-identical, field-
  for-field, to what `next --answer ... --json` returns for those keys.
- PLUS one sibling field: `data.answered_decision_id` = the `decision_id`
  persisted in step 1 (self-documenting orchestrator-api name for the
  CLI's terser `answered` key — following this repo's existing convention
  of curated field names, e.g. `start-implementation`/`start-review`'s
  `wp_id`/`from_lane`/`to_lane`, not a verbatim re-export).
- **`data` carries NO `answer` key** (the CLI's second extra key, the
  echoed submitted answer text, `next_cmd.py:915`) — intentionally
  OMITTED per SPEC-FRESH2-002's resolution: the host already possesses the
  value it submitted in its own request, unlike `answered_decision_id`,
  which can name an auto-resolved id the host did not already know.

**FR-012 does NOT apply to this verb** (spec Acceptance Scenario 6): this
mechanism operates on the run-snapshot's `pending_decisions`, not
`decisions/index.json` — a mission whose current phase has no
`OriginFlow` member (`tasks`, `analyze`) can still have a pending
`decision_required` moment, and `answer-decision` resolves it normally.
Do NOT apply WP05's `INVALID_ORIGIN_FLOW` guard here.

## Subtask T036: RED — extend `test_next_invocation_lifecycle_seam.py` (NOT a new file)

**Purpose**: Extend WP02's shared SC-008 test module with the
orchestrator-api path — proving a shared, single test file fails if EITHER
caller (host CLI or orchestrator-api) regresses.

**Steps**:
1. Open `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py`
   (WP02's file — **do not create a new file, do not rewrite the existing
   content**). Import WP02's `assert_lifecycle_seam_effects` helper
   UNMODIFIED — do not re-derive a parallel helper.
2. Add a new test function driving a fixture mission to a
   `decision_required` state (blocking `AuditStep`, `decision_id:
   "audit:<step_id>"`) via `spec-kitty next --json`, then calling the
   orchestrator-api `answer-decision` command as `run_action`, and calling
   `assert_lifecycle_seam_effects(feature_dir, repo_root, mission_slug,
   run_action)` against it.
3. This is RED pre-implementation because the `answer-decision` command
   does not exist in `commands.py` yet (Typer "no such command" /
   non-zero exit) — a genuine, non-vacuous RED.
4. Keep WP02's `pytestmark = pytest.mark.integration` (+ `git_repo` if
   present) — do not change it.
5. Also create `tests/specify_cli/orchestrator_api/test_answer_decision.py`
   for the verb's OWN negative-path/response-shape tests that don't belong
   in the shared seam file (Acceptance Scenarios 2, 3, 4, 5, 6 — ambiguous/
   not-pending/no-pending/OriginFlow-independence/next-step-parity) — mark
   `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]`, matching
   `test_transition_subtask_gate.py`'s precedent (real fixture-mission
   run-snapshot I/O).
6. Confirm RED on `planning_base_branch` for both files' new content.

**Files**: `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py` (extended, ~+60-100 lines), `tests/specify_cli/orchestrator_api/test_answer_decision.py` (new, ~180-250 lines).

**Validation**: both fail (command not found) on `planning_base_branch`.

## Subtask T037: Implement `answer-decision` core (steps 1 + 3, the two engine calls)

**Purpose**: Persist-and-advance, with the auto-resolve/ambiguous/not-pending/no-pending error handling.

**Steps**:
1. `@app.command(name="answer-decision")`, options `--mission`, `--agent`,
   `--result` (required alongside `--answer`), `--answer`, `--decision-id`
   (optional — auto-resolve when omitted), `--policy` (required —
   mutating verb).
2. Implement the auto-resolve/ambiguous/not-pending/no-pending logic
   exactly as described in Context step 1, using
   `_internal_runtime.engine._read_snapshot` and
   `runtime_bridge.get_or_start_run` (mirror `next_cmd.py:975-1005`'s
   exact sequence — resolve `feature_dir`/`mission_type`/`run_ref` the
   same way `_handle_answer` does, via `placement_seam(...).read_dir(
   MissionArtifactKind.PRIMARY_METADATA)`).
3. Call `runtime_bridge.answer_decision_via_runtime(...)`.
4. Call `decide_next` from `runtime.next.decision` (the ENGINE, not
   WP02's seam) with this verb's own `--result`.

**Files**: `src/specify_cli/orchestrator_api/commands.py` (~80-120 new lines).

**Validation**: `test_answer_decision.py`'s ambiguous/not-pending/no-pending/success-path scenarios pass for the two-engine-call portion (lifecycle parity not yet wired — T038 completes it).

## Subtask T038: Wire the three FR-014 seam side effects (steps 2, 4, 5)

**Purpose**: The load-bearing part of this WP — SPEC-FRESH2-001 compliance.

**Steps**:
1. Import `pair_previous_lifecycle_record`, `emit_mission_next_invoked`,
   `write_issuance_lifecycle_record` from
   `runtime.next.next_invocation_lifecycle` (WP02's module) — this is the
   FIRST import of `runtime.next` INTO `orchestrator_api/commands.py`
   (confirmed zero such imports exist today, per plan.md § (a) — this WP
   establishes it, following `next_cmd.py`'s own established
   CLI-layer-imports-`runtime.next` precedent).
2. Call `pair_previous_lifecycle_record(...)` BEFORE the `decide_next` call
   from T037 (exact ordering matters — matches `next_cmd.py:244` running
   before `next_cmd.py:248-250`).
3. Call `emit_mission_next_invoked(...)` AFTER `decide_next` returns,
   passing the returned `decision` object.
4. Call `write_issuance_lifecycle_record(...)` AFTER
   `emit_mission_next_invoked`, ONLY when `decision.kind == "step"` —
   preserve this exact conditional.
5. **Never** reimplement any of these three functions' logic inline in
   `commands.py` — if you find yourself writing lifecycle-record or
   event-log I/O code directly in `commands.py`, stop: that is the
   inlining the operator ruling explicitly rejected.

**Files**: part of T037's diff in `commands.py` (~20-30 additional lines).

**Validation**: T036's extended `test_next_invocation_lifecycle_seam.py`
test passes — `assert_lifecycle_seam_effects` observes all three side
effects from the orchestrator-api `answer-decision` path.

## Subtask T039: Compose the response shape

**Purpose**: `Decision.to_dict()` + `answered_decision_id` sibling field, no `answer` echo.

**Steps**:
1. `data = decision.to_dict()` (from T037's `decide_next` call), then
   `data["answered_decision_id"] = <the decision_id from step 1>`.
2. Confirm NO `data["answer"]` key is set — grep the diff for `"answer"`
   as a dict key to self-check before committing.
3. `validate_outbound_payload(data, "orchestrator_api")` then
   `make_envelope`/`_emit`.

**Files**: part of T037/T038's diff.

**Validation**: `test_answer_decision.py`'s response-shape assertions
(Acceptance Scenarios 1 and 3 — `answered_decision_id` present,
`Decision.to_dict()` keys byte-identical to `next --answer --json`, no
`answer` key) pass.

## Subtask T040: SC-007/SC-008 full assertion pass

**Purpose**: Confirm this WP is graded against the actual acceptance bar,
not a partial implementation that "looks done."

**Steps**:
1. Run the FULL extended `test_next_invocation_lifecycle_seam.py` — both
   WP02's original CLI-path test and this WP's new orchestrator-api-path
   test must be green in the SAME file, proving a single shared assertion
   helper catches a regression in either caller.
2. Add a field-for-field diff assertion in `test_answer_decision.py`
   comparing `answer-decision`'s response against an actual
   `spec-kitty next --answer ... --json` invocation for the identical
   scenario (Acceptance Scenario 1's "byte-identical parity" bar) — do not
   settle for "looks similar," assert actual equality on every
   `Decision.to_dict()`-derived key.

**Files**: `test_answer_decision.py` (part of T036's file, extended here).

**Validation**: both tests green.

## Subtask T041: Negative-path coverage + NFR-001 re-run

**Purpose**: NFR-002/SC-004 + confirm zero regression.

**Steps**:
1. Confirm `AMBIGUOUS_PENDING_DECISION`, `DECISION_NOT_PENDING`,
   `NO_PENDING_DECISION`, `RESULT_REQUIRED` are all covered by dedicated
   test cases (Acceptance Scenarios 2, 4, 5) in `test_answer_decision.py`.
2. Extend `test_commands_fail_closed.py`/`test_typed_error_fail_closed.py`
   with missing `--policy` on `answer-decision`.
3. Re-run full existing `tests/specify_cli/orchestrator_api/` suite AND
   the existing `next_cmd.py` `--answer` surface
   (`test_next_answer_effective_root.py`, `test_next_fail_closed.py`,
   `test_next_owned_commit_guard.py`, `test_next_typed_error_passthrough.py`)
   to confirm this WP's new `runtime.next` import into `commands.py`
   introduces no regression to either surface.

**Files**: `test_commands_fail_closed.py`, `test_typed_error_fail_closed.py` (extended).

**Validation**: all green.

## Write-Scope / Adjacent Open PRs

`orchestrator_api/commands.py` — same-file overlap with **PR #3826**
(merge-mission area) and with sibling WPs WP03/WP04/WP05/WP06 (mutually
independent per plan.md's parallel-lane design); marked
`scope: codebase-wide` for the same reason as its siblings (see WP03's
Write-Scope note). This WP ALSO owns
`tests/specify_cli/next/test_next_invocation_lifecycle_seam.py`, shared
with WP02 — that overlap is exempt from the ownership check via the
WP02→WP08 dependency edge (sequential pair, not concurrent), not via
`codebase-wide`. **PR #3826 merged into `main` on 2026-09-02**; this
mission's branch has not yet rebased onto that merge as of this tasks
phase, so `commands.py`'s merge-mission area on `main` already carries
#3826's changes. Sequence the MERGE of this WP against WP03/04/05/06,
and re-verify `commands.py` against `main`'s current state (not the
now-stale #3826-still-open assumption) — but note this WP's merge
additionally has a HARD prerequisite (WP02 merged first), unlike
WP03-06's soft merge-ordering recommendation.

## Definition of Done

- [ ] RED commit(s): extended `test_next_invocation_lifecycle_seam.py` +
      new `test_answer_decision.py` both fail on `planning_base_branch`
      (post-WP02).
- [ ] `answer-decision` implemented: auto-resolve/ambiguous/not-pending/
      no-pending handling, THEN the two engine calls, THEN all three
      FR-014 seam side effects called via WP02's module (never inlined).
- [ ] Response = `Decision.to_dict()` + `answered_decision_id` sibling,
      NO `answer` key.
- [ ] FR-012's `INVALID_ORIGIN_FLOW` guard NOT applied to this verb.
- [ ] SC-007 field-for-field parity test against a real `next --answer
      --json` invocation passes.
- [ ] SC-008 shared regression test (both CLI and orchestrator-api paths
      in the ONE file) green.
- [ ] Negative-path cases (`AMBIGUOUS_PENDING_DECISION`,
      `DECISION_NOT_PENDING`, `NO_PENDING_DECISION`, `RESULT_REQUIRED`,
      `POLICY_METADATA_REQUIRED`) all covered.
- [ ] Existing `next_cmd.py` `--answer` test surface AND existing
      orchestrator-api suite both green (NFR-001, C-005 behaviour
      preservation).
- [ ] `mypy --strict` / `ruff check` clean.

Run: `spec-kitty agent action implement WP08 --agent <name>`

## Risks

- **Partial-composite regression**: implementing only steps 1+3 (the two
  engine calls) and skipping 2/4/5 would produce a verb that PASSES a
  naive "does it return the right JSON" test while silently failing
  SC-007/SC-008 — this is the single highest-consequence mistake possible
  in this mission; T038/T040 exist specifically to catch it. Do not mark
  this WP done on the strength of T037 alone.
- **Wrong call order**: `pair_previous_lifecycle_record` must run BEFORE
  `decide_next`; `emit_mission_next_invoked`/`write_issuance_lifecycle_record`
  must run AFTER. A reordering would still "look" correct in a superficial
  test but break the observable ordering guarantee the CLI provides today.
- **Inlining temptation**: re-implementing lifecycle/event-log I/O
  directly in `commands.py` "for simplicity" instead of importing WP02's
  module is an architecture violation the operator ruling explicitly
  rejected — a reviewer must check for this explicitly, not assume it
  away.

## Reviewer Guidance

- This is the second of the two WPs (with WP02) plan.md recommends reading
  FIRST AND IN ISOLATION. Read WP02's actual landed
  `next_invocation_lifecycle.py` alongside this WP's diff — confirm every
  one of the three functions is IMPORTED, never redefined or inlined.
- Confirm the SC-008 shared test file was EXTENDED, not rewritten or
  duplicated — diff WP02's original commit against this WP's changes to
  confirm WP02's original test content is untouched.
- Confirm `data` has no `answer` key and does have `answered_decision_id`
  — this is a one-line check with real regression value (SPEC-FRESH2-002).
- Confirm FR-012's OriginFlow guard is genuinely absent from this verb's
  code path (Acceptance Scenario 6) — grep for `INVALID_ORIGIN_FLOW` in
  the WP08 diff; any hit is a violation.
