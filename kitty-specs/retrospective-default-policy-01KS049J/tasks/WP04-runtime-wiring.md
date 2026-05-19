---
work_package_id: WP04
title: 'Runtime wiring: default + strict gate flows'
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-001
- FR-005
- FR-008
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts were generated on main; completed changes must merge back into main. Execution worktrees are allocated per computed lane from lanes.json after finalize-tasks.
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
phase: Runtime
assignee: ''
agent: claude
history:
- timestamp: '2026-05-19T13:29:59Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/runtime_bridge.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/next/_internal_runtime/retrospective_terminus.py
- tests/next/test_retrospective_terminus_wiring.py
- tests/integration/retrospective/**
role: implementer
tags: []
---

# Work Package Prompt: WP04 — Runtime Wiring (Default + Strict Gate Flows)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Replace `facilitator_callback=None` with the real generator + policy pipeline. Implement the two completion flows: default (post-completion best-effort with warn-on-failure) and strict (pre-completion gate with `failure_policy: block`). Anchor evaluation at the canonical "mission completion" point per data-model.md.

## Context

This is the load-bearing wiring change that makes the rest of the mission visible to end users. The runtime today:

- `next/runtime_bridge.py` calls `run_terminus(..., facilitator_callback=None, ...)`. Enabled strict paths fail closed.
- `next/_internal_runtime/retrospective_terminus.py` is the terminus that consumes (or would consume) the callback.

References:
- ADR § Mission completion: [`architecture/3.x/adr/2026-05-19-1-retrospective-default-policy-architecture.md`](../../../architecture/3.x/adr/2026-05-19-1-retrospective-default-policy-architecture.md)
- Canonical "mission completion" definition: [data-model.md § Mission completion](../data-model.md#mission-completion-canonical-definition)
- State transitions: [data-model.md § State transitions](../data-model.md#state-transitions)
- Default vs strict scenarios: [spec.md User Scenarios](../spec.md#user-scenarios--testing)

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Execution worktree resolved via `lanes.json` after `finalize-tasks`.

## Subtasks

### T018 — Replace `facilitator_callback=None` with real wiring

**Purpose**: The structural fix. After this subtask, the call graph from `runtime_bridge.py` reaches the real generator + writer + event emitter.

**Steps**:

1. In `src/specify_cli/next/runtime_bridge.py`, locate the `facilitator_callback=None` call site (likely a single call to `run_terminus(...)`).
2. Import from the WP01-WP03 surfaces:
   ```python
   from specify_cli.retrospective import (
       resolve_policy, default_policy, RetrospectivePolicy, PolicyResolutionError,
       generate_retrospective, write_record,
       emit_captured, emit_capture_failed,
   )
   ```
3. Build a `facilitator_callback` closure that takes the mission context the terminus passes:
   ```python
   def facilitator_callback(mission_ctx):
       try:
           policy, source_map = resolve_policy(repo_root)
       except PolicyResolutionError as exc:
           # Default policy degrades to warn; strict path bubbles up.
           return RetrospectiveCallbackResult(
               status="policy_resolution_failed",
               error=exc, policy=default_policy(), source_map={...},
           )
       # ... (T019/T020 implement the success/failure branches)
   ```
4. Update `run_terminus(..., facilitator_callback=facilitator_callback, ...)`.
5. Verify the wiring test (T023) catches a regression if anyone reintroduces `None` here.

**Files**:
- `src/specify_cli/next/runtime_bridge.py` (extend, ~80 lines added; the call-site change itself is ~3 lines, but the closure adds ~50)

**Validation**:
- [ ] No call site passes `facilitator_callback=None` for enabled-policy paths
- [ ] Import graph: `runtime_bridge` depends on the WP01-WP03 surfaces

---

### T019 — Default post-completion flow

**Purpose**: Under default policy, mission completion attempts generation, writes the record on success, emits an event either way, and never blocks.

**Steps**:

1. In `retrospective_terminus.py` (or `runtime_bridge.py`, whichever owns the orchestration today — keep responsibilities consistent), implement the default flow per the state transition diagram:
   ```
   if not policy.enabled: return (no-op)
   try:
       record = generate_retrospective(mission_handle, policy, repo_root)
       write_record(record, mode="error", repo_root=repo_root)  # at completion time, record should not exist
       emit_captured(record, repo_root, provenance_kind="runtime_post_completion", actor=runtime_actor)
       return CallbackResult(status="captured")
   except (Exception) as exc:
       emit_capture_failed(
           mission_id, mission_slug, failure_category=classify(exc),
           failure_message=str(exc), remediation_hint=hint_for(exc),
           policy_source=source_map,
           attempted_provenance_kind="runtime_post_completion",
       )
       log.warning(...)
       return CallbackResult(status="failed_but_continuing")
   ```
2. `classify(exc)`:
   - `RecordExistsError` (rare at completion time but possible if backfill ran first): `failure_category="other"`, hint to re-run with `--overwrite`
   - `PolicyResolutionError`: `failure_category="policy_resolution_error"`, hint with source path
   - `FileNotFoundError`/`IsADirectoryError`: `failure_category="missing_artifacts"`, hint pointing at `spec-kitty migrate normalize-lifecycle`
   - Other → `failure_category="generator_exception"`, full message in logs (NOT in event payload)
3. The terminus returns success to its caller; mission completion proceeds.

**Files**:
- `src/specify_cli/next/_internal_runtime/retrospective_terminus.py` (extend, ~100 lines)

**Validation**:
- [ ] Default policy + healthy mission → record written + `RetrospectiveCaptured` event + mission completes
- [ ] Default policy + generator throws → `RetrospectiveCaptureFailed` event + mission still completes (NOT blocked)
- [ ] Default policy + `enabled: false` → no events, no record, mission completes silently

---

### T020 — Strict pre-completion gate (`timing: before_completion + failure_policy: block`)

**Purpose**: Under strict policy, generation must succeed before completion proceeds. Failure blocks with a structured reason citing policy_source. `--skip-retrospective` is the documented bypass with logged actor/provenance.

**Steps**:

1. Detect strict mode: `policy.timing == "before_completion" and policy.failure_policy == "block"`.
2. Strict flow:
   ```
   if not policy.enabled: return (no-op — disabled means no gate)
   try:
       record = generate_retrospective(...)
       write_record(record, mode="error", ...)
       emit_captured(... provenance_kind="runtime_strict_gate")
       return CallbackResult(status="captured", gate_passed=True)
   except Exception as exc:
       emit_capture_failed(... attempted_provenance_kind="runtime_strict_gate")
       return CallbackResult(
           status="gate_blocked",
           gate_passed=False,
           block_reason=format_block_reason(exc, source_map),
       )
   ```
3. The caller (in `runtime_bridge.py` or `merge.py` orchestration) inspects `gate_passed`. If False, raise a `RetrospectiveGateBlocked(reason)` exception that the CLI command converts to a structured exit-1 with the message:
   ```
   Retrospective gate blocked completion.
   Policy: failure_policy=block, timing=before_completion
     resolved from: <source_map for failure_policy and timing>
   Failure: <failure_category> — <failure_message>
   Remediation: <remediation_hint>
   To bypass once: re-run with --skip-retrospective (logged in event log).
   ```
4. Add `--skip-retrospective` flag to the completing command (typically `spec-kitty merge`, but confirm by grepping for the `MissionCompleted` emit site). When set:
   - Bypass the gate entirely
   - Emit a `RetrospectiveSkipped` event (define alongside Captured/Failed in WP03's events.py) with actor + reason
   - Mission completion proceeds

**Files**:
- `src/specify_cli/next/_internal_runtime/retrospective_terminus.py` (extend, ~100 lines)
- `src/specify_cli/retrospective/events.py` (extend with `RetrospectiveSkipped` event type; WP03's owned_files include this file — coordinate at merge time)

**Validation**:
- [ ] Strict policy + healthy mission → record + `RetrospectiveCaptured(provenance_kind="runtime_strict_gate")` + mission completes
- [ ] Strict policy + generator fails → `RetrospectiveCaptureFailed` + `RetrospectiveGateBlocked` exception → CLI exits 1 with the formatted message
- [ ] Strict policy + `--skip-retrospective` → `RetrospectiveSkipped` event with actor/reason; mission completes

**Note on owned-files overlap**: WP03 owns `events.py`. The `RetrospectiveSkipped` event type belongs there. Coordinate by adding it in WP03 (extend T015's scope to include the third event type) and importing in this WP. Update WP03's owned_files only via merge of both PRs onto main; do not edit WP03 files from this WP's worktree.

---

### T021 — `policy_source` attribution on every event

**Purpose**: Every `RetrospectiveCaptured`, `RetrospectiveCaptureFailed`, `RetrospectiveSkipped` event MUST carry the resolved `policy_source` snapshot.

**Steps**:

1. Thread the `source_map` from `resolve_policy()` through to every `emit_*` call.
2. The emit helpers in WP03 already accept `policy_source: dict[str, str]` — pass the source_map verbatim.
3. Source map values use the conventions from [data-model.md § Resolution rules](../data-model.md#resolution-rules):
   - `".kittify/config.yaml#retrospective.<key>"`
   - `"<charter-path>:retrospective.<key>"`
   - `"<default>"`
   - `"<env:SPEC_KITTY_RETROSPECTIVE>"` / `"<env:SPEC_KITTY_MODE>"`
   - `"<resolution_error>"` (when policy resolution failed)

**Files**:
- `src/specify_cli/next/_internal_runtime/retrospective_terminus.py` (light additions, ~20 lines)

**Validation**:
- [ ] Every emitted retrospective event in integration tests has a non-empty `policy_source`
- [ ] When charter is absent and config is absent: all leaf keys in `policy_source` are `"<default>"`

---

### T022 — Anchor gate evaluation at canonical "mission completion"

**Purpose**: Per data-model.md, the strict gate fires immediately before `MissionCompleted` would otherwise emit, after all WPs terminal AND merge has landed.

**Steps**:

1. Locate the `MissionCompleted` event emit site (grep for `MissionCompleted` or the existing terminus completion path).
2. The retrospective gate sits in the call sequence as:
   ```
   ... merge succeeded
   ... all WPs in terminal lanes (done/canceled) verified
   --- gate evaluation point ---
   retrospective_terminus.run(policy, mission_ctx)  # T019/T020 dispatch
       if gate_blocked: raise RetrospectiveGateBlocked(...)
   --- gate passed ---
   emit MissionCompleted(...)
   ```
3. This means the order is: (a) all WPs terminal, (b) merge written, (c) retrospective gate, (d) `MissionCompleted`. Not (a)→(c)→(b)→(d) and not (b)→(d)→(c).
4. Verify the existing completion path satisfies (a) AND (b) before reaching the gate. If not, this is a wiring bug — surface in review.
5. `--skip-retrospective` modifies (c) to a no-op-with-Skipped-event, NOT a no-op-without-event.

**Files**:
- `src/specify_cli/next/runtime_bridge.py` (light additions, ~20 lines for the precondition check)
- `src/specify_cli/next/_internal_runtime/retrospective_terminus.py` (the orchestration)

**Validation**:
- [ ] Integration test: a strict-blocked mission has no `MissionCompleted` event in the event log
- [ ] Integration test: a strict-passed mission has both `RetrospectiveCaptured` AND `MissionCompleted`, in that order (by lamport)
- [ ] Integration test: a strict-skipped mission has `RetrospectiveSkipped` AND `MissionCompleted`, in that order

---

### T023 — Wiring test + integration tests

**Purpose**: Lock the wiring fix structurally AND functionally.

**Steps**:

1. **Wiring test** at `tests/next/test_retrospective_terminus_wiring.py`:
   ```python
   def test_runtime_bridge_does_not_pass_facilitator_callback_none_for_enabled_policy():
       # Inspect the actual call site or use mock.patch to capture the call
       # Assert: when policy.enabled is True, facilitator_callback is not None
   ```
   Use either AST inspection of `runtime_bridge.py` (more brittle) or a mock-based test that captures `run_terminus`'s `facilitator_callback` argument.

2. **Integration tests** at `tests/integration/retrospective/`:
   - `test_default_flow_healthy.py` — scaffold a mission in `tmp_path` with realistic artifacts; run the completion path; assert record on disk + `RetrospectiveCaptured` event + `MissionCompleted` event
   - `test_default_flow_generator_failure.py` — break the mission (e.g. remove `status.events.jsonl`); assert warn + `RetrospectiveCaptureFailed` + mission completes
   - `test_strict_flow_block.py` — strict policy + broken mission → `RetrospectiveGateBlocked` raised; no `MissionCompleted` emitted
   - `test_strict_flow_skip.py` — strict policy + broken mission + `--skip-retrospective` → `RetrospectiveSkipped` + mission completes
   - `test_opt_out.py` — `enabled: false` → no events, no record, mission completes
   - `test_latency_budget.py` — default flow on a 4-WP / 30-event mission completes in < 2.0s wall-clock (NFR-005)
   - `test_policy_source_attribution.py` — every emitted retrospective event has a non-empty `policy_source` matching the resolver's output

3. Use `tmp_path` + canonical helpers to scaffold missions. Reuse WP02's fixture missions where shape matches.

**Files**:
- `tests/next/test_retrospective_terminus_wiring.py` (new, ~80 lines)
- `tests/integration/retrospective/` (new directory, ~7 test files, ~600 lines total)

**Validation**:
- [ ] All 7 integration tests pass
- [ ] Wiring test passes
- [ ] Latency budget assertion holds in CI (run 3x and use median)

---

## Definition of Done

- [ ] All 6 subtasks complete
- [ ] `uv run pytest tests/next/test_retrospective_terminus_wiring.py tests/integration/retrospective/ -q` exits 0
- [ ] `uv run pytest tests/retrospective/ -q` exits 0 (WP01-WP03 stay green)
- [ ] `uv run ruff check src/specify_cli/next/ tests/integration/retrospective/` exits 0
- [ ] No edits outside `owned_files`
- [ ] `facilitator_callback=None` is no longer reachable from any enabled-policy path

## Risks & Reviewer Guidance

- **NFR-005 latency budget**: T023's latency test is the regression catcher. Run locally and verify the assertion has margin (locally < 500ms suggests CI < 2.0s is safe).
- **Skip-retrospective audit**: `--skip-retrospective` is a privileged operation. The Skipped event MUST capture the actor (CLI user identity from `git config user.email` or equivalent) and a free-form reason. Reviewer should verify the reason is required, not optional.
- **Gate ordering (T022)**: a subtle bug here would let `MissionCompleted` emit before the gate fires. The integration tests assert lamport ordering — reviewer should sanity-check by reading one of those tests.

## Next

After this WP merges, WP07 (Docs/Skills) can document the working surfaces.

Implementation command:

```bash
spec-kitty agent action implement WP04 --agent claude
```
