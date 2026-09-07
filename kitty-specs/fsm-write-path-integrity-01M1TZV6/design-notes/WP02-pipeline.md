# WP02 design note — status-owned transition pipeline and the flat shell

**Mission**: `fsm-write-path-integrity-01M1TZV6` · **WP**: WP02 · **Author**: claude-fable-5-1 (python-pedro, implementer) · **Date**: 2026-09-06

Binding inputs: `contracts/emit-pipeline.md` §1–§2, §6; `data-model.md` §4–§5; `research.md` §1 (decision Q4 `01M1V80R6F6RTMR7Y3C2WBKR32`); spec US2, FR-005, FR-018, NFR-004, C-006, C-009.

## 1. Module

`src/specify_cli/status/transition_pipeline.py` — `PreparedTransition` (frozen dataclass) and `prepare_transition(...)`.

The body is `coordination/status_transition.py::_prepare_event` (`:842-945`) promoted verbatim, in step order: alias-resolve → workspace-context default → gate inference (only `in_progress → for_review`, subtask gate only when not forced, evidence gate only when the caller left it `None`) → alias-collapse (`event=None`, `mirror_frontmatter_lane=True`) → `_build_done_evidence` → `GuardContext` → the tree's one `validate_transition` → `build_status_event(...)` with every field `_prepare_event` passes (`reason_source`, `policy_metadata`, `review_result`, `mission_id` included). `_annotation_for_request` (`status_transition.py:948`) is pure (mints a ULID and a timestamp, no I/O) and was promoted too; it populates `PreparedTransition.annotation`.

The module imports nothing from `specify_cli.coordination`; it performs zero writes, zero locks, zero git, zero fan-out (AST pins in `tests/status/test_transition_pipeline.py`; `tests/architectural/test_status_module_boundary.py` needed no change — it enumerates importers of `status.*`, not `status/` modules).

`_prepare_event` itself is untouched (WP06 owns `coordination/status_transition.py` and `status/aggregate.py`, deletes it, and proves delegation-equivalence). `tests/specify_cli/coordination` stays green untouched.

### Contract deviations (small, deliberate)

| Item | Contract §1 | Implemented | Why |
|---|---|---|---|
| `annotation` type | `StatusEvent \| None` | `InnerStateChanged \| None` | That is the real annotation type (`wp_state.annotate` returns `InnerStateChanged`); typing it as `StatusEvent` would be false. |
| Injected-I/O defaults | `= resolve_subtasks_gate_dir` / `= _infer_*` | `= None` sentinels resolving to today's helpers at call time | `resolve_subtasks_gate_dir` must stay a lazy import (the `missions` package cannot load at `status` import time — same shape the shells used before), and the `emit` helpers are resolved through the module namespace at call time so existing `monkeypatch.setattr(emit_module, ...)` tests keep working. |
| `readiness` | required keyword | `DependencyReadiness \| None = None` | Per the WP prompt: accepted and inert until WP04 adds `GuardContext.dependency_ready` and the guard. Carries a narrowly-justified `# noqa: ARG001` (same pattern as `sync_dossier`). |

## 2. Fan-out seam shape (T011/T012)

Chosen: a keyword-only **`fan_out: bool = True`** on both `emit_status_transition` and `emit_status_transition_batch`.

- Additive keyword with a default → the public contract of the 41 test importers is unchanged; no new symbol, no tuple return.
- Batch symmetry for WP06's `_fallback_emit_batch`.
- Observable contract: `fan_out=False` skips step 7 entirely (`_saas_fan_out` and `_resolved_binding_fan_out`); persistence, materialize and mirror are untouched. Pinned at the adapter registry in `tests/status/test_emit_fanout_after_adapter.py::TestFanOutSeam` (zero handler calls) and at the shell call sites in `tests/status/test_emit.py::TestFlatShellFanOutSeam`.

The deferred-callable alternative (`emit_status_transition_deferred` returning `(event, fan_out)`) was not taken: it adds a second public door for WP03's shell-proliferation gate to police and gains nothing the flag does not.

## 3. Q6 — where the five `_emit` privates land (`01M1V8J667A286GPHKTWYB1WCS`)

**Decision: the helpers stay module-private in `status/emit.py`; the pipeline consumes them through the same-package module reference (`from . import emit as _emit`, attribute-resolved at call time). Nothing becomes public.**

| Helper | Home | Used by |
|---|---|---|
| `_derive_from_lane` | `emit.py` (read) | shells only — the pipeline takes `from_lane` as a value (NFR-004) |
| `_generate_ulid` | `emit.py` | pipeline (annotation), `build_status_event`, shells |
| `_mirror_phase1_frontmatter_lane` | `emit.py` (write) | shells only — the pipeline only *requests* it (`mirror_frontmatter_lane`); it remains the tree's only `write_frontmatter` of `lane` (`test_2093_authority_invariant.py` green, unchanged) |
| `build_status_event` | `emit.py` (already public) | pipeline, collapse arm |
| `_infer_subtasks_complete` / `_infer_implementation_evidence` | `emit.py` (reads) | pipeline defaults, injectable |
| `_build_done_evidence`, `_legacy_alias_collapses_to_current_lane`, `TransitionError` | `emit.py` | pipeline |

Rationale: (a) the reads and the one write are shell concerns and belong next to the shells; (b) the same-package reference is layering-clean (C-006 forbids `status → coordination`, not `status → status`); (c) no facade widening — `status/__init__.py` is untouched (a change there needs a version bump per CLAUDE.md, and WP06's only consumer, `coordination/status_transition.py`, is an exempt plumbing file that may import the submodule directly); (d) call-time attribute resolution keeps every existing `emit_module` monkeypatch effective. The import cycle `emit ↔ transition_pipeline` is intra-package and verified from both entry orders.

Recorded via `spec-kitty agent decision resolve … --other-answer`; the Q6 marker was removed from `plan.md`.

## 4. Readiness

`prepare_transition(readiness=...)` is accepted and passed through with `None` semantics. WP04 adds the `GuardContext.dependency_ready` field and the guard, and the shells resolve readiness in-lock against their write surface (FR-013). Both `None` and a satisfied verdict are tested to pass through today.

## 5. Shells (T011/T012)

Flat single door `emit_status_transition`: lock (keyed `canonical_feature_dir.name` via `resolve_status_lock_root`, FR-004 — the same one-line change WP01 makes at the old `emit.py:634`) → `_load_mission_id` → `_derive_from_lane` once → `prepare_transition` → collapse arm (`_collapse_alias_in_place`: log + mirror + the same unpersisted synthetic event as before) or `_persist_prepared` (atomic append of event+annotation → materialize → mirror) → release → fan-out. The 300-line inline validation/build is gone; legacy-argument coercion lives in `_coerce_transition_request`.

Batch door `emit_status_transition_batch` (FR-018, Q1): identity checks for **every** member run before the lock (`canonicalize_feature_dir` consults the git worktree registry; NFR-001), then ONE `feature_status_lock` covers `_load_mission_id`, one `_derive_from_lane`, every `prepare_transition` (chaining `from_lane` in memory), the single atomic append, materialize and the mirrors; fan-out after release. All-or-nothing is preserved and pinned (`test_batch_mid_sequence_refusal_persists_nothing`).

NFR-004 pin (`test_emit_reads_log_once`, `test_batch_emit_reads_log_once_for_the_whole_batch`): `_derive_from_lane == 1` and exactly one `store.read_events` **before the append** per single emit and per batch. Reads after the append are the pre-existing durability read-back (`verify_event_readback`, one per appended event) and materialize — not pipeline cost.

## 6. Divergences found — for WP06 to adjudicate

Rule applied: keep the flat shell's observable behaviour unless the mission's own parity requirement (FR-007 / data-model S-2 / contract §2 "batch applies steps exactly as the single variant") says otherwise; record everything.

| ID | Divergence | Handling in WP02 | WP06 action |
|---|---|---|---|
| D-1 | `_prepare_event` passes `request.effective_root` to `resolve_subtasks_gate_dir`; the flat shells (single and batch) never did. The pipeline threads it. | Flat shells inject `_flat_subtasks_dir_resolver`, which drops `effective_root` — behaviour preserved verbatim. `effective_root` does survive `replace(request, feature_dir=coord_fd)` in `_fallback_emit_single._coord`, so honouring it would change which `tasks.md` the coord fallback arm reads. | Decide whether the flat shells honour `effective_root` (FR-007 parity says yes ⇒ delete the adapter and its `ARG001` note) or keep the adapter. |
| D-2 | The plain batch door alone skipped the `<execution_mode>:<root>` workspace-context default on `claimed → in_progress` (#946); `_prepare_event`, and so the transactional batch, always applied it. | **Parity taken**: the batch composes the pipeline verbatim, so the default now applies. Production callers (`status/work_package_lifecycle.py:159/:198`) always pass `workspace_context` for this edge, so only direct callers that omitted it observe it. Pinned by `test_batch_claimed_to_in_progress_defaults_workspace_context_like_every_other_door` with the #946 provenance in its docstring. | Confirm parity, or reinstate the #946 skip as an explicit pipeline policy knob if the operator wants the plain batch to fail closed on a missing workspace. |
| D-3 | Batch annotations were stamped `batch_started_at + (N + i) µs` (after every event); the pipeline stamps an annotation with its own transition's `at`. | Accepted; reducer results unchanged. The annotation shares its transition's `at` and is minted after the event, but no ULID sort order between the two is claimed: `_generate_ulid` (python-ulid `ULID()`) is random within a millisecond, not monotonic. Ordering is not load-bearing — `spec_kitty_events.diary.reduce_parsed` folds annotations in a dedicated post-transition partition pass (not a timestamp-interleaved single pass), and every `(at, event_id)` sort in the tree compares transitions with transitions only. The batch door still appends annotation rows after all transition rows (`[*events, *annotations]`). Pinned by `test_batch_annotation_shares_its_transition_timestamp` (`at` equality + snapshot lane; the former `event_id >` assertion was deleted in review cycle 1 as a flake by construction). | None expected. |
| D-4 | Batch alias-collapse members were skipped without the frontmatter mirror; the single door mirrors. The pipeline returns `mirror_frontmatter_lane=True` for both. | Batch keeps skipping (today's behaviour). | Decide whether the batch collapse arm should mirror like the single door. |
| D-5 | Batch identity `TypeError`s used to surface per request, interleaved with validation. | Now raised for all members up-front, before the lock. Same exception, same all-or-nothing. | None. |

Also inherited, not changed: `status/aggregate.py:685` still runs its own `validate_transition` before delegating to the transactional door — P-2 ("exactly once across the whole tree") holds for the flat shells now and completes when WP06 deletes the aggregate duplicate.

## 7. #3460 inner-state degrade pins (spec US2 scenario 5)

Named tests that pin the deliberate `BookkeepingWorktreeMissing` degrade; WP06 must keep them green:

- `tests/specify_cli/coordination/test_status_transition.py::test_inner_state_annotation_degrades_when_coordination_branch_missing`
- `tests/specify_cli/cli/commands/agent/test_tasks_move_task_degod.py::test_runtime_state_persistence_error_propagates` (the `_mt_emit_runtime_state` branch on `resolved_auto_commit`, #3460)

## 8. Q4 rider — ADR amendment (for WP06)

Per `research.md` §1 the ADR chain #1667 / C-004 needs one amendment paragraph naming the two senses of "authoritative": `MissionStatus` remains the *intended domain facade* for callers; `status/transition_pipeline.py::prepare_transition` is the *validation/build authority*; lock, commit ordering and fan-out timing are shell responsibilities by design (two shell kinds, explicit per-shell failure policies, C-007). WP06 writes that paragraph when it composes the transactional shells and deletes `_prepare_event`.

## 9. Tests added

- `tests/status/test_transition_pipeline.py` (new): alias resolve/collapse, gate-inference call counts (with/without force, non-review edges), evidence inference only when `None`, `effective_root` threading, `DoneEvidence` build + malformed refusal, provenance/policy/review-result/identity on the built event, `at` stamping (annotation shares the transition's `at`; no ULID sort order is asserted), workspace-context default, single `validate_transition` + refusal, readiness pass-through (`None`/satisfied), in-memory purity (no writes, lock forbidden), AST layering/purity pins with a non-vacuity mutation check, NFR-004 single + batch.
- `tests/status/test_emit.py`: `TestFlatShellFanOutSeam`, `TestFlatShellLockAndValidation` (FR-004 lock key, one `validate_transition` per emit through the shell), `TestBatchShellLock` (one acquisition held from derive through mirror, fan-out after release; mid-sequence refusal persists nothing; D-2 parity pin; D-3 annotation timestamp pin).
- `tests/status/test_emit_fanout_after_adapter.py`: `TestFanOutSeam` (zero adapter calls with `fan_out=False`, single and batch; default batch fires once per event).
