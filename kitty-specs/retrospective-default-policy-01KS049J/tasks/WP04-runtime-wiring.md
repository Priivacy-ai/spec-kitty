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
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
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
4. Add `--skip-retrospective="<reason>"` flag to the completing command (typically `spec-kitty merge`, but confirm by grepping for the `MissionCompleted` emit site). When set:
   - Bypass the gate entirely.
   - Import `emit_skipped` and `RetrospectiveSkipped` from `specify_cli.retrospective.events` (defined and exported by **WP03 T015** — this WP does not edit `events.py`).
   - Call `emit_skipped(...)` with `skip_reason="<reason>"`, `skip_reason_source="cli_flag"`, `policy_source=source_map`, `actor=cli_actor()`.
   - Empty `skip_reason` is rejected by `emit_skipped` with `ValueError` per the contract. The CLI surfaces this as a `BadParameter` ("--skip-retrospective requires a reason").
   - Mission completion proceeds after the Skipped event lands.

**Files**:
- `src/specify_cli/next/_internal_runtime/retrospective_terminus.py` (extend, ~100 lines)

This WP **does not** edit `src/specify_cli/retrospective/events.py` or any other WP03-owned file. All three event types (`RetrospectiveCaptured`, `RetrospectiveCaptureFailed`, `RetrospectiveSkipped`) and their emit helpers are owned by WP03 T015. This WP only imports them:

```python
from specify_cli.retrospective.events import (
    RetrospectiveCaptured, RetrospectiveCaptureFailed, RetrospectiveSkipped,
    emit_captured, emit_capture_failed, emit_skipped,
)
```

**Validation**:
- [ ] Strict policy + healthy mission → record + `RetrospectiveCaptured(provenance_kind="runtime_strict_gate")` + mission completes
- [ ] Strict policy + generator fails → `RetrospectiveCaptureFailed` + `RetrospectiveGateBlocked` exception → CLI exits 1 with the formatted message
- [ ] Strict policy + `--skip-retrospective="<non-empty reason>"` → `RetrospectiveSkipped(skip_reason=..., skip_reason_source="cli_flag", bypassed_provenance_kind="runtime_strict_gate")` event; mission completes
- [ ] Strict policy + `--skip-retrospective=""` (empty reason) → CLI rejects with `BadParameter` (no event emitted, mission does not complete)

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

1. **Wiring test** at `tests/next/test_retrospective_terminus_wiring.py` — REQUIRE BOTH approaches:

   **(a) AST-level assertion** — parse `runtime_bridge.py` and assert no `Call` to `run_terminus` passes `facilitator_callback=None`:
   ```python
   def test_no_none_facilitator_callback_in_source_ast():
       import ast, pathlib
       src = pathlib.Path("src/specify_cli/next/runtime_bridge.py").read_text()
       tree = ast.parse(src)
       for node in ast.walk(tree):
           if not isinstance(node, ast.Call):
               continue
           if not _is_run_terminus_call(node):
               continue
           for kw in node.keywords:
               assert not (kw.arg == "facilitator_callback" and _is_constant_none(kw.value)), (
                   f"runtime_bridge.py:{node.lineno} passes facilitator_callback=None; "
                   "the wiring fix from this mission's WP04 has regressed."
               )
   ```

   **(b) Runtime mock-based assertion** — patch `run_terminus` and assert the closure passed in for an enabled policy is non-None and callable:
   ```python
   def test_runtime_passes_non_none_callback_for_enabled_policy(monkeypatch):
       calls: list = []
       monkeypatch.setattr("specify_cli.next.runtime_bridge.run_terminus",
                           lambda **kw: calls.append(kw))
       # Drive the runtime bridge against a default-policy mission
       _invoke_runtime_for_completion(mission_handle="fake", policy=default_policy())
       assert len(calls) == 1, "run_terminus should be called exactly once"
       cb = calls[0]["facilitator_callback"]
       assert cb is not None, "Enabled policy must wire a real callback"
       assert callable(cb), "facilitator_callback must be callable"
   ```

   **Why both**: AST inspection catches a hard-coded `None` reintroduction at the source level. The mock-based assertion catches the subtler regression where a feature flag, conditional branch, or environment check silently sets the callback to None at runtime even though the source looks healthy. A regression on either path is independently fatal.

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
- [ ] **NFR-001 aggregate budget**: `uv run pytest tests/retrospective tests/integration/retrospective tests/next/test_retrospective_terminus_wiring.py -q` completes in under 60 seconds wall-clock on the project's CI runner
- [ ] `uv run ruff check src/specify_cli/next/ tests/integration/retrospective/` exits 0
- [ ] **No env-var mutation in this WP's owned tests**: `grep -nE "monkeypatch\.setenv.*SPEC_KITTY_(RETROSPECTIVE|MODE)|os\.environ\[.*SPEC_KITTY_(RETROSPECTIVE|MODE)" tests/next/test_retrospective_terminus_wiring.py tests/integration/retrospective/` returns no hits (FR-016 enforcement)
- [ ] No edits outside `owned_files`
- [ ] `facilitator_callback=None` is no longer reachable from any enabled-policy path (verified via both AST + runtime mock per T023.1)

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
