---
work_package_id: WP02
title: Occurrence Inventory — Mechanical Audit
dependencies:
- WP01
requirement_refs:
- C-003
- C-005
- FR-006
- FR-007
- NFR-001
planning_base_branch: feat/retire-doctrine-term
merge_target_branch: feat/retire-doctrine-term
branch_strategy: Planning artifacts for this mission were generated on feat/retire-doctrine-term. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/retire-doctrine-term unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 2 - Evidence Base
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md
- kitty-specs/retire-doctrine-term-01M0JMK9/inventory-hits.tsv
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md
- kitty-specs/retire-doctrine-term-01M0JMK9/inventory-hits.tsv
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Exhaustive Occurrence Inventory

## Start

Load `curator-carla`; read WP01 ADR/baseline, `contracts/inventory-schema.md`,
`contracts/operator-surface-map-schema.md`, `data-model.md`, `research.md`, and quickstart §4. Never
refetch/repoint the frozen target.

## Goal

Create a deterministic manifest set-equal to every forced-text content occurrence and matching tracked
pathname outside the fixed `kitty-specs/` exclusion root. Every row is work. No X1/X2/X3,
ignored/internal/historical/fixture/generated/metadata classification or external current-repo deferral
exists. The TSV is ephemeral evidence (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`): write it to the mission
directory (untracked via the mission-local `.gitignore`) and pin its SHA-256/row count in committed
`inventory.md`.

## T005 — Exact audits

Load `target_tip` as `base_commit`. Run the exact no-pipeline Python subprocess procedures from
`contracts/inventory-schema.md` — the content argv with the fixed `:(exclude)kitty-specs/` pathspec and the
pathname drop of `kitty-specs/` after the rc check. Preserve argv, raw return codes, outputs, stderr, and
hashes; record excluded-root content/pathname counts as orientation. Accept content rc 1 only with empty
stdout; reject content rc >1, any pathname-command nonzero rc, output/rc inconsistency, `-I`, any root
narrowing beyond the fixed exclusion, shell-expanded files, sampling, or pathname decoding loss. Exercise
the named git-failure mutation before recording set equality.

## T006 — Per-hit manifest

Write the fixed TSV schema with one row per content match ordinal and one per pathname. Include:

- all public/private `src/doctrine/` files, symbols/imports and matching pathnames;
- tests, fixtures, build hooks, distribution/wheel/metadata, CI/scripts/workflows;
- Charter/glossary source, graph, interview, synthesis, generated/live surfaces;
- packs/project roots, skills/profiles/directives/prompts/overrides/generated/installed assets;
- ADRs, docs archives, event/history snapshots, evidence, docs/comments/READMEs and referrers outside
  `kitty-specs/` (including referrers to archive paths);
- every compatibility control/fixture/alias candidate.

Assign S1–S10 and one OC to each. Split classes when semantic seam or future M1–M6 owner differs.

## T007 — Set equality

Prove deterministic sort/IDs/hashes; manifest content rows equal grep coordinates and pathname rows equal
NUL stream. Compute both row kinds with the contract's exact domain tag, LP fields, big-endian uint64
content coordinates, lowercase tree OID, raw path/match bytes, and empty pathname coordinate/match fields.
Run byte-identical independent reproduction. Derive all counts. Zero duplicates, omissions, unclassified
rows, X values, or invented rows. Record the TSV SHA-256, row count, and exact reproduction command in
`inventory.md` so WP05 can regenerate and match it.

## T008 — Inventory and CR candidates

Derive `inventory.md` from TSV. Record exact OC membership and bounded/disjoint CR candidates for 3.x:
frozen-base source hits, introduction M1–M4, fixed/M2-map target, product budget, control record, named
tests, M6 removal. State that later-created product/control coordinates are new M6 work and do not alter
source OC ownership. Do not assign primary owners here, but make classes assignment-ready and forbid current-repo
deferral.

## Done

Audits, hashes, manifest arithmetic, all-tree-outside-`kitty-specs/` scope, and CR candidates are
reproducible from the frozen base; the TSV is untracked and hash-pinned. Any exempt row fails.

## Activity Log

Runtime-owned. Do not edit this prompt to record activity; use Spec Kitty task status/events.
