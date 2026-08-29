---
work_package_id: WP01
title: ADR Authoring and Registration
dependencies: []
requirement_refs:
- C-001
- C-002
- C-003
- C-004
- C-005
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-011
- NFR-002
planning_base_branch: feat/retire-doctrine-term
merge_target_branch: feat/retire-doctrine-term
branch_strategy: Planning artifacts for this mission were generated on feat/retire-doctrine-term. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/retire-doctrine-term unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Canonical Authority
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: scribe-sally
authoritative_surface: docs/adr/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/implementation-baseline.json
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/implementation-baseline.json
- docs/adr/3.x/index.md
- docs/development/3-2-page-inventory.yaml
- docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md
- docs/adr/3.x/*-retire-doctrine-term-charter-is-the-canonical-vocabulary.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – ADR Authoring and Registration

## Start

Load `scribe-sally`; read `spec.md`, `plan.md`, `research.md`, `data-model.md`, all contracts,
`quickstart.md`, the Charter dependency graph, and review feedback. Before editing, fetch/check current
`origin/main` and atomically persist exact target + implementation base in owned
`implementation-baseline.json`. Do not execute product renames.

## Goal

Create/register one Accepted, self-sufficient ADR for complete current-tree terminology extinction. It
must record the operator override, M1 effectiveness, complete Charter owner workflow, M2 all-code
topology convergence, M3/M4 data-safe old-path extinction, M5 current-tree history rewrite outside the
immutable `kitty-specs/` archive, and M6 exact zero audits over `HEAD` with that single fixed exclusion.

## T001 — Author exact decision

Use `docs/architecture/adr-template.md` and next free actual-date sequence. Include every item in
`contracts/adr-content-contract.md`, especially:

- no internal/history/test/generated/metadata/current-tree exemption outside the fixed `kitty-specs/` root;
- the two fixed exclusions: Git object history outside `HEAD` and the immutable `kitty-specs/`
  historical-archive root (`DM-01M0NMS9WPH33EPFCJQRTQVNSA`) — no slug/directory/file under it is renamed or
  edited; archive referrers are recited by `mission_id`/mid8 or token-free path;
- narrow override superseding customization/path and historical-current-tree immutability without
  authorizing data loss/silent collision handling;
- the exact `contracts/adr-content-contract.md` owner table: direct governance/directives/overrides,
  activation only through activate/deactivate + shared engine, sanctioned lossless answers migration plus
  round-trip serializer hardening, generate-only YAML catalog/metadata, context-owned local cache,
  synthesis-owned manifest, and repeated zero-consumer proof plus deletion of obsolete writerless
  `.kittify/charter/graph.yml`; every no-hit artifact has a verified no-op;
- atomic glossary parity across `docs/context/doctrine.md` → `docs/context/charter.md`,
  `.kittify/glossaries/spec_kitty_core.yaml`, and
  `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml`; state that WP04 binds canonical
  `issue-matrix.json` #2727 into downstream M1 rather than requiring WP01 to consume a future output;
- old source tree convergence into collision-free `src/charter/` at M2;
- exact content/path audits with the fixed `:(exclude)kitty-specs/` pathspec / `kitty-specs/` drop,
  canonical row hashing, mandatory audit entrypoint/check marker, and numeric-byte negative tests at M6.

The ADR must state that `charter generate` never overwrites `charter.md`, does not own graph/context/
manifest/activation, that activation routes only through activate/deactivate + shared engine, that current
answers require the fixed lossless migration before hardened interview ownership, and that `charter sync`
is not a writer. M1 local decisions must be zero from this ADR.

## T002 — Prior ADR relationship

Update only the prior ADR status/pointer in this planning WP and preserve its resolution mechanics. Do not
claim its current-tree body/title/path is permanently immutable: the ADR must assign that file and every
other current-tree ADR/docs/archive/history artifact outside `kitty-specs/` to M5 rewrite/rename. Git
history and the `kitty-specs/` archive preserve prior bytes.

## T003 — Register

Run `python -m scripts.docs.freshen_adr_inventory`, then `--check`. The generated index and page inventory
must match the ADR filename/title. Hand edits to generated registration are forbidden.

## T004 — Self-sufficiency gate

An independent reader must answer the eight quickstart ADR questions without chat context. Reject:
user-visible/supported-only zero, X1/X2/X3, preserved old internal source topology, immutable current-tree
history outside `kitty-specs/`, any exclusion other than the fixed archive root, completed old paths,
runtime managed-path ledger architecture, or any M1 question.

## Done

ADR + registration + baseline committed on WP branch; checks recorded; planning-only diff maintained.

## Activity Log

Runtime-owned. Do not edit this prompt to record activity; use Spec Kitty task status/events.
