---
work_package_id: WP03
title: Point-in-time redistribution + architecture index
dependencies: []
requirement_refs:
- C-001
- C-002
- FR-001
- FR-002
- FR-004
- FR-005
planning_base_branch: docs/common-docs-section-audit
merge_target_branch: docs/common-docs-section-audit
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-section-audit. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-section-audit unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-docs-structural-sanity-01KY53KJ
base_commit: 0361d2f2d6b4717e7b2c64933d122f952b29cc74
created_at: '2026-07-22T16:59:05.290674+00:00'
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
history:
- timestamp: '2026-07-22T16:30:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/architecture/
create_intent:
- docs/plans/engineering-notes/883-research-synthesis.md
- docs/plans/engineering-notes/883-mission-type-authority-brief.md
- docs/plans/engineering-notes/architecture-audits/
- docs/plans/engineering-notes/code-as-a-crime-scene-overview.md
- docs/plans/engineering-notes/teamspace-mission-state-920-closeout.md
execution_mode: code_change
model: sonnet
owned_files:
- docs/architecture/883-research-synthesis.md
- docs/architecture/883-mission-type-authority-brief.md
- docs/architecture/audits/
- docs/architecture/assessments/code-as-a-crime-scene-overview.md
- docs/architecture/index.md
- docs/migrations/teamspace-mission-state-920-closeout.md
- docs/plans/engineering-notes/883-research-synthesis.md
- docs/plans/engineering-notes/883-mission-type-authority-brief.md
- docs/plans/engineering-notes/architecture-audits/
- docs/plans/engineering-notes/code-as-a-crime-scene-overview.md
- docs/plans/engineering-notes/teamspace-mission-state-920-closeout.md
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – Point-in-time redistribution + architecture index

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `curator-carla` profile via the `/ad-hoc-profile-load` skill.
Adopt its identity, governance scope, boundaries, and the initialization declaration it prints. Everything
below is authored for that profile: knowledge-base/doc-tree curation, canonical-home discipline,
distil-then-retire, evidence-recorded adjudication. Do not begin editing until the profile is loaded and its
init declaration is on the record.

- **Profile**: `curator-carla`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Relocate the 9 firm point-in-time architecture artifacts to `docs/plans/engineering-notes/` (FR-001),
adjudicate the 2 FR-002 borderlines with a recorded verdict (default STAYS unless verified point-in-time),
and refresh `architecture/index.md` to full post-move section membership (FR-004). This WP does the **content
moves + index only** — redirect-map regeneration, relative-link repointing, page-inventory/toc regen, and the
one non-docs referrer sweep are **WP05's job**. Do NOT touch `redirect_map.yaml` here.

**Success criteria (SC-001, SC-005)**:
- `architecture/` holds no dated/point-in-time dossier (the 9 firm files are under `engineering-notes/`).
- Each borderline (assessment + closeout) carries a one-line recorded verdict; a file moves ONLY if verified
  point-in-time.
- `architecture/index.md` enumerates 100% of the post-move section membership.

## Context & Constraints

- **Charter**: `.kittify/charter/charter.md` — canonical homes, campsite cleaning, evidence-backed decisions.
- **Read before editing**: `spec.md` (US1, US4, US5; FR-001/002/004/005; SC-001/005; Edge Cases),
  `plan.md` (IC-03, IC-05), `research.md` (D3 redistribution homes, D4 borderline handling),
  `occurrence_map.yaml` (the `moves:` spine + the commented BORDERLINE note — the authoritative move list),
  `data-model.md` (bucket→home table), `docs/adr/3.x/2026-06-27-1` (Common-Docs reconciliation ADR: D7
  distil-then-retire → engineering-notes).
- **Move mechanic**: these are genuine RELOCATIONS (target does NOT yet exist) → `git mv`. This is NOT the
  fold-then-delete case (that is WP04). Use `git mv` so history follows the file.
- **C-001 (guides boundary)**: nothing moves into `docs/guides/`. Destinations are `engineering-notes/` only.
- **C-002 / D3**: the 7 audits land grouped as `engineering-notes/architecture-audits/` to preserve provenance.
- **Coordinate (C-003)**: the `docs-ia-onboarding-overhaul` mission owns `guides/`; #2227 owns
  architecture-residuals; #2215 owns era-suffixed READMEs — do not double-move into their scope.
- **Non-docs referrer (hand-off)**: `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml:50`
  references a moved audit path. `relative_link_fixer` walks `docs/**` ONLY and will NOT catch it — leave it
  for **WP05's** `bulk_ref_rewrite`/manual sweep (occurrence_map records it as `manual_review`). Note it in
  your Activity Log so WP05 does not miss it.
- **Do NOT** run redirect/link tooling or edit `redirect_map.yaml` / the page-inventory / `toc.yml` — WP05
  owns the derived-artifact work (and this mission does NOT regenerate `redirect_map.yaml` at all — PB2). Your
  job ends at the moves + `index.md` + `related:` frontmatter on the files you moved.
- **You DO own `occurrence_map.yaml`'s `moves:` spine for borderline promotion (PC6):** if T015/T016 verify a
  borderline as point-in-time and MOVE it, promote that file into the `moves:` spine (add the `from`/`to`/`reason`
  entry, remove it from the commented BORDERLINE note). This is the ONLY edit WP03 makes to `occurrence_map.yaml`
  — never touch `redirect_map.yaml` (derived, and not regenerated by this mission).

## Branch Strategy

- **Strategy**: coord topology; execution worktree allocated per computed lane from `lanes.json`.
- **Planning base branch**: `docs/common-docs-section-audit`
- **Merge target branch**: `docs/common-docs-section-audit`

> Populated by `spec-kitty agent mission tasks` / `finalize-tasks`. Do not change manually.

## Subtasks & Detailed Guidance

### Subtask T012 — Relocate `883-research-synthesis.md` [P]

- **Purpose**: FR-001 — the self-declared point-in-time pre-spec research for #883 leaves living-design.
- **Steps**:
  1. `git mv docs/architecture/883-research-synthesis.md docs/plans/engineering-notes/883-research-synthesis.md`.
  2. Update the moved file's `related:` frontmatter edges so paths resolve from the new location (relative
     `../` depth changes moving from `architecture/` to `plans/engineering-notes/`). Fix only the frontmatter
     on the MOVED file; broad referrer repointing is WP05.
  3. Scrub any now-stale "lives under architecture/" self-reference in its own prose.
- **Files**: `docs/architecture/883-research-synthesis.md` → `docs/plans/engineering-notes/883-research-synthesis.md`.
- **Validation**: file exists at the new path; `git status` shows a rename; 0 referrers per occurrence_map
  (this file has 0 docs referrers) so no external repoint needed here.
- **Edge cases**: none — 0 referrers.

### Subtask T013 — Relocate `883-mission-type-authority-brief.md` [P]

- **Purpose**: FR-001 — dated mission dossier, not living design.
- **Steps**:
  1. `git mv docs/architecture/883-mission-type-authority-brief.md docs/plans/engineering-notes/883-mission-type-authority-brief.md`.
  2. Fix the moved file's `related:` frontmatter for the new depth; scrub stale self-location prose.
  3. This file has **2 docs referrers** (occurrence_map) — do NOT repoint them here (WP05), but LIST them in
     your Activity Log so WP05's sweep is checkable.
- **Files**: `docs/architecture/883-mission-type-authority-brief.md` → `docs/plans/engineering-notes/883-mission-type-authority-brief.md`.
- **Validation**: rename recorded; new path exists.
- **Edge cases**: none beyond the 2 referrers handed to WP05.

### Subtask T014 — Relocate the `architecture/audits/` directory (7 files) [P]

- **Purpose**: FR-001 — 7 dated 2026-05 CaaCS forensic audits / triage / issue-draft dumps are point-in-time,
  not living design.
- **Steps**:
  1. `git mv docs/architecture/audits docs/plans/engineering-notes/architecture-audits` (moves all 7 files:
     `2026-05-11-findings-vs-issues-update.md`, `2026-05-11-issue-992-984-audit-comments.md`,
     `2026-05-822-crosscheck.md`, `2026-05-caacs-meta-assessment.md`,
     `2026-05-phase3-f1-knowledge-capture-plan.md`, `2026-05-phase3-issue-drafts-and-triage.md`,
     `2026-05-spec-kitty-caacs.md`).
  2. Fix `related:` frontmatter on each moved file for the new depth; scrub stale self-location prose.
  3. **Hand-off (critical)**: `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml:50`
     references `docs/architecture/audits/2026-05-spec-kitty-caacs.md` — a NON-docs referrer
     `relative_link_fixer` will never see. Record this explicitly in the Activity Log for **WP05's**
     `bulk_ref_rewrite`/manual sweep. This directory has **11 docs referrers** — list them for WP05 too.
- **Files**: `docs/architecture/audits/` → `docs/plans/engineering-notes/architecture-audits/`.
- **Validation**: the `audits/` dir no longer exists under `architecture/`; all 7 files present under
  `engineering-notes/architecture-audits/`; `git status` shows the directory rename.
- **Edge cases**: preserve the folder grouping (do not scatter the 7 files); the non-docs paradigm referrer
  MUST be handed to WP05 — a missed rewrite there breaks `check_docs_freshness`/link integrity later.

### Subtask T015 — FR-002 adjudicate the crime-scene assessment (DEFAULT STAYS)

- **Purpose**: FR-002 — the assessment defaults to STAYS; move ONLY if verified point-in-time. No force-move.
- **Steps**:
  1. Open `docs/architecture/assessments/code-as-a-crime-scene-overview.md`. Read it and decide: is it a
     **durable explainer** (a living methodology/overview that belongs in `architecture/`) OR a **pointer to
     the dated audits** (point-in-time residue that should follow the audits to `engineering-notes/`)?
  2. **Record a one-line verdict** in the Activity Log with the evidence (e.g. "STAYS — durable explainer of
     the CaaCS method, not tied to the 2026-05 run" OR "MOVE — verified point-in-time, only cross-references
     the dated audits").
  3. **If STAYS (default)**: do nothing to the file (leave it in `architecture/`; it will be captured by
     `index.md` in T017, incl. as an `assessments/` subdir page — PC3). **If MOVE (verified only)**: `git mv`
     it to `docs/plans/engineering-notes/code-as-a-crime-scene-overview.md`, fix `related:`, note its **2 docs
     referrers** for WP05, AND **promote it into `occurrence_map.yaml`'s `moves:` spine** (PC6 — WP03 owns the
     map's `moves:` spine when a borderline is promoted; add the `from`/`to`/`reason` entry and remove it from
     the commented BORDERLINE note). The assessment is a never-published in-repo path, so its move needs only
     referrer repointing (WP05 T024), no redirect.
- **Files**: `docs/architecture/assessments/code-as-a-crime-scene-overview.md` (and its engineering-notes
  destination ONLY if verified point-in-time); `occurrence_map.yaml` (only if promoted to MOVE).
- **Validation**: a recorded verdict exists; the file's location matches the verdict.
- **Edge cases**: absent clear point-in-time evidence, it STAYS — do not move on suspicion (FR-002 binding).

### Subtask T016 — FR-002 adjudicate the migrations closeout (DEFAULT STAYS)

- **Purpose**: FR-005/FR-002 — the `…-920-closeout.md` defaults to STAYS; move ONLY if verified point-in-time
  (a dated one-mission closeout in the runbook zone).
- **FR-005 satisfaction (PC4):** FR-005 is satisfied by the **recorded FR-002 verdict per SC-001** — NOT by an
  unconditional move. US5's acceptance ("`migrations/` holds no closeout") applies **only when the file is
  verified point-in-time** and thereby moves; if the recorded verdict is STAYS (default, absent point-in-time
  evidence), FR-005 is satisfied by the recorded decision and the file remains — do not force the move to
  "achieve" US5.
- **Steps**:
  1. Open `docs/migrations/teamspace-mission-state-920-closeout.md`. Decide: reusable runbook (STAYS) OR dated
     one-mission closeout evidence (verified point-in-time → MOVE to
     `docs/plans/engineering-notes/teamspace-mission-state-920-closeout.md`).
  2. **Record a one-line verdict** with evidence in the Activity Log.
  3. **If MOVE (verified)**: `git mv`, scrub point-in-time residue, fix `related:`, note its **4 docs
     referrers**, and **promote it into `occurrence_map.yaml`'s `moves:` spine** (PC6). **CRITICAL redirect
     caveat (PB2):** UNLIKE the other moves, the 920-closeout URL **IS** in `redirect_baseline_urls.json`
     (published) — and this mission does **NOT** regenerate `redirect_map.yaml` (regenerating would wipe the
     landed `01KW3SBK` 149 redirects), so moving this file would 404 its baseline URL with no redirect to
     catch it. Therefore a closeout MOVE is **NOT a silent WP03 action**: default STAYS is strongly preferred,
     and a verified-point-in-time MOVE must be **escalated to the operator** (the redirect-corpus gap must be
     resolved deliberately, not by silently regenerating the map). **If STAYS (expected default)**: leave it —
     no baseline impact.
- **Files**: `docs/migrations/teamspace-mission-state-920-closeout.md` (+ engineering-notes destination if
  verified); `occurrence_map.yaml` (only if promoted to MOVE).
- **Validation**: recorded verdict; file location matches verdict; if moved, the operator-escalation of the
  baseline-redirect gap is recorded.
- **Edge cases**: the wider `migrations/` dated-residue sweep is OUT of scope (only this one named file);
  default STAYS unless verified; a MOVE trips the baseline-published-URL redirect gap (escalate, do not
  silently regenerate the redirect map).

### Subtask T017 — Refresh `architecture/index.md` to full membership

- **Purpose**: FR-004 / SC-005 — the index currently lists ~4 of ~60 pages; make it enumerate 100% of the
  POST-MOVE section membership.
- **Steps**:
  1. After T012–T016 settle the section's membership, enumerate every remaining `.md` under
     `docs/architecture/` **RECURSIVELY, including subdirectory pages** (excluding the moved-out files;
     INCLUDING any borderline that STAYED). Concretely: if the crime-scene assessment STAYS (T015 default),
     `docs/architecture/assessments/code-as-a-crime-scene-overview.md` is a subdir page that MUST appear in the
     index — WP02's `index_completeness` recurses into the curated-complete section's subdirs, so a subdir page
     absent from `index.md` fails the check.
  2. Rewrite `docs/architecture/index.md` to list every page (match the existing index's link/entry style —
     read it first; it is small). Group logically if the current index groups.
  3. This is exactly what WP02's `index_completeness` check verifies for `architecture/` (the sole
     curated-complete section) — the index must enumerate 100% of the recursive membership or that check fails
     in WP05's sweep.
- **Files**: `docs/architecture/index.md`.
- **Validation**: every non-index `.md` in `architecture/` (incl. subdirs, e.g. `assessments/…`) appears in
  `index.md`; a manual diff of `ls docs/architecture/**/*.md` vs the index entries shows full coverage.
- **Edge cases**: do not list moved-out files; DO include subdirectory pages (the `index_completeness` check
  recurses — a STAYING `assessments/` page must be enumerated); do not relocate `index.md` (it stays).

## Test Strategy

- No unit tests authored here (content ops). Verification is structural:
  `git status` shows clean renames; `ls docs/architecture/` shows no dated dossier / no `audits/` dir;
  `architecture/index.md` covers the section.
- The link/freshness gates run in **WP05's** aggregate sweep — do NOT run `relative_link_fixer` /
  `check_docs_freshness` here (they need the redirect-map regen that WP05 owns).

## Risks & Mitigations

- **Editing derived artifacts**: touching `redirect_map.yaml`/inventory/`toc.yml` here would collide with
  WP05's single-writer regen — mitigate by strictly staying in owned_files + `index.md`.
- **Force-moving a borderline** (FR-002): mitigate by the recorded-verdict discipline — default STAYS.
- **Dropping the non-docs referrer**: the paradigm.yaml ref is invisible to `relative_link_fixer` — mitigate
  by the explicit T014 Activity-Log hand-off to WP05.
- **Guides-zone leak** (C-001): destinations are `engineering-notes/` only — never `guides/`.

## Review Guidance (reviewer-renata / opus)

Verify: all 9 firm files are under `engineering-notes/` via `git mv` (renames, not delete+add); `audits/`
grouped as `architecture-audits/`; each borderline carries a recorded verdict and its location matches
(default STAYS honoured — no force-move); `architecture/index.md` enumerates the full post-move membership;
NO edits to `redirect_map.yaml`/inventory/`toc.yml` (WP05 owns those); the non-docs paradigm referrer is
handed to WP05 in the Activity Log; nothing landed in `guides/`.

## Activity Log

> **CRITICAL**: entries in chronological order (oldest first, newest last). Append at the END.

- 2026-07-22T16:30:00Z – system – Prompt created.
</content>
