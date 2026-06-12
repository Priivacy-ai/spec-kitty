---
work_package_id: WP02
title: Living-architecture layout + moves
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
tracker_refs:
- '#1805'
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "817895"
history:
- '2026-06-09: created by /spec-kitty.tasks (planner-priti)'
agent_profile: architect-alphonso
authoritative_surface: architecture/
execution_mode: code_change
owned_files:
- architecture/README.md
- architecture/vision/**
- architecture/audience/**
- architecture/1.x/**
- architecture/2.x/**
- architecture/3.x/vision/**
- architecture/3.x/research/**
- docs/explanation/**
- .kittify/charter/**
role: architect
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your profile first: `/ad-hoc-profile-load architect-alphonso`. Adopt its identity and boundaries before proceeding.

## Objective
Establish the **living-architecture-at-top + versioned-history-beneath** layout (R-02/R-03): top-level living `architecture/` with `vision/`, `audience/`, `diagrams/`, and a `README.md` that states the boundary rule; per-version `{adr,vision,research}` history beneath; **RECONCILE the already-canonical top-level layout and DELETE residual parallel content** (architecture/glossary/ pointer belongs to WP01; verify no stale `architecture/docs/` or misplaced narrative remains here — C-005); carry the C4 forward; rewrite architecture-path references (incl. the charter authority paths). Path rewrites guided by the reference-rewrite checklist in `occurrence_map.yaml` (architecture section, O1 revert — advisory checklist, not an enforcement gate).

## Context
- Decisions: research.md R-01 (boundary rule: architecture/ = decisions & models, docs/ = consumption, explanation links UP no dup), R-02 (living top + versioned history; decay = demote on obsolescence), R-03 (vision is an architecture concern; no docs/vision/). C-005 single source of truth — no parallel architecture narrative surfaces.
- The charter "Project authority paths" cite `architecture/2.x/adr/`, `architecture/adrs/`, `glossary/contexts/` — update them here (this WP owns `.kittify/charter/**`; glossary's canonical path confirmed by WP01).
- WP03 owns `architecture/diagrams/**` content and WP06 owns `architecture/3.x/adr/**` — create the skeletons here, leave their content to them.

## Subtasks
### T006 — Top-level living layout + README boundary rule
Create `architecture/vision/`, `architecture/diagrams/` (skeleton with numbered C4 level dirs), retain `architecture/audience/`. Rewrite `architecture/README.md`: boundary rule (architecture=decisions&models, docs=consumption), navigation, and the **decay rule** (living-at-top → demote to `architecture/<version>/` on obsolescence) so it can't re-drift.
### T007 — Carry C4 forward
Move the current C4 (markdown+mermaid) into `architecture/diagrams/{01_context,02_containers,03_components}/`; leave the `architecture/2.x/` snapshot frozen as history. (Content refresh is WP03.)
### T008 — Versioned history + docs de-dup
Ensure `architecture/{1.x,2.x,3.x}/{adr,vision,research}` exist; demote any obsolete top-level narrative into its version dir. Update `docs/explanation/` to **link up** to architecture (remove duplicated architecture narrative — single source of truth).
### T009 — Rewrite architecture references + charter authority paths
Rewrite all references to moved architecture/glossary paths, including the charter's authority paths (`.kittify/charter/**`). Finalize the architecture section of `occurrence_map.yaml` (all 8 categories explicit).
### T010 — Reference-integrity verification
Grep for old paths (`architecture/2.x/adr`, `architecture/glossary`, etc.); confirm only intended/historical hits. Fill the occurrence_map verification block.

## Branch Strategy
Plan/merge target `feat/doctrine-glossary-consolidation-01KTNWFC`; per-lane worktree from `lanes.json` after finalize.

## Ownership & out-of-map edits
Owned: frontmatter. **Out-of-map edits allowed with a recorded one-line rationale.** Coordinate the charter authority-path file with WP01's glossary path output. Don't touch `architecture/diagrams/**` content (WP03) or `architecture/3.x/adr/**` (WP06) beyond skeletons.

## Review / Sign-off (R-07)
**architect-alphonso sign-off** on the boundary rule + layout + decay rule; reviewer profile for reference integrity.

## Definition of Done
- Living layout in place; README states boundary + decay rules; C4 carried forward; versioned history coherent; docs/explanation links up (no dup); all architecture refs rewritten; reference-integrity grep clean; occurrence_map architecture section finalized (advisory checklist, O1 revert).
- Closes #1805 (architecture/docs restructure + C4 refresh — folded as this mission's source FR).
- Consolidated doctrine artifact layout must not foreclose a future optional per-artifact tier field (upstream #1843): tiers, when they come, are declared fields — never directory structure.

## Risks
- Broken internal doc links; charter authority-path miss. Mitigate via occurrence-map + grep (T010).

## Activity Log

- 2026-06-11T15:10:07Z – claude:opus:curator-carla:implementer – shell_pid=804690 – Assigned agent via action command
- 2026-06-11T15:22:08Z – claude:opus:curator-carla:implementer – shell_pid=804690 – Living-architecture layout: top-level vision/ + diagrams/ (C4 carried forward, frozen 2.x retained), versioned-history vision/research slots in 1.x/2.x/3.x, README boundary+decay rules, deleted glossary row dropped + glossary canon repointed to top-level, ARCHITECTURE_DOCS_GUIDE current-track=3.x. Closes #1805. #1843 non-foreclosure noted (tier=declared field not directory). Gates: terminology PASS; link/glossary 1493 passed (1 pre-existing unrelated kitty-specs contract-example failure); markdownlint-cli2@0.18.1 (CI-pinned) 0 errors. Commit 33d41f59f. Out-of-map (warned, rationale): diagrams/** = T007-mandated skeleton (content=WP03); ARCHITECTURE_DOCS_GUIDE = T009 ref-correctness. NOTE: charter authority-path 2.x/adr->3.x/adr modernization NOT done — escalated (touches generation-fed prompt templates + resolver + 3 tests); 2.x/adr did not 'move' so left intact pending architect call.
- 2026-06-11T15:23:08Z – claude:opus:reviewer-renata:reviewer – shell_pid=817895 – Started review via action command
- 2026-06-11T15:27:03Z – user – shell_pid=817895 – Review passed: living-architecture layout (vision/ + diagrams/{01_context,02_containers,03_components}) established; README boundary+decay rules present; #1843 non-foreclosure DoD satisfied (tier=declared field, never directory — README L67-71); glossary structure-row dropped, repointed to top-level glossary/; C4 carried forward (635 lines, mermaid intact) with all relative links resolving incl. 2.x anchors; frozen 2.x snapshot (adr/C4/README) untouched, only additive 1.x/2.x/3.x research+vision history slots; #1805 restructure substantively delivered; reference-integrity grep clean (no stale architecture/docs or architecture/glossary live refs); ARCHITECTURE_DOCS_GUIDE current-track=3.x. Gates: terminology 2 passed; markdownlint-cli2@0.18.1 0 errors/277 files; link+glossary 1493 passed (1 PRE-EXISTING unrelated failure: charter-extends-and-drg-regen.md MISSING_FRONTMATTER, untouched by WP02 delta, last edited in planning commit 040cc7ce8 — reported per Pre-existing Failure Reporting Rule, non-blocking). STOP adjudicated SOUND: charter 2.x/adr->3.x/adr authority-pointer flip is a policy modernization (not a moved-path rewrite per T009) touching generation templates+resolver+3 tests; charter authority paths (glossary/contexts/, architecture/2.x/adr/, architecture/adrs/) all resolve to existing locations incl. compat symlinks — no broken refs. Deferred to WP06 (owns 3.x/adr/**) with recorded note; duplicate doctrine-layer-merge-semantics ADR (2.x+3.x copies) flagged as WP06 input. Out-of-map edits (diagrams/** T007 skeleton, ARCHITECTURE_DOCS_GUIDE T009) have documented rationale and are in-scope.
