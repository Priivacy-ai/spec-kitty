---
work_package_id: WP01
title: ADR Authoring and Registration
dependencies: []
requirement_refs:
- C-002
- C-003
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

Run `spec-kitty agent profile show scribe-sally`, load that profile, then read `spec.md`, `plan.md`, `research.md`, `data-model.md`, both ADR/operator-map contracts, and `quickstart.md`. Check review feedback in mission status before editing.

## Goal

Create and register one self-sufficient ADR that fixes the vocabulary and compatibility contract. Supersede only the terminology portion of `2026-07-15-1`; preserve its resolution mechanics and body.

## T001 — Author ADR

Before any edit, run `git fetch origin main`, require
`git merge-base --is-ancestor origin/main HEAD`, then capture `git rev-parse origin/main` and
`git rev-parse HEAD`. Atomically persist both exact SHAs in owned `implementation-baseline.json` with
`target_ref: origin/main`, `target_tip`, `implementation_base`, UTC `captured_at`, `captured_by`,
`wp_id: WP01`, and both capture commands. Prove target is an ancestor of implementation base. This
durable snapshot binds WP01–WP05; later WPs do not refetch/repoint it. If a different target is
incorporated later, restart on a fresh branch from that target with only planning commits replayed.

Use `docs/architecture/adr-template.md` and the next free dated sequence. Set `status: Accepted`, use the actual creation date, and record deciders/reviewers; mandatory item 1 keeps product-vocabulary effectiveness conditional on M1/I1. The ADR must state all content-contract items, including:

- “charter” is the user/operator-facing umbrella; `src/charter/` remains an unrelated existing code package;
- Charter Pack = versioned distributable governance catalogue (offer side);
- Charter Bundle = project-local materialized files under `.kittify/charter/` (consume side);
- Active Charter = one governance artefact activated/wired in for the project;
- Inactive Charter = an artefact available in a Charter Pack but not activated;
- existing kind labels survive in their existing roles, without claiming all are activatable;
- non-public internal package/module/import/symbol names remain out of scope; operator-visible
  content/pathnames, supported public Python names/imports, exact `doctrine.api.__all__` exports, and
  installable distribution/project/wheel metadata are in scope;
- reproduce the complete ID table from the ADR contract, including both `spk-doctrine-charter` and `spec-kitty-charter-doctrine` → `spk-charter-lifecycle`, the six other named skill replacements, `charter-daphne`, and `018-charter-versioning-requirement`; every old ID is a 3.x warning alias removed by M6;
- 3.x compatibility and 4.0 zero-user-visible rule;
- the glossary must change all authorities and replace Doctrine Pack with Charter Pack;
- the fixed non-command mappings: glossary `docs/context/doctrine.md` → `docs/context/charter.md` with active referrers in M1; distinct selection/org-pack/tracker mappings; target URN plus known serialized/API rows; and the operator-map requirement to enumerate exact `doctrine.api.__all__` and `spec-kitty-doctrine` distribution/wheel surfaces; project overlays `.kittify/doctrine/` → `.kittify/charter-packs/` in M3 under checked dual-read/collision/migration behavior;
- exact guard intent: fingerprint every pre-M1 guard-root hit using exact ordinary OC/X records plus a non-owning semantic CR reservation overlay for retained IDs/routes/keys/paths/parser literals/redirects/warnings; each OC keeps one M1–M5 owner, each CR has a disjoint source budget, one M1–M4 introduction, exact X3 control, and M6 removal; every funded source OC owner equals introduction wave, which atomically sets `reserved` to `active` (or M2 distribution-only `closed-no-channel`); mutable M2 target resolution does not change CR identity and fails closed until frozen before edits; I6 is X-only with empty CR inventory; ordinary and CR-evasion mutations fail.

Include this exact legacy-free line for M1 to place in the human-authored governance/directives section of `.kittify/charter/charter.yaml`:

> Terminology Canon: Use “charter” for the governance artefact layer: “charter pack” for a distributable catalogue, “charter bundle” for the project-local file set, “active charter” for an activated artefact, and “inactive charter” for an available but unactivated artefact.

State owner-correct bundle operations: direct-edit human-owned `charter.yaml` sections; directly curate `charter.md` if classified text requires it; `charter generate` refreshes catalog/metadata only; `charter sync` writes neither file; other sections use their owning workflows. M1, not this WP, executes those product changes.

## T002 — Amend prior ADR

Change `2026-07-15-1` status/pointer metadata only. Its body must remain byte-identical. The other ten matching-title ADRs remain immutable.

## T003 — Register

Run `python -m scripts.docs.freshen_adr_inventory`; do not hand-edit the generated index/lockfile. Verify using the script's supported check mode and docs freshness tests.

## T004 — Self-check

Read only the new ADR and answer these exact six questions:

1. What decision was made and what canonical term replaces the retired one?
2. How does Charter Pack differ from Charter Bundle, and what distinguishes Active Charter from Inactive Charter?
3. Which kind labels survive in their existing roles, and what replaces the former “Doctrine Domain” glossary sense?
4. What is in/out of scope, including operator-ID mappings, the non-public-internal versus
   supported-public-Python-API distinction, aggregate exact `doctrine.api.__all__` evidence, and
   public distribution/wheel treatment?
5. What is the 3.x policy and 4.0 removal rule?
6. How does the governance term differ from `src/charter/`?

All answers must come from the ADR. This author check does not replace WP05's one named independent reviewer.

## Verification

```bash
python -m scripts.docs.freshen_adr_inventory --check
git diff docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md
pytest -q tests/architectural/test_no_legacy_terminology.py
```

Reject body drift, another ADR status change, a product rename, a Terminology Canon instruction for `AGENTS.md`, or any ambiguous Pack/Bundle/activation definition.

## Activity Log

The generation record below is immutable. Do not edit this prompt to append activity;
status/history is event-log owned. Use
`spec-kitty agent tasks move-task WP01 --to <status>`.

- 2026-08-21T00:00:00Z – system – Prompt created.
