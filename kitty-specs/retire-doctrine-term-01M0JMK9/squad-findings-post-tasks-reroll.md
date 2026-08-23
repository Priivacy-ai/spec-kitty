# Adversarial Squad Findings — Post-Tasks Correction and Reroll

**Point-cut**: post-tasks / pre-implementation
**Date**: 2026-08-22
**Profiles**: architect-alphonso, reviewer-renata, planner-priti
**Original sharp question**: Was the earlier user-facing-only program coherent and executable?

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
| CI contract corpus failed | Removed the illustrative schema block/skip-marker dependency; executable evidence is the TSV plus audit arithmetic, so no architectural test-baseline ratchet is needed. |
| Compatibility ownership collided across waves | Ordinary hits retain one M1–M5 OC owner; non-owning semantic CR reservations carry disjoint source budgets, exact X3 controls, owner=introduction joins, bounded state transitions, and M6 removal. |
| Public API/distribution scope was incomplete | M2's authoritative operator map covers supported Python facade/export contracts, exact aggregate `doctrine.api.__all__` evidence, distribution/wheel metadata, publication disposition, and every consumer; non-emitted physical implementation paths remain X1. |
| Lifecycle ownership rejected normal execution | C-001 permits the exact mission-relative runtime placements, including status/lanes/matrices/dossiers, runtime-captured `baseline-tests.json`, and `review-cycle-N.md`, while WP prompts remain immutable inputs. |
| Target freshness could deadlock C-001 | WP01 atomically freezes current `target_tip` plus `implementation_base`; WP02–WP05 reuse it and verify exact merge-base identity. Post-capture target incorporation requires a fresh target-based branch, planning-only replay, and WP01 restart. Each future M1–M6 wave freezes its own wave-local snapshot. |
| Runtime issue-matrix placement drifted | C-001 now permits canonical mission-relative `issue-matrix.json` from merged `main`; obsolete `.md` is not treated as a normal writer output. |
| Open #2727 had no approval-gate artifact | The canonical writer created `issue-matrix.json`; its WP04-owned `deferred-with-followup` row names #2727 and the atomic glossary-authority/parity obligation. Approval and merge-gate completeness both pass. |

Historical `squad-findings-post-spec.md`, `squad-findings-post-plan.md`, and `squad-findings-post-plan-coverage.md` remain untouched snapshots.

## Historical reroll verdict (superseded by operator override)

| Lens | Profile | Verdict |
|------|---------|---------|
| Architecture | architect-alphonso | PASS |
| Contract | reviewer-renata | PASS |
| Planning/execution | planner-priti | PASS |

All three profiles independently reran against the corrected tree on 2026-08-22 and returned
`VERDICT: PASS`. The reroll covered the complete planning graph, executable WP topology, frozen
snapshot semantics, compatibility-reservation lifecycle, issue-matrix approval path, validators, and
fresh-clone continuation at WP01. No implementation work was performed.

## 2026-08-22 authoritative scope override folded

The operator superseded the reviewed user-facing-only scope after the historical PASS above. That PASS is
not evidence for the new terminal contract. The corrected planning set now requires:

| Override requirement | Folded correction |
|---|---|
| Terminal scope | Zero case-insensitive content occurrences and zero tracked pathname occurrences across all current `HEAD`; Git object history outside `HEAD` only exclusion. |
| No exemptions | Removed X1/X2/X3, internal, historical-current-tree, fixture, metadata, generated, test, and supported-surface terminal carve-outs. |
| Charter authority | M1 updates ADR + complete Charter/glossary source/graph/interview/synthesis/generated owner graph and records the narrow no-data-loss override at I1. |
| Executable topology | M2 owns all public/private source packages, symbols, imports, tests, fixtures, build hooks, CLI/API/config/workflow/distribution metadata and freezes collision-free convergence into `src/charter/`. |
| Project/agent paths | M3/M4 preserve content canonically and hard-fail divergent collisions; completed migrations cannot retain old roots/installed paths. Runtime managed-path ledger overdesign is rejected. |
| Current-tree history | M5 rewrites/renames ADRs, missions, archives, evidence, history snapshots, filenames, and referrers; Git history preserves prior bytes. |
| Compatibility extinction | M6 removes every alias/key/path/control/fixture/baseline/allowlist and uses numeric-byte negative tests before exact all-`HEAD` zero audits. |
| Ownership | Every hit is assigned exactly once to M1–M6; no current-repository deferral. |

## Final independent reroll under the operator override

All reviewers loaded their assigned profile and live Charter context, treated
`DM-01M0NDJ33GCKATG3H4BK4PAMNG` as controlling, and reviewed this as a research/planning mission. They
did not treat the superseded Charter preservation/history rules as blockers: M1 updates the Charter
itself, and M5 owns current-tree history.

| Lens | Profile | Verdict | Final evidence |
|---|---|---|---|
| Architecture | architect-alphonso | PASS | Complete M1→M6 topology; every current-tree hit/path owned; exact-zero I6 only. |
| Contract | reviewer-renata | PASS | Fail-closed byte-safe audits, exact Charter writers/migrations, deterministic hashes, commit/tree-bound M6 check. |
| Planning/execution | planner-priti | PASS | Strict/set-equal stack; M1 zero-decision plan; M2 bounded map; no old-path or history escape. |

The reroll first found and then verified closure of fail-open shell pipelines, incorrect Charter artifact
writers, lossy interview-answer serialization, ambiguous occurrence hashing, glossary/#2727 reachability,
compatibility-coordinate ownership, and stale final-tree evidence. The final contract requires the
token-literal-free `scripts/audit_retired_term_zero.py` entrypoint and external required check
`terminology-zero-current-tree` against the exact merge/publish result tree.

**Final verdict: PASS.** This planning mission does not perform the product rename. It guarantees the
downstream program cannot legitimately complete M6/4.0 while any case-insensitive matching content or
tracked pathname remains in current `HEAD`; Git object history outside `HEAD` is the sole exclusion.
