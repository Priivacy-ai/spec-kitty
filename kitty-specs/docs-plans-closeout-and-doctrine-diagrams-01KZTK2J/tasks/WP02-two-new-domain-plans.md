---
work_package_id: WP02
title: Author packs-extraction + api-dashboard domain plans with boundary seams (IC-03)
dependencies:
- WP01
requirement_refs:
- C-003
- FR-003
- FR-004
planning_base_branch: feat/docs-plans-tier3-closeout
merge_target_branch: feat/docs-plans-tier3-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/docs-plans-tier3-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-plans-tier3-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
history:
- at: '2026-08-12'
  note: Authored by /spec-kitty.tasks (post-plan-squad model). IC-03, depends on IC-01 (plans carry doc_status durable).
agent_profile: curator-carla
authoritative_surface: docs/plans/domains/
create_intent:
- docs/plans/domains/packs-extraction-domain-plan.md
- docs/plans/domains/api-dashboard-domain-plan.md
execution_mode: code_change
owned_files:
- docs/plans/domains/packs-extraction-domain-plan.md
- docs/plans/domains/api-dashboard-domain-plan.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load curator-carla
```

Apply its initialization, boundaries, directives, and tactics. Then read this WP, `spec.md` (FR-003, FR-004, C-003, US2), `plan.md` (IC-03), `research.md` (D3), and the existing `docs/plans/doctrine-charter-domain-plan.md` §3.2 and §3.6 (the sections these plans must non-goal against) plus `docs/plans/saas-hosted-sync-domain-plan.md` (structural template).

## Objective

Author the two remaining domain-plan throughlines — `packs-extraction` and `api-dashboard` — **directly under `docs/plans/domains/`**, each carrying `doc_status: durable`, in the canonical §1–§6 domain-plan shape, and each declaring an **explicit scope boundary (non-goal)** against the doctrine-charter plan so the four throughlines do not overlap.

## Context

- **These plans are authored in `docs/plans/domains/` from the start** (not in `docs/plans/` then moved). IC-04 (WP for the migration) creates `docs/plans/domains/index.md` and moves the two *existing* plans in; it depends on this WP so the four plans co-exist before the index is written. Creating a file under `docs/plans/domains/` will create the directory.
- **Both carry `doc_status: durable`** (requires WP01 landed). Mirror the frontmatter shape of `docs/plans/saas-hosted-sync-domain-plan.md`: `title`, `description` (≤180 chars), `doc_status: durable`, `updated: '2026-08-12'`, and a `related:` list of resolvable repo-relative `.md` paths.
- **`related:` path caution (structural lint):** every `related:` entry must resolve to an existing `.md`. Since these plans sit under `docs/plans/domains/`, sibling references to the other domain plans use the `domains/` paths (e.g. `docs/plans/domains/doctrine-charter-domain-plan.md`) — but the doctrine-charter plan is not moved until IC-04. To avoid a dangling `related:` at this WP's commit, reference the doctrine-charter plan at its **current** path `docs/plans/doctrine-charter-domain-plan.md`; IC-04's occurrence map will rewrite it during the move. Record this in the activity log so IC-04's link sweep expects it.
- **Terminology canon (C-003):** use **Mission**, never "feature". The api-dashboard plan documents eliminating the `Feature:` UI drift (#650) as a goal — reference it as the drift being killed, never reintroduce `Feature:` as live language.

### Subtask T007 — `packs-extraction-domain-plan.md` (physical extraction lineage)

**Purpose**: A durable throughline for the **physical extraction / modularization** of the doctrine layer.

**Steps**:
1. Create `docs/plans/domains/packs-extraction-domain-plan.md` with durable frontmatter.
2. Body in the §1–§6 shape (mirror doctrine-charter-domain-plan.md):
   - **§1 Purpose & scope** — the physical extraction/modularization lineage: the standalone `spec-kitty-doctrine` module boundary (evidence: `src/doctrine/pyproject.toml` already exists), the charter↔doctrine import-cycle blocker, in-place strangler cutover, and repo-split transparency.
   - **§2 Where this lives today (honest inventory)** — cite `docs/plans/3-2-x-open-core-delivery-plan.md` §2.2–2.3 and the standalone `src/doctrine/pyproject.toml`.
   - **§3 Standing concerns (durable spine)** — the module boundary, import-cycle break, tier/pack physical packaging (epics #2466 / #2539 / #2216).
   - **§4 Known gaps**, **§5 Release-scoped view**, **§6 Cross-references**.
   - **Explicit boundary / non-goal (FR-003, mandatory):** a clearly-labelled statement that this plan is the **physical code extraction / modularization** lineage and explicitly **non-goals** the doctrine-charter plan's **§3.2 (doctrine/charter extensibility & the pack ecosystem)** — which owns the *authoring/governance* extensibility model (pack tiers, DRG merge semantics, `enhances`/`overrides`), NOT the physical repo/module split. Cross-link §3.2 so the seam is navigable.

**Files**: `docs/plans/domains/packs-extraction-domain-plan.md` (new).

### Subtask T008 — `api-dashboard-domain-plan.md` (application/mission-data API + dashboard)

**Purpose**: A durable throughline for the **application/mission-data API (#645) and dashboard/UX (#650)**.

**Steps**:
1. Create `docs/plans/domains/api-dashboard-domain-plan.md` with durable frontmatter.
2. Body in the §1–§6 shape:
   - **§1 Purpose & scope** — the application/mission-data API surface (#645, Epic: Stable Application API Surface) and the dashboard/UX surface (#650), including killing the `Feature:` UI-label drift (#650) in favour of the Mission canon.
   - **§2–§6** as above (honest inventory, standing concerns, gaps, release-scoped view, cross-references).
   - **Explicit boundary / non-goal (FR-004, mandatory):** a clearly-labelled statement that this plan owns the **application/mission-data API + dashboard** and explicitly **non-goals** the doctrine-charter plan's **§3.6 (stable public API surface for doctrine & charter)** — a *different* API: §3.6 is the `runtime → charter → doctrine` **Python import surface / single-entry-point** for the doctrine modules (#3179), whereas this plan is the **application data API consumed by the dashboard**. Name the disambiguation explicitly (two things called "API") and cross-link §3.6. Note that §3.6's #3179 reconciles its epic home to #645 — so state precisely which slice of #645 lives here (the application/mission-data surface + dashboard) vs there (the doctrine module import surface).

**Files**: `docs/plans/domains/api-dashboard-domain-plan.md` (new).

### Subtask T009 — Validate frontmatter + links + terminology

**Purpose**: Prove both plans pass the docs gates at this WP's boundary.

**Steps**:
1. Run `PWHEADLESS=1 python -m pytest tests/docs/test_related_validator.py tests/docs/test_description_length_gate.py tests/docs/test_docs_structural_lint.py -q` — both new plans pass (`related:` resolves, `description` ≤180, `doc_status: durable` accepted, frontmatter contract met).
2. Run `pytest tests/architectural/test_no_legacy_terminology.py -q` (must stay green) — **but note this guard does NOT scan for `feature`/`Feature:`** (it enforces `ceremony`→`status commit` and a lane-consolidation phrase only). C-003 is therefore **reviewer-verified, not gate-enforced**: when documenting the #650 UI drift, describe it as the `Feature`-labelled UI drift (never write a bare live `Feature:` token as if it were canonical), then `rg -n 'Feature:' docs/plans/domains/api-dashboard-domain-plan.md` and confirm every hit is inside a clearly-historical/quoted "the drift being killed" context.
3. Do NOT regenerate the docs lockfiles here — that is IC-04's job (the new pages will be added to the inventory during the migration WP's regeneration).

**Files**: none.

## Branch Strategy

Planning/base branch: `feat/docs-plans-tier3-closeout`. Final merge target: `feat/docs-plans-tier3-closeout`. Execution worktrees are allocated per computed lane from `lanes.json`.

## Definition of Done

- Both plans exist under `docs/plans/domains/` with `doc_status: durable` and canonical §1–§6 structure.
- packs-extraction carries an explicit non-goal against doctrine-charter §3.2; api-dashboard carries an explicit non-goal against §3.6 — each cross-linked and each disambiguating the shared word ("packs" / "API").
- `related:` entries all resolve at this WP's commit; `description` ≤180; terminology guard green; C-003 reviewer-verified — no bare live `Feature:` token used as canonical (the `rg` check recorded).

## Reviewer guidance

- Verify the boundary statements are **concrete** (name the specific overlapping section and what is in/out), not a generic "see also".
- Verify durable frontmatter (proves WP01 landed) and that the plans do not duplicate the doctrine-charter §3.2/§3.6 content — they point at it.
- **C-003 has no automated backstop** (the terminology guard does not scan `Feature`): independently `rg -n 'Feature' docs/plans/domains/api-dashboard-domain-plan.md` and confirm no hit reads as live canonical UI language.
- Confirm no docs-lockfile edits leaked in (that is IC-04's owned surface).
