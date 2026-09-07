---
work_package_id: WP02
title: Status-Owned Transition Pipeline + Flat Shell
dependencies: []
requirement_refs:
- C-006
- C-009
- FR-005
- FR-018
- NFR-004
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-fsm-write-path-integrity-01M1TZV6
base_commit: 7b90adcfdaf4ab5ef5229fa466bb6091f5769a07
created_at: '2026-09-06T12:14:35.880563+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
phase: Wave 0 - Pipeline extraction (mission core, part 1)
agent: claude
history:
- at: '2026-09-06T11:57:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent:
- src/specify_cli/status/transition_pipeline.py
- tests/status/test_transition_pipeline.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/transition_pipeline.py
- src/specify_cli/status/emit.py
- tests/status/test_transition_pipeline.py
- tests/status/test_emit.py
- tests/status/test_emit_durability.py
- tests/status/test_emit_fanout_after_adapter.py
- tests/specify_cli/status/test_emit.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Status-Owned Transition Pipeline + Flat Shell

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

This is the first half of the mission's core (spec "WP02", dossier D5). It creates the **named validation-and-event-build authority** (decision Q4, `01M1V80R6F6RTMR7Y3C2WBKR32`): one pure, I/O-parameterized pipeline in `status/`, and composes the **flat/primary shell** over it. WP06 will compose the transactional shells and delete the old `_prepare_event`.

Done means:

1. `src/specify_cli/status/transition_pipeline.py` exists with `PreparedTransition` and `prepare_transition(...)` exactly per `contracts/emit-pipeline.md` §1; it imports nothing from `specify_cli.coordination`.
2. `emit_status_transition` (`src/specify_cli/status/emit.py:508`) and `emit_status_transition_batch` (`:808-960`) compose the pipeline; the batch door acquires `feature_status_lock` (FR-018, decision Q1).
3. The flat shell can be told not to fan out (`fan_out: bool = True` or a returned deferred callable) — WP06's coord fallback arm needs this to close the phantom fan-out.
4. NFR-004 pin: `_derive_from_lane` is invoked at most once per emit and reads the full log exactly once (call-count test, not timing).
5. `tests/architectural/test_status_module_boundary.py` and `tests/architectural/test_2093_authority_invariant.py` are green; the phase-gated frontmatter `lane` mirror is still the tree's only `write_frontmatter` of `lane`.
6. Q6 (`01M1V8J667A286GPHKTWYB1WCS`, where the five `_emit` privates land) is decided, recorded in `design-notes/WP02-pipeline.md`, resolved via the decision CLI, and its marker removed from `plan.md`.

## Context & Constraints

- Spec US2, FR-005, FR-018, NFR-004, C-006, C-009. Contract `contracts/emit-pipeline.md` §1–§2, §6. Data model §4–§5. Research §1 (why the pipeline, six options).
- **The source to promote**: `_prepare_event` at `src/specify_cli/coordination/status_transition.py:842-945`. Read it line by line. It already IS the shared core (alias-resolve → infer gates → alias-collapse → build evidence → `validate_transition` → `build_status_event`) and reaches into five `_emit` privates: `_derive_from_lane`, `_generate_ulid`, `_mirror_phase1_frontmatter_lane`, `build_status_event`, `_infer_subtasks_complete` (plus `_infer_implementation_evidence`, `_build_done_evidence`, `_legacy_alias_collapses_to_current_lane`).
- **Do NOT edit `coordination/status_transition.py` or `status/aggregate.py`** — WP06 owns them. `_prepare_event` continues to exist until WP06 deletes it; the two must be behaviourally identical, which WP06 proves with delegation-equivalence tests. To make that proof easy, promote verbatim and keep step order.
- **Layering (C-006)**: `status` never imports `coordination`. `tests/architectural/test_status_module_boundary.py` enforces it; your new module must pass it without a new exemption.
- **Q6 hard constraint**: `_mirror_phase1_frontmatter_lane` must remain the tree's ONLY `write_frontmatter` of `lane` (`tests/architectural/test_2093_authority_invariant.py`). Wherever it lands, do not add a second writer.
- **NFR-004 / Q7**: preserve cost; no snapshot-anchored read.
- **WP01 touches `emit.py:634`** (the lock-argument line, `feature_status_lock(... feature_dir.name ...)`). Preserve that argument when you refactor the shell; if WP01 has not landed yet, key the lock on `canonical_feature_dir.name` yourself — it is the FR-004 end state either way.
- `emit_status_transition` is `# NOSONAR` for parameter count and near the C901 ceiling: extract, do not grow.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP02`.

## Subtasks & Detailed Guidance

### Subtask T009 – Create `status/transition_pipeline.py`

- **Purpose**: FR-005 — the one pure pipeline.
- **Steps**:
  1. Create the module with a docstring naming it the single validation/build authority and citing decision `01M1V80R6F6RTMR7Y3C2WBKR32` and the C-006 direction.
  2. Define `@dataclass(frozen=True) class PreparedTransition: event: StatusEvent | None; resolved_lane: str; annotation: StatusEvent | None; mirror_frontmatter_lane: bool`.
  3. Define `prepare_transition(*, request, feature_dir, mission_slug, mission_id, from_lane, readiness=None, at=None, resolve_subtasks_dir=..., infer_subtasks_complete=..., infer_implementation_evidence=...) -> PreparedTransition` — the signature in `contracts/emit-pipeline.md` §1. `readiness` is accepted now (typed `DependencyReadiness | None`, from `specify_cli.core.dependency_graph`) and **passed through as `None` semantics** until WP04 wires the guard; do not add the `GuardContext` field yourself.
  4. Body = `_prepare_event` promoted verbatim: raise `TypeError` on missing `wp_id/to_lane/actor`; alias-resolve; workspace-context default; gate inference only when `not force and from_lane == IN_PROGRESS and resolved == FOR_REVIEW` (keep the `resolve_subtasks_gate_dir` seam with `effective_root=request.effective_root`); alias-collapse ⇒ `PreparedTransition(event=None, resolved_lane, annotation=None, mirror_frontmatter_lane=True)` — the pipeline **returns the instruction to mirror; it does not call `_mirror_phase1_frontmatter_lane`** (that is a write; shells do it); evidence build; `validate_transition` exactly once; `build_status_event(...)` with every field `_prepare_event` passes today (including `reason_source`, `policy_metadata`, `review_result`).
  5. Annotation: `_annotation_for_request` lives in `status_transition.py:948` — read it; if it is pure (builds a `StatusEvent` from the request), promote it too and populate `annotation`; if it touches I/O, leave it in WP06's hands and set `annotation=None` with a `# WP06` note.
  6. Q6: decide where the helpers live. Recommended: keep them in `emit.py` as module-private and import them into the pipeline (`from specify_cli.status import emit as _emit` inside `status/` is fine — same package); do not make them public. Record the decision (T013).
- **Files**: `src/specify_cli/status/transition_pipeline.py` (new).
- **Parallel?**: No.
- **Notes**: Zero writes, zero locks, zero git, zero fan-out in this module. Put that sentence in the module docstring and a test (T014) enforces it.

### Subtask T010 – Pipeline unit tests

- **Purpose**: Sonar new-code coverage + the behavioural contract.
- **Steps**: `tests/status/test_transition_pipeline.py` (new) using `tmp_path` mission dirs and injected fakes:
  - alias `doing` → `in_progress` resolved; alias-collapse when already there ⇒ `event is None`, `mirror_frontmatter_lane is True`;
  - gate inference invoked ONLY for `in_progress→for_review` without force (assert fakes' call counts);
  - `implementation_evidence_present` inferred only when `None`;
  - evidence dict → `DoneEvidence` via `_build_done_evidence`;
  - `validate_transition` called exactly once (wrap it); refusal ⇒ `TransitionError`;
  - `build_status_event` receives `reason_source`, `policy_metadata`, `review_result`, `mission_id`;
  - missing `wp_id` ⇒ `TypeError`;
  - `readiness=None` and `readiness=<satisfied>` both pass through (post-WP04 the unsatisfied case is tested there).
- **Files**: `tests/status/test_transition_pipeline.py`.
- **Parallel?**: No.

### Subtask T011 – Flat/primary shell composes the pipeline; fan-out seam

- **Purpose**: FR-005 second half for the flat shell; the seam WP06 needs for FR-008.
- **Steps**:
  1. In `emit_status_transition` (`emit.py:508-806`): under the existing `feature_status_lock`, keep step order — derive `from_lane` once (`:645`), call `prepare_transition(...)`, then: if `event is None` → mirror only (existing alias-collapse behaviour, verify the current code's return value for that arm and keep it), else atomic append → `materialize` → `_mirror_phase1_frontmatter_lane`. Release. Then step 7 fan-out.
  2. Add `fan_out: bool = True` keyword (keyword-only, default preserves behaviour). When `False`, skip `_saas_fan_out` and `_resolved_binding_fan_out` and return the event; the caller (WP06's coord arm) fans out after its commit. Alternative acceptable shape: return `(event, deferred_fan_out: Callable[[], None])` from a new sibling `emit_status_transition_deferred(...)` and keep the public signature untouched — choose the one that keeps `emit_status_transition`'s public contract byte-stable for its 41 test importers; document the choice in the design note.
  3. Delete the now-duplicated inline validation/build code from the shell. Extract helpers so the function stays ≤15 complexity; the `# NOSONAR` parameter-count comment stays.
  4. Update `tests/status/test_emit.py` / `tests/specify_cli/status/test_emit.py` only where they asserted internal call shapes; behaviour assertions must pass unchanged. Add a test that `fan_out=False` records zero adapter calls (`tests/status/test_emit_fanout_after_adapter.py` has the adapter-recording fixture pattern).
- **Files**: `src/specify_cli/status/emit.py`, tests above.
- **Parallel?**: Yes (with T012, different functions in the same file — coordinate hunks).

### Subtask T012 – Batch door takes the lock and composes the pipeline (FR-018, Q1)

- **Purpose**: `emit_status_transition_batch` (`emit.py:808-960`) is confirmed lockless (zero `feature_status_lock` in the body; appends via `append_event_stream_atomic_verified` ~`:934`).
- **Steps**:
  1. Acquire `feature_status_lock(resolve_status_lock_root(feature_dir, repo_root), feature_dir.name)` ONCE around the per-request loop + the single atomic append + materialize + mirrors. Release before fan-out.
  2. Per request: derive `from_lane` from the **in-memory accumulated state** the batch already tracks (do not re-read the log per request — that would break NFR-004's "one full read"); call `prepare_transition`; collect events/annotations; apply the alias-collapse arm as today.
  3. Preserve the batch's failure policy (an invalid request in the middle: check current behaviour — all-or-nothing before any append — and keep it; write a test pinning it).
  4. Honour the same `fan_out` seam as T011 for symmetry (WP06's `_fallback_emit_batch` needs it).
  5. Test: lock-held during the batch append (flip WP01's xfail if it has landed; otherwise add the assertion here and WP01's parametrized test will pick it up).
- **Files**: `src/specify_cli/status/emit.py`, `tests/status/test_emit.py`.
- **Parallel?**: Yes (with T011).

### Subtask T013 – NFR-004 call-count pin and the Q6 design note

- **Purpose**: Structural cost guarantee; decision hygiene.
- **Steps**:
  1. Test: wrap `_derive_from_lane` and the store read (`read_events`/`read_event_stream`) with counters; one single emit ⇒ derive==1, full read==1; one batch of N ⇒ derive≤1 per request and full read==1 total. Put it in `tests/status/test_transition_pipeline.py` or `test_emit.py`.
  2. Write `kitty-specs/fsm-write-path-integrity-01M1TZV6/design-notes/WP02-pipeline.md`: module name, the fan-out seam shape chosen, the Q6 landing decision with rationale, the "readiness accepted, wired in WP04" note, and a pointer to WP06 for the ADR-amendment paragraph (Q4).
  3. `spec-kitty agent decision resolve 01M1V8J667A286GPHKTWYB1WCS --mission fsm-write-path-integrity-01M1TZV6 --final-answer "<choice>"`; delete the Q6 `[NEEDS CLARIFICATION …]` line from `plan.md` (one-line diff); run `spec-kitty agent decision verify --mission fsm-write-path-integrity-01M1TZV6` ⇒ clean.
- **Files**: tests, design note, `plan.md` (one line).
- **Parallel?**: No.

### Subtask T014 – Boundary and invariant pins

- **Purpose**: C-006 and the 2093 invariant, enforced for the new module.
- **Steps**:
  1. Run `.venv/bin/pytest tests/architectural/test_status_module_boundary.py -q`. If the boundary test enumerates `status/` modules explicitly, add `transition_pipeline.py` to the enforced set (that test file is not in your owned files — a one-line add is acceptable with an Activity Log rationale; if the change is larger, stop and report).
  2. Add a focused test (in `tests/status/test_transition_pipeline.py`) that parses `transition_pipeline.py` with `ast` and asserts: no `import`/`from` of `specify_cli.coordination`, no `open(`, no `feature_status_lock`, no `subprocess`.
  3. Run `.venv/bin/pytest tests/architectural/test_2093_authority_invariant.py -q` — must be green with no change.
- **Files**: `tests/status/test_transition_pipeline.py`; possibly one line in `tests/architectural/test_status_module_boundary.py`.
- **Parallel?**: No.

## Test Strategy

```bash
make test-fast
.venv/bin/pytest tests/status tests/specify_cli/status tests/specify_cli/coordination -q
.venv/bin/pytest tests/architectural/test_status_module_boundary.py tests/architectural/test_2093_authority_invariant.py tests/architectural/test_no_legacy_status_emit_callers.py -q
.venv/bin/ruff check src/specify_cli/status tests/status && .venv/bin/mypy src/specify_cli/status/transition_pipeline.py src/specify_cli/status/emit.py
```

`tests/specify_cli/coordination` is in your blast radius because `_prepare_event` still calls `_emit` helpers you may move — it must stay green untouched.

## Risks & Mitigations

- **Behaviour drift vs `_prepare_event`**: promote verbatim; WP06 adds delegation-equivalence tests; if you find a genuine difference between the flat shell's inline logic and `_prepare_event` (there is at least one: `_prepare_event` passes `effective_root` to `resolve_subtasks_gate_dir`, the flat shell at `emit.py:653` does not), **keep the flat shell's current observable behaviour** and record the divergence in the design note for WP06 to adjudicate. Do not silently "fix" it here.
- **41 test importers of the plain door**: keep the public signature stable.
- **Shared file with WP01** (`emit.py:634` lock argument): merge WP01 first if both are ready; otherwise rebase carefully.

## Review Guidance

- Pipeline module: pure (AST test), verbatim step order, one `validate_transition`.
- Flat shell: no inline validation left; lock held from derive through mirror; fan-out after release; `fan_out=False` path covered.
- Batch door: lock acquired once; one full-log read; failure policy pinned.
- NFR-004 test present and green; boundary/2093 tests green; Q6 resolved, marker gone, `decision verify` clean.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T11:57:59Z – system – Prompt created.
- 2026-09-06T12:54:18Z – claude-fable-5-1 – shell_pid=53806 – WP02 implemented on lane-b (aaf65f7f4 + 8768aa0d7): status/transition_pipeline.py (prepare_transition, PreparedTransition) promoted verbatim from _prepare_event; emit_status_transition and emit_status_transition_batch compose it; batch door now takes feature_status_lock once (FR-018); lock keyed on feature_dir.name (FR-004); fan_out=True keyword seam on both doors; Q6 resolved (helpers stay module-private in status/emit.py). Verification: tests/status+tests/specify_cli/status+tests/specify_cli/coordination+3 architectural = 1868 passed/1 skipped; make test-fast recipe via .venv/bin/pytest = 1679 passed; ruff 0; mypy 0. Planning artifacts (design-notes/WP02-pipeline.md, plan.md Q6 marker removal, WP prompt Activity Log) could not stay on the lane branch (move-task gate) and are handed to the orchestrator as a patch for missions/coreloop-proto-missions.
- 2026-09-06T13:20:26Z – unknown – Review cycle 1 (af81e2072): F1 ruff format on emit.py + test_transition_pipeline.py, format gate green (111 passed incl. test_ruff_format_enforcement). F2 deleted non-monotonic ULID ordering assertion in test_emit.py, replaced sibling '<' assertion in test_transition_pipeline.py with distinctness check, reworded pipeline step-7 comment; corrected D-3 paragraph handed to orchestrator for the planning branch. tests/status + specify_cli/status + coordination: 1853 passed, 1 skipped; ruff/mypy clean.
