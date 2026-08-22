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

Run `spec-kitty agent profile show planner-priti`, load it, then read both `contracts/stacked-plan-schema.md` and `contracts/operator-surface-map-schema.md`, the ADR, inventory + manifest, methodology, data model, and quickstart §§5–6. Check review feedback first.

## Goal

Create `stacked-plan.md` with schema-complete M1–M6 entries, the sole OC-to-mission assignment table, bounded local questions, rollback, and a recorded M1 zero-decision dry run.

## Fixed stack

| Mission | Slug | Fixed responsibility | Invariant |
|---------|------|----------------------|-----------|
| M1 | `charter-authority-flip` | three glossary authorities; `docs/context/charter.md` plus active referrers; X2 refs retained as history/no dangling active refs; selection-key migration; owner-correct bundle operations; exact canon; guard/registry last | I1 |
| M2 | `charter-cli-surface` | freeze exhaustive operator-surface map; canonical CLI + serialized/API values + old warning/read aliases; separate org-pack and tracker-ownership config migrations; every mapped producer/consumer same-wave | I2 |
| M3 | `charter-packs-source` | built-in/org/project Charter Packs/overlays; fixed `.kittify/doctrine/` → `.kittify/charter-packs/` checked migration; canonical directive ID + alias | I3 |
| M4 | `charter-skills-artifacts` | full ADR skill/profile map; non-route prompts/overrides/generated agents via upgrade; old warning aliases | I4 |
| M5 | `charter-docs-prose` | remaining active human prose regardless directory; immutable ADR/history stays X2 | I5 |
| M6 | `charter-removal-audit` | remove legacy aliases/keys/paths and prove terminal content+pathname audit at 4.0 | I6 |

Do not change granularity or reassign the fixed canonical ID mappings.

## T013 — Per-mission entries

For each mission write: slug, purpose, inputs, outputs, explicit `depends_on`, OC IDs, `change_mode: bulk_edit`, occurrence-map obligation, invariant, local design questions, named verifiers, and rollback.

- All M1–M6 are bulk edits; M6 removal is occurrence-sensitive.
- M1 local questions must be empty.
- M2 may carry one question: exact canonical destination/name for each still-unfixed command,
  M2-scope serialized/API token, supported public Python API import/name, or public distribution/wheel
  surface. It owns every mapped consumer and freezes authoritative map plus CLI projection; M3–M5
  exclude map hits. Public rows use one OC-backed aggregate `doctrine.api` facade row to enumerate
  exact `__all__` membership without invented hit rows, plus separate legacy-bearing member rows,
  `spec-kitty-doctrine` metadata, publication evidence, canonical charter facade/distribution,
  re-exports/docs/build/install/wheel tests, evidence-required 3.x compatibility, and M6 removal.
- No M4 mapping question remains: skill/profile canonical names are fixed. M3 directive name is fixed.
- No path/config question remains: the active glossary pathname/referrer wave, three semantic config seams,
  and `.kittify/charter-packs/` destination with canonical-write/dual-read/collision/migration contract
  are fixed inputs. M3 owns all readers, writers, staging, migration, docs/config/tests same-wave.
- Compatibility OC entries are assigned to M6 from the start. Each M1–M4 introduction wave may
  relocate only registered exact fingerprints within its frozen maximum and must update named
  enumeration plus behavior/migration tests. M6 empties registry and runtime/file/key inventory.
- Rollback follows methodology's reverse-suffix/forward-fix contract.

## T014 — Assignment table

Map every in-scope OC-## exactly once. `inventory.md` must not duplicate assignment. Cross-repo deferrals require surface, repo, owner, milestone, tracking reference/downstream process, and rationale; no `TBD`. Confirm each mission's `retires` list equals its assignment rows.

## T015 — M1 readiness record

Draft a skeleton (not a new mission spec) using only current artifacts and mark each item determined with a precise citation:

- Charter Pack/Bundle and Active/Inactive definitions;
- all three glossary authority paths, parity, and #2727 coordination;
- human-owned `charter.yaml` edit, curated `charter.md` handling, generate-only catalog/metadata, owning flows for other sections;
- exact legacy-free Terminology Canon line in `charter.yaml`, not `AGENTS.md`;
- exact ordinary pre-M1 OC/X fingerprint records with owner waves, same-wave shrink, X-only ordinary I6, and four ordinary mutation cases;
- M6-owned compatibility registry covering every retained ID/route/key/path/parser/redirect/warning,
  with full legacy value/path, canonical replacement, introduction wave, frozen maximum, exact
  fingerprints, named tests, controlled relocation, and empty I6 inventory;
- M1 occurrence classes/map, checks, output, I1, and rollback.

Pass = zero gaps/local questions. A gap routes to owning WP artifact and blocks WP04; do not invent a decision here.

## Verification

Check every OC exactly once; every entry complete; M1→I1 … M6→I6; all M1–M6 bulk; M1 questions empty; later questions bounded/owned; no ownerless deferral; rollback present; M1 skeleton fully cited.

Reject `assigned_mission` in inventory, M1→I2, M6 non-bulk, M1–M5 “zero questions” as a blanket rule, a partial/wildcard operator map, mapped hits assigned to M3–M5, a deferred M4 ID mapping, or hand-wavy bundle regeneration.

## Activity Log

The generation record below is immutable. Do not edit this prompt to append activity;
status/history is event-log owned. Use
`spec-kitty agent tasks move-task WP04 --to <status>`.

- 2026-08-21T00:00:00Z – system – Prompt created.
