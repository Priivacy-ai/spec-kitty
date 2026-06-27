---
work_package_id: WP01
title: Reconciliation ADR (serial spine)
dependencies: []
requirement_refs:
- C-004
- FR-001
tracker_refs: []
planning_base_branch: docs/2165-consolidation-research
merge_target_branch: docs/2165-consolidation-research
branch_strategy: Planning artifacts for this mission were generated on docs/2165-consolidation-research. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-consolidation-research unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: architect-alphonso
authoritative_surface: architecture/3.x/adr/2026-06-27-1-common-docs-reconciliation.md
create_intent:
- architecture/3.x/adr/2026-06-27-1-common-docs-reconciliation.md
execution_mode: code_change
owned_files:
- architecture/3.x/adr/2026-06-27-1-common-docs-reconciliation.md
role: implementer
tags: []
shell_pid: "518690"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load architect-alphonso` (or read `src/doctrine/agent_profiles/built-in/architect-alphonso.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Author **one** reconciliation ADR that decides every open mechanism the Common Docs consolidation depends on, so Mission B opens with **zero undecided design**. This ADR is the **serial spine** — every other WP in Mission A and all of Mission B sits behind it (C-001: it must be accepted + merged before Mission B begins).

## Context

This is Mission A (the governed foundation) of a 3-ship split. The research is in `docs/engineering_notes/651-docs-consolidation/` (treat as ground truth) and the decisions are pre-settled by a 5-lens squad — your job is to **record them precisely in canonical ADR form**, not re-litigate them. Use the existing ADR convention in `architecture/3.x/adr/` (read 2-3 recent ADRs for the house style). **Do NOT mutate any doc-tree file** (C-006) — you author exactly one new ADR.

## Subtasks

### T001 — Scaffold the ADR
Create `architecture/3.x/adr/2026-06-27-1-common-docs-reconciliation.md` with the house header (Status: Accepted, Date, Deciders, Context). Context = the four-root + shadow-tree split-brain, the metadata split-brain, DocFX-on-GitHub-Pages, ~117 unique ADRs (191 files; the 20 era-less in flat `architecture/adrs/` are the exact figure).

### T002 — Decide Candidate A + `doc_status` + the 13-section structure
Record: in-file frontmatter is the metadata SSOT; the page-inventory becomes a generated/validated lockfile; `citation_refs` is dropped. The frontmatter status key is **`doc_status`** (namespaced — bare `status` collides with the WP-lane model, C-004). The target tree is the 13-section Common Docs structure with **`adr/<era>/`** (relax the standard's flat `adr/` to preserve the 99/120-ADR era history).

### T003 — Decide the DocFX redirect mechanism
Record: DocFX + GitHub Pages have **no native redirect**; the chosen mechanism is **generated `<meta http-equiv="refresh">` stub pages per old path**, emitted into the DocFX `_site` from a checked-in redirect map (a post-build step in `scripts/docs/`). Note that a captured baseline URL inventory is the denominator for "100% URLs resolve" (Mission B's NFR).

### T004 — Decide the glossary read-path mapping
Record (the load-bearing C-001 decision): the dashboard's `GlossaryHandler` reads `.kittify/glossaries/<scope>.yaml` **seed files** (via `load_seed_file()`), **not** the human `glossary/contexts/*.md`. The move of the human markdown to `context/` MUST preserve or regenerate the seed read-path, and the doctrine-extraction source is the seed. State which artifact moves and how both paths stay intact.

### T005 — Decide the era-less-ADR migration plan + the curation policy
Record: the **20 ADRs that live only in flat `architecture/adrs/`** (no era home) are 3.x by date → migrate to `adr/3.x/` (executed in Mission B), and the flat shim closes only after migration. Record the delete-stale curation policy + the distil-then-retire lifecycle for in-flight investigations (→ `plans/`).

### T006 — Record acceptance + the merge-boundary
Mark the ADR Accepted and state explicitly that **Mission B is blocked until this ADR is merged** (C-001 is a merge boundary, not intra-mission ordering).

## Branch Strategy

Planning + final merge target: `docs/2165-consolidation-research`. Execution worktree is allocated per the computed lane in `lanes.json` (this is the Lane-A spine — it gates WP02–WP06).

## Definition of Done

- [ ] One new ADR at the owned path, in canonical house style.
- [ ] Each of the 7 decisions matches its **pre-settled value** (not just "a paragraph exists"): D1 Candidate A; D2 `doc_status`; D3 13-section + `adr/<era>/`; D4 meta-refresh stub map; D5 `load_seed_file()` seed read-path preserved; D6 era-less→`adr/3.x/` by date; D7 delete-stale + distil-then-retire.
- [ ] The merge-boundary note (C-001) is recorded.
- [ ] No doc-tree file other than the new ADR is touched (C-006).
- [ ] `ruff`/terminology guard clean on the new file.

## Risks & Reviewer Guidance

- The **redirect mechanism (T003)** and the **glossary read-path (T004)** are the load-bearing decisions — Mission B's NFR-002 and C-006 rest on them; review them hardest.
- Reviewer: confirm each of the 7 decisions is decided (not deferred), and that the ADR does not itself move/rename any doc (it's authored in place; its own relocation is Mission B's job).

## Activity Log

- 2026-06-27T06:36:40Z – claude:opus:architect-alphonso:implementer – shell_pid=504343 – Assigned agent via action command
- 2026-06-27T06:40:40Z – claude:opus:architect-alphonso:implementer – shell_pid=504343 – Ready for review: reconciliation ADR records all 7 pre-settled decisions + C-001 merge boundary
- 2026-06-27T06:41:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=518690 – Started review via action command
- 2026-06-27T06:47:01Z – user – shell_pid=518690 – Review passed (reviewer-renata): all 7 ADR decisions at pre-settled values, C-006 single-file, merge-boundary recorded; issue-matrix filled by orchestrator.
