# Implementation Plan: Rehome & Complete Writing-Comms Doctrine

**Branch**: `feat/rehome-writing-comms-doctrine` | **Date**: 2026-08-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/rehome-writing-comms-doctrine-01KZ9V0S/spec.md`

## Summary

Land community contribution PR #2918 ("The Magnificent 7" writing & communications
doctrine set) onto the current `packs/built-in/` doctrine surface and reconcile the two
on-record adversarial-squad reviews. This is a **doctrine-authoring mission**: it moves 30
YAML/markdown artifacts to canonical paths, hand-authors Doctrine-Relationship-Graph (DRG)
nodes + inbound edges so nothing is orphan, refreshes the pinned doctrine-integrity gates,
and reconciles content/authority/trust blockers (routing regressions, false attributions,
over-claimed enforcement, credential handling, authority overlaps) — closing each blocker
in doctrine, not by building new runtime. Contributor authorship is preserved; the change
lands via a PR to `main` that the operator merges.

Technical approach and per-concern decomposition are grounded in Phase 0 research
([research.md](./research.md), decisions D-01…D-06).

## Technical Context

**Language/Version**: Python 3.11+ (doctrine tooling) with YAML/Markdown doctrine artifacts
**Primary Dependencies**: spec-kitty doctrine toolchain — DRG merge/reachability (`src/doctrine/drg/`), doctrine loader (`packs/built-in` resolver), `spec-kitty doctrine validate`, `spec-kitty doctor doctrine`, dispatch router (`src/specify_cli/invocation/router.py`, `src/doctrine/model_task_routing/`)
**Storage**: Version-controlled files — `packs/built-in/<type>/*.yaml`, per-kind `packs/built-in/<kind>.graph.yaml` fragments, `packs/built-in/assets/audiences/*`
**Testing**: pytest doctrine-integrity gates (`tests/doctrine/` incl. `drg/test_reachability.py`, `test_pack_relocation_doctor_gate.py`, `test_shipped_profiles.py`) + routing regression tests; ATDD red-first per WP; targeted surface only (full suite deferred to CI per charter Testing Requirements)
**Target Platform**: spec-kitty CLI doctrine layer (cross-platform)
**Project Type**: single (doctrine content + graph fragments + tests inside the CLI repo)
**Performance Goals**: N/A — content mission; no runtime perf surface (doctrine load stays well under CLI <2s budget)
**Constraints**: Canonical `packs/built-in/` surface only (retired `src/doctrine/*/built-in/` must not return); DRG edges hand-authored with canonical endpoint shapes (`<kind>:<id>` or fragment-local bare id — no `urn:profile:` shapes, extractor retired #2950); doctrine-only (no meeting-minutes runtime/validator/publisher built here); no greenwashing (assets stay assets); Terminology Canon enforced; PR-only to main, operator merges
**Scale/Scope**: 30 files relocated; 7 profiles + 4 directives + 2 styleguides + 2 procedures + 1 tactic + 5 assets DRG-wired; ~3 pinned gates refreshed; routing regressions for 3 contested roles; 6 content/authority/trust blockers reconciled

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** (Governing Principle; DIRECTIVE_044): CENTRAL to this mission — FR-010 resolves each authority overlap to one authority or an explicit, non-contradictory boundary; no second glossary/terminology/diagram/persona authority is introduced. ✅ aligned.
- **Architectural alignment** (DIRECTIVE_001): artifacts land on the declared canonical surface (`packs/built-in/`) via the real loader + DRG model; no surface is worked around. ✅ aligned.
- **ATDD-first / red-first** (C-011, DIRECTIVE_041/034): the routing regressions and each refreshed gate are pinned RED on the planning base and GREEN on the WP tip; no retry-to-green. ✅ planned.
- **Canonical sources, no improvise** (DIRECTIVE_044): DRG fragments authored in the canonical per-kind `graph.yaml`; no extractor resurrection; no relabel of assets→templates (no greenwashing). ✅ aligned.
- **Terminology canon**: run `tests/architectural/test_no_legacy_terminology.py`; new prose obeys Mission-not-Feature. ✅ planned.
- **Git/workflow discipline** (DIRECTIVE_045): PR-only to `main`; operator merges; contributor authorship preserved. ✅ aligned.
- **No version numbers in scope** (specify/plan governance): directive *numbers* 047-050 are doctrine identifiers, not release versions — permitted; no release/version assignment in this mission. ✅ aligned.

No violations → Complexity Tracking not required.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.

  If multiple developers/agents will work on this mission, add an "Implementation
  Concern Map" section below to decompose architectural intent into IC-## concerns
  before generating tasks.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]
**Testing**: [Project-specific test approach or NEEDS CLARIFICATION]
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [single/web/mobile - determines source structure]
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on charter file]

## Project Structure

### Documentation (this mission)

```
kitty-specs/[###-mission]/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

Target surface for the relocated + wired artifacts (canonical `packs/built-in/`, pack-above-category):

```
packs/built-in/
├── agent_profiles/
│   ├── analyst-annie.agent.yaml          # relocated from src/doctrine/agent_profiles/built-in/
│   ├── comms-cleo.agent.yaml             #   (routing narrowed — FR-005)
│   ├── diagram-daisy.agent.yaml          #   (routing narrowed + false-attribution removed — FR-005/006)
│   ├── lexical-larry.agent.yaml          #   (authority boundary — FR-010)
│   ├── minutes-maker-mahad.agent.yaml    #   (enforcement claims scoped — FR-007)
│   ├── scribe-sally.agent.yaml
│   └── synthesizer-sam.agent.yaml
├── directives/
│   ├── 047-audience-oriented-writing.directive.yaml    # (persona-ref boundary — FR-010)
│   ├── 048-version-governance.directive.yaml
│   ├── 049-agent-declaration-and-self-introduction.directive.yaml  # (must-vs-advisory — FR-009)
│   └── 050-credential-handling-discipline.directive.yaml           # (connector-side/redaction — FR-008)
├── styleguides/
│   ├── professional-communications.styleguide.yaml
│   └── meeting-minutes-format.styleguide.yaml
├── procedures/
│   ├── glossary-maintenance-workflow.procedure.yaml
│   └── meeting-minutes-pipeline.procedure.yaml         # (trust boundaries stated — FR-007)
├── tactics/
│   └── writing-audience-catalog.tactic.yaml            # (type: asset ref — now enum-valid)
├── assets/audiences/                                    # inverted from assets/audiences/built-in/
│   ├── README.md
│   ├── software_engineer.md  (+ .asset.yaml)
│   ├── automation_agent.md   (+ .asset.yaml)
│   ├── agentic-framework-core-team.md (+ .asset.yaml)
│   ├── line_manager.md       (+ .asset.yaml)
│   └── nontech_educator.md   (+ .asset.yaml)
├── agent_profile.graph.yaml   # DRG fragments — hand-authored nodes + inbound edges (FR-003)
├── directive.graph.yaml       #   for every new artifact so nothing is orphan
├── styleguide.graph.yaml
├── procedure.graph.yaml
├── tactic.graph.yaml
└── asset.graph.yaml

tests/doctrine/                                   # pinned gates refreshed (FR-004) + red-first coverage
├── test_shipped_profiles.py                      #   set-equality + per-profile contract (7 new profiles)
├── test_pack_relocation_doctor_gate.py           #   profile/graph identity counts
└── drg/test_reachability.py                      #   reachability frozensets/counts
# + routing regression tests (FR-005) at the routing test entry point (located in Phase 0 research)
```

**Structure Decision**: Single-project doctrine content mission. All artifacts live under
`packs/built-in/<type>/` (assets under `packs/built-in/assets/audiences/`); reachability is
declared in the per-kind `packs/built-in/<kind>.graph.yaml` fragments; verification lives in
`tests/doctrine/` plus the routing test surface. No new runtime module is created — the
meeting-minutes trust boundaries and credential handling are expressed as doctrine (C-003).

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

*Include this section when the mission has multiple distinct architectural areas that inform how tasks are decomposed.*

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become
> multiple WPs; multiple small concerns may merge into one WP. Do not label concerns
> with WP-style IDs or sequencing language.

### IC-01 — Re-home & path relocation

- **Purpose**: Move all 30 contributed files onto the canonical surface so the loader can find them (the whole PR is misplaced post-#2467).
- **Relevant requirements**: FR-001; C-001
- **Affected surfaces**: `src/doctrine/*/built-in/*` → `packs/built-in/<type>/*`; assets → `packs/built-in/assets/audiences/*` (invert nesting); preserve the two READMEs the shipped-profiles gate checks (`packs/built-in/agent_profiles/README.md` + the package README)
- **Sequencing/depends-on**: none (foundational)
- **Risks**: A left-behind file at the old path is silently dead (loader scans only `packs/built-in`); relocation must be a move, not a copy. Preserve contributor authorship on these moves (see IC-07).

### IC-02 — Shipped-profile contract completion

- **Purpose**: Author the 16 missing frontmatter contract fields so all 7 profiles pass the shipped-profiles gate and load valid.
- **Relevant requirements**: FR-002; NFR-003 (partial)
- **Affected surfaces**: the 7 `packs/built-in/agent_profiles/*.agent.yaml` — add `collaboration.canonical-verbs` (all 7), `collaboration.output-artifacts` (diagram-daisy, scribe-sally), `mode-defaults`+`use-case` (scribe-sally), `context-sources.doctrine-layers` (all but synthesizer-sam), confirm `directive-references`
- **Sequencing/depends-on**: IC-01
- **Risks**: `canonical-verbs` interacts with routing (IC-03) — verbs must not re-introduce a generic-role collision; keep them domain-specific.

### IC-03 — Routing narrowing + red-first regression

- **Purpose**: Preserve legacy dispatch to incumbent specialists by narrowing the colliding profiles' primary role.
- **Relevant requirements**: FR-005; NFR-002; SC-004
- **Affected surfaces**: `roles[0]` on diagram-daisy (designer→diagram-author), comms-cleo (curator→communicator), synthesizer-sam (curator→synthesizer); new red-first tests in `tests/specify_cli/invocation/test_router.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: over-narrowing could stop a profile routing for its own scope — pair each negative regression with a positive route test. The RED-first assertion must fail on the base (profiles-added-naively) and pass after the narrowing.

### IC-04 — Content / authority / trust reconciliation

- **Purpose**: Make the doctrine honest and non-contradictory — remove over-claims/false attributions and resolve authority overlaps (research D-06).
- **Relevant requirements**: FR-006, FR-007, FR-008, FR-009, FR-010; SC-005; C-003
- **Affected surfaces**: diagram-daisy (strip 031 attribution + ban; trim tool matrix to toolguide refs), meeting-minutes-pipeline + minutes-maker-mahad (scope claims + state trust boundaries), 050 (connector-side/redaction), 049 (narrow to advisory), lexical-larry↔curator-carla boundary, 047 references (repoint to writing-audience-catalog), 048↔018 cross-ref
- **Sequencing/depends-on**: IC-01
- **Risks**: edits here change frontmatter `references`, so they must settle **before** IC-05 regenerates the graph. Changing curator-carla is touching an incumbent — keep it to an additive boundary line, no behavior change.

### IC-05 — DRG frontmatter wiring + regenerate

- **Purpose**: Ensure every new artifact is DRG-reachable (no orphans) by declaring edge-minting frontmatter, then regenerate the fragments.
- **Relevant requirements**: FR-003; NFR-001; C-002
- **Affected surfaces**: `context-sources.directives`/`tactic-references` on the 7 profiles; top-level `references:` on directives/procedures/tactic; regenerated `packs/built-in/<kind>.graph.yaml` fragments via `spec-kitty doctrine regenerate-graph`
- **Sequencing/depends-on**: IC-02, IC-04 (frontmatter references must be final)
- **Risks**: profile→directive edges mint only from `context-sources.directives`, NOT `directive-references` — a common trap. Must pass `regenerate-graph --check`. Don't hand-edit fragments.

### IC-06 — Pinned-gate refresh + validation sweep

- **Purpose**: Update the pinned doctrine-integrity gates to the enlarged set and prove the whole set validates clean.
- **Relevant requirements**: FR-004; NFR-001, NFR-003; SC-001, SC-002, SC-003, SC-006
- **Affected surfaces**: `test_pack_relocation_doctor_gate.py` (`EXPECTED_PROFILE_COUNT 18→25`; recompute `(324,892)`), `test_shipped_profiles.py` (`EXPECTED_PROFILE_IDS +7`), `tests/doctrine/drg/test_reachability.py` (recompute empirically; ledger row only if a pin moves); run `spec-kitty doctrine validate` + `doctor doctrine --json`
- **Sequencing/depends-on**: IC-05 (counts/edges settle only after regenerate)
- **Risks**: Do NOT pre-edit reachability frozensets speculatively; measure. Confirm the `type: asset` reference resolves end-to-end once assets are in place (research D-02).

### IC-07 — Contributor attribution preservation

- **Purpose**: Preserve zohar's authorship through the re-home.
- **Relevant requirements**: FR-011
- **Affected surfaces**: git history / provenance of the landed commits (co-authorship or preserved authored commits + a provenance note)
- **Sequencing/depends-on**: none (git strategy; applied at landing/wrap-up)
- **Risks**: A wholesale re-author erases the contribution credit — preserve it deliberately.
