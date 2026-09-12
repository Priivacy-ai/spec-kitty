---
work_package_id: WP06
title: 'ADR: checkout ownership for mission create and next'
dependencies:
- WP01
requirement_refs:
- FR-011
- NFR-004
- C-002
planning_base_branch: fix/worktree-owned-root-3328-v2
merge_target_branch: fix/worktree-owned-root-3328-v2
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-owned-root-3328-v2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-owned-root-3328-v2 unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
history:
- at: '2026-08-11T13:37:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: ''
authoritative_surface: docs/adr/3.x/
create_intent: []
execution_mode: planning_artifact
model: ''
owned_files:
- docs/adr/3.x/*-checkout-ownership-for-mission-create-and-next.md
- scripts/docs/freshen_adr_inventory.py
- tests/docs/test_freshen_adr_inventory.py
- docs/adr/3.x/index.md
- docs/development/3-2-page-inventory.yaml
- docs/development/3-2-docs-retrieval-index.yaml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP06 - ADR: checkout ownership for mission create and next

## Objective

Record the new checkout-ownership validation mechanism (WP01's primitive, consumed by WP02/WP03) as a formal Architecture Decision Record, since research (`research.md` D-7) confirmed no existing ADR covers invoking-checkout ownership validation. Repair the canonical ADR freshener's Common Docs era-index authority so the ADR can be registered through the generator rather than by hand (#3345).

## Context

`cross_cutting: true` — this WP has no `plan_concern_refs` because it documents ALL of IC-01 through IC-05 collectively rather than implementing any single one. It can be drafted in parallel with WP02-WP05 (once WP01's shape is settled) and finalized once the feature lands, so the ADR reflects the actual implemented shape rather than the planned one.

Read `docs/adr/README.md` for the numbering/naming convention before creating the file. Read the four nearest-adjacent existing ADRs cited in `research.md` D-7 (`2026-06-24-2-write-branch-resolution-primary-anchor.md`, `2026-06-19-1-coord-empty-surface-fallback.md`, `2026-06-03-2-executioncontext-owner-and-committarget.md`, `2026-04-03-1-execution-lanes-own-worktrees-and-mission-branches.md`) for house style and structure — match their format exactly.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### Subtask T020 - Author the ADR

- **Purpose**: Durable record of the decision for future readers (including #3128's implementer, who will consume this ADR's decision as a building block).
- **Steps**:
  1. Confirm the next available date-prefixed slot under `docs/adr/3.x/` at implementation time (research risk #3 — do not assume a slot from planning time since concurrent missions may have claimed one; `zeitgeist_presence` confirmed multiple active sessions on this repo during planning).
  2. Write the ADR covering: Context (the ambient-fallback problem, #3129's diagnosis, #3128's relationship), Decision (the `OwnershipClaim`/`OwnershipValidationResult` primitive, the `--owned-checkout` CLI affordance on `mission create`/`next` only, the explicit non-reuse of `allow_worktree_context`), Consequences (what #3128 can now build on; what remains explicitly out of scope — the shadow-workspace redesign from #3129), and Alternatives Considered (reusing/loosening `allow_worktree_context` — rejected per NFR-003; extending `detect_execution_context`'s `.worktrees`-literal scope instead of adding a new primitive — rejected because it doesn't address `mission create`'s separate guard).
  3. Cross-reference `kitty-specs/worktree-owned-root-3328-01KZRG01/data-model.md` and `contracts/checkout-ownership-cli-contract.md` by relative path rather than duplicating their content.
- **Files**: `docs/adr/3.x/<confirmed-date>-checkout-ownership-for-mission-create-and-next.md` (new, ~100-150 lines, matching house ADR length)

### Subtask T021 - Restore canonical era-index generation

- **Purpose**: Close #3345, discovered by T020: the Common Docs move made `docs/adr/3.x/README.md` a redirect stub and `index.md` the era table authority, while the canonical freshener still hardcodes `README.md`.
- **Steps**:
  1. Add a redirect-stub plus `index.md` fixture to `tests/docs/test_freshen_adr_inventory.py`; capture RED showing check/write mode cannot see the authoritative table.
  2. Minimally make `scripts/docs/freshen_adr_inventory.py` resolve the sanctioned era index while preserving existing legacy `README.md` table fixtures, exact `docs/adr/<era>/<file>.md` containment, and path-escape refusal. Fail closed only when a table-maintaining canonical landing page declares an `## Index` section whose ADR table is malformed; sanctioned legacy 1.x/2.x table-less `index.md` landing pages that do not declare that section remain skipped. Add production-shaped fixtures for both cases, including the legacy `index.md` plus redirect `README.md` layout used by the real repository.
  3. Run `python -m scripts.docs.freshen_adr_inventory docs/adr/3.x/<ADR>.md`. Do not hand-edit either generated output.
  4. Run the sanctioned docs retrieval-index writer for the new ADR, then require `python scripts/docs/docs_index.py --strict` to report exact agreement. Do not hand-edit the generated retrieval index.
  5. Re-run the freshener with `--check` and require clean agreement between check and write mode. On the real repository tree, both `--all` and `--all --check` must succeed without changing sanctioned output. For an explicit malformed target that declares `## Index`, write and `--check` modes must both report structural failure with exit 2 rather than misclassifying `--check` as a missing-row exit 1.
- **Files**: `scripts/docs/freshen_adr_inventory.py`, `tests/docs/test_freshen_adr_inventory.py`, `docs/adr/3.x/index.md` (generator-only), `docs/development/3-2-page-inventory.yaml` (generator-only), `docs/development/3-2-docs-retrieval-index.yaml` (generator-only)

## Test Strategy

- RED/GREEN the redirect-stub + canonical `index.md` authority in `tests/docs/test_freshen_adr_inventory.py`.
- Run the full freshener unit file, real-tree `--all` and `--all --check`, the canonical freshener `--check`, strict docs retrieval-index freshness, docs structural/relative-link gates, and `tests/architectural/test_no_legacy_terminology.py`.
- Preserve legacy README-table fixtures, production-shaped table-less 1.x/2.x `index.md` landing pages, and path-escape safety; generated index/inventory diffs must be attributable only to the new ADR.

## Risks & Mitigations

- **Risk**: Date-slot collision with a concurrently-landed ADR. **Mitigation**: check `git log --oneline -- docs/adr/3.x/` immediately before creating the file, not just at plan time.

## Definition of Done

- [ ] ADR file exists at the correct, non-colliding date-prefixed path.
- [ ] Matches house ADR structure (Context/Decision/Consequences/Alternatives).
- [ ] Cross-references data-model.md and the CLI contract without duplicating their content.
- [ ] Redirect-stub eras resolve the canonical `index.md`; legacy README-table fixtures and containment guards remain green.
- [ ] `--all` and explicit-target `--check` return exit 2 for a declared `## Index` with a malformed ADR table, while production-shaped legacy table-less `index.md` eras remain skipped and real-tree `--all`/`--all --check` succeed without mutation.
- [ ] Sanctioned generators update the ADR index, page inventory, and docs retrieval index; freshener `--check` and retrieval-index strict mode report clean.

## Reviewer Guidance

- Confirm the ADR accurately reflects what WP01-WP05 actually implemented (not the plan's initial sketch) — read it against the merged diff, not just against plan.md.
- Confirm #3345 is closed by a RED-to-GREEN canonical-authority fix, not by a hand-edited index or weakened containment check.

**Implementation command**: `spec-kitty agent action implement WP06 --agent <name>`

## Activity Log

- 2026-08-11T13:37:00Z - system - Prompt created.
- 2026-08-11T23:21:07Z – codex – Reviewer-renata/Prime WP05 MEDIUM mapped to core #3343: the immutable installed-wheel linked-worktree acceptance test is marked distribution+slow+e2e but selected by no current CI job. WP06 ADR must record #3343 CI contract, trigger/evidence expectations, and that #3328 local 20-run proof is authoritative until the governed CI follow-up lands. #3343 remains unassigned because implementation has not begun.
- 2026-08-12T00:20:00Z – planner-priti – Canonical freshener RED exposed #3345: Common Docs moved the era table to `index.md` but the generator still targets the README redirect stub. Added T021 and exactly the freshener/test/generated-output paths required to restore generator-only registration; no index bytes may be hand-authored.
- 2026-08-12T01:00:00Z – planner-priti – Prime cycle 1 rejected WP06 because the ADR was absent from the generated docs retrieval index (`DOCS-INDEX-DRIFT` added=1) and observed that `--all` silently skipped malformed canonical indexes. Added only the retrieval-index output plus the fail-closed `--all` contract; sanctioned generators remain the sole byte authority.
- 2026-08-12T01:37:00Z – planner-priti – Prime cycle 2 proved the broad fail-closed guard regressed the repository's sanctioned 1.x/2.x table-less `index.md` landing pages. Refined T021 to use an explicit `## Index` declaration as the structural-maintenance signal, require production-shaped legacy fixtures and real-tree `--all`/`--all --check` success, and require exit-2 structural parity for explicit malformed-target check mode. Owned files and requirement mapping remain unchanged.
