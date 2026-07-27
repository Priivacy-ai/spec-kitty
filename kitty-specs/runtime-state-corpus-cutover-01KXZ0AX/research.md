# Phase 0 Research: Runtime-State Corpus Cutover

All spec requirements are grounded in the post-#2817 tree (verified by the pre-planning brownfield
squad — see spec "Pre-planning verification note"). No `[NEEDS CLARIFICATION]` markers remain; the
decisions below are engineering choices resolved from the spec + charter, recorded here as the
authoritative design ground for `/spec-kitty.tasks`.

## D-01 — One shared cutover orchestration helper (not two callers re-implementing verify-then-flip)

- **Decision**: Add `migration/runtime_state_cutover.py` — a single helper implementing
  `backfill → fail-closed verify → atomic per-mission status_phase flip`. Both the operator CLI
  (IC-01) and the upgrade migration (IC-02) call it.
- **Rationale**: The fail-closed atomicity (NFR-001) is the load-bearing invariant; it must live in
  exactly one place. Two callers re-deriving "seed, then verify, then flip only if ok" is precisely the
  logical-duplication trap (one operation across N sites → one canonical seam). The helper wraps the
  existing library's `run_backfill_and_verify` and adds the flip.
- **Alternatives rejected**: (a) put the flip logic in the CLI and have the migration shell out to the
  CLI — brittle, couples migration to CLI parsing; (b) duplicate verify-then-flip in each caller —
  drifts, and a bug fixed in one is missed in the other.

## D-02 — status_phase is the sole-writer, post-verify flip; it stays a LIVE runtime gate for the kept lane mirror (corrected post-planning)

- **Decision**: The cutover helper is the **only** writer of `meta.json` `status_phase`, and writes it
  **only after** a mission's verify passes (FR-003). IC-03 deletes the phase-1 **reader-authority**
  predicate `_phase1_snapshot_authority_active`, so *runtime-slot* readers become unconditional (always
  the snapshot).
- **CORRECTION (post-planning architect review)**: `status_phase` does **not** become inert after IC-03.
  The kept `_legacy_lane_mirror_enabled` (`emit.py:413-424`, retained by C-004) **still reads
  `status_phase`** via `_read_status_phase`. So:
  - FR-003's atomic verify-then-flip is **load-bearing, not vestigial** — it now gates the *lane mirror*
    rather than the deleted runtime-slot predicate. (This answers the brief's status_phase question: the
    flip still matters.)
  - **Side effect of the flip**: today every mission is `status_phase=0` → lane mirror **OFF**; flipping
    a mission to `status_phase=1` **activates** the lane mirror for it. IC-03 must carry a regression
    proving lane behaviour is unchanged by the activation. If activation proves problematic, decoupling
    the lane mirror from `status_phase` is a **follow-up** (C-004 keeps it out of scope here).
  - **IC-06 must NOT retire the `status_phase` field** — dropping it would silently disable the lane
    mirror corpus-wide. `status_phase` is explicitly out of IC-06's bounds.
- **Correctness for existing deployments** rests on the **upgrade migration running the backfill (and
  flipping `status_phase`) before the upgraded code serves reads** (IC-02) — plus **IC-01b** backfilling
  *this* repo's corpus in the mission's own merge unit. `spec-kitty upgrade` installs new code and runs
  migrations within one command; the new-code-meets-un-backfilled-corpus window is *inside* that command,
  closed by the migration (precondition: no concurrent spec-kitty runtime command during `upgrade`).
- **Refuse-to-flip footgun**: because `status_phase` has no other writer, "refuse to flip a mission whose
  verify hasn't passed" is enforced by making the helper the sole writer — no hand-flip surface to abuse.
- **Idempotency source of truth**: the **backfill seeds** (deterministic content-namespaced ULIDs), not
  `status_phase`; a re-run seeds nothing because the ids exist. `status_phase` is a fast skip-hint.
- **Alternatives rejected**: drop `status_phase` entirely — breaks the lane mirror (C-004) and
  contradicts FR-003; keep the runtime-slot predicate as a live gate — contradicts C-002.

## D-03 — CLI = per-mission best-effort; upgrade migration = fail-closed abort on any failure

- **Decision**: `spec-kitty migrate backfill-runtime-state` flips each mission independently: it seeds +
  verifies + flips every mission that passes, records failures, and exits non-zero if any mission
  failed (never flips an unverified mission). The **upgrade migration** is stricter: **any** mission's
  verify failure aborts the whole migration step with an operator-actionable message (NFR-005), leaving
  no mission half-flipped.
- **Rationale**: The CLI is an operator tool — reporting per-mission results and letting the operator
  triage is more useful than all-or-nothing. The upgrade path is unattended and must not leave a
  deployment in a mixed/ambiguous state without the operator knowing, so it fails the upgrade step
  loudly. Both honour "refuse to flip unverified" (NFR-001); they differ only in blast-radius on failure.
- **"Non-partially-flipped" clarified (NFR-005)**: a mission is never left *half*-flipped (flipped
  without a passing verify). Across the corpus, each mission is independently consistent — either
  flipped-and-verified or not-flipped-and-legacy. NFR-005's guarantee is *per-mission* atomicity, not
  corpus all-or-nothing.
- **Alternatives rejected**: corpus-wide all-or-nothing transaction for the CLI — no cross-mission
  atomicity primitive exists (each mission is an independent event log), and it would block the whole
  corpus on one bad mission.

## D-04 — Upgrade migration is a new auto-discovered module, ordered after the charter folds

- **Decision**: Add `upgrade/migrations/m_<version>_runtime_state_backfill.py` self-registering via
  `@MigrationRegistry.register`; no central sequence-list edit (`auto_discover_migrations()` walks
  `m_*.py`). Choose a version-key prefix that sorts **after** the charter-fold migrations.
- **Rationale**: Matches the canonical upgrade-migration pattern (the charter.yaml fold the brief cites);
  hand-rolling a sequence entry would drift from the registry mechanism.
- **Alternatives rejected**: a manual runner hook — not the sanctioned surface.

## D-05 — Fallback deletion order: verify the event-sourced replacement exists first (merge path)

- **Decision**: Before deleting `merge/done_bookkeeping.py::_extract_done_evidence` (frontmatter
  done-evidence synthesis, FR-006b), confirm the merge done path already reads done-evidence from the
  event log for backfilled missions. The verdict fallback in `workflow_cores.py` (FR-006a) is the
  **same block** as the FR-007 review bypass reader → deleted-and-rerouted as one edit.
- **Rationale**: `done_bookkeeping` feeds the **merge** gate; deleting synthesis without an event-sourced
  replacement would break merge for any mission. C-001 order (delete fallbacks only after backfill has
  seeded the approvals as events) makes this safe, but the replacement read must be exercised by a test.
- **Alternatives rejected**: delete first and fix merge later — violates C-001 and risks a red merge gate.

## D-06 — Not a DIRECTIVE_035 bulk edit

- **Decision**: No `occurrence_map.yaml`. The 12-site flag removal is a **heterogeneous per-site
  refactor** — each call site collapses its `if predicate: … else: …` differently (some keep the
  snapshot branch, some are early-returns, `support.py` has two distinct sites). It is not a mechanical
  same-string replacement.
- **Re-verify trigger**: if, during implementation, the collapse proves mechanically uniform across
  sites, revisit and add the map. Current evidence (squad) says heterogeneous.

## D-07 — The dogfood corpus backfill is a WP with an owner (BLOCKER-fix from post-planning review)

- **Decision**: Add IC-01b — a WP that **runs** `migrate backfill-runtime-state` over **this repo's**
  `kitty-specs/` and **commits** the resulting seed events + `status_phase` flips, landing in the same
  merge unit as IC-03/IC-04, with edges `IC-01 → IC-01b → {IC-03, IC-04}`.
- **Why (the failure it prevents)**: all 299 dogfood missions are `status_phase=0` today, and under the
  flag-OFF path runtime slots are written to frontmatter **only, never emitted as events**
  (`emit.py:314-317`). The moment IC-03 makes readers unconditional on local main, every dogfood mission
  reads an **empty snapshot** → `_infer_subtasks_complete` fail-closes to `False`, ownership/review reads
  return `None`, the suite goes red. IC-01 ships the *tool*; IC-02 backfills *consumers*; **no WP
  backfilled this repo** — the exact contract-step-ownership gap the mission's own field report documents
  (`docs/plans/engineering-notes/2026-07-19-migration-contract-step-ownership-field-report.md`). The plan
  must own backfill *execution*, not just the *tool*.
- **Merge-unit atomicity**: IC-01b must land before IC-03 during WP-by-WP merge to local main, else main
  is transiently red. The dependency edges enforce it; the mission PR carries all three together.
- **Alternatives rejected**: rely on the consumer upgrade migration to cover the dogfood repo — it runs
  on `spec-kitty upgrade`, not on this mission's merge, so it does not close the in-repo window.

> **⚠️ D-08/D-09 SUPERSEDED IN PART by the 2026-07-20 operator decision** — see D-10/D-11 below. D-08's
> "escalation is a conditional follow-up" is now "SaaS delivery is in scope, via the existing structured
> actor (no shared-package change)". D-09's "keep `agent_profile`/`role` frontmatter" is reversed for the
> *resolved actual* (event-sourced); only the *authored* recommendation stays frontmatter. Kept for the
> audit trail.

## D-08 — `InnerStateChanged` stays LOCAL; escalation to `spec_kitty_events` is a conditional follow-up, not this slice

- **Decision**: Do **not** escalate `InnerStateChanged` into the shared `spec_kitty_events` package to
  close #2816. It is correctly a local off-axis annotation folded by the local reducer.
- **Evidence** (events-boundary review): the only cross-boundary event contract is the lane transition
  (`StatusEvent` → `spec_kitty_events` `StatusTransitionPayload`), already shared. `emit_inner_state_changed`
  (`emit.py:888-951`) **persists + materializes only** — no `_saas_fan_out`, no `fire_dossier_sync`
  (contrast the lane path's Step-7 SaaS fan-out / Step-8 dossier sync). `_saas_fan_out` is typed to
  `StatusEvent` (lane fields only). The dossier/sync projection (`dossier/snapshot.py`) carries artifact
  content-hashes + completeness counts — **zero WP runtime fields**. `InnerStateChanged.to_dict()`
  serializes only to the local `status.events.jsonl`; no wire form crosses the package boundary. The
  5.2.0/6.0.0 version gate is about the `Lane` **enum** (genesis lane), orthogonal to runtime annotations.
- **Conditional follow-up (out of scope; file only if/when needed)**: if a future SaaS surface must
  display live WP runtime state (e.g. "agent X, PID Y on WP03"), add a shared `WPRuntimeStateChanged`
  event type to `spec_kitty_events` + a fan-out call in `emit_inner_state_changed`. That is a product
  decision, NOT a #2816 correctness gap. Recorded in the spec's Out-of-Scope section.

## D-09 — The dashboard is a bypass reader, and the #2093 invariant is blind to it (found reviewing the dashboard path)

- **Finding**: `dashboard/scanner.py::_process_wp_file` reads runtime `agent` (:937), `assignee` (:978),
  and subtask completion (:954-965) via `read_wp_frontmatter(...).<attr>` — **typed attribute access, not
  `extract_scalar`**. The #2093 invariant's detector (`_reads_dynamic_field_via_extract_scalar`, :312)
  matches only `extract_scalar(…, "<field>")`, so it never saw this reader. Emptying the tolerated set
  without extending the detector is a **false green**.
- **Decision**: IC-04 routes the dashboard's runtime reads onto the snapshot (keeping `agent_profile`/
  `role` frontmatter-sourced — those are #2093 static authored-intent, not runtime). IC-05 **extends the
  detector** to catch runtime-field attribute reads on typed frontmatter/metadata objects, and proves it
  flags the dashboard scanner red **before** the reroute (non-vacuous).
- **Why it matters**: the dashboard is the operator's primary runtime-state view; post-cutover, reading
  stale/stripped frontmatter would show wrong `agent`/`assignee`/progress. This is exactly the
  split-brain #2093 forbids — and the class the invariant must actually cover to be meaningful.

## D-10 — Resolved runtime IDENTITY (role/profile/model) is event-sourced; authored intent stays frontmatter (operator decision 2026-07-20)

- **Decision**: The *actual* `role`, `agent_profile` (+version), `model`, and `provider` that take a WP
  are recorded on the event log at each **pick-up/claim/reassign** transition and folded **latest-wins**
  into the snapshot. The WP/dashboard reader reconstructs this resolved final-state from the event log;
  the *authored/recommended* assignment stays frontmatter-canonical and is shown **distinctly**.
- **Rationale (the operator's lifecycle argument)**: the actual identity **shifts** across the WP
  lifecycle — an implementer profile on model A claims it, a reviewer profile on model B picks it up, a
  model can be swapped mid-cycle. A single static frontmatter value is therefore **wrong mid-cycle**;
  only the event log's latest-actual reduction is correct. This is why a *pre-computed/pre-advised* value
  cannot be the canonical "what is running this WP".
- **Grounding (3-lens research)**: these fields are NOT event-sourced today — `WPInnerStateDelta` carries
  no `profile`/`model`/`role`; the `agent` slot holds only the bare `--agent` string; `model` is
  persisted nowhere (advisory `RoutingRecommendation` only; ADR-2026-07-19-1 deferred it as blocker B4);
  resolved profile is recorded only on the dispatch/Op path (`kitty-ops`, keyed by invocation_id, no
  WP-lane back-ref). So this is **net-new vocabulary + a resolve seam** (IC-08), not a reroute.
- **#2093 guard (C-007)**: the recorded value MUST come from `resolve_profile`/`resolved_agent()` / the
  dispatch resolution — copying the frontmatter `agent_profile` string into an event would manufacture a
  *new* split-brain (the exact anti-pattern #2093 forbids).
- **role reversal**: the #2093 ruling text lists `role` as dynamic; an interim note had kept it
  frontmatter. Ratified here (C-009 ADR) as: authored role → frontmatter; **actual** role → event-sourced.
- **Scope**: this is #2093's resolved-binding "record" slice + #2400's WP-metadata half. The full #2399
  fail-closed *enforcement* (agent cannot act without a resolved+recorded profile) stays OUT.

## D-11 — SaaS delivery rides the existing structured `actor`; no shared-package change on the preferred path

- **Decision**: Deliver the resolved binding to the SaaS consumer by enriching the **structured `actor`**
  (`{role, profile, tool, model}`) on the claim/review `StatusEvent` and its existing `_saas_fan_out`
  (`emit.py:954-1008`). `spec_kitty_events` 6.1.0 `StatusTransitionPayload.actor` is already
  `Union[str, Dict]` accepting exactly that shape → **zero shared-package change**.
- **Fallback**: if the SaaS UI needs an *off-transition* binding-change event (e.g. a mid-WP model swap
  with no lane change), add a `WPResolvedBindingChanged` shared event + a fan-out to
  `emit_inner_state_changed` (which has none today), **version-gated** exactly like the genesis-lane gate
  (`_EVENTS_SUPPORTS_… = hasattr(spec_kitty_events, "WPResolvedBindingChanged")`). This lets #2816 land the
  local event now and enable fan-out when the package ships — never block on the external release.
- **Do NOT escalate `InnerStateChanged` itself** — it is a grab-bag (shell_pid/subtasks/tracker_refs) the
  SaaS consumer does not want; the actor-on-transition or a purpose-built binding event is cleaner.
- **Sequencing (cross-repo)**: `spec_kitty_events` is external (consume via public imports only). Preferred
  path needs no release. Fallback path: local-first + version-gated fan-out (option i), never block-on-shared.

## D-12 — Dispatch→claim linkage for the resolved binding (operator decision Q1, 2026-07-20)

- **Decision**: obtain the genuine resolved model+profile from the dispatch/Op path and **thread it into
  the implement/review commands** (new `--model`/`--profile`/`--invocation-id` options or side-channel on
  `cli/commands/agent/workflow.py`), consumed at the claim seams. Operator chose full model-actual now over
  the leaner resolve-at-seam.
- **Why forced**: adversarial grounding proved the claim seam has ONLY the bare `--agent` string +
  frontmatter-coerced values (`workflow.py:918,:1368`; `resolved_agent()` derives from frontmatter,
  `wp_metadata.py:418-470`); the genuine resolution (`RoutingRecommendation.model`, `registry.resolve`)
  lives only in `invocation/executor.py:249,265`, keyed by `invocation_id`, no WP-lane back-ref. Recording
  the frontmatter value would violate C-007/INV-6.
- **Emit-shape reconciliation**: emit the binding as an **annotation** (latest-wins at BOTH claim points —
  the reducer's `policy_metadata` claim fold fires only on `planned→claimed`, `reducer.py:102`, so
  review-claim would be missed) AND enrich the transition's structured `actor` for the IC-09 fan-out. Both.
- **Historical binding correction (C-011)**: the accepted field-authority ADR forbids copying authored
  recommendations into resolved-actual events. Legacy WPs remain unresolved until a genuine
  resolver-backed pick-up; deterministic authored-derived `resolved_binding` seeds are removed by exact
  seed identity without touching live annotations.
- **Scope note**: this is a cross-layer addition (invocation + command surface + claim seams) — the
  mission's largest scope-growth. Operator-accepted ("implementation can wait; get the spec right").

## D-13 — Subtask completion fully event-sourced; markdown checkboxes removed (operator decision Q2)

- **Decision**: the snapshot `subtasks` slot is the **sole** authority; **remove** the `- [ ] T###`
  markdown checkboxes; agents use `spec-kitty agent tasks mark-status`; update the doctrine prompt
  templates to direct them there. The WP view pulls resolved status, not the incoherent checkbox proxy.
- **Grounding**: today the dashboard counts live `tasks.md` checkboxes (`scanner.py:958-965`) and the
  lane-transition guard blocks on checkbox rows (`core/subtask_rows.py`); the snapshot slot is written only
  by `mark-status` (`tasks_mark_status.py:371`). So a raw checkbox edit without `mark-status` shows frozen
  progress — the incoherence the operator wants removed.
- **Ordering (C-010)**: remove checkboxes **only after** the backfill seeds historical completion from
  them (`_subtasks_from_tasks_md` reads them). Backfill-then-remove, same class as C-001.
- **Breadth**: touches the lane-transition guard (behaviour-sensitive) + the doctrine prompt templates
  across the mission-step families (propagated to 13 agent dirs via `spec-kitty upgrade`; never hand-edit
  agent copies). Own concern → IC-10.

## D-14 — Campsite census: two forced tidy-firsts, god-module surgical-only, extra consolidation seams

- **Two functions breach the complexity ceiling as a direct result of this mission's edits** → tidy-first
  extract in the SAME WP: `status/reducer.py::_apply_annotation_delta` (cx 13 → >15 when IC-08 adds slots)
  → data-driven replace-slot table; `dashboard/scanner.py::_process_wp_file` (cx 13 → >15 on the IC-04/07
  reroute) → extract a `_wp_runtime_view` helper backed by the reconstruction reader.
  `tasks_move_task.py::_mt_emit_runtime_state` is already at 15 (flag removal lowers it; the ownership
  reroute must extract, not inline).
- **God-modules — surgical edits ONLY, degod is OUT (tracked separately)**: `cli/commands/implement.py`
  (1863), `workflow_executor.py` (2044), `status/emit.py` (1008; `emit_status_transition` carries a
  tracked `# NOSONAR` — do NOT let IC-08/09 actor-enrichment inflate it; thread via a helper),
  `tasks_move_task.py` (2416), `migration/mission_state.py` (1982).
- **`migration/mission_state.py` is in the brief's surface list but NOT in the plan's edit map** — verify
  at `/tasks` whether it is actually touched; drop from the surface list if not, else surgical-only.
- **Extra consolidation seams** (beyond the 3-gates→1 and the shared cutover helper): (1) `tasks_status_cmd.py`
  is a **4th** gate consumer — the canonical `reconstruct_wp_view` must back all four; (2) a **shared
  review-slot reader** across `merge/done_bookkeeping.py::_extract_done_evidence` and
  `workflow_cores.py::resolve_review_feedback_context` (both interpret the review slot with different
  fallbacks → merge-gate vs CLI could diverge on reviewer attribution); (3) `WPInnerStateDelta`'s
  triple-enumeration (`is_empty`/`to_dict`/`from_dict`) → data-drive before IC-08 adds fields.
- **Per-IC campsite tasks** (SAFE unless noted): IC-01 hoist duplicated `--dry-run`/`--mission`/summary
  option decls in `migrate_cmd.py` (S1192); IC-03 delete the orphan flag-wrapper functions + dead docstring
  refs at each of the 12 sites (don't leave orphan wrappers); IC-04 narrow the broad `except Exception:`
  in `workflow_cores.py:299` + delete the dead `frontmatter-migration:` synth branch in `done_bookkeeping.py`;
  IC-06 keep `status_phase` out of bounds.

## Risks & pre-existing-red discipline (charter: Pre-existing Failure Reporting)

- **Phantom `SYNC_DISABLE_ENV_VARS`** `arch-adversarial (arch_shard_1)` red is **pre-existing on main**
  (CI-runner artifact, exists nowhere in source) — NOT this mission's; do not "fix".
- **Known-P0 reds** (ADR 2026-07-17-1: #2736, #2772, #1834) stay red; confirm on merge-base before
  attributing any red to this diff (test-run baseline-red gotcha).
- **`uv run` discipline**: run tests via `uv run --extra test python -m pytest -p no:cacheprovider <FILE>`
  — bare `python` resolves a sibling checkout and yields false greens.
- **Never run the whole `tests/architectural/` dir** — it hangs; per-file with a timeout only.
- **Dead-symbol re-pin coupling**: the 15-symbol frozenset un-pin MUST land in the WP that first wires a
  caller (IC-01), or `test_no_dead_symbols` / `test_auto_exempt_disjoint_from_hand_allowlist` trips.
- **`done_bookkeeping` under `merge/`** — a merge-path change; exercise the event-sourced done-evidence
  read before deleting the synthesis.

## Best practices applied

- ATDD-first (C-011): each new branch/helper (orchestration helper, CLI command, upgrade migration,
  bypass-reader reroute, fail-closed abort) gets a focused test in the same WP, incl. fault-injection
  for verify-abort and flip-refusal.
- Sonar: complexity ≤15 (extract the orchestration into small phases: seed / verify / flip); hoist
  repeated literals (command names, `status_phase` key, messages) to constants; no suppression.
