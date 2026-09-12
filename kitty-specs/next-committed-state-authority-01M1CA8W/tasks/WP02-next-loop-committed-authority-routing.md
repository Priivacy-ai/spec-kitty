---
work_package_id: WP02
title: next loop routes through committed authority
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-005
- NFR-001
- C-001
- C-002
- C-003
- C-006
- C-007
planning_base_branch: fix/next-committed-state-authority
merge_target_branch: fix/next-committed-state-authority
branch_strategy: Planning artifacts for this mission were generated on fix/next-committed-state-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/next-committed-state-authority unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
history: []
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- tests/runtime/next/test_merged_mission_terminal.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/runtime/next/runtime_bridge.py
- tests/specify_cli/next/test_runtime_bridge.py
- tests/runtime/next/test_merged_mission_terminal.py
role: implementer
tags: []
tracker_refs: []
---

# WP02 — next loop routes through committed authority

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Route the `spec-kitty next` control loop through the committed authority built in WP01: (a) #3780 — make the step-advancement predicate honor operator provenance so a canceled-with-provenance WP advances while a synthetic cancellation blocks; (b) #2947 — add a committed-authority terminal/conflict pre-check in BOTH `next` entry points (`decide_next_via_runtime` advancing → `kind: terminal`; `query_current_state` query → `kind: query`/`mission_state: done`) so a merged mission is recognized (and a conflict/artifact-missing case fails closed) instead of fabricating an unstarted run from a stale coordination checkout.

## Context

Depends on **WP01** (`src/runtime/next/committed_authority.py` — `wp_ending` IC-01, `mission_terminal_verdict` IC-02). **Read** `../spec.md`, `../plan.md`, `../research.md`, and `../tracer-design-decisions.md` first — `research.md` carries the exact truth table, call sites, and guard tests.

This WP owns `runtime_bridge.py` (the only WP that edits it). Load-bearing decisions:
- **TWO entry points, both in `runtime_bridge.py`** (BLOCKER-2). The #2947 pre-check must be applied in BOTH:
  - **Advancing mode** — `decide_next_via_runtime` (`runtime_bridge.py:2090`), reached by `spec-kitty next --result success` (what issue #2947's repro actually ran). This path CAN emit `kind: terminal`; on a merged mission return `kind: terminal` (the issue's expected result) and create **no** run.
  - **Query mode** — `query_current_state` (`:2289`), reached by bare `--json`. This path **structurally only emits `kind: query`** (every builder hardcodes it; `tests/contract/test_next_no_implicit_success.py:127` asserts it — a guard in T011's keep-green list). So a merged mission returns `kind: query` with `mission_state: "done"` (the existing finalized-override precedent, `:2153`), NOT `kind: terminal`. Do NOT force `kind: terminal` in query mode.
  - Both consume WP01's `mission_terminal_verdict` (one authority, both surfaces — FR-008).
- **D8 / F1** — place the pre-check in `query_current_state` **before** `mission_context_for` (`:2310`), and in `decide_next_via_runtime` before it selects a workspace / starts a run (before the `mission_context_for`/`get_or_start_run` calls, ~:273/:1481). Do NOT push behavior into the shared `_resolve_mission_read_path` (pure resolver, ~9 callers).
- **D9 / F4** — short-circuit BEFORE `_finalized_task_board_override_step` (:652, invoked :2391), which reads the stale `status_state.read_dir`. The pre-check reads committed authority via WP01's `mission_terminal_verdict` (PRIMARY surface), never the coord checkout.
- **F5 invariant** — the pre-check fires **only** when `mission_terminal_verdict` is `terminal` or `blocked_conflict` (i.e. `mission_number` present AND committed status resolves). For `none`, behavior is byte-identical to today — this protects the many in-flight query fixtures.
- **#3780** — extend `_wp_blocks_step` to accept provenance and route the `review` branch through `is_acceptable_ending`; consume WP01's `wp_ending` so lane+provenance come from a single reduction. **Do NOT** change `_should_advance_wp_step`'s public 2-arg signature (callers `:785`, `:1574`, `runtime_bridge_composition.py:500`; test monkeypatches assume 2 args).

**Do NOT** modify `status_lanes.py` (C-001), the lane state machine (C-002), or WP01's module. Keep the guard suites green (see T011).

### Subtask T007: RED — #3780 provenance-gated advancement repro (FR-005, FR-006)

**Purpose**: Prove the review-step stall on a canceled-with-provenance WP, before the fix.

**Steps**:
1. In `tests/specify_cli/next/test_runtime_bridge.py`, add `@pytest.mark.regression` tests referencing `#3780`:
   - canceled WITH operator provenance at review → `_should_advance_wp_step("review", fd) is True` (advances). The existing helper `_write_status_events` writes `reason: None` (→ synthetic); emit a canceled event carrying operator provenance (`reason_source: "operator"` or a non-empty non-template reason) — extend the helper or add one.
   - canceled with operator provenance at implement → advances (True).
   - synthetic cancellation (`reason: None`) at review AND implement → still blocks (`is False` at review) — fail-closed.
2. Confirm RED on base: the review case returns False today (lane-only predicate).

**Files**: `tests/specify_cli/next/test_runtime_bridge.py` (extend; ~60 lines). Keep the existing `test_should_advance_implement_one_canceled` (:229) green.
**Validation**: review-with-provenance case fails on base for the documented reason.

### Subtask T008: RED — #2947 merged-mission terminal repro (FR-001, FR-002, FR-003, FR-009)

**Purpose**: Prove the merged-mission restart and pin the terminal/blocked verdicts, before the fix.

**Steps**:
1. In `tests/runtime/next/test_merged_mission_terminal.py` (new), build the merged-mission fixture (PRIMARY: `mission_number` assigned + committed status all-accepted; stale COORD checkout: all-`planned`/artifact-missing — the two-surface split, mirror WP01 T001) and assert through the REAL entries:
   - **Advancing mode** (`decide_next_via_runtime` / `spec-kitty next --result success`): merged mission → `decision.kind == "terminal"` and **no runtime run created**. Observable for "no run" (SHOULD-FIX-5): assert `.kittify/runtime/feature-runs.json` (`runtime_bridge_io._feature_runs_path(repo_root)`) is absent or unchanged before→after. RED on base (creates a run, returns `kind: step`/discovery).
   - **Query mode** (`query_current_state` / bare `--json`): merged mission → `decision.kind == "query"` AND `mission_state == "done"` (NOT `kind: terminal` — query mode is structurally `kind: query`). RED on base (returns `mission_state: discovery`/not_started).
   - `mission_number` assigned but committed status NOT all-accepted (conflict) → `kind == "blocked"` with the conflict reason (FR-009), in both modes.
   - unmerged (`mission_number` absent) whose actionable step needs a workspace missing the mission's artifacts → `kind == "blocked"` artifact-missing (FR-003).
   - never-started (no committed status log) → unchanged behavior, not spuriously terminal (C-003).
2. Mark `@pytest.mark.regression`, reference `#2947`.

**Files**: `tests/runtime/next/test_merged_mission_terminal.py` (new, ~180 lines). Study existing `next` query fixtures (`tests/next/test_query_mode_unit.py`, `tests/runtime/test_bridge_*`) for setup patterns; copy the `mission_number` meta shape from `tests/fixtures/clean_install_fixture_mission/.../meta.json`.
**Validation**: advancing-mode terminal case and query-mode `mission_state:done` case both fail on base (fabricated discovery/step + created run).

### Subtask T009: Implement #3780 — provenance-gated advancement (FR-005, FR-006, FR-007, C-003, C-004)

**Purpose**: Route the predicate through provenance via WP01's fold.

**Steps**:
1. In `runtime_bridge.py`, in the `_should_advance_wp_step` loop (:711–721), replace the lane-only `get_wp_lane`→`wp_state_for` read with WP01's `committed_authority.wp_ending(feature_dir, wp_id)` (single reduction; preserves fail-loud). Derive lane + `acceptable`/provenance from it.
2. Extend `_wp_blocks_step(step_id, state, has_provenance=False)` (default keeps the single caller stable). Route the `review` branch through `is_acceptable_ending(lane, has_provenance=...)` (or equivalently consume `wp_ending.acceptable`): canceled+operator → not blocked; synthetic canceled → blocked; approved/done → not blocked; else → blocked (matches today's table for non-canceled). Keep `implement` behavior.
3. Do NOT change `_should_advance_wp_step`'s 2-arg signature.

**Files**: `runtime_bridge.py` (modify `_should_advance_wp_step`, `_wp_blocks_step`; ~20 lines).
**Validation**: T007 turns GREEN; guard suites (T011) stay green.

### Subtask T010: Implement #2947 — committed-authority pre-check in `query_current_state` (FR-001, FR-002, FR-003, FR-009, C-005, D8, D9, F5)

**Purpose**: Terminal/conflict verdict before workspace selection.

**Steps**:
1. Add ONE call to WP01's `mission_terminal_verdict(repo_root, mission_slug)` in EACH entry point, early (before workspace selection / run start):
   - **`query_current_state` (:2289)** — before `mission_context_for` (:2310):
     - `terminal` → return `kind: query` with `mission_state="done"` (mirror `_build_finalized_override_query_decision` :2153 — do NOT emit `kind: terminal` here; query mode is structurally `kind: query`).
     - `blocked_conflict` → return a `kind: blocked` decision with a clear conflict reason.
     - `none` → fall through unchanged (F5 invariant).
   - **`decide_next_via_runtime` (:2090)** — before it selects a workspace / starts a run (before the `mission_context_for`/`get_or_start_run` calls, ~:273/:1481):
     - `terminal` → return `kind: terminal` (matches issue #2947's `--result success` expectation) and create NO run.
     - `blocked_conflict` → `kind: blocked` conflict.
     - `none` → fall through unchanged.
2. **Blocked-result construction (SHOULD-FIX-3)**: there is no factory — mirror the existing inline blocked emissions at `runtime_bridge.py:2557` / `:2666`, i.e. `_materialize_decision(_cores.DecisionEnvelope(kind=DecisionKind.blocked, agent=…, mission_slug=…, mission=mission_type, mission_state=<step>, reason=<conflict/artifact-missing msg>, step_id=…))`. Do NOT invent a new payload shape.
3. FR-003 artifact-missing on the unmerged actionable path: rely on the resolver's existing `require_exists=True` → `StatusReadPathNotFound` (F1); wire/propagate it into a `kind: blocked` structured result rather than adding new global behavior.
4. Ensure `_finalized_task_board_override_step` never runs for a merged mission (the pre-check returns first).

**Files**: `runtime_bridge.py` (modify `query_current_state` + `decide_next_via_runtime`; ~40–60 lines). Consider extracting a small shared `_merged_mission_short_circuit(...)` helper consumed by both to keep complexity ≤15.
**Validation**: T008 (both modes) turns GREEN; guard suites stay green.

### Subtask T011: GREEN + guard-preserving verify + live #3780 proof (NFR-001, C-007)

**Purpose**: Prove both repros pass, nothing regressed, and the stall is gone in a real run.

**Steps**:
1. Run the guard-preserving suites and keep them green: `tests/runtime/test_bridge_parity.py` (incl. `:817`) + `_bridge_oracle.py`, `tests/runtime/test_bridge_decide_next.py`, `tests/runtime/test_bridge_composition.py`, `tests/next/test_query_mode_unit.py`, `tests/contract/test_next_no_implicit_success.py`, and `tests/specify_cli/next/test_runtime_bridge.py`.
2. **Live #3780 proof (C-007)**: on a real fixture mission with a canceled-with-provenance WP at review, run the actual `spec-kitty next` command (fresh editable install of THIS worktree — `pip install -e .`) and capture output showing the loop advances (no stall). Record the transcript in the WP evidence / review notes. Code looking fixed ≠ fixed.
3. Determinism (NFR-001): run `query_current_state` twice on the same committed state and assert identical verdict independent of the coord checkout.

**Files**: none new (verification).
**Validation**: all named suites green; live transcript attached; determinism asserted.

### Subtask T012: Campsite tidy + scope gate (DIRECTIVE_025, C-006, C-001, C-002)

**Purpose**: Clean touched `runtime_bridge.py` functions and prove scope integrity.

**Steps**:
1. Ruff + mypy --strict clean on `runtime_bridge.py` touched regions (complexity ≤15; extract a small helper if the pre-check pushes `query_current_state` over). No new suppressions.
2. Docstrings on the changed functions naming the committed-authority routing; terminology check (`pytest tests/architectural/test_no_legacy_terminology.py`).
3. Confirm zero diff to `status_lanes.py` (C-001), the lane state machine (C-002), and WP01's module; confirm the 2-arg `_should_advance_wp_step` signature is intact.

**Files**: `runtime_bridge.py` only.
**Validation**: ruff/mypy/terminology green.

## Definition of Done

- T007 (#3780) and T008 (#2947) regressions were RED on the lane's `planning_base_branch` and are GREEN at final.
- `_wp_blocks_step` honors operator provenance (canceled+operator advances review/implement; synthetic blocks) via WP01's single-reduction fold; `_should_advance_wp_step` keeps its 2-arg signature.
- Merged mission recognized in BOTH modes: `decide_next_via_runtime` returns `kind: terminal` (no run created — `feature-runs.json` unchanged); `query_current_state` returns `kind: query`/`mission_state: done`; conflict/artifact-missing → `kind: blocked`; verdict `none` → byte-identical behavior (F5 invariant).
- Guard-preserving suites green; **live `next`-run transcript** proves the #3780 stall is gone (C-007).
- No diff to `status_lanes.py`, the lane state machine, WP01's module, or `_resolve_mission_read_path` behavior.
- Ruff + mypy --strict + terminology-guard clean; per-subtask completion via `spec-kitty agent tasks mark-status <Txxx> --status done`.
- Implementation command: `spec-kitty agent action implement WP02 --agent <name>`.

## Risks

- **In-flight fixture regression (F5)**: an early terminal/blocked return firing on a fixture that sets `mission_number` for unrelated reasons. Mitigation: the F5 invariant (fire only on `terminal`/`blocked_conflict`) + running the parity/oracle/query-mode suites.
- **Wrong surface (F4/D9)**: wiring the pre-check to the selected `status_state.read_dir` reproduces #2947. Mitigation: consume WP01's `mission_terminal_verdict` (PRIMARY) only; place the call before `mission_context_for`.
- **Signature blast radius**: adding a param to `_should_advance_wp_step` breaks 3 callers + monkeypatches. Mitigation: extend only `_wp_blocks_step` with a defaulted param.
- **Blocked-reason drift (F6)**: inventing a new blocked payload. Mitigation: reuse an existing `DecisionKind.blocked` reason constructor.

## Reviewer Guidance

- Verify the #2947 pre-check is BEFORE `mission_context_for` and reads only committed authority (WP01 module), never the coord surface; verify `_finalized_task_board_override_step` cannot run for a merged mission.
- Verify the F5 invariant: `none` verdict → zero behavior change (diff the query result for an in-flight fixture).
- Verify `_should_advance_wp_step` is still 2-arg and the review truth table matches the spec (canceled+operator advances; synthetic blocks).
- Insist on the **live** `next`-run transcript for #3780 — not a static reading.
- Confirm zero diff to the shipped authority, the lane machine, and the pure resolver.
