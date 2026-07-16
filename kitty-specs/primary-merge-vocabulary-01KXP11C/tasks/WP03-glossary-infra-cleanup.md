---
work_package_id: WP03
title: Glossary-infrastructure cleanup (README + prose fold)
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: feat/terminology-primary-merge-disambiguation
merge_target_branch: feat/terminology-primary-merge-disambiguation
branch_strategy: Planning artifacts for this mission were generated on feat/terminology-primary-merge-disambiguation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/terminology-primary-merge-disambiguation unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
phase: Phase 2 - Hygiene
assignee: ''
agent: "claude"
shell_pid: "1158279"
shell_pid_created_at: "1784230336.27"
history:
- at: '2026-07-16T18:15:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: glossary/
create_intent:
- docs/context/historical-terms.md
- docs/context/naming-decision-tool-vs-agent.md
execution_mode: code_change
model: ''
owned_files:
- glossary/README.md
- glossary/historical-terms.md
- glossary/naming-decision-tool-vs-agent.md
- docs/context/index.md
- src/doctrine/README.md
role: curator
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Glossary-infrastructure cleanup

## ⚡ Do This First: Load Agent Profile
Load `curator-carla` via `/ad-hoc-profile-load`.

## Objectives & Success Criteria
- One prose-glossary home: `glossary/README.md` no longer points at the dead `glossary/contexts/` dir; legacy `glossary/` prose relocated under `docs/context/` per occurrence_map `moves[]`.
- `relative_link_fixer --check` clean; `.github` symlinks intact.

## Context & Constraints
- Depends on WP01 (canonical entries exist in `docs/context/` to point at).
- occurrence_map `moves[]`: `glossary/historical-terms.md` + `glossary/naming-decision-tool-vs-agent.md` → `docs/context/`. `glossary/README.md` is repointed **in place** (not moved).
- Downstream consumers of the `glossary/` surface (#1341 event-log SoT, #648 static-site) — note only; no change required here.

## Subtasks & Detailed Guidance
### T010 – Repoint `glossary/README.md` context links → `docs/context/` (FR-005).
### T011 – `git mv` the two legacy prose files → `docs/context/`; preserve headings; add to `docs/context/index.md` (FR-006).
### T012 – Update inbound references + fix `../` relative links; `git add -f` any `.github` symlinks. **Include the inline-code path reference at `src/doctrine/README.md:48`** (`` `glossary/naming-decision-tool-vs-agent.md` `` → new `docs/context/` path) — it is inline-code, NOT a markdown link, so `relative_link_fixer --check` will NOT catch it. (Also note historical refs in `docs/plans/initiatives/2026-04-*/README.md:77,90` — lower priority, update if trivial.)

## Test Strategy
- `uv run python -m scripts.docs.relative_link_fixer --check`; anti-sprawl ratchet `--strict`; description-length gate on moved pages.

## Risks & Mitigations
- Moving docs breaks `../` links + `.github` symlinks — the classic docs-move gate; run the link fixer before commit.

## Review Guidance
- Confirm no dead `glossary/contexts/` link remains; moved pages carry valid frontmatter + appear in index.

## Activity Log
- 2026-07-16T18:15:00Z – system – Prompt created.
- 2026-07-16T19:23:42Z – claude – shell_pid=1126696 – Assigned agent via action command
- 2026-07-16T19:28:48Z – claude – shell_pid=1126696 – Glossary README repointed; legacy prose folded to docs/context; doctrine README inline-ref fixed
- 2026-07-16T19:32:23Z – claude – shell_pid=1158279 – Started review via action command
- 2026-07-16T19:32:47Z – user – shell_pid=1158279 – FR-005: glossary/README.md has 0 glossary/contexts refs, all backtick paths repoint to live docs/context/*.md (spot-checked 7 targets exist). FR-006: both prose files git-mv'd (R077/R079, --follow shows history continuity), glossary/ now holds only README.md, valid frontmatter with descriptions 146/153 chars (<=180), both linked in docs/context/index.md. T012: src/doctrine/README.md inline-ref repointed. Gates clean: relative_link_fixer --check (0 dead), anti_sprawl_ratchet --strict (0), description_length_check --strict (0/461). Scope clean: only 5 owned/create-intent paths, no code. Orphaned refs at docs/plans/initiatives/2026-04-*/README.md:77,90 are in a historical draft plan (not owned), task-scoped as lower-priority note.
