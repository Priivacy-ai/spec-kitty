---
work_package_id: WP10
title: 2x Versioned Docs Expansion
lane: "approved"
dependencies: [WP02, WP03, WP06]
requirement_refs: [FR-011]
planning_base_branch: fix/skill-audit-and-expansion
merge_target_branch: fix/skill-audit-and-expansion
branch_strategy: Planning artifacts for this feature were generated on fix/skill-audit-and-expansion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/skill-audit-and-expansion unless the human explicitly redirects the landing branch.
base_branch: 056-documentation-parity-sprint-WP10-merge-base
base_commit: c2e0ca9d75e42e104483b8d54f408f4a55d82f9c
created_at: '2026-03-22T15:07:16.088509+00:00'
subtasks: [T049, T050, T051, T052, T053]
agent: coordinator
shell_pid: '26483'
reviewed_by: "Robert Douglass"
review_status: "approved"
history:
- date: '2026-03-22'
  action: created
  agent: claude
  note: Generated from plan.md Phase 5
---

# WP10: 2x Versioned Docs Expansion

## Objective

Expand the thin 2x/ versioned docs and add cross-references to the new guides
created in WP02, WP03, and WP06. The 2x/ docs are the versioned track that
was previously the only content on the docs site.

## Context

These files are currently stubs:
- `docs/2x/doctrine-and-constitution.md` — 60 lines
- `docs/2x/glossary-system.md` — 37 lines
- `docs/2x/runtime-and-missions.md` — 49 lines

They need to be expanded with concise summaries and links to the comprehensive
guides now available in how-to/ and explanation/.

## Implementation

### T049: Expand doctrine-and-constitution.md

Read `docs/2x/doctrine-and-constitution.md` (60 lines). Expand to ~120-150
lines covering:
- What the constitution is and why it matters (2-3 paragraphs)
- The interview → generate → sync → context workflow (brief)
- Available directives and paradigms (list)
- Link to full guide: `../how-to/setup-governance.md`

### T050: Expand glossary-system.md

Read `docs/2x/glossary-system.md` (37 lines). Expand to ~100-120 lines covering:
- What the glossary does (1-2 paragraphs)
- The 4 scopes and precedence (brief table)
- Strictness modes (one-liner each)
- CLI commands overview (list with one-line descriptions)
- Link to full guide: `../how-to/manage-glossary.md`

### T051: Expand runtime-and-missions.md

Read `docs/2x/runtime-and-missions.md` (49 lines). Expand to ~120-150 lines:
- The 4 built-in missions (brief comparison table)
- What `spec-kitty next` does (one paragraph)
- The mission → feature → WP hierarchy (brief)
- Link to full guide: `../explanation/mission-system.md`
- Link to runtime loop: `../explanation/runtime-loop.md`

### T052: Add cross-references

In each expanded doc, add a "Learn More" section at the bottom with links to:
- The relevant how-to guide
- The relevant explanation doc
- The relevant reference doc

Ensure relative paths work from the 2x/ directory.

### T053: Update 2x/toc.yml

Verify `docs/2x/toc.yml` entries are correct. Add new entries if any new
files were created (unlikely — we're expanding existing files).

## Definition of Done

- [ ] doctrine-and-constitution.md expanded from 60 to 120+ lines
- [ ] glossary-system.md expanded from 37 to 100+ lines
- [ ] runtime-and-missions.md expanded from 49 to 120+ lines
- [ ] Cross-references to new guides added
- [ ] All relative links verified
- [ ] toc.yml verified

## Implementation Command

```bash
spec-kitty implement WP10 --base WP06
```

## Activity Log

- 2026-03-22T15:07:16Z – coordinator – shell_pid=26483 – lane=doing – Assigned agent via workflow command
- 2026-03-22T15:15:15Z – coordinator – shell_pid=26483 – lane=for_review – 2x docs expanded: doctrine 60->121 lines, glossary 37->103 lines, runtime 49->120 lines. Cross-references to how-to/explanation/reference guides added. toc.yml verified, all relative links validated.
- 2026-03-22T15:16:34Z – coordinator – shell_pid=26483 – lane=approved – Review passed: all 3 stubs expanded with content and cross-references
