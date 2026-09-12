---
work_package_id: WP06
title: Transactional Convergence, Aggregate De-duplication, Fan-out, Docs
dependencies:
- WP02
requirement_refs:
- C-001
- C-007
- C-008
- FR-006
- FR-007
- FR-008
- FR-009
- NFR-005
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-fsm-write-path-integrity-01M1TZV6
base_commit: 7b90adcfdaf4ab5ef5229fa466bb6091f5769a07
created_at: '2026-09-06T13:26:20.457594+00:00'
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
- T037
- T038
- T039
phase: Wave 1 - Pipeline convergence (mission core, part 2)
agent: claude
history:
- at: '2026-09-06T11:57:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- tests/specify_cli/coordination/test_phantom_fanout.py
- tests/specify_cli/coordination/test_plain_door_semantics.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/status/aggregate.py
- CLAUDE.md
- docs/architecture/status-model.md
- tests/specify_cli/coordination/test_status_transition.py
- tests/specify_cli/coordination/test_phantom_fanout.py
- tests/specify_cli/coordination/test_plain_door_semantics.py
- tests/status/test_agent_status_emit_aggregate_wiring.py
- tests/status/test_aggregate_coord_deleted_contract.py
- tests/status/test_aggregate_surface_resolution.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Transactional Convergence, Aggregate De-duplication, Fan-out, Docs

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log. Address every item before completion and log what changed.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

Second half of the mission's core (spec "WP02" / dossier D6–D9). Depends on WP02's pipeline and fan-out seam.

Done means:

- **SC-002** (RED on main): coord-topology mission, fallback arm, commit forced to fail ⇒ **zero** SaaS/zeitgeist fan-out for the truncated event. Today `_fallback_emit_single._coord` (`src/specify_cli/coordination/status_transition.py:401-432`) calls the plain door whose step-7 fan-out (`status/emit.py:794`) fires before `_commit_status_artifacts_to_coord`.
- **SC-003** (RED on main): an owned-mission (`effective_root`) request through the transactional **batch** door gets the same `ActionContextError` refusal and `effective_root` acquisition as the single door (`:1342-1345` / `:1362-1369` vs `:1594-1616`). Decision Q5 = parity.
- **SC-007** (GREEN on main, stays green): a stored-`LANES` mission emitted through the plain door gains no commits and spawns no identity-resolution git subprocess (C-008).
- **US2-4**: `MissionStatus.transition` (`src/specify_cli/status/aggregate.py:605-698`) no longer re-derives/re-infers/re-validates; validation runs exactly once per emit tree-wide.
- All three failure policies stay explicit (C-007) and their pins stay green: `tests/specify_cli/coordination/test_status_transition.py::test_inner_state_annotation_degrades_when_coordination_branch_missing` (#3460), `::test_transactional_emit_fails_closed_when_coordination_branch_missing` (#1848), `tests/specify_cli/cli/commands/agent/test_tasks_move_task_degod.py::test_runtime_state_persistence_error_propagates`.
- `_prepare_event` is deleted; the transactional single/batch/inner-state doors compose `prepare_transition`.
- Docs: the stale "single entry point" sentence is corrected (minimal hunk) in CLAUDE.md's status section and `docs/architecture/status-model.md:393`; the Q4 ADR-amendment paragraph is in `design-notes/WP06-convergence.md`; terminology guard green.

## Context & Constraints

- Spec US2, FR-006..009, FR-018 (lock is WP02's; you compose over it), C-001, C-007, C-008, NFR-005. Contract `contracts/emit-pipeline.md` §2 (shell contract), §5 (plain-door pin). Data model §5. Research §1 (Q4 and the six options — read it; you write the ADR paragraph), §3 D-1 (the "four plain-door callers" are docstring mentions; the pin's rationale is the fallback arm `status_transition.py:392`).
- **Q4 decision** (`01M1V80R6F6RTMR7Y3C2WBKR32`): the pipeline is the named validation/build authority; `MissionStatus` remains the intended domain facade but is NOT the write chokepoint; its eight direct-transactional bypassers do NOT migrate here. Do not "improve" by routing callers through the aggregate.
- **C-001**: preserve the coord/primary partition: coord topology ⇒ coord worktree write + `safe_commit` + truncate-rollback symmetry, fail-loud `FallbackCoordWorktreeUnresolved` (`:176`, `:259`, `:382-435`); flat/`LANES`/`SINGLE_BRANCH` ⇒ uncommitted primary write.
- **C-006**: `coordination` imports `status` (downward). `status/aggregate.py:623` already lazily imports `coordination` — that is the cited precedent violation. Do not add another; do not remove it either (that is a caller-migration mission). Keep the lazy import as-is and note it.
- **C-008**: plain-door semantics for flat/LANES: no identity git subprocesses, no commits.
- **Doc contention (FR-009 / R12)**: CLAUDE.md status section and `status-model.md` have three writers (this WP, PR #3885, Mission C). Your edit is ONE sentence each. Mission C owns final text.
- `emit_status_transition_transactional` etc. are near the complexity ceiling; extracting the pipeline should reduce them. No suppressions.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP06` (the resolver bases you on WP02's lane).

## Subtasks & Detailed Guidance

### Subtask T031 – Red-first: phantom fan-out

- **Purpose**: FR-008 / SC-002 / R3.
- **Steps**:
  1. `tests/specify_cli/coordination/test_phantom_fanout.py` (new): build a coord-topology mission in a `tmp_path` git repo where `_transaction_topology_available` is False so the fallback path is taken (see how `test_status_transition.py` reaches `_fallback_emit_single` — reuse its fixtures). Register a recording SaaS fan-out handler via `specify_cli.status.register_saas_fanout_handler` (pattern in `tests/status/test_emit_fanout_after_adapter.py`).
  2. Monkeypatch `_commit_status_artifacts_to_coord` to raise. Emit via `emit_status_transition_transactional`.
  3. Assert: the exception propagates (or whatever the arm's failure policy is today — read `:404-432` and pin it), the event is truncated from the coord log, AND the recorded fan-out list is empty. On main the list has one entry ⇒ RED. `xfail(strict=True)` until T036.
- **Files**: `tests/specify_cli/coordination/test_phantom_fanout.py`.
- **Parallel?**: Yes (with T032, T033).

### Subtask T032 – Red-first: batch parity + ordering pins

- **Purpose**: FR-007 / SC-003 / D7.
- **Steps**:
  1. Parity pin: build a request with `effective_root` set for a mission where `_transaction_topology_available` is True; submit through `emit_status_transition_batch_transactional`; assert `ActionContextError("OWNED_TRANSACTION_UNAVAILABLE"…)` under the same condition the single door raises it (`:1342-1345`), and that `BookkeepingTransaction.acquire` receives `repo_root=primary_root or repo_root` + `effective_root=` (`:1362-1369`) — today the batch passes plain `repo_root` and no kwarg. RED.
  2. Ordering pin: single transactional path defers via `queue_saas_emission` (`:1403`); the plain door fans out immediately (`emit.py:794`). Write an equivalence test asserting "fan-out happens after the durable write completes" for both doors — RED for the fallback arm until T036.
  3. Both `xfail(strict=True)` until T035/T036; T039 replaces them with delegation-equivalence tests.
- **Files**: `tests/specify_cli/coordination/test_status_transition.py` (add cases) or the new file.
- **Parallel?**: Yes.

### Subtask T033 – Plain-door semantics pin (C-008, SC-007)

- **Purpose**: Guards against the rejected shim mechanism resurfacing during convergence.
- **Steps**: `tests/specify_cli/coordination/test_plain_door_semantics.py` (new): stored-`LANES` mission (write `meta.json` topology accordingly) in a `tmp_path` git repo with one commit; emit via `emit_status_transition_transactional` (which takes the `_fallback_emit_single._primary` arm ⇒ plain door); assert `git rev-list --count HEAD` unchanged and — by patching `subprocess.run`/the git helper the identity resolver uses — that no `git` invocation for identity resolution occurred beyond what the fixture itself needs. GREEN on main; must stay green after every later subtask. Rationale docstring cites `status_transition.py:392`, not the four docstring mentions (research §3 D-1).
- **Files**: `tests/specify_cli/coordination/test_plain_door_semantics.py`.
- **Parallel?**: Yes.

### Subtask T034 – Single transactional door composes the pipeline; delete `_prepare_event`

- **Purpose**: FR-006 (1 of 3 orchestrations).
- **Steps**:
  1. In `emit_status_transition_transactional` (`:1318-1417`): inside the transaction, keep `from_lane = _derive_from_lane(txn.feature_dir, wp_id)` once; replace `_prepare_event(...)` with `prepare_transition(request=..., feature_dir=txn.feature_dir, mission_slug=..., mission_id=mission_id_for_event, from_lane=from_lane, readiness=None)`; on `event is None` keep the no-op arm (the synthetic same-lane event return at `:1383-1396`) and perform the frontmatter mirror the pipeline now only *requests* (`mirror_frontmatter_lane`) — call `_emit._mirror_phase1_frontmatter_lane(txn.feature_dir, wp_id, resolved_lane)` here (the ONLY write of `lane`; 2093 invariant).
  2. `annotation`: use `PreparedTransition.annotation` if WP02 promoted `_annotation_for_request`; otherwise keep calling `_annotation_for_request` here.
  3. Delete `_prepare_event` (`:842-945`). Grep for other callers (`emit_inner_state_changed_transactional`, batch) — T035 converts them; delete only after all three compose the pipeline.
- **Files**: `src/specify_cli/coordination/status_transition.py`.
- **Parallel?**: No.

### Subtask T035 – Batch parity + inner-state door

- **Purpose**: FR-006 (2 and 3 of 3), FR-007.
- **Steps**:
  1. `emit_status_transition_batch_transactional` (`:1574+`): add the owned-mission check (`if request.effective_root is not None and not topology_available: raise ActionContextError(...)` mirrored from `:1342-1345`) and the `BookkeepingTransaction.acquire(repo_root=identity.primary_root or identity.repo_root, ..., effective_root=identity.repo_root if identity.primary_root is not None else None)` shape from `:1362-1369`. Extract the shared identity/acquire preamble into one helper used by both doors so the whack-a-field divergence becomes structurally impossible (D7).
  2. Per request in the batch: `prepare_transition` with the in-transaction accumulated `from_lane`; keep the batch failure policy at `:1574` explicit (read it; pin it if not already pinned).
  3. `emit_inner_state_changed_transactional` (`:1446`): it emits an annotation, not a lane transition — check whether it calls `_prepare_event` at all; if it only builds an annotation, leave its logic, but ensure its `BookkeepingWorktreeMissing` degrade arm (#3460) is untouched and its pin stays green.
  4. Keep `queue_saas_emission(txn, …)` as the deferred fan-out for the transactional doors (already post-commit via `txn.defer_outbound`).
- **Files**: `src/specify_cli/coordination/status_transition.py`, tests.
- **Parallel?**: No.

### Subtask T036 – Coord fallback arm: fan-out only after commit

- **Purpose**: FR-008 — close the phantom.
- **Steps**:
  1. `_fallback_emit_single._coord` (`:404-432`): call the flat shell with WP02's seam (`fan_out=False` or the deferred-callable variant); after `_commit_status_artifacts_to_coord` succeeds, perform the fan-out (call the deferred callable, or call `_emit._saas_fan_out(event, mission_slug, repo_root, policy_metadata=…, ensure_sync_daemon=…)` + `_resolved_binding_fan_out` if you used the boolean seam); in the `finally: if not committed:` branch, restore artifacts and do NOT fan out.
  2. `_fallback_emit_batch` (`:439-486`): same treatment for the batch coord arm.
  3. `_primary` arms: unchanged (flat/LANES: no commit exists; immediate fan-out is correct).
  4. Flip T031's xfail; add the batch variant of the phantom test.
- **Files**: `src/specify_cli/coordination/status_transition.py`, `tests/specify_cli/coordination/test_phantom_fanout.py`.
- **Parallel?**: No.

### Subtask T037 – Aggregate de-duplication

- **Purpose**: FR-006 (the aggregate's duplicate validation), US2-4.
- **Steps**:
  1. `MissionStatus.transition` (`aggregate.py:605-698`): delete the local from-lane derivation, gate inference (`_resolve_review_gate_inputs`), `GuardContext` build and `validate_transition` call at `:685`. Keep `_resolve_current_lane` ONLY if something other than validation needs `current_actor` — it is threaded into the request for the transactional door's `current_actor` guard input; if so, keep computing `current_actor` and inject it via `_enrich_transition_request`, but do NOT validate here.
  2. Keep the alias-collapse early return only if the transactional door does not already handle it (it does, via the pipeline's `event is None` arm) — delete it.
  3. The docstring must state: validated once, in the status-owned pipeline, inside the transaction; the aggregate composes the transactional shell. Cite decision `01M1V80R6F6RTMR7Y3C2WBKR32`.
  4. Tests: `tests/status/test_agent_status_emit_aggregate_wiring.py` and siblings — update assertions that counted a validation call in the aggregate; add a tree-wide "validate exactly once per emit" test (wrap `validate_transition`, emit via `ms.transition`, assert count == 1).
  5. Leave the lazy `from specify_cli.coordination.status_transition import …` at `:623` in place; add a comment "C-006 precedent violation; caller-migration mission owns removal".
- **Files**: `src/specify_cli/status/aggregate.py`, the three aggregate test files.
- **Parallel?**: No.

### Subtask T038 – Docs + ADR-amendment note + terminology guard

- **Purpose**: FR-009 / D9 / Q4 rider / directive 003.
- **Steps**:
  1. CLAUDE.md, "Status Model Patterns" table row for `emit_status_transition()` says "Single entry point: validate → persist → materialize → views → SaaS". Replace with one sentence: "Flat/primary shell over the status-owned `transition_pipeline` (validation runs once there); the transactional shell lives in `coordination/status_transition.py`." One row only.
  2. `docs/architecture/status-model.md:393`: same one-sentence correction.
  3. `design-notes/WP06-convergence.md`: (a) the ADR-amendment paragraph for the #1667 / C-004 chain — two senses of "authoritative": `MissionStatus` = intended domain facade for callers (unchanged intent), `transition_pipeline.prepare_transition` = single validation/build authority (new, this mission); the eight direct transactional callers remain and their migration is a future mission; cite `research.md` §1 and the decision id; (b) the failure-policy table (C-007) with test nodeids; (c) any flat-shell vs `_prepare_event` divergence WP02 recorded and how you adjudicated it.
  4. `.venv/bin/pytest tests/architectural/test_no_legacy_terminology.py -q` before pushing any doc hunk.
- **Files**: `CLAUDE.md`, `docs/architecture/status-model.md`, design note.
- **Parallel?**: No.

### Subtask T039 – C-009 swap, pins, blast radius

- **Purpose**: Transitional repros become permanent behaviour tests.
- **Steps**:
  1. Replace T032's divergence pins with delegation-equivalence tests: for each door (plain, single txn, batch txn), the same `TransitionRequest` yields a `StatusEvent` equal modulo `event_id`/`at`, and `prepare_transition` is the only validator invoked.
  2. Keep T031 and T033 as permanent tests (rename to behaviour names).
  3. Run the pins: the #3460 / #1848 / move-task nodeids listed under Objectives.
  4. Record commands + counts in the PR body.
- **Files**: tests.
- **Parallel?**: No.

## Test Strategy

```bash
make test-fast
.venv/bin/pytest tests/status tests/specify_cli/status tests/specify_cli/coordination -q
.venv/bin/pytest "tests/specify_cli/coordination/test_status_transition.py::test_inner_state_annotation_degrades_when_coordination_branch_missing" "tests/specify_cli/coordination/test_status_transition.py::test_transactional_emit_fails_closed_when_coordination_branch_missing" "tests/specify_cli/cli/commands/agent/test_tasks_move_task_degod.py::test_runtime_state_persistence_error_propagates" -q
.venv/bin/pytest tests/specify_cli/cli/commands/agent tests/specify_cli/merge tests/specify_cli/lanes -q   # direct transactional callers
.venv/bin/pytest tests/architectural/test_status_module_boundary.py tests/architectural/test_2093_authority_invariant.py tests/architectural/test_no_legacy_terminology.py tests/architectural/test_no_legacy_status_emit_callers.py -q
.venv/bin/ruff check src tests && .venv/bin/mypy src/specify_cli/coordination/status_transition.py src/specify_cli/status/aggregate.py
```

## Risks & Mitigations

- **R1** collapsing in the wrong direction → the pipeline is already in `status/` (WP02); you only compose. If you find yourself importing `coordination` from `status/`, stop.
- **R2** plain-door callers gain commits → T033 runs after every subtask.
- **R3** phantom fan-out → T031 + T036.
- **Failure-policy erosion** → the three pins are in the Test Strategy; run them after T034, T035, T036 separately.
- **R12** doc contention → one sentence per file.

## Review Guidance

- Confirm T031 was RED at the merge-base and is green now; confirm zero fan-out on the failure path for both single and batch coord arms.
- Confirm batch parity via the shared preamble helper (no duplicated identity/acquire code left).
- Confirm `_prepare_event` is gone and `validate_transition` is called once per emit through every door (T039 test).
- Confirm the aggregate's lazy import remains with the C-006 comment, and no caller was migrated.
- Confirm docs: exactly one sentence per file; ADR paragraph present; terminology guard green.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T11:57:59Z – system – Prompt created.
- 2026-09-06T14:12:18Z – claude – shell_pid=2467 – WP06 implemented at 2cad2894a: transactional single/batch/inner-state doors compose status.transition_pipeline via shared _resolve_transaction_entry/_acquire_status_transaction (batch parity FR-007); _prepare_event deleted; coord fallback arms fan out only the committed tail after safe_commit (FR-008, RED proof order=[fan_out, commit] on base); MissionStatus.transition de-duplicated (validate once tree-wide); C-007 pins green; docs one sentence each (AGENTS.md via CLAUDE.md symlink, status-model.md:211); design note with Q4 ADR amendment + D-1..D-6 at scratchpad wp06-planning-artifacts/.../design-notes/WP06-convergence.md
