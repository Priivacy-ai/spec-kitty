---
work_package_id: WP16
title: Divio re-section — fold the 120 Divio pages into the 13-section structure (FR-009 IC-01 correction)
dependencies:
- WP03
- WP04
- WP07
requirement_refs:
- FR-001
- FR-009
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T092
- T093
- T094
- T095
- T096
- T097
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: docs/api
create_intent: []
execution_mode: code_change
owned_files:
- docs/how-to/**
- docs/tutorials/**
- docs/reference/**
- docs/explanation/**
- docs/recovery/**
- docs/api/**
role: implementer
tags: []
shell_pid: "1572867"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Fold the **existing docs/ Divio dirs (120 pages)** into the 13-section structure per **FR-009** — the IC-01 correction the original `moves:` spine missed (surfaced by WP09's review: without it, these 120 pages orphan and `guides/`/`api/` stay permanently empty). Map per the now-added `moves:` pairs:

- `docs/how-to/` (67) + `docs/tutorials/` (9) → **`docs/guides/`**
- `docs/reference/` (22) → **`docs/api/`** (new section)
- `docs/explanation/` (20) → **`docs/architecture/`** (the unified living design from WP03)
- `docs/recovery/` (2) → **`docs/operations/`** (WP04's ops content)

This runs after WP03 (created the section homes), WP04 (created `guides/`+`operations/`), and WP07 (the redirect generator + its baseline) — because the Divio dirs are **PUBLISHED** (120 of WP02's 168 baseline URLs), so their relocation **requires redirect stubs** (NFR-002), and this WP regenerates WP07's redirect map to cover them.

## Context

`occurrence_map.yaml` `moves:` now carries the 4 Divio pairs (the "Divio → 13-section re-section (FR-009)" block — IC-01 correction). Execute exactly those pairs.

**Ownership (occurrence-map-governed leeway):** this WP **owns the 5 Divio SOURCE dirs** (`how-to`/`tutorials`/`reference`/`explanation`/`recovery`) **+ the new `docs/api/`** (its unique destination). It also writes into `docs/guides/`, `docs/operations/` (WP04-owned) and `docs/architecture/` (WP03-owned) and regenerates `scripts/docs/redirect_map.yaml` (WP07-owned) — those are **sequenced leeway** edits (this WP runs strictly after WP03/WP04/WP07), declared NOT in `owned_files` so finalize does not lane-collapse them. The dependency ordering guarantees the targets exist before the merge.

**N→1 merge hazard:** how-to + tutorials both land in `guides/`, and explanation merges into the WP03-populated `architecture/`. Disambiguate any filename collision **data-preservingly** (never overwrite a destination file). If two sources collide on a name, keep both (suffix one) and flag it — mirror WP03's era-suffix precedent.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-001 (re-section the existing `docs/` Divio subdirs into the 13-section structure), FR-009 (the Divio→guides/api/architecture/operations source→target mapping).

## Subtasks

### T092 — Move how-to + tutorials → `docs/guides/`
`git mv` every page from `docs/how-to/` and `docs/tutorials/` into `docs/guides/`. Both Divio types are task/learning oriented → guides. Collision-safe (no overwrite; suffix + flag on a name clash). `docs/guides/` already has WP04's content + `index.md` — merge, don't clobber.

### T093 — Move reference → `docs/api/`
`git mv` `docs/reference/` pages into the new `docs/api/` section. Create `docs/api/index.md` (section landing). This is the section that was empty in WP09's docfx globs — this WP fills it.

### T094 — Move explanation → `docs/architecture/`
`git mv` `docs/explanation/` pages into `docs/architecture/` (the unified living design WP03 populated). **Watch for name collisions** with WP03-landed files (e.g. a generic `index.md` / `README.md`) — preserve both data-preservingly. The explanation content is the "why" layer of the living architecture.

### T095 — Move recovery → `docs/operations/`
`git mv` the 2 `docs/recovery/` runbooks into `docs/operations/` (joins WP04's ops runbooks). Collision-safe.

### T096 — Regenerate the redirect map + re-verify coverage (NFR-002)
The Divio dirs were published, so their old URLs need redirects. **Re-run WP07's `scripts/docs/redirect_stub_generator.py` regenerate-map** so `redirect_map.yaml` now includes the Divio→new-section pairs (it derives from `moves:`, which now has them). Re-run the coverage check against WP02's 168-URL baseline — the ~120 Divio URLs must now be **covered** (directly or via stub). Confirm no stub points at a 404. Each new/merged section (`guides`, `api`, `operations`, `architecture`) carries an `index.md`.

### T097 — Verify the re-section + suite green
**Source→dest reconciliation:** every moved file's destination byte-matches its source (no data loss); source count == dest count; the 5 Divio source dirs are empty/removed. No live reference points at a removed `docs/{how-to,reference,explanation,tutorials,recovery}/` path that isn't redirect-covered (WP08's bulk rewrite — which now sees the Divio `moves:` — handles the in-tree refs; flag any it would miss). Terminology guard green; `ruff` on the regenerated map/script clean.

## Surfaces & Loci (from `occurrence_map.yaml` `moves:` — Divio block)

| From | To | Count | Notes |
|------|----|-------|-------|
| `docs/how-to` + `docs/tutorials` | `docs/guides` | 67 + 9 | merge into WP04's guides |
| `docs/reference` | `docs/api` | 22 | new section (fills WP09's empty glob) |
| `docs/explanation` | `docs/architecture` | 20 | merge into WP03's living design |
| `docs/recovery` | `docs/operations` | 2 | join WP04's ops |
| `scripts/docs/redirect_map.yaml` | — | regen | re-derived to cover the 120 Divio URLs (leeway, WP07-owned) |

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-001 (re-section existing Divio subdirs into 13-section) | T092, T093, T094, T095 |
| FR-009 (Divio→guides/api/architecture/operations mapping) | T092, T093, T094, T095, T096 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP03 (section homes), WP04 (guides/operations exist), WP07 (redirect generator + baseline). Lands before WP08 (refs) / WP12 (frontmatter) / WP14 (rulers full-gate) — they depend on WP16 so the assembled tree is complete.

## Definition of Done

- [ ] All 120 Divio pages moved per the `moves:` Divio block (how-to+tutorials→guides, reference→api, explanation→architecture, recovery→operations); the 5 source dirs empty/removed.
- [ ] **Source→dest reconciliation:** every destination byte-matches its source; source count == dest count; no data loss; N→1 collisions disambiguated data-preservingly (no overwrite).
- [ ] **`docs/api/` created + populated** (fills WP09's previously-empty glob); each merged section keeps its `index.md`.
- [ ] **Redirect coverage restored:** WP07's `redirect_map.yaml` regenerated from the updated `moves:`; the ~120 published Divio URLs are covered against WP02's 168 baseline; no stub→404.
- [ ] **No reference/runtime break:** WP08's bulk rewrite (depends on WP16) covers in-tree refs to the moved Divio paths via the new `moves:`; flag any ref it would miss as an IC-01 gap.
- [ ] Terminology guard + `ruff` clean.

## Risks & Reviewer Guidance

- **Reviewer (data-loss focus):** the N→1 merges (how-to+tutorials→guides; explanation→architecture-with-WP03-content) are the collision risk — confirm zero overwrites via source→dest byte reconciliation.
- **Redirect coverage** — the Divio dirs ARE published; confirm the regenerated redirect_map covers all 120 (a dropped redirect is a dead public URL).
- **Leeway boundary** — confirm WP16 only ADDED Divio content to guides/operations/architecture (did not disturb WP04/WP03's already-landed files) and only regenerated (not hand-edited) the redirect_map.

## Activity Log

- (populated at implement time)
- 2026-06-27T14:35:49Z – claude:opus:python-pedro:implementer – shell_pid=1518600 – Assigned agent via action command
- 2026-06-27T15:07:22Z – claude:opus:python-pedro:implementer – shell_pid=1518600 – Divio re-section: 125 files moved (byte-reconciled), docs/api populated, redirect_map regenerated (120 Divio URLs covered), 8 scaffold collisions prefix-disambiguated
- 2026-06-27T15:07:38Z – claude:opus:reviewer-renata:reviewer – shell_pid=1572867 – Started review via action command
- 2026-06-27T15:13:07Z – user – shell_pid=1572867 – Review passed: 125 moves byte-reconciled, 8 scaffold-only collisions prefix-disambiguated (0 content loss, 0 overwrites), docs/api populated, redirect_map covers 120 Divio URLs vs baseline, leeway clean
