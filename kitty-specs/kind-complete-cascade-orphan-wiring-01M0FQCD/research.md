# Research: Kind-Complete Cascade + Orphan Wiring (M5)

Phase 0 output. All baselines measured on `upstream/main @ f82aa0ff8` (M1–M4 landed).

## Measured baselines

### B1 — Cascade from every built-in mission_type returns 0 (#2829)

Building the shipped DRG (`load_built_in_graph()`) and running
`cascade_activation_targets(graph, mission_type_urn, CascadeScope.all())`:

| mission_type | activated kinds | total ids |
|---|---|---|
| `mission_type:documentation` | [] | 0 |
| `mission_type:plan` | [] | 0 |
| `mission_type:research` | [] | 0 |
| `mission_type:software-dev` | [] | 0 |

Cause: `REFERENCE_RELATIONS = {requires, suggests, refines}`. `mission_type
--requires--> action:<id>/<step>`; the `action` node's outbound edges are `scope`
(e.g. `software-dev/implement` has 39 `scope` edges) and `instantiates` — neither
followed. The forward closure stops at the `action` node, which `_kind_of` drops
(action ∉ `ArtifactKind`), so nothing is returned.

### B2 — Adding {scope, instantiates} reaches governance + templates/assets

Forward closure from `mission_type:documentation` over
`REFERENCE_RELATIONS ∪ {scope, instantiates}` reaches: `tactic ×22`,
`directive ×7`, `styleguide ×2`, `template ×8`, `asset ×1` (+ `action ×7`,
dropped). So the fix delivers governance artifacts — but also reaches
non-charter-activatable `template`/`asset`.

### B3 — 137 sources already surface template/asset today

`_referenced_artifacts` yields `template:`/`asset:` for **137** existing cascade
sources (agent profiles, `DIRECTIVE_025`, …) via `requires`/`suggests`/`refines`.
The consumer (`activate.py:_render_cascade_activation`) writes an activation per
id; `template`/`asset` are not in `YAML_KEY_MAP` (derived from
`CHARTER_KIND_TOKENS`), so `CharterPackManager._require_kind` raises `ValueError`,
which `activate.py:320-325` catches and prints as a yellow
"could not cascade-activate template/<id>" warning. So non-activatable kinds in
cascade output is **pre-existing and tolerated** (noisy, not fatal). No existing
cascade test pins that behavior.

### B4 — Frontmatter promotion is lossless for the 4 orphans

`_relation_for_ref_type`: directive refs → `requires`, everything else →
`suggests`. All 4 targets are toolguide/styleguide → `suggests`, matching the
overlay. Directive references parse `when` (`extractor.py:739`) but not `reason`;
adding symmetric `reason=ref.get("reason")` (backward-compatible — no shipped ref
carries `reason`) makes promotion lossless (same triple + when + reason), so the
regenerated committed fragment stays byte-identical.

## Decision records

### D1 — Followed-relation set: add `scope` + `instantiates`; exclude the rest (ADR)

- **Decision**: `REFERENCE_RELATIONS` becomes
  `{requires, suggests, refines, scope, instantiates}`.
- **Rationale**: `scope` is the action→governance edge (165 edges) — the load-
  bearing #2829 fix. `instantiates` (action→template, 11 edges) is added so the
  action hop is complete and consistent with the ~137 sources that already reach
  templates; its non-activatable targets are handled by the candidate filter
  (D2), not by omitting the relation.
- **Excluded**: `vocabulary` (targets `glossary_scope`, a non-artifact node
  dropped by `_kind_of`; 0 edges; a leaf — provably inert for cascade; glossary
  scope is `resolve_context` step 4 / M4's concern). `applies` (dead — nothing
  traverses it), `replaces` (supersession), `delegates_to` (runtime handoff),
  `specializes_from` (lineage, resolved by the profile repo), `enhances`/
  `overrides` (pack overlay), `in_tension_with`/`reconciles_tension` (co-valid
  competitors, not references), `rejects` (points at anti-patterns). Following
  any would over-cascade.
- **Symmetry**: `REFERENCE_RELATIONS` feeds both activation and deactivation
  exclusivity; the expansion applies to both, and excluded relations stay
  excluded in both.
- **Alternatives**: (a) `scope` only — same activatable result once templates are
  filtered, but leaves the action hop half-followed and inconsistent with the
  137 template-reaching sources. (b) add `vocabulary` — provably inert; rejected
  for principled minimality. (c) no candidate filter — keeps the template/asset
  warning noise; rejected (see D2).

### D2 — Candidate filter: only propose `CHARTER_ACTIVATABLE_KINDS`

- **Decision**: `_referenced_artifacts` keeps only reached nodes whose kind ∈
  `doctrine.artifact_kinds.CHARTER_ACTIVATABLE_KINDS` (all kinds minus `template`,
  `asset`).
- **Rationale**: This is the "kind-complete" half. Widening reach surfaces
  templates (via `instantiates`) and assets (via requires/suggests chains);
  without the filter, activating a mission type would emit a flood of misleading
  "could not cascade-activate" warnings. The filter reuses the single canonical
  authority (no re-declared exclusion list — NFR-002) and is not a per-specific-
  kind branch. It also removes the pre-existing B3 noise for the 137 sources.
- **Blast radius**: no existing cascade test pins template/asset in output (B3),
  so the change is corrective, low-risk.
- **Alternative**: filter only in `cascade_activation_targets` (leaves the no-
  cascade warning + deactivation still surfacing template/asset). Rejected —
  `_referenced_artifacts` is the shared seam; filtering there fixes all three
  consumers consistently.

### D3 — Orphan dispositions

- **Promote 4 to frontmatter** (single-authority, lossless per B4):
  - `DIRECTIVE_034 --suggests--> styleguide:given-when-then-authoring`
  - `DIRECTIVE_034 --suggests--> toolguide:gherkin`
  - `DIRECTIVE_030 --suggests--> toolguide:sonar`
  - `DIRECTIVE_041 --suggests--> styleguide:quadruple-a-test-format`
  Each mirrors an existing `directive → styleguide/toolguide suggests` pattern in
  the shipped graph (C-003) — a relationship already blessed as an overlay edge,
  now moved to its single canonical home. Shipped edge set unchanged → reachability
  pins do not move.
- **`styleguide:deployable-skill-authoring` → direct-activation-only.** No
  defensible source: the onboarding procedure mentions "skill" zero times and the
  styleguide is a distribution-surface concern, not a pack-authoring one. It has
  no inbound edge anywhere (not even in the overlay). Recorded in a new, small,
  documented direct-activation-only disposition with this rationale — never given
  a guessed edge (C-003).
- **Alternative**: minimal (only dispose the source-less one, leave 4 overlay-
  resolved). Rejected by operator — leaves the pure-graph orphan debt carrying 4
  entries that have a defensible single-authority home.

### D4 — Single golden re-ledger (C-001)

- The cascade change (D1/D2) moves **no** extractor/reachability golden count:
  those measure `resolve_context` (action channel) + profile channel + the graph
  edge set, not cascade `REFERENCE_RELATIONS`. It is validated by new cascade
  tests only.
- The orphan change (D3) moves: `_ACTIVATED_BUT_ORPHANED` −5,
  `_ORPHANS_RESOLVED_BY_OVERLAY` −4 (the 4 leave overlay-resolution for
  frontmatter), and introduces the direct-activation-only disposition for the 5th.
  The shipped edge set is unchanged (promotions are lossless; overlay removed but
  frontmatter adds the identical edge), so `_SHIPPED_ORPHANS` and the reachability
  pins (`_ACTION_UNREACHABLE_*`, `_PROFILE_UNREACHABLE`, `_PROFILE_RESCUES`) do not
  move for the 4. Every move is traced to one edge/relation cause; the re-ledger
  is applied once, in IC-02.

## Discovered during implementation — `mission_type:plan` scopes no governance

After the traversal fix, three of the four built-in mission types cascade to
governance (measured activatable ids: documentation 31, research 23, software-dev
160; baseline all 0). `mission_type:plan` still cascades to **empty** — not
because the #2829 dead-end persists (the closure now correctly passes *through*
its action nodes) but because plan's step contracts author **no `scope` edges**:
`action:plan/plan` and `action:plan/specify` carry only `instantiates→template`,
and `action:plan/research` / `action:plan/review` carry no outbound edges at all.
Templates are correctly dropped at candidacy, so plan reaches nothing activatable.

This is a **graph-data property** (the plan step contracts govern nothing), not a
cascade-code defect, and authoring plan-step governance would (a) move golden
counts via new edges — violating "re-ledger once" — and (b) sit outside this
mission's cascade-traversal + orphan-wiring scope (it is mission-step-contract
authoring, adjacent to M3's operating-procedures domain). **Follow-up**: author
`scope` governance on the plan mission-type step contracts (separate mission /
issue). FR-002, SC-001, and contract C-CAS-1 were reworded to "governance-bearing"
mission types with plan documented as the measured exception; WP01 pins this with
`test_plan_cascade_is_empty_because_its_actions_scope_no_governance`.

## Supply-chain security

No dependency is added, upgraded, or removed. The `051-supply-chain-install-safety`
directive does not apply to this mission. (Recorded per the plan supply-chain step;
silence here is an examined "N/A", not an omission.)

## Adversarial evidence

No security-impacting dependency decision is made, so no supply-chain adversarial
pass is required. The design's contested points (relation-set membership; orphan
dispositions) were resolved with the operator before authoring (see spec + D1–D3);
an aggregate adversarial squad runs pre-merge per the charter close-out sequence.
