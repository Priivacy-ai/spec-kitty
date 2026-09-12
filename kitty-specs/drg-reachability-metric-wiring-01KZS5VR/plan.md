# Implementation Plan: DRG Reachability Metric & Orphan Wiring

**Branch**: `fix/drg-reachability-metric-wiring` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/drg-reachability-metric-wiring-01KZS5VR/spec.md`

## Summary

Deliver #3009 remedy point 3 — a **whole-graph action/profile reachability companion guard** that names
the URN of any activatable doctrine node reachable from no channel ("cascades to nothing") — and shrink
that debt by authoring the **six genuine, traced inbound edges** research found (three directive edges,
three profile→procedure edges). Reconcile every moved golden constant with a wiring-table composition
ledger row, curate the #1923 residual truthfully (retire the stale entry, promote the six now-wired,
justify the honest activation/runtime-only residuals), and close #3009 + #1923. No valid artifact is
deleted; no edge is manufactured to shrink a metric (binding curation policy D-C2 / C-003).

Prior art consumed (do not redo): A1/PR#3301 fixed the slug-hub directive id-normalizer (root of #3009 for
slug-named directives) and re-pinned numeric guards; #3009 point 1 (membership frozensets `_INTENTIONAL_ORPHANS`
/ `_SHIPPED_ORPHANS`) landed earlier (commits `a19d0f42e`/`15fb436a2`); interim missions already wired 8 of
the original 9 activated orphans and retired `toolguide:rtk-search-tooling`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: doctrine DRG subsystem (`doctrine.drg.*`) — loader, reachability, query, migration/extractor, migration/hand_authored_overlay; pytest; ruamel/pyyaml for graph fragments
**Storage**: Committed per-kind DRG graph fragments under `packs/built-in/*.graph.yaml` (regenerated deterministically); artifact YAMLs under `packs/built-in/`
**Testing**: pytest — `tests/doctrine/drg/test_reachability.py` (reachability ledger), `tests/doctrine/drg/migration/test_extractor_projection.py` (incidence ledger), `tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py` (orphan ceiling); new focused tests for the companion guard's URN-naming behavior
**Target Platform**: Linux/macOS/Windows dev + CI (Python library)
**Project Type**: single (Python CLI/library)
**Performance Goals**: N/A (build-time graph guard; sub-second)
**Constraints**: Genuine-edge-only (NFR-001); reachability/incidence residuals only shrink or hold (C-003, NFR-005); ledger row for every pin move (NFR-004); zero new ruff/mypy issues (NFR-006); no B2 scope (C-004)
**Scale/Scope**: ~347-node built-in graph; 6 authored edges; ~1 new guard + membership frozenset; ~8–10 golden-constant moves across 3 test files + 1 wiring-table doc + 1 residual doc

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority / canonical sources (PASS)**: edges authored in the operator-blessed
  `_CURATED_ARTIFACT_EDGES` (extractor.py) — the established #3009-remedy home (precedent: WP09 daphne fix,
  remedy-4). No improvised authoring site; overlays (tension/lineage) are not repurposed.
- **DDD + tiered rigour (PASS)**: DRG is a core subsystem → strict rigour: focused tests for each new
  branch/helper, deterministic guard, no suppressions.
- **ATDD-first (PASS)**: each wired edge gets a red-first reachability assertion (unreachable→reachable);
  the companion guard gets a red-first URN-naming test (delete an edge → named failure).
- **Quality & Tech-Debt Standing Orders (PASS)**: campsite-first on the touched ledger comments;
  delta-accounting discipline (NFR-004) is itself a standing-order-grade guardrail.
- **Terminology Canon (PASS)**: Mission terminology; DRG domain terms are canonical (docs/context/).
- **Reconciling change-scope tensions (NOTED)**: `directive:DISCIPLINED_REFACTORING` and
  `procedure:refactoring` are near-duplicate doctrine — A2 LINKS (one `suggests` edge), does NOT consolidate
  (consolidation is a separate doctrine-authoring decision, out of scope).
- **Binding curation policy D-C2 / C-003 (PASS, load-bearing)**: wire only genuine referents; document the
  rest; delete nothing valid. Every edge is cited to artifact text in research.md.

No violations → Complexity Tracking not required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/drg-reachability-metric-wiring-01KZS5VR/
├── plan.md              # This file
├── research.md          # Phase 0 — consolidated 3-lens triage + edge trace table
├── data-model.md        # Phase 1 — DRG entities, the moved-pin ledger, the companion metric definition
├── quickstart.md        # Phase 1 — how to run the guard, regenerate fragments, verify a wire
├── contracts/
│   └── reachability-companion-guard.md   # Behavioral contract of the new guard (membership + URN-naming)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/doctrine/drg/
├── reachability.py                     # canonical action_channel_reachable / profile_channel_reachable (consume, do not reimplement)
├── query.py                            # resolve_context traversal (scope→requires→suggests→vocabulary)
├── loader.py                           # load_built_in_graph() — the shipped composed graph
└── migration/
    ├── extractor.py                    # _CURATED_ARTIFACT_EDGES — authoring site for the 6 edges; generate_graph
    └── hand_authored_overlay.py        # overlay families (NOT touched for reachability edges)

packs/built-in/
├── *.graph.yaml                        # committed per-kind graph fragments — REGENERATED deterministically
├── directives/…                        # DISCIPLINED_REFACTORING, RECONCILE_…, USE_MUTATION_… (cite text)
├── procedures/…                        # refactoring, spike-timebox-policy, glossary-maintenance-workflow, meeting-minutes-pipeline
└── agent_profiles/…                    # researcher-robbie, lexical-larry, minutes-maker-mahad (cite ownership)

tests/doctrine/drg/
├── test_reachability.py                # + companion guard + _ACTION_UNREACHABLE_SHIPPED; reachability pins move
└── migration/test_extractor_projection.py   # incidence ledger frozensets move (_ACTIVATED_BUT_ORPHANED must only shrink)
tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py   # DOCUMENTED_ORPHAN_RESIDUAL ceiling ratchet

docs/plans/doctrine/delivery-reachability-wiring-table.md          # composition-ledger rows for every pin move
kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/drg-orphan-residual.md   # #1923 residual truth-up
```

**Structure Decision**: Single-project Python. The change is concentrated in the DRG migration/extractor
authoring table + the two test ledgers + the regenerated graph fragments + two docs. All work touches a
**shared, tightly-coupled surface** (the same graph fragments and the same two ledger test files), which
dominates the lane strategy (see IC risks).

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Key Design Decisions

- **DD-1 — Companion metric framing (`_ACTION_UNREACHABLE_SHIPPED`, action-only whole-graph, with an
  asserted partition).** *(Revised after post-plan squad — Alphonso Axis-1 / Debbie / Renata.)* The primary
  pin is the membership set of *activatable-kind* nodes **not reachable from any action root** (action
  channel at bootstrap depth d2), excluding traversal roots (actions + agent_profiles as seeds) and
  by-design edgeless kinds (mission_step_contract, asset, anti_pattern, template, mission_type,
  glossary_pack). This is the "**measured from action roots**" guard #3009 point 3 literally asks for
  (the issue's headline 46%/144). **Measured: 88 → 75** after wiring — and it captures the full cascade
  (the three directives + their Fowler/mutation tactic + toolguide families, 13 nodes, leave), so edges
  1 and 4 are pin-guarded (the earlier both-channel-only framing could not guard them, because
  DISCIPLINED_REFACTORING / USE_MUTATION are non-activated **and** already profile-reachable).
  - The action-only alternative was earlier dismissed citing "170"; that was an unfair comparison (no
    exclusions applied). Like-for-like (same by-design/seed exclusions) it is **88**, not 170.
  - **Asserted internal partition (Debbie's totality requirement, #3009 "record which nodes the count
    covers"):** the 75 splits into **34 both-channel-dead** (reachable from *neither* channel — the
    genuine residual) + **41 profile-rescued** (action-unreachable but delivered via the profile channel's
    `{requires, specializes_from, suggests}` web — by design, surfaced when the owning profile is active).
    Both subsets are named frozensets whose union equals the primary pin (asserted total & disjoint), so no
    member rides along unexamined.
  - Assertion is **set-equality** (names the URN via the existing `_describe` differ), computed via the
    canonical `action_channel_reachable` / `profile_channel_reachable` helpers (never a re-implemented
    walk). The action channel uses a named `_ACTION_D2_DEPTH` constant, not a bare literal. The guard
    helper lives **in the test module** (not `src/`) to avoid a dead-symbol arch-gate red (Renata F7).
  - `anti_pattern` is in the by-design exclusion (resolved by URN presence, not traversal); rationale
    recorded in the contract so an orphaned anti-pattern is not silently laundered.

- **DD-2 — FR-007 profile→procedure wiring uses curated tuples with honest relations; systemic projection
  filed.** *(Revised after squad — Alphonso Axis-2 / Debbie #6.)* Three curated tuples in
  `_CURATED_ARTIFACT_EDGES`, each with the **relation the source's own text supports** (not a uniform
  `requires`):
  - edge 5 `agent_profile:researcher-robbie --requires--> procedure:spike-timebox-policy` — robbie's
    **structured** `operating-procedures` field lists it (machine-readable ownership).
  - edge 6b `agent_profile:minutes-maker-mahad --requires--> procedure:meeting-minutes-pipeline` — mahad is
    the "**primary agent for**" it (explicit ownership).
  - edge 6a `agent_profile:lexical-larry --suggests--> procedure:glossary-maintenance-workflow` — **suggests,
    not requires**: larry is a "**feeder into**" the workflow while `curator-carla` owns its acceptance;
    `requires` would overstate the relation (Debbie #6). Verified: `suggests` still makes the procedure
    profile-channel reachable (the channel walks `suggests` too).
  - We do **not** backfill a structured `operating-procedures` entry onto larry (it would falsely assert
    ownership of a workflow he only feeds). A tracked follow-up for the **systemic** `operating-procedures →
    requires` projection (the field exists on 16 profiles / ~40 entries and is projected by nothing) is
    **filed in W3**, not merely mentioned — its unaudited blast radius (moves more pins) keeps it out of A2.

- **DD-3 — Link DISCIPLINED_REFACTORING to procedure:refactoring (they are complementary, not duplicate).**
  *(Refined after Alphonso Axis-4.)* The procedure cites 9 Fowler tactics; the directive holds **7 disjoint**
  ones + the discipline — disjoint partitions are complementary, so there is **no split-brain to resolve**,
  only a missing traversal edge. A2 authors the single `suggests` link (making the directive action-
  reachable). Any residual "two artifacts titled around disciplined refactoring" consolidation question is a
  doctrine-authoring decision **filed as a follow-up in IC-03**, not asserted away.

- **DD-4 — Honest residuals stay residual (two distinct metrics — do not conflate).**
  *(Revised after Debbie #2 / #7.)*
  - **Reachability residuals** (members of the both-channel-dead subset of `_ACTION_UNREACHABLE_SHIPPED`):
    `directive:DIRECTIVE_035` (runtime `change_mode: bulk_edit` gate — an action-scope edge would misfire on
    every mission), `directive:DIRECTIVE_039` (opt-in culture), `procedure:migrate-project-guidance-to-spec-kitty-charter`
    (one-time onboarding, **not owned by `doctrine-daphne` because it is a one-time charter migration, not a
    recurring profile procedure** — Debbie #7), `styleguide:deployable-skill-authoring` (no honest static
    referent — daphne/DIRECTIVE_044/common-docs are subject-mismatched). `paradigm:atomic-design` is also a
    reachability residual (**inert-edge**: its only inbound is from a tactic that is itself unreachable —
    it is NOT "wired", correcting the earlier note). Each enrolled with an explicit "reachable by
    charter-activation/runtime only, by design" note.
  - **Incidence residual (a DIFFERENT metric — #1923, not the reachability guard):**
    `agent_profile:human-in-charge` is an agent_profile, i.e. a profile **seed / traversal root** — it is
    excluded from `_ACTION_UNREACHABLE_SHIPPED` by construction and must NOT be presented as a reachability
    residual. It stays strictly an incidence residual with its runtime-sentinel note.

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs.

*(Revised after squad — Alphonso Axis-3 collapsed 5 concerns → 3. All concerns share the same two ledger
test files + regenerated `packs/built-in/*.graph.yaml`, so they MUST be **sequential WPs on a single lane**;
parallel lanes would add/add-conflict. The 6 edges add zero new nodes, so node-count inventory tests are
unaffected and the determinism/byte-identity gate self-adjusts.)*

### IC-01 — Wiring + behavioral red-first

- **Purpose**: Author the six genuine edges in `_CURATED_ARTIFACT_EDGES` (3 directive `suggests`; edges 5/6b
  `requires`, edge 6a `suggests` per DD-2), regenerate the graph fragments deterministically, and prove each
  with a **behavioral** red-first assertion.
- **Relevant requirements**: FR-004, FR-005, FR-006, FR-007; SC-002, SC-003.
- **Affected surfaces**: `src/doctrine/drg/migration/extractor.py` (`_CURATED_ARTIFACT_EDGES` + inline
  rationale comments citing artifact text); regenerated `packs/built-in/*.graph.yaml`;
  `tests/doctrine/drg/test_reachability.py` (behavioral assertions).
- **ATDD (Renata F3)**: per wired node, `assert target not in reachable` (pre-edge) → `assert target in
  reachable` (post-edge) via the canonical helpers — NOT a frozenset-literal edit. This is the real
  red-first; pin updates are follow-on bookkeeping in IC-02.
- **Sequencing/depends-on**: first (foundational graph change).
- **Risks**: 4 directive sources must be directly `scope`-seeded for the `suggests` to be non-inert
  (verified — they are). Regeneration must be byte-identical on re-run.

### IC-02 — Companion metric + pin reconciliation + mechanical ledger coverage

- **Purpose**: Add the `_ACTION_UNREACHABLE_SHIPPED` guard (action-only whole-graph, 88→75) with its
  asserted **34 both-channel-dead + 41 profile-rescued** partition; reconcile every moved golden pin; add a
  **mechanical** ledger cross-check for the new pin's deltas; ratchet the incidence ceiling.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-010; NFR-003, NFR-004, NFR-005; C-003, C-005;
  SC-001, SC-005.
- **Affected surfaces**: `test_reachability.py` (new guard + 3 frozensets [primary + 2 partition subsets] +
  `_BY_DESIGN_UNREACHABLE_KINDS` + reuse `_describe` differ + **new** `test_action_unreachable_shipped_
  members_have_ledger_coverage` analog to the `_PROFILE_RESCUES` gate — Renata F2/Debbie #5; guard helper
  kept **in the test module** — Renata F7; a **by-design-kind exclusion** test — Renata F4);
  `test_extractor_projection.py` (`_ACTIVATED_BUT_ORPHANED` shrink [RECONCILE leaves], `_AWAITING_REFERENCES`
  shrink [DISCIPLINED_REFACTORING/USE_MUTATION leave incidence], `_INTENTIONAL_ORPHANS`/`_SHIPPED_ORPHANS`,
  `_ORPHANS_RESOLVED_BY_OVERLAY`, numbered-ledger entry 18 + shipped-edge-count prose);
  `test_doctrine_regenerate_graph.py` (`DOCUMENTED_ORPHAN_RESIDUAL` ratchet DOWN in the SAME WP as the
  incidence shrink); `docs/plans/doctrine/delivery-reachability-wiring-table.md` (ledger rows — **run
  `inventory_lockfile --write`**, it is inventory-tracked — Renata F6).
- **Correct per-member accounting (Renata F1/F5)**: `_PROFILE_UNREACHABLE` (activated-only) shrinks by
  exactly `glossary-maintenance-workflow` (the only activated one of the three procedures), which then
  **enters** `_PROFILE_RESCUES`; `_ACTION_UNREACHABLE_D1/D2` (activated-only) shrink via the cascaded
  **activated tactics** (`refactoring-*`, mutation-testing-workflow), NOT the directives (DISC/USE are not
  activated). Exact integers computed at implement time against the regenerated graph; every entering/leaving
  member gets a wiring-table row.
- **Sequencing/depends-on**: IC-01 (needs the final graph).
- **Risks**: D18 surface — now partly mechanized (F2). Partition identities must stay total & disjoint
  (`sum(parts)==len(_INTENTIONAL_ORPHANS)`; primary == 34-dead ∪ 41-rescued, disjoint). Every pin move needs
  a ledger row (per-WP acceptance check).

### IC-03 — Residual curation (full enumeration) + follow-up filing + ticket closure

- **Purpose**: Give **every** member of the pinned residual a disposition (Debbie #1 totality); truth-up the
  #1923 residual doc; file the deferred follow-ups; close #3009 + #1923 with reconciled evidence.
- **Relevant requirements**: FR-008, FR-009, FR-011; NFR-002; SC-004.
- **Enumeration (Debbie #1)**: the 41 profile-rescued members are dispositioned **as a group** ("action-
  unreachable, delivered via the profile channel — by design"); the 34 both-channel-dead members each get a
  one-line disposition — honest activation/runtime-only residual (with note) | by-construction | B2-deferred-
  with-referent-named. No member rides along unexamined. `agent_profile:human-in-charge` is recorded ONLY as
  an incidence (#1923) residual, not a reachability one (Debbie #2). `paradigm:atomic-design` recorded as an
  inert-edge reachability residual, correcting the "promoted to wired" note (Debbie #4).
- **Follow-ups to FILE (real tracked issues, not prose — Alphonso Axis-2/Axis-4)**: (a) systemic
  `operating-procedures → requires` projection; (b) `DISCIPLINED_REFACTORING` vs `procedure:refactoring`
  consolidation triage; (c) `quadruple-a` / `DIRECTIVE_041` action-scope traversability.
- **#3009 closure note (Alphonso Axis-5/Debbie #3)**: state that the guard is CI/build-time only
  (`doctrine doctor` does not surface reachability), and that both the action-only whole-graph (`reachable_
  from_actions`, the issue's literal ask) and the both-channel-dead subset are now pinned.
- **Affected surfaces**: `kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/drg-orphan-residual.md`
  (NOT inventory-tracked); exemption comments; CHANGELOG; issue comments at PR time.
- **Sequencing/depends-on**: IC-02 (reflects the final pinned sets).
- **Risks**: Must match the graph's true residual exactly; no valid-artifact deletion (NFR-002).
