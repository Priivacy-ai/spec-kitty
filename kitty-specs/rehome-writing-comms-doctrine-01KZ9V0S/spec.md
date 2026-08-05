# Mission Specification: Rehome & Complete Writing-Comms Doctrine

**Mission Branch**: `feat/rehome-writing-comms-doctrine`
**Created**: 2026-08-05
**Status**: Draft
**Input**: Land community contribution PR #2918 ("The Magnificent 7" writing & communications built-in doctrine set) onto the current `packs/built-in/` doctrine surface, wired into the doctrine graph and reconciled against the two on-record adversarial-squad reviews.

## Context

PR #2918 contributes a self-contained writing / communications doctrine set: 7 agent
profiles (analyst-annie, comms-cleo, diagram-daisy, lexical-larry, minutes-maker-mahad,
scribe-sally, synthesizer-sam), 4 directives (047 audience-oriented-writing, 048
version-governance, 049 agent-declaration-and-self-introduction, 050
credential-handling-discipline), 2 styleguides (professional-communications,
meeting-minutes-format), 2 procedures (glossary-maintenance-workflow,
meeting-minutes-pipeline), 1 tactic (writing-audience-catalog), and 5 writing-audience
persona assets. The content is wanted. It cannot land as authored because it targets the
retired `src/doctrine/<type>/built-in/` layout (the built-in-doctrine consolidation,
keystone #2467, relocated everything to `packs/built-in/` at the repo root), and two
adversarial-squad reviews on the PR flagged routing, authority, and trust-boundary
problems that a straight rebase would not fix. This is therefore a **doctrine-authoring
mission** — YAML artifacts, hand-authored Doctrine-Relationship-Graph (DRG) fragments, and
doctrine-integrity tests — not a runtime-code mission. Original contributor authorship is
preserved.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The doctrine set lands on the current surface, loadable and wired (Priority: P1)

A maintainer lands the contribution. Every artifact resolves at its canonical
`packs/built-in/<type>/` path (assets under `packs/built-in/assets/audiences/`), loads
through the canonical doctrine loader without error, and is reachable in the
Doctrine-Relationship-Graph via hand-authored inbound edges — no orphan artifacts. The
doctrine-integrity gates recognise the enlarged set.

**Why this priority**: This is the foundational slice. Until the artifacts are at the
canonical paths and DRG-wired, they are silently dead files — the loader does not scan the
old tree, and an unwired artifact is reachable by nobody. Nothing else in the mission has
value until this holds.

**Independent Test**: Materialise all artifacts at the canonical paths, run
`spec-kitty doctrine validate` (expect 0 errors) and `spec-kitty doctor doctrine --json`
(expect healthy, 0 skipped profiles), and run the DRG reachability gate (expect every new
node reachable).

**Acceptance Scenarios**:

1. **Given** the contribution authored against `src/doctrine/*/built-in/`, **When** the mission relocates it, **Then** 0 files remain under any nested `*/built-in/` path and every artifact lives under `packs/built-in/<type>/`.
2. **Given** the relocated artifacts, **When** `spec-kitty doctrine validate` runs, **Then** it reports 0 errors across all new artifacts (including the tactic's `type: asset` reference, which the current `ArtifactKind` enum permits).
3. **Given** the hand-authored DRG fragments, **When** the reachability gate runs, **Then** each new node has at least one inbound `requires`/`suggests` edge and 0 new orphans are reported.
4. **Given** an edge whose endpoint is written in a non-canonical shape (e.g. `urn:profile:…`), **When** the DRG merges, **Then** the mission has already corrected it to a valid DRG URN (`<kind>:<id>`) or fragment-local bare id, so no edge is silently dropped.

---

### User Story 2 - Existing routing is preserved (Priority: P1)

An agent is dispatched for work that already has an incumbent specialist — generic
`designer`, `curator`, or `researcher` work. It still routes to the incumbent
(designer-dagmar, curator-carla, researcher-*), not to a newly-added writing/comms profile
that declared an overlapping generic role at a higher priority. The new profiles capture
only their intended narrow scope.

**Why this priority**: The reviews found this is a *structural* regression: with no
discriminating context signals, routing priority dominates, and diagram-daisy declares
generic role `designer` at priority 60 versus designer-dagmar at 50 (comms-cleo similarly
shadows generic curator/researcher work). Landing the set without narrowing these roles
silently steals dispatch from incumbents. A landed regression in routing is worse than a
deferred contribution.

**Independent Test**: Dispatch/route-resolve for each contested generic role with no
discriminating context and assert the incumbent specialist is selected; the regression
tests are RED if the new profiles are added with their authored priorities and GREEN after
the narrowing fix.

**Acceptance Scenarios**:

1. **Given** a dispatch for generic `designer` work with no discriminating context, **When** routing resolves, **Then** designer-dagmar is selected, not diagram-daisy.
2. **Given** a dispatch for generic `curator`/`researcher` work, **When** routing resolves, **Then** the incumbent specialist is selected, not comms-cleo.
3. **Given** a dispatch that genuinely matches a new profile's narrow scope (e.g. diagram-as-code from a written brief), **When** routing resolves, **Then** the new profile is selected.

---

### User Story 3 - The doctrine is honest and non-contradictory (Priority: P2)

A maintainer reads any new artifact and finds no claim of enforcement that does not ship,
no attribution of policy to a directive that does not contain it, and no authority that
silently competes with existing doctrine. Where the new set overlaps an existing authority,
there is either one authority or an explicit, non-contradictory boundary.

**Why this priority**: The reviews found the content over-claims and conflicts: diagram-daisy
attributes a global architecture-representation ban to Directive 031 (which contains no such
policy); minutes-maker-mahad claims schema validation / publishing enforcement with no
shipped schema/validator/publisher; Directive 050 handles credentials post-exposure;
Directive 049 says specialists "must" self-declare but is advisory and 6/7 profiles omit the
declaration; and lexical-larry / glossary-maintenance / version-governance / diagram-daisy /
the writing-audience concept overlap existing glossary, terminology, diagram, and
stakeholder-persona authorities. Doctrine that lies or contradicts itself is a liability
even when loadable.

**Independent Test**: Review each flagged blocker against the reconciled artifact and confirm
the over-claim/false-attribution/authority-conflict is gone; where the fix is doctrine prose,
confirm the requirement is stated (not merely implied) and no shipped-enforcement claim
remains.

**Acceptance Scenarios**:

1. **Given** diagram-daisy, **When** read, **Then** it makes no architecture-representation prohibition attributed to Directive 031 (the false attribution is removed, or the policy is moved to explicitly-scoped, separately-reviewed org doctrine — not built-in).
2. **Given** the meeting-minutes procedure, **When** read, **Then** it states its trust-boundary requirements (consent, retention, prompt-injection handling, least-privilege credentials, approval preview) as doctrine, and minutes-maker-mahad claims no enforcement (schema/validator/publisher) that does not ship.
3. **Given** Directive 050, **When** read, **Then** credential handling prefers connector-side injection / pre-model redaction / least privilege over post-exposure stripping.
4. **Given** Directive 049 and the 7 profiles, **When** read together, **Then** the "must self-declare" claim and the profiles' declarations agree (either the declaration is wired into all 7, or the directive's claim is narrowed to match its advisory status).
5. **Given** any overlapping authority (glossary/terminology/version, diagram toolguides, writing-audience vs stakeholder-persona), **When** read, **Then** there is one authority or an explicit boundary, and Directive 047's references do not contradict the writing-audience README's stated separation.

---

### User Story 4 - Contributor authorship is preserved (Priority: P3)

The original contributor's authorship survives the re-home. The landed history and/or a
provenance note credit the original author; the maintainer rework is additive, not a
wholesale re-attribution.

**Why this priority**: This stays a wanted community contribution; the hold was about
*where the surface is*, not the value. Preserving attribution is a courtesy and a
correctness matter, but it does not gate the doctrine's function, so it is P3.

**Independent Test**: Inspect the landed commit history / provenance for the original
author's attribution alongside the maintainer rework.

**Acceptance Scenarios**:

1. **Given** the landed PR, **When** its history is inspected, **Then** the original contributor's authorship is preserved (co-authorship, provenance note, or preserved authored commits).

### Edge Cases

- A relocated artifact is left at the old `src/doctrine/*/built-in/` path → the loader (which scans only `packs/built-in`) treats it as a silently-dead file and `tests/doctrine/test_shipped_profiles.py` goes red on the set-equality assertion. The mission must relocate, not copy.
- A DRG edge endpoint is written in a shape the vocabulary does not recognise (`urn:profile:…`) → the bridge drops it in silence and the artifact is orphaned. Endpoints must be valid DRG URNs (`<kind>:<id>`) or fragment-local bare ids.
- Asset nesting is left category-above-pack (`assets/audiences/built-in/`) rather than the canonical pack-above-category (`packs/built-in/assets/audiences/`) → assets are not scanned.
- Directive numbers 047-050 have been claimed upstream since authoring → renumber the files, their `id:` fields, and every cross-reference (verified free on current main; re-verify at implement).
- Narrowing a new profile's generic role too far → it no longer routes even for its intended narrow scope (guard with a positive routing test alongside the negative regression).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Relocate all artifacts to canonical paths | As a maintainer, I want all 30 contributed files moved to `packs/built-in/<type>/` (assets to `packs/built-in/assets/audiences/`, dropping every nested `built-in/` segment) so the loader can find them. | High | Open |
| FR-002 | Artifacts load and validate | As a maintainer, I want every relocated artifact to load through the canonical loader and pass `spec-kitty doctrine validate` with 0 errors so nothing is a dead file. | High | Open |
| FR-003 | DRG wiring — no orphans | As a maintainer, I want every new artifact to declare the frontmatter references that mint inbound `requires`/`suggests` DRG edges (profile reachability via `context-sources.directives`/`tactic-references`), and the per-kind `packs/built-in/<kind>.graph.yaml` fragments regenerated (`spec-kitty doctrine regenerate-graph`) so nothing is orphan and the `--check` freshness gate passes. | High | Open |
| FR-004 | Refresh pinned-count gates | As a maintainer, I want the pinned-count doctrine-integrity gates (`test_pack_relocation_doctor_gate.py`, `tests/doctrine/drg/test_reachability.py`, `tests/doctrine/test_shipped_profiles.py`) updated to the enlarged set so they gate the real inventory. | High | Open |
| FR-005 | Preserve legacy routing | As an operator, I want the new profiles' generic-role priorities narrowed (or given discriminating specialization context) so existing dispatch to incumbent specialists (designer-dagmar, curator-carla, researcher-*) is preserved, with routing regression tests. | High | Open |
| FR-006 | Remove false Directive-031 attribution | As a maintainer, I want diagram-daisy's architecture-representation ban falsely attributed to Directive 031 removed (or moved to explicitly-scoped org doctrine) so no built-in artifact invents global policy. | High | Open |
| FR-007 | Honest meeting-minutes trust boundaries | As a maintainer, I want the meeting-minutes procedure to state its trust-boundary requirements (consent, retention, prompt-injection handling, least-privilege, approval preview) as doctrine and minutes-maker-mahad's enforcement claims scoped to what ships. | Medium | Open |
| FR-008 | Reconcile Directive 050 credential handling | As a maintainer, I want Directive 050 to prefer connector-side injection / pre-model redaction / least privilege over post-exposure stripping. | Medium | Open |
| FR-009 | Reconcile Directive 049 self-declaration | As a maintainer, I want Directive 049's "must self-declare" claim and the 7 profiles' declarations reconciled (wire the declaration into all 7, or narrow the directive to its advisory status). | Medium | Open |
| FR-010 | Resolve authority overlaps | As a maintainer, I want the SSOT/authority overlaps resolved to one authority or an explicit boundary (glossary/terminology/version vs existing doctrine; diagram-daisy vs mermaid/plantuml toolguides; writing-audience vs stakeholder-persona, incl. Directive 047's references). | Medium | Open |
| FR-011 | Preserve contributor authorship | As the project, I want the original contributor's authorship preserved in the landed history/provenance. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero orphans | DRG reachability gate reports 0 new orphan nodes and `spec-kitty doctor doctrine --json` reports 0 skipped profiles. | Integrity | High | Open |
| NFR-002 | Routing regression coverage | Each *reproducing* contested role — designer and curator (researcher verified non-colliding, research D-03: it is a secondary role) — has a negative routing regression test (incumbent preserved) AND a positive test (new profile still routes for its narrow scope), asserted against the shipped profiles; a positive researcher-incumbent assertion documents the non-collision; 100% of pre-existing routing assertions still pass. | Reliability | High | Open |
| NFR-003 | Validation clean | `spec-kitty doctrine validate` reports 0 errors across all new artifacts; the targeted `tests/doctrine/` suite passes locally. | Correctness | High | Open |
| NFR-004 | Scoped test surface | Per-WP validation targets the directories bounding the change (`tests/doctrine/`, routing tests); the full suite is deferred to CI per charter Testing Requirements. | Process | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical surface only | All artifacts live under `packs/built-in/`; the retired `src/doctrine/*/built-in/` tree must not be reintroduced. | Technical | High | Open |
| C-002 | Generated DRG, freshness-gated | Built-in DRG fragments are GENERATED by `spec-kitty doctrine regenerate-graph` from artifact frontmatter (+ a small hand overlay for tension/reject edges), and must pass `regenerate-graph --check`. Profile→directive edges mint only from `context-sources.directives`/`tactic-references`, not the display-only `directive-references` field. The `urn:profile:`-shape endpoint hazard applies to hand-authored org-pack fragments (`_resolve_edge_endpoint`), not the generated built-in layer. | Technical | High | Open |
| C-003 | Doctrine, not runtime | This mission delivers doctrine artifacts + DRG wiring + integrity tests only. It does not build a meeting-minutes runtime, validator, or publisher; trust-boundary and credential requirements are expressed as doctrine. Any executable enforcement is an out-of-scope follow-up. | Technical | High | Open |
| C-004 | No greenwashing; terminology canon | Resolve root causes, not relabels (assets stay assets); obey the Terminology Canon (Mission not Feature) and pass `tests/architectural/test_no_legacy_terminology.py`. | Governance | High | Open |
| C-005 | PR-only; operator merges | Land via a PR to `main`; agents never merge to protected main — the operator merges. | Governance | High | Open |
| C-006 | Directive numbering | 047-050 verified free on current main; re-verify at implement and, if collided, renumber the files, their `id:` fields, and all cross-references. | Technical | Medium | Open |

### Key Entities

- **Agent Profile**: A routable specialist persona (`packs/built-in/agent_profiles/<id>.agent.yaml`) with role/priority/specialization signals that drive dispatch routing.
- **Directive / Styleguide / Procedure / Tactic**: Governance artifacts (`packs/built-in/<type>/…`) carrying binding or advisory rules, formats, workflows, and techniques.
- **Audience Asset**: A writing-audience persona (`packs/built-in/assets/audiences/<name>.md` + `.asset.yaml` sidecar) consumed by the writing-audience tactic.
- **DRG node / edge / per-kind graph fragment**: The reachability wiring (`packs/built-in/<kind>.graph.yaml`); a node with no inbound edge is an orphan.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 21 schema-checkable artifacts + 5 assets (with sidecars) + READMEs land under `packs/built-in/`; 0 files remain under any nested `*/built-in/` path.
- **SC-002**: `spec-kitty doctrine validate` reports 21/21 OK; `spec-kitty doctor doctrine --json` reports healthy with 0 skipped profiles.
- **SC-003**: DRG reachability gate reports 100% of the new nodes reachable (0 new orphans).
- **SC-004**: For each *reproducing* contested role — designer and curator (researcher verified non-colliding per research D-03) — a no-discriminating-context dispatch routes to the incumbent specialist, asserted against the **shipped** profiles — proven by a routing regression test that was RED with the profiles added naively and GREEN after the narrowing fix, with the pre-narrowing RED run captured as committed evidence.
- **SC-005**: 0 new doctrine artifacts claim enforcement, or attribute policy, that does not ship (each of the flagged blockers reconciled and re-reviewed).
- **SC-006**: The targeted `tests/doctrine/` and routing suites are green locally; the full suite is green on CI before the operator merges.
