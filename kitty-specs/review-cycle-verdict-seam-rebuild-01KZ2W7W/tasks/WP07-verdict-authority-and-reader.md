---
work_package_id: WP07
title: Verdict authority and its reader
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-022
- NFR-002
- NFR-003
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
- T031
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: src/specify_cli/status/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/reducer.py
- src/specify_cli/status/models.py
- src/specify_cli/post_merge/review_artifact_consistency.py
- src/specify_cli/merge/preflight.py
- src/specify_cli/merge/forecast.py
- src/specify_cli/cli/commands/review/_lane_gate.py
- src/specify_cli/orchestrator_api/commands.py
- tests/status/test_reducer.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP07 - Verdict authority and its reader

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load architect-alphonso
```

## Objective

This is the mission's core invariant (spec.md User Story 1; plan.md IC-04).
Today, `ReviewResult` rides the status event (`reviewer`, `verdict`,
`reference`, `feedback_path`) as an **index entry with no reader** —
`reduce()` never surfaces `review_result`, so nothing downstream of the
reducer can answer "is this work package approved?" from the event. Every one
of ten measured consumer call sites across eight modules answers that question
today by parsing artifact frontmatter instead — the shape FR-001/SC-011
require to stop.

This WP does two things, and both are required, not either-or:

1. **Give the event's verdict a reducer slot and a reader** — a real branch in
   `_wp_state_from_event`, carried forward like every other runtime slot, with
   an explicit precedence rule against the pre-existing `review` slot (which
   carries the *arbiter override*, a distinct fact).
2. **Re-point the safety-relevant consumers at that reader** — the merge gate,
   the lane gate, `merge/preflight.py`, `merge/forecast.py`, and the external
   `orchestrator_api` ingress. A slot nobody reads is documentation, not a
   delivered property (Complexity Tracking table, plan.md).

**The reader must be snapshot-first-with-fallback, never snapshot-only.** The
corpus cutover to the reduced-snapshot model was deferred by explicit human
decision; `status_phase` is a **per-mission opt-in** key in `meta.json`, and
*this mission's own `meta.json` has no such key* (confirmed:
`kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/meta.json` carries no
`status_phase` field). A snapshot-only reader would therefore return "no
verdict" for every un-migrated mission — including, ironically, this one —
and SC-012 explicitly calls that failure mode unacceptable for a safety gate.
Implementing this WP as a naive re-point manufactures the exact defect the
mission exists to close.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — the
  "Verdict authority (the split, measured)" section under Definitions,
  FR-001, FR-022, SC-011, SC-012, User Story 4 (the fail-open kanban reader
  and uncaught arbiter crash are WP14's problem, not this WP's — do not fix
  them here, but do not regress them either).
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-04
  ("Verdict authority and its reader"), and the Complexity Tracking table's
  two rows (both directly justify this WP's shape: a second reducer slot
  distinct from `review`, and the requirement that re-pointing consumers is
  in-scope, not deferred).
- `docs/adr/3.x/2026-07-19-1-wp-runtime-state-event-log-eviction-via-innerstatechanged.md`
  — the governing ADR. It names "review-cycle fields" among state to be
  evicted and pins "one authority per datum — runtime state has exactly one
  read path (the reduced snapshot)", with the typed `WPInnerStateDelta` slot
  on `InnerStateChanged` as the chartered mechanism. This WP's new slot must
  follow that mechanism, not invent a parallel one.
- `src/specify_cli/status/reducer.py` — read the whole file, but specifically:
  - `_RUNTIME_SLOTS` (line 46) — the tuple of per-WP runtime slots carried
    forward across transitions. **The new verdict slot is explicitly NOT a
    `_RUNTIME_SLOTS`-table row** (plan.md IC-04's risk note) — it needs its
    own branch in `_wp_state_from_event`, described below, not a mechanical
    addition to this tuple.
  - `_wp_state_from_event` (line 100) — builds the per-WP state dict for one
    transition, carrying forward every untouched runtime slot from
    `previous`. This is where the new branch is added.
  - `_apply_annotation_delta` (line 155) — folds a typed `WPInnerStateDelta`
    into the snapshot; note the existing `review` slot handling near line
    200 (`if delta.review is not None: state["review"] = ...`) — this is the
    **pre-existing** slot for the arbiter override, and this WP's new slot
    must be named distinctly and its precedence against `review` stated
    explicitly (see T026).
  - `tests/architectural/test_2093_authority_invariant.py` — already imports
    `_EVENT_SLOTS = frozenset(_RUNTIME_SLOTS)` straight from the reducer as
    its single source of truth for "which slots are event-sourced". **Adding
    a slot here widens `_EVENT_SLOTS` and can red this test's arm 2** ("no
    field is dual-homed" — the static `WP_FIELD_ORDER` schema and the
    event-sourced slot set must share only an explicitly tolerated migration
    set). Read this test's full docstring before touching `_RUNTIME_SLOTS` at
    all, and re-run it after every change to this file.
- `src/specify_cli/status/models.py` — `ReviewResult` (line 266: `reviewer`,
  `verdict`, `reference`, `feedback_path` — four fields) and `ReviewOverride`
  (line 398: `at`, `actor`, `wp_id`, `reason` — the pinned four-field shape
  WP03/WP09 of a related mission reference verbatim; do not touch its shape).
  These are two *different* facts on two different slots — this WP's new
  slot is for `ReviewResult`-derived verdict authority, not a variant of
  `ReviewOverride`.
- `src/specify_cli/status/wp_state.py` — `check_transition` (line 162) and
  `_check_force` (line 187-194): **`review_result` is not always populated**
  — when `ctx.force` is true, `check_transition` short-circuits straight to
  `self._check_force(ctx)` (line 183-184) and never reaches `guard_for(target,
  ctx)`, which is presumably where a review-result-carrying guard would live.
  T028 must define the reader's behaviour for `review_result: null` reached
  this way — it is not a damaged-record case (WP14's concern), it is a
  legitimate "no verdict was ever supplied for this transition" case.
- `src/specify_cli/orchestrator_api/commands.py:1296` (`_parse_review_result_json`)
  — the **external ingress**. This function validates an operator-supplied
  `--review-result-json` payload at exactly four fields (`reviewer`,
  `verdict`, `reference`, plus `feedback_path` optionally) before constructing
  a `ReviewResult`. This is the hole T031 closes — anything reachable from
  outside the process that can inject a `ReviewResult` must be validated
  against the same authority contract the reducer now enforces.
- `src/specify_cli/post_merge/review_artifact_consistency.py`,
  `src/specify_cli/merge/preflight.py`, `src/specify_cli/merge/forecast.py`,
  `src/specify_cli/cli/commands/review/_lane_gate.py` — read each in full.
  **None of these four currently import anything from `status/reducer.py` or
  reference `review_result`/`ReviewResult`** — confirmed by direct grep. All
  four currently answer "is this WP approved?" exclusively via
  `find_rejected_review_artifact_conflicts` /
  `rejected_review_artifact_for_terminal_lane`, which parse review-cycle
  artifact frontmatter. This is the frontmatter-authority pattern FR-001/SC-011
  require these four callers to stop being the *sole* answer for — T029/T030
  re-point them to consult the new reducer slot as well.

**Ten consumer call sites across eight modules** answer "which verdict is
current?" from artifact frontmatter today — more than the three an earlier
revision of this plan named. This WP's `owned_files` covers the
**safety-relevant** subset (the merge gate, the lane gate, preflight,
forecast, and the orchestrator API ingress); it does not claim to re-point
every one of the ten in this WP alone — record in this WP's Activity Log which
of the ten remain un-migrated after this WP, so a later WP (or WP13's
consumer-unification pass) has an accurate residual list rather than an
assumed-zero one.

**Constraints (binding)**:
- Do not touch `ReviewOverride`'s four-field shape (`at`, `actor`, `wp_id`,
  `reason`) — it is pinned verbatim by another mission's WP03/WP09.
- Do not remove or weaken the existing `review` slot's handling in
  `_apply_annotation_delta` — the new slot is additive, and both slots may be
  populated simultaneously (an override recorded after an approval, for
  instance); T026 states the precedence rule for that case, it does not
  collapse the two into one.
- `mypy --strict` / `ruff` clean, complexity ceiling ≤15 on every touched
  function (NFR-002) — `_wp_state_from_event` and `_apply_annotation_delta`
  are both already nontrivial; extract a helper rather than inlining the new
  branch if either would cross 15.
- NFR-004 (≥90% diff-coverage) applies to every touched line in this WP's
  eight owned files.

## Subtask T025 — Add the reducer branch surfacing the event verdict

- **Purpose**: Give `ReviewResult` a reducer-computed slot so something
  downstream of `reduce()` can finally read it.
- **Steps**:
  1. In `src/specify_cli/status/reducer.py`, add a new branch to
     `_wp_state_from_event` (near line 100-152) that, when the incoming
     `event` carries a populated `ReviewResult` (via whatever field the event
     model exposes it on — trace `StatusEvent`'s definition in `models.py` to
     confirm the exact attribute path from event to `ReviewResult`, do not
     assume it matches `WPInnerStateDelta.review`), derives the new slot's
     value and writes it into `state`.
  2. Carry the new slot forward like the existing runtime slots — but **not**
     by adding it to `_RUNTIME_SLOTS` (see T026's naming/precedence note for
     why it needs its own carry-forward branch instead of a tuple entry).
  3. Confirm `reduce()` (line 265) actually calls `_wp_state_from_event` on
     the code path that processes a transition carrying a `ReviewResult` —
     trace the call at line 331 (`wp_states[event.wp_id] =
     _wp_state_from_event(event, current)`) to confirm no earlier filtering
     drops `ReviewResult`-bearing events before they reach this function.
- **Files**: `src/specify_cli/status/reducer.py`
- **Validation checklist**:
  - [ ] A `StatusEvent` carrying a `ReviewResult` produces a snapshot with the
        new slot populated after `reduce()`.
  - [ ] An event with no `ReviewResult` leaves the slot untouched (carried
        forward from `previous`, or absent if never set).
  - [ ] `_wp_state_from_event`'s cyclomatic complexity stays ≤15 after the
        addition (extract a helper if the new branch pushes it over).
- **Edge Cases**: A transition that carries a `ReviewResult` with
  `verdict="changes_requested"` (the rejection case) must populate the slot
  identically to the `verdict="approved"` case — this reader has no business
  filtering by verdict value; it surfaces whatever the event says.

## Subtask T026 — Name the slot distinctly from `review`; state the precedence rule

- **Purpose**: The pre-existing `review` slot already carries
  `ReviewOverride.to_dict()` — a different fact (an arbiter's decision to
  proceed over a standing rejection) from the verdict this WP surfaces (a
  reviewer's approve/reject decision). Overloading one slot with two facts is
  exactly the ambiguity ADR 2026-07-19-1 exists to remove (Complexity Tracking
  table, plan.md). This subtask is the naming and precedence decision, not
  incidental to T025.
- **Steps**:
  1. Choose a slot name that is unambiguous against `review` — e.g.
     `review_result` (matching the field name already used on `StatusEvent`
     and in `wp_state.py`'s `_check_review_result` reference) is the natural
     choice; confirm it does not collide with any existing snapshot key
     before committing to it.
  2. Document, in the reducer module's docstring or an inline comment at the
     new branch, the **precedence rule** for the case where both `review` and
     the new slot are populated for the same WP (e.g., a standing rejection
     is later overridden by an arbiter — both facts exist, and a consumer
     asking "is this approved?" needs a deterministic answer). State clearly:
     an arbiter override in the `review` slot takes precedence over a
     `review_result` verdict of `changes_requested` for gate-clearing
     purposes (this matches the existing arbiter behaviour — an override
     already clears the merge gate without needing an approval — see
     `test_2684_review_override_recognition.py`, referenced in spec.md
     FR-010), but does **not** overwrite or erase the `review_result` slot's
     own value — a consumer asking "what was the reviewer's actual verdict"
     (as opposed to "is the gate clear") still needs the real answer.
  3. Add this precedence rule as an explicit, testable assertion in
     `tests/status/test_reducer.py` (T025/T026's shared test surface) — not
     merely as a comment.
- **Files**: `src/specify_cli/status/reducer.py`, `tests/status/test_reducer.py`
- **Validation checklist**:
  - [ ] The new slot's name does not collide with `review` or any other
        existing snapshot key.
  - [ ] A test exists asserting the precedence rule when both slots are
        populated for the same WP.
  - [ ] The docstring/comment stating the precedence rule is discoverable at
        the point where both slots are written (not buried in an unrelated
        location).
- **Edge Cases**: A WP that has `review_result` populated but `review` (the
  override slot) never touched must resolve identically before and after this
  change — the precedence rule only matters when both are present; it must
  not alter the single-slot-populated case.

## Subtask T027 — Make the reader snapshot-first with PRIMARY fallback

- **Purpose**: Deliver FR-001/SC-011 as an actual property, not a
  documentation claim, while not manufacturing SC-012's forbidden failure
  mode (a safety gate silently returning "no verdict" for every un-migrated
  mission).
- **Steps**:
  1. Build a reader function (a natural home is alongside the reducer, e.g.
     `status/reducer.py` or a thin wrapper in `status/__init__.py`'s public
     surface — check what other "resolved fact" readers in `status/` already
     expose as their public entry point and match that convention rather than
     inventing a new module) that: given a `feature_dir` and `wp_id`, first
     calls `materialize`/`reduce` and reads the new `review_result` slot from
     the snapshot; if the slot is **absent from the snapshot entirely**
     (not merely `None` for a legitimate populated-but-empty state — see
     T028), fall back to the pre-existing frontmatter-parsing path
     (`rejected_review_artifact_for_terminal_lane` /
     `latest_review_artifact_verdict`, whichever the specific consumer
     already uses) as the un-migrated-mission compatibility path.
  2. This reader is explicitly **snapshot-first-with-fallback**, never
     snapshot-only. Do not gate the fallback on `status_phase` or any other
     per-mission opt-in key — this mission's own `meta.json` has no such key,
     so a `status_phase`-gated fallback would not even help this mission
     migrate itself.
  3. Add `status_phase` to WP01's census as a governed input (per plan.md's
     IC-04 risk note) — if WP01 has already landed by the time this WP
     starts, confirm the census already covers it; if not, coordinate with
     WP01's owner or add the governed-input entry directly if the census
     format allows a follow-on addition without reopening WP01's own scope.
  4. Write the reader such that a genuinely damaged/unreadable frontmatter
     fallback source does not crash uncaught — this WP does not own reader
     polarity generally (WP14 does), but this *specific new* reader must not
     introduce a sixth undeclared-polarity reader into the census WP01
     produces. State its polarity explicitly (fail-closed: treat an
     unreadable fallback as "no verdict", consistent with how the merge gate
     already treats a missing artifact) and note that choice in the module
     docstring for WP14 to pick up.
- **Files**: `src/specify_cli/status/reducer.py` (or the module you determine
  is the correct public-reader home per the existing `status/` convention)
- **Validation checklist**:
  - [ ] A migrated mission (snapshot slot populated) reads its verdict from
        the snapshot without touching the frontmatter fallback path at all.
  - [ ] An un-migrated mission (snapshot slot entirely absent — simulate by
        constructing a snapshot from events with no `ReviewResult` ever
        emitted) falls back to frontmatter and returns the real verdict, not
        "no verdict".
  - [ ] This mission's own `meta.json` (no `status_phase` key) is used as a
        literal test fixture proving the fallback path actually fires for a
        real, current, un-migrated case — not just a synthetic one.
  - [ ] The reader's failure polarity on an unreadable fallback source is
        documented and tested.
- **Edge Cases**: A mission mid-migration — snapshot slot present but empty
  (`review_result: None`) versus snapshot slot key absent entirely — must be
  distinguished; the former is T028's "populated but null" case (do not fall
  back), the latter is "never migrated" (do fall back). Conflating the two
  reintroduces the SC-012 failure by falling back when it shouldn't, or
  worse, reintroduces stale-artifact trust when it should have fallen back.

## Subtask T028 — Define behaviour for `review_result: null` under `--force`

- **Purpose**: `wp_state.py:183-184`'s `check_transition` short-circuits to
  `_check_force(ctx)` when `ctx.force` is true, bypassing `guard_for(target,
  ctx)` entirely — meaning a forced transition can complete with no
  `ReviewResult` ever supplied. The reader built in T027 must have an explicit,
  tested answer for this case, distinct from "un-migrated mission" (T027) and
  distinct from "damaged record" (WP14).
- **Steps**:
  1. Confirm by direct trace (not assumption) that a `--force` transition
     really does skip review-result population — write a minimal
     reproduction: build a transition with `force=True`, `actor` and `reason`
     set, no `ReviewResult`, run it through `reduce()`, and inspect the
     resulting snapshot's `review_result` slot.
  2. Define the reader's behaviour when the slot is **present in the
     snapshot but its value is `None`/absent** (as distinct from the key
     being missing from the snapshot dict altogether, T027's fallback
     trigger): this reads as "no verdict was ever recorded for this WP's
     current state" — a legitimate, honest answer, not an error and not a
     trigger for the frontmatter fallback (the event log, having actually
     processed this WP, is authoritative that no verdict exists — falling
     back to a stale frontmatter artifact here would resurrect exactly the
     multi-authority problem this mission closes).
  3. Ensure every re-pointed consumer (T029/T030/T031) treats "no verdict
     recorded" (this case) differently from "verdict recorded as rejected" —
     a terminal-lane gate, for instance, should very likely still refuse a
     `None` verdict for an `approved`/`done` WP (absence of evidence is not
     evidence of approval), but the earlier merge gate must not report this
     as a schema error or a "damaged record" the way it would a genuinely
     corrupt artifact.
- **Files**: `src/specify_cli/status/reducer.py`, wherever T027's reader lives,
  `tests/status/test_reducer.py`
- **Validation checklist**:
  - [ ] A `--force` transition with no `ReviewResult` is reproduced and its
        resulting snapshot slot value is asserted explicitly (not merely
        "doesn't crash").
  - [ ] The reader distinguishes "slot present, value null" from "slot key
        absent" and does not fall back to frontmatter for the former.
  - [ ] At least one re-pointed consumer (pick the merge gate, since it's the
        highest-stakes) is tested against this exact case: forced transition
        to `approved`/`done`, no verdict recorded, gate still refuses.
- **Edge Cases**: A `--force` transition that *also* happens to have a stale
  rejected artifact on disk from an earlier, non-forced cycle — the reader
  must not resurrect that stale artifact as the answer just because the event
  log says "null"; "null" is itself the authoritative answer once the event
  log has spoken for this WP's current transition.

## Subtask T029 — Re-point the merge gate and `_lane_gate` at the slot

- **Purpose**: `post_merge/review_artifact_consistency.py` (the merge gate)
  and `cli/commands/review/_lane_gate.py` (Gate 1, WP lane consistency) both
  currently answer "is this WP's latest verdict acceptable?" purely via
  `find_rejected_review_artifact_conflicts` /
  `rejected_review_artifact_for_terminal_lane`, i.e., frontmatter parsing.
  Confirmed by direct grep: neither file references `review_result` or
  `ReviewResult` today. This subtask makes them consult T027's reader too.
- **Steps**:
  1. In `_lane_gate.py`'s `check_wp_lanes` (the function that currently calls
     `find_rejected_review_artifact_conflicts(feature_dir)` directly), add a
     call to T027's reader for each non-done WP under consideration and
     incorporate its answer into the existing findings-list mechanism — do
     not replace the frontmatter check outright (WP08 must land its
     reconciliation first, and WP13 is what narrows/unifies the fan-out
     later; this WP adds the event-sourced answer *alongside* the existing
     frontmatter check, consistent with FR-001's "the event is authoritative
     for which verdict is current" — meaning when the two disagree, the
     event wins, not that the frontmatter check is deleted here).
  2. In `post_merge/review_artifact_consistency.py`, locate every function
     currently reading `rejected_review_artifact_for_terminal_lane` and
     thread in the same event-sourced check, with the event's answer taking
     precedence per FR-001 when the two disagree.
  3. Add a defined conflict-resolution note (a comment, and a test) for the
     case where the event says "approved" but the frontmatter's latest
     artifact says "rejected" (or vice versa) — per FR-001, the event wins;
     this is the literal delivered property this WP exists to make real.
- **Files**: `src/specify_cli/post_merge/review_artifact_consistency.py`,
  `src/specify_cli/cli/commands/review/_lane_gate.py`
- **Validation checklist**:
  - [ ] Both gates consult the event-sourced reader in addition to the
        existing frontmatter check.
  - [ ] A test seeds a WP where the event says `approved` and the
        frontmatter's latest artifact says `rejected`; the gate reports
        approved (event wins).
  - [ ] A test seeds the reverse (event says `changes_requested`,
        frontmatter says `approved`); the gate refuses (event wins).
  - [ ] The existing frontmatter-only tests for both gates still pass
        unmodified where no event-sourced verdict exists (T027's fallback
        path).
- **Edge Cases**: A WP with `review_result: null` (T028's forced-transition
  case) reaching the merge gate for an `approved`/`done` lane must still be
  refused by the gate — the gate's existing frontmatter-based refusal is the
  correct fallback answer here, since the event log has nothing to add and
  the frontmatter is the only remaining signal (this is different from the
  slot-absent/un-migrated case, where fallback happens by design in T027).

## Subtask T030 — Re-point `merge/preflight.py` and `merge/forecast.py`

- **Purpose**: These two modules are the real, exercised call sites for the
  merge gate at merge time (`preflight.py`) and at `merge --dry-run` preview
  time (`forecast.py`) — both currently import
  `run_review_artifact_consistency_preflight` /
  `format_review_artifact_finding` / `review_artifact_finding_diagnostic` from
  `post_merge/review_artifact_consistency.py` and nothing from `status/`.
  Once T029 makes the gate itself event-aware, these two callers need no
  further code change **if** they call through the gate's public functions
  unconditionally — confirm that by tracing the actual call path, not by
  assumption, since `forecast.py`'s `_emit_review_artifact_block` renders its
  own preview text and may independently need the event-sourced answer.
- **Steps**:
  1. Trace both modules' calls into `post_merge/review_artifact_consistency.py`
     end to end. If they consume `run_review_artifact_consistency_preflight`'s
     return value opaquely (no independent re-derivation), T029 alone
     suffices and this subtask's work is confirming/testing that.
  2. If either independently re-parses artifact frontmatter (check
     `_emit_dry_run_error`, `_emit_review_artifact_block`, and any other
     `forecast.py` function touching review artifacts), re-point it at
     T027's reader the same way T029 did for the gate.
  3. Add or update `--dry-run` output tests confirming the previewed verdict
     matches the event-sourced answer when the two partitions disagree.
- **Files**: `src/specify_cli/merge/preflight.py`,
  `src/specify_cli/merge/forecast.py`
- **Validation checklist**:
  - [ ] Confirmed by trace (documented in this WP's Activity Log) whether
        either module independently re-derives a verdict outside the gate's
        own function calls.
  - [ ] If independent logic exists, it is re-pointed and tested identically
        to T029's gate-level test.
  - [ ] If no independent logic exists, a regression test proves the
        dry-run preview already reflects T029's event-sourced answer
        end-to-end (not merely "the code compiles").
- **Edge Cases**: `merge --dry-run`'s JSON payload shape is frozen by
  `contracts/cli-surface-contract.md` per `forecast.py`'s own docstring — if
  any new key is needed to surface the event-sourced verdict distinctly from
  the frontmatter one, that is a contract change requiring the same care as
  any other frozen-surface change (check whether the existing
  `REJECTED_REVIEW_ARTIFACT_CONFLICT` key can carry the richer answer, or
  whether a new key is genuinely needed and must be added to the contract
  file, not silently introduced).

## Subtask T031 — Close the `orchestrator_api` ingress hole

- **Purpose**: `orchestrator_api/commands.py:1296`'s
  `_parse_review_result_json` is the **external ingress** — an operator (or
  any external automation calling the orchestrator API) supplies
  `--review-result-json` and this function constructs a `ReviewResult` from
  it, validating exactly four fields (`reviewer`, `verdict`, `reference`,
  optionally `feedback_path`). This is the one entry point where an
  externally-supplied payload becomes the authoritative event this WP just
  made real — if its validation is looser than what the reducer/reader now
  assume, an external caller can inject a malformed or semantically-invalid
  verdict that the new authoritative path trusts blindly.
- **Steps**:
  1. Read `_parse_review_result_json` in full and enumerate what it currently
     validates: JSON-decodability, dict-shape, and that
     `reviewer`/`verdict`/`reference` are non-empty strings. Note what it does
     **not** validate: whether `verdict` is one of the sanctioned values
     (`"approved"` / `"changes_requested"` per `ReviewResult`'s docstring),
     and whether `reference` has the expected `feedback://` shape when
     `feedback_path` is also supplied.
  2. Add validation for `verdict`'s value against the sanctioned set — do not
     invent a new vocabulary (no new verdict value, only what
     `ReviewResult`'s docstring already sanctions).
  3. Ensure a malformed payload still raises `ValueError` with a message
     specific enough to name which field/value failed — not a bare re-raise
     of a generic JSON error for a semantic validation failure.
  4. Add a test seeding an out-of-vocabulary `verdict` value and asserting
     rejection with a clear message, alongside the existing JSON-shape tests.
- **Files**: `src/specify_cli/orchestrator_api/commands.py`
- **Validation checklist**:
  - [ ] `_parse_review_result_json` rejects an out-of-vocabulary `verdict`
        value with a clear `ValueError`.
  - [ ] Existing valid-payload tests for this function still pass unmodified.
  - [ ] The four-field validation this function already performs
        (`reviewer`/`verdict`/`reference` non-empty strings,
        `feedback_path` optional) is preserved, not weakened.
- **Edge Cases**: An external caller supplying `verdict="rejected"` (the
  vocabulary used elsewhere in this codebase for review-cycle artifacts,
  e.g. `REVIEW_ARTIFACT_VERDICTS`) rather than `ReviewResult`'s own
  `"changes_requested"` — confirm which vocabulary is actually correct for
  this ingress point (trace what value `_mt_plan_review_result` and other
  internal callers actually construct `ReviewResult` with) and reject the
  wrong one with a message naming the expected value, rather than silently
  accepting a plausible-looking but wrong string.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. This WP depends on WP01 (the
verdict-seam census) and branches from WP01's landed base. Completed changes
merge back into `pr/review-verdict-write-integrity-01KZ1CGF` unless the human
explicitly redirects the landing branch.

## Definition of Done

- The new reducer slot exists, is named distinctly from `review`, is not a
  `_RUNTIME_SLOTS` row, has a carry-forward entry, and its precedence rule
  against `review` is documented and tested.
- `test_2093_authority_invariant.py` (arm 2 in particular) still passes —
  confirm explicitly; do not assume adding a slot outside `_RUNTIME_SLOTS`
  is automatically safe against this test without running it.
- The reader is snapshot-first-with-fallback; the fallback is proven against
  this mission's own un-migrated `meta.json` as a real fixture, not only a
  synthetic one.
- `review_result: null` under `--force` is a defined, tested case distinct
  from both the un-migrated-mission fallback and WP14's damaged-record cases.
- The merge gate, `_lane_gate`, `merge/preflight.py`, `merge/forecast.py`, and
  the `orchestrator_api` ingress all consult the event-sourced answer, with
  the event winning on disagreement per FR-001.
- The residual count of un-migrated consumer call sites (out of the measured
  ten, across eight modules) is recorded honestly in this WP's Activity Log —
  not assumed to be zero.
- `mypy --strict` and `ruff` clean across all eight owned files; complexity
  ≤15 on every touched function; ≥90% diff-coverage.

## Risks & Mitigations

- **Snapshot-only regression**: the single most consequential risk named by
  the prior adversarial round — a naive re-point that drops the frontmatter
  fallback reproduces exactly the "no verdict" failure SC-012 forbids.
  Mitigate by testing the fallback against this mission's own un-migrated
  `meta.json`, a real fixture already in the repository.
- **Slot/`_EVENT_SLOTS` collision**: adding the new slot without care can red
  `test_2093_authority_invariant.py`'s arm 2 (dual-homing check). Mitigate by
  keeping the new slot out of `_RUNTIME_SLOTS` and running that test after
  every reducer change, not just at the end.
- **Precedence rule left implicit**: if the `review`/`review_result`
  interaction is only informally understood, a later WP (WP12's arbiter
  retirement, WP13's consumer unification) will re-derive it inconsistently.
  Mitigate by writing the rule down and testing it explicitly in this WP.
- **Ingress validation gap silently widened rather than closed**: adding a
  reader that trusts `ReviewResult` more than before, without tightening
  `_parse_review_result_json`'s validation, would make the external ingress
  a bigger attack surface than it was pre-mission. T031 is not optional
  cleanup — it is the closing half of the authority split this WP delivers.

## Reviewer Guidance

- Confirm the fallback path is proven against a real un-migrated mission
  (this mission's own `meta.json` is the intended fixture) — a reviewer
  should ask to see this specific test, not just a synthetic "slot absent"
  fixture.
- Confirm `test_2093_authority_invariant.py` was actually run (not merely
  assumed unaffected) after the reducer changes, and both arms still pass.
- Confirm the precedence rule between `review` and the new slot is both
  documented and covered by a test with both slots populated simultaneously.
- Confirm the `--force`/`review_result: null` case (T028) is tested against
  at least the merge gate, and that it is NOT conflated with either the
  un-migrated-mission fallback or a damaged-record case.
- Confirm `_parse_review_result_json`'s new vocabulary validation doesn't
  reject valid payloads existing callers already send — check for a
  regression in the existing orchestrator-api test suite for this function.
- Confirm the WP's Activity Log honestly states how many of the ten measured
  consumer call sites remain un-migrated, rather than implying full coverage.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.
- 2026-08-04T00:00:00Z – claude – lane=for_review – Implemented T025-T031.
  Summary: added a `review_result` reducer slot (NOT a `_RUNTIME_SLOTS` row —
  its own branch in `_wp_state_from_event`, triggered only on an
  outbound-from-`in_review` transition, sticky/carried-forward otherwise), a
  three-way reader (`ReviewResultLookup` / `review_result_from_state` /
  `event_sourced_review_result` in `status/reducer.py`), and re-pointed the
  merge gate (`post_merge/review_artifact_consistency.py`'s
  `find_rejected_review_artifact_conflicts`) to consult it with the event
  winning on disagreement (FR-001). `_lane_gate.py`, `merge/preflight.py`,
  `merge/forecast.py` needed no functional change — traced (not assumed) to
  consume the gate's shared function/result opaquely; each got a doc
  comment recording the trace. `orchestrator_api/commands.py` (T031) needed
  **no change at all**: the verdict-vocabulary validation the prompt
  describes as missing was already implemented and already tested (commit
  `50998a2e28`, 2026-07-09), predating this mission's creation
  (2026-08-03) — a prompt error, reported below.
  **Precedence rule (T026), verbatim**: an arbiter override recorded in the
  `review` slot clears the merge gate over a `review_result` of
  `"changes_requested"` for gate-clearing purposes ONLY; it does not
  overwrite or erase the `review_result` slot's own value — a consumer
  asking "what did the reviewer actually say" still reads the real,
  un-mutated `review_result`.
  **T030 trace result**: neither `merge/preflight.py` nor `merge/forecast.py`
  independently re-derives a verdict outside the gate's public functions —
  both consume `run_review_artifact_consistency_preflight`'s
  `ReviewArtifactPreflightResult` (`.passed` / `.findings` / `.diagnostics()`)
  opaquely. No `--dry-run` payload-shape change was needed; the existing
  `verdict` field inside `REJECTED_REVIEW_ARTIFACT_CONFLICT` findings now
  carries the event-sourced value when the event disagrees with frontmatter,
  so `contracts/cli-surface-contract.md` did not need a new key.
  **Honest residual (of the ten measured consumer call sites across eight
  modules the prompt/plan.md cite)**: this WP re-points exactly ONE reader
  function, `find_rejected_review_artifact_conflicts`
  (`post_merge/review_artifact_consistency.py`) — consumed by three call
  sites (the merge gate directly, `_lane_gate.py`'s Gate 1, and
  `merge/preflight.py`/`merge/forecast.py` transitively through it) — plus
  closes the external-ingress vocabulary hole at T031 (already closed
  pre-mission, confirmed by trace, no code change). I could not locate a
  single authoritative itemized list matching the literal "ten across eight"
  figure; the closest artifact, WP01's own
  `tests/architectural/census/verdict_seam_IC01.yaml`, enumerates **17**
  reader rows across **7** modules (a differently-scoped set — it includes
  readers that answer other questions, e.g. feedback-pointer resolution,
  not only "which verdict is current"). Against that census, the following
  reader rows remain **un-migrated** (frontmatter-only) after this WP — 16 of
  17, all outside this WP's `owned_files`:
  `agent_utils/status.py::_get_wp_review_verdict`,
  `agent_utils/status.py::show_kanban_status`,
  `cli/commands/agent/tasks_parsing_validation.py::_apply_review_status_flags`,
  `cli/commands/agent/tasks_parsing_validation.py::_get_latest_review_cycle_verdict`,
  `cli/commands/agent/workflow_cores.py::resolve_review_feedback_pointer`,
  `cli/commands/agent/workflow_executor.py::implement_try_render_fix_mode_prompt`,
  `review/arbiter.py::_persist_in_artifact`,
  `review/arbiter.py::get_arbiter_overrides_for_wp`,
  `review/arbiter.py::persist_arbiter_decision`,
  `review/artifacts.py::ReviewCycleArtifact.from_file`,
  `review/artifacts.py::ReviewCycleArtifact.latest`,
  `review/artifacts.py::latest_review_artifact_verdict`,
  `review/artifacts.py::rejected_review_artifact_for_terminal_lane`,
  `review/cycle.py::_guard_feedback_source_provenance`,
  `review/cycle.py::create_rejected_review_cycle`,
  `review/cycle.py::resolve_review_cycle_pointer`,
  `review/cycle.py::validate_review_artifact_file`.
  Do NOT read this WP as full coverage — WP13's consumer-unification pass
  (or a later WP) owns closing the rest.
  **Ownership-escalation note**: `find_rejected_review_artifact_conflicts`
  needed the event-sourced verdict, which architecturally must be consumed
  through the `specify_cli.status` public facade
  (`tests/architectural/test_status_module_boundary.py`'s SR-2 repo-wide AST
  gate) — but `status/__init__.py` (the facade's `__all__`) is NOT in this
  WP's `owned_files`. Resolved WITHOUT touching that file: the gate-verdict
  decode was written locally in `review_artifact_consistency.py` (mirroring
  its own pre-existing `_snapshot_review_override` convention) using only
  `ReviewResult`, which the facade already exports — so `review_result_from_state`
  / `event_sourced_review_result` / `ReviewResultLookup` stay reducer-internal,
  proven by `tests/status/test_reducer.py`, but are not yet promoted onto the
  public facade for other packages to import directly. Flagging so a later WP
  (or an operator) can add them to `status/__init__.py`'s `__all__` if a
  future consumer needs the shared accessor rather than a local decode.
  **Prompt errors found** (beyond the one pre-corrected in this WP's own
  brief): (1) T031's entire premise is stale — `_parse_review_result_json`
  already validates `verdict` against `{"approved", "changes_requested"}`
  and already has a dedicated out-of-vocabulary regression test
  (`tests/agent/test_orchestrator_commands_integration.py::
  test_transition_rejects_invalid_review_result_json`, parametrized with
  `verdict="maybe"`) — both landed in commit `50998a2e28` (2026-07-09),
  before this mission (`review-cycle-verdict-seam-rebuild-01KZ2W7W`) was
  created (2026-08-03). (2) The "ten consumer call sites across eight
  modules" figure (spec.md / plan.md IC-04 / this WP's own prompt) could not
  be independently verified against a single itemized source; the nearest
  artifact (WP01's census) yields a differently-shaped 17-rows/7-modules
  reader enumeration — see the residual list above.
- 2026-08-04T00:00:00Z – claude – lane=for_review – Addressed reviewer's
  blocking finding: the `review_result` trigger in `_wp_state_from_event` was
  keyed solely on `event.from_lane == Lane.IN_REVIEW`, but the emit path
  (`status/emit.py`, `coordination/status_transition.py`,
  `orchestrator_api/commands.py`'s external `transition` command) applies no
  `from_lane` filter of its own, so a single-hop `in_progress -> approved`
  (a legal edge per `InProgressState.allowed_targets`, reachable through the
  external orchestrator-api ingress with `evidence` + a populated
  `review_result` and no hop through `in_review`) carried a real verdict the
  narrower trigger silently dropped — worse, a prior `in_review` cycle's
  carried-forward stale verdict would then be presented as current. Fixed by
  widening the trigger to `event.review_result is not None or
  event.from_lane == Lane.IN_REVIEW`: any event carrying a populated verdict
  now populates the slot with it (overriding any carried-forward stale
  value), and the `from_lane == IN_REVIEW` leg is kept solely to capture the
  forced-null case (T028) that only that guard's bypass creates. Updated
  `_wp_state_from_event`'s docstring accordingly. Added two tests to
  `tests/status/test_reducer.py`:
  `test_single_hop_in_progress_to_approved_with_review_result_populates_slot`
  and
  `test_single_hop_in_progress_to_approved_overrides_stale_carried_forward_verdict`
  — both pass. Re-ran `tests/status/test_reducer.py` +
  `test_2093_authority_invariant.py` (53 passed) and
  `tests/post_merge/ tests/merge/ tests/review/` (1162 passed, 1 skipped) —
  identical to the reviewer's own independent numbers. ruff, ruff C901, and
  `mypy --strict` clean on all seven touched `src/` files plus
  `tests/status/test_reducer.py`; zero new suppressions.
  **Residual, recorded per reviewer instruction (no behaviour change made)**:
  T028 step 3's "hardening" half — a terminal-lane gate refusing a `None`
  recorded verdict for an `approved`/`done` WP even when the frontmatter's
  latest artifact happens to read `approved` (absence of evidence is not
  evidence of approval) — is **not delivered** by this WP.
  `_resolve_terminal_verdict_conflict`'s step 5 defers to the frontmatter-only
  answer for the null case, which is byte-for-byte the pre-WP07 behaviour
  preserved deliberately (changing it would alter forced-approval workflows
  outside this WP's charter). Concretely: forced-approval + no recorded
  verdict + a stale **approved** artifact still clears the gate today. This
  is WP13/WP14 territory (consumer unification / declared reader polarity),
  not silently satisfied by this WP.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP07 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
