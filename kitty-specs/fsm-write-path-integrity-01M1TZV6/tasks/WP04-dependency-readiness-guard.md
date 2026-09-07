---
work_package_id: WP04
title: Dependency Readiness Guard inside the FSM
dependencies:
- WP03
- WP06
requirement_refs:
- C-004
- C-005
- FR-012
- FR-013
- FR-014
- NFR-002
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
phase: Wave 2 - Guard on the unified pipeline
history:
- at: '2026-09-06T11:57:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent:
- tests/status/test_dependency_guard.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/models.py
- src/specify_cli/status/wp_state.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- src/specify_cli/cli/commands/agent/tasks_status_view.py
- src/runtime/next/discovery.py
- tests/status/test_dependency_guard.py
- tests/specify_cli/status/test_wp_state.py
- tests/specify_cli/status/test_transition_context.py
role: implementer
agent: claude
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Dependency Readiness Guard inside the FSM

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

User Story 4 (P2). Today `validate_transition` has NO dependency logic, and a direct emit claiming a dep-blocked WP succeeds; the six pre-flight checks are advisory UX with a TOCTOU window.

Done means (SC-005):

1. `GuardContext` (`src/specify_cli/status/models.py:885`) gains `dependency_ready: bool | None = None`.
2. `validate_transition` refuses `planned→claimed` and `claimed→in_progress` when `dependency_ready is False` (unless `force` with actor+reason); passes on `True` and on `None` (**fail-OPEN**, decision Q8 `01M1V8HVDQH36X06JDK22SZV02`, C-004).
3. Both shells resolve readiness **inside the lock/transaction against their write surface** (`txn.feature_dir` for coord) and pass it to `prepare_transition` (FR-013). A verdict-less shell emit that claims a dep-blocked WP is refused (RED on main → GREEN).
4. Probe sites `src/specify_cli/lanes/recovery.py:78` and `src/specify_cli/cli/commands/agent/tasks_transition_core.py:337` still pass with self-built contexts (`None`).
5. `dependency_readiness_for_wp` (`src/specify_cli/core/dependency_graph.py:34`) is reused, not reimplemented; the six pre-flight sites are left in place and re-commented as UX (FR-014).
6. Replay purity (C-005 / NFR-002): `reducer.py` has zero `validate_transition`/`GuardContext` references; a history containing a now-dep-illegal claim replays and audits with no guard finding.
7. Re-invoking `implement` on an `in_progress` WP is still a no-op resume.

## Context & Constraints

- Spec US4, FR-012..014, C-004, C-005, NFR-002, non-goal 6. Contract `contracts/dependency-guard.md` (polarity table, placement, resolution site, test matrix). Data model §6.
- **Polarity rationale (record it, T025)**: fail-closed on `None` would silently kill the two probe sites; fail-open is sound because after WP03 no durable write bypasses the shells, and the shells always supply the verdict. Do NOT copy `subtasks_complete`'s `is not True` polarity (`wp_state.py:370`).
- **Precedent shape**: `subtasks_complete` threading — `emit.py:645-665` (shell infers), pipeline builds `GuardContext`, `wp_state.py:guard_for` checks. Follow that shape exactly; guards never consult `ctx.force` (#1775 M2 — force is handled once at `check_transition`).
- **Out-of-map leeway (declared in the plan)**: `src/specify_cli/status/transition_pipeline.py` (WP02), `src/specify_cli/status/emit.py` (WP02), `src/specify_cli/coordination/status_transition.py` (WP06), `src/specify_cli/orchestrator_api/commands.py` (WP01 owns it for a comment; you add two comments at `:1115`/`:1440`). Each edit: minimal, one-line rationale in the Activity Log ("FR-013 verdict supplier" / "FR-014 demotion comment").
- **Readiness inputs**: `dependency_readiness_for_wp(wp_id, dependencies, wp_lanes, provenance=...)` — `dependencies` come from the WP file frontmatter (see how `cli/commands/implement.py:1330-1340` obtains `declared_deps`, and `_snapshot.work_packages` for provenance); `wp_lanes` from the reduced snapshot of the **write surface**. Inside the transaction use `txn.feature_dir`; in the flat shell use `canonical_feature_dir`. The snapshot read must come from the same full-log read the shell already performs for `_derive_from_lane` where possible (NFR-004: do not add a second full read — reduce once, take both `from_lane` and `wp_lanes` from it; if `_derive_from_lane` does not expose the snapshot, extend it to return both, keeping the call-count pin green).
- No changes to edges, force, terminal rules (non-goal 6).

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP04` (based on the WP03+WP06 lanes; the resolver picks the base).

## Subtasks & Detailed Guidance

### Subtask T020 – Red-first: a dep-blocked claim succeeds today

- **Purpose**: SC-005 / D10 repro.
- **Steps**: `tests/status/test_dependency_guard.py` (new): mission dir with WP01 `in_progress` and WP02 declaring `dependencies: [WP01]` in its frontmatter; emit `planned→claimed` for WP02 through the flat shell (`emit_status_transition`) with no readiness supplied. Assert `TransitionError`. On main the claim succeeds ⇒ `xfail(strict=True)` until T022/T023.
- **Files**: `tests/status/test_dependency_guard.py`.
- **Parallel?**: No.

### Subtask T021 – Field + guard clause

- **Purpose**: FR-012.
- **Steps**:
  1. `models.py` `GuardContext`: add `dependency_ready: bool | None = None` with a docstring line stating the tri-state semantics and the fail-open rationale pointer.
  2. `wp_state.py`: in the state class(es) whose `guard_for` handles `target == Lane.CLAIMED` (from `PLANNED`) and `target == Lane.IN_PROGRESS` (from `CLAIMED`), add: `if ctx.dependency_ready is False: return False, "Transition <from> -> <to> blocked: unsatisfied dependencies (force with reason to override)"`. If `TransitionInputs` (the ctx type in `wp_state.py`) is a separate record from `GuardContext`, thread the field through the same way `subtasks_complete` is threaded (find the mapping in `transitions.py`).
  3. Unit tests in `tests/specify_cli/status/test_wp_state.py` / `test_transition_context.py`: `False` refuses on both edges; `True`/`None` pass; other edges ignore the field; `force` + actor + reason bypasses (via `check_transition`, not inside the guard).
- **Files**: `src/specify_cli/status/models.py`, `src/specify_cli/status/wp_state.py`, tests.
- **Parallel?**: No.

### Subtask T022 – Shells supply the verdict in-lock (FR-013)

- **Purpose**: The guard must not reproduce the pre-flight TOCTOU it closes.
- **Steps**:
  1. Flat shell (`emit.py`, under `feature_status_lock`, after `from_lane` derivation): compute `readiness = _resolve_dependency_readiness(canonical_feature_dir, wp_id, snapshot)` — a new small helper in `emit.py` (or in `transition_pipeline.py` as a pure function taking the snapshot + declared deps; prefer pure) that returns `DependencyReadiness | None` (`None` when the WP file declares no dependencies — that is still a verdict; return a satisfied readiness, not `None`, so the shells never send `None`). Pass to `prepare_transition(readiness=…)`.
  2. Transactional shells (`status_transition.py`, inside `BookkeepingTransaction.acquire`): same helper against `txn.feature_dir`. Batch: per request against the accumulated in-transaction state.
  3. Declared deps: read the WP file frontmatter from the **primary planning surface** for the `dependencies` list (WP files live on primary; lanes are read from the write surface). Reuse whatever helper `implement.py:1330` uses.
  4. Log one Activity Log line per out-of-map file.
- **Files**: `src/specify_cli/status/emit.py`, `src/specify_cli/coordination/status_transition.py` (out-of-map, minimal), helper location per step 1.
- **Parallel?**: No.

### Subtask T023 – Pipeline threads readiness into `GuardContext`

- **Purpose**: The single validation point consumes the verdict.
- **Steps**: in `transition_pipeline.prepare_transition`, `GuardContext(..., dependency_ready=(readiness.satisfied if readiness is not None else None))`. Flip T020's xfail. Add a pipeline-level test: `readiness` unsatisfied ⇒ `TransitionError` on `planned→claimed`; satisfied ⇒ event built.
- **Files**: `src/specify_cli/status/transition_pipeline.py` (out-of-map), `tests/status/test_dependency_guard.py`.
- **Parallel?**: No.

### Subtask T024 – Probe, force, chain, surface, replay tests

- **Purpose**: The C-004/C-005 pins and the acceptance matrix.
- **Steps** (all in `tests/status/test_dependency_guard.py` unless noted):
  1. Probe pins: call `validate_transition("planned","claimed", GuardContext(actor=RECOVERY_ACTOR, workspace_context="recovery"))` exactly as `lanes/recovery.py:78` does ⇒ `ok`; replicate `tasks_transition_core.py:337`'s force-free backward-edge probe shape ⇒ unchanged result. Also run the existing `tests/specify_cli/lanes/` recovery tests.
  2. Chain matrix: dep `approved` ⇒ claim allowed; dep `done` ⇒ allowed; dep `canceled` with operator provenance ⇒ allowed; dep `in_progress` ⇒ blocked; `for_review` ⇒ blocked; blocked + `force` with actor+reason ⇒ allowed and the event carries `force=True` + reason.
  3. Coord surface: coord-topology fixture where primary shows the dep `in_progress` but the coord surface shows `approved` (or vice versa); assert the verdict follows the coord surface (`txn.feature_dir`).
  4. Pre-lock TOCTOU: a thread flips the dep to `in_progress` while the emitter waits for the lock; assert the verdict reflects the post-lock state.
  5. Replay purity: `ast`-scan `reducer.py` for `validate_transition`/`GuardContext` ⇒ none; build a history with a claim that is now dep-illegal, `reduce()` it, run `validate_transition_legality` (`status/validate.py`) ⇒ no guard finding.
- **Files**: tests.
- **Parallel?**: Yes (alongside T021).

### Subtask T025 – Demote the six pre-flight sites; no-op resume pin; polarity note

- **Purpose**: FR-014 single-sourcing; documentation for future readers.
- **Steps**:
  1. At each site — `cli/commands/implement.py:1340`, `cli/commands/agent/workflow_executor.py:653`, `cli/commands/agent/tasks_status_view.py:228`, `orchestrator_api/commands.py:1115` and `:1440`, `runtime/next/discovery.py:150` — add a two-line comment: "Pre-flight UX only (FR-014, fsm-write-path-integrity WP04). The authoritative dependency gate is `GuardContext.dependency_ready`, resolved in-lock by the emit shells." No logic change.
  2. Pin: `implement` re-invoked on an `in_progress` WP is a no-op resume and is not re-gated (find the existing resume test in `tests/specify_cli/cli/commands/` and add the dep-blocked variant: dep regresses to `in_progress` after WP02 was legitimately claimed ⇒ resume still works).
  3. `design-notes/WP04-guard.md`: polarity decision + rationale (Q8), resolution-site rule, the helper's location, and the statement that no edge/force/terminal logic changed.
- **Files**: the six caller files (comments), tests, design note.
- **Parallel?**: No.

## Test Strategy

```bash
make test-fast
.venv/bin/pytest tests/status tests/specify_cli/status tests/specify_cli/coordination tests/specify_cli/lanes tests/specify_cli/cli/commands/agent -q
.venv/bin/pytest tests/status/test_transition_pipeline.py -q   # NFR-004 call-count pin must stay green
.venv/bin/pytest tests/architectural/test_status_module_boundary.py -q
.venv/bin/ruff check src tests && .venv/bin/mypy src/specify_cli/status/models.py src/specify_cli/status/wp_state.py src/specify_cli/status/transition_pipeline.py
```

## Risks & Mitigations

- **R4** fail-closed breaks probes → T024 step 1.
- **R5** resolved pre-lock or on the wrong surface → T024 steps 3–4.
- **NFR-004 regression** (second full read for `wp_lanes`) → reuse the derive read; the call-count pin catches it.
- **Same-mission deadlock** (gating on `done` only) → `dependency_readiness_for_wp` already accepts `approved`; matrix step 2 pins it.

## Review Guidance

- Confirm T020 was RED at the base; confirm the guard is in `wp_state.py` via the established shape and never reads `ctx.force`.
- Confirm `None` passes (probe pins) and shells never send `None`.
- Confirm readiness is computed after lock acquisition, from the write surface, without an extra full-log read.
- Confirm the six sites are comments-only diffs; design note explains the polarity.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T11:57:59Z – system – Prompt created.
- 2026-09-06T15:29:46Z – unknown – T020 RED proof on base 596396b7d: tests/status/test_dependency_guard.py::test_flat_shell_refuses_verdictless_claim_of_dep_blocked_wp -> 'Failed: DID NOT RAISE TransitionError' (verdict-less flat-shell planned->claimed of a dep-blocked WP succeeds); kept xfail(strict) until T023, then flipped GREEN.
- 2026-09-06T15:29:48Z – unknown – T021: GuardContext.dependency_ready: bool|None=None (models.py) + TransitionContext/TransitionInputs Protocol field; guard clauses in PlannedState/ClaimedState.guard_for refuse only on False (fail-OPEN on None, C-004/Q8); guards never read ctx.force. Unit tests in test_wp_state.py/test_transition_context.py.
- 2026-09-06T15:29:50Z – unknown – T022 (FR-013 verdict supplier): new pure status/dependency_verdict.py (readiness_from_snapshot, wp_lanes_from_snapshot; reuses dependency_readiness_for_wp with provenance). Out-of-map status/emit.py: _reduce_write_surface (the ONE full-log read, NFR-004), _derive_from_lane(snapshot=) keyword, _declared_dependencies (raw frontmatter 'dependencies' key on the PRIMARY planning dir; fail-closed on unparseable/malformed), _resolve_dependency_readiness; both flat shells supply the verdict in-lock. Out-of-map coordination/status_transition.py: both transactional shells resolve readiness inside the transaction against txn.feature_dir with WP file from identity.feature_dir. Shells never send None.
- 2026-09-06T15:29:51Z – unknown – T023 (out-of-map status/transition_pipeline.py): prepare_transition threads dependency_ready=None if readiness is None else readiness.satisfied into GuardContext; noqa ARG001 removed. T020 flipped GREEN.
- 2026-09-06T15:29:53Z – unknown – T024 matrix in tests/status/test_dependency_guard.py (52 tests): probe pins (recovery + FR-015 backward edge, None passes), chain matrix (approved/done/canceled+operator allowed; in_progress/for_review/canceled-synthetic blocked; force+actor+reason recorded), batch all-or-nothing, cross-thread lock-held TOCTOU (verdict reflects post-lock state), coord topology (verdict follows txn.feature_dir both directions + in-transaction order pin, one read), replay purity (reducer AST scan + now-dep-illegal history replays/audits clean).
- 2026-09-06T15:29:54Z – unknown – T025: FR-014 demotion comments (no logic change) at implement.py, workflow_executor.py, tasks_status_view.py, runtime/next/discovery.py, orchestrator_api/commands.py :1115 and :1440 (out-of-map, comments only); no-op resume pin tests/status/test_work_package_lifecycle.py::test_start_implementation_resume_is_not_regated_when_dependency_regresses; design note (polarity, resolution-site rule, helper location, non-goal 6) written to scratch design-notes/WP04-guard.md for the orchestrator to land.
- 2026-09-06T15:29:56Z – unknown – Out-of-map rationale: transition_pipeline.py = FR-013 consumer; emit.py = FR-013 verdict supplier + NFR-004 single reduce; coordination/status_transition.py = FR-013 verdict supplier (txn.feature_dir); transition_context.py = Protocol conformance for the new field; orchestrator_api/commands.py = FR-014 demotion comments; test_work_package_lifecycle.py = resume pin beside existing no_op tests.
- 2026-09-06T15:29:58Z – unknown – Verification: blast radius (status+coordination+lanes+unit/status) 2098 passed/2 skipped; agent CLI 1901 passed/1 skipped/2 xfailed; pins+touched files 327 passed; architectural gates 62 passed, whole-repo ruff-format check red on base (WP01 lock test files, none from this diff); ruff/C901/format --force-exclude clean; mypy clean on 6 status files, coordination/status_transition.py 4 pre-existing errors unchanged.
- 2026-09-06T16:24:58Z – unknown – Review cycle 1 / finding 3 (RED-proof provenance): the T020 RED run on base 596396b7d used the pre-dependency_verdict revision of tests/status/test_dependency_guard.py; the committed file imports specify_cli.status.dependency_verdict and so errors at collection on the base. Reproducible standalone shape (the reviewer's): seed WP01+WP02 planned, drive WP01 to in_progress via the flat shell, claim WP02 via the flat shell -> 'Failed: DID NOT RAISE TransitionError' on 596396b7d; the same repro raises on the lane.
- 2026-09-06T16:25:15Z – unknown – Review cycle 1 / findings 1+2: (1) status/wp_metadata.py gained the pure exported helper coerce_legacy_dependencies (WPMetadata._normalize_legacy_fields now calls it; rules moved, not duplicated); emit._coerce_declared_dependencies calls the same helper so the shells accept exactly the legacy string forms ('[]', 'WP01, WP02', bare WP01) the FR-014 pre-flight parser accepts; only values WPMetadata also refuses stay fail-closed. (2) Shape (b) chosen: emit._resolve_dependency_readiness maps a read/parse failure to dependency_verdict.unresolvable_readiness (an UNSATISFIED verdict with a self-describing marker + WARNING log) so only planned->claimed / claimed->in_progress are refused, force+actor+reason still bypasses, and ->blocked / ->canceled / review edges are never affected. Addendum: scratch wp04-planning-artifacts/WP04-guard-cycle1-addendum.md (A1-A6). Finding 4 carried to the caller-migration follow-up (A4).
- 2026-09-06T16:25:22Z – unknown – Out-of-map edit rationale (status/wp_metadata.py, not a WP04-owned file): the reviewer required the shells to reuse WPMetadata's own legacy dependencies coercion rather than a second parser; the only non-duplicating shape is to lift that coercion into a module-level pure helper in wp_metadata.py and have both the model validator and emit call it. Behaviour of WPMetadata is unchanged (its two existing legacy-normalization tests pass unmodified; new TestCoerceLegacyDependencies pins helper == model).
- 2026-09-06T16:25:31Z – unknown – Cycle 1 verification: targeted files (test_dependency_guard, test_transition_pipeline, test_emit, test_wp_metadata) 280 passed; blast radius tests/status tests/specify_cli/status tests/specify_cli/coordination tests/specify_cli/lanes tests/unit/status -n 3 --dist loadfile 2199 passed/2 skipped; tests/specify_cli/cli/commands/agent -n 3 1900 passed/1 skipped/2 xfailed/1 failed (test_tasks_move_task_pre_review_gate_parent_death::test_sigkill_of_cli_parent_preserves_lane_and_event_authority -- SIGKILL-parent timing test, passes 2/2 in isolation, ran under CPU contention; not this diff); 4 architectural gates 55 passed; test_no_legacy_terminology 10 passed; ruff check/C901/format --force-exclude clean on every changed file (whole-repo format gate still red only on WP01's five files); mypy clean on emit/dependency_verdict/transition_pipeline/wp_state/models/wp_metadata. Hand probes: dependencies '[]' claim OK; bare WP01 (approved) claim OK; corrupt frontmatter: claim REFUSED (guard msg), ->blocked OK, forced ->canceled OK, forced claim OK; live 062 WP07/WP10/WP11 resolve to () == parse_wp_dependencies []. Fixed a latent test-helper flake: _event's at-stamp wrapped every 60 events and the reducer sorts by (at, event_id), which reordered the coord test's chain once new tests shifted the counter; stamp is now monotonic.
