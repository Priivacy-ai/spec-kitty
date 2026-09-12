# Mission Specification: DRG Reachability Metric & Orphan Wiring

**Mission Branch**: `fix/drg-reachability-metric-wiring`  
**Created**: 2026-08-11  
**Status**: Draft  
**Input**: Deep DRG orphan wiring + reachability-metric honesty; closes #3009 and #1923. Follow-on to A1/PR#3301.

## Context & Background

The Doctrine Reference Graph (DRG) composes doctrine artifacts (directives, tactics, styleguides,
toolguides, procedures, paradigms, agent profiles, actions, mission types) into a graph. When a charter
**activates** an artifact, the value of that activation is that the artifact becomes reachable during
context resolution — a workflow action walks `scope → requires/suggests/vocabulary` and surfaces the
activated doctrine. If nothing reaches an activated artifact, activating it "cascades to nothing."

Issue **#3009** established that the shipped orphan guard measures the **wrong thing**: it counts nodes
*incident to zero edges* (incidence). An activated directive can carry outbound edges — non-orphan by
incidence — yet be reachable from no action, so it is inert in fact while the metric reads it as healthy.
The issue proposed three remedies: (1) replace the bare orphan **count** with a **membership** set so a
new orphan names itself; (2) per-artifact triage of the residual; (3) add a **reachability** companion
metric measured from action roots, so the meaningful condition is the one guarded. Remedies (1) and (2)
have been substantially delivered by interim missions and A1/PR#3301 (which fixed the slug-hub directive
id-normalizer — the root cause for slug-named directives — and re-pinned the numeric guards). Remedy (3)
— the reachability companion — remains **open**, and it is the load-bearing guard that must exist before
the future mission "B2" migrates 400+ inline references and moves all the graph numbers at once.

Issue **#1923** tracks the residual orphan curation. Its authoritative doc lists 14 (later 10) residual
orphans, but the graph has moved on: 6 are now genuinely wired, 1 (`toolguide:rtk-search-tooling`) was
retired, and the true residual is a small set of genuine activation/runtime-only artifacts.

Research (three parallel lenses, findings in the mission notes) triaged the current residual and found a
small set of orphans that DO have a genuine, traceable doctrinal referent whose edge was simply never
authored — and a smaller set that are honestly activation/runtime-only, where any edge would be
metric-gaming (prohibited by the DRG curation policy D-C2 / C-003).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reachability is measured and guarded, not just incidence (Priority: P1)

A doctrine maintainer (or a future migration mission) needs to know, at any commit, exactly which
activatable doctrine artifacts are reachable from **no** workflow action or agent-profile channel — i.e.
which activated doctrine "cascades to nothing." Today the guard only sees edge-incidence, so an artifact
with outbound edges but no inbound path passes silently. This story adds a whole-graph reachability
companion guard whose failure **names the offending URN**, so a regression (a newly-unreachable node, or a
node that quietly *became* reachable) announces itself by identity rather than by a shifted count.

**Why this priority**: This is the structural, load-bearing deliverable of #3009 point 3. Without it, the
"cascades to nothing" defect class is invisible, and mission B2 would migrate references against a metric
known to be the wrong one. Every other outcome in this mission moves this metric; it must exist first.

**Independent Test**: Add the companion guard with a pinned membership set; verify that (a) it passes on
the current graph, (b) artificially deleting a real inbound edge makes it fail and **names** the now-
unreachable URN, and (c) it is computed via the canonical reachability helpers, not a re-implemented walk.

**Acceptance Scenarios**:

1. **Given** the shipped built-in graph, **When** the reachability companion guard runs, **Then** it
   computes the set of activatable-kind nodes reachable from neither the action channel nor the
   profile channel (excluding traversal roots and by-design edgeless kinds) and asserts it equals the
   pinned membership set — passing on the current graph.
2. **Given** a genuine inbound edge is removed from a currently-reachable activated node, **When** the
   guard runs, **Then** it fails and the failure message names that node's URN as newly unreachable.
3. **Given** a residual orphan is wired to a genuine referent in this mission, **When** the guard runs,
   **Then** the pinned membership set shrinks by exactly that node and the change is accompanied by a
   composition-ledger row explaining the move.

---

### User Story 2 - Residual orphans with a genuine referent become reachable (Priority: P2)

An agent whose charter activates a doctrine artifact expects that activation to *do something* — to make
the artifact surface during the relevant workflow action or agent profile. For the residual orphans that
have a genuine, traceable doctrinal relationship whose edge was simply never authored, this story adds
that inbound edge so activation genuinely cascades. Each edge must represent a real relationship, cited to
the artifact's own text; manufacturing an edge only to shrink a metric is prohibited.

**Why this priority**: This is the honest half of "wiring" — it shrinks the reachability debt by making
inert doctrine effective, and it cascades to the orphaned tactic families those directives select. It
depends on Story 1 existing so the improvement is measured.

**Independent Test**: For each wired node, assert it is unreachable before the edge and reachable after,
via the canonical reachability helpers; and assert the edge's rationale is recorded in the wiring-table
ledger.

**Acceptance Scenarios**:

1. **Given** `directive:DISCIPLINED_REFACTORING` is action-unreachable, **When** a `suggests` edge is
   authored from the (action-reachable) `procedure:refactoring` that already selects Fowler tactics,
   **Then** the directive — and the refactoring tactics it holds — become action-reachable.
2. **Given** `directive:RECONCILE_CHANGE_SCOPE_TENSIONS` is action-unreachable, **When** `suggests` edges
   are authored from the directives its own scope names as its trigger (`DIRECTIVE_024`, `DIRECTIVE_025`),
   **Then** the reconciler becomes action-reachable.
3. **Given** `directive:USE_MUTATION_TESTING_TO_VALIDATE_TEST_QUALITY` is action-unreachable, **When** a
   `suggests` edge is authored from the test-quality-gate directive (`DIRECTIVE_030`) it deepens, **Then**
   the mutation directive and its workflow family become action-reachable.
4. **Given** three profile-run procedures (`spike-timebox-policy`, `glossary-maintenance-workflow`,
   `meeting-minutes-pipeline`) are unreachable, **When** a `requires` edge is authored from each owning
   agent profile that declares it runs that procedure, **Then** each procedure becomes profile-channel
   reachable (so charter-cascade over the profile reaches it).

---

### User Story 3 - The residual is curated honestly and the tickets close (Priority: P3)

A future maintainer opening #3009 or #1923 needs the residual-orphan record to be *true*: which artifacts
are genuinely activation/runtime-only (kept with an explicit exemption note), which were retired, and which
are now wired. This story truthfully updates the residual documentation, enrolls the honest residuals with
exemption notes, retires the stale entry, and closes both tickets — with no valid artifact deleted and no
edge manufactured to game a metric.

**Why this priority**: Closure and honesty. It has no code-behavior effect on its own, but it prevents the
next agent from re-litigating settled decisions or "fixing" residuals that are correct-by-design.

**Independent Test**: The residual doc's set matches the graph's true residual; the retired entry is
absent from disk and graph; each honest residual carries a rationale; and the ticket-closure references
are present.

**Acceptance Scenarios**:

1. **Given** `toolguide:rtk-search-tooling` no longer exists on disk or in the graph, **When** the residual
   doc is updated, **Then** its row is removed with a retirement note citing the removal commit.
2. **Given** the honest activation/runtime-only reachability residuals (e.g. `directive:DIRECTIVE_035`,
   `directive:DIRECTIVE_039`, `procedure:migrate-project-guidance-to-spec-kitty-charter`,
   `styleguide:deployable-skill-authoring`, `paradigm:atomic-design`), **When** they are enrolled, **Then**
   each carries an explicit "reachable by charter-activation/runtime only, by design" rationale. (Note:
   `agent_profile:human-in-charge` is a profile seed / traversal root — it is an **incidence** (#1923)
   residual, not a reachability residual, and is recorded only under the incidence metric.)
3. **Given** the full pinned residual (`_ACTION_UNREACHABLE_SHIPPED`, 75 members), **When** the curation is
   complete, **Then** every member has a disposition — per-node for the 34 both-channel-dead, group-level for
   the 41 profile-delivered — so no member rides along unexamined behind a green pin.

### Edge Cases

- A node is non-orphan by incidence (has outbound edges) but reachable from no channel — the incidence
  guard passes while the reachability guard must fail; the two metrics are complementary, not redundant.
- An inbound edge originates from a source that is *itself* unreachable (an inert edge) — it de-orphans by
  incidence but does not confer reachability; the reachability metric must not be fooled by it.
- Wiring one directive cascades reachability to a whole tactic family — the pinned membership set must move
  by all affected nodes, each with a ledger row, not just the directly-wired node.
- A residual orphan superficially "pairs" with another (e.g. a directive and its workflow tactic) but
  neither is the canonical referent of the other — wiring a reciprocal edge would be circular metric-
  gaming and is prohibited.
- The reachability depth parameter (steady-state vs bootstrap) changes which nodes are reached via the
  depth-gated `suggests` leg; the metric and any moved pins must be explicit about which depth they assert.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Reachability companion guard | As a doctrine maintainer, I want a guard that pins the membership set of activatable nodes reachable from no action root (the #3009 "reachable from actions" measure), partitioned into a both-channel-dead subset and a by-design profile-delivered subset, so that "activated doctrine that cascades to nothing" is a visible, named, fully-enumerated condition rather than a hidden count. | High | Open |
| FR-002 | Guard names the URN on regression | As a doctrine maintainer, I want the reachability guard's failure to name the specific offending URN(s), so that a regression is diagnosable by identity, not by a shifted count. | High | Open |
| FR-003 | Guard uses canonical reachability helpers | As a doctrine maintainer, I want the companion metric computed via the canonical `action_channel_reachable` / `profile_channel_reachable` helpers, so that it cannot drift from the resolver's real traversal semantics. | High | Open |
| FR-004 | Wire DISCIPLINED_REFACTORING | As an implementer, I want `directive:DISCIPLINED_REFACTORING` reached from the action-reachable `procedure:refactoring` that selects Fowler tactics, so that activating disciplined-refactoring doctrine actually surfaces it (and its tactic family) during implement/review. | High | Open |
| FR-005 | Wire RECONCILE_CHANGE_SCOPE_TENSIONS | As an implementer, I want `directive:RECONCILE_CHANGE_SCOPE_TENSIONS` reached from `DIRECTIVE_024`/`DIRECTIVE_025` (which its own scope names as its trigger), so that the reconciler is action-reachable. | High | Open |
| FR-006 | Wire USE_MUTATION_TESTING | As an implementer, I want `directive:USE_MUTATION_TESTING_TO_VALIDATE_TEST_QUALITY` reached from the test-quality-gate directive `DIRECTIVE_030` it deepens, so that the mutation-testing family is action-reachable. | Medium | Open |
| FR-007 | Wire profile-run procedures | As a doctrine maintainer, I want `procedure:spike-timebox-policy`, `procedure:glossary-maintenance-workflow`, and `procedure:meeting-minutes-pipeline` reached from the agent profiles that declare they run them, so that activating those profiles cascades to the procedures. | Medium | Open |
| FR-008 | Enroll honest residuals with exemption notes | As a future maintainer, I want each genuinely activation/runtime-only residual enrolled with an explicit exemption rationale, so that a correct-by-design residual is not mistaken for a defect. | Medium | Open |
| FR-009 | Truthful residual documentation | As a future maintainer, I want the #1923 residual doc to reflect the true current residual (retired entry removed, wired entries promoted, honest residuals justified), so that the record is trustworthy. | Medium | Open |
| FR-010 | Delta-accounting ledger rows | As a reviewer, I want every golden-constant/pin move to carry a composition-ledger row naming the responsible edge, so that a pin change is auditable against its cause and cannot be silently green-washed. | High | Open |
| FR-011 | Close #3009 and #1923 | As the operator, I want this mission to close #3009 and #1923 with evidence, so that the long-standing orphan-metric and curation tickets are resolved. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Genuine-edge-only (no metric-gaming) | 100% of authored edges cite the source/target artifact text that establishes the relationship; zero edges exist whose sole justification is shrinking a metric (auditable against the wiring-table ledger). | Integrity | High | Open |
| NFR-002 | No valid-artifact deletion | Zero valid, deliberately-authored artifacts are deleted to shrink any metric; only artifacts already retired on disk are recorded as retired. | Integrity | High | Open |
| NFR-003 | Guard determinism | The reachability companion guard produces an identical membership set across repeated runs on an unchanged graph (no ordering or nondeterminism), verified by the guard being a pure function of the loaded graph. | Reliability | High | Open |
| NFR-004 | Ledger-vs-diff coverage | Every membership-set or pin move in the diff has a matching wiring-table ledger row; a pin move with no ledger row fails review even if the assertion is green. | Auditability | High | Open |
| NFR-005 | Existing guards stay green | All existing DRG orphan/reachability guards (`test_extractor_projection`, `test_reachability`, `test_doctrine_regenerate_graph`) pass, with any moved pins ratcheted in the correct direction (incidence and reachability residuals only shrink or hold). | Reliability | High | Open |
| NFR-006 | Zero lint/type regressions | `ruff` and `mypy` report zero new issues on all touched files; no new suppressions added. | Quality | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Curation policy D-C2 / C-003 | An orphan is unreferenced, not defective: it is wired only when a genuine referent exists, else documented as a residual; never deleted to shrink a metric, never given a manufactured edge. | Doctrine | High | Open |
| C-002 | Canonical authoring sites | Curated remedy edges are authored in the operator-blessed `_CURATED_ARTIFACT_EDGES` table (or, for profile-run procedures, via the structured profile field if that projection is adopted); tension/lineage overlays are not repurposed for reachability edges. | Technical | High | Open |
| C-003 | Reachability-only-shrinks | The tracked `_ACTIVATED_BUT_ORPHANED` defect set and the reachability residual may only shrink or hold in this mission; no node may be added to a defect/residual set to make an assertion pass. | Doctrine | High | Open |
| C-004 | No B2 scope | The broader migration of 400+ inline `references:` into authored edges (mission B2) is out of scope; this mission delivers only the companion metric, the traced residual wiring, and the curation. | Scope | Medium | Open |
| C-005 | Ratchet the incidence ceiling | Where the incidence residual shrinks, the documented ceiling constant is lowered to match (no leftover slack that would re-hide a new orphan). | Technical | Medium | Open |

### Key Entities

- **DRG node**: A doctrine artifact identified by a URN (`<kind>:<id>`). Kinds include directive, tactic,
  styleguide, toolguide, procedure, paradigm, agent_profile, action, mission_type, mission_step_contract,
  asset, glossary_pack, template, anti_pattern.
- **DRG edge**: A directed, typed relationship between nodes (`requires`, `suggests`, `scope`,
  `vocabulary`, `specializes_from`, and others). Edges are projected from artifact reference fields or
  authored in the curated-edges table / overlay.
- **Reachability channel**: A traversal entry vector — the *action channel* (from action roots via
  `scope → requires/suggests`) and the *profile channel* (from agent-profile roots via `requires` /
  `specializes_from`). A node reached by neither is "cascades to nothing."
- **Incidence orphan**: A node incident to zero edges (the metric #3009 critiques as insufficient).
- **Reachability residual**: An activatable node reachable from no channel (the metric #3009 asks for).
- **Composition-ledger row**: An auditable record, in the wiring-table doc, naming the edge responsible
  for a membership-set or pin move.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reachability companion guard exists whose failure names the offending URN(s); removing any
  one genuine inbound edge from a currently-reachable activated node causes a named failure (demonstrated).
- **SC-002**: The action-only whole-graph unreachable set (`_ACTION_UNREACHABLE_SHIPPED`) shrinks from 88 to
  75 — the three wired directives plus their cascaded tactic/toolguide families leave — and its both-channel
  "dead doctrine" subset shrinks from 38 to 34 (RECONCILE_CHANGE_SCOPE_TENSIONS + three profile-run
  procedures leave). The activated-only action pins shrink via the cascaded **activated tactics** (the
  `refactoring-*` family + mutation-testing-workflow), not the directives themselves (which are not
  activated). Every move is backed by a composition-ledger row, with no node added to any residual/defect set.
- **SC-003**: 100% of authored edges are traceable to the source/target artifact text that establishes the
  relationship; an independent review confirms zero metric-gamed edges.
- **SC-004**: The #1923 residual doc matches the graph's true residual (retired entry removed, 6 promoted,
  honest residuals justified); #3009 and #1923 are closed with evidence.
- **SC-005**: All existing DRG guards and the full `ruff`/`mypy` gates pass with zero new issues; every
  moved pin is ratcheted in the correct (shrink/hold) direction.
