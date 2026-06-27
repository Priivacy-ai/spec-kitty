---
work_package_id: WP10
title: Shadow-tree resolution — docs/1x+2x delete+redirect; docs/3x distil+move+redirect (C-004)
dependencies:
- WP03
- WP07
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T059
- T060
- T061
- T062
- T063
- T064
agent: "claude:opus:python-pedro:implementer"
history: []
agent_profile: python-pedro
authoritative_surface: docs/3x
create_intent: []
execution_mode: code_change
owned_files:
- docs/1x/**
- docs/2x/**
- docs/3x/**
role: implementer
tags: []
shell_pid: "1518600"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Resolve the three `docs/<version>x` shadow trees correctly (FR-008): `docs/1x` + `docs/2x` (true HTML snapshots) → **delete + redirect**; `docs/3x` (**live charter content**) → **distil + move + redirect, never blind-delete** (C-004 — a merge-blocker). Also verify-before-delete the 4 `docs/architecture/` orphans. This is IC-05d.

## Context

`occurrence_map.yaml` `exceptions` (`docs/1x/**`, `docs/2x/**` → `do_not_change` = delete+redirect, not path-rewrite) + `moves:` (`docs/3x` → `docs/context`) + the spec FR-008 are the authority.

- **`docs/1x` + `docs/2x`:** true HTML snapshots — delete + redirect (the captured baseline URLs anchor the redirect coverage, NFR-002). Do NOT path-rewrite in place.
- **`docs/3x`:** holds **live charter content** (`charter-overview.md`, `governance-files.md`, `index.md`). **Distil + move + redirect** into `docs/context/` — never blind-delete (C-004). Fix the **3 nav refs** (`toc.yml` / `llms.txt` / `index.md`). **Record the landing zone for #2053** (coordinate only — do not build the charter-landing implementation).
- **`docs/architecture/` orphans (4):** `adr-connector-auth-binding-separation.md`, `adr-github-app-installation-authority.md`, `feature-detection.md`, `gap-analysis-connector-installation-model.md`. The 2 connector-auth ADRs → promote to `docs/adr/3.x/` (per `moves:`); the other 2 → verify then promote or confirm a canonical home **before** deletion.

**Depends on WP07** so the deletes are paired with redirect entries (every deleted shadow URL must have a covering stub).

## Requirement refs (hints for the orchestrator's map-requirements)

FR-008 (shadow-tree resolution: 1x/2x delete+redirect, 3x distil+move+redirect, architecture orphans verify-before-delete), C-004 (3x never blind-deleted — merge-blocker).

## Subtasks

### T059 — Delete `docs/1x` + `docs/2x` with redirect entries
Confirm `docs/1x` + `docs/2x` are true HTML snapshots (no live source). Delete them; ensure every old shadow URL is represented as a redirect entry (WP07 derives the map from `moves:`/exceptions — confirm coverage, do not hand-edit WP07's map). The baseline URLs for these snapshots must resolve via a stub (NFR-002).

### T060 — Distil `docs/3x` live charter content
For `charter-overview.md`, `governance-files.md`, `index.md` in `docs/3x`: distil the durable charter content and move it into `docs/context/` (C-004 — never blind-delete). Preserve the live information; do not lose charter state.

### T061 — Fix the 3 `docs/3x` nav refs
Update the 3 navigation references (`toc.yml`, `llms.txt`, `index.md`) that point at `docs/3x` to the new `docs/context/` homes. A dangling nav ref is a broken link (NFR-004).

### T062 — Record the #2053 landing zone
Document where the `docs/3x` charter content landed post-distillation (for #2053 — coordinate only). Add the landing-zone note for the issue-matrix; do NOT build the charter-landing implementation.

### T063 — Verify-before-delete the 4 `docs/architecture/` orphans
Promote the 2 connector-auth ADRs (`adr-connector-auth-binding-separation.md`, `adr-github-app-installation-authority.md`) to `docs/adr/3.x/` (per `moves:`). For `feature-detection.md` + `gap-analysis-connector-installation-model.md`: verify content, then promote or confirm a canonical home before deleting. No blind delete.

### T064 — Verify + redirect coverage for the shadow deletes
Confirm no shadow tree (`docs/1x`/`2x`/`3x`) survives (single-root invariant, SC-001). Run WP07's coverage check including the shadow-tree redirect entries — every deleted shadow URL resolves via a stub. Terminology guard clean.

## Surfaces & Loci

| Surface | Resolution | Authority |
|---------|-----------|-----------|
| `docs/1x/**` | delete + redirect (true HTML snapshot) | `occurrence_map.yaml` exceptions `do_not_change` |
| `docs/2x/**` | delete + redirect (true HTML snapshot) | exceptions `do_not_change` |
| `docs/3x/**` (`charter-overview.md`, `governance-files.md`, `index.md`) | **distil + move + redirect** → `docs/context/` | `moves:`; C-004 merge-blocker |
| `docs/3x` nav refs in `toc.yml` / `llms.txt` / `index.md` | fix the 3 refs | FR-008 |
| `docs/architecture/adr-connector-auth-binding-separation.md`, `adr-github-app-installation-authority.md` | promote → `docs/adr/3.x/` | `moves:` |
| `docs/architecture/feature-detection.md`, `gap-analysis-connector-installation-model.md` | verify-before-delete (promote or home) | FR-008, C-004 |

Coordinate-only: #2053 (record the `docs/3x` charter landing zone — do not build the charter-landing implementation).

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-008 (1x/2x delete+redirect; 3x distil+move+redirect; orphans verify-before-delete) | T059, T060, T061, T063, T064 |
| C-004 (`docs/3x` never blind-deleted — merge-blocker) | T060, T062 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP03 (the move) + WP07 (redirect entries pair the deletes). Feeds WP14 (single-root invariant must hold before the ratchet flips blocking).

## Definition of Done

- [ ] `docs/1x` + `docs/2x` deleted; every old shadow URL covered by a redirect stub (NFR-002).
- [ ] `docs/3x` **distilled + moved + redirected** into `docs/context/` — **C-004 merge-blocker satisfied** (no blind delete; live charter content preserved); the 3 nav refs fixed.
- [ ] **Content-preservation proven, not presence:** assert the distilled `docs/context/` targets **contain the charter material** carried from `docs/3x` (the live `charter-overview.md` / `governance-files.md` / `index.md` headings + body present in the distilled output) — a redirect pointing at an empty or placeholder page is a C-004 violation. Show the source-section → preserved-content mapping, not just "destination file exists".
- [ ] The 4 `docs/architecture/` orphans **verified before deletion** — 2 connector-auth ADRs promoted to `docs/adr/3.x/`; the other 2 promoted or homed.
- [ ] **Redirect/back-compat in place so no URL breaks**: every deleted/moved shadow URL resolves via a WP07 stub; #2053 landing zone recorded.
- [ ] No shadow tree survives (single-root invariant, SC-001); terminology guard clean.

## Risks & Reviewer Guidance

- **Reviewer (C-004 merge-blocker focus):** confirm `docs/3x` was **distilled + moved**, not blind-deleted — the live charter content (`charter-overview.md`, `governance-files.md`, `index.md`) must be present in `docs/context/`.
- **An orphan deleted without verification** could lose a real ADR (the 2 connector-auth ADRs especially) — verify-before-delete.
- **A shadow delete without a redirect entry** is a dead public URL — pair every delete with WP07 coverage.

## Activity Log

- (populated at implement time)
- 2026-06-27T14:35:39Z – claude:opus:python-pedro:implementer – shell_pid=1518600 – Assigned agent via action command
- 2026-06-27T15:20:50Z – claude:opus:python-pedro:implementer – shell_pid=1518600 – shadow trees: 1x/2x deleted→archive-redirect, 3x distilled→context (C-004 verbatim content-preservation mapping), 4 orphans handled (2 ADRs promoted, 2 homed), single-root SC-001, 11/11 redirect tests
- 2026-06-27T15:27:19Z – user – shell_pid=1518600 – Review passed: 1x/2x deleted+redirect-covered (13 archive redirects; deleted shadows were meta-refresh stubs, live .md twins in docs/archive/{1x,2x}), 3x DISTILLED into context (C-004 content-preservation INDEPENDENTLY verified — charter-overview.md & governance-files.md byte-identical blobs d042269/ebcb6cd, index.md fully folded with all 13 links+sections; nav toc/llms/index repoint to context/, no 3x survives), 4 orphans verified+homed (2 connector-auth ADRs promoted to docs/adr/3.x/, feature-detection+gap-analysis in docs/architecture/), single-root SC-001 confirmed (docs/1x|2x|3x GONE), terminology guard green. Redirect suite 10/11 green; the 1 failure (test_committed_redirect_map_is_diff_stable) is a PROVEN orchestrator-reset artifact (df709272d wiped lane occurrence_map) — re-derived against WP10 canonical occurrence_map at c1d5a9584 yields 16==16 MATCH. #2053 landing zone coordinate-only. Flags assessed: 3->16 re-pin legitimate; ~30 dangling 3x prose links=WP08; docfx 3x block=WP09.
