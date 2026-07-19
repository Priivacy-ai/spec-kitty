# Implementation Plan: Sync batch-400 poison isolation (bisection)

**Branch**: `fix/2736-batch-400-poisoning-isolation` | **Date**: 2026-07-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/sync-batch-400-poison-isolation-01KXW08B/spec.md`

> Pre-spec research: [research/pre-spec-4lens-squad.md](research/pre-spec-4lens-squad.md). Post-spec squad
> findings + the P0-vs-refactor sequencing are folded into the spec (Post-Spec Squad Findings section).

## Summary

**Approach (chosen):** CLI-side **recursive bisection** on a whole-batch HTTP 400 in
`delivery/receivers.py` — split → re-POST **both** halves → recurse to singletons — isolating the
culprit and delivering every innocent half. The culprit stays `rejected` (non-terminal, retryable);
because `rejected` re-selects forever, bisection is what stops the *whole-batch re-poisoning*. No server
change (non-destructive FIFO drain + selective commit make it CLI-solvable).

The culprit-isolating split rests on a **shared pure primitive** at `core/batch_partition.py` — two
distinct functions: `split_in_half(events)` (plain keep-left cut) and `create_aware_midpoint(events,
key_of)` (create-aware cut). It is the SSOT that also **closes #2755** by de-duplicating the one real
sibling split site (`_shrink_events_for_retry`, which consumes the *plain* `split_in_half`). Per post-spec
alignment, this is a shared *mechanism* with per-caller *policy*, **not** a `BatchSplitter(mode=…)`
god-authority. **The create-before-status ordering invariant is NOT the primitive's job** (a batch-spanning
create/status pair cannot be kept together by any midpoint) — it is enforced by IC-04's **sequential
left-before-right recursion** in the bisect adapter (post-plan squad: alphonso + renata).

**Sequenced so the release-blocking P0 ships independently of the SSOT retrofit** (the highest-risk,
lowest-urgency work): the P0 lands on the primitive + bisection; #2755 closure is last and release-optional.

**Rejected alternatives:** change the server all-or-nothing 400 contract (deliberate boundary; CLI-side
fully solves delivery); a single policy-bearing split authority (false unification — the 413/400/queue
policies differ, paula); CLI emits `force` on the backward transition (corrupts provenance — the CLI FSM
is authoritative; server aligns via spec-kitty-saas#509).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib + existing `specify_cli.delivery` (receivers, ledger) / `specify_cli.sync`
(batch, queue) / `specify_cli.status` packages; no new third-party dependency
**Storage**: the append-only delivery ledger (`SqliteDeliveryLedger`) + the sync queue (non-destructive FIFO
drain, `ORDER BY timestamp ASC, id ASC`) — both unchanged in shape
**Testing**: pytest ATDD/red-first — the merged `tests/delivery/test_poison_batch_2736.py` (RED anchor),
new straddle-ordering + ledger-residual + bounded/idempotent tests, the live offline-queue-disposition test, the
CLI FSM contract test; a **drain harness** (`deliver()` → record → `select_undelivered` → re-drain) is new
test infrastructure (IC-01)
**Target Platform**: Linux/macOS dev + CI
**Performance Goals**: none new — bisection fires only on the poison path; ~2·log₂(N) POSTs per culprit,
bounded (NFR-002); the happy `sync now` path is untouched (NFR-001)
**Constraints**: CLI repo only (C-001 — SaaS work → #509/#510); no server contract change (C-002); no
`force` papering (C-003 — CLI FSM authoritative); the shared split is a **pure mechanism** at `core/`
(neutral leaf — NOT `delivery/`, which would invert the `delivery → sync` edge into a `sync → delivery`
cycle, uncaught by the layer gate — alphonso), not a policy-owning authority (paula); ordering is the
bisect adapter's sequential recursion, not the primitive; touched functions ≤ CC-15; ATDD red-first; no
direct push to origin/main
**Scale/Scope**: 1 new pure primitive module + 1 receiver-adapter change + 1 live offline-queue in-context fix +
1 contract test + the drain-harness test infra; ~6 WPs (P0 = 3 of them)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Loaded via `spec-kitty charter context --action plan` (DIR-001…DIR-013).

| Gate / Standing Order | Applies? | How this plan satisfies it |
|---|---|---|
| **ATDD-first / red-first** | ✅ | The P0 anchor `test_poison_batch_2736.py` is merged-RED for the product reason; new ACs (straddle-order, ledger-residual, bounded/idempotent) are authored red-first before the fix. |
| **Single canonical authority (DIR-044)** | ✅ | The SSOT is ONE pure primitive module at `core/batch_partition.py` (the neutral leaf both `delivery` and `sync` already import downward via `core.time_utils`); the genuinely-shared midpoint math is `split_in_half`, with exactly one home so no splitter re-derives the `len//2` cut. Guard (SC-004) = behavioral-delegation + AST `//2`-midpoint, scoped to `split_in_half` (not a source-count). |
| **Architectural alignment** | ✅ | Shared *mechanism* + per-caller *policy* (paula); `_run_dispatch_batches` (limit-halving) is an explicit non-goal — not forced into the seam. Bounded-context boundary respected (receiver `DeliveryResult` vs legacy `BatchEventResult` kept separate). |
| **Campsite / CC-15 / Sonar** | ✅ | The single-send-helper + primitive extractions are testable pure functions; each new branch/helper gets a focused test; the #2755 de-dup reduces (not grows) duplication. |
| **Red-main-is-honest (ADR 2026-07-17-1)** | ✅ | The P0 anchor is honestly RED on the base; the fix flips it green; the culprit stays `rejected` (matches the test — question-2 is NOT papered over). |
| **Git/workflow discipline (no direct push)** | ✅ | Lands via `pr/<slug>` PR to upstream/main (draft-first). |
| **Tracker Ticket Assignment Rule** | ✅ | #2736 (P0, parent #1800) + #2755 (superseded-by #2736) assigned to stijn-dejongh; SaaS #509/#510 filed cc @LynnColeArt cross-linking #2736; #2736 informs Lynn. |
| **Terminology canon** | ✅ | `Mission` not `feature`; no `feature*` aliases in new code. |

**No unjustified violations.** Complexity Tracking records the deliberate P0-vs-refactor sequencing fence.

## Project Structure

### Documentation (this mission)

```
kitty-specs/sync-batch-400-poison-isolation-01KXW08B/
├── plan.md, spec.md, research/pre-spec-4lens-squad.md
├── traces/{tooling-friction,approach,design-decisions}.md   # mission tracer files (seeded)
└── tasks/                                                    # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── core/
│   └── batch_partition.py  # NEW — pure SSOT leaf (imported downward by BOTH delivery & sync, like
│                           #   core.time_utils): `split_in_half(events)` (plain keep-left cut) +
│                           #   `create_aware_midpoint(events, key_of)` (create-aware cut). Ordering-agnostic.
├── delivery/
│   ├── receivers.py      # `_HttpReceiver._post_batch`/`deliver` → extract `_attempt_batch_send`
│   │                     #   → (int|None, Mapping|None); recursive bisection adapter (send-both, sequential
│   │                     #   L-before-R) using create_aware_midpoint; None-status → all-transient, no recurse;
│   │                     #   `_map_400:368` fan-out reached only for culprit-bearing singletons
│   └── ledger.py         # (read) `select_undelivered` / non-terminal `rejected` — the residual-set signal
├── sync/
│   └── batch.py          # `_parse_error_response:967-985` no-details branch → transient (LIVE fix, WP04);
│                         #   `_shrink_events_for_retry:392` rewired onto PLAIN `split_in_half` (WP05)
└── status/wp_state.py    # (read/contract-test only) force-free backward edges

tests/
├── core/
│   └── test_batch_partition.py           # NEW: the pure primitive (split_in_half halving, create-aware midpoint)
├── delivery/
│   ├── test_poison_batch_2736.py         # MODIFY: order-recording poster; culprit-singleton assertion
│   └── test_batch_bisection_ordering.py  # NEW: straddle fixture + receipt-order + drain-harness residual-set
├── sync/                                 # NEW focused test for the live offline-queue in-context fix
├── architectural/                        # NEW: single-authority guard (behavioral delegation + AST //2)
└── status/                               # NEW: CLI FSM force-free contract test
```

**Structure Decision**: Single-project CLI/library. One new pure module (`core/batch_partition.py` — placed
in `core/`, not `delivery/`, so the #2755 retrofit's `sync` consumer imports *downward* into a neutral leaf
instead of creating a `sync → delivery` runtime cycle the layer gate wouldn't catch — alphonso), one
receiver-adapter change, one in-context legacy fix, and test infrastructure (drain harness). No new
package, no server change, no data model beyond the existing ledger/queue.

## Complexity Tracking

| Deliberate choice | Why | Simpler alternative rejected because |
|---|---|---|
| P0 (bisection) sequenced ahead of + independent of the #2755 SSOT retrofit | The P0 is release-blocking; the retrofit touches merged #2735 code (highest regression risk) | Gating the release on #2755 closure welds a P2 refactor to the P0 ship date (priti) |
| Shared *pure mechanism* + per-caller policy (not a mode-object authority) | The split policies genuinely differ (413 drop-rest / 400 send-both / queue disposition); one authority conflates bounded contexts (paula) | A `BatchSplitter(mode=…)` recreates the split-brain inside one class |
| Drain-harness test infra (deliver → ledger → select_undelivered → re-drain) | `deliver()` doesn't touch the ledger; the re-poison mechanism only shows across a full drain (renata) | A `deliver()`-layer success-count restates SC-001 and never exercises the non-terminal re-poison |

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.
> Sequencing intent: **IC-02 + IC-03 → IC-04 is the P0 critical path (release-blocker);** IC-05/IC-06/IC-07
> are off it (IC-06 last + release-optional).

### IC-01 — Acceptance infrastructure (red-first anchor + drain harness)

- **Purpose**: Make the P0 provable and non-fakeable — extend the merged repro + stand up a drain harness.
- **Relevant requirements**: SC-001, SC-002, SC-003, FR-008; US1/US2.
- **Affected surfaces**: `tests/delivery/test_poison_batch_2736.py` (order-recording poster; culprit-singleton
  assertion), `tests/delivery/test_batch_bisection_ordering.py` (NEW — straddle fixture **with teeth: the
  culprit sits in the create/left half, and the create+status events are non-adjacent and on opposite sides
  of the naive midpoint** — else the assertion passes trivially; `receipt_index(create) < receipt_index(status)`;
  ledger residual-set `select_undelivered == {culprit}` + re-drain no-reselection).
- **Sequencing/depends-on**: authored red-first alongside IC-04.
- **Risks**: the poster must record an ordered receipt log (NOT `frozenset`). The drain harness must record
  `deliver()` results into the ledger or SC-002 collapses to SC-001 — and the **bridge must pass the
  `DeliveryOutcome` enum**: `ledger.record_result(event_id=r.event_id, target_id=tid, result=r.outcome)`.
  Passing the `DeliveryResult` object raises `ValueError` in `_coerce_result_token` (pedro's "looks-done-but-
  throws" trap). No WP07 dispatcher is needed — the harness stands up in `tests/delivery/` directly.

### IC-02 — Single-attempt batch-send seam (prereq refactor)

- **Purpose**: Extract one `_attempt_batch_send(events) -> (int | None, Mapping | None)` so the bisect can
  recurse over it. The `None` status models the transport-failure branch (`requests.RequestException`, which
  short-circuits to a batch-wide TRANSIENT before `map_batch_response`) — the caller maps `None →
  all-transient and does NOT recurse/split` (splitting a transport failure would multiply transients).
- **Relevant requirements**: FR-001. **Affected surfaces**: `src/specify_cli/delivery/receivers.py`.
- **Sequencing/depends-on**: none (first). **Risks**: pure refactor — existing `tests/delivery/` stay green;
  the seam signature must carry `int | None` (not `int`) or the transport branch has no representable status.

### IC-03 — The shared pure partition primitive (SSOT mechanism)

- **Purpose**: One home for two distinct functions — `split_in_half(events)` (plain keep-left cut, consumed
  by the legacy 413 shrink) and `create_aware_midpoint(events, key_of)` (create-aware cut, consumed by the
  bisect). Placed at **`core/batch_partition.py`** (neutral leaf both packages already import downward), NOT
  `delivery/` (alphonso: avoids the `sync → delivery` cycle IC-06 would otherwise introduce). **The primitive
  is ordering-agnostic** — it does not and cannot guarantee create-before-status for a batch-spanning pair;
  that is IC-04's sequential recursion. `create_aware_midpoint` has a single consumer today; the genuinely
  de-duplicated / #2755-relevant surface is `split_in_half`.
- **Relevant requirements**: FR-003 (mechanism half), FR-006 (mechanism — **necessary but NOT sufficient to
  close #2755; #2755 stays Open until IC-06 rewires the legacy consumer**). **Affected surfaces**:
  `src/specify_cli/core/batch_partition.py` (NEW), `tests/core/test_batch_partition.py` (NEW).
- **Sequencing/depends-on**: none (P0 prereq). **Risks**: element-generic via injected `key_of` (works on
  `dict` keyed at `aggregate_id` AND `OutboundEvent` keyed inside `payload`) — do NOT sniff the wp_id shape
  inside the primitive (would recreate the bounded-context leak); pure/deterministic/no-I/O; `split_in_half`
  guarantees a non-empty left slice for the singleton edge (`max(1, len//2)`).

### IC-04 — Recursive bisection adapter (the MVP)

- **Purpose**: The release-blocking fix — isolate the culprit, deliver innocents, preserve ordering. **The
  ordering guarantee (`receipt_index(create) < receipt_index(status)`) lives HERE**, in the sequential
  left-before-right recursion — the primitive cannot provide it (alphonso).
- **Relevant requirements**: FR-002, FR-003 (sequential L-before-R), FR-004, FR-008; NFR-001, NFR-002/003;
  US1/US2. **NFR-001 owned here**: the no-poison `sync now` happy path is behaviorally unchanged and
  `tests/delivery/` + `tests/sync/` stay green (closes the SC-006 ownership gap — renata).
- **Affected surfaces**: `src/specify_cli/delivery/receivers.py` — a new `_bisect_send(events) -> list[...]`
  (attempt via IC-02 helper → on 400-without-`details` & `len>1`: split via `create_aware_midpoint` + concat
  `_bisect_send(left)+_bisect_send(right)` → base `len==1` → `_map_400` singleton), keeping `deliver()`/
  `_post_batch` trivial (CC-15 safe). **A `None` status from IC-02 → all-transient, never split.**
- **Sequencing/depends-on**: IC-02, IC-03. **Risks**: sequential (never parallel) recursion; culprit stays
  `rejected` non-terminal (not force-parked); bounded/terminating; no accepted event re-POSTs (idempotency).

### IC-05 — Offline-queue **live** disposition fix

- **Purpose**: Fix the **LIVE** whole-batch-400 poison in the offline-queue path. **Post-tasks squad
  correction (paula, verified from source):** the originally-named `_record_all_events_failed:475-499` is
  DORMANT (all seven live callers pass `transient=True`); the live poison is `_parse_error_response`'s
  no-`details` else-branch (`sync/batch.py:967-985`), reached from the live `batch_sync` 400 handler
  (`:1188` → `process_batch_results`, which bumps `retry_count` on every `rejected` innocent) via
  `sync/background.py:455`.
- **Relevant requirements**: FR-005; SC-007. **Affected surfaces**: `src/specify_cli/sync/batch.py:967-985`
  (`_parse_error_response` no-`details` branch → treat as transient, mirroring the sibling 403/5xx branch),
  a focused `tests/sync/` test driving the live `batch_sync` 400-no-details path. **Leave the per-event
  `details` path (`:923-966`) unchanged — server-adjudicated, not poison.**
- **Sequencing/depends-on**: **none** — the fix is "mark transient, not rejected" and does NOT consume the
  primitive, so it is WP01-independent and ships in parallel-group 0. **Risks**: fix in the legacy
  `dict`/`BatchEventResult` model; do NOT import the receiver bisect (different bounded context); do NOT
  touch the server-adjudicated `details` path.

### IC-06 — #2755 SSOT retrofit + single-authority guard (last, release-optional)

- **Purpose**: Close #2755 — rewire `_shrink_events_for_retry` onto the **plain `split_in_half`** (NOT
  `create_aware_midpoint` — the byte-shrink must not inherit create-aware snapping); guard the SSOT.
- **Relevant requirements**: FR-006; SC-004. **Affected surfaces**: `src/specify_cli/sync/batch.py:392`
  (import `core.batch_partition.split_in_half`), `tests/architectural/` (behavioral-delegation guard + AST
  guard that no other `src/` module contains a `//2` events-midpoint, **scoped to `split_in_half`'s math**).
- **Sequencing/depends-on**: IC-03 (`split_in_half`), IC-05 (same file — sequence after the live fix).
  **Risks / post-tasks squad**: the rewire is **behavior-preserving by construction** — `split_in_half(events)[0]`
  is textually equal to the inline `events[:max(1,len//2)]` (renata) — so the six #2735 tests MUST stay green
  with NO shift; **any red is a mechanical bug to FIX, not "friction" to defer** (the escape hatch is reserved
  for a documented architectural blocker with operator sign-off, never a self-inflicted red). Guard hierarchy:
  **T017 behavioral-delegation (spy the real `split_in_half`) is the LOAD-BEARING, non-fakeable guard**; the
  AST `//2` guard (T018) is belt-and-suspenders and MUST allowlist `core/batch_partition.py` **and**
  `doc_analysis/gap_analysis.py:392` (a live unrelated `len//2` — paula/debbie), or scope to the `events`/
  `batch` identifier. Keep the 413 keep-left-drop-rest policy. **Off the P0 release gate** — genuinely
  decoupled (nothing in IC-01..IC-04 consumes the shrink rewire).

### IC-07 — CLI FSM force-free contract test (independent)

- **Purpose**: Pin `in_progress→planned` + review-rejection edges as force-free (CLI authoritative); document
  SaaS#509 as the server alignment.
- **Relevant requirements**: FR-007; SC-005; C-003. **Affected surfaces**: `tests/status/` (contract test).
- **Sequencing/depends-on**: none (parallelizable). **Risks**: assert the FSM guard does not consult `force`
  on these edges; the CLI must NOT emit force.
