---
work_package_id: WP02
title: Flush-target fixes, red-first
dependencies: []
requirement_refs:
- C-004
- FR-005
- FR-006
- FR-007
- FR-008
- NFR-001
- NFR-004
- NFR-007
planning_base_branch: feat/dead-port-disposition
merge_target_branch: feat/dead-port-disposition
branch_strategy: Planning artifacts for this mission were generated on feat/dead-port-disposition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dead-port-disposition unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dead-port-disposition-01M1VRA2
base_commit: 97be35cc059195502284bee7f5d62789c37f3669
created_at: '2026-09-06T18:31:34.726572+00:00'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Correctness
history:
- at: '2026-09-06T16:48:26Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: debugger-debbie
authoritative_surface: src/runtime/next/
create_intent:
- tests/runtime/test_bridge_decision_log_flush.py
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/runtime_bridge.py
- src/specify_cli/events/decision_log.py
- tests/runtime/test_bridge_decision_log_flush.py
- tests/specify_cli/events/test_decision_log.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Flush-target fixes, red-first

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `debugger-debbie`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

This WP is the user-visible correctness fix of the mission and the MVP. Two paths in the `next` bridge hand decision-request events to the plain no-op seam instead of the decision-log wrap, so those requests never reach `kitty-specs/<mission>/decisions.events.jsonl`:

1. **Strict-policy buffer flush** — `runtime_bridge.py:2187` `buffer.flush(ctx.sync_emitter)`.
2. **Composition dispatch** — `runtime_bridge.py:1976` `sync_emitter=ctx.sync_emitter`.

Done means every rule F1–F7 in `contracts/decision-log-flush.md` holds:

- F1 and F2 have regression tests that you ran and **observed red** before the fix and green after (NFR-001). The red run's output is pasted into the Activity Log (T013).
- F3 (refused terminal gate writes nothing) and F4 (exactly one entry, no duplicate) are green.
- `DecisionGitLog.seed_from_snapshot` exists as a pass-through with its own unit test (F6).
- `pytest tests/runtime/test_bridge_retrospective.py tests/runtime/test_bridge_engine.py tests/runtime/test_bridge_parity.py tests/specify_cli/events/` unchanged and green (C-004: behavior preserved except these two fixes).
- No file outside `owned_files` is modified. In particular, do **not** touch the bridge's emitter import or construction sites (`:195`, `:1552`, `:2739`) — WP03 owns those edits and depends on this WP.

## Context & Constraints

- Governing ADR: `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md` §Context "A latent correctness bug" and "A second bypass"; §Decision Outcome (c).
- Contract: `kitty-specs/dead-port-disposition-01M1VRA2/contracts/decision-log-flush.md`.
- Research that binds you: `research.md` R-3 (the defect, the fixture kind, ordering / no double emit).
- Data model: `data-model.md` §State transitions (strict retrospective policy) and its four invariants.
- Code you must read before editing:
  - `src/runtime/next/runtime_bridge.py:1453-1479` (`DecideNextContext`), `:1888-1990` (`_dn_composition_dispatch`), `:2006-2055` (pre-state capture / rollback), `:2057-2106` (`_dn_terminal_retrospective_gate`), `:2108-2200` (`_dn_decision_materialize`).
  - `src/runtime/next/runtime_bridge_retrospective.py:69-149` (`_BufferingRuntimeEmitter`, `_retrospective_blocks_completion` at `:384`).
  - `src/runtime/next/runtime_bridge_engine.py:190-227` (`_emit_decision_required`), `:323-350` (`advance_run_state_after_composition` seeds the emitter it is given at `:344`).
  - `src/specify_cli/events/decision_log.py:63-190` (`DecisionGitLog`; only the two decision methods write).
  - Existing fixture idioms: `tests/runtime/test_bridge_retrospective.py:198-206` (policy monkeypatch), `tests/specify_cli/events/test_decision_log.py:85-100` (`DecisionGitLog` construction, `_decisions_file`), `tests/specify_cli/events/test_decision_log_coord.py:24-40` (`_write_coord_meta`).
- Charter: ATDD-first / `034-test-first-development` — the tests exist and are red before the fix lands. `043-close-defect-class-by-construction` — the guard that prevents recurrence is WP04's; your job is the fix plus proof.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/dead-port-disposition; completed changes must merge back into feat/dead-port-disposition.
- **Planning base branch**: feat/dead-port-disposition
- **Merge target branch**: feat/dead-port-disposition

> Execution worktrees are allocated per computed lane from `lanes.json`; run `spec-kitty agent action implement WP02 --agent <name>` and work inside the workspace it returns. This WP has no dependencies and runs in parallel with WP01.

## Subtasks & Detailed Guidance

### Subtask T007 – Test fixtures

- **Purpose**: A deterministic, engine-free harness that drives the two bridge phases with a real `DecisionGitLog` so the decision-log file is the oracle.
- **Steps**: Create `tests/runtime/test_bridge_decision_log_flush.py` with `pytestmark = [pytest.mark.regression, pytest.mark.unit, pytest.mark.fast]` and these helpers:
  1. `_strict_policy()` → `SimpleNamespace(enabled=True, timing="before_completion", failure_policy="block")`. Assert once in a sanity test that `_retrospective_seam._retrospective_blocks_completion(_strict_policy()) is True`.
  2. `_mission(tmp_path, slug)` → creates `tmp_path/"kitty-specs"/slug/` with a coord-shaped `meta.json` (copy `_write_coord_meta`'s JSON shape), and `run_dir = tmp_path/"run"` containing a minimal `state.json` (`{}` is enough if you stub capture) and an empty `run.events.jsonl`. Returns `(feature_dir, run_dir)`.
  3. `_decision_log(tmp_path, slug)` → `DecisionGitLog(repo_root=tmp_path, worktree_root=tmp_path, destination_ref=f"kitty/mission-{slug}", mission_slug=slug, inner=NullEmitter())`. Patch `specify_cli.events.decision_log.safe_commit` for the whole module (autouse fixture) so no git runs.
  4. `_ctx(tmp_path, slug, *, run_dir, feature_dir, log)` → `DecideNextContext` is `@dataclasses.dataclass(frozen=True)` (`runtime_bridge.py:1452`), so construct it by keyword: `rb.DecideNextContext(agent="tester", mission_slug=slug, result="success", repo_root=tmp_path, feature_dir=feature_dir, now="2026-09-06T00:00:00Z", mission_type="software-dev", sync_emitter=NullEmitter(), emitter_for_engine=log, origin={}, progress=None, run_ref=SimpleNamespace(run_id="run-1", run_dir=str(run_dir)), run_dir=run_dir, current_step_id="plan")`. **`sync_emitter` is a distinct plain `NullEmitter`; `emitter_for_engine` is the log wrapping a different `NullEmitter`.** That asymmetry is what makes the bug observable.
  5. `_requested_payload(...)` → build a `DecisionInputRequestedPayload` (import from `spec_kitty_events.mission_next`; copy the field set from `tests/specify_cli/events/test_decision_log.py`'s helper).
  6. `_count_requests(path)` → number of lines in `decisions.events.jsonl` whose `event_type` is `DecisionInputRequested` (0 if the file is absent).
  7. Bridge stubs (monkeypatch on `rb`): `_resolve_retrospective_policy_for_runtime` → `(policy, {}, None)`; `_dn_capture_pre_speculative_state` → `(b"{}", 0)`; `_resolve_mission_id_for_terminus` → `None`; `_run_retrospective_learning_capture` → no-op (or raising, for F3); `_materialize_decision` may stay real.
- **Files**: `tests/runtime/test_bridge_decision_log_flush.py` (new)
- **Parallel?**: No.
- **Notes**: Import the bridge as `from runtime.next import runtime_bridge as rb` and the seam as `from runtime.next import runtime_bridge_retrospective as _retrospective_seam` to match sibling tests. `run_ref` may be a `SimpleNamespace(run_id=..., run_dir=...)`; every other field is a plain value.

### Subtask T008 – F1: strict-retrospective-policy `decision_required` reaches the log (red first)

- **Purpose**: Prove the flush target bug on the exact path the ADR names.
- **Steps**:
  1. Stub `rb.runtime_next_step` with a fake that, given `emitter=`, calls `emitter.emit_decision_input_requested(_requested_payload(...))` and returns a **real `NextDecision`** (import from `runtime.next._internal_runtime.schema`) with `kind="decision_required"`, `decision_id="audit:review"`, `step_id="review"`, `question="…"`, `options=[...]`, `run_id`, `mission_key="software-dev"` (copy the constructor shape from `tests/runtime/test_bridge_engine.py:445` / `:494`). After the flush, `_dn_decision_materialize` hands that object to `rb._map_runtime_decision(...)` (`runtime_bridge.py:2199`), which reads the full `NextDecision` surface — a bare `.kind` stub will not survive the phase. If `_map_runtime_decision` still needs run-dir state you do not want to build, monkeypatch it to return a minimal `Decision` (the test's oracle is the log file, not the returned decision).
  2. Build ctx with strict retrospective policy stubs; call `rb._dn_decision_materialize(ctx)`.
  3. Assert `_count_requests(_decisions_file(tmp_path, slug)) == 1`.
  4. Run it. **Expected before T010: 0 == 1 fails.** Copy the failure line into the Activity Log.
- **Files**: `tests/runtime/test_bridge_decision_log_flush.py`
- **Parallel?**: No.
- **Notes**: The buffer captures the emit because `engine_emitter = buffer` under strict retrospective policy (`:2149-2150`); the flush at `:2187` then replays into `ctx.sync_emitter` (plain), so the log sees nothing. That is the red.

### Subtask T009 – F2: composition dispatch reaches the log (red first)

- **Purpose**: Prove the second bypass, which is independent of policy.
- **Steps**:
  1. Read `_dn_composition_dispatch` (`:1888-1990`) to find which callables it invokes before reaching the `_advance_run_state_after_composition(...)` call at `:1966-1977` (composition, guard evaluation, prompt build). Monkeypatch each on `rb` to the minimal success shape so control reaches that call. If the pre-dispatch surface is too wide, narrow the test to the call itself: monkeypatch `rb._advance_run_state_after_composition` with a spy that records the `sync_emitter` kwarg and calls `sync_emitter.emit_decision_input_requested(payload)`; then assert **both** that the log gained one entry **and** that the recorded emitter is `ctx.emitter_for_engine` (`is`). The `is` assertion is what stays meaningful after the fix.
  2. Run it. **Expected before T011: fails** (emitter is `ctx.sync_emitter`, log count 0).
- **Files**: `tests/runtime/test_bridge_decision_log_flush.py`
- **Parallel?**: No.

### Subtask T010 – Fix one: gated flush target

- **Purpose**: F1.
- **Steps**: In `src/runtime/next/runtime_bridge.py` at `:2183-2187`:
  ```python
  # Gate either passed (terminal allow) or never ran (non-terminal /
  # not opted in): flush any buffered emit calls into the decision-log-
  # wrapped engine emitter so decision events are durably recorded and
  # observers receive them in original order (ADR 2026-09-06-2 (c)).
  if buffer is not None:
      buffer.flush(ctx.emitter_for_engine)
  ```
  Re-run F1 → green. Re-run `tests/runtime/test_bridge_retrospective.py` → unchanged.
- **Files**: `src/runtime/next/runtime_bridge.py`
- **Parallel?**: No.
- **Notes**: `DecisionGitLog` forwards every emit to `inner`, so non-decision moments still reach the plain seam exactly once (F5). `flush` skips target methods that do not exist, so nothing raises.

### Subtask T011 – Fix two: composition emitter + `DecisionGitLog.seed_from_snapshot`

- **Purpose**: F2 and F6.
- **Steps**:
  1. `runtime_bridge.py:1976`: `sync_emitter=ctx.sync_emitter,` → `sync_emitter=ctx.emitter_for_engine,`. Update the comment block at `:1958-1964` to say the helper emits through the decision-log-wrapped emitter.
  2. `advance_run_state_after_composition` calls `sync_emitter.seed_from_snapshot(snapshot)` (`runtime_bridge_engine.py:344`). `DecisionGitLog` has no such method, so add to `src/specify_cli/events/decision_log.py`, in the "Delegating methods" block:
     ```python
     def seed_from_snapshot(self, snapshot: Any) -> None:
         """Pass-through: seeding is the inner seam's concern; a sink without it is fine."""
         seed = getattr(self._inner, "seed_from_snapshot", None)
         if seed is not None:
             seed(snapshot)
     ```
  3. Add to `tests/specify_cli/events/test_decision_log.py`: `test_seed_from_snapshot_delegates_to_inner` (inner = `MagicMock(spec=NullEmitter)` with a `seed_from_snapshot` attr → called once with the snapshot) and `test_seed_from_snapshot_tolerates_inner_without_seed` (inner = `MagicMock(spec=["emit_decision_input_requested"])` → no error).
  4. Re-run F2 → green.
- **Files**: `src/runtime/next/runtime_bridge.py`, `src/specify_cli/events/decision_log.py`, `tests/specify_cli/events/test_decision_log.py`
- **Parallel?**: No.

### Subtask T012 – F3 and F4

- **Purpose**: Prove rollback is intact and there is no double write.
- **Steps**:
  1. F3 `test_strict_policy_refused_terminal_gate_writes_nothing`: fake `runtime_next_step` emits `emit_decision_input_requested` **and** `emit_mission_run_completed` into the given emitter and returns `kind == terminal`; monkeypatch `rb._run_retrospective_learning_capture` to raise `RuntimeError("gate refused")`; monkeypatch `rb._dn_rollback_buffered_run_state` with a spy. Call `_dn_decision_materialize`; assert the returned decision is `blocked`, `_count_requests == 0`, the rollback spy was called once, and the inner `NullEmitter` of the log never saw `emit_mission_run_completed` (wrap inner in a recording subclass).
  2. F4 `test_gated_flush_does_not_duplicate`: same as F1; assert `_count_requests == 1` and additionally that a second call to `buffer.flush` (obtain the buffer by spying `rb._BufferingRuntimeEmitter`) is a no-op. If capturing the buffer is awkward, the count assertion alone satisfies NFR-004.
- **Files**: `tests/runtime/test_bridge_decision_log_flush.py`
- **Parallel?**: No.

### Subtask T013 – Red→green evidence

- **Purpose**: NFR-001 is only satisfied if the red run is on record.
- **Steps**: Append to the Activity Log: the exact pytest command, the failing assertion lines from the pre-fix run of F1 and F2, and the passing counts after T010/T011. Then run the full check list in Test Strategy and record counts.
- **Files**: this prompt's Activity Log.

## Test Strategy

```bash
# Red (after T008/T009, before T010/T011) — expect 2 failed:
.venv/bin/pytest tests/runtime/test_bridge_decision_log_flush.py -q -p no:cacheprovider
# Green (after T012):
.venv/bin/pytest tests/runtime/test_bridge_decision_log_flush.py tests/specify_cli/events/ -q -p no:cacheprovider
.venv/bin/pytest tests/runtime/test_bridge_retrospective.py tests/runtime/test_bridge_engine.py tests/runtime/test_bridge_parity.py tests/runtime/test_bridge_decide_next.py -q -p no:cacheprovider
.venv/bin/ruff check src/runtime/next/runtime_bridge.py src/specify_cli/events/decision_log.py tests/runtime/test_bridge_decision_log_flush.py
.venv/bin/mypy src/specify_cli/events/decision_log.py
```

## Risks & Mitigations

- **`_map_runtime_decision` reads more than `.kind`** → return a real `NextDecision` from the fake engine step (T008 step 1), or monkeypatch the mapper.
- **`_dn_composition_dispatch` pre-dispatch surface is wide** → fall back to the spy-on-`_advance_run_state_after_composition` shape in T009; the `is ctx.emitter_for_engine` assertion is the durable proof.
- **Parity oracle expectations** — `tests/runtime/test_bridge_parity.py` asserts on the *answer-path* sync sink (`:1165-1166`), not on gated decide-next runs; if any parity test asserts gated-path events in the sync sink, report it in the Activity Log and stop; do not weaken the assertion.
- **`safe_commit` firing in tests** → module-level autouse patch on `specify_cli.events.decision_log.safe_commit`.

## Review Guidance

- Confirm the Activity Log contains a genuine red run (assertion text), not a narrative claim.
- Confirm exactly two production lines changed in `runtime_bridge.py` (`:1976`, `:2187`) plus comments; the import at `:195` and construction sites are untouched.
- Confirm `DecisionGitLog.seed_from_snapshot` is a pure pass-through.
- Confirm F3 asserts both "no log write" and "rollback called".

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append at the end. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`.

- 2026-09-06T16:48:26Z – system – Prompt created.
- 2026-09-06T18:58:00Z – claude/debugger-debbie – Implemented T007–T012 in commit 585f73d79 (worktree lane-b). Production diff: `runtime_bridge.py:1976` → `sync_emitter=ctx.emitter_for_engine`; `:2189` → `buffer.flush(ctx.emitter_for_engine)` (+ comment blocks); `decision_log.py` + `DecisionGitLog.seed_from_snapshot` pass-through. New `tests/runtime/test_bridge_decision_log_flush.py` (fixtures, sanity, F1–F4); two F6 tests in `tests/specify_cli/events/test_decision_log.py`. **Red-first evidence (T013)** — command: `PYTHONPATH=$PWD/src PWHEADLESS=1 timeout 600 .venv/bin/pytest tests/runtime/test_bridge_decision_log_flush.py -q -p no:cacheprovider`. Pre-fix run (two earlier wrong-reason reds from fixture defects were fixed before any production edit): `test_strict_policy_decision_required_reaches_decision_log` → `AssertionError: buffered DecisionInputRequested must be appended to the decision log exactly once / assert 0 == 1`; `test_composition_dispatch_decision_required_reaches_decision_log` → `AssertionError: composition dispatch must emit through the decision-log wrap / assert <_RecordingNullEmitter> is <DecisionGitLog>` (plus `AttributeError: '_RecordingNullEmitter' object has no attribute 'seed_from_snapshot'` from the helper seeding the plain seam) — `2 failed, 1 passed`. Post-fix: flush + decision_log tests 39 passed; flush file alone 5 passed; `test_bridge_retrospective.py test_bridge_engine.py test_bridge_parity.py test_bridge_decide_next.py tests/specify_cli/events/` 162 passed, 1 failed — the failure is `test_bridge_decide_next.py:672`, a pre-existing assertion that pinned the F2 defect (`is ctx.sync_emitter`); corrected as a declared one-token out-of-map edit (coupled to the `:1976` fix) in a follow-up commit. ruff (4 touched files + diff-scoped sweep) exit 0; mypy `decision_log.py` 0 errors (13 pre-existing in transitively-checked `_internal_runtime/engine.py`/`schema.py`, untouched); terminology grep empty.
