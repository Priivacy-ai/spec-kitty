# Adversarial Squad Findings — Post-Tasks Correction and Reroll

**Point-cut**: post-tasks / pre-implementation  
**Date**: 2026-08-22  
**Profiles**: architect-alphonso, reviewer-renata, planner-priti  
**Sharp question**: Is this a coherent, exhaustive, executable program for retiring the user-facing word “doctrine”, and can a fresh clone continue the mission without re-deciding scope or repairing lifecycle state?

## Initial verdict

All three lenses requested changes. Renata identified two critical contract failures; Alphonso and Priti independently reproduced the main architecture/planning failures. No implementation work was reviewed or performed.

## Convergent findings folded

| Finding | Correction |
|---------|------------|
| Broken shell-expanded audit, stale branch point, and pathname/blob omission | Fetch/incorporate `origin/main`, pin its exact tip, then use forced-text `git grep -aino --column` plus NUL-safe `git ls-tree -z`; one-row-per-hit `inventory-hits.tsv`; `-I` is forbidden because it omitted 177 reviewed-base hits. |
| Per-file totals allowed fake classification | Stable content/path coordinates joined to OC-## or X1/X2/X3; all summaries mechanically derived; assignment removed from inventory. |
| Missing live surfaces | S1–S10 now includes serialized config, overrides, all glossary authorities, project overlays/paths, workflows, and operator IDs. |
| Operator profile/directive IDs contradicted 4.0 rule | Fixed canonical mappings: `spk-charter-*`, `charter-daphne`, `018-charter-versioning-requirement`; 3.x warning aliases; M6 removal. |
| No replacement for Doctrine Pack | Canonical **Charter Pack** (offer) distinguished from **Charter Bundle** (project-local consume surface). |
| Active/inactive ontology conflicted | Active/inactive now describe an individual governance artefact's activation, never bundle state. |
| Bundle ownership was factually wrong | Direct edits only to human-owned `charter.yaml` sections and curated `charter.md`; `charter generate` only for catalog/metadata; sync is not a writer; other sections routed to owning workflows. |
| Glossary authority/path model was wrong | M1 atomically updates docs context, `.kittify/glossaries/spec_kitty_core.yaml`, and built-in glossary pack under parity, coordinating with open #2727 without split authority. |
| File/count guard was vacuous on mixed files | Exact classified occurrence fingerprints with required mutations for growth, equal-count substitution, stale baseline, and new files. |
| Plan determinism conflicted with M2 design | NFR-003 now forbids unresolved cross-wave inputs; later bounded/owned local questions are permitted. M2 command map is named; M1 has zero; skill/profile/directive mappings are fixed. |
| M6 bulk mode and rollback absent | Every M1–M6 wave is bulk with scoped occurrence map. Rollback is revert-alone before dependents, otherwise reverse landed suffix or forward-fix; M6 alias restoration is limited to supported 3.x. |
| WP prompts contradicted source contracts | WP01–WP05 regenerated around the corrected contracts, exact six ADR questions, M1→I1 … M6→I6, one independent reviewer, owner-complete deferrals, and dual C-001 diff bases. |
| Runtime topology was stale | Coordination doctor repair retained: flattened single-branch metadata, no missing coordination branch. Task finalization and fresh-clone `next` are required before handoff. |
| CI contract corpus failed | Inventory YAML example carries a reasoned round-trip skip marker; ratchet baseline increment is documented and tested. |
| Compatibility ownership collided across waves | Ordinary hits retain one M1–M5 OC owner; non-owning semantic CR reservations carry disjoint source budgets, exact X3 controls, owner=introduction joins, bounded state transitions, and M6 removal. |
| Public API/distribution scope was incomplete | M2's authoritative operator map covers supported Python facade/export contracts, exact aggregate `doctrine.api.__all__` evidence, distribution/wheel metadata, publication disposition, and every consumer; non-emitted physical implementation paths remain X1. |
| Lifecycle ownership rejected normal execution | C-001 permits the exact mission-relative runtime placements, including status/lanes/matrices/dossiers and `review-cycle-N.md`, while WP prompts remain immutable inputs. |

Historical `squad-findings-post-spec.md`, `squad-findings-post-plan.md`, and `squad-findings-post-plan-coverage.md` remain untouched snapshots.

## Reroll verdict

Pending same-profile reroll against the corrected diff.
