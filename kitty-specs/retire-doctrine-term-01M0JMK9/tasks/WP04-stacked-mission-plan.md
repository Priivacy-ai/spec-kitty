---
work_package_id: WP04
title: Stacked Mission Plan
dependencies:
- WP03
requirement_refs:
- FR-009
- FR-010
- NFR-003
planning_base_branch: feat/retire-doctrine-term
merge_target_branch: feat/retire-doctrine-term
branch_strategy: Planning artifacts for this mission were generated on feat/retire-doctrine-term. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/retire-doctrine-term unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
phase: Phase 4 - Execution Stack
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: planner-priti
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/stacked-plan.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/stacked-plan.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Stacked Mission Plan

## Start

Load `planner-priti`; read `contracts/stacked-plan-schema.md`,
`contracts/operator-surface-map-schema.md`, ADR, inventory/manifest, methodology, data model, and
quickstart §§5–7; load canonical mission `issue-matrix.json` and its #2727 row. Check review feedback.

## Goal

Create `stacked-plan.md` with complete M1–M6 entries, exact OC/hit primary-owner and CR lifecycle tables,
M1 zero-decision proof, M2 bounded topology-map gate, and executable tests/merge gates/rollback.

## T013 — Fixed stack entries

Use these responsibilities without weakening:

| Wave | Fixed responsibility | Invariant |
|---|---|---|
| M1 | ADR-effective full Charter authority plus atomic parity transaction across docs context, `.kittify/glossaries/spec_kitty_core.yaml`, built-in glossary pack, referrers + explicit override + guard | I1 |
| M2 | all private/public source/code/test/build/CLI/API/config/workflow/metadata topology; old source tree merged/relocated into collision-free `src/charter/` | I2 |
| M3 | verified pack/project-overlay migration to `.kittify/charter-packs/`; no old root on completion | I3 |
| M4 | every source/generated/installed/shared agent asset canonical; no old installed path on completion | I4 |
| M5 | all remaining current-tree prose/history/ADR/docs/archive/evidence filenames/referrers outside the immutable `kitty-specs/` archive; archive referrers recited by `mission_id`/mid8 or token-free path | I5 |
| M6 | all aliases/keys/paths/controls/fixtures/baselines/allowlists removed; exact zero over `HEAD` with the single fixed `kitty-specs/` exclusion | I6 |

Each entry includes every field from stack schema, fresh base/audit, `change_mode: bulk_edit`, and exact
input/output handoffs.

## T014 — Cardinality and compatibility

Write one row per OC with exact member hits and one M1–M6 owner. Prove wave sets pairwise disjoint and union
equals manifest. No current-repo external deferral or X owner. Write one CR row with disjoint frozen-base
sources whose OC owner equals introduction, target/budget/control/tests, and distinct later-created
product/control coordinates assigned to M6 removal. No coordinate is double-owned or source double-funded.

M6's owner set includes every compatibility control, fixture, redirect, warning, alias, old key/path,
transition baseline/allowlist, and any remaining detector literal.

## T015 — Dry runs and gates

M1 dry run consumes the ADR contract's exact Charter sources and maps each artifact to direct policy edit,
activation-engine command, sanctioned lossless answers migration + serializer hardening, YAML catalog/
metadata generation, context refresh, synthesis, verified no-op, or repeated
zero-consumer deletion of obsolete `graph.yml`; it produces the tracked authority state, glossary
authorities, override, selection migration, and guard with zero questions.
It also consumes #2727 from `issue-matrix.json` and atomically updates
`docs/context/doctrine.md` → `docs/context/charter.md`, `.kittify/glossaries/spec_kitty_core.yaml`,
`packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml`, and all active referrers; glossary
semantic/hash/link parity is a single rollback gate and cannot be deferred or split.

M2 dry run produces map/projection set-equal to every old private/public topology hit; every collision with
existing `src/charter/` is `merge-existing` or exact `relocate` before first edit. Its only local gate cannot
change scope/order.

M3/M4 use fixed backup/verify/conflict rules, not runtime ledgers. M5 has no history exemption beyond the
fixed `kitty-specs/` root, which it never edits or renames. M6 has no exception question and requires
checked zero content/path audits (contract pathspec only) bound to the exact final commit/tree;
any tree change invalidates evidence and CI/release reruns token-literal-free
`scripts/audit_retired_term_zero.py` under required marker `terminology-zero-current-tree` on the
merge/publish result tree. Attestation is external stdout, never a tracked write.

## Done

The plan is executable from artifacts alone; all ownership arithmetic, dependencies, outputs, tests,
merge gates, and rollback are explicit.

## Activity Log

Runtime-owned. Do not edit this prompt to record activity; use Spec Kitty task status/events.
