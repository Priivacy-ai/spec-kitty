# Mission Specification: Sync batch-400 poison isolation (bisection)

**Mission Branch**: `fix/2736-batch-400-poisoning-isolation`
**Created**: 2026-07-19
**Status**: Draft
**Input**: P0 #2736 — one invalid event poisons its whole sync batch; innocent events don't deliver and get a misleading error. Fold in as much CLI-repo-editable scope as possible (operator @stijn-dejongh).

> Pre-spec research: [research/pre-spec-4lens-squad.md](research/pre-spec-4lens-squad.md) (debugger-debbie, architect-alphonso, planner-priti, researcher-robbie). Root cause + fix seam + ordering invariant all code-verified.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Innocent events in a poisoned batch deliver; the culprit is isolated (Priority: P1)

As an operator draining a sync backlog, when one genuinely-invalid event shares a batch with valid
events, I want every **innocent** event to deliver and only the **guilty** event to be rejected —
with its own specific reason — so that one bad event can never strand the rest of my backlog.

**Why this priority**: This is the P0 (#2736). Today a whole-batch HTTP 400 with no per-event
`details` makes the CLI (`receivers._map_400:368`) fan the batch error onto **every** event; since
`rejected` is non-terminal (`ledger.py:60-68`), the invalid event re-poisons every subsequent drain
and the innocents can *never* deliver. It is the upstream cause of the `wp_status_event_without_create`
projection-anomaly backlog (WP-status delivers while WP-create stays stranded).

**Independent Test**: Extend/keep-green the merged red-first repro `tests/delivery/test_poison_batch_2736.py`:
a mixed batch (1 invalid + N valid) through `ExternalReceiver.deliver` returns N `success` for the
innocents and one specific `rejected` for the culprit — AND (isolation pinned) the poster's POST log
shows the culprit reduced to a **final singleton** `{culprit}` POST, so isolation is asserted, not implied.

**Acceptance Scenarios**:

1. **Given** a batch of N events where exactly one is server-invalid and the server returns a
   whole-batch 400 with no per-event `details`, **When** `ExternalReceiver.deliver` runs, **Then**
   every innocent event returns `success` (delivered) and only the invalid event returns `rejected`
   carrying its own reason (not the fanned batch error).
2. **Given** the culprit event re-appears in a later drain, **When** the drain runs, **Then**
   bisection isolates it to a singleton again and the innocents are unaffected (no re-poisoning) —
   the culprit stays retryable (`rejected`, not force-parked) so it can deliver once SaaS#509 lands.
3. **Given** a batch with zero invalid events that 400s for a transient reason, **When** delivered,
   **Then** no event is falsely rejected (bisection terminates without mis-attributing a culprit).

---

### User Story 2 - Bisection preserves create-before-status ordering (Priority: P1)

As the SaaS projection consumer, I want the bisection to never deliver a WP-**status** event ahead of
its WP-**create** event, so the fix does not introduce *new* `wp_status_event_without_create`
inversions while it clears the old ones.

**Why this priority**: The load-bearing correctness invariant (robbie + alphonso). A create/status
pair straddling the split boundary — left half (create) 400s/recurses while right half (status)
200s/commits — would orphan the status. FIFO drain (`queue.py:1586`) guarantees create-before-status
in the drained list; bisection must not break it.

**Independent Test** (pinned, non-fakeable): a FIFO batch `[create(wpX)@idx0, …fillers…, invalid@idxK,
status(wpX)@idxN-1]` with create and status **non-adjacent and on OPPOSITE sides of the naive
midpoint**, and the **culprit in the create-bearing (left) half** — so a policy-preserving-but-order-
breaking bisect (left 400s/recurses while right 200s/commits) *would* commit `status(wpX)` before
`create(wpX)` succeeds. The fake poster records an **ordered receipt log** (accepted `event_id`s in POST
sequence — NOT a `frozenset`, which destroys order). A "same-half" set-membership assertion is
insufficient and rejected in review.

**Acceptance Scenarios**:

1. **Given** the pinned straddle fixture above, **When** bisection runs, **Then**
   `receipt_index(create(wpX)) < receipt_index(status(wpX))` — the create is accepted by the server
   strictly before its status. This REDs a naive-midpoint bisect.
2. **Both** dimensions are independently required (no OR): (a) the **create-aware split boundary**
   (in the shared primitive) keeps the pair un-split — tested via `create_aware_midpoint`'s unit tests;
   (b) **sequential left-before-right** recursion — tested via the receipt-order assertion above.

---

### User Story 3 - One shared partition MECHANISM (SSOT), not a god-authority — closes #2755 (Priority: P2)

As a maintainer, I want the create-aware halving **mechanism** to have exactly one home that the
poison-bisect and the legacy `_shrink_events_for_retry` both consume, each keeping its own **policy**
(send-both-halves vs keep-left-drop-rest) — so the split-brain surface shrinks and every splitter
inherits the un-splittable create/status boundary by construction.

**Why this priority**: Operator direction — **fully fold #2755** — done the *right* way (post-spec
alignment). The "four sites" span two bounded contexts + a limit-halving layer, so a single
policy-bearing authority would be a false unification (a `BatchSplitter(mode=…)` god-object recreates
the split-brain inside one class). The genuinely-shared SSOT is the pure `split_in_half` +
`create_aware_midpoint` primitive. The live `_run_dispatch_batches` (halves a re-selection *limit*, not
a sequence) is **excluded** as a non-goal. The offline-queue fix (FR-005) is a *disposition* fix in
its own context, not an "adopt the bisect" — it does not consume the primitive. `#2755` closes when
WP05 lands; **this is off the P0 release gate** (the P0 ships on US1/US2 alone).

**Independent Test**: The single split primitive has focused unit tests; a focused test drives the
legacy path's fan-out and asserts it no longer marks innocents rejected.

**Acceptance Scenarios**:

1. **Given** the two real split sites (the poison-bisect adapter and the legacy `_shrink_events_for_retry`
   — "byte-sizing" is already that same helper, not a distinct site), **When** they split a batch, **Then**
   both call the one shared `split_in_half` / `create_aware_midpoint` primitive (behavioral-delegation +
   AST guard; no independent `//2` midpoint elsewhere).
2. **Given** the legacy OfflineQueue drain hits a whole-batch failure, **When** it dispositions events,
   **Then** it does not fan a batch-level error onto innocent events (thin fix + focused test).

---

### User Story 4 - The CLI transition FSM is the authoritative, force-free contract (Priority: P2)

As the transition-contract owner, I want a CLI-side test that pins `in_progress → planned` (and the
review-rejection edges) as **force-free** legal transitions, documenting that the CLI is correct and
the SaaS server matrix is the side that must align (SaaS#509).

**Why this priority**: Question-2. Operator decision: **CLI FSM authoritative**. The CLI must NOT
emit `force` on these edges (that stamps a guard-bypass override + corrupts provenance). This pins
the contract so a future change can't silently make the CLI paper over server strictness.

**Independent Test**: A contract test asserting the canonical FSM (`wp_state.py`) permits
`in_progress → planned` with reason-only (no force), and the review-rejection edges with review_ref-only.

**Acceptance Scenarios**:

1. **Given** the canonical `wp_state.py` FSM, **When** `in_progress → planned` is validated with a
   reason and no force, **Then** it is legal (force-free) — and the test documents that a server 400
   demanding force is a SaaS-side contract drift tracked in spec-kitty-saas#509.

### Edge Cases

- All-invalid batch → bisection recurses to N singletons, each correctly rejected (bounded O(N) POSTs).
- Single-event batch that 400s → base case: that one event is rejected (no further split).
- A whole-batch 400 that DOES carry per-event `details` → keep the existing granular path; bisect only
  the no-granularity, >1-event case.
- A create lacking `project_uuid` (queued CLI-locally, never sent) → not a delivery bug; the anomaly
  metric won't reach zero from delivery alone (documented, SaaS#510).
- Crash between sub-POSTs → re-post returns `duplicate` (idempotent); no accepted event re-posts.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Extract a single-attempt batch-send helper (`_attempt_batch_send(events) -> (int \| None, Mapping \| None)`) in `delivery/receivers.py` — recursion needs one clean seam. The `None` status models the transport-failure branch (`requests.RequestException`); the bisect caller maps `None → all-transient and does NOT recurse` (never split a transport failure). | US1 | High | Open |
| FR-002 | Recursive bisection on a whole-batch 400 (>1 event, no per-event `details`): split → re-POST **BOTH** halves → recurse to singletons. NOT #2735's shrink-and-drop. `deliver()` accumulates results across sub-POSTs, returns exactly one result per input event (innocents `success`, culprit `rejected` with its own reason). | US1 | High | Open |
| FR-003 | The **create-aware split boundary lives in the shared partition primitive** (`create_aware_midpoint(events, key_of=<wp_id>)`) so EVERY splitter inherits it — it snaps the cut to keep an *adjacent* `wp_id`'s create+status out of different halves. The **ordering guarantee** for a batch-*spanning* create/status pair (which no midpoint can keep together) is the bisect adapter's **sequential left-before-right** recursion (never parallel/reorder). BOTH are independently required (no OR) — the primitive itself is ordering-agnostic. | US2 | High | Open |
| FR-004 | The isolated culprit stays **retryable** (`rejected`, non-terminal) — NOT force-parked — so it delivers once the SaaS matrix aligns (SaaS#509); bisection ensures it never re-poisons innocents. | US1 | Medium | Open |
| FR-005 | Narrow **in-context** fix to the **LIVE** legacy whole-batch-400 disposition `_parse_error_response`'s no-`details` else-branch (`sync/batch.py:967-985`, reached from the live `batch_sync` 400 handler at `:1188` via `sync/background.py:455`): when the server returns a whole-batch 400 with NO per-event `details`, it currently stamps EVERY event `status="rejected"`, and `process_batch_results` bumps `retry_count` on every innocent (only `rejected` mutates retry). It must NOT mark innocents `rejected`/retry-bumped — treat the no-adjudication case as transient (mirroring the sibling 403/5xx branch, which already passes `transient=True`). **Leave the per-event-`details` path (`:923-966`) unchanged — that IS server-adjudicated per-event rejection, not poison.** Fix within the legacy `dict`/`BatchEventResult` model; do NOT import the receiver's bisect (different bounded context). Focused test drives the live `batch_sync`/`_parse_error_response` 400-no-details path. **NB (post-tasks squad, paula/verified): the originally-named `_record_all_events_failed:475-499` is DORMANT — all seven live callers pass `transient=True`, so fixing it is a no-op; the live poison is `_parse_error_response`.** | US3 | High | Open |
| FR-006 | **Close #2755 via a shared MECHANISM, not a god-authority.** Extract ONE pure, element-generic primitive — `split_in_half(events) -> (left, right)` + `create_aware_midpoint(...)` — that the poison-bisect adapter and the legacy `_shrink_events_for_retry` (drop-the-rest policy) both consume; each caller keeps its own **policy**. Explicitly **EXCLUDE `sync/cli/commands/sync.py::_run_dispatch_batches`** (halves a re-selection *limit*, not a sequence — a stated non-goal). Reject a `BatchSplitter(mode=…)` object. | US3 | Medium | Open |
| FR-007 | CLI transition-contract test pinning `in_progress → planned` (reason-only) and the review-rejection edges (review_ref-only) as **force-free** legal per `wp_state.py`; documents SaaS#509 as the server-side alignment. The CLI must NOT emit force on these edges. | US4 | Medium | Open |
| FR-008 | Delivery-completeness measured as a **ledger residual-set equality after a full drain**: stand up a drain harness (`deliver()` → record results into the `SqliteDeliveryLedger` → `select_undelivered`), seed a poison-containing backlog, and assert `set(select_undelivered(...)) == {culprit_id}` (every innocent has a terminal-success row) AND a re-drain does NOT re-select the innocents (no re-poison). No "due to poisoning" attribution (un-measurable). | US1 | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Red-first + no regression | `tests/delivery/test_poison_batch_2736.py` (merged red-first) goes GREEN; the full `tests/delivery/` + `tests/sync/` suites stay green; `sync now` happy path (no poison) is behaviorally unchanged. | Reliability | High | Open |
| NFR-002 | Bounded bisection | Pinned by assertions on the poster's ordered POST log: single-culprit fixture asserts `len(posted_batches) <= 2*ceil(log2(N)) + 1`; all-invalid fixture asserts `<= 2*N - 1` AND that no singleton batch is ever re-split (termination — no size-1 POST appears twice). | Performance | High | Open |
| NFR-003 | Idempotency | Across a full `deliver()`, the multiset of accepted (`success`) `event_id`s has NO duplicates (no accepted half is re-POSTed); only the failed half re-POSTs; a cross-pass/crash re-post returns `duplicate`. Asserted, not narrated. | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | CLI repo only | This mission edits only `spec-kitty` (CLI). All SaaS-side changes (server transition matrix, anomaly reducer/backfill) are cross-repo follow-ups filed on `spec-kitty-saas` (#509, #510) with the decisions recorded — NOT open TBDs. | Technical | High | Open |
| C-002 | No server contract change | The server's strict all-or-nothing 400 is a deliberate boundary; #2736 is solved CLI-side (non-destructive FIFO drain + selective commit). Do NOT change the server 400 contract for this mission. | Technical | High | Open |
| C-003 | No force papering | The CLI must NOT emit `force=true` on backward review-rejection edges to satisfy the server (corrupts provenance / stamps a false guard-bypass override). CLI FSM is authoritative. | Technical | High | Open |
| C-004 | Terminology / no legacy terms | `Mission` not `feature`; keep `status commit` etc. per the Terminology Canon. | Technical | Medium | Open |

### Key Entities *(include if feature involves data)*

- **Whole-batch 400 response** — server verdict with a top-level `error` and (for the poison case) no
  per-event `details`; the input to `_map_400`.
- **Batch-split primitive** — the single shared pure module at `core/batch_partition.py` (neutral leaf, NOT `delivery/` — avoids a `sync → delivery` cycle): `split_in_half(events)` (plain keep-left cut — the genuinely de-duplicated / #2755-relevant surface, consumed by the bisect AND the legacy `_shrink_events_for_retry`) + `create_aware_midpoint(events, key_of)` (create-aware cut — single consumer today: the bisect).
- **DeliveryResult** — one per input event; `success` | `rejected` (retryable, non-terminal) | `duplicate`.
- **Create-aware split boundary** — the mid-index snap that keeps a `wp_id`'s create+status un-splittable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

**P0 release gate (SC-001..SC-003, SC-006) — the mission ships when these hold, independent of the SSOT retrofit:**

- **SC-001**: `tests/delivery/test_poison_batch_2736.py` is GREEN — a mixed poison batch delivers all
  innocents (`success`) and rejects only the culprit with its own reason (RED on the mission base). The
  test asserts (via the poster's POST log) the culprit is isolated to a **final singleton** POST.
- **SC-002**: Delivery-completeness as a **ledger residual-set equality** — after a full drain of a
  poison-containing backlog, `set(select_undelivered(...)) == {culprit_id}` and a re-drain does NOT
  re-select the innocents (no re-poison). (No un-measurable "due to poisoning" attribution.)
- **SC-003**: Ordering invariant PINNED — the straddle fixture (create/status non-adjacent, opposite
  sides of the naive midpoint, culprit in the create half) asserts `receipt_index(create) <
  receipt_index(status)`; a "same-half" assertion is rejected. Zero new inversions.
- **SC-006**: NFR-001 — `sync now` happy path behaviour-unchanged; `tests/delivery/` + `tests/sync/`
  green; bounded bisection (NFR-002 POST-count + termination assertions) + idempotency (NFR-003
  no-duplicate-accepted) held.

**Off the P0 gate (deferrable to a follow-up without holding the release):**

- **SC-004** *(WP05 outcome — NOT a P0-ship criterion)*: **#2755 closed** — one pure `split_in_half` +
  `create_aware_midpoint` primitive consumed by the poison-bisect adapter AND `_shrink_events_for_retry`
  (each keeping its policy). Guard = **behavioral delegation** (spy the primitive, assert each real
  consumer calls it) **+ an AST guard** that no other `src/` module contains a `//2` events-midpoint
  outside that primitive — NOT a source-count. `_run_dispatch_batches` is an explicit non-goal.
- **SC-005**: The CLI transition-contract test (FR-007) pins the force-free backward edges; SaaS#509 +
  SaaS#510 are filed (cc @LynnColeArt, cross-linked #2736) with the CLI-authoritative + risk decisions.
- **SC-007** *(WP04)*: the **live** `batch.py` whole-batch-400 disposition (`_parse_error_response`
  no-`details` branch) no longer marks innocents `rejected`/retry-bumped (in-context fix, FR-005); the
  per-event-`details` server-adjudicated path is unchanged.

## Out of Scope (genuinely cross-repo — tracked follow-ups)

- **SaaS transition-matrix alignment** (accept `in_progress → planned` un-forced) → **spec-kitty-saas#509**.
- **SaaS `wp_status_event_without_create` reducer semantics + accrued ~487 orphan backfill** →
  **spec-kitty-saas#510** (settle-vs-recompute treated as a risk; post-deploy metric measurement).
- Everything editable in this CLI repo is **folded in** (bisection, live offline-queue fix, #2755 de-dup as a
  shared mechanism, CLI contract test). The deferral boundary equals the repo boundary — nothing in-repo
  is deferred (planner-priti confirmed the fold is at its correct maximum).

## Sequencing (P0 ships independently of the SSOT retrofit)

Critical path = **the pure primitive + the bisection**, which alone turn `test_poison_batch_2736.py`
green and deliver the innocents (the release-blocking obligation). The #2755 SSOT retrofit (SC-004) is
**off the P0 gate** — a stuck refactor must not hold the release-blocker. Finalized WP shape (from
`/spec-kitty.tasks`; the seam-extraction FR-001 merged into WP02 with the bisection — same `receivers.py`):

- **WP01** — the pure shared primitive `split_in_half` + `create_aware_midpoint` at `core/batch_partition.py`
  (FR-003 mechanism, FR-006 mechanism). *P0 foundation.*
- **WP02 (MVP)** — `_attempt_batch_send` seam (FR-001) + recursive bisection (FR-002/003 sequential/004/008;
  US1+US2) + acceptance infra, consuming WP01 → repro GREEN + straddle-order + ledger-residual +
  bounded/idempotent tests. *Release-blocker.*
- **WP03** — CLI FSM force-free contract test (FR-007; independent). *Parallelizable, off the P0 gate.*
- **WP04** — offline-queue **LIVE** disposition fix `_parse_error_response` no-details branch (FR-005;
  post-tasks squad re-target — the originally-named `_record_all_events_failed` is dormant). *No dep, off the
  P0 gate.*
- **WP05** — SSOT retrofit: rewire `_shrink_events_for_retry` onto the plain `split_in_half`; behavioral+AST
  guard; **closes #2755** (SC-004). *Last, release-optional.*

## Post-Spec Squad Findings (folded) *(audit trail)*

Three lenses (reviewer-renata, paula-patterns, planner-priti) — all **SAFE-WITH-CHANGES**, all folded.
The P0 delivery fix (US1/US2, FR-001–004/008) was clean as first written; the changes tightened the
#2755 fold + the non-fakeability of the correctness ACs.

- **[HIGH, paula] #2755 was a false unification.** The "four split sites" span two bounded contexts +
  `_run_dispatch_batches`'s limit-halving. Reworded FR-006/US3/SC-004 to a shared *mechanism*
  (`split_in_half` + `create_aware_midpoint`) + per-caller *policy*; excluded `_run_dispatch_batches`;
  the create-aware cut moved INTO the primitive so every splitter inherits it.
- **[HIGH, renata] ordering AC fakeable.** The repro's poster records `frozenset` (order-lossy) and there
  was no straddle fixture + an `OR` escape. FR-003/US2/SC-003 now pin a create/status-straddle fixture
  (culprit in the create half) + an ordered receipt log asserting `receipt_index(create) < receipt_index(status)`;
  both dimensions required (no OR).
- **[HIGH, renata] #2755 guard near-vacuous** (the shared surface is one-line index math) + "byte-sizing"
  is not a distinct site (it's already `_shrink_events_for_retry`). SC-004 guard is now behavioral
  delegation + an AST check against stray `//2` midpoints; consumer list pruned to real sites.
- **[MED, renata] delivery-completeness hand-wave.** `deliver()` doesn't touch the ledger + "due to
  poisoning" is un-measurable. FR-008/SC-002 re-pinned as a ledger residual-set equality after a full
  drain (needs a drain harness — WP03).
- **[MED, renata] NFR-002/003 narrated.** Now pinned with POST-count + termination + no-duplicate-accepted assertions.
- **[HIGH-coupling, priti] the P0 gate was welded to the P2 refactor.** SC-004 decoupled from the P0
  release gate; WP sequencing puts the #2755 retrofit last + release-optional so the P0 ships on the
  primitive + bisection alone. (This audit trail predates `/spec-kitty.tasks`; the final numbering is
  WP01 primitive → WP02 P0 bisection, WP03 FSM contract, WP04 live queue fix, WP05 = the #2755 retrofit.)
  **Tracker:** #2755 wired as *superseded-by #2736, closes when the retrofit (WP05) lands* (not `blocked_by`).
- **Concessions (all three):** the red-first anchor is honestly RED for the product reason; FR-004
  matches the test (culprit correctly rejected, non-terminal); the FSM force-free contract (FR-007/C-003)
  is code-true; the fold is at its correct maximum (deferral boundary = repo boundary).
