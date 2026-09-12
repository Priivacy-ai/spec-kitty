# Mission Specification: Doctrine DRG Silent-Drop Boundary Fix

**Mission Branch**: `fix/doctrine-drg-silent-drop-boundary`
**Created**: 2026-08-23
**Status**: Draft
**Input**: Research brief `docs/plans/investigations/2026-08-declared-but-inert-doctrine-seams.md`; scope = GitHub #3608 + #3629 + verify-and-close #3530.

## Problem Statement

Doctrine/DRG artifacts are authored, schema-legitimized, and validated — and then
silently never take effect at runtime, because the boundary between *declaration*
and *consumption* is neither derived-from-a-single-source, nor fail-loud, nor
test-pinned. A governance author gets a green result over an inert artifact: no
exception, no diagnostic, no delivery. This mission closes three concrete
instances of that failure and pins the boundary so it cannot silently reopen.

- **#3608** — `_DRG_NODE_KINDS` (`src/charter/synthesizer/topic_resolver.py:37`)
  is a hand-copied subset of the canonical `NodeKind` enum
  (`src/doctrine/drg/models.py`). It has drifted 6 kinds
  (`anti_pattern`, `asset`, `glossary`, `glossary_pack`,
  `mission_step_contract`, `template`), so legitimate DRG-URN selectors such as
  `glossary_pack:<id>` silently fall through the resolution tier at
  `topic_resolver.py:236` and never resolve. No drift-guard test exists.
- **#3629** — three follow-ups from the M2 DRG-projection squad:
  (1) `ContextSources.{tactics, toolguides, styleguides, doctrine-layers,
  additional}` (`src/doctrine/agent_profiles/profile.py`) are declared and
  schema-legitimized but never reach a delivery path — only
  `context-sources.directives` is projected (`extractor.py:920-921`). A research
  squad (see `research/context-sources-drg-projection.md`) established that
  `context-sources.*` is a **redundant, mostly-inert second surface**: the
  renderer that delivers profile text to a dispatched agent reads the top-level
  `*-references` fields (the canonical, rationale-bearing, DRG-provisioned
  surface), not `context-sources.*`. Resolved direction (DM-01M0PEAQ5G1VDR3CSJSV51SD8Y):
  **consolidate on `*-references` and remove `context-sources.*`**.
  (2) `extract_governance_profile_scope_edges` (`extractor.py:1336`) minted
  `scope` edges from bare ids with no existence check. **Already fixed on `main`**
  by commit `d8beee2761` — `assert_governance_scope_edges_resolve`
  (`extractor.py:1406`, wired at `:1574`, tested at
  `test_extractor.py:1608-1653`) now fails loud on an unresolved selection. This
  mission **verifies** the fix (incl. any org-tier gap) and closes the item; it
  does not re-implement it.
  (3) a doc-nit on golden re-ledger wording (`extractor.py:557`).
- **#3530** — a tracking issue whose 7 of 8 direct members are now closed and
  whose chain-merge fix landed (`merge.py:1122` iterates all fragments). Its
  closing condition (a *chain* of org packs delivers *every* declared kind, and a
  misconfigured pack fails loud) needs execution-level verification. Per operator
  direction the fixture is the repo's own `packs/internal/` (spec-kitty-internal)
  org pack. Grounding that fixture surfaced a **new instance of the same family**:
  `load_validated_graph`'s `org_roots=` seam (`_drg_helpers.py:138-182`) never
  reads `drg/fragment.yaml` and suppresses the "no graph" warning when one exists,
  so the executor and `action_doctrine_bundle` callers silently drop the internal
  pack's doctrine (`test_executor.py:878-916` documents the degrade). This mission
  fixes that seam and verifies chain delivery on the real pack.

**Milestone 3.2.x (#4):** advances G1 (deepen Doctrine/Charter/DRG runtime
impact), G2 (strangle core domains onto canonical SSOTs — no hand-copied
authorities), and the "no new shadow paths" principle. Related fail-loud epic:
#3410. Whack-a-copy family: #3562, #3461, #3427.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - DRG-URN selectors for every canonical kind resolve (Priority: P1)

A doctrine/charter author writes a selector that references a legitimate DRG node
kind — for example `glossary_pack:my-terms` or `mission_step_contract:plan-review`
— in a synthesizable artifact. Today, because the resolver's kind set is a
hand-copied subset that has drifted, the URN silently fails to resolve as a DRG
node and falls through with no error. After this mission, every kind the
canonical `NodeKind` enum defines is recognized by the resolver, and a
newly-added enum member is recognized automatically without a second hand-edit.

**Why this priority**: This is the highest-leverage, lowest-risk fix (a single
SSOT derivation + a pin), it directly restores currently-broken resolution for
`glossary_pack`/`mission_step_contract`/etc., and it prevents the next drift. It
is the archetype of the whole mission's thesis.

**Independent Test**: With `_DRG_NODE_KINDS` derived from `NodeKind`, assert the
resolver recognizes a `glossary_pack:<id>` URN as a DRG node kind (previously
returned `None`), and run a drift-guard test asserting the recognized set equals
`{k.value for k in NodeKind}`.

**Acceptance Scenarios**:

1. **Given** the canonical `NodeKind` enum defines 16 kinds, **When** the
   resolver evaluates the set of DRG node kinds it recognizes, **Then** the set
   equals exactly `{k.value for k in NodeKind}` (no missing kinds, no extras).
2. **Given** a selector `glossary_pack:<id>`, **When** the DRG-URN resolution
   tier at `topic_resolver.py` evaluates it, **Then** the left-hand side is
   recognized as a known DRG node kind (it is no longer silently rejected at the
   membership gate).
3. **Given** a hypothetical new member added to `NodeKind`, **When** the
   drift-guard test runs, **Then** it passes without any edit to
   `topic_resolver.py` (derivation, not a guarded copy).

---

### User Story 2 - A mistyped governance-profile selection fails loud, on both tiers (Priority: P2)

A mission-type author writes a `governance-profile.yaml` that selects doctrine by
bare id (e.g. `selected_directives`, `selected_tactics`). If they typo an id or
reference a nonexistent artifact, the selection must be reported loudly rather
than silently pruned — whether the profile ships in the built-in pack or an org
pack. **Built-in tier**: this already landed on `main` (commit `d8beee2761`) —
`assert_governance_scope_edges_resolve` raises naming each unresolved `selected_*`,
wired into `generate_graph`; this mission adds the missing end-to-end test that
pins that wiring (the shipped tests use synthetic edges). **Org tier** (research
finding): there is **no governance-profile scope path at all** today — an org-tier
`selected_*` typo is unread *and* unguarded (a total no-op). This mission
**implements** the net-new org-tier extraction + post-merge fail-loud guard.

**Why this priority**: The built-in half is a regression pin; the org-tier half is
**net-new implementation** (not "verify") — the squad reclassified it (F9), and the
operator chose to build it now rather than defer. Both halves share the mission's
fail-loud thesis.

**Independent Test**: Run the existing regression
(`test_extractor.py:1608-1653`); additionally construct an **org-tier**
`governance-profile.yaml` with a nonexistent selection and assert it also fails
loud (or document the gap and add the guard).

**Acceptance Scenarios**:

1. **Given** a built-in `governance-profile.yaml` selecting a nonexistent id,
   **When** the DRG is generated, **Then** `assert_governance_scope_edges_resolve`
   raises naming the offending id (confirmed already true).
2. **Given** an **org-tier** `governance-profile.yaml` selecting a nonexistent id,
   **When** doctrine is loaded/merged, **Then** it fails loud too (verify; close
   the gap if the guard does not cover the org path).

---

### User Story 3 - Profile references live on one canonical surface (Priority: P1)

A profile author writes `context-sources.tactics` (6 profiles do) or
`context-sources.additional` (16 profiles do), reasonably expecting that content
to reach a dispatched agent — the schema legitimizes it. It does not: the
renderer delivers from the top-level `*-references` surface, and `context-sources.*`
is a redundant, mostly-inert duplicate (research: `research/context-sources-drg-projection.md`).
After this mission there is **one** canonical profile-reference surface — the
top-level `*-references` fields — and `context-sources.*` is removed. Authored
tactic/toolguide/styleguide intent is preserved by migrating it onto the
`*-references` surface (which the extractor projects to DRG edges and the renderer
delivers); the non-artefact fields (`additional` free-text, `doctrine-layers`
layer-names) are removed outright as they have no edge/delivery shape.

**Why this priority**: This is the most authored-against instance of the
silent-drop family (25 shipped profiles carry inert `context-sources.*`), and
resolving it removes a whole duplicated authority surface (G2).

**Independent Test**: After the mission, assert (a) `context-sources` is no longer
a valid profile field (schema rejects it / migration removed it); (b) each shipped
profile's previously-authored tactic/toolguide/styleguide intent is present on the
`*-references` surface and reaches a dispatched agent via the profile DRG channel;
(c) no profile-reference kind remains simultaneously schema-legal and never-read.

**Acceptance Scenarios**:

1. **Given** a profile that authored `context-sources.tactics: [t1]` before
   migration, **When** the migration runs, **Then** `t1` appears under
   `tactic-references` and is delivered to a dispatched agent (via the existing
   profile DRG channel), with no `context-sources` block remaining.
2. **Given** any profile after the mission, **When** it authors a `context-sources`
   block, **Then** the loader rejects it (the field no longer exists) — it is not
   silently accepted-and-ignored.
3. **Given** the 25 shipped profiles, **When** the mission completes, **Then**
   0 of them carry `context-sources.*`, and their directive/tactic/toolguide/
   styleguide references are all on the `*-references` surface.
4. **Given** `additional` / `doctrine-layers` content (no artefact/edge shape),
   **When** the migration runs, **Then** those fields are removed (not silently
   retained as dead fields).

---

### User Story 4 - The spec-kitty-internal pack's doctrine reaches every consumer seam (Priority: P1)

The repository's own **spec-kitty-internal** org pack (`packs/internal/`) is the
#3530 verification fixture — the real dogfooded org pack, not a synthetic one.
Research established the pack **already conforms** to current org-tier conventions
(plural node kinds are canonical; `drg/fragment.yaml` is the required shape;
`pack.yaml`/`pack-manifest.yaml` are deferred for org packs; the validator runs
green). What "updating it to current conventions" actually surfaces is a
**branch-aligned silent-drop bug**: `load_validated_graph`'s `org_roots=` seam
(`src/charter/_drg_helpers.py:138-182`) reads only root `*.graph.yaml`, **never
reads `drg/fragment.yaml`, and suppresses the "no graph" warning when a fragment
exists** (`:174`). Two production callers pass only `org_roots=`
(`mission_step_contracts/executor.py:362`, `charter/action_doctrine_bundle.py:192`),
so the internal pack's entire doctrine is silently dropped on those seams — an
existing test (`test_executor.py:878-916`) even documents the degrade. After this
mission, every seam that consumes org doctrine folds `drg/fragment.yaml` (or the
warning is honest), and the built-in + internal chain delivers every declared kind
to every consumer — closing #3530 with evidence on the real pack.

**Why this priority**: This is a live silent-drop bug on the exact family the
mission targets (declared-and-conformant, validates green, reaches no consumer via
the executor/action-bundle seam), it is the reason the dogfooded pack's doctrine
does not take effect, and it is what makes the #3530 chain verification meaningful.

**Independent Test**: Register `packs/internal/` as an org pack over built-in and
drive the executor / action-doctrine-bundle path; assert every kind it declares
(glossary pack, procedure, directive, DRG nodes + `refines` edges to built-in)
reaches that consumer (currently dropped); and that a deliberately-misconfigured
variant fails loud rather than degrading silently.

**Acceptance Scenarios**:

1. **Given** the internal pack registered as an org tier, **When** the executor /
   `action_doctrine_bundle` path (`org_roots=` seam) loads doctrine, **Then** the
   pack's `drg/fragment.yaml` nodes and edges are folded (not silently dropped),
   or a missing fragment produces an honest warning (no false suppression).
2. **Given** the built-in + spec-kitty-internal chain (≥2 layers), **When**
   doctrine is loaded/merged/activated across all consumer seams, **Then** every
   kind declared by the internal pack (not only built-in's) reaches its consumer,
   including its DRG nodes and `refines` edges.
3. **Given** a deliberately-misconfigured variant of the internal pack, **When**
   doctrine is loaded, **Then** the misconfiguration is reported loudly instead of
   counted as success.
4. **Given** the verification suite passes, **When** #3530's closing condition is
   evaluated, **Then** it is met (leaving only the explicitly-non-child #3412
   open).

### Edge Cases

- A `NodeKind` member exists whose URN prefix differs from its value — the
  derivation must key on the canonical value used at the resolution membership
  gate, matching how URNs are parsed.
- `context-sources.additional` is freeform (not an artifact-kind reference) and
  `doctrine-layers` may be a layer selector rather than an artifact id — the
  resolved direction must treat non-artifact-reference kinds differently from
  artifact-reference kinds (do not mint a dangling edge for a freeform value).
- A governance-profile selection that is valid but points at an artifact from a
  not-yet-loaded org pack — the fail-loud guard must not false-positive on
  legitimately-deferred cross-pack references (align with existing extractor
  posture; scope the check to genuinely unresolvable ids).
- The drift-guard test must fail if the copy grows *extra* kinds too, not only if
  it shrinks (exact set equality, both directions).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Derive DRG node-kind set from `NodeKind` | As a doctrine author, I want the resolver's recognized DRG node kinds derived from the canonical `NodeKind` enum so that no kind is silently unrecognized. | High | Open |
| FR-002 | Drift-guard test (behaviour-pinned) | As a maintainer, I want a drift-guard that pins the membership-gate **behaviour** — a monkeypatched/extra `NodeKind` member is recognized without editing `topic_resolver.py` — so future drift fails loudly in CI. (NOT literal set-equality, which is a post-derive tautology.) | High | Open |
| FR-003 | `glossary_pack`/`mission_step_contract`/etc. URNs resolve | As a charter author, I want previously-dropped DRG-URN kinds recognized at the resolution tier so that legitimate selectors no longer fall through silently. | High | Open |
| FR-004 | Remove `context-sources.*` from model + schema | As a profile author, I want the redundant `context-sources` block removed from `ContextSources`, `AgentContextSources`, and `agent-profile.schema.yaml` so that there is one canonical profile-reference surface. | High | Open |
| FR-005 | Migrate authored refs onto `*-references` (set-merge, no loss) | As a maintainer, I want a migration that set-merges (not appends) authored `directives`/`tactics`/`toolguides`/`styleguides` from `context-sources.*` onto `*-references`, and **deliberately re-homes** `additional` bindings that carry meaning (e.g. reviewer-renata's `adversarial-evidence-disposition`, pinned by a supply-chain test) rather than dropping them, so no authored intent is lost. | High | Open |
| FR-006 | Update 25 shipped profiles + all `context-sources` consumers | As a maintainer, I want the 25 `packs/built-in/agent_profiles/*.agent.yaml` profiles migrated AND every `context-sources` consumer updated (`agent_profiles/__init__.py` `__all__`, `scripts/generate_schemas.py`, `scripts/doctrine/inline_reference_inventory.py`, and the asserting tests) so removal breaks nothing silently. | High | Open |
| FR-007 | Extractor projects agent_profile edges from `*-references`; regenerate golden + reconcile overlay | As a doctrine consumer, I want the extractor to project `agent_profile` edges from `*-references`, the golden `agent_profile.graph.yaml` regenerated, and `hand_authored_overlay.py` reconciled (incl. the deliberate python-pedro/DIRECTIVE_034 delivery decision) with a composition-ledger entry, so migrated references reach a dispatched agent with an auditable graph. | High | Open |
| FR-008 | Close #3629 p2 (built-in e2e) AND implement org-tier fail-loud | As a mission-type author, I want (a) an end-to-end `generate_graph` test pinning the built-in `assert_governance_scope_edges_resolve` guard, and (b) **net-new** org-tier governance-profile scope extraction + fail-loud guard + tests (no org-tier path exists today), so a nonexistent selection fails loud on both tiers. | Medium | Open |
| FR-009 | Fix the org fragment silent-drop at the two deficient callers | As a doctrine consumer, I want `executor.py:362` and `action_doctrine_bundle.py:192` to thread `org_fragments=load_org_drg(repo_root, strict=False)` (mirroring the 4 callers that already do) so an org pack's `drg/fragment.yaml` reaches those consumers. **Fix at the callers, not the `org_roots=` seam** (a seam fix double-folds for the dual-callers and mis-tiers org content). | High | Open |
| FR-010 | Refresh `packs/internal/` README | As a maintainer, I want the internal pack's stale README updated (it omits the on-disk `directives/` dir + `OPERATOR_SIGNAL_CONTRACT` node); the pack is already structurally conformant, so no restructure. | Low | Open |
| FR-011 | Chain delivery verification (class-b internal + class-a 2nd fixture) | As an operator, I want tests proving (b) built-in + spec-kitty-internal delivers every kind the internal pack declares across the executor/action-bundle seam, AND (a) built-in + internal + a **2nd minimal org fixture** folds pack #2's fragment node/edge (the multi-org-pack path), so #3530 is evidenced for both classes. | Medium | Open |
| FR-012 | Misconfigured-pack-in-chain fails loud (enumerated) | As an operator, I want enumerated misconfig cases (nonexistent refine target; missing required fragment key; declared kind with no node) each to **raise** with a target-naming message (distinct from the honest "no graph" warning) so the chain never reports success over an inert pack. | Medium | Open |
| FR-013 | Golden re-ledger doc-nit correction | As a maintainer, I want the extractor procedure-branch docstring wording on golden re-ledger (`extractor.py:557`) clarified so that it matches the M2 WP04 reality. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No new suppressions | Zero new `# noqa`, `# type: ignore`, or per-file ignore additions; new code passes `ruff` and `mypy` with zero issues. | Maintainability | High | Open |
| NFR-002 | Test coverage for every new branch | Every new helper/branch (derivation, fail-loud guard, projection/removal, chain verification) has a focused test in the same work package. | Reliability | High | Open |
| NFR-003 | Terminology guard green | `pytest tests/architectural/test_no_legacy_terminology.py` passes (Mission-not-Feature, canonical terms) before push. | Compliance | Medium | Open |
| NFR-004 | Complexity ceiling | Touched functions remain at cyclomatic complexity ≤15 (ruff C901 / Sonar S3776). | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Single source of truth | The resolver's DRG node-kind set MUST be derived from `NodeKind`, not a hand-maintained copy (G2; no new shadow authority). | Technical | High | Open |
| C-002 | Fail-loud over silent-prune | Boundary failures (unknown kind, nonexistent selection, misconfigured pack) MUST surface as an error/diagnostic, never a silent drop or a success count. | Technical | High | Open |
| C-003 | No silent fallback | Any new resolution/validation path MUST fail closed with a structured error on ambiguity or absence — no silent fallback (repo doctrine). | Technical | High | Open |
| C-004 | Consolidate on `*-references` | The resolved direction (DM-01M0PEAQ5G1VDR3CSJSV51SD8Y) is to remove `context-sources.*` and consolidate on the top-level `*-references` surface; no authored artefact-reference intent may be lost in migration. | Process | High | Resolved |
| C-005 | Schema change requires migration | Removing `context-sources.*` MUST be accompanied by a migration and MUST update all 25 shipped profiles; a profile authoring the removed block MUST be rejected, not silently ignored. | Technical | High | Open |
| C-006 | No silent behaviour change to delivered content | Consolidation MUST preserve what reaches a dispatched agent today, verified by an **empty golden `agent_profile.graph.yaml` diff** except deliberately-ledgered deltas. The one known delta — python-pedro/DIRECTIVE_034 (overlay `suggests` link suppressed once 034 becomes a requires-diamond) — MUST be resolved deliberately and ledgered, never silent. | Technical | High | Open |
| C-007 | #3514 and #3511 out of scope | The P0 test-authority gap (#3514) and the pack-metadata integration cutover (#3511) are NOT in this mission's scope. #3412 (malformed-manifest → None) also stays out and open. | Scope | Medium | Open |

### Key Entities *(include if feature involves data)*

- **NodeKind**: the canonical enum of DRG node kinds; the single source of truth
  the resolver's recognized set must derive from.
- **DRG URN**: a `<kind>:<id>` selector whose `<kind>` is gated against the
  recognized node-kind set at the resolution tier.
- **ContextSources**: the agent-profile block declaring reference channels
  (`directives`, `tactics`, `toolguides`, `styleguides`, `doctrine-layers`,
  `additional`); today only `directives` is projected.
- **DRG edge / Relation**: the canonical projection mechanism (e.g.
  `agent_profile --REQUIRES--> directive`) that carries authored intent to the
  consumer; candidate replacement for the inert context-sources fields.
- **Governance-profile selection**: a mission-type's `selected_*` bare-id lists
  that mint `scope` edges; the fail-loud guard target.
- **Org doctrine pack chain**: an ordered set of doctrine layers (here
  `packs/built-in/` layer 0 + `packs/internal/` org layer) whose every declared
  kind must reach its consumer; #3530's bug used to drop edges past the first.
- **spec-kitty-internal pack** (`packs/internal/`): the repository's own dogfooded
  org-tier pack; the #3530 verification fixture, to be updated to the latest
  structural conventions first (FR-009).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The set of DRG node kinds recognized by the resolver equals the
  canonical enum exactly (16 of 16 kinds; 0 missing, 0 extra), verified by a
  drift-guard test that fails on any future divergence.
- **SC-002**: 100% of previously-dropped DRG-URN kinds
  (`anti_pattern`, `asset`, `glossary`, `glossary_pack`,
  `mission_step_contract`, `template`) are recognized at the resolution tier
  after the fix (measured: 6 of 6 now resolve where 0 did).
- **SC-003**: A governance-profile selection naming a nonexistent artifact
  fails loud naming the offending id in 100% of cases on **both** the built-in
  tier (end-to-end `generate_graph` test) and the newly-implemented org tier;
  valid selections produce 0 new diagnostics (no false positives).
- **SC-004**: `context-sources` is removed entirely — 0 profile-reference kinds
  remain simultaneously schema-legal and never-read; all 25 shipped profiles
  carry references only on the `*-references` surface; 0 authored artefact
  references lost in migration.
- **SC-005**: (class-b) The spec-kitty-internal pack, loaded as an org tier over
  built-in, delivers 100% of the kinds it declares — **including the executor /
  action-doctrine-bundle seam that drops it today**; (class-a) a built-in +
  internal + 2nd-org-fixture chain folds pack #2's fragment node/edge; and
  enumerated misconfigurations fail loud — together satisfying #3530's closing
  condition.
- **SC-006**: 0 new lint/type suppressions introduced; touched functions remain
  at complexity ≤15.

## Assumptions

- The #3530 per-seam org-tier fixes and the chain-merge fix (`merge.py:1122`
  iterating all fragments) are already landed on `main`; this mission verifies and
  closes, it does not re-fix them.
- `#3412` (YAML-syntax-malformed manifest degrades to None) is explicitly *not* a
  child of #3530 and remains open after this mission.
- The `context-sources.*` direction is **resolved** (DM-01M0PEAQ5G1VDR3CSJSV51SD8Y,
  full consolidation on `*-references`) from a 3-agent research squad; findings
  recorded in `research/context-sources-drg-projection.md`.
- #3629 part 2 **built-in** guard is already fixed on `main` (commit `d8beee2761`)
  — this mission adds the end-to-end pin. The **org-tier** governance-profile
  fail-loud path is **net-new** (built here, not verified) — the #3629 close
  comment MUST disclose this (post-tasks G3); a follow-up issue may be filed for
  org-tier governance ergonomics beyond parity.
- Breaking change (context-sources removal) requires a CHANGELOG entry + version
  bump (DIR-009) and a next-unreleased migration name (`m_3_3_1_*`, since
  `m_3_2_6`…`m_3_3_0` already ship). Both are WP02 DoD items.
- Per operator direction, the #3530 chain verification uses the real
  `packs/internal/` (spec-kitty-internal) org pack as its fixture. Research
  established the pack is **already structurally conformant** (plural kinds +
  `drg/fragment.yaml` are the canonical org shape; `pack.yaml`/manifest deferred),
  so "update to current conventions" resolves to a README refresh (FR-010) plus
  the real code fix (FR-009, the `org_roots`-seam silent-drop). built-in + internal
  is the ≥2-layer chain. If a strict *multi-org-pack* chain (≥2 org packs) is
  needed to exercise the exact #3530 merge path, a second minimal org fixture may
  be added — resolved at plan time.
- This mission targets a draft PR to upstream; the operator merges.
