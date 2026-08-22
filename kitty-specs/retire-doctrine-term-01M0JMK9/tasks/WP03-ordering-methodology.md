---
work_package_id: WP03
title: Ordering and Methodology Analysis
dependencies:
- WP02
requirement_refs:
- C-004
- FR-008
planning_base_branch: feat/retire-doctrine-term
merge_target_branch: feat/retire-doctrine-term
branch_strategy: Planning artifacts for this mission were generated on feat/retire-doctrine-term. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/retire-doctrine-term unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 3 - Methodology
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: planner-priti
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/methodology.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/methodology.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Ordering and Methodology Analysis

## Start

Run `spec-kitty agent profile show planner-priti`, load it, then read the ADR, inventory + hit manifest, `research.md`, `data-model.md`, both operator-map/stacked-plan contracts, and `quickstart.md` §§5–7. Check review feedback first.

## Goal

Create `methodology.md`: explain why M1–M6 use the fixed authority-first order; state I0–I6; define a non-vacuous fingerprint guard, one verifier per S1–S10 surface, per-wave evidence, compatibility tests, and rollback.

## T009 — Ordering and invariants

For every transition, cite inventory classes and the concrete risk closed:

1. M1 flips all glossary authorities, renames the docs authority plus every active referrer, retains immutable X2 refs as history and proves no dangling active refs, migrates the charter selection key, and changes human-owned charter instruction surfaces atomically, then arms guard last.
2. M2 freezes the exhaustive operator-surface map, then moves executable commands, serialized/API tokens, the distinct org-pack and tracker-ownership config seams, and every mapped producer/consumer together regardless directory.
3. M3 moves Charter Pack/overlay/path surfaces to the fixed `.kittify/charter-packs/` root under the canonical-write/dual-read/collision contract and moves the directive ID.
4. M4 moves skills/profile IDs/prompts/overrides/generated agent copies through owning upgrade flows.
5. M5 moves all remaining active human prose regardless directory after executable/instruction sources.
6. M6 removes compatibility only at 4.0 and proves terminal audit.

State exact map M1→I1, M2→I2, M3→I3, M4→I4, M5→I5, M6→I6. I0 is pre-M1.

## T010 — Fingerprint guard

Seed two tracks for every classified pre-M1 occurrence inside guard roots.

Ordinary primary-use OC-## hits owned by M1–M5 plus X1/X2/X3 use exact records: kind,
repo-relative path, normalized-line/path SHA-256, match ordinal, classification ID, and owner wave.
Diagnostic line numbers are not identity. Materialize the complete pre-M1 baseline, then record the
scoped same-PR M1 source/baseline shrink before the final post-M1 guard lands. Later owner waves remove
their OC records; I6 may retain only justified X fingerprints.

Every intentionally retained 3.x identifier, command route, serialized key, project path,
parser/migrator literal, redirect, or warning is an OC assigned to M6 from the start. Its registry
entry records full legacy literal/path, canonical replacement, M1–M4 introduction wave, M6 removal,
pre-M1 frozen maximum, exact current source/path fingerprints, and a named enumeration plus
behavior/migration test. Only the declared introduction wave may atomically relocate exact
fingerprints, never grow the maximum. It must prove canonical replacement, legacy behavior/migration,
warning where executable, and runtime/file/key enumeration. M6 deletes registry, implementation,
and exposure; terminal enumeration is empty.

Ordinary current fingerprints and registered compatibility fingerprints must equal their respective
baselines outside a declared relocation. Shrink source and baseline together. Define tests that fail for:

- new hit in a baselined file;
- replacement of an allowed internal hit with user-facing text at equal count;
- removal of an allowed hit without removing baseline entry;
- new file with a hit.
- unregistered or undeclared-wave compatibility addition/move;
- compatibility fingerprints above the frozen per-entry maximum;
- a product compatibility literal constructed from fragments to evade the registry.

Only detector fixtures may construct the literal from fragments and remain X3. Product aliases,
parsers, redirects, warnings, keys, and paths remain in-scope. No file/directory/count allowlist and
no blind spot deferred to later audit.

## T011 — Verification matrix

Create one row for every S1–S10 category and split mixed-root portions. Assign one primary mechanism: fingerprint guard, pinned audit, glossary parity, pack/config migration tests, CLI/output snapshots, bundle/context checks, or workflow CI. Every OC-## must map to exactly one primary row; secondary defense may be noted but cannot mask missing ownership.

M1 authority operations must be owner-correct:

- `docs/context/charter.md` plus all active referrers and the two YAML glossary authorities move atomically under parity and #2727 coordination; immutable X2 refs remain byte-identical historical text with no current-HEAD link promise;
- human-owned `charter.yaml` sections and curated `charter.md` are direct edits;
- `charter generate` refreshes catalog/metadata only; sync is not a writer;
- graph/interview/runtime content uses owning flows.

## T012 — Catfooding, evidence, compatibility, rollback

Require each M1–M6 wave to pin its base, regenerate content/path manifest and scoped occurrence map,
shrink ordinary guard fingerprints, apply only its registered compatibility relocations, update
same-wave consumers, and record invariant evidence. M1 owns the glossary pathname/referrers and
selection key. M2 freezes authoritative `canonical-operator-surface-map.md` plus mechanically derived
set-equal `canonical-cli-route-map.md`, owns every mapped command, serialized/API occurrence,
supported public Python API export/import, one OC-backed aggregate `doctrine.api` facade with exact
`__all__` membership evidence plus separate legacy-bearing member rows, public
distribution/wheel metadata and publication-evidence treatment, plus every consumer regardless
directory, and independently migrates org-pack versus tracker-ownership seams; M3–M5 exclude mapped
hits. M3 owns all old/new overlay-root readers, writers, staging, migration, config/docs,
and tests. Prove canonical replacement, old 3.x compatibility + warning/migration, enumeration, and
M6 absence for every command/key/path/skill/profile/directive/redirect class.
M2 also owns the fixed target URN change `doctrine:<kind>:<id>` → `charter:<kind>:<id>` across
synthesizer apply/dry-run producers, retrospective/event/JSON consumers, renderers, schemas, and
contract tests. Canonical writers emit only the new URN; 3.x active readers accept the old URN with
warning until M6. Immutable X2 journals stay byte-identical and are rendered canonically through a
non-emitting historical normalizer classified X3 from the start; it is not an active-input alias.
Public Python rows migrate supported access to canonical charter-facade imports, keep 3.x
`DeprecationWarning` aliases with parity tests, and remove old names from supported exports/docs in M6;
distribution rows rename before first publication or register evidence-required compatibility,
update wheel-closure tests, and remove old metadata/exports in M6; non-public implementation
symbols/module paths remain X1.

Rollback contract:

- before a dependent wave lands, revert current wave alone;
- after dependents, reverse landed suffix M(n)..M1 or forward-fix;
- M6 may restore aliases only while 3.x support remains; after 4.0 use release rollback, not a partial semantic reversion.

## Verification

A reviewer must be able to challenge every ordering choice and locate a risk/rationale, invariant, and named check. Validate S1–S10 coverage, four ordinary mutations plus compatibility relocation/budget/fragment mutations, per-wave manifest trigger, compatibility proof, and rollback rules. M1 implementer must be able to build guard machinery from this document without a new decision.

Reject M1→I2, file allowlists, count-only budgets, “audit will catch it later” gaps, `charter sync` as writer, or missing config/path/operator-ID surfaces.

## Activity Log

The generation record below is immutable. Do not edit this prompt to append activity;
status/history is event-log owned. Use
`spec-kitty agent tasks move-task WP03 --to <status>`.

- 2026-08-21T00:00:00Z – system – Prompt created.
