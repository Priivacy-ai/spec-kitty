# Design Decisions

> Capture the rationale that would otherwise evaporate.

Mission: `sync-batch-400-poison-isolation-01KXW08B` · #2736.

## Entries (append dated)

- 2026-07-19 — **Decision: fix CLI-side (bisection), not the server 400 contract.** Alternatives:
  per-event partial-accept server contract; server per-event `details` granularity. Rationale: the strict
  all-or-nothing 400 is a deliberate boundary (operator's call); non-destructive FIFO drain + selective
  commit mean the CLI-side bisect fully delivers innocents without a server change. A granular server would
  only save round-trips on a rare poison path.

- 2026-07-19 — **Decision: question-2 (`in_progress→planned` force) — CLI FSM is authoritative.**
  Alternatives: server-authoritative (CLI emits force). Rationale: the canonical `wp_state.py` FSM allows
  the backward review-rejection edge force-free (reason-only); forcing it would falsely stamp a guard-bypass
  audit override + demand a synthetic reason, corrupting provenance. The server matrix is the drift → aligns
  server-side (spec-kitty-saas#509). The red-first test asserts the event *correctly rejected*, so this does
  not gate the P0.

- 2026-07-19 — **Decision: #2755 fold = one shared MECHANISM, not a god-authority.** Alternatives: a
  `BatchSplitter(mode=…)` object owning all split policies; leave the bisect as a 3rd independent site.
  Rationale (paula): the split *policies* genuinely differ (413 keep-left-drop-rest vs 400 send-both-recurse
  vs a limit-halving orchestration that isn't a sequence split at all). A mode-object recreates the
  split-brain inside one class. The genuinely-shared SSOT is the pure `split_in_half` +
  `create_aware_midpoint` primitive; `_run_dispatch_batches` is excluded (halves a re-selection *limit*).

- 2026-07-19 — **Decision: the create-aware split boundary lives in the shared primitive, not the bisect.**
  Alternatives: implement create-aware cut only in the poison-bisect. Rationale (paula whack-a-field): if it
  lives only in the bisect, `_shrink_events_for_retry` and any future split site silently reintroduce the
  create/status inversion. Putting it in the primitive means every splitter inherits the un-splittable-pair
  guarantee by construction.

- 2026-07-19 — **Decision: the isolated culprit stays retryable (`rejected`, non-terminal), NOT
  force-parked.** Alternatives: park the singleton as `terminal_failed` to stop the re-post churn.
  Rationale: parking would prevent the event from EVER delivering after the SaaS matrix aligns (#509);
  bisection already isolates it so it never re-poisons innocents. The harmless singleton re-post per drain
  is accepted; the red-first test pins `rejected`.

- 2026-07-19 — **Decision: measure delivery-completeness as a ledger residual-set equality, not a
  "0-undelivered-due-to-poisoning" proxy.** Alternatives: assert the live SaaS `wp_status_event_without_create`
  metric (un-gate-able from the CLI repo). Rationale (renata): "due to poisoning" attribution isn't
  CLI-measurable (can't distinguish from `project_uuid`-missing stranding). A `select_undelivered == {culprit}`
  + re-drain no-reselection assertion is concrete and pins the non-terminal-rejected re-poison mechanism.
  The SaaS metric semantics (settle vs recompute) is a risk tracked in spec-kitty-saas#510.

- 2026-07-19 — **Decision: P0 release gate decoupled from the #2755 SSOT retrofit.** Alternatives: gate the
  release on SC-004 (#2755 closed). Rationale (priti): the P0 (deliver innocents) is release-blocking; the
  SSOT retrofit is reliability tech-debt with the highest regression risk (touches merged #2735 code). WP
  sequencing ships the P0 on WP01+WP02→WP03; WP05b (retrofit) is last and release-optional so a stuck
  refactor can't hold the release-blocker hostage.
- 2026-07-19 (post-plan squad) — **Decision: the shared primitive lives at `core/batch_partition.py`, NOT
  `delivery/partition.py`.** Alternatives: keep it in `delivery/` (its first consumer). Rationale (alphonso,
  independently confirmed by pedro): the #2755 retrofit makes `sync/batch.py` import the primitive; if it
  lived in `delivery/`, that's a **runtime `sync → delivery` edge** that inverts the only existing cross-edge
  (`delivery → sync`, today TYPE_CHECKING-only) into a `delivery ⇄ sync` cycle — and the layer-rules gate
  would NOT catch it (both packages sit inside the single `specify_cli` layer), so it's silent debt.
  `core/` is the neutral leaf both already import downward (`core.time_utils`), giving `delivery → core` +
  `sync → core` with no cycle. Correct-by-construction, not by discipline (DIR-043/044).

- 2026-07-19 (post-plan squad) — **Decision: `split_in_half` (plain keep-left) and `create_aware_midpoint`
  stay TWO functions; the 413 shrink consumes the plain one.** Alternatives: bake create-aware into the one
  shared cut. Rationale (alphonso + pedro): `_shrink_events_for_retry` is keep-left-drop-rest byte-sizing —
  it has no ordering concern and must NOT inherit create-aware snapping (wrong policy). The genuinely-shared
  / de-duplicated surface is `split_in_half`'s `max(1, len//2)` midpoint; `create_aware_midpoint` has a
  single consumer (the bisect). SC-004's single-authority guard is therefore scoped to `split_in_half`.

- 2026-07-19 (post-plan squad) — **Decision: the create-before-status ORDERING guarantee is the bisect
  adapter's sequential recursion, not the primitive.** Alternatives: treat `create_aware_midpoint` as the
  ordering fix. Rationale (alphonso + renata): a batch-*spanning* create/status pair cannot be kept together
  by ANY midpoint; the midpoint only prevents *adjacent*-pair straddle. The `receipt_index(create) <
  receipt_index(status)` invariant is enforced by delivering left-before-right sequentially. The primitive is
  ordering-agnostic; the spec/plan wording was corrected to stop attributing ordering to it.

- 2026-07-19 (post-plan squad, pedro) — **Decision: the drain harness records `deliver()` results into the
  ledger via `record_result(..., result=r.outcome)` — the `DeliveryOutcome` enum, never the `DeliveryResult`
  object** (which stringifies to a dataclass repr → `ValueError` in `_coerce_result_token`). No WP07
  dispatcher is needed; the harness stands up in `tests/delivery/` directly. Captured because it is the
  single highest-risk "looks-done-but-throws" trap for the SC-002 acceptance.

- 2026-07-19 (post-plan squad, pedro) — **Decision: the `_attempt_batch_send` seam is typed
  `(int | None, Mapping | None)`; a `None` status (transport failure) maps to all-transient and is NEVER
  recursed/split.** Rationale: splitting a `requests.RequestException` would multiply transient failures
  across the recursion; the transport branch has no HTTP status to represent as a plain `int`.
- 2026-07-19 (post-tasks squad, paula/HIGH — VERIFIED) — **Decision: FR-005 re-targets from the DORMANT
  `_record_all_events_failed:475-499` to the LIVE `_parse_error_response:967-985` no-details branch.**
  Alternatives: keep the original target (ship a no-op) or defer. Rationale: verified from source that all
  seven `_record_all_events_failed` callers pass `transient=True` (its `rejected` branch is dead), while the
  live `batch_sync` 400 handler (`:1188`, live via `background.py:455`) routes no-details whole-batch 400s
  through `_parse_error_response`'s else-branch, which stamps EVERY event `rejected` → `process_batch_results`
  bumps `retry_count` on every innocent (only `rejected` mutates retry). Our original scope would have shipped
  a dormant no-op for a live-poison requirement. The fix: treat no-adjudication 400 as transient (mirror the
  sibling 403/5xx branch); leave the per-event `details` path (server-adjudicated) untouched. **This is a plan
  defect the post-tasks squad caught before implement.**

- 2026-07-19 (post-tasks squad, priti+renata converge) — **Decision: split WP04 → WP04 (live P1 fix, no
  dep, group 0) + WP05 (#2755 retrofit, dep WP01+WP04).** Rationale: (priti) bundling welded a now-HIGH live
  fix behind an unnecessary WP01 dependency and a highest-risk-P2; the live fix consumes no primitive, so it
  ships fastest standalone. (renata) the escape hatch was vacuous — `split_in_half(events)[0]` is textually
  identical to the inline `events[:max(1,len//2)]`, so the retrofit is behavior-preserving and any #2735 red
  is a mechanical bug, not "friction." WP05 owns only the guard test; its one-line rewire is a declared
  out-of-map edit sequenced after WP04 (avoids the same-file ownership clash that forced the original merge).

- 2026-07-19 (post-tasks squad) — **Decision: T017 behavioral-delegation spy is the LOAD-BEARING #2755
  guard; the AST `//2` guard (T018) is belt-and-suspenders and MUST allowlist `core/batch_partition.py` +
  `doc_analysis/gap_analysis.py:392`.** Rationale (paula+debbie, converge): an AST `//2` walk is inherently
  too-broad (false-positives on the live unrelated `len(project_areas)//2` in gap_analysis) or too-narrow
  (misses aliased spellings), so it can't robustly prove single-authority alone; behavioral delegation can.

- 2026-07-19 (post-tasks squad, renata) — **Decision: the `create_aware_midpoint` primitive is pure
  key-adjacency, NOT create/status role-aware.** Deciding "which straddling event is the create" would force
  the primitive to sniff event roles/shape, contradicting the shape-blind `key_of`-only contract. Same-key
  adjacency + nudge is sufficient; ordering stays in WP02's sequential recursion.
- <!-- append implement decisions here -->
