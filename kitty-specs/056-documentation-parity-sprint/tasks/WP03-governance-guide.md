---
work_package_id: WP03
title: Project Governance Guide
lane: planned
dependencies: [WP01]
requirement_refs: [FR-003]
planning_base_branch: fix/skill-audit-and-expansion
merge_target_branch: fix/skill-audit-and-expansion
branch_strategy: Planning artifacts for this feature were generated on fix/skill-audit-and-expansion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/skill-audit-and-expansion unless the human explicitly redirects the landing branch.
subtasks: [T011, T012, T013, T014, T015, T016]
history:
- date: '2026-03-22'
  action: created
  agent: claude
  note: Generated from plan.md Phase 2
---

# WP03: Project Governance Guide

## Objective

Create `docs/how-to/setup-governance.md` — a user-facing guide distilled from
the `spec-kitty-constitution-doctrine` skill. Walk users through the interview,
generation, sync, and context workflow. Omit extraction regex patterns, parser
internals, and compiler implementation details.

## Source Material

Read `src/doctrine/skills/spec-kitty-constitution-doctrine/SKILL.md` and its
references for the full technical detail.

## Implementation

### T011: Three-layer model explanation

Open with a clear explanation of the 3 layers:
1. Constitution (constitution.md) — the human-editable policy document
2. Extracted config (governance.yaml, directives.yaml) — machine-readable, auto-generated
3. Doctrine references (library/*.md) — detailed guidance docs

Key message: edit constitution.md, everything else is derived.

### T012: Interview workflow

Document both paths with commands:
- Quick: `spec-kitty constitution interview --profile minimal --defaults --json`
- Full: `spec-kitty constitution interview --profile comprehensive`

Explain the 8 minimal questions and what they control. Mention that comprehensive
adds 3 more (documentation, risk, amendment policies).

### T013: Generation and sync

Document the generation and sync commands:
```bash
spec-kitty constitution generate --from-interview --json
spec-kitty constitution sync --json
spec-kitty constitution sync --force --json
spec-kitty constitution status --json
```

Explain that generate triggers sync automatically. Explain hash-based staleness
detection at user level (status shows "stale" when constitution.md changed
since last sync).

### T014: Context loading

Explain how governance context affects workflow actions:
```bash
spec-kitty constitution context --action implement --json
```

Show that the runtime calls this automatically during slash commands. Manual
invocation is for debugging. Explain bootstrap vs compact modes at user level.

### T015: Anti-patterns

List the common mistakes:
- Editing governance.yaml directly (overwritten by sync)
- Skipping the interview (generic defaults)
- Stale constitution (wrong policy injected)

### T016: Update toc.yml

Add `setup-governance.md` entry to `docs/how-to/toc.yml`.

## Definition of Done

- [ ] Guide created at `docs/how-to/setup-governance.md`
- [ ] All CLI commands verified against `--help`
- [ ] No internal architecture details (no parser regex, no compiler internals)
- [ ] toc.yml updated

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```
