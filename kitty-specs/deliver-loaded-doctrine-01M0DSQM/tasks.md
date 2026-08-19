# Tasks: Deliver Loaded Doctrine to the Agent (M4)

**Mission**: deliver-loaded-doctrine-01M0DSQM | **Branch**: `m4-doctrine-delivery`
**Planning base**: `m4-doctrine-delivery` | **Merge target**: `m4-doctrine-delivery`

Three file-disjoint work packages run as parallel lanes (a/b/c) with **no inter-dependencies**. Each carries its own red-first tests (prove red on `upstream/main` first — C-003) and its own totality/ledger guard. ruff + mypy --strict, zero new suppressions (C-002). `charter` must not import `specify_cli` (C-001). NFR-001 token budget respected throughout.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first: glossary delivers to a slot + every None delivery-table row has a stated reason | WP01 | |
| T002 | Give GLOSSARY_PACK a real `glossary_packs` slot; add stated reason to ANTI_PATTERN (close the None-reason class) | WP01 | |
| T003 | Add `glossary_pack_ids` to `_ActionDoctrineBundle`, populate from the slot map | WP01 | |
| T004 | Glossary render row/helper: term-name surface list + `--include glossary-pack:<id>` pointer (names-only, NFR-001) | WP01 | |
| T005 | Red-first: procedure/tactic step `description` renders in bundle body + profile inline body | WP01 | |
| T006 | Render step `description` in `artifact_bodies` + `profile_sections`; byte-identical when absent | WP01 | |
| T007 | Document styleguide/toolguide pointer-only as intentional (stated reason + schema/doc note); no behaviour change | WP01 | |
| T008 | Red-first: project-overlay profile at `.kittify/agent_profiles` visible via activation-aware service (un-carve the 3 tests) | WP02 | [P] |
| T009 | `DoctrineService` gains `agent_profile_overlay_dir`; `agent_profiles` honours it, else `_project_dir` | WP02 | [P] |
| T010 | Thread `agent_profile_overlay_dir` through both builders + public builder (default None byte-identical; single-wrapper-body) | WP02 | [P] |
| T011 | Migrate `default_profile_repository` onto the factory+overlay; delete carve-out; preserve C-008 org merge | WP02 | [P] |
| T012 | Verify byte-identical builder when overlay unset (test) + mypy --strict | WP02 | [P] |
| T013 | Red-first: `context --json` ships typed `procedures[]` + schema 1.1.0 + `procedures` in ledger; asset reference-only | WP03 | [P] |
| T014 | `_ARRAY_BY_KIND` add `"procedure": "procedures"` | WP03 | [P] |
| T015 | `context.py`: move procedure from `extra_delivered` to `repos_by_kind`; asset stays reference-only | WP03 | [P] |
| T016 | `context_contract.py`: bump `CONTEXT_SCHEMA_VERSION` 1.0.0→1.1.0 + add `"procedures"` to ledger + document asset asymmetry | WP03 | [P] |

## Work Packages

### WP01 — Delivery-table & render family (lane-a)

**Goal**: Close the action-bundle delivery/render no-ops — glossary reaches the agent (names-only + pointer), every `None` delivery-table row carries a stated reason, procedure/tactic step `description` renders, and the styleguide/toolguide pointer-only choice is documented as intentional.
**Priority**: P1 (US1, US2). **Closes**: #3489, #3488(render half); FR-001..FR-005, FR-011(glossary org), NFR-001, NFR-003.
**Independent test**: activate a graph-reachable glossary pack → term surfaces appear under action doctrine with a `--include glossary-pack:<id>` pointer; a procedure step's `description` renders alongside its `title`; the totality guard confirms zero unexplained `None` rows.
**Included subtasks**: T001, T002, T003, T004, T005, T006, T007.
**Dependencies**: none.
**Risks**: totality tests redden until slot + render row land together (that is the guard working — land T002+T004 in the same change); glossary render must stay names-only (NFR-001).
**Prompt**: [tasks/WP01-delivery-table-render-family.md](tasks/WP01-delivery-table-render-family.md) (~7 subtasks, ~420 lines)

### WP02 — Builder overlay seam (#3176) (lane-b)

**Goal**: Thread an optional `agent_profile_overlay_dir` through the doctrine-service builders and `DoctrineService`, default None (byte-identical unset), so `.kittify/agent_profiles` is reachable; migrate `default_profile_repository` onto it and delete the carve-out.
**Priority**: P1 (US3). **Closes**: #3176; FR-006, FR-007, NFR-002.
**Independent test**: a profile authored at `.kittify/agent_profiles/<id>.agent.yaml` is visible through the activation-aware service; the three carved-out projection tests pass; unset-overlay builder is byte-identical.
**Included subtasks**: T008, T009, T010, T011, T012.
**Dependencies**: none.
**Risks**: must preserve the single-wrapper-body invariant (C-006) and the C-008 org-merge gate; `charter` must not import `specify_cli` (C-001).
**Prompt**: [tasks/WP02-builder-overlay-seam.md](tasks/WP02-builder-overlay-seam.md) (~5 subtasks, ~340 lines)

### WP03 — procedures[] JSON contract (#3389) (lane-c)

**Goal**: Promote `procedure` to the fifth typed array in `context --json`, keep `asset` reference-only (stated in contract), and bump `CONTEXT_SCHEMA_VERSION` + ledger atomically.
**Priority**: P2 (US4). **Closes**: #3389; FR-008, FR-009, FR-010, FR-011(procedures org).
**Independent test**: `charter context --action <a> --json` includes a typed `procedures[]` under `context_schema_version` 1.1.0, with no `assets` typed array and `procedures` in the ledger.
**Included subtasks**: T013, T014, T015, T016.
**Dependencies**: none.
**Risks**: versioned-contract change — the schema bump + ledger update must be atomic with the array promotion (C-005); must not reshape any other top-level key (C-C4).
**Prompt**: [tasks/WP03-procedures-json-contract.md](tasks/WP03-procedures-json-contract.md) (~4 subtasks, ~260 lines)

## MVP / sequencing

All three WPs are independent and can run fully in parallel (lanes a/b/c). WP01 is the highest-value slice (closes the headline #3489 silent-loss defect). Consolidation review runs a squad on the combined diff before the PR to `main`.
