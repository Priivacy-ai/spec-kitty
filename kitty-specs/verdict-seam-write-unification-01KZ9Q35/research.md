# Phase 0 Research — Plan-Phase Decisions

The pre-spec investigation lives in [`research/pre-spec-research.md`](./research/pre-spec-research.md)
(five profile-loaded streams, `file:line`-anchored). This file records the **plan-phase** decisions
that resolve every open fork before `/spec-kitty.tasks`. There are **zero** `[NEEDS CLARIFICATION]`
markers.

## D-PLAN-1 — Collapse-first ordering dissolves FR-001's commit-atomicity

- **Decision**: Sequence IC-01 → IC-02 (backfill+durability) → IC-03 (reader collapse) → IC-04
  (write-partition flip). The write-partition flip lands *after* every verdict reader has moved to
  the event authority.
- **Rationale**: Once no consumer reads the `.md` for a verdict (IC-03), moving where the prose `.md`
  is physically written (IC-04) cannot affect the approval guard — the flip becomes non-safety-critical.
  This meets FR-001's guarantee (no partial-order fail-open) by *ordering*, not by a large
  write+reader single commit. It is also the only order that satisfies the two blocker findings
  (authority must be populated before readers flip; the un-migrated cohort must be backfilled first).
- **Alternatives rejected**: (a) atomic write+reader mega-commit (spec FR-001 literal reading) — larger,
  harder-to-review, and still unsafe without the backfill; (b) write-first then migrate readers —
  the exact fail-open the research proved (§5.C).
- **Spec relationship**: refines FR-001's *mechanism* (ordering) while preserving its guarantee. The
  post-plan squad should confirm the ordering closes the fail-open window with no residual.

## D-PLAN-2 — Verdict-provenance backfill: idempotency + cohort sizing

- **Decision**: A new `migration/verdict_provenance_backfill.py` reduces each existing terminal `.md`
  verdict into `status.events.jsonl` via `emit_status_transition`, keyed so a re-run is a no-op
  (idempotent on `(mission, wp, verdict, cycle)`). The provenance gate parses for "terminal `.md`
  verdict with no event `review_result` slot" and blocks IC-03's reader deletion until zero.
- **Rationale**: FR-012; closes the arch-lens blocker (event log not retroactive; `reducer.py:198`).
- **Open measurement (do in IC-02, not blocking planning)**: count the real cohort across in-repo
  missions before running, so the migration is sized against data (operator asked to confirm scope;
  confirmed in-scope).

## D-PLAN-3 — Vocabulary bridge home + guard

- **Decision**: One canonical surface beside `status/models.py` (e.g. `verdict_vocab.py`), a total
  function `artifact_verdict → event_verdict` over `{approved, rejected, arbiter_override,
  approved_after_orchestrator_fix} → {approved, changes_requested}` and its inverse for prose/render.
  An architectural test forbids any *other* module from spelling the `rejected`↔`changes_requested`
  equivalence inline (today inline in 9 modules).
- **Rationale**: FR-005; prevents the bridge from becoming a new drift surface (paula/renata).

## D-PLAN-4 — FR-004 enforcement: derived ratchet AND census (belt + suspenders)

- **Decision**: Extend `test_2093_authority_invariant.py` (add `agent_utils`/`review`/`post_merge` to
  `_READER_AUTHORITY_ROOTS`, add a `review-cycle-*.md`-glob detector arm, add `verdict` to tracked
  fields, add a synthetic-poison non-vacuity test) **and** rely on the all-`src/` verdict-seam census
  as the enumeration ratchet. Two independent checks, because the census caught what `test_2093`
  structurally could not (renata's load-bearing finding).
- **Rationale**: FR-004/SC-002; a single check was proven insufficient.

## D-PLAN-5 — Prose-only artifact: no verdict field (structural single-authority)

- **Decision**: The best-effort `.md` is written **without** a `verdict:` frontmatter field (SC-007),
  so it physically cannot be re-read as a verdict source. A census-backed check asserts the written
  artifact carries no field the census classifies as a verdict.
- **Rationale**: Finding 3 — demoting the commit to best-effort without removing the field leaves a
  persisted dual-store. Removing the field makes single-authority structural, not disciplinary.
- **Consequence**: `_guard_feedback_source_provenance` (the #990/#2996 duplicate-feedback guard, which
  parses `feedback_source` *as an artifact*) is **re-expressed** to check prose identity without a
  verdict read-back, or retired if the provenance concern is fully covered by the event authority —
  resolved during IC-04 with its own test.

## D-PLAN-6 — Review-cycle merge driver relaxes under D3

- **Decision**: With the `.md` non-authoritative and unread, the `spec-kitty-review-cycle` fail-closed
  conflict-marker driver **downgrades to non-aborting** (union/last-writer on prose) rather than
  Exit(1). Retiring it entirely is the fallback if no prose-merge is needed.
- **Rationale**: FR-014; a cosmetic render divergence must not block a squash.

## D-PLAN-7 — #2804 fixed at the write surface (#2404)

- **Decision**: `accept` writes the acceptance-matrix to the COORD surface (no PRIMARY husk); the
  driver-registration-before-squash guarantee is defense-in-depth. A write-side check asserts no
  PRIMARY acceptance-matrix is authored under a coordination topology.
- **Rationale**: FR-009; merely winning-at-merge is timing-dependent and leaves the add/add source
  (paula). Operator confirmed #2404 in scope.

## D-PLAN-8 — Merge gate goes pure-event

- **Decision**: `find_rejected_review_artifact_conflicts` reads only the event authority;
  `_artifact_dirs_for_wp` + the `_resolve_terminal_verdict_conflict` artifact leg are **retired**
  (census retirement rows), not repointed.
- **Rationale**: FR-013; the blocker contradiction (FR-001 "repoint" vs FR-003 "retire the consumer").
  Depends on IC-02 (authority populated).

---

# Phase 0 Research — Post-Plan Squad Folds (D-PLAN-9..16)

The post-plan adversarial squad (4 lenses, live-code-verified) confirmed the collapse-first
*ordering* but broke the plan's parallelism/sizing claims and found two correctness bugs in the
backfill and the SC-007 mechanism. Folded decisions:

## D-PLAN-9 — All verdict readers die in IC-03 (arch Finding A)

Two verdict readers the original plan left for IC-04 — the approval-write probe
(`tasks_verdict_persistence.py:531-568`, calls `latest_review_artifact_verdict`) and the arbiter
reader (`arbiter.py:461`) — are frontmatter verdict reads. **Pull the entire `review/artifacts.py`
verdict-parser family retirement** (`latest_review_artifact_verdict`,
`rejected_review_artifact_for_terminal_lane`, `ReviewCycleArtifact.latest`) **and the probe
repoint into IC-03**, so *every* verdict reader dies in one atomic wave. This restores the
dissolution: IC-04 becomes a pure schema+placement change with no verdict reader left.

## D-PLAN-10 — Backfill uses `append_events_atomic_verified`, not `emit_status_transition` (arch Finding B)

`emit_status_transition` derives `from_lane` from the WP's *current* lane and runs
`validate_transition` (FSM matrix) — it cannot replay a historical `in_review→…` edge onto a
settled WP. Use `append_events_atomic_verified` with a hand-constructed event (the repo's own
precedent, `backfill_runtime_state.py:1507`). **The event's `at` MUST be the historical verdict
timestamp** (from the `.md`/git record), never `now()`, or a late-stamped rejection sorts last and
resurrects over a real later approval. Define "terminal verdict" = the latest `review-cycle-N.md`
for the WP; handle a `.md` rejection superseded by a later lane-only approval. Idempotency key
includes temporal identity. Red-first: a WP with a historical `.md` rejection followed by a later
approval reduces to `approved` after backfill.

## D-PLAN-11 — Durability demote lands with the reader flip, not before (auth Finding F2)

IC-02 adds `emit_status_transition` as an *authoritative* durability write but keeps the `.md`
commit **hard-error**. The demote-to-best-effort lands **in IC-03's PR** (same PR as the reader
flip). **C-008 amended**: *the `.md` durability demote never precedes the reader flip.* Otherwise a
best-effort render failure diverges the event log and the `.md` while readers still read the `.md`.

## D-PLAN-12 — SC-007 is a schema change + a new check (auth Finding F1; renata Finding 4)

`verdict` is a required `ReviewCycleArtifact` field (`artifacts.py:148`), emitted by `to_dict`,
hard-validated by `from_dict:214`. IC-04 **removes the field from the dataclass + `to_dict` + the
`from_dict`/`validate_review_artifact` validation** — a schema change. The "census-backed check"
does not and cannot exist (the census classifies functions, not serialized fields); IC-04 adds a
**new serialized-artifact assertion** (parse the written `.md`, assert no `verdict` key). Sequence:
the verdict-parser family retirement (IC-03) lands *before* the field removal (IC-04), else
`from_dict` breaks. Enumerate the `test_review_durability_matrix.py` re-pins the field removal
triggers.

## D-PLAN-13 — Durability anchors re-pointed to the event log (renata Findings 1, 2)

`test_review_durability_matrix.py`'s SC-003 anchor asserts on `.md` files + a clean git status —
the exact `.md`-commit property the mission retires; post-demote it reds. **Re-point SC-003 to count
durable *event* records** (`read_events`/reducer slots). NFR-004's "exactly one authoritative call"
verifier counts `commit_artifact` (the demoted `.md` commit) — **re-point to count the
`emit_status_transition` append == 1** per verdict; the `artifact_calls == 1` assertion becomes a
best-effort observation. These pins are *rewritten*, not "greened as-is."

## D-PLAN-14 — Vocabulary bridge is display-only; overrides never synthesize a verdict (renata Finding 3)

The reducer deliberately does **not** overwrite `review_result` for an arbiter override (it clears
the gate over a standing `changes_requested`; the `ReviewOverride` record carries provenance,
`reducer.py:244-252`) — the #3044 separation. **Scope the bridge to `{approved, rejected}` for
`review_result` emission.** `arbiter_override` / `approved_after_orchestrator_fix` are **not**
verdict-bridge inputs to a `review_result` event; they resolve via `ReviewOverride`/orchestrator-fix
records, or the bridge output is display-only and forbidden from feeding an emitted `review_result`.
Negative test: an `arbiter_override` must not produce an `approved` `review_result` event while its
`ReviewOverride` slot carries the provenance. The `.from_dict` census gap's real site is
`models.py:570` (not `_runtime_repair_delta`, which uses a direct ctor already matched).

## D-PLAN-15 — Provenance interlock is a TEST, and a NEW predicate (arch Finding C)

The reconcile doctor reports `live_coord_pre_adr_primary_record` — a *location* class, not the
FR-012 *provenance* predicate ("terminal `.md` verdict + no event slot"). Add the new provenance
predicate as an explicit IC-02 deliverable, distinct from the location class; FR-007's location gate
and FR-012's provenance gate are two separately-named findings. The "blocks reader deletion"
interlock is enforced by the **SC-008 hermetic red-first test** (seed a pre-event `.md`-only
rejection → backfill → delete readers → assert approval still refused), not a runtime block. Make
the SC-008 pin a hard dependency edge from IC-02 to the *first* IC-03 commit.

## D-PLAN-16 — IC-06 splits; IC-04's physical flip is largely subsumed (planner; renata Finding 5)

- **IC-06a (parallel-safe)**: `merge/executor.py` accept→COORD + `mission_finalize._scaffold_acceptance_matrix_if_lane_based:1315`
  (the actual PRIMARY-husk producer — suppress the PRIMARY scaffold under coord topology) +
  `m_3_2_6_*` migrations + a write-side check that greps **every** `write_acceptance_matrix` call
  site. Genuinely touches no IC-01..05 file.
- **IC-06b (serial with IC-04)**: `merge_driver.py` matrix drivers + `init.py` `.gitattributes`
  registration + `.md`→`.json` seed drift. Shares `merge_driver.py`/`init.py` with IC-04's FR-014
  driver relax → same lane, not parallel. Add `test_merge_reconciliation_class_guard.py`,
  `verdict_seam_IC04.yaml`, `test_review_cycle_merge_driver.py` to the IC-04/06b surface set.
- **IC-04 physical flip is largely subsumed**: the review-cycle *commit* is already COORD (per-file
  classifier, ADR 2026-08-03-1); `test_analysis_report_rehome:232` pins the *physical on-disk* write
  to PRIMARY and is green. Once the collapse (IC-03) removes every verdict reader, the `.md` physical
  location no longer affects any verdict decision. **IC-04's real deliverables are the schema change
  (D-PLAN-12), the census resolver retirements, the driver relax (FR-014), and FR-011** — not a
  redundant physical move. Whether to *additionally* relocate the physical write to COORD for
  prose-consistency (re-pinning `test:232`) is a narrow `/tasks` decision, not a mission guarantee.
  Reconcile FR-007 wording: `_review_cycle_wp_dir` is `status: retire` in the census, so the fallback
  is **relocated** into the canonical placement resolver, not "preserved verbatim."

## Corrected shared-file serialization set (C-008)

`{verdict_seam_census.yaml, verdict_seam_IC01.yaml}` serialize IC-01/IC-02/IC-02b/IC-03/IC-04;
`{merge_driver.py, init.py}` serialize IC-04/IC-06b. Only **IC-06a** is a genuinely parallel lane.
Re-baseline the file estimate to ~35 (named-only floor was 20-24). Every census row is mapped to an
owning IC before `/tasks`; `orchestrator_api/commands.py::_parse_review_result_json` is ruled
in/out explicitly (it parses injected JSON, not frontmatter → likely stays, but carries inline vocab
→ swept by IC-02b).

## D-PLAN-17 — #3219 canonical flatten primitive (operator-added, post-plan)

Fold in #3219: extract `flatten_coordination_metadata(feature_dir)` (all three mutations —
`del coordination_branch` + `pop topology` + `flattened=True` — in one
load→mutate→`write_meta(validate=False)`), converging `merge/executor.py` (#3218),
`_coordination_doctor.py:816-826`, and `mission_type.py::_flatten_discarded_mission`. Correct the
`mission close --discard` partial-flatten latent bug (it never pops `topology` → a discarded coord
mission can still hit `CoordinationBranchDeleted`). Import the `topology`/`flattened` key constants
from `backfill_topology.py` (their semantic owner). Non-vacuous single-source arch-guard so the 5th
re-inline reds (this is the 4th touch: #2069→#2120→#2614→#3086/#3218).

- **Domain note**: this is coordination-metadata SSOT, adjacent to (not part of) the verdict seam —
  the same *canonical-source-unification pattern* the mission embodies, on a sibling field-set.
  Folded per operator instruction as IC-07.
- **Dependency**: assumes PR #3218 (the #3086 hotfix, handed to the parallel session) has landed on
  the base; IC-07 converges the executor call site #3218 introduces. If #3218 is not yet on `main`
  at rebase time, IC-07 waits. **Shares `merge/executor.py` with IC-06a** → serialize/same lane.
- **Also verify** (#3218 landing-review residual): the `--push` origin-divergence — `_phase_push`
  (phase 11) runs before cleanup (phase 12), so a `--push` merge lands the flatten bookkeeping
  commit local-only; origin/target keep the stale `coordination_branch`.
