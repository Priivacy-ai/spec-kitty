# Research (Phase 0) — Doctrine Delivery Activation Fast-Follow

Full evidence-dense grounding (file:line anchors, per-scout risks) lives in
[pre-planning-ledger.md](./pre-planning-ledger.md). This file records the Phase-0 **decisions**
that grounding produced.

## Decisions

| # | Decision | Rationale | Alternatives rejected |
|---|----------|-----------|-----------------------|
| D1 | Surface `when` in the **charter/consumer layer** (reuse `edge_to_reference`/`STATED_DEFAULT_WHEN`), keeping `doctrine.drg.query.walk_edges` node-level. | The node walk discards the edge; leaking edge objects into the doctrine query layer would breach the layer boundary. `edge_to_reference` already models `{id,relation,when,reason}`. | Mutate `walk_edges` to return edges (cross-layer leak); a second parallel walk (C-001 forbids). |
| D2 | The widened suggests-reach delivers via the existing `context.py` NodeKind delivery table, links-not-bodies, reusing the requires-closure "fetch + when-doing" cadence. | Following `suggests` reaches non-procedure kinds; NFR-003 forbids eager body dumps; the cadence already exists (landing pass). | Deliver all reached kinds as full bodies (context bloat); restrict to procedures (under-delivers A/B/C/E). |
| D3 | Backfill a grounded `when` on the Family A architect→DDD edges (from their existing `reason`). | Those edges carry no `when`; a bare `STATED_DEFAULT_WHEN` render is lower-quality than an authored condition. **Surface at post-plan check-in.** | Ship Family A with default `when` (acceptable fallback, lower quality); leave Family A undelivered. |
| D4 | Family C is TWO complementary vectors: techniques via IC-01 suggests-walk; template artefacts via IC-03 `template:instantiates`. | The wiring table's Family C assessment names `template:instantiates` from `action:documentation/design` as the template path; the walk delivers the technique doctrine. | Assume the walk alone discharges Family C (architect-risk-7: it doesn't). |
| D5 | Each companion edge (IC-03/IC-04) must land in a relation an **active channel walks**; the WP's ATDD acceptance is "artefact delivered", which fails on an authored-but-inert edge. | Authoring an unwalked edge repeats the exact bug this mission fixes. Self-correcting via the acceptance test. | Author edges + trust they deliver (inert-edge regression). |
| D6 | #3075 root-fix: route ALL THREE document emitters (incl. `pack_assembler`) through `graph_document_to_dict`, register each, add a non-vacuous discovery gate; fold Protocol typing. | Two patched sites leave `pack_assembler` (worse — bypasses the mapping funnel) silently non-conforming; the registry is fail-open by construction. | Patch only the two named sites (leaves the third + future regressions). |
| D7 | #3062: catch `DRGGraphSchemaError` at both pack_validator sites → `ValidationIssue`; fix asset `_source_paths` via a base `_post_validate` success-path hook, fixing the AgentProfileRepository twin in the same WP. | A base-boundary hook fixes both repos without whack-a-field; the error deliberately isn't a `DRGLoadError` subclass, so it must be caught explicitly. | Patch AssetRepository only (leaves the twin); make it a DRGLoadError subclass (breaks fail-closed intent). |
| D8 | #2532 is a deliberate SLICE — extract reference-pointer + delivery-table helpers only; `Refs`, not `Closes`. | The brief scopes FR-012 to specific helpers "for consistency"; extracting them won't de-god the 3528-line module. | `Closes #2532` (false-closes a still-god module). |
| D9 | Ordering: IC-09 first (de-flake), IC-01 core, IC-03/IC-04 (+Family-A `when`) before IC-05 terminal reconciliation, IC-08 after IC-01, IC-06/IC-07 fully parallel. | NFR-002 (no stale goldens) forces reconciliation last; the fixture false-red noises every ATDD cycle; IC-08 extracts IC-01's final cadence. | Reconcile early (goldens re-stale); extract before IC-01 (nothing to extract yet). |

## Open sub-questions — RESOLVED in plan phase (post-plan squad, D10–D19)

- **OQ-1 → RESOLVED (D13):** `resolve_context` walks scope/requires/suggests/vocabulary — NOT
  `instantiates` (query.py:139-160, verified). The C4 zoom-in tactic already `references:` the mermaid
  templates, so FR-007 delivery rides IC-01's suggests-walk reaching that tactic; the `template:instantiates`
  edge is topology completion. **IC-03 stays schema-tier; no core query.py edit.** ATDD = templates reach
  the architect via the delivered C4 tactic's references.
- **OQ-2 → RESOLVED (D14):** the canonical relation is the EXISTING `Relation.REJECTS` (models.py:123),
  direction **tactic → anti_pattern** (matching 8 existing edges + `validator.py:171`). anti_patterns are
  never delivered by design → validation-tier, no inert-edge problem. Extends the existing 6-node corpus;
  coordinate with #2847 (no new shape to migrate).
- **OQ-3 → decide in IC-01 (D2):** widen the NodeKind delivery table beyond procedures for the
  profile-channel; links-not-bodies (NFR-003). Unchanged.

## Post-plan squad decisions (D10–D19) — see pre-planning-ledger "POST-PLAN SQUAD" section

- **D10** assert on `profile_channel_reachable` (profile channel), NEVER `resolve_context`.
- **D11** surface `when` by reusing `link_references(roots=profile_seeds, …)`; no re-walk.
- **D12** SPLIT IC-06 → IC-06a (parallel registry/gate) + IC-06b (Protocol typing, after IC-01+IC-09).
- **D13/D14** OQ-1/OQ-2 resolved above.
- **D15** graph-count/histogram goldens owned by the AUTHORING WP (IC-03/IC-04); IC-05 owns only
  reachability goldens.
- **D16** IC-05 also owns `_ACTION_UNREACHABLE_D2`.
- **D17** forward-API retirement pre-classification (below).
- **D18** NFR-002 pins are review-gated, not CI-gated.
- **D19** baseline deferred set = **60** (the "50"/"39" wiring-table figures are stale; reconcile at WP04).

### Forward-API retirement pre-classification (D17, provisional — confirm per-symbol at impl)

| Symbol | Def module | Disposition |
|--------|-----------|-------------|
| `agent_profile_seed_urns` | reachability.py:58 | LIKELY-WIRED (compute profile seeds in delivery projection) |
| `PROFILE_CHANNEL_RELATIONS` | reachability.py:48 | MAYBE-WIRED (if consumer references it cross-file) |
| `partition_delivery` | progressive_disclosure.py:93 | MAYBE-WIRED (if delivery cadence uses it cross-file) |
| `action_channel_reachable` | reachability.py:69 | STAYS (action channel; no src consumer built) |
| `action_seed_urns` | reachability.py:53 | STAYS (action channel) |
| `charter_activated_urns` | pack_context.py:496 | STAYS (charter-activation reachability — different concern) |
| `normalize_activation_identifier` | pack_context.py:362 | STAYS (activation concern) |
| `partition_activated_unreachable` | pack_context.py:426 | STAYS (activation concern) |
| `ActivationReachabilityPartition` | pack_context.py:389 | STAYS (activation concern) |

`_symbol_has_caller` counts cross-file `src/` importers only (tests NOT counted). Retirement ≈ **2–3**, not
9; the rest stay allowlisted-with-note (manufacturing a fake importer is itself the gate's named anti-pattern).

## Out of scope (C-006, separate missions)

Value-based edge properties (B1 `impacts`/`is_symmetric`) + the DDD↔documentation mutual-reinforcement
edge depending on them; #3064 empty-charter/`default-charter.yml` asset (DIRECTIVE_044 always-on).
Adjacent-but-separate: #3056 (agent fetch-instruction + 118 `when`-edge backfill), #2847 (anti-pattern
corpus promotion) — `Refs` only, keep IC-04 bounded.
