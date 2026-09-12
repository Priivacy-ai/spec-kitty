# Tasks: Rehome & Complete Writing-Comms Doctrine

**Mission**: `rehome-writing-comms-doctrine-01KZ9V0S` · **Branch**: `feat/rehome-writing-comms-doctrine`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

Decomposition is by **file ownership** (no two WPs share `owned_files`), because the mission is
mostly sequential passes over the same artifacts. Each type-WP relocates *and* reconciles its own
files; WP04 is the sequential tail (regenerate + gates) depending on the three content WPs.
Source content is on ref `pr-2918`.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Relocate 7 profiles + READMEs to packs/built-in/agent_profiles/ (preserve authorship) | WP01 | |
| T002 | Author shipped-profile contract fields (16 gaps: canonical-verbs, output-artifacts, mode-defaults, doctrine-layers) | WP01 | |
| T003 | Red-first routing regression on shipped profiles (DESIGNER + CURATOR incumbents win) | WP01 | |
| T004 | Narrow colliding primary roles (diagram-daisy, comms-cleo, synthesizer-sam) → routing green | WP01 | |
| T005 | diagram-daisy: strip false Directive-031 attribution + arch-ban; trim tool matrix to toolguide refs | WP01 | |
| T006 | minutes-maker-mahad: scope enforcement claims to agent discipline | WP01 | |
| T007 | lexical-larry: glossary-authority boundary (curator-carla owns; Larry diagnostic feeder) | WP01 | |
| T008 | Wire profile DRG frontmatter (context-sources.directives / tactic-references) | WP01 | |
| T009 | Relocate directives 047-050 to packs/built-in/directives/ (preserve authorship) | WP02 | [P] |
| T010 | Directive 047: repoint references to writing-audience-catalog; drop stakeholder refs | WP02 | |
| T011 | Directive 048: add cross-ref boundary to DIRECTIVE_018 | WP02 | |
| T012 | Directive 049: narrow "must self-declare" to advisory language | WP02 | |
| T013 | Directive 050: re-anchor on connector-side injection / pre-redaction / least-privilege | WP02 | |
| T014 | Relocate procedures/styleguides/tactic + invert asset nesting to packs/built-in/assets/audiences/ | WP03 | [P] |
| T015 | meeting-minutes-pipeline: state trust-boundary requirements as doctrine | WP03 | |
| T016 | meeting-minutes-pipeline: scope enforcement claims (no unshipped schema/validator/publisher) | WP03 | |
| T017 | glossary-maintenance-workflow: confirm composer of existing tactics (no duplicate authority) | WP03 | |
| T018 | writing-audience-catalog tactic: keep type:asset ref pointed at relocated assets | WP03 | |
| T019 | professional-communications + meeting-minutes-format styleguides: relocate + confirm refs shape | WP03 | |
| T020 | Run doctrine regenerate-graph; commit fragments; regenerate-graph --check exit 0 | WP04 | |
| T021 | test_pack_relocation_doctor_gate: EXPECTED_PROFILE_COUNT 18→25; recompute (node,edge) tuple | WP04 | |
| T022 | test_shipped_profiles: add 7 ids to EXPECTED_PROFILE_IDS | WP04 | |
| T023 | test_reachability: recompute frozensets empirically; ledger row only if a pin moves | WP04 | |
| T024 | Validation sweep: pack validate + doctor doctrine 25/25 + terminology guard; capture evidence | WP04 | |

---

## WP01 — Writing-comms agent profiles: relocate, complete, narrow, reconcile, wire

- **Goal**: Land the 7 profiles on the canonical surface, complete their shipped-profile contract, preserve legacy routing, remove the profile-level over-claims/false-attributions, and wire their DRG edges.
- **Priority**: P1 (foundational + routing-safety)
- **Independent test**: shipped-profile gate green for the 7; red-first routing regression RED→GREEN; `spec-kitty doctrine validate` clean on the 7.
- **Subtasks**: T001–T008
- **Dependencies**: none
- **Prompt**: [tasks/WP01-agent-profiles.md](./tasks/WP01-agent-profiles.md) (~450 lines)
- **Requirements**: FR-001, FR-002, FR-003, FR-005, FR-006, FR-007, FR-010, FR-011; NFR-002

## WP02 — Writing-comms directives (047–050): relocate & reconcile

- **Goal**: Land 047-050 and reconcile their content — repoint 047, boundary 048↔018, narrow 049 to advisory, re-anchor 050 on prevention.
- **Priority**: P2
- **Independent test**: `doctrine validate` clean on 047-050; manual review confirms each blocker disposition (research D-06 §3,4,5c).
- **Subtasks**: T009–T013
- **Dependencies**: none
- **Prompt**: [tasks/WP02-directives.md](./tasks/WP02-directives.md) (~300 lines)
- **Requirements**: FR-001, FR-008, FR-009, FR-010

## WP03 — Procedures, styleguides, tactic & audience assets: relocate & reconcile

- **Goal**: Land the procedures/styleguides/tactic and invert the audience assets; state the meeting-minutes trust boundaries and scope the pipeline's enforcement claims; keep the glossary workflow a composer.
- **Priority**: P2
- **Independent test**: `doctrine validate` clean; the `type: asset` tactic reference resolves; manual review confirms trust-boundary statements + no unshipped-enforcement claims.
- **Subtasks**: T014–T019
- **Dependencies**: none
- **Prompt**: [tasks/WP03-procedures-styleguides-tactic-assets.md](./tasks/WP03-procedures-styleguides-tactic-assets.md) (~350 lines)
- **Requirements**: FR-001, FR-007, FR-010

## WP04 — DRG regeneration, pinned-gate refresh & validation sweep

- **Goal**: Regenerate the DRG fragments from the final frontmatter, refresh the pinned counts, and prove the whole set validates clean with no orphans.
- **Priority**: P1 (the landing gate)
- **Independent test**: `regenerate-graph --check` exit 0; the three doctrine gates + terminology guard green; `doctor doctrine` healthy 25/25, 0 skipped, 0 orphans.
- **Subtasks**: T020–T024
- **Dependencies**: WP01, WP02, WP03
- **Prompt**: [tasks/WP04-drg-regen-and-gates.md](./tasks/WP04-drg-regen-and-gates.md) (~300 lines)
- **Requirements**: FR-003, FR-004; NFR-001, NFR-003

---

## Sequencing & parallelism

- **Parallel:** WP01, WP02, WP03 have disjoint `owned_files` and no dependencies — they run concurrently in separate lanes.
- **Sequential tail:** WP04 depends on all three (DRG regeneration and pinned counts settle only after every artifact's frontmatter is final).
- **MVP:** WP01 (on-surface, contract-complete, routing-safe profiles) is the highest-value slice.

## Cross-WP notes

- **Attribution (FR-011):** every relocation commit (T001, T009, T014) carries a
  `Co-Authored-By:` trailer for the original contributor; the PR body credits them. Applied in
  each content WP; WP01 is the requirement anchor.
- **FR-007 spans two WPs:** the minutes-maker-mahad *profile* claims are scoped in WP01 (T006);
  the meeting-minutes-*pipeline* claims + trust boundaries are in WP03 (T015, T016). Keep the two
  edits consistent.
- **047–050 reachability depends on WP01's wiring (cross-lane, priti-H1):** directives 047–050
  are NOT charter-activation kinds, so their ONLY inbound `requires` DRG edges come from the
  profile `context-sources.directives` entries WP01/T008 declares (comms-cleo→047,
  lexical-larry→048, minutes-maker-mahad→049/050, etc.). Those target ids are minted in the
  parallel WP02/WP03 lanes, so they will NOT resolve on WP01's lane in isolation — WP01 must
  **declare them anyway and must not prune them**; cross-artifact resolution + the no-orphan
  check happen at WP04 integration. If WP01 prunes them, 047–050 orphan at the WP04 gate.
- **Tiered rigour:** WP01 carries executable red-first routing coverage; WP02/WP03 content
  reconciliations are prose-honesty edits verified by `doctrine validate` + reviewer confirmation
  against research D-06 (no unit test fakeable for prose). WP04 is the executable landing gate.
