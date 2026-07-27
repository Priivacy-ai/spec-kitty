# Pre-spec research — #2736 batch-400 poison isolation (4-lens squad)

Four profile-loaded lenses (debugger-debbie, architect-alphonso, planner-priti, researcher-robbie),
read-only, code-verified. Strong convergence. Operator (@stijn-dejongh) scope decisions folded.

## Root cause (debbie + alphonso, code-verified)

- **Fan-out site (live path):** `src/specify_cli/delivery/receivers.py:361-378` `_map_400`, fan-out at **line 368**
  — a whole-batch 400 with a top-level `error` and no per-event `details` marks **every** event `REJECTED`
  with the batch error. `_HttpReceiver._post_batch` (`receivers.py:477-498`) does ONE POST, no bisection.
  The red-first repro `tests/delivery/test_poison_batch_2736.py` drives `ExternalReceiver.deliver` — so the
  fix lives in the receiver `deliver()`/`_post_batch` seam.
- **Permanent-poison mechanism:** `rejected` is **non-terminal** in the ledger
  (`src/specify_cli/delivery/ledger.py:60-68` `select_undelivered` excludes only terminal-success +
  `terminal_failed`). The invalid event stays selectable forever → every future `sync now` re-forms a batch
  with it → 400s again → innocents can never deliver. (`sync.py:781-829` `skip`-loop is a head-of-line
  palliative only; it does not isolate the culprit.)
- **Dormant parallel mask:** `src/specify_cli/sync/batch.py:475-499` `_record_all_events_failed` carries the
  SAME whole-batch fan-out on the legacy OfflineQueue path (not the live `sync now` surface). **Operator
  decision: FOLD a thin fix + focused test** (defense-in-depth).

## Fix seam (alphonso)

- **CLI-side recursive bisection** on a whole-batch 400 (multi-event, no per-event `details`): split →
  re-POST **both** halves → recurse to singletons. NOT #2735's shrink-and-drop (413 keeps the first half,
  drops the rest — for 400 the dropped half may hold the culprit OR the innocents). Reuse the halving
  primitive; not the shrink-loop's drop semantics.
- **Prerequisite refactor (load-bearing):** the POST+dispatch (200/401/400/else) is inlined ~3× with no
  single send helper. Extract one `_attempt_batch_send(events) -> (status, body)` and recurse the bisect on
  it. `deliver()` accumulates results across sub-POSTs and returns one result per input event.
- **#2755 de-dup (operator: FOLD):** the bisect adds a 3rd batch-splitting site (413-shrink, byte-sizing,
  poison-bisect). Extract ONE shared split/halving primitive all three use.
- **No server change for #2736.** Non-destructive FIFO drain (`queue.py:1570-1593`) + selective commit means
  a 200 half delivers and only the culprit singleton is dispositioned — CLI-side bisect fully solves delivery.

## Ordering invariant (robbie + alphonso — load-bearing correctness)

WP-create must reach the server no later than its WP-status (else the SaaS reducer emits
`wp_status_event_without_create`). Bisection must preserve create-before-status in **server-receipt order**:
- **(a) Sequential left-before-right depth-first recursion** — fully resolve the left half before sending the
  right half. Never parallel, never reorder.
- **(b) Create-aware split boundary** — snap the mid index so a given `wp_id`'s create + status never land in
  different halves (group contiguous same-`wp_id` runs). Makes the pair un-splittable.

## Question-2: `in_progress → planned` force divergence — OPERATOR DECISION: CLI FSM AUTHORITATIVE

- The canonical CLI FSM (`src/specify_cli/status/wp_state.py:383-386`) allows `in_progress → planned` (and the
  review-rejection edges) **force-free**, guarded by reason/ReviewResult only. `force` is reserved for terminal
  exits / guard bypass (and stamps an audit override). The CLI is CORRECT; the SERVER matrix is stricter.
- **Fold (CLI-side):** a contract/regression test pinning the canonical FSM's force-free backward edges — the
  CLI must NOT emit `force` (that corrupts provenance).
- **Defer (cross-repo):** the SaaS transition-matrix alignment → filed **spec-kitty-saas#509** (CLI-authoritative
  decision recorded, cc @LynnColeArt, cross-links #2736). Does NOT gate #2736 (the red-first test asserts the
  event is *correctly rejected*).

## Projection anomaly `wp_status_event_without_create` — OPERATOR DECISION: TREAT AS RISK

- The reducer lives in `spec-kitty-saas` (NOT this repo) — the live metric cannot be a CLI unit gate.
- **Fold (CLI-side):** a delivery-completeness proxy AC ("0 innocent creates left undelivered due to poisoning
  after a full drain") + the FIFO-order-preservation invariant above. Post-deploy: capture the metric pre/post.
- **Defer (cross-repo):** reducer semantics (current-state vs append-only → settles vs needs-recompute) + the
  accrued ~487 backfill → filed **spec-kitty-saas#510** (cc @LynnColeArt, cross-links #2736). The mission's
  success statement reads "delivers the stranded creates; anomaly settle vs recompute is tracked in SaaS#510."

## Scope (priti + operator fold-in maximization)

| Item | Verdict |
|---|---|
| Batch-400 bisection in `receivers._post_batch` (+ single-send helper) | **FOLD — MVP** |
| Create-aware ordering invariant (sequential + un-splittable pairs) | **FOLD** |
| Dormant `sync/batch.py` fan-out fix + test | **FOLD** (operator) |
| #2755 shared batch-split primitive de-dup | **FOLD** (operator) |
| Question-2 CLI contract test (FSM force-free authoritative) | **FOLD** |
| Delivery-completeness + FIFO-order ACs (`test_poison_batch_2736.py` green) | **FOLD** |
| SaaS transition-matrix alignment | **DEFER → spec-kitty-saas#509** |
| SaaS anomaly reducer semantics + orphan backfill | **DEFER → spec-kitty-saas#510** |

Tracker: #2736 hygiene correct (P0, Bug, parent #1800, unblocked — #2734 closed / #2735 merged).
Cross-note #2755 (poison-bisect becomes the de-dup driver — subsumed, not just noted).
