---
work_package_id: WP04
title: Shadow-tree fold-then-delete
dependencies: []
requirement_refs:
- FR-003
- NFR-005
planning_base_branch: docs/common-docs-section-audit
merge_target_branch: docs/common-docs-section-audit
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-section-audit. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-section-audit unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-docs-structural-sanity-01KY53KJ
base_commit: aac68479d6dcdde4b46b6d4565acc4bcbc0f4d8d
created_at: '2026-07-22T16:59:14.559640+00:00'
subtasks:
- T018
- T019
- T020
- T021
history:
- timestamp: '2026-07-22T16:30:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/plans/notes/
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- docs/plans/notes/
- docs/architecture/feature-detection.md
- docs/architecture/gap-analysis-connector-installation-model.md
- docs/adr/3.x/adr-connector-auth-binding-separation.md
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – Shadow-tree fold-then-delete

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `curator-carla` profile via the `/ad-hoc-profile-load` skill.
Adopt its identity, governance scope, boundaries, and the initialization declaration it prints. Everything
below is authored for that profile: knowledge-base curation, single-canonical-copy discipline, distil unique
content before retiring a duplicate (never blind-delete). Do not begin editing until the profile is loaded
and its init declaration is on the record.

- **Profile**: `curator-carla`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Retire the `docs/plans/notes/` split-brain shadow tree (FR-003, NFR-005, SC-004). For EACH of the 3 drifted
shadows, the canonical twin **already exists** — so this is **FOLD-THEN-DELETE**, never `git mv`:

1. `diff` the shadow against its canonical twin;
2. PORT any unique content from the shadow INTO the existing canonical copy;
3. `git rm` the shadow;
4. correct the emptied `notes/` README.

**Referrer repointing + old-shadow→canonical redirects are WP05's sweep** — leave WP05 a note of the referrer
counts; do NOT touch `redirect_map.yaml` or run `relative_link_fixer` here.

**Success (NFR-005, SC-004)**: after this WP, `plans/notes/` no longer shadows any canonical basename; each
canonical twin carries the reconciled (union) content; no unique content is lost.

## Context & Constraints

- **Charter**: `.kittify/charter/charter.md` — single canonical copy, distil-then-retire, no blind-delete.
- **Read before editing**: `spec.md` (US3; FR-003; NFR-005; Edge Cases — "a shadow has DIVERGED, preserve
  unique content before deleting"), `plan.md` (IC-04), `research.md` (D4 — "FOLD-then-DELETE, NOT relocation;
  a mechanical `git mv shadow canonical` would CLOBBER the canonical — forbidden"), `occurrence_map.yaml`
  (the 3 FOLD-THEN-DELETE entries with `reason:` prefixed "FOLD-THEN-DELETE"), `quickstart.md` (Recipe B —
  the exact fold-then-delete sequence).
- **BINDING mechanic (D4)**: the `to:` target in each occurrence_map fold entry ALREADY EXISTS (it is the
  canonical twin that STAYS). The from→to pair is retained in the map ONLY so WP05's `redirect_stub_generator`
  derives old-shadow.html → EXISTING canonical.html. You must NEVER `git mv` — that clobbers the canonical.
- **Do NOT** touch `redirect_map.yaml`, the page-inventory, or `toc.yml`, and do NOT run `relative_link_fixer`
  / `bulk_ref_rewrite` — those are WP05's single-writer derived-artifact + referrer sweep. Hand WP05 the
  referrer counts.
- **No `git stash`, no branch-switching** in the lane worktree (shared stash stack / HEAD hazards).

## Branch Strategy

- **Strategy**: coord topology; execution worktree allocated per computed lane from `lanes.json`.
- **Planning base branch**: `docs/common-docs-section-audit`
- **Merge target branch**: `docs/common-docs-section-audit`

> Populated by `spec-kitty agent mission tasks` / `finalize-tasks`. Do not change manually.

## Subtasks & Detailed Guidance

### Subtask T018 — Fold-then-delete `feature-detection.md` [P]

- **Purpose**: FR-003 — reconcile the 396-line shadow into the 388-line canonical twin, then delete the shadow.
- **Steps**:
  1. `diff docs/plans/notes/feature-detection.md docs/architecture/feature-detection.md` — study every
     divergence. The shadow is 8 lines longer; identify what is UNIQUE to the shadow (not merely reordered).
  2. Port genuinely-unique/newer content from the shadow INTO `docs/architecture/feature-detection.md`
     (the canonical). Preserve the canonical's frontmatter/structure; merge prose thoughtfully — do not blindly
     concatenate. If the shadow is purely stale (older duplicate with nothing unique), record that and skip the
     port.
  3. `git rm docs/plans/notes/feature-detection.md`.
  4. Record the shadow's **5 docs referrers** (occurrence_map) in the Activity Log for WP05's repoint + the
     old-shadow→canonical redirect.
- **Files**: `docs/architecture/feature-detection.md` (canonical, edited), `docs/plans/notes/feature-detection.md`
  (removed).
- **Validation**: the shadow no longer exists; the canonical carries any unique content; no content regression
  in the canonical (its original content is intact).
- **Edge cases**: if the shadow's "unique" content is actually OUTDATED vs the canonical, keep the canonical's
  version and note the decision — newer/correct wins, not longer.

### Subtask T019 — Fold-then-delete `gap-analysis-connector-installation-model.md` [P]

- **Purpose**: FR-003 — reconcile the shadow into its canonical `architecture/` twin, then delete.
- **Steps**:
  1. `diff docs/plans/notes/gap-analysis-connector-installation-model.md docs/architecture/gap-analysis-connector-installation-model.md`.
  2. Port unique content INTO the canonical `docs/architecture/gap-analysis-connector-installation-model.md`.
  3. `git rm docs/plans/notes/gap-analysis-connector-installation-model.md`.
  4. Record the **1 docs referrer** for WP05.
- **Files**: `docs/architecture/gap-analysis-connector-installation-model.md` (canonical, edited), shadow
  removed.
- **Validation**: shadow gone; canonical holds the union content.
- **Edge cases**: same newer-wins rule as T018.

### Subtask T020 — Fold-then-delete `adr-connector-auth-binding-separation.md` (flag #2227) [P]

- **Purpose**: FR-003 — reconcile the 179-line shadow into the 177-line canonical ADR twin, then delete.
- **Steps**:
  1. `diff docs/plans/notes/adr-connector-auth-binding-separation.md docs/adr/3.x/adr-connector-auth-binding-separation.md`.
  2. Port unique content INTO the canonical `docs/adr/3.x/adr-connector-auth-binding-separation.md`. This file
     is an ADR — preserve MADR structure/status frontmatter; be conservative merging into an accepted ADR.
  3. **#2227 coordination (C-003)**: this ADR is part of #2227's census-tail (architecture-residuals). Flag in
     the Activity Log that the fold touched a #2227-adjacent ADR so the overlap is visible; do not expand scope
     into #2227's other residuals.
  4. `git rm docs/plans/notes/adr-connector-auth-binding-separation.md`.
  5. Record the **6 docs referrers** for WP05.
- **Files**: `docs/adr/3.x/adr-connector-auth-binding-separation.md` (canonical ADR, edited), shadow removed.
- **Validation**: shadow gone; canonical ADR holds the union content; MADR frontmatter intact.
- **Edge cases**: an ADR's status/decision must not be altered by the fold — only merge supporting content;
  if the shadow proposes a DIFFERENT decision, do NOT merge it — flag it for #2227 instead.

### Subtask T021 — Correct/remove the emptied `notes/` README

- **Purpose**: FR-003 — after the 3 folds, `plans/notes/` is emptied of shadows; its README must not advertise
  a shadow tree.
- **Steps**:
  1. Read `docs/plans/notes/README.md`. If the directory is now EMPTY of content pages (only the README
     remains), either (a) remove the directory entirely (`git rm docs/plans/notes/README.md` + the now-empty
     dir) OR (b) if `plans/notes/` legitimately retains other non-shadow content, rewrite the README to
     describe only what remains and drop any reference to the folded-out files.
  2. Confirm no `plans/notes/` basename still shadows a canonical twin (NFR-005) — this is what WP02's
     `shadow_tree_basename` check verifies in WP05's sweep.
- **Files**: `docs/plans/notes/README.md` (+ possibly the emptied directory).
- **Validation**: `ls docs/plans/notes/` shows no shadow content pages; the README (if kept) references only
  surviving content.
- **Edge cases**: if removing the dir, ensure no referrer points at `plans/notes/README.md` still needing a
  redirect — record any such referrer for WP05.

## Test Strategy

- No unit tests authored here (content ops). Verification is structural:
  `ls docs/plans/notes/` shows no shadow basenames; `git status` shows 3 `git rm`s + edits to the 3 canonical
  twins; the canonical twins retain their original content plus any unique folded-in content.
- The `shadow_tree_basename` lint + link/freshness gates run in **WP05's** aggregate sweep — not here.

## Risks & Mitigations

- **Clobbering the canonical** (D4): a `git mv shadow canonical` destroys the canonical — mitigate by strictly
  following fold-then-delete (edit canonical + `git rm` shadow); NEVER `git mv` in this WP.
- **Losing unique content** (Edge Case): diff BEFORE deleting; port unique content first — never blind-delete.
- **Altering an accepted ADR's decision** (T020): merge only supporting content; a divergent decision goes to
  #2227, not into the canonical ADR.
- **Editing derived artifacts**: staying in owned_files avoids colliding with WP05's redirect/inventory regen.

## Review Guidance (reviewer-renata / opus)

Verify: each shadow was `git rm`'d, NOT `git mv`'d (the canonical twins still exist with intact original
content); a diff-then-port is evidenced (unique shadow content is present in the canonical, or a note says the
shadow was purely stale); the ADR fold (T020) did not alter the ADR's decision/status and flags #2227; the
`notes/` README no longer advertises shadows; NO edits to `redirect_map.yaml`/inventory/`toc.yml`; referrer
counts handed to WP05 in the Activity Log.

## Activity Log

> **CRITICAL**: entries in chronological order (oldest first, newest last). Append at the END.

- 2026-07-22T16:30:00Z – system – Prompt created.
</content>
