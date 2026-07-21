---
work_package_id: WP02
title: Two-Zone Hierarchical Navigation Rebuild
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-015
tracker_refs: []
planning_base_branch: feat/docs-ia-onboarding-overhaul
merge_target_branch: feat/docs-ia-onboarding-overhaul
branch_strategy: Planning artifacts for this mission were generated on feat/docs-ia-onboarding-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-ia-onboarding-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: "claude:sonnet-5:curator-carla:reviewer"
history: []
agent_profile: curator-carla
authoritative_surface: docs/toc.yml
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/toc.yml
role: implementer
tags: []
shell_pid: "89676"
shell_pid_created_at: "1784569938.953445"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load curator-carla` (role: implementer). Then read, in order:
[spec.md](../spec.md) FR-003/FR-015/NFR-003, [plan.md](../plan.md) §IC-01, [research.md](../research.md)
item 6, [data-model.md](../data-model.md)'s `NavigationZone`/`NavigationGroup` entities, and
`docs-audit.md` (produced by WP01 — read it fresh, it has the final file locations).

## Objective

Rebuild `docs/toc.yml` into exactly two top-level zones — an end-user zone and a contributor
zone — each with 6 or fewer unexpanded top-level entries, using DocFX's native nested `items:`
syntax. This is pure navigation-configuration work: no content file is moved or edited here
(WP01 already did the moves this WP needs to reference).

## Context

- Today's `docs/toc.yml` has 16 top-level entries (verified count): Home, Context, Architecture,
  ADRs, Plans, API, Configuration, Integrations, Security, Guides, Operations, Migrations,
  Changelog, Release Goals, Mission Runs, and Historical Archive (which is already nested via
  `items:` — proof the mechanism works with zero pipeline changes, see research.md item 6).
- DocFX nested TOC precedent (do not deviate from this proven syntax):
  ```yaml
  - name: Historical Archive
    items:
      - name: Archive Overview
        href: archive/
      - name: Archive (2.x)
        href: archive/2x/
      - name: Archive (1.x)
        href: archive/1x/
  ```
- Zone assignment guidance (finalize using WP01's `docs-audit.md`, this is a starting default,
  not a rigid mandate): **end-user zone** — Home, Context (user-facing subset), API,
  Configuration, Integrations, Security, Guides (post-WP01 end-user remainder), Migrations,
  Changelog, Release Goals, and the new WP04/WP05/WP06 pages (Core Concepts, Charter, Doctrine).
  **Contributor zone** — Architecture, ADRs, Plans, Operations, Development (WP01's relocation
  target), Mission Runs. Historical Archive can sit under either zone or stand alone at the top
  level — use your judgment and record the choice; it's low-traffic reference material, not a
  correctness-critical assignment.
- Nothing here is set in stone except the requirement: end-user zone must never expose a
  contributor-only page (C-005), and each zone must have ≤6 unexpanded top-level entries
  (NFR-003).

## Subtask guidance

- **T006 — Design the group structure.** Before touching `toc.yml`, sketch the target tree: two
  top-level zone entries, and under each, ≤6 `NavigationGroup` children (each itself possibly
  nesting further — DocFX supports arbitrary depth). Write this design as a short section
  (append, don't overwrite) in `docs-audit.md` so the decision is recorded and reviewable before
  you touch the actual YAML.
- **T007 — Rebuild `docs/toc.yml`.** Replace the flat 16-entry list with the two-zone nested
  structure from T006. Every existing top-level section must land somewhere in the new tree —
  do not silently drop a section. Use the "Historical Archive" entry's existing syntax as your
  template for every nested group. Point `href` values at WP01's final (post-move) file
  locations — grep `docs-audit.md` for any file you're linking to confirm its current path.
- **T008 — Update child TOCs referencing moved paths.** Check whether any child `toc.yml` file
  (e.g. `docs/guides/toc.yml` if one exists, or similar per-section TOCs) has entries pointing
  at files WP01 relocated out of `docs/guides/` into `docs/development/`; update those
  references. `docs/development/` may need its own child `toc.yml` if it doesn't have one and
  the new file count warrants it — check the existing convention other sections use (e.g.
  `docs/api/toc.yml`) and follow it.
- **T009 — Validate structure and the C-005 cross-zone-leakage invariant.** Parse `docs/toc.yml`
  with a YAML loader to confirm it's valid
  (`python3 -c "import yaml; yaml.safe_load(open('docs/toc.yml'))"`). Manually walk the tree and
  count: exactly 2 top-level zone entries, ≤6 immediate children each. This is the explicit
  verification point for spec.md's C-005 invariant ("no end-user-zone page links into
  contributor-only content"): walk the nested tree from each end-user top-level group's subtree
  and confirm zero contributor-zone pages appear reachable within it (by reading the tree, not by
  building the site — no live DocFX build available locally).

## Branch Strategy

Planning artifacts were generated on `feat/docs-ia-onboarding-overhaul`. This WP branches from
that base during `/spec-kitty.implement`, after WP01 has landed, and merges back into
`feat/docs-ia-onboarding-overhaul`.

## Definition of Done

- [ ] `docs/toc.yml` is valid YAML with exactly 2 top-level zone entries.
- [ ] Each zone has ≤6 unexpanded top-level (immediate-child) entries.
- [ ] Every section from the original 16-entry flat list is represented somewhere in the new
      tree — nothing silently dropped.
- [ ] No `href` in the end-user zone's subtree points at a `docs/development/**` path.
- [ ] Any child TOC referencing a WP01-relocated path is updated.
- [ ] The T006 design rationale is recorded in `docs-audit.md`.

## Risks & Mitigations

- **Broken links from stale `href`s** if WP01's final file locations aren't rechecked before
  writing `toc.yml` — always read `docs-audit.md` fresh, don't rely on the pre-move file list in
  plan.md's Project Structure sketch.
- **Accidental cross-zone leak** — a contributor page nested under an end-user group would
  violate C-005. Double-check the zone assignment guidance above against WP01's actual
  dispositions before finalizing.

## Review Guidance

- Count top-level entries per zone yourself; don't trust a summary.
- Trace 3 random end-user-zone paths down to a leaf `href` and confirm none resolves into
  `docs/development/`.

## Activity Log

- {{TIMESTAMP}} – system – Prompt created.
- 2026-07-20T17:33:41Z – claude:sonnet-5:curator-carla:implementer – shell_pid=79881 – Assigned agent via action command
- 2026-07-20T17:51:48Z – claude:sonnet-5:curator-carla:implementer – shell_pid=79881 – Ready for review: docs/toc.yml rebuilt into two-zone hierarchy (2 zones, 6 children each), docs/development/toc.yml added, docs/guides/how-to-toc.yml updated, C-005 verified clean, all 16 original sections present, all hrefs resolve.
- 2026-07-20T17:52:21Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=89676 – Started review via action command
- 2026-07-20T17:56:09Z – user – shell_pid=89676 – Review passed: docs/toc.yml has exactly 2 top-level zones (Using Spec Kitty=6 children, Contributing=6 children), all 16 original sections independently re-derived as present, C-005 cross-zone check clean across docs/toc.yml AND all 3 reachable child TOCs under guides/ (no development/** hrefs anywhere in end-user subtree), docs/development/toc.yml is a perfect 1:1 match with the 17 non-index .md files in docs/development/, docs/guides/how-to-toc.yml no longer references any of WP01's 13 relocated files, relative_link_fixer.py --check reports 0 dead links, and the only out-of-scope diffs are expected status-bookkeeping files.
