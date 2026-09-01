# Phase 0 Research — Mission Completion Terminal State

All "unknowns" here are **mechanism** decisions the post-spec squad deferred to plan; the
product decisions (D1–D3) are settled in [spec.md](spec.md). Evidence anchors:
[research/post-spec-squad-findings.md](research/post-spec-squad-findings.md).

## R1 — Provenance mechanism (operator-authored vs synthetic)

- **Decision**: A canceled work package is accept-eligible only when the operator supplied
  a reason via `--note`. The mechanism is a **first-class `reason_source: "operator" |
  "synthetic"` field on `StatusEvent`** (`status/models.py`), set at the emit site
  (`tasks_move_task.py`, not the pure-planning `build_transition_plan` in
  `tasks_transition_core.py`) and projected into the reduced snapshot. **Not** overloading
  `policy_metadata`, and **not** a reduce-time template match (post-tasks reviewer: a
  template match is fakeable and reintroduces F1 one layer up).
- **Post-tasks correction (pedro BLOCKER)**: the original WP01 anchor
  (`tasks_transition_core.py:307-317`) is a pure planning function that never emits;
  `owned_files` corrected to include `status/models.py`, `status/emit.py`, and
  `tasks_move_task.py`. The provenance must be asserted on the **raw event** (`read_events`),
  not only via the reducer.
- **Rationale**: The squad proved (F1, reviewer+debugger, `tasks_transition_core.py:307-317`)
  that "non-empty reason" is auto-forged — `--force` with no note yields
  `reason="Force move to canceled"`. Only an explicit operator signal is non-forgeable and
  makes FR-003 reachable through the canonical command (SC-002).
- **Alternatives considered**:
  - *Force-cancel-without-note records an empty sentinel* — reachable, but loses the "who
    forced this" audit that `force=true` + actor already give; and empty strings invite
    whitespace fake-greens (`validate.py:126-128` is truthiness-only).
  - *Dedicated cancellation-reason event type* — cleaner long-term but a larger surface
    change; deferred as unnecessary for this slice.

## R2 — Provenance read seam

- **Decision**: Project a `cancellation_reason` (and its provenance marker) into the
  per-WP reduced snapshot (`reducer.py:166-177`) when `lane==canceled`.
- **Rationale**: F3 (architect+debugger) — accept reads the snapshot
  (`acceptance/__init__.py:997,1021`), which today drops `reason`. Projecting keeps accept a
  single read and stays within C-002 (still event-sourced) and C-001 (a projection, not a
  state-machine change).
- **Alternatives**: log lookup by `last_event_id` inside `acceptance/` — rejected; scatters
  a second event read into the acceptance layer and duplicates event-parsing logic.

## R3 — Acceptable-ending authority

- **Decision**: `is_acceptable_ending(lane, *, has_provenance) -> bool` in
  `src/specify_cli/status_lanes.py`; consumed by accept, merge, and the dependency gate.
  Admits `{approved, done}` unconditionally; admits `canceled` only with provenance;
  references `TERMINAL_LANES` only to classify canceled. Deletes the three
  `_ACCEPTED_READY_LANES` copies.
- **Rationale**: F2 (architect, supersedes planner) — terminality (`{done,canceled}`),
  acceptability (`{approved,done}`), and provenance are three separable decisions.
  Consuming `is_terminal` wholesale would reject `approved` and accept `canceled` blindly.
  One predicate satisfies directives 043/044.
- **Alternatives**: reuse `is_terminal()` directly — rejected (category error, proven).

## R4 — Merge exclusion granularity

- **Decision**: Filter canceled WPs from `all_wp_ids` at `merge/executor.py:1660`; add an
  all-canceled lane guard in `_phase_merge_lanes`. Retain the cancellation audit record.
- **Rationale**: F4 (architect+debugger) — a lane holds many WPs (`lanes/models.py:84`);
  merge asserts per-WP done/review (`done_bookkeeping.py`). Lane-level "skip" is the wrong
  unit and would drop surviving approved work.
- **Alternatives**: skip the whole lane whenever it contains a canceled WP — rejected
  (would fail to integrate surviving approved WPs in the same lane).

## R5 — Dependency-on-canceled closure (FR-009)

- **Decision**: In `core/dependency_graph.py:59`, a `canceled`-with-provenance dependency
  is treated as resolved/removed via the same acceptable-ending authority.
- **Rationale**: F5 (planner) — canceled is currently non-satisfying; canceling a
  depended-upon WP (reachable from `in_progress` without `--force`) strands the dependent
  → the mission's own trap, and a third disagreeing consumer.
- **Alternatives**: extend #3713's active-to-canceled *rejection* from finalize to runtime
  move-task — rejected as more invasive and it forbids a legitimate replan; resolving the
  gate is the smaller, more honest change.
- **Post-tasks correction (pedro HIGH / paula BLOCKER)**: `dependency_readiness_for_wp` is
  lane-only; the claim gate consumes it in `workflow_executor.py:634` (which already reduces
  the snapshot). WP04 owns `workflow_executor.py` and adds an **optional** provenance param
  (default preserves the 5 read-only callers). It also **replaces** `_SATISFYING_DEPENDENCY_LANES`
  with the predicate (identical truth table — directive 044), rather than special-casing.
  The FR-009 face splits: **claim** gate = WP04 (`dependency_graph.py` + `workflow_executor.py`);
  **merge** gate = WP03 (`policy/merge_gates.py`).
- **Both CLI claim gates threaded (post-review REJECT fix)**: WP04 threads provenance through
  BOTH `workflow_executor.py:653` (`agent action implement`) AND `implement.py:1317`
  (`_ensure_wp_claim_preconditions` — the primary `spec-kitty implement WP##` command, "the only
  supported way to prepare a workspace" per CLAUDE.md). The first WP04 review REJECTED because
  `implement.py` was left lane-only, leaving the #2945 strand trap open on the main claim path; it is
  now fixed and covered by an integration test (`TestImplementClaimGateThreadsProvenance`) that seeds
  a real event log and asserts the gate admits a canceled(operator) dependency and blocks a
  canceled(synthetic) one.
- **Deferred callers of `dependency_readiness_for_wp` (tracked follow-up)** — NOT updated in this
  mission (they keep the backward-compatible lane-only default). All are **fail-closed**: a
  canceled-with-provenance dependency is treated as still-blocking (never wrongly admitted), so the
  worst case is an over-conservative refusal, not a silent skip. Correctly classified (post-merge
  cross-WP squad, HIGH finding):
  - `orchestrator_api/commands.py:1139` (`start-implementation`) — this is a **mutating CLAIM gate**
    (the external-API equivalent of `implement.py`'s `_ensure_wp_claim_preconditions`), NOT a
    read-only caller. It reproduces the #2945 strand on the orchestrator-api claim path and the
    follow-up MUST thread `provenance=…work_packages` here, mirroring `implement.py`/`workflow_executor.py`.
  - `runtime/next/discovery.py:132` (`_build_wp_lane_map`/`_preview_from_candidates`) — the canonical
    `spec-kitty next` claimable-preview; collapses the snapshot to `dict[str, Lane]`, so threading
    provenance needs a signature change. Governed Shared Package Boundary — warrants its own change.
    The follow-up must cover this `next`-loop parity.
  - `orchestrator_api/commands.py:817` (`list-ready`) and `tasks_status_view.py:223` — genuinely
    **read-only/advisory** display surfaces; cosmetic divergence only.
  File a follow-up issue covering the two claim/preview surfaces so parity is not silently assumed.

## R8 — Other parallel {approved,done} authorities (unification disposition)

Post-spec F2 and post-tasks paula named additional lane-sets. Dispositions (directive 003/044):
- `_ACCEPTED_READY_LANES` ×3 (`acceptance/__init__.py:145`, `gates_core.py:52`, `summary_core.py:173,202`)
  — **collapsed** onto `is_acceptable_ending` (WP02).
- `_SATISFYING_DEPENDENCY_LANES` (`dependency_graph.py:34`) — **collapsed** (WP04).
- `policy/merge_gates.py` (`:155-164`, `:253`) — **routed through** the predicate (WP03).
- `audit/classifiers/wp_files.py:16` `{done,approved}` — **knowingly separate**: this classifies
  which files a completed WP touched for *audit*, not acceptance gating; different concern, out of scope.
- `migration/rebuild_state.py:140` `{done,canceled,approved}` — **knowingly separate**: migration-only
  state reconstruction; accepting `canceled` unconditionally is correct there (it is rebuilding history,
  not gating a live mission). Out of scope.

## R6 — Authoring-time detector (FR-007)

- **Decision**: Enumerable trigger-phrase detector over acceptance-criteria/subtask prose,
  validated against a fixed labeled corpus (positive + adversarial-negative fixtures),
  advisory only. Precision/recall target: **100% recall on the positive fixtures, 0 false
  positives on the negative fixtures**; the corpus is the oracle, not an open-world claim.
- **Rationale**: F6 (debugger+reviewer+planner) — no structured signal exists
  (`ownership/models.py`); an open-world "0% false positives" is unfalsifiable, so the claim
  is scoped to a fixed corpus. A structured `completion_kind` field is #3550 territory
  (C-003).
- **Alternatives**: add `completion_kind: post_integration` WP field now — rejected for this
  slice (scope; overlaps #3550's redesign).

## R7 — Regression baseline (NFR-001/SC-004)

- **Decision**: Pin baseline commit **`a59460ec15`** (branch base = `upstream/main` at
  mission start). "0 regressions" is measured against this commit for the suites named in
  NFR-001. Honor the repo's baseline-red gotcha (known-P0 reds are not this mission's).
- **Rationale**: F7 (reviewer) — unpinned baselines are subset-fakeable.

## Adversarial evidence dispositions (per contracts/adversarial-evidence-contract.md)

| Finding | Lens(es) | Disposition |
|---------|----------|-------------|
| F1 provenance auto-synthesis (BLOCKER) | reviewer, debugger | **changed** — spec redefined provenance as operator-authored (D2); R1 |
| F2 FR-005 mis-framed | architect (vs planner) | **changed** — acceptable-ending predicate; R3 |
| F3 reducer drops reason | architect, debugger | **changed** — reducer projection; R2 / C-002 |
| F4 merge granularity | architect, debugger | **changed** — WP-granular exclusion; R4 / FR-004 |
| F5 dependency strand | planner | **changed** — pulled into scope as FR-009/SC-005; R5 |
| F6 FR-007 unmeasurable | debugger, reviewer, planner | **changed** — fixed-corpus SC-003; R6 |
| F7 unpinned baseline | reviewer | **changed** — baseline `a59460ec15` pinned; R7 |
| C-002 `get_lane_from_frontmatter` misnomer | architect | **deferred_with_rationale** — reader is correct today; rename out of scope unless free |
| #2745 shared merge surface | planner | **accepted** — noted as C-005 compose constraint; no code now |

No contested finding was silently dropped.
