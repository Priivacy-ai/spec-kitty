---
work_package_id: WP07
title: domains/ migration + top-level index merge + lockfile regen (IC-04 bulk edit)
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
requirement_refs:
- C-001
- C-002
- FR-005
planning_base_branch: feat/docs-plans-tier3-closeout
merge_target_branch: feat/docs-plans-tier3-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/docs-plans-tier3-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-plans-tier3-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
history:
- at: '2026-08-12'
  note: Authored by /spec-kitty.tasks (post-plan-squad model). IC-04 bulk edit; final integration WP; merges IC-02 retire-index + IC-04 domains cluster into the one shared top-level index.md.
agent_profile: curator-carla
authoritative_surface: docs/plans/domains/
create_intent:
- docs/plans/domains/index.md
- docs/plans/domains/saas-hosted-sync-domain-plan.md
- docs/plans/domains/doctrine-charter-domain-plan.md
execution_mode: code_change
owned_files:
- docs/plans/index.md
- docs/plans/domains/index.md
- docs/plans/saas-hosted-sync-domain-plan.md
- docs/plans/doctrine-charter-domain-plan.md
- docs/plans/domains/saas-hosted-sync-domain-plan.md
- docs/plans/domains/doctrine-charter-domain-plan.md
- docs/plans/3-2-x-approach.md
- docs/plans/3-2-x-executive-overview.md
- docs/plans/3-2-x-milestone-roadmap.md
- docs/plans/3-2-x-open-core-delivery-plan.md
- docs/development/3-2-page-inventory.yaml
- docs/development/3-2-docs-retrieval-index.yaml
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load curator-carla
```

Apply its initialization, boundaries, directives, and tactics. Then read this WP, `spec.md` (FR-005, US2, C-001, C-002), `plan.md` (IC-04), `research.md` (D4), and `occurrence_map.yaml` (the canonical bulk-edit map that drives the gate).

## Objective

Migrate all four domain plans into `docs/plans/domains/`, flip the two moved plans `active → durable`, create `domains/index.md`, and update **every** reference — the top-level `docs/plans/index.md` (merging the domains-cluster edit **and** the IC-02 retire-index reconciliation into this one WP), the four `3-2-x-*` release docs, and the moved plans' own `related:` lists — then regenerate the docs lockfiles and prove **zero dead links**.

## Context

- **Bulk-edit gate:** `meta.json` sets `change_mode: bulk_edit`; `occurrence_map.yaml` (schema `src/doctrine/schemas/occurrence-map.schema.yaml`) is canonical and **the `/spec-kitty.implement` command WILL require it** — keep it conformant, do not delete it. The map covers only the two **existing** plans' move (saas + doctrine-charter); the two new plans (WP02) were authored under `domains/` already and are out of the map (additive, not a rename).
- **Dependencies:** this WP runs LAST. WP02 must have created `domains/packs-extraction-domain-plan.md` + `domains/api-dashboard-domain-plan.md`; WP03–WP06 must have completed their retirements so the top-level index reconciliation reflects final state. Do NOT re-edit the section indexes (they are owned by the retire WPs) — only the **top-level** `docs/plans/index.md`.
- **`durable` requires WP01** (the moved plans get `doc_status: durable`).
- **`gh` auth:** `unset GITHUB_TOKEN` before any `gh` command.

### Subtask T028 — Move the two existing plans into domains/ (git mv) + flip to durable + reconcile references

1. `git mv docs/plans/saas-hosted-sync-domain-plan.md docs/plans/domains/saas-hosted-sync-domain-plan.md` and the same for `doctrine-charter-domain-plan.md`.
2. In each moved file: set frontmatter `doc_status: active → durable`; bump `updated: '2026-08-12'`.
3. **Reconcile the moved files' `related:` correctly.** Frontmatter `related:` entries are **repo-root-relative** (e.g. `docs/plans/index.md`, `docs/adr/3.x/...`), resolved against repo_root — so **do NOT add `../` depth**. Only rewrite entries that name the *other moved sibling* (`docs/plans/saas-hosted-sync-domain-plan.md` → `docs/plans/domains/saas-hosted-sync-domain-plan.md`, and vice-versa). Leave every other repo-relative `related:` entry byte-for-byte.
4. **Heal body inline links (the depth-sensitive class) with the tool, not by hand:** run `python scripts/docs/relative_link_fixer.py --write` — it heals move-broken bare-relative body links via the `occurrence_map.yaml` `moves:` spine (covers both relocations). Do not hand-edit body links.
5. **Reconcile the moved `doctrine-charter-domain-plan.md`'s references to WP04-retired pages (US1 trust goal).** This durable throughline `related:`-cites and body-links `docs/plans/doctrine/charter-activation-reachability-assessment.md`, `runtime-charter-doctrine-boundary.md`, and `next-slice-wheel-mission-types-public-api-research.md` — all flipped to `deprecated` by WP04. Do NOT leave the durable plan presenting retired notes as its live design corpus: reframe those references as historical records (or drop them). `related:` resolution still passes either way; this is a curation-correctness fix, not a gate fix. (WP04's activity log flags this hand-off.)

### Subtask T029 — Author domains/index.md

Create `docs/plans/domains/index.md` (frontmatter `doc_status: active`, `updated: '2026-08-12'`, resolvable `related:`) cataloguing all four throughlines (saas-hosted-sync, doctrine-charter, packs-extraction, api-dashboard) in one hop, with a one-line scope blurb each. This is the `domains/` cluster's self-catalog (US2: reachable in one hop). **Deliberately `doc_status: active`, NOT `durable`** — the index is a living navigation page whose contents change as throughlines are added; add a one-line comment/rationale so a later curator does not "fix" it to durable.

**Reference reconciliation for WP02's plans (folded into the T028 move sweep + T031):**

The `packs-extraction`/`api-dashboard` plans (authored by WP02, owned by WP02) reference `doctrine-charter-domain-plan.md` at its **pre-move** path for their §3.2/§3.6 boundary seams. After T028 moves it into `domains/`, those references break. `relative_link_fixer.py --write` (T028 step 4) heals bare-relative **body** links automatically; any **frontmatter `related:`** entry naming the old path must be repointed to `docs/plans/domains/doctrine-charter-domain-plan.md`. These two files are **not** in this WP's `owned_files` (to avoid an ownership-overlap gate failure with WP02) — editing them here is a **sanctioned out-of-owned-files bulk edit**: WP07 depends on WP02 so there is no concurrent writer (the no-overlap guard is satisfied), the change is a link-rewrite only, and it is in-scope of `occurrence_map.yaml`'s `domains/*-domain-plan.md` `related:` exception. Record the one-line rationale in the activity log.

### Subtask T030 — Top-level docs/plans/index.md: domains cluster + retire-index reconciliation (MERGED)

1. **Domains cluster:** repoint the two existing domain-plan links to `domains/...`, make the two `*(planned domain plan)*` slots (packs-extraction, api-dashboard) **live links** into `domains/`, add a `domains/index.md` link, and update the frontmatter `related:` list to the new paths.
2. **Retire-index reconciliation (the IC-02 half, merged here per the shared-file note):** the "Working collections (by area)" prose that describes now-retired clusters as live (e.g. "runtime/state overhaul", "surface-resolution clusters", "triage logs") must be reconciled to reflect the WP03–WP06 retirements — describe the sections by what remains live, not by retired clusters.
3. Keep `3-2-x-milestone-roadmap.md` in the index (it is retire-**deferred**, C-001) — only its link target may change if it moved (it did not); do not mark it retired.

### Subtask T031 — Release-doc cross-refs + roadmap links (C-001-safe)

Update the four `3-2-x-*` release docs so every reference to a moved plan resolves to `domains/...`:
- `3-2-x-approach.md` (4 refs), `3-2-x-executive-overview.md` (3), `3-2-x-open-core-delivery-plan.md` (3), `3-2-x-milestone-roadmap.md` (3 — **update links only; the roadmap itself stays live/deferred**).
Use `occurrence_map.yaml`'s `user_facing_strings: rename_if_user_visible` as the guide.

### Subtask T032 — Regenerate lockfiles + prove zero dead links

1. Regenerate the docs lockfiles (do NOT hand-edit them): `python scripts/docs/docs_index.py --write` and `python scripts/docs/inventory_lockfile.py --write` (confirm exact flags via `--help`; the inventory lockfile is `docs/development/3-2-page-inventory.yaml`, the retrieval index `docs/development/3-2-docs-retrieval-index.yaml`).
2. Prove zero dead links against the **real tree**, not just fixtures: run `python scripts/docs/relative_link_fixer.py --check` (the body-link authority over `docs/**/*.md`) and `python scripts/docs/related_validator.py` (frontmatter). Then the unit gates: `PWHEADLESS=1 python -m pytest tests/docs/test_relative_link_fixer.py tests/docs/test_related_validator.py tests/docs/test_docs_index.py tests/docs/test_inventory_lockfile.py tests/docs/test_docs_structural_lint.py -q`. Confirm both new plans present in the inventory and four throughlines reachable in one hop. (Confirm exact flags via `--help`; the `--check` run over the actual moved paths is the authority — do not rely on the unit test's synthetic fixtures alone.)
3. Full docs gate: `PWHEADLESS=1 python -m pytest tests/docs/ tests/architectural/test_no_legacy_terminology.py -q` (green) and `python scripts/docs/check_docs_freshness.py` (0 errors).

## Branch Strategy

Planning/base branch: `feat/docs-plans-tier3-closeout`. Merge target: `feat/docs-plans-tier3-closeout`. Worktrees per lane from `lanes.json`.

## Definition of Done

- All four domain plans live under `docs/plans/domains/`; the two moved plans carry `doc_status: durable`; `domains/index.md` catalogs all four (one-hop reachable from the plans index).
- Every reference to a moved plan resolves (zero dead links, proven by `relative_link_fixer.py --check` + `related_validator.py` over the real tree) — top-level index, the four `3-2-x-*` docs, the moved plans' `related:` lists, **and WP02's two new plans' references** (reconciled as a sanctioned out-of-owned-files edit); the two `*(planned)*` slots are now live links.
- The durable `doctrine-charter-domain-plan.md` no longer presents the three WP04-retired pages as its live design corpus (reframed as historical or dropped).
- Top-level `docs/plans/index.md` reflects both the domains cluster and the IC-02 retirements; the roadmap remains live (C-001).
- Lockfiles regenerated from frontmatter (not hand-edited); `occurrence_map.yaml` kept conformant.
- `tests/docs/` + terminology guard green; `check_docs_freshness.py` 0 errors.

## Reviewer guidance

- Verify the move used `git mv` (history preserved) and the two moved plans are `durable`, not `active`.
- Verify **zero** dead links via the relative-link-fixer + related-validator + lockfile-freshness gates (not by eyeballing).
- Verify the roadmap is still live (C-001) and only its links changed; confirm the lockfiles were regenerated, not hand-edited.
- Verify the top-level index's retire-reconciliation matches what WP03–WP06 actually retired (no cluster still described as live that was deprecated).
