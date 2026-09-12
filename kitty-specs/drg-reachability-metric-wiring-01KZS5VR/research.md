# Phase 0 Research — DRG Reachability Metric & Orphan Wiring

Consolidated from three parallel research lenses (directives/reachability; metric/test-ledger blueprint;
styleguide/toolguide/skills + #1923 residual). All claims verified against live graph
(`load_built_in_graph()` on `packs/built-in/`) and green tests. Every proposed edge is cited to the
source/target artifact text — the D-C2/C-003 anti-metric-gaming test applied per node.

## Decision: Add a whole-graph reachability companion guard (#3009 point 3)

- **Decision**: Add `_ACTION_UNREACHABLE_SHIPPED` (a frozenset membership pin) + a set-equality guard in
  `tests/doctrine/drg/test_reachability.py`, computing the activatable-kind nodes reachable from neither
  channel (action d2 ∪ profile), excluding traversal roots and by-design edgeless kinds. Failure names the
  URN via the existing differ.
- **Rationale**: The shipped guards measure **incidence** (`_SHIPPED_ORPHANS`=21) or the **activated-only**
  universe. Nothing pins whole-graph action-reachability, so a node with outbound edges but no inbound path
  passes silently (#3009's "50 nodes have outbound edges only, unreachable in fact"). The whole-graph frame
  additionally catches unreachable doctrine *before* it is activated — the value needed before mission B2.
- **Alternatives considered**: (a) action-only whole-graph (`347 − seeds − reachable` = 170@d2) — rejected:
  double-counts the by-design profile-delivered residual. (b) activated-only both-channel (=30, the current
  `_ACTION_UNREACHABLE_D2 ∩ _PROFILE_UNREACHABLE`) — rejected: already implicitly guarded, adds little.
- **Mechanics**: `resolve_context` walks `scope`(d1) → `requires`(∞) + `suggests`(depth) from scope-resolved
  artifacts → `vocabulary`(d1). Profile channel walks `PROFILE_CHANNEL_RELATIONS = {requires,
  specializes_from, suggests}` (3 relations — `reachability.py:59-61`; an earlier draft here said 2, which
  understated why so many nodes are profile-rescued: the profile `suggests` web is a *soft/advisory*
  delivery). Use canonical `action_channel_reachable(graph, action_seeds, depth)` /
  `profile_channel_reachable(graph, profile_seeds)` (`src/doctrine/drg/reachability.py:80/110`). **Do NOT
  re-implement the walk** — every hand-rolled BFS in this subsystem's history produced a different wrong
  number.

> **SUPERSEDED (post-plan squad):** the "both-channel" metric framing below was revised. The primary pin
> is now the **action-only** whole-graph set (`_ACTION_UNREACHABLE_SHIPPED`, **88 → 75**, the #3009 literal
> "reachable from actions" ask), with an asserted partition into **34 both-channel-dead** + **41
> profile-rescued**. See plan.md DD-1 and data-model.md. The both-channel number (38→34) is retained as the
> dead-doctrine subset.

## Decision: Wire six genuine inbound edges (traced)

Authoring site for all six: `src/doctrine/drg/migration/extractor.py` → `_CURATED_ARTIFACT_EDGES`
(extractor.py:264, consumed at :866) — the operator-blessed #3009-remedy home. Each `(source, target,
Relation)` tuple carries an inline rationale comment. Then regenerate `packs/built-in/*.graph.yaml`.

| # | Edge (source --rel--> target) | Channel effect | Trace (artifact text) | Why genuine (not gamed) |
|---|---|---|---|---|
| 1 | `procedure:refactoring --suggests--> directive:DISCIPLINED_REFACTORING` | action-reachable (procedure:refactoring scoped by implement/review/tasks) + cascades 7 Fowler tactics | refactoring.procedure.yaml:26-31 (step 2 "Select the relevant refactoring tactics"); disciplined-refactoring.directive.yaml:14-17,26-27 ("Name the smell first"); procedure comment :59-62 blesses inbound wiring "not metric-gaming — real choices" | Same doctrinal domain, artificially split: the procedure already cites 9 Fowler tactics; the directive holds 7 disjoint ones + the discipline. |
| 2 | `directive:DIRECTIVE_024 --suggests--> RECONCILE_CHANGE_SCOPE_TENSIONS` | action-reachable (024 reachable) | reconcile-change-scope-tensions.directive.yaml:16-20 (scope: "Applies whenever a change is evaluated against DIRECTIVE_024, DIRECTIVE_025…") | The reconciler's own scope names 024 as its trigger; only the traversable edge was missing. |
| 3 | `directive:DIRECTIVE_025 --suggests--> RECONCILE_CHANGE_SCOPE_TENSIONS` | reinforces #2 | same scope sentence (names 025) | Same; enforcement advisory ⇒ `suggests`. RECONCILE is a tracked `_ACTIVATED_BUT_ORPHANED` member → this shrinks that defect set. |
| 4 | `directive:DIRECTIVE_030 --suggests--> USE_MUTATION_TESTING_TO_VALIDATE_TEST_QUALITY` | action-reachable (030 reachable) + cascades mutation family | use-mutation-testing….yaml:4-11,24-28 (critiques coverage = 030's metric); 030-test-and-typecheck-quality-gate.directive.yaml:12-13; remedy-4 used same `030--suggests-->` shape (extractor.py:374-386) | 030 governs the coverage gate; the mutation directive validates whether covered tests constrain behaviour. `lenient-adherence` ⇒ `suggests`. |
| 5 | `agent_profile:researcher-robbie --requires--> procedure:spike-timebox-policy` | profile-channel reachable | researcher-robbie.agent.yaml:58-60 structured `operating-procedures: [research-template, spike-timebox-policy]`; procedure entry-condition spike-timebox-policy.procedure.yaml:12-17 | Structured `operating-procedures` field declares the profile runs it ⇒ `requires` (exact WP09 precedent, strongest of the three). |
| 6a | `agent_profile:lexical-larry --suggests--> procedure:glossary-maintenance-workflow` | profile-channel reachable (suggests is in the channel) | lexical-larry.agent.yaml:53-54 ("the diagnostic **feeder into** the glossary-maintenance-workflow"); `curator-carla` owns its acceptance (larry.yaml:39-42) | **suggests, not requires** (Debbie #6): larry FEEDS the workflow, does not depend on/own it; `requires` would overstate. Verified suggests still confers profile-reachability. |
| 6b | `agent_profile:minutes-maker-mahad --requires--> procedure:meeting-minutes-pipeline` | profile-channel reachable | minutes-maker-mahad.agent.yaml:39-40 ("Mahad is the primary agent for the meeting-minutes-pipeline procedure") | Explicit prose ownership; prose-grounded (flagged: DD-2). |

**Verified independently**: at HEAD, `procedure:refactoring`, `DIRECTIVE_024`, `DIRECTIVE_025`,
`DIRECTIVE_030` are action-reachable; `DISCIPLINED_REFACTORING`, `RECONCILE_…`, `USE_MUTATION_…` are
action-unreachable. So edges 1–4 genuinely convert unreachable→reachable.

## Decision: Keep five honest residuals (no edge), retire one, promote six

- **Residual (honest, activation/runtime-only — wiring would be doctrinally wrong):**
  - `directive:DIRECTIVE_035` — runtime `change_mode: bulk_edit` gate (035…yaml:10-11); bulk-edit is not a
    first-class action/mission_type, so any `action--scope-->035` misfires on every mission.
  - `directive:DIRECTIVE_039` — operator-selected opt-in culture (039…yaml:6-8).
  - `procedure:migrate-project-guidance-to-spec-kitty-charter` — one-time charter onboarding, zero owners.
  - `styleguide:deployable-skill-authoring` — no honest static referent; wiring to daphne/DIRECTIVE_044/
    common-docs is subject-mismatched (only consumer is the runtime `spk-meta-skill-authoring` skill, not a
    DRG node).
  - `agent_profile:human-in-charge` — runtime-assignment sentinel.
  - (plus by-construction residuals already documented: 17 mission_step_contract, glossary_pack, asset,
    toolguide:powershell-syntax.)
- **Retired**: `toolguide:rtk-search-tooling` — removed from disk + graph (commit `95c5b925a`, fold
  `0df8ce380`). Remove its stale row from the residual doc.
- **"Promoted" — reclassified by REACHABILITY, not incidence (Debbie #4).** The earlier claim that six were
  "promoted to wired" conflated incidence-wiring with reachability. Verified against the live graph:
  - **Genuinely ACTION-reachable** (truly resolved): `tactic:decision-marker-capture`,
    `tactic:no-parallel-duplicate-test-runs`, `toolguide:python-review-checks`,
    `procedure:red-main-release-discipline`.
  - **PROFILE-only** (incidence-wired, action-unreachable — profile-rescued residual):
    `styleguide:reasons-canvas-writing`, `tactic:occurrence-classification-workflow`.
  - **Reachability-DEAD (inert edge)**: `paradigm:atomic-design` — its only inbound is
    `tactic:atomic-design-review-checklist --suggests-->`, and that tactic is itself unreachable. It is a
    **reachability residual**, NOT wired. This is exactly the incidence-masks-reachability trap #3009 targets.
  - BDD/test styleguides+toolguides (given-when-then, quadruple-a, gherkin, sonar) are incidence-wired via
    overlay directive edges; `quadruple-a` carries an **inert** edge (DIRECTIVE_041 not action-scoped) — a
    traversability note, NOT wired further in A2 (a second edge would be gaming).

## Decision: FR-007 via curated tuples, systemic projection deferred

The extractor projects `directive-references`/`tactic-references` but **not** the structured
`operating-procedures` field (model `agent_profiles/profile.py:161`, consumed by no edge builder). Teaching
it to project `operating-procedures→requires` would wire all profile-run procedures at once (canonical-
source hygiene, prevents drift) — but with an unaudited blast radius. **A2 uses three curated tuples**
(edges 5/6a/6b) and files the systemic projection as a follow-up (see plan DD-2).

## Ledger-move accounting (delta discipline — NFR-004)

Every pin move needs a composition-ledger row in `docs/plans/doctrine/delivery-reachability-wiring-table.md`
naming the responsible edge, plus an entry in the extractor numbered ledger block.
`test_profile_rescues_have_ledger_coverage` cross-checks every `_PROFILE_RESCUES` member. D18 review-gate:
a pin move with no ledger row is a hard reject even if green. Constants that move on this wiring:
`_ACTIVATED_BUT_ORPHANED` (RECONCILE leaves — shrink), `_AWAITING_REFERENCES` (DISCIPLINED_REFACTORING,
USE_MUTATION leave — shrink), `_INTENTIONAL_ORPHANS`/`_SHIPPED_ORPHANS`, `_ORPHANS_RESOLVED_BY_OVERLAY`,
`_ACTION_UNREACHABLE_D1/D2`, `_PROFILE_UNREACHABLE`, `_PROFILE_RESCUES`, `DOCUMENTED_ORPHAN_RESIDUAL`
(ratchet down), and the new `_ACTION_UNREACHABLE_SHIPPED`. `_NORMALIZATION_DELTA` does NOT move on wiring.
Exact post-wiring values are computed empirically in Phase 1 / implement, not guessed.

## Empirical verification of reachability mechanics (computed against live graph)

The traversal (`resolve_context`, query.py:139-155): scope(d1) from action → `scoped_artifacts`; then
`requires`(∞) + `suggests`(≤depth) walked **from `scoped_artifacts`**; profile channel walks
`{requires, specializes_from}`(∞) from profile seeds. Verified by constructing each edge via the real
`DRGEdge` model and re-resolving:

- **Whole-graph "dead doctrine" measure** (activatable nodes reachable from NEITHER channel, excluding
  traversal roots + by-design edgeless kinds): **38 → 34** after the six edges. The four that leave are
  `RECONCILE_CHANGE_SCOPE_TENSIONS` + the three procedures (`spike-timebox-policy`,
  `glossary-maintenance-workflow`, `meeting-minutes-pipeline`) — they were reachable from neither channel.
- **`DISCIPLINED_REFACTORING` and `USE_MUTATION_TESTING` are already PROFILE-channel reachable** (via
  implementer-profile `requires`/`specializes_from` chains), so they are correctly NOT "dead doctrine" and
  do not move the both-channel companion. Wiring them (edges 1, 4) makes them **action-channel** reachable
  and cascades their tactic families into action context: **action-channel reachable d2 153 → 166 (+13)**,
  d1 143 → 146. That win is guarded by the existing activated-only `_ACTION_UNREACHABLE_D1/D2` pins moving.
- **Metric decision (DD-1 confirmed)**: the companion pins the **both-channel** whole-graph set (38→34) —
  a node reached by the profile channel is surfaced when its profile is active, so it is not dead; counting
  it as a defect would be a false positive. The action-cascade win of edges 1/4 is captured by the existing
  activated-universe pins, not the companion. Both signals are therefore guarded and complementary.

Anchor numbers for the ledger (whole-graph, load_built_in_graph, d2 for action channel):
| measure | before | after |
|---|---:|---:|
| action-channel reachable (d1 / d2) | 143 / 153 | 146 / 166 |
| profile-channel reachable | 178 | 182 |
| whole-graph unreachable-activatable (`_ACTION_UNREACHABLE_SHIPPED`) | 38 | 34 |

Exact moves of the *activated-only* pins (`_ACTION_UNREACHABLE_D1/D2`, `_PROFILE_UNREACHABLE`,
`_PROFILE_RESCUES`) and the incidence frozensets are computed at implement time against the regenerated
graph, each with a wiring-table ledger row (NFR-004).
